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
from core import config, i18n, unlocks
from core import hedging as H
from core import portfolio as pf
from core import quant_tools as QT
from ui import fonts, widgets

NOTIONAL_STEPS = [0.5, 1.0]      # fractions du notionnel bêta proposées


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


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

    def _hedge_before_after(self, ctx):
        """Perte du portefeuille à marché -10 % avant/après le put proposé
        (core/trade_preview + crisis_lab sur une copie) — en cache par
        (pas de marché, strike, maturité)."""
        key = (self.market.step_count, self.strike_idx, self.years_idx,
               round(ctx.get("notional", 0.0), -3))
        cached = getattr(self, "_ba_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        out = None
        notional = ctx.get("notional", 0.0)
        if notional > 0:
            try:
                from core import crisis_lab
                from core import trade_preview as tp
                p = self.app.gs.player
                before = crisis_lab.reprice(p, self.market, eq_shock=-0.10, dy=0.0)["total"]
                q = tp.clone_player(p)
                r = H.buy_put(q, self.market, notional,
                              H.STRIKE_CHOICES[self.strike_idx],
                              H.MATURITY_CHOICES[self.years_idx])
                if r.get("ok"):
                    after = crisis_lab.reprice(q, self.market, eq_shock=-0.10, dy=0.0)["total"]
                    out = {"before": before, "after": after}
            except Exception:
                from core import crashlog
                crashlog.swallowed("app_hedge.before_after")
        self._ba_cache = (key, out)
        return out

    def _buy_put(self):
        p = self.app.gs.player
        if not unlocks.unlocked(p, "hedge"):
            g = unlocks.effective_required_grade(p, "hedge")
            self._say(_L(f"Couverture verrouillée (débloquée au grade {config.GRADES[g]}).", f"Hedging locked (unlocked at grade {config.GRADES[g]})."),
                      config.COL_DOWN)
            return
        ctx = self._ctx or {}
        notional = ctx.get("notional", 0.0)
        if notional <= 0:
            self._say(_L("Rien à couvrir : aucune exposition longue.", "Nothing to hedge: no long exposure."), config.COL_DOWN)
            return
        r = H.buy_put(p, self.market, notional,
                      H.STRIKE_CHOICES[self.strike_idx],
                      H.MATURITY_CHOICES[self.years_idx])
        if r.get("ok"):
            self._say(_L(f"Put souscrit : {widgets.format_money(notional, self._cur())} "
                         f"couverts, prime {widgets.format_money(r['premium'], self._cur())}.",
                         f"Put bought: {widgets.format_money(notional, self._cur())} "
                         f"hedged, premium {widgets.format_money(r['premium'], self._cur())}."),
                      config.COL_UP)
            self._cache_key = None
        else:
            reason = {"cash": _L("trésorerie insuffisante pour la prime", "insufficient cash for the premium"),
                      "notional": _L("notionnel invalide", "invalid notional")}.get(r.get("reason"),
                                                            r.get("reason", "?"))
            self._say(_L(f"Refusé : {reason}.", f"Rejected: {reason}."), config.COL_DOWN)

    def _exec_pair(self):
        p = self.app.gs.player
        if not unlocks.unlocked(p, "leverage"):
            g = unlocks.effective_required_grade(p, "leverage")
            self._say(_L(f"Vente à découvert verrouillée (grade {config.GRADES[g]}).", f"Short selling locked (grade {config.GRADES[g]})."),
                      config.COL_DOWN)
            return
        ctx = self._ctx or {}
        qty = ctx.get("hedge_qty", 0)
        if qty < 1 or not self.pair_hedge:
            self._say(_L("Ratio trop faible : rien à shorter.", "Ratio too low: nothing to short."), config.COL_DOWN)
            return
        r = pf.short(p, self.market, self.pair_hedge, qty)
        if r.get("ok"):
            self._say(_L(f"Couverture posée : short {qty} × {self.pair_hedge} "
                         f"(ratio {ctx['hr']['ratio']:.2f}).",
                         f"Hedge set: short {qty} × {self.pair_hedge} "
                         f"(ratio {ctx['hr']['ratio']:.2f})."), config.COL_UP)
            self._cache_key = None
        else:
            self._say(_L(f"Short refusé : {r.get('reason', '?')}.", f"Short rejected: {r.get('reason', '?')}."), config.COL_DOWN)

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
        widgets.draw_text(surf, _L("COUVERTURE — PROTECTION DU PORTEFEUILLE", "HEDGE — PORTFOLIO PROTECTION"),
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        # tuiles d'exposition
        tiles = [
            (_L("EXPOSITION LONGUE", "LONG EXPOSURE"), widgets.format_money(ctx.get("long_value", 0.0), cur)),
            (_L(f"BÊTA vs {ctx.get('index', '—')}", f"BETA vs {ctx.get('index', '—')}"), f"{ctx.get('beta', 0.0):.2f}"),
            (_L("DÉJÀ COUVERT", "ALREADY HEDGED"), f"{ctx.get('coverage', 0.0) * 100:.0f}%"),
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
        for mode, lbl in (("put", _L("PUT INDICE (portefeuille)", "INDEX PUT (portfolio)")),
                          ("pair", _L("PAIRE (position)", "PAIR (position)"))):
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
        inner = widgets.draw_panel(surf, left, _L("Nouveau put protecteur", "New protective put"),
                                   config.COL_CYAN)
        y = inner.y + 2
        widgets.draw_text(surf, _L("Strike (% de l'indice) :", "Strike (% of index):"), (inner.x, y),
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
        widgets.draw_text(surf, _L("Maturité :", "Maturity:"), (inner.x, y), fonts.tiny(bold=True),
                          config.COL_TEXT_DIM)
        x = inner.x + 150
        self._years_rects = {}
        for i, yr in enumerate(H.MATURITY_CHOICES):
            lbl = (_L(f"{int(yr * 12)} mois", f"{int(yr * 12)}mo") if yr < 1
                   else _L(f"{yr:.0f} an", f"{yr:.0f}y"))
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
        widgets.draw_text(surf, _L("Taille (× notionnel bêta) :", "Size (× beta notional):"), (inner.x, y),
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
            widgets.draw_text(surf, _L(f"Indice {q['underlying']} : {q['spot']:,.0f} — "
                              f"strike {q['strike']:,.0f} · vol {q['sigma'] * 100:.0f}% "
                              f"· taux {q['rate'] * 100:.1f}%",
                              f"Index {q['underlying']}: {q['spot']:,.0f} — "
                              f"strike {q['strike']:,.0f} · vol {q['sigma'] * 100:.0f}% "
                              f"· rate {q['rate'] * 100:.1f}%"),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 20
            widgets.draw_text(surf, _L(f"Notionnel couvert : "
                              f"{widgets.format_money(ctx.get('notional', 0.0), cur)}",
                              f"Notional hedged: "
                              f"{widgets.format_money(ctx.get('notional', 0.0), cur)}"),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            y += 22
            widgets.draw_text(surf, _L(f"Prime à payer : "
                              f"{widgets.format_money(ctx.get('premium', 0.0), cur)} "
                              f"({q['premium_rate'] * 100:.2f}% du notionnel)",
                              f"Premium to pay: "
                              f"{widgets.format_money(ctx.get('premium', 0.0), cur)} "
                              f"({q['premium_rate'] * 100:.2f}% of notional)"),
                              (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            y += 22
            # LA pédagogie du hedge : la perte à -10 % AVANT / APRÈS le put
            # (Labo de crise sur une copie, en cache par pas + réglages)
            ba = self._hedge_before_after(ctx)
            if ba:
                widgets.draw_text(surf, widgets.fit_text(
                    _L(f"Si marché -10 % : {ba['before']:+,.0f} sans couverture "
                    f"-> {ba['after']:+,.0f} avec ce put",
                    f"If market -10%: {ba['before']:+,.0f} unhedged "
                    f"-> {ba['after']:+,.0f} with this put"), fonts.tiny(), inner.w),
                    (inner.x, y), fonts.tiny(), config.COL_WARN)
                y += 20
            else:
                y += 8
        self._buy_btn = pygame.Rect(inner.x, y, 190, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._buy_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._buy_btn, 1, border_radius=4)
        widgets.draw_text(surf, _L("SOUSCRIRE LE PUT", "BUY THE PUT"), self._buy_btn.center,
                          fonts.small(bold=True), config.COL_UP, align="center")
        hint = _L("Si l'indice finit sous le strike à l'échéance, le put paie la "
               "différence — la prime est le coût de l'assurance.",
               "If the index ends below the strike at expiry, the put pays the "
               "difference — the premium is the cost of the insurance.")
        hint_font = fonts.tiny()
        n_lines = len(widgets.wrap_text_lines(hint, hint_font, inner.w))
        hint_h = n_lines * (hint_font.get_height() + 4)
        widgets.draw_text_wrapped(surf, hint, (inner.x, inner.bottom - hint_h),
                                  hint_font, config.COL_TEXT_DIM, inner.w)
        # puts en cours
        rinner = widgets.draw_panel(surf, right, _L("Couvertures en cours", "Active hedges"),
                                    config.COL_AMBER)
        hedges = ctx.get("hedges", [])
        if not hedges:
            widgets.draw_text(surf, _L("Aucun put en cours.", "No active put."), (rinner.x, rinner.y + 4),
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
            widgets.draw_text(surf, _L(f"indice {hpos['perf']:+.1f}% depuis l'achat · "
                              f"échéance dans {hpos['steps_left']} pas · ",
                              f"index {hpos['perf']:+.1f}% since buy · "
                              f"expiry in {hpos['steps_left']} steps · ")
                              + (_L("DANS LA MONNAIE", "IN THE MONEY") if hpos["in_money"] else _L("hors monnaie", "out of the money")),
                              (rinner.x + 10, y + 17), fonts.tiny(), col)
            y += 40

    # ---------------------------------------------------------- mode pair
    def _draw_pair(self, surf, body, ctx, cur):
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left, _L("Position à couvrir", "Position to hedge"), config.COL_CYAN)
        held = ctx.get("held", [])
        self._pos_rects = {}
        if not held:
            widgets.draw_text(surf, _L("Aucune position longue à couvrir.", "No long position to hedge."),
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
        rinner = widgets.draw_panel(surf, right, _L("Instrument de couverture (short)", "Hedging instrument (short)"),
                                    config.COL_AMBER)
        cands = ctx.get("candidates", [])
        self._cand_rects = {}
        y = rinner.y + 2
        if not cands:
            widgets.draw_text(surf, _L("Sélectionnez une position à gauche.", "Select a position on the left."),
                              (rinner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        for tk, corr in cands:
            r = pygame.Rect(rinner.x - 4, y - 2, rinner.w + 8, 20)
            self._cand_rects[tk] = r
            sel = tk == self.pair_hedge
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, tk, (rinner.x, y), fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            widgets.draw_text(surf, _L(f"corr {corr:+.2f}", f"corr {corr:+.2f}"), (rinner.x + 90, y),
                              fonts.small(), config.COL_TEXT_DIM)
            y += 21
        hr = ctx.get("hr")
        if hr and self.pair_hedge:
            y += 8
            widgets.draw_text(surf, _L(f"Ratio min-variance h = {hr['ratio']:.2f} · "
                              f"R² = {hr['r2'] * 100:.0f}%",
                              f"Min-variance ratio h = {hr['ratio']:.2f} · "
                              f"R² = {hr['r2'] * 100:.0f}%"),
                              (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            y += 20
            widgets.draw_text(surf, _L(f"Vol résiduelle attendue : "
                              f"{hr['resid_vol_pct']:.0f}% de la vol d'origine",
                              f"Expected residual vol: "
                              f"{hr['resid_vol_pct']:.0f}% of original vol"),
                              (rinner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 22
            qty = ctx.get("hedge_qty", 0)
            widgets.draw_text(surf, _L(f"Ordre : SHORT {qty} × {self.pair_hedge} "
                              f"(≈ {widgets.format_money(qty * ctx.get('hedge_price', 0.0), cur)})",
                              f"Order: SHORT {qty} × {self.pair_hedge} "
                              f"(≈ {widgets.format_money(qty * ctx.get('hedge_price', 0.0), cur)})"),
                              (rinner.x, y), fonts.small(bold=True), config.COL_DOWN)
            y += 26
            self._short_btn = pygame.Rect(rinner.x, y, 190, 26)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._short_btn,
                             border_radius=4)
            pygame.draw.rect(surf, config.COL_DOWN, self._short_btn, 1, border_radius=4)
            widgets.draw_text(surf, _L("EXÉCUTER LE SHORT", "EXECUTE THE SHORT"), self._short_btn.center,
                              fonts.small(bold=True), config.COL_DOWN, align="center")
        else:
            self._short_btn = None
        pair_hint = _L("Plus la corrélation est forte, plus le short compense les "
                    "variations de la position couverte.",
                    "The stronger the correlation, the more the short offsets the "
                    "moves of the hedged position.")
        pair_font = fonts.tiny()
        pair_lines = len(widgets.wrap_text_lines(pair_hint, pair_font, rinner.w))
        pair_h = pair_lines * (pair_font.get_height() + 4)
        widgets.draw_text_wrapped(surf, pair_hint, (rinner.x, rinner.bottom - pair_h),
                                  pair_font, config.COL_TEXT_DIM, rinner.w)
