"""
app_greeks.py — Application « Desk Options » du bureau (NATIVE).

Trois onglets de vraie finance d'options, sur le desk RÉEL du jeu
(core/options.py — les positions achetées ici vivent dans player.options
et sont dénouées à l'échéance par le moteur) :

- STRATÉGIE : construit un paquet multi-jambes (call/put secs, straddle,
  strangle, put protecteur — core/option_strategies.py), affiche le
  PROFIL DE P&L À L'ÉCHÉANCE (courbe, points morts, perte max), les
  grecques du paquet avec leur lecture (Δ exposition directionnelle,
  Γ accélération, ν sensibilité vol, Θ coût du temps), et EXÉCUTE toutes
  les jambes d'un coup (prime totale vérifiée avant le premier ordre).
- MODÈLES : price LA MÊME option sous 5 modèles (core/option_pricing.py :
  Black-Scholes-Merton, binomial CRR européen ET américain — la prime
  d'exercice anticipé, Monte-Carlo antithétique avec erreur-type, Merton
  à sauts — le smile) : on VOIT où les hypothèses divergent.
- BOOK : grecques agrégées des options en portefeuille, réévaluées au
  marché du jour (delta cash, gamma cash, vega, theta/jour) — la vraie
  feuille de risque d'un desk.

Verrou de grade : le déblocage « options » (comme la commande OPTIONS).
"""
import pygame

from apps.base import DesktopApp
from core import config, unlocks
from core import option_pricing as OP
from core import option_strategies as OS
from core import options as opt
from ui import fonts, widgets

TABS = [("strat", "STRATÉGIE"), ("models", "MODÈLES"), ("book", "BOOK")]
MATURITIES = opt.MATURITY_CHOICES          # 0.25 / 0.5 / 1.0
GREEK_HELP = [
    ("Δ delta", "exposition directionnelle (équivalent actions)"),
    ("Γ gamma", "variation du delta pour 1 % de spot"),
    ("ν vega", "P&L pour +1 point de volatilité"),
    ("Θ theta", "P&L par JOUR qui passe (le coût du temps)"),
]


