"""
app_hedge.py — Application « Couverture (Hedge) » du bureau (NATIVE).

Deux stratégies RÉELLES (exécutables, pas des maquettes) :

- PUT INDICE (portefeuille) : réutilise le desk de couverture existant
  (`core/hedging.py` — put protecteur sur l'indice régional, prime
  Black-Scholes, dénoué à l'échéance par le moteur). L'app ajoute le
  DIMENSIONNEMENT au bêta : elle calcule le bêta du panier vs l'indice
  (core/quant_tools.beta) et propose un notionnel = bêta × exposition
  longue — la taille de put qui neutralise (au 1er ordre) le risque de
  marché du book. Choix strike/maturité, prime affichée AVANT l'achat,
  liste des puts en cours avec valeur mark-to-model.

- PAIRE (position) : couvre UNE position longue par la vente à découvert
  d'une action corrélée — ratio de couverture à variance minimale
  h = cov/var (core/quant_tools.hedge_ratio), candidats suggérés par
  corrélation décroissante, qualité affichée (corrélation, R², vol
  résiduelle attendue). L'exécution passe par core/portfolio.short
  (soumise au déblocage « leverage », comme la commande SHORT).
"""
import pygame

from apps.base import DesktopApp
from core import config, unlocks
from core import hedging as H
from core import portfolio as pf
from core import quant_tools as QT
from ui import fonts, widgets

NOTIONAL_STEPS = [0.5, 1.0]      # fractions du notionnel bêta proposées


