"""
app_vollab.py — Application « Labo de vol » du bureau (NATIVE).

Économétrie appliquée, deux onglets :

- GARCH : estimation d'un GARCH(1,1) sur un titre (core/garch.py — grille
  de vraisemblance, variance ciblée) : α (réaction), β (mémoire),
  persistance des grappes de vol, prévision de vol à 12 pas CONVERGENTE
  vers le long terme — comparée à la vol que PRICE le desk d'options :
  verdict « vol chère / bon marché » qui alimente les straddles.

- RÉGIMES : le moteur du jeu a de vrais régimes cachés — l'onglet fait ce
  que ferait un quant : un filtre bayésien à 2 états (CALME/STRESS) sur
  les seuls rendements observables de l'indice (core/regime_inference.py),
  la bande P(stress) dans le temps, et la VÉRITÉ du moteur à côté pour
  juger le filtre.
"""
import pygame

from apps.base import DesktopApp
from core import config, i18n
from core import garch as G
from core import regime_inference as RI
from ui import fonts, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


TABS = [("garch", ("GARCH (prévision de vol)", "GARCH (vol forecast)")),
        ("regimes", ("RÉGIMES (inférence)", "REGIMES (inference)"))]


class VolLabApp(DesktopApp):
    title = "Labo de vol"
    icon_kind = "quant"
    default_size = (1040, 620)
    min_size = (800, 480)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.tab = "garch"
        self.ticker = self._default_ticker()
        self._cache_key = None
        self._garch = None
        self._regime = None
        self._tab_rects = {}
        self._chip_rects = {}
        self._strat_btn = None

    def _default_ticker(self):
        p = self.app.gs.player
        for tk, pos in p.portfolio.items():
            if pos["shares"] > 0 and tk in self.market.ticker_idx:
                return tk
        top = self.market.top_companies(n=1)
        return top[0]["ticker"] if top else ""

    def _ensure_computed(self):
        key = (self.market.step_count, self.tab, self.ticker)
        if key == self._cache_key:
            return
        self._cache_key = key
        if self.tab == "garch":
            self._garch = G.analyze(self.market, self.ticker)
        else:
            self._regime = RI.infer(self.market)

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
        if self._strat_btn and self._strat_btn.collidepoint(pos):
            if self.desktop is not None:
                self.desktop._open_scene_window("greeks")
            return True
        return False

    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, _L("LABO DE VOL — GRAPPES, PRÉVISION, RÉGIMES", "VOL LAB — CLUSTERS, FORECAST, REGIMES"),
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        x, y = rect.x + pad, rect.y + 32
        self._tab_rects = {}
        for tab, lblpair in TABS:
            lbl = _L(*lblpair)
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
        if self.tab == "garch":
            self._draw_garch(surf, body)
        else:
            self._draw_regimes(surf, body)

    # ---------------------------------------------------------------- GARCH
    def _draw_garch(self, surf, body):
        p = self.app.gs.player
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
            if x + w > body.right:
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
        top = y + 28
        g = self._garch
        if g is None:
            widgets.draw_text(surf, _L("Historique insuffisant pour estimer un GARCH.", "Insufficient history to estimate a GARCH."),
                              (body.x, top + 8), fonts.small(), config.COL_TEXT_DIM)
            self._strat_btn = None
            return
        m = g["model"]
        inner = widgets.draw_panel(
            surf, pygame.Rect(body.x, top, body.w, body.bottom - top),
            f"GARCH(1,1) — {self.ticker}", config.COL_CYAN)
        yy = inner.y + 2
        widgets.draw_text(surf, _L(f"σ²_t = ω + α·r²(t−1) + β·σ²(t−1) — "
                          f"α = {m['alpha']:.2f} (réaction) · β = {m['beta']:.2f} "
                          f"(mémoire) · persistance α+β = {m['persistence']:.2f}",
                          f"σ²_t = ω + α·r²(t−1) + β·σ²(t−1) — "
                          f"α = {m['alpha']:.2f} (reaction) · β = {m['beta']:.2f} "
                          f"(memory) · persistence α+β = {m['persistence']:.2f}"),
                          (inner.x, yy), fonts.small(), config.COL_TEXT)
        yy += 22
        widgets.draw_text(surf, _L(f"Vol instantanée {g['vol_now_ann'] * 100:.0f}% → "
                          f"prévision 12 pas {g['vol_forecast_ann'] * 100:.0f}% → "
                          f"long terme {g['vol_lr_ann'] * 100:.0f}% · le desk price "
                          f"{g['vol_desk_ann'] * 100:.0f}%",
                          f"Instantaneous vol {g['vol_now_ann'] * 100:.0f}% → "
                          f"12-step forecast {g['vol_forecast_ann'] * 100:.0f}% → "
                          f"long term {g['vol_lr_ann'] * 100:.0f}% · the desk prices "
                          f"{g['vol_desk_ann'] * 100:.0f}%"),
                          (inner.x, yy), fonts.small(bold=True), config.COL_AMBER)
        yy += 24
        vcol = (config.COL_UP if g["edge"] > 0.03
                else config.COL_DOWN if g["edge"] < -0.03 else config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.fit_text(g["verdict"], fonts.small(bold=True),
                                                 inner.w),
                          (inner.x, yy), fonts.small(bold=True), vcol)
        yy += 26
        # courbe de prévision convergente
        curve = g["forecast_curve"]
        chart = pygame.Rect(inner.x, yy, inner.w - 8,
                            max(60, inner.bottom - yy - 44))
        pygame.draw.rect(surf, config.COL_PANEL, chart, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, chart, 1, border_radius=4)
        vols = [v for _h, v in curve] + [g["vol_lr_ann"], g["vol_desk_ann"]]
        lo, hi = min(vols) * 0.95, max(vols) * 1.05
        rng = (hi - lo) or 1.0

        def py(v):
            return chart.bottom - 12 - int((v - lo) / rng * (chart.h - 24))
        for ref, col, lbl in ((g["vol_lr_ann"], config.COL_TEXT_DIM, _L("long terme", "long term")),
                              (g["vol_desk_ann"], config.COL_AMBER, _L("desk", "desk"))):
            yv = py(ref)
            for x0 in range(chart.x + 8, chart.right - 8, 8):
                pygame.draw.line(surf, col, (x0, yv), (min(x0 + 4, chart.right - 8), yv))
            widgets.draw_text(surf, lbl, (chart.right - 70, yv - 12), fonts.tiny(), col)
        pts = [(chart.x + 12 + int(i / (len(curve) - 1) * (chart.w - 26)), py(v))
               for i, (_h, v) in enumerate(curve)]
        pygame.draw.aalines(surf, config.COL_CYAN, False, pts)
        for pt in pts:
            pygame.draw.circle(surf, config.COL_WHITE, pt, 2)
        widgets.draw_text(surf, _L("Prévision σ (annualisée) sur 12 pas — elle "
                          "CONVERGE vers le long terme à vitesse (α+β)^h.",
                          "σ forecast (annualized) over 12 steps — it "
                          "CONVERGES to the long term at rate (α+β)^h."),
                          (chart.x + 8, chart.y + 4), fonts.tiny(),
                          config.COL_TEXT_DIM)
        self._strat_btn = pygame.Rect(inner.x, inner.bottom - 32, 190, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._strat_btn, border_radius=4)
        pygame.draw.rect(surf, vcol, self._strat_btn, 1, border_radius=4)
        widgets.draw_text(surf, _L("→ DESK OPTIONS", "→ OPTIONS DESK"), self._strat_btn.center,
                          fonts.small(bold=True), vcol, align="center")

    # -------------------------------------------------------------- RÉGIMES
    def _draw_regimes(self, surf, body):
        r = self._regime
        inner = widgets.draw_panel(surf, body,
                                   _L("Filtre bayésien 2 états sur l'indice", "2-state Bayesian filter on the index"),
                                   config.COL_CYAN)
        if r is None:
            widgets.draw_text(surf, _L("Historique insuffisant.", "Insufficient history."), (inner.x, inner.y + 6),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        y = inner.y + 2
        icol = config.COL_DOWN if r["inferred"] == "STRESS" else config.COL_UP
        widgets.draw_text(surf, _L(f"Inféré depuis les prix : {r['inferred']} "
                          f"(P(stress) = {r['p_now'] * 100:.0f}%)",
                          f"Inferred from prices: {r['inferred']} "
                          f"(P(stress) = {r['p_now'] * 100:.0f}%)"),
                          (inner.x, y), fonts.small(bold=True), icol)
        y += 20
        tcol = config.COL_DOWN if r["truth_is_stress"] else config.COL_UP
        widgets.draw_text(surf, _L(f"Vérité du moteur : {r['truth']} — le filtre ", f"Engine truth: {r['truth']} — the filter ")
                          + (_L("a RAISON ✓", "is RIGHT ✓") if r["agreement"] else _L("se trompe ✗", "is wrong ✗")),
                          (inner.x, y), fonts.small(), tcol)
        y += 26
        probs = r["probs"]
        chart = pygame.Rect(inner.x, y, inner.w - 8, inner.bottom - y - 20)
        pygame.draw.rect(surf, config.COL_PANEL, chart, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, chart, 1, border_radius=4)
        thr_y = chart.bottom - 8 - int(RI.STRESS_THRESHOLD * (chart.h - 16))
        for x0 in range(chart.x + 8, chart.right - 8, 8):
            pygame.draw.line(surf, config.COL_AMBER, (x0, thr_y),
                             (min(x0 + 4, chart.right - 8), thr_y))
        n = len(probs)
        for i, pr in enumerate(probs):
            x0 = chart.x + 8 + int(i / max(1, n - 1) * (chart.w - 18))
            h = int(pr * (chart.h - 16))
            col = config.COL_DOWN if pr >= RI.STRESS_THRESHOLD else config.COL_CYAN
            pygame.draw.line(surf, col, (x0, chart.bottom - 8),
                             (x0, chart.bottom - 8 - h))
        widgets.draw_text(surf, _L("P(stress | rendements observés) dans le temps — "
                          "un régime, ça COLLE (transition 0,95), un mauvais jour "
                          "isolé ne suffit pas.",
                          "P(stress | observed returns) over time — "
                          "a regime STICKS (transition 0.95), a single bad "
                          "day is not enough."), (chart.x + 8, chart.y + 4),
                          fonts.tiny(), config.COL_TEXT_DIM)