class GreeksApp(DesktopApp):
    title = "Desk Options"
    icon_kind = "greeks"
    default_size = (1080, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.tab = "strat"
        self.ticker = self._default_ticker()
        self.strategy = "call"
        self.years_idx = 0
        self.contracts = 10
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self._cache_key = None
        self._q = None
        self._models = None
        self._book = None
        self._tab_rects = {}
        self._chip_rects = {}
        self._strat_rects = {}
        self._years_rects = {}
        self._qty_minus = None
        self._qty_plus = None
        self._exec_btn = None

    def _default_ticker(self):
        p = self.app.gs.player
        for tk, pos in p.portfolio.items():
            if pos["shares"] > 0 and tk in self.market.ticker_idx:
                return tk
        top = self.market.top_companies(n=1)
        return top[0]["ticker"] if top else ""

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        p = self.app.gs.player
        key = (self.market.step_count, self.tab, self.ticker, self.strategy,
               self.years_idx, self.contracts,
               len(getattr(p, "options", []) or []))
        if key == self._cache_key:
            return
        self._cache_key = key
        years = MATURITIES[self.years_idx]
        self._q = OS.quote_strategy(p, self.market, self.ticker,
                                    self.strategy, years, self.contracts)
        if self.tab == "models" and self._q:
            leg = self._q["legs"][0]
            self._models = OP.compare_models(
                leg["spot"], leg["strike"], years, leg["rate"], leg["sigma"],
                option=leg["option_type"])
        if self.tab == "book":
            self._book = OS.book_greeks(p, self.market)

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for tab, r in self._tab_rects.items():
            if r.collidepoint(pos):
                self.tab = tab
                return True
        for tk, r in self._chip_rects.items():
            if r.collidepoint(pos):
                self.ticker = tk
                self.msg = ""
                return True
        for s, r in self._strat_rects.items():
            if r.collidepoint(pos):
                self.strategy = s
                return True
        for i, r in self._years_rects.items():
            if r.collidepoint(pos):
                self.years_idx = i
                return True
        if self._qty_minus and self._qty_minus.collidepoint(pos):
            self.contracts = max(1, self.contracts - 5)
            return True
        if self._qty_plus and self._qty_plus.collidepoint(pos):
            self.contracts = min(10_000, self.contracts + 5)
            return True
        if self._exec_btn and self._exec_btn.collidepoint(pos):
            self._execute()
            return True
        return False

    def _execute(self):
        p = self.app.gs.player
        if not unlocks.unlocked(p, "options"):
            g = unlocks.effective_required_grade(p, "options")
            self._say(f"Options verrouillées (débloquées au grade {config.GRADES[g]}).",
                      config.COL_DOWN)
            return
        r = OS.execute_strategy(p, self.market, self.ticker, self.strategy,
                                MATURITIES[self.years_idx], self.contracts)
        if r.get("ok"):
            cur = config.CONTINENTS[p.continent]["currency"]
            self._say(f"{r['label']} exécuté — prime "
                      f"{widgets.format_money(r['premium'], cur)}, "
                      f"{len(r['positions'])} jambe(s) au book.", config.COL_UP)
            self._cache_key = None
        else:
            reason = {"cash": "trésorerie insuffisante pour la prime totale",
                      "needs_stock": f"il faut détenir ≥ {self.contracts} actions "
                                     f"{self.ticker} (put protecteur)",
                      "quote": "cotation impossible"}.get(r.get("reason"),
                                                          r.get("reason", "?"))
            self._say(f"Refusé : {reason}.", config.COL_DOWN)

    def _say(self, text, col):
        self.msg, self.msg_col = text, col

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "DESK OPTIONS — STRATÉGIES · MODÈLES · GRECQUES",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        # onglets
        x, y = rect.x + pad, rect.y + 32
        self._tab_rects = {}
        for tab, lbl in TABS:
            w = fonts.tiny(bold=True).size(lbl)[0] + 18
            r = pygame.Rect(x, y, w, 22)
            self._tab_rects[tab] = r
            sel = tab == self.tab
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 8
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(),
                                                     rect.right - pad - x - 6),
                              (x + 6, y + 5), fonts.tiny(), self.msg_col)
        # rangée sélection commune (ticker / stratégie / maturité / quantité)
        y += 28
        y = self._draw_controls(surf, rect, pad, y)
        body = pygame.Rect(rect.x + pad, y + 6, rect.w - 2 * pad,
                           rect.bottom - pad - y - 6)
        if self.tab == "strat":
            self._draw_strat(surf, body)
        elif self.tab == "models":
            self._draw_models(surf, body)
        else:
            self._draw_book(surf, body)

    def _chip_row(self, surf, items, current, x, y, x_max, accent):
        rects = {}
        for key, lbl in items:
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            if x + w > x_max:
                break
            r = pygame.Rect(x, y, w, 20)
            rects[key] = r
            sel = key == current
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              accent if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        return rects, x

    def _draw_controls(self, surf, rect, pad, y):
        p = self.app.gs.player
        chips = [tk for tk, pos in p.portfolio.items()
                 if pos["shares"] > 0 and tk in self.market.ticker_idx]
        for c in self.market.top_companies(n=6):
            if c["ticker"] not in chips:
                chips.append(c["ticker"])
        if self.ticker and self.ticker not in chips:
            chips.insert(0, self.ticker)
        self._chip_rects, _x = self._chip_row(
            surf, [(tk, tk) for tk in chips[:8]], self.ticker,
            rect.x + pad, y, rect.right - pad, config.COL_AMBER)
        y += 24
        self._strat_rects, x = self._chip_row(
            surf, [(s, OS.STRATEGIES[s]["label"]) for s in OS.STRATEGY_ORDER],
            self.strategy, rect.x + pad, y, rect.right - pad - 230, config.COL_CYAN)
        labels = {0.25: "3 mois", 0.5: "6 mois", 1.0: "1 an"}
        self._years_rects, x = self._chip_row(
            surf, [(i, labels[m]) for i, m in enumerate(MATURITIES)],
            self.years_idx, x + 10, y, rect.right - pad - 90, config.COL_UP)
        # quantité
        self._qty_minus = pygame.Rect(rect.right - pad - 88, y, 20, 20)
        self._qty_plus = pygame.Rect(rect.right - pad - 20, y, 20, 20)
        for r, sym in ((self._qty_minus, "−"), (self._qty_plus, "+")):
            pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, sym, r.center, fonts.small(bold=True),
                              config.COL_TEXT, align="center")
        widgets.draw_text(surf, f"{self.contracts}",
                          (self._qty_minus.right + 24, y + 3),
                          fonts.small(bold=True), config.COL_TEXT, align="center")
        return y + 24

    # ------------------------------------------------------- onglet STRAT
    def _draw_strat(self, surf, body):
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        if self._q is None:
            widgets.draw_text(surf, "Cotation indisponible pour cette sélection.",
                              (body.x, body.y + 8), fonts.small(), config.COL_TEXT_DIM)
            self._exec_btn = None
            return
        q = self._q
        col_w = int(body.w * 0.58)
        chart = pygame.Rect(body.x, body.y, col_w, body.h)
        panel = pygame.Rect(chart.right + 12, body.y, body.w - col_w - 12, body.h)
        self._draw_payoff(surf, chart, q, cur)
        inner = widgets.draw_panel(surf, panel, q["label"], config.COL_AMBER)
        y = inner.y + 2
        widgets.draw_text(surf, widgets.fit_text(q["view"], fonts.tiny(), inner.w),
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 20
        for leg in q["legs"]:
            widgets.draw_text(surf, f"{leg['qty']:.0f} × {leg['option_type'].upper()} "
                              f"strike {leg['strike']:,.2f} "
                              f"(prime {leg['premium']:,.2f}/u)",
                              (inner.x, y), fonts.small(), config.COL_TEXT)
            y += 18
        if q["needs_stock"]:
            widgets.draw_text(surf, f"+ vos {q['contracts']} actions {q['ticker']} détenues",
                              (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
            y += 18
        y += 4
        widgets.draw_text(surf, f"PRIME TOTALE : "
                          f"{widgets.format_money(q['premium'], cur)}",
                          (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
        y += 22
        be = " · ".join(f"{b:,.1f}" for b in q["breakevens"]) or "—"
        widgets.draw_text(surf, f"Points morts : {be}", (inner.x, y),
                          fonts.tiny(), config.COL_TEXT)
        y += 16
        widgets.draw_text(surf, f"Perte max : {widgets.format_money(q['max_loss'], cur)}",
                          (inner.x, y), fonts.tiny(), config.COL_DOWN)
        y += 22
        gvals = [q["greeks"]["delta"], q["greeks"]["gamma"],
                 q["greeks"]["vega"], q["greeks"]["theta"]]
        for (lbl, help_txt), v in zip(GREEK_HELP, gvals):
            widgets.draw_text(surf, f"{lbl} {v:+.2f}", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_CYAN)
            widgets.draw_text(surf, widgets.fit_text(help_txt, fonts.tiny(),
                                                     inner.w - 110),
                              (inner.x + 106, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 15
        y += 8
        self._exec_btn = pygame.Rect(inner.x, min(y, inner.bottom - 30), 210, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._exec_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._exec_btn, 1, border_radius=4)
        widgets.draw_text(surf, "EXÉCUTER LE PAQUET", self._exec_btn.center,
                          fonts.small(bold=True), config.COL_UP, align="center")

    def _draw_payoff(self, surf, rect, q, cur):
        inner = widgets.draw_panel(surf, rect, "P&L à l'échéance vs cours final",
                                   config.COL_UP)
        spots, pnl = q["spots"], q["pnl"]
        lo, hi = float(pnl.min()), float(pnl.max())
        if hi <= lo:
            hi = lo + 1.0
        plot = inner.inflate(-14, -22)

        def px(i):
            return plot.x + int(i / (len(spots) - 1) * plot.w)

        def py(v):
            return plot.bottom - int((v - lo) / (hi - lo) * plot.h)
        zero_y = py(0.0)
        pygame.draw.line(surf, config.COL_BORDER, (plot.x, zero_y),
                         (plot.right, zero_y))
        # cours actuel (verticale)
        sx = plot.x + int((q["spot"] - spots[0]) / (spots[-1] - spots[0]) * plot.w)
        for y0 in range(plot.y, plot.bottom, 8):
            pygame.draw.line(surf, config.COL_TEXT_DIM, (sx, y0),
                             (sx, min(y0 + 4, plot.bottom)))
        widgets.draw_text(surf, f"spot {q['spot']:,.1f}", (sx + 4, plot.y),
                          fonts.tiny(), config.COL_TEXT_DIM)
        pts = [(px(i), py(float(v))) for i, v in enumerate(pnl)]
        pygame.draw.aalines(surf, config.COL_UP, False, pts)
        for b in q["breakevens"]:
            bx = plot.x + int((b - spots[0]) / (spots[-1] - spots[0]) * plot.w)
            pygame.draw.circle(surf, config.COL_AMBER, (bx, zero_y), 4)
        widgets.draw_text(surf, f"grille {spots[0]:,.0f} → {spots[-1]:,.0f} · "
                          "points ambre = points morts",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    # ----------------------------------------------------- onglet MODÈLES
    def _draw_models(self, surf, body):
        if self._q is None or self._models is None:
            widgets.draw_text(surf, "Cotation indisponible.", (body.x, body.y + 8),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        leg = self._q["legs"][0]
        inner = widgets.draw_panel(
            surf, body,
            f"La même option ({leg['option_type'].upper()} {self.ticker} "
            f"strike {leg['strike']:,.1f}) sous 5 modèles", config.COL_CYAN)
        widgets.draw_text(surf, "Un seul contrat, mêmes entrées (S, K, T, r, σ) — "
                          "seules les HYPOTHÈSES changent.",
                          (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        y = inner.y + 22
        prices = [r["price"] for r in self._models["rows"]]
        pmax = max(prices) or 1.0
        bar_w = min(260, inner.w - 420)
        for row in self._models["rows"]:
            widgets.draw_text(surf, row["label"], (inner.x, y),
                              fonts.small(bold=True), config.COL_TEXT)
            bx = inner.x + 230
            pygame.draw.rect(surf, config.COL_PANEL,
                             pygame.Rect(bx, y + 2, bar_w, 12), border_radius=2)
            pygame.draw.rect(surf, config.COL_CYAN,
                             pygame.Rect(bx, y + 2,
                                         int(bar_w * row["price"] / pmax), 12),
                             border_radius=2)
            widgets.draw_text(surf, f"{row['price']:,.2f}",
                              (bx + bar_w + 10, y), fonts.small(bold=True),
                              config.COL_AMBER)
            widgets.draw_text(surf, widgets.fit_text(row["note"], fonts.tiny(),
                                                     inner.right - bx - bar_w - 90),
                              (bx + bar_w + 80, y + 2), fonts.tiny(),
                              config.COL_TEXT_DIM)
            y += 30
        y += 8
        notes = [
            "· Binomial ≈ BS : l'arbre CRR converge vers la formule fermée (européen).",
            "· Américain ≥ européen : l'écart est la prime d'exercice anticipé "
            "(≈ 0 pour un call sans dividende — résultat classique).",
            "· Monte-Carlo : mêmes hypothèses que BS, mais estimation ± erreur-type.",
            "· Merton à sauts : un marché qui peut SAUTER (crises du jeu) vaut plus "
            "cher sur les ailes — c'est l'origine du smile de volatilité.",
        ]
        for n in notes:
            if y > inner.bottom - 14:
                break
            widgets.draw_text(surf, widgets.fit_text(n, fonts.tiny(), inner.w),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 15

    # -------------------------------------------------------- onglet BOOK
    def _draw_book(self, surf, body):
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        inner = widgets.draw_panel(surf, body, "Grecques agrégées du book d'options",
                                   config.COL_AMBER)
        book = self._book or {"rows": [], "totals": {}}
        if not book["rows"]:
            widgets.draw_text(surf, "Aucune option en portefeuille — construisez un "
                              "paquet dans l'onglet STRATÉGIE.",
                              (inner.x, inner.y + 6), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        t = book["totals"]
        tiles = [
            ("Δ CASH", widgets.format_money(t["delta_cash"], cur),
             "exposition action équivalente"),
            ("Γ CASH (1 %)", widgets.format_money(t["gamma_cash"], cur),
             "variation du Δ pour 1 % de spot"),
            ("ν VEGA (+1 pt)", widgets.format_money(t["vega"], cur),
             "P&L pour +1 point de vol"),
            ("Θ / JOUR", widgets.format_money(t["theta_day"], cur),
             "le temps qui passe"),
            ("VALEUR", widgets.format_money(t["value"], cur), "mark-to-model"),
        ]
        tx = inner.x
        for lbl, val, sub in tiles:
            tw = max(150, fonts.small(bold=True).size(val)[0] + 20)
            if tx + tw > inner.right:
                break
            tr = pygame.Rect(tx, inner.y, tw, 52)
            pygame.draw.rect(surf, config.COL_PANEL, tr, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, tr, 1, border_radius=4)
            widgets.draw_text(surf, lbl, (tr.x + 8, tr.y + 4), fonts.tiny(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (tr.x + 8, tr.y + 18),
                              fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, widgets.fit_text(sub, fonts.tiny(), tw - 14),
                              (tr.x + 8, tr.y + 36), fonts.tiny(), config.COL_TEXT_DIM)
            tx += tw + 8
        y = inner.y + 62
        cols = [("POSITION", 0), ("ÉCH. (pas)", int(inner.w * 0.34)),
                ("VALEUR", int(inner.w * 0.47)), ("Δ", int(inner.w * 0.62)),
                ("Γ", int(inner.w * 0.72)), ("ν", int(inner.w * 0.82)),
                ("Θ", int(inner.w * 0.92))]
        for lbl, dx in cols:
            widgets.draw_text(surf, lbl, (inner.x + dx, y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        y += 16
        for row in book["rows"]:
            if y > inner.bottom - 14:
                break
            widgets.draw_text(surf, f"{row['contracts']:.0f} {row['type'].upper()} "
                              f"{row['ticker']} @{row['strike']:,.0f}",
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{row['steps_left']}",
                              (inner.x + cols[1][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, widgets.format_money(row["value"], cur),
                              (inner.x + cols[2][1], y), fonts.small(),
                              config.COL_TEXT)
            for (lbl, dx), g in zip(cols[3:], ("delta", "gamma", "vega", "theta")):
                widgets.draw_text(surf, f"{row[g]:+.2f}", (inner.x + dx, y),
                                  fonts.small(), config.COL_CYAN)
            y += 18
