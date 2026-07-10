"""
app_valuation.py — Application « Valorisation » du bureau (NATIVE).

L'outillage de l'investisseur FONDAMENTAL (core/valuation.py), trois
onglets :

- DCF : flux projetés sur les états financiers simulés de la société,
  WACC et croissance terminale réglables (±), valeur intrinsèque par
  action vs le cours, verdict sous/surévaluée, et LA table de sensibilité
  WACC × g_terminal (une valorisation est une plage, pas un chiffre).
  Bouton TRADER pour agir sur l'écart.
- SML : la Security Market Line — nuage bêta × rendement de tout le
  roster, droite du CAPM tracée ; au-dessus = « bon marché » au sens du
  CAPM (alpha positif). Table des meilleurs alphas, cliquable.
- LBO : le pont d'IRR — curseurs (multiple d'entrée, levier, croissance
  EBITDA, multiple de sortie, durée) et la décomposition EXACTE de la
  création de valeur en DÉSENDETTEMENT / CROISSANCE / EXPANSION DE
  MULTIPLE, avec MOIC et IRR. Le schéma qu'on apprend en private equity.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import valuation as VAL
from ui import fonts, widgets

TABS = [("dcf", "DCF"), ("sml", "SML (CAPM)"), ("lbo", "PONT LBO")]
LBO_PARAMS = [
    ("entry_mult", "Multiple d'entrée", 4.0, 12.0, 0.5, "×"),
    ("debt_pct", "Levier (dette/EV)", 0.30, 0.80, 0.05, "%"),
    ("growth", "Croissance EBITDA", -0.05, 0.15, 0.01, "%"),
    ("exit_mult", "Multiple de sortie", 4.0, 12.0, 0.5, "×"),
    ("years", "Durée (années)", 3, 7, 1, "a"),
]


class ValuationApp(DesktopApp):
    title = "Valorisation"
    icon_kind = "research"
    default_size = (1080, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.tab = "dcf"
        self.ticker = self._default_ticker()
        self.wacc = VAL.DEFAULT_WACC
        self.g_term = VAL.DEFAULT_G_TERM
        self.lbo = {"entry_mult": 8.0, "debt_pct": 0.60, "growth": 0.05,
                    "exit_mult": 8.0, "years": 5}
        self._cache_key = None
        self._dcf = None
        self._sens = None
        self._sml = None
        self._bridge = None
        self._tab_rects = {}
        self._chip_rects = {}
        self._adj_rects = {}
        self._trade_btn = None
        self._sml_rows_rects = {}

    def _default_ticker(self):
        p = self.app.gs.player
        for tk, pos in p.portfolio.items():
            if pos["shares"] > 0 and tk in self.market.ticker_idx:
                return tk
        top = self.market.top_companies(n=1)
        return top[0]["ticker"] if top else ""

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        key = (self.market.step_count, self.tab, self.ticker,
               round(self.wacc, 4), round(self.g_term, 4),
               tuple(sorted(self.lbo.items())))
        if key == self._cache_key:
            return
        self._cache_key = key
        if self.tab == "dcf":
            self._dcf = VAL.dcf(self.market, self.ticker, self.wacc, self.g_term)
            self._sens = VAL.dcf_sensitivity(self.market, self.ticker)
        elif self.tab == "sml":
            self._sml = VAL.sml(self.market)
        else:
            self._bridge = VAL.lbo_bridge(
                100.0, self.lbo["entry_mult"], self.lbo["debt_pct"],
                self.lbo["growth"], self.lbo["exit_mult"], self.lbo["years"])

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
                return True
        for key, r in self._adj_rects.items():
            if r.collidepoint(pos):
                self._adjust(key)
                return True
        if self._trade_btn and self._trade_btn.collidepoint(pos):
            if self.desktop is not None and self.ticker:
                self.desktop.open_trading(self.ticker)
            return True
        for tk, r in self._sml_rows_rects.items():
            if r.collidepoint(pos):
                self.ticker = tk
                self.tab = "dcf"
                return True
        return False

    def _adjust(self, key):
        if key == "wacc+":
            self.wacc = min(0.15, round(self.wacc + 0.005, 4))
        elif key == "wacc-":
            self.wacc = max(0.04, round(self.wacc - 0.005, 4))
        elif key == "g+":
            self.g_term = min(self.wacc - 0.005, round(self.g_term + 0.005, 4))
        elif key == "g-":
            self.g_term = max(0.0, round(self.g_term - 0.005, 4))
        elif key.startswith("lbo:"):
            _p, name, sign = key.split(":")
            spec = next(s for s in LBO_PARAMS if s[0] == name)
            lo, hi, step = spec[2], spec[3], spec[4]
            v = self.lbo[name] + (step if sign == "+" else -step)
            self.lbo[name] = type(spec[2])(max(lo, min(hi, round(v, 4))))

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "VALORISATION — DCF · CAPM · LBO",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
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
        body = pygame.Rect(rect.x + pad, y + 28, rect.w - 2 * pad,
                           rect.bottom - pad - y - 28)
        if self.tab == "dcf":
            self._draw_dcf(surf, body)
        elif self.tab == "sml":
            self._draw_sml(surf, body)
        else:
            self._draw_lbo(surf, body)

    def _mini_btn(self, surf, key, x, y, sym):
        r = pygame.Rect(x, y, 18, 18)
        self._adj_rects[key] = r
        pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=3)
        pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=3)
        widgets.draw_text(surf, sym, r.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        return r.right

    # ------------------------------------------------------------------ DCF
    def _draw_dcf(self, surf, body):
        p = self.app.gs.player
        self._adj_rects = {}
        # chips tickers (détenues + top capis)
        chips = [tk for tk, pos in p.portfolio.items()
                 if pos["shares"] > 0 and tk in self.market.ticker_idx]
        for c in self.market.top_companies(n=8):
            if c["ticker"] not in chips:
                chips.append(c["ticker"])
        if self.ticker and self.ticker not in chips:
            chips.insert(0, self.ticker)
        x, y = body.x, body.y
        self._chip_rects = {}
        for tk in chips[:10]:
            w = fonts.tiny(bold=True).size(tk)[0] + 14
            if x + w > body.right - 220:
                break
            r = pygame.Rect(x, y, w, 20)
            self._chip_rects[tk] = r
            sel = tk == self.ticker
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, tk, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        # réglages WACC / g_terminal
        x += 12
        widgets.draw_text(surf, f"WACC {self.wacc * 100:.1f}%", (x, y + 3),
                          fonts.tiny(bold=True), config.COL_CYAN)
        x += fonts.tiny(bold=True).size(f"WACC {self.wacc * 100:.1f}%")[0] + 6
        x = self._mini_btn(surf, "wacc-", x, y, "−") + 3
        x = self._mini_btn(surf, "wacc+", x, y, "+") + 12
        widgets.draw_text(surf, f"g∞ {self.g_term * 100:.1f}%", (x, y + 3),
                          fonts.tiny(bold=True), config.COL_CYAN)
        x += fonts.tiny(bold=True).size(f"g∞ {self.g_term * 100:.1f}%")[0] + 6
        x = self._mini_btn(surf, "g-", x, y, "−") + 3
        self._mini_btn(surf, "g+", x, y, "+")
        top = y + 30
        d = self._dcf
        if d is None:
            widgets.draw_text(surf, "DCF impossible ici (EBIT négatif ou données "
                              "manquantes) — essayez une autre société.",
                              (body.x, top + 8), fonts.small(), config.COL_TEXT_DIM)
            self._trade_btn = None
            return
        cur = config.CONTINENTS[p.continent]["currency"]
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, top, col_w, body.bottom - top)
        right = pygame.Rect(left.right + 12, top, col_w, left.h)
        inner = widgets.draw_panel(surf, left, f"{d['name']} — valeur intrinsèque",
                                   config.COL_CYAN)
        yy = inner.y + 2
        upcol = config.COL_UP if d["upside"] >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{d['per_share']:,.2f} / action",
                          (inner.x, yy), fonts.title(bold=True), upcol)
        yy += 46
        verdict = ("SOUS-ÉVALUÉE" if d["upside"] > 0.10 else
                   "SURÉVALUÉE" if d["upside"] < -0.10 else "proche du cours")
        widgets.draw_text(surf, f"Cours {d['price']:,.2f} → potentiel "
                          f"{d['upside'] * 100:+.0f}% ({verdict})",
                          (inner.x, yy), fonts.small(bold=True), upcol)
        yy += 26
        rows = [
            (f"FCF année 0 (≈ NOPAT) : {widgets.format_money(d['fcf0'], cur)}",
             config.COL_TEXT),
            (f"Croissance explicite : {d['growth'] * 100:+.1f}%/an sur "
             f"{VAL.DCF_YEARS} ans", config.COL_TEXT_DIM),
            (f"VA flux explicites : {widgets.format_money(d['pv_explicit'], cur)}",
             config.COL_TEXT),
            (f"VA valeur terminale : {widgets.format_money(d['pv_terminal'], cur)} "
             f"({d['pv_terminal'] / d['ev'] * 100:.0f}% de l'EV !)",
             config.COL_AMBER),
            (f"EV {widgets.format_money(d['ev'], cur)} − dette nette "
             f"{widgets.format_money(d['net_debt'], cur)} = fonds propres "
             f"{widgets.format_money(d['equity'], cur)}", config.COL_TEXT),
        ]
        for txt, col in rows:
            widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.w),
                              (inner.x, yy), fonts.tiny(), col)
            yy += 17
        yy += 8
        self._trade_btn = pygame.Rect(inner.x, min(yy, inner.bottom - 28), 150, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._trade_btn, border_radius=4)
        pygame.draw.rect(surf, upcol, self._trade_btn, 1, border_radius=4)
        widgets.draw_text(surf, "TRADER →", self._trade_btn.center,
                          fonts.small(bold=True), upcol, align="center")
        widgets.draw_text(surf, "Hypothèses : capex ≈ dotations, ΔBFR négligé "
                          "(FCF ≈ NOPAT).", (inner.x, inner.bottom - 12),
                          fonts.tiny(), config.COL_TEXT_DIM)
        # table de sensibilité
        rinner = widgets.draw_panel(surf, right,
                                    "Sensibilité (valeur/action) — WACC × g∞",
                                    config.COL_AMBER)
        sens = self._sens
        cw = (rinner.w - 70) // len(sens["waccs"])
        for j, wacc in enumerate(sens["waccs"]):
            widgets.draw_text(surf, f"{wacc * 100:.0f}%",
                              (rinner.x + 70 + j * cw + cw // 2, rinner.y),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM,
                              align="center")
        vals = [v for row in sens["grid"] for v in row if v]
        vmin, vmax = (min(vals), max(vals)) if vals else (0, 1)
        rng = (vmax - vmin) or 1.0
        ch = min(44, (rinner.h - 40) // len(sens["g_terms"]))
        for i, g in enumerate(sens["g_terms"]):
            ry = rinner.y + 16 + i * ch
            widgets.draw_text(surf, f"g {g * 100:.0f}%", (rinner.x, ry + ch // 2 - 6),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM)
            for j, _w in enumerate(sens["waccs"]):
                v = sens["grid"][i][j]
                r0 = pygame.Rect(rinner.x + 70 + j * cw, ry, cw - 3, ch - 3)
                if v is None:
                    pygame.draw.rect(surf, config.COL_PANEL, r0, border_radius=3)
                    continue
                t = (v - vmin) / rng
                col = (int(40 + (1 - t) * 160), int(60 + t * 130), 70)
                pygame.draw.rect(surf, col, r0, border_radius=3)
                if d["price"] and abs(v / d["price"] - 1.0) < 0.05:
                    pygame.draw.rect(surf, config.COL_WHITE, r0, 1, border_radius=3)
                widgets.draw_text(surf, f"{v:,.0f}", r0.center, fonts.tiny(bold=True),
                                  config.COL_WHITE, align="center")
        sens_hint = ("Cadre blanc = cases compatibles avec le cours actuel "
                    "(±5 %) — ce que le marché « price ».")
        sens_font = fonts.tiny()
        sens_lines = len(widgets.wrap_text_lines(sens_hint, sens_font, rinner.w))
        sens_h = sens_lines * (sens_font.get_height() + 3)
        widgets.draw_text_wrapped(surf, sens_hint, (rinner.x, rinner.bottom - sens_h),
                                  sens_font, config.COL_TEXT_DIM, rinner.w, line_gap=3)

    # ------------------------------------------------------------------ SML
    def _draw_sml(self, surf, body):
        self._sml_rows_rects = {}
        s = self._sml
        if s is None:
            widgets.draw_text(surf, "Historique insuffisant.", (body.x, body.y + 8),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        col_w = int(body.w * 0.60)
        chart = pygame.Rect(body.x, body.y, col_w, body.h)
        table = pygame.Rect(chart.right + 12, body.y, body.w - col_w - 12, body.h)
        inner = widgets.draw_panel(surf, chart,
                                   "Security Market Line — rendement vs bêta",
                                   config.COL_CYAN)
        rows = s["rows"]
        betas = [r["beta"] for r in rows]
        rets = [r["ret"] for r in rows]
        b_lo, b_hi = min(betas + [0.0]), max(betas)
        r_lo, r_hi = min(rets), max(rets)
        sb = (b_hi - b_lo) or 1.0
        sr = (r_hi - r_lo) or 1.0
        plot = inner.inflate(-40, -30)
        plot.move_ip(14, 0)

        def px(b, r):
            return (plot.x + int((b - b_lo) / sb * plot.w),
                    plot.bottom - int((r - r_lo) / sr * plot.h))
        pygame.draw.line(surf, config.COL_BORDER, plot.bottomleft, plot.bottomright)
        pygame.draw.line(surf, config.COL_BORDER, plot.topleft, plot.bottomleft)
        # droite du CAPM entre b_lo et b_hi
        line0 = px(b_lo, s["rf"] + b_lo * (s["r_market"] - s["rf"]))
        line1 = px(b_hi, s["rf"] + b_hi * (s["r_market"] - s["rf"]))
        pygame.draw.aaline(surf, config.COL_AMBER, line0, line1)
        held = {tk for tk, pos in self.app.gs.player.portfolio.items()
                if pos["shares"] > 0}
        for r in rows:
            pt = px(r["beta"], r["ret"])
            col = (config.COL_UP if r["alpha"] > 0 else config.COL_DOWN)
            pygame.draw.circle(surf, col, pt, 3 if r["ticker"] in held else 2,
                               0 if r["ticker"] in held else 1)
        widgets.draw_text(surf, f"droite : r = rf {s['rf'] * 100:.0f}% + β × "
                          f"(marché {s['r_market'] * 100:.0f}% − rf) · "
                          "au-dessus = alpha CAPM positif · points pleins = détenues",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
        # table des meilleurs alphas
        tinner = widgets.draw_panel(surf, table, "Meilleurs alphas (clic → DCF)",
                                    config.COL_UP)
        yy = tinner.y + 2
        for r in rows[:14]:
            if yy > tinner.bottom - 16:
                break
            row_r = pygame.Rect(tinner.x - 4, yy - 2, tinner.w + 8, 18)
            self._sml_rows_rects[r["ticker"]] = row_r
            widgets.draw_text(surf, r["ticker"], (tinner.x, yy),
                              fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"β {r['beta']:.2f}",
                              (tinner.x + 66, yy), fonts.tiny(), config.COL_TEXT_DIM)
            acol = config.COL_UP if r["alpha"] > 0 else config.COL_DOWN
            widgets.draw_text(surf, f"α {r['alpha'] * 100:+.0f}%",
                              (tinner.x + 130, yy), fonts.tiny(bold=True), acol)
            yy += 19

    # ------------------------------------------------------------------ LBO
    def _draw_lbo(self, surf, body):
        self._adj_rects = {}
        b = self._bridge
        inner = widgets.draw_panel(surf, body,
                                   "Pont de création de valeur (EBITDA d'entrée "
                                   "normalisé à 100)", config.COL_AMBER)
        y = inner.y + 2
        for name, label, _lo, _hi, _step, unit in LBO_PARAMS:
            v = self.lbo[name]
            txt = (f"{label} : {v:.0%}" if unit == "%" else
                   f"{label} : {v:g}{'×' if unit == '×' else ' ans' if unit == 'a' else ''}")
            widgets.draw_text(surf, txt, (inner.x, y + 2), fonts.tiny(bold=True),
                              config.COL_TEXT)
            x = inner.x + 230
            x = self._mini_btn(surf, f"lbo:{name}:-", x, y, "−") + 3
            self._mini_btn(surf, f"lbo:{name}:+", x, y, "+")
            y += 24
        if b is None:
            return
        y += 6
        icol = config.COL_UP if b["irr"] >= 0.15 else (
            config.COL_AMBER if b["irr"] >= 0 else config.COL_DOWN)
        widgets.draw_text(surf, f"MOIC {b['moic']:.2f}× · IRR {b['irr'] * 100:+.1f}%/an",
                          (inner.x, y), fonts.title(bold=True), icol)
        y += 34
        # pont en barres : equity entrée → +3 effets → equity sortie
        effects = [
            ("Fonds propres entrée", b["equity0"], config.COL_TEXT_DIM),
            ("+ Croissance EBITDA", b["growth_effect"], config.COL_UP),
            ("+ Expansion multiple", b["multiple_effect"], config.COL_CYAN),
            ("+ Désendettement", b["paydown_effect"], config.COL_AMBER),
            ("= Fonds propres sortie", b["equity_end"], config.COL_WHITE),
        ]
        vmax = max(abs(v) for _l, v, _c in effects) or 1.0
        bar_w = inner.w - 330
        for label, v, col in effects:
            widgets.draw_text(surf, label, (inner.x, y), fonts.small(bold=True), col)
            bx = inner.x + 210
            w = int(abs(v) / vmax * bar_w)
            pygame.draw.rect(surf, col, pygame.Rect(bx, y + 2, max(2, w), 12),
                             border_radius=2)
            widgets.draw_text(surf, f"{v:+,.0f}" if "=" not in label and
                              "entrée" not in label else f"{v:,.0f}",
                              (bx + w + 8, y), fonts.tiny(bold=True), col)
            y += 24
        y += 4
        widgets.draw_text(surf, f"Dette : {b['debt0']:,.0f} → {b['debt_end']:,.0f} "
                          f"(cash sweep) · EV sortie {b['exit_ev']:,.0f}",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "Invariant : croissance + multiple + désendettement "
                          "= gain de fonds propres, exactement.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