class HedgeApp(DesktopApp):
    title = "Couverture"
    icon_kind = "shield"
    default_size = (980, 620)
    min_size = (720, 480)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.mode = "put"                    # "put" | "pair"
        self.strike_idx = 1                  # défaut -5 %
        self.years_idx = 0                   # défaut 3 mois
        self.notional_frac = 1.0             # × notionnel bêta
        self.pair_ticker = None              # position à couvrir
        self.pair_hedge = None               # instrument de couverture
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self._cache_key = None
        self._ctx = None
        self._mode_rects = {}
        self._strike_rects = {}
        self._years_rects = {}
        self._frac_rects = {}
        self._buy_btn = None
        self._pos_rects = {}
        self._cand_rects = {}
        self._short_btn = None

    # ------------------------------------------------------------ contexte
    def _ensure_ctx(self):
        p = self.app.gs.player
        key = (self.market.step_count, self.mode, self.strike_idx,
               self.years_idx, round(self.notional_frac, 2),
               self.pair_ticker, self.pair_hedge, len(p.portfolio),
               len(getattr(p, "hedges", []) or []))
        if key == self._cache_key:
            return
        self._cache_key = key
        self._ctx = self._compute()

    def _compute(self):
        p = self.app.gs.player
        m = self.market
        ctx = {"gross": pf.gross_exposure(p, m),
               "coverage": H.coverage_ratio(p, m),
               "hedges": H.holdings(p, m)}
        # bêta du panier vs l'indice régional
        port_r, _tks = QT.portfolio_step_returns(p, m)
        idx = QT.main_index(m, p)
        bench_r = QT.index_returns(m, idx)
        ctx["index"] = idx
        ctx["beta"] = QT.beta(port_r, bench_r) if len(port_r) else 0.0
        long_val = sum(h["value"] for h in pf.holdings(p, m) if not h["short"])
        ctx["long_value"] = long_val
        ctx["beta_notional"] = max(0.0, ctx["beta"]) * long_val
        if self.mode == "put":
            strike_pct = H.STRIKE_CHOICES[self.strike_idx]
            years = H.MATURITY_CHOICES[self.years_idx]
            try:
                q = H.quote(p, m, strike_pct, years)
            except Exception:
                q = None
            ctx["quote"] = q
            notional = ctx["beta_notional"] * self.notional_frac
            if notional <= 0:
                notional = long_val * self.notional_frac
            ctx["notional"] = notional
            ctx["premium"] = (notional * q["premium_rate"]) if q else 0.0
        else:
            held = [h for h in pf.holdings(p, m) if not h["short"]]
            ctx["held"] = held
            if self.pair_ticker is None and held:
                self.pair_ticker = held[0]["ticker"]
            if self.pair_ticker:
                cands = QT.hedge_candidates(m, self.pair_ticker, n=5)
                ctx["candidates"] = cands
                if self.pair_hedge is None and cands:
                    self.pair_hedge = cands[0][0]
                if self.pair_hedge:
                    a = QT.returns_of(m, self.pair_ticker)
                    h = QT.returns_of(m, self.pair_hedge)
                    ctx["hr"] = QT.hedge_ratio(a, h)
                    pos = p.portfolio.get(self.pair_ticker)
                    val = (pos["shares"] * (m.price_of(self.pair_ticker) or 0.0)
                           if pos else 0.0)
                    ctx["pos_value"] = max(0.0, val)
                    hp = m.price_of(self.pair_hedge) or 0.0
                    ctx["hedge_price"] = hp
                    ctx["hedge_qty"] = (int(round(ctx["hr"]["ratio"] * ctx["pos_value"] / hp))
                                        if hp > 0 else 0)
        return ctx

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for mode, r in self._mode_rects.items():
            if r.collidepoint(pos):
                self.mode = mode
                self.msg = ""
                return True
        if self.mode == "put":
            for i, r in self._strike_rects.items():
                if r.collidepoint(pos):
                    self.strike_idx = i
                    return True
            for i, r in self._years_rects.items():
                if r.collidepoint(pos):
                    self.years_idx = i
                    return True
            for f, r in self._frac_rects.items():
                if r.collidepoint(pos):
                    self.notional_frac = f
                    return True
            if self._buy_btn and self._buy_btn.collidepoint(pos):
                self._buy_put()
                return True
        else:
            for tk, r in self._pos_rects.items():
                if r.collidepoint(pos):
                    self.pair_ticker = tk
                    self.pair_hedge = None
                    return True
            for tk, r in self._cand_rects.items():
                if r.collidepoint(pos):
                    self.pair_hedge = tk
                    return True
            if self._short_btn and self._short_btn.collidepoint(pos):
                self._exec_pair()
                return True
        return False

    def _buy_put(self):
        p = self.app.gs.player
        if not unlocks.unlocked(p, "hedge"):
            g = unlocks.effective_required_grade(p, "hedge")
            self._say(f"Couverture verrouillée (débloquée au grade {config.GRADES[g]}).",
                      config.COL_DOWN)
            return
        ctx = self._ctx or {}
        notional = ctx.get("notional", 0.0)
        if notional <= 0:
            self._say("Rien à couvrir : aucune exposition longue.", config.COL_DOWN)
            return
        r = H.buy_put(p, self.market, notional,
                      H.STRIKE_CHOICES[self.strike_idx],
                      H.MATURITY_CHOICES[self.years_idx])
        if r.get("ok"):
            self._say(f"Put souscrit : {widgets.format_money(notional, self._cur())} "
                      f"couverts, prime {widgets.format_money(r['premium'], self._cur())}.",
                      config.COL_UP)
            self._cache_key = None
        else:
            reason = {"cash": "trésorerie insuffisante pour la prime",
                      "notional": "notionnel invalide"}.get(r.get("reason"),
                                                            r.get("reason", "?"))
            self._say(f"Refusé : {reason}.", config.COL_DOWN)

    def _exec_pair(self):
        p = self.app.gs.player
        if not unlocks.unlocked(p, "leverage"):
            g = unlocks.effective_required_grade(p, "leverage")
            self._say(f"Vente à découvert verrouillée (grade {config.GRADES[g]}).",
                      config.COL_DOWN)
            return
        ctx = self._ctx or {}
        qty = ctx.get("hedge_qty", 0)
        if qty < 1 or not self.pair_hedge:
            self._say("Ratio trop faible : rien à shorter.", config.COL_DOWN)
            return
        r = pf.short(p, self.market, self.pair_hedge, qty)
        if r.get("ok"):
            self._say(f"Couverture posée : short {qty} × {self.pair_hedge} "
                      f"(ratio {ctx['hr']['ratio']:.2f}).", config.COL_UP)
            self._cache_key = None
        else:
            self._say(f"Short refusé : {r.get('reason', '?')}.", config.COL_DOWN)

    def _say(self, text, col):
        self.msg, self.msg_col = text, col

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_ctx()
        surf.fill(config.COL_BG, rect)
        pad = 14
        cur = self._cur()
        ctx = self._ctx or {}
        widgets.draw_text(surf, "COUVERTURE — PROTECTION DU PORTEFEUILLE",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        # tuiles d'exposition
        tiles = [
            ("EXPOSITION LONGUE", widgets.format_money(ctx.get("long_value", 0.0), cur)),
            (f"BÊTA vs {ctx.get('index', '—')}", f"{ctx.get('beta', 0.0):.2f}"),
            ("DÉJÀ COUVERT", f"{ctx.get('coverage', 0.0) * 100:.0f}%"),
        ]
        tx, ty = rect.x + pad, rect.y + 34
        for label, val in tiles:
            tw = max(150, fonts.small(bold=True).size(val)[0] + 24)
            tr = pygame.Rect(tx, ty, tw, 44)
            pygame.draw.rect(surf, config.COL_PANEL, tr, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, tr, 1, border_radius=4)
            widgets.draw_text(surf, label, (tr.x + 8, tr.y + 5), fonts.tiny(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (tr.x + 8, tr.y + 20),
                              fonts.small(bold=True), config.COL_TEXT)
            tx += tw + 8
        # onglets
        self._mode_rects = {}
        mx = rect.x + pad
        my = ty + 54
        for mode, lbl in (("put", "PUT INDICE (portefeuille)"),
                          ("pair", "PAIRE (position)")):
            w = fonts.tiny(bold=True).size(lbl)[0] + 18
            r = pygame.Rect(mx, my, w, 22)
            self._mode_rects[mode] = r
            sel = mode == self.mode
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            mx += w + 8
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(),
                                                     rect.right - pad - mx - 6),
                              (mx + 6, my + 5), fonts.tiny(), self.msg_col)
        body = pygame.Rect(rect.x + pad, my + 30, rect.w - 2 * pad,
                           rect.bottom - pad - my - 30)
        if self.mode == "put":
            self._draw_put(surf, body, ctx, cur)
        else:
            self._draw_pair(surf, body, ctx, cur)

    # ----------------------------------------------------------- mode put
    def _draw_put(self, surf, body, ctx, cur):
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left, "Nouveau put protecteur",
                                   config.COL_CYAN)
        y = inner.y + 2
        widgets.draw_text(surf, "Strike (% de l'indice) :", (inner.x, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        x = inner.x + 150
        self._strike_rects = {}
        for i, spct in enumerate(H.STRIKE_CHOICES):
            lbl = f"{spct * 100:.0f}%"
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y - 3, w, 20)
            self._strike_rects[i] = r
            sel = i == self.strike_idx
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        y += 28
        widgets.draw_text(surf, "Maturité :", (inner.x, y), fonts.tiny(bold=True),
                          config.COL_TEXT_DIM)
        x = inner.x + 150
        self._years_rects = {}
        for i, yr in enumerate(H.MATURITY_CHOICES):
            lbl = f"{int(yr * 12)} mois" if yr < 1 else f"{yr:.0f} an"
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y - 3, w, 20)
            self._years_rects[i] = r
            sel = i == self.years_idx
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        y += 28
        widgets.draw_text(surf, "Taille (× notionnel bêta) :", (inner.x, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        x = inner.x + 150
        self._frac_rects = {}
        for f in NOTIONAL_STEPS:
            lbl = f"{f:.0%}"
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y - 3, w, 20)
            self._frac_rects[f] = r
            sel = abs(f - self.notional_frac) < 1e-9
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        y += 30
        q = ctx.get("quote")
        if q:
            widgets.draw_text(surf, f"Indice {q['underlying']} : {q['spot']:,.0f} — "
                              f"strike {q['strike']:,.0f} · vol {q['sigma'] * 100:.0f}% "
                              f"· taux {q['rate'] * 100:.1f}%",
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 20
            widgets.draw_text(surf, f"Notionnel couvert : "
                              f"{widgets.format_money(ctx.get('notional', 0.0), cur)}",
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            y += 22
            widgets.draw_text(surf, f"Prime à payer : "
                              f"{widgets.format_money(ctx.get('premium', 0.0), cur)} "
                              f"({q['premium_rate'] * 100:.2f}% du notionnel)",
                              (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            y += 30
        self._buy_btn = pygame.Rect(inner.x, y, 190, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._buy_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._buy_btn, 1, border_radius=4)
        widgets.draw_text(surf, "SOUSCRIRE LE PUT", self._buy_btn.center,
                          fonts.small(bold=True), config.COL_UP, align="center")
        widgets.draw_text(surf, "Si l'indice finit sous le strike à l'échéance, le put "
                          "paie la différence — la prime est le coût de l'assurance.",
                          (inner.x, inner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)
        # puts en cours
        rinner = widgets.draw_panel(surf, right, "Couvertures en cours",
                                    config.COL_AMBER)
        hedges = ctx.get("hedges", [])
        if not hedges:
            widgets.draw_text(surf, "Aucun put en cours.", (rinner.x, rinner.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        y = rinner.y + 2
        for hpos in hedges[:10]:
            if y > rinner.bottom - 30:
                break
            col = config.COL_UP if hpos["in_money"] else config.COL_TEXT_DIM
            widgets.draw_text(surf, f"{hpos['underlying']} · strike "
                              f"{hpos['strike_pct'] * 100:.0f}% · "
                              f"{widgets.format_money(hpos['notional'], cur)}",
                              (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"indice {hpos['perf']:+.1f}% depuis l'achat · "
                              f"échéance dans {hpos['steps_left']} pas · "
                              + ("DANS LA MONNAIE" if hpos["in_money"] else "hors monnaie"),
                              (rinner.x + 10, y + 17), fonts.tiny(), col)
            y += 40

    # ---------------------------------------------------------- mode pair
    def _draw_pair(self, surf, body, ctx, cur):
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left, "Position à couvrir", config.COL_CYAN)
        held = ctx.get("held", [])
        self._pos_rects = {}
        if not held:
            widgets.draw_text(surf, "Aucune position longue à couvrir.",
                              (inner.x, inner.y + 4), fonts.tiny(), config.COL_TEXT_DIM)
        y = inner.y + 2
        for h in held[:12]:
            if y > inner.bottom - 20:
                break
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 20)
            self._pos_rects[h["ticker"]] = r
            sel = h["ticker"] == self.pair_ticker
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, h["ticker"], (inner.x, y), fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            widgets.draw_text(surf, widgets.format_money(h["value"], cur),
                              (inner.x + 90, y), fonts.small(), config.COL_TEXT_DIM)
            y += 21
        # candidats + qualité + exécution
        rinner = widgets.draw_panel(surf, right, "Instrument de couverture (short)",
                                    config.COL_AMBER)
        cands = ctx.get("candidates", [])
        self._cand_rects = {}
        y = rinner.y + 2
        if not cands:
            widgets.draw_text(surf, "Sélectionnez une position à gauche.",
                              (rinner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        for tk, corr in cands:
            r = pygame.Rect(rinner.x - 4, y - 2, rinner.w + 8, 20)
            self._cand_rects[tk] = r
            sel = tk == self.pair_hedge
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, tk, (rinner.x, y), fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            widgets.draw_text(surf, f"corr {corr:+.2f}", (rinner.x + 90, y),
                              fonts.small(), config.COL_TEXT_DIM)
            y += 21
        hr = ctx.get("hr")
        if hr and self.pair_hedge:
            y += 8
            widgets.draw_text(surf, f"Ratio min-variance h = {hr['ratio']:.2f} · "
                              f"R² = {hr['r2'] * 100:.0f}%",
                              (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            y += 20
            widgets.draw_text(surf, f"Vol résiduelle attendue : "
                              f"{hr['resid_vol_pct']:.0f}% de la vol d'origine",
                              (rinner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 22
            qty = ctx.get("hedge_qty", 0)
            widgets.draw_text(surf, f"Ordre : SHORT {qty} × {self.pair_hedge} "
                              f"(≈ {widgets.format_money(qty * ctx.get('hedge_price', 0.0), cur)})",
                              (rinner.x, y), fonts.small(bold=True), config.COL_DOWN)
            y += 26
            self._short_btn = pygame.Rect(rinner.x, y, 190, 26)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._short_btn,
                             border_radius=4)
            pygame.draw.rect(surf, config.COL_DOWN, self._short_btn, 1, border_radius=4)
            widgets.draw_text(surf, "EXÉCUTER LE SHORT", self._short_btn.center,
                              fonts.small(bold=True), config.COL_DOWN, align="center")
        else:
            self._short_btn = None
        widgets.draw_text(surf, "Plus la corrélation est forte, plus le short "
                          "compense les variations de la position couverte.",
                          (rinner.x, rinner.bottom - 14), fonts.tiny(),
                          config.COL_TEXT_DIM)
