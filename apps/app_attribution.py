"""
app_attribution.py — Application « Attribution (Brinson) » du bureau.

« Suis-je bon ou chanceux ? » — deux onglets sur core/brinson.py :

- BRINSON : l'écart de performance vs le marché entier (pondéré capi),
  décomposé par secteur en effet d'ALLOCATION (surpondérer les bons
  secteurs) et effet de SÉLECTION (choisir les bons titres dedans), avec
  l'invariant affiché : allocation + sélection + interaction = écart total.
- FACTEURS : régression des rendements du portefeuille sur les facteurs
  observables du marché (monde / secteurs / régions) — bêtas, ALPHA
  annualisé (ce qui reste une fois les paris factoriels retirés) et R²
  (un « stock picker » à R² 95 % ne fait que des paris sectoriels).

Recalcul automatique à chaque pas de marché ; fenêtres 3M/1A/3A.
"""
import pygame

from apps.base import DesktopApp
from core import brinson as BR
from core import config
from core import quant_tools as QT
from ui import fonts, widgets

PERIODS = ["3M", "1A", "3A"]
TABS = [("brinson", "BRINSON"), ("factors", "FACTEURS")]


class AttributionApp(DesktopApp):
    title = "Attribution (Brinson)"
    icon_kind = "graph"
    default_size = (1040, 620)
    min_size = (780, 480)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.tab = "brinson"
        self.period = "1A"
        self._cache_key = None
        self._br = None
        self._fr = None
        self._tab_rects = {}
        self._period_rects = {}

    def _ensure_computed(self):
        p = self.app.gs.player
        key = (self.market.step_count, self.period, len(p.portfolio))
        if key == self._cache_key:
            return
        self._cache_key = key
        lookback = QT.PERIOD_STEPS[self.period]
        self._br = BR.brinson(p, self.market, lookback)
        self._fr = BR.factor_regression(p, self.market, lookback)

    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        for tab, r in self._tab_rects.items():
            if r.collidepoint(event.pos):
                self.tab = tab
                return True
        for period, r in self._period_rects.items():
            if r.collidepoint(event.pos):
                self.period = period
                return True
        return False

    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "ATTRIBUTION DE PERFORMANCE — BON OU CHANCEUX ?",
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
        x += 8
        self._period_rects = {}
        for period in PERIODS:
            w = fonts.tiny(bold=True).size(period)[0] + 14
            r = pygame.Rect(x, y, w, 22)
            self._period_rects[period] = r
            sel = period == self.period
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, period, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        body = pygame.Rect(rect.x + pad, y + 30, rect.w - 2 * pad,
                           rect.bottom - pad - y - 30)
        if self.tab == "brinson":
            self._draw_brinson(surf, body)
        else:
            self._draw_factors(surf, body)

    # -------------------------------------------------------------- Brinson
    def _draw_brinson(self, surf, body):
        br = self._br
        if br is None:
            widgets.draw_text(surf, "Détenez des actions pour comparer votre "
                              "gestion au marché.", (body.x, body.y + 8),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        inner = widgets.draw_panel(
            surf, body, f"Vous {br['r_p'] * 100:+.1f}% · marché "
            f"{br['r_b'] * 100:+.1f}% · écart {br['excess'] * 100:+.1f}%",
            config.COL_UP if br["excess"] >= 0 else config.COL_DOWN)
        t = br["totals"]
        widgets.draw_text(surf, f"= ALLOCATION {t['allocation'] * 100:+.1f}%  "
                          f"+ SÉLECTION {t['selection'] * 100:+.1f}%  "
                          f"+ interaction {t['interaction'] * 100:+.1f}%",
                          (inner.x, inner.y), fonts.small(bold=True),
                          config.COL_AMBER)
        y = inner.y + 24
        cols = [("SECTEUR", 0), ("POIDS (v/b)", int(inner.w * 0.24)),
                ("REND. (v/b)", int(inner.w * 0.42)),
                ("ALLOCATION", int(inner.w * 0.60)),
                ("SÉLECTION", int(inner.w * 0.80))]
        for lbl, dx in cols:
            widgets.draw_text(surf, lbl, (inner.x + dx, y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        y += 16
        amax = max((abs(r["allocation"]) for r in br["rows"]), default=0.0)
        smax = max((abs(r["selection"]) for r in br["rows"]), default=0.0)
        vmax = max(amax, smax) or 1.0
        bar_w = int(inner.w * 0.16)
        for row in br["rows"]:
            if y > inner.bottom - 30:
                break
            widgets.draw_text(surf, widgets.fit_text(row["sector"],
                                                     fonts.small(bold=True),
                                                     int(inner.w * 0.22)),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{row['w_p'] * 100:.0f}/{row['w_b'] * 100:.0f}%",
                              (inner.x + cols[1][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{row['r_p'] * 100:+.0f}/{row['r_b'] * 100:+.0f}%",
                              (inner.x + cols[2][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            for (lbl, dx), key in ((cols[3], "allocation"), (cols[4], "selection")):
                v = row[key]
                bx = inner.x + dx
                mid = bx + bar_w // 2
                w = int(abs(v) / vmax * bar_w * 0.5)
                col = config.COL_UP if v >= 0 else config.COL_DOWN
                pygame.draw.line(surf, config.COL_BORDER, (mid, y), (mid, y + 12))
                pygame.draw.rect(surf, col,
                                 pygame.Rect(mid if v >= 0 else mid - w, y + 2, w, 9),
                                 border_radius=2)
                widgets.draw_text(surf, f"{v * 100:+.1f}", (bx + bar_w + 4, y),
                                  fonts.tiny(), col)
            y += 19
        widgets.draw_text(surf, "Allocation = surpondérer les bons secteurs · "
                          "Sélection = choisir les bons titres dedans.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    # ------------------------------------------------------------- Facteurs
    def _draw_factors(self, surf, body):
        fr = self._fr
        if fr is None:
            widgets.draw_text(surf, "Détenez des actions (avec assez d'historique) "
                              "pour régresser votre gestion sur les facteurs.",
                              (body.x, body.y + 8), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        acol = config.COL_UP if fr["alpha_ann"] >= 0 else config.COL_DOWN
        inner = widgets.draw_panel(
            surf, body, f"Alpha {fr['alpha_ann'] * 100:+.1f}%/an · "
            f"R² {fr['r2'] * 100:.0f}% ({fr['n']} pas)", acol)
        verdict = ("L'essentiel de votre P&L vient des FACTEURS (paris de "
                   "marché/secteur/région), pas du choix des titres."
                   if fr["r2"] > 0.85 else
                   "Une vraie part de votre P&L est IDIOSYNCRATIQUE — du "
                   "stock picking (ou du bruit).")
        widgets.draw_text(surf, widgets.fit_text(verdict, fonts.small(), inner.w),
                          (inner.x, inner.y), fonts.small(), config.COL_AMBER)
        y = inner.y + 26
        rows = fr["rows"][:12]
        bmax = max((abs(r["beta"]) for r in rows), default=0.0) or 1.0
        bar_w = inner.w - 320
        for row in rows:
            if y > inner.bottom - 30:
                break
            widgets.draw_text(surf, widgets.fit_text(row["label"],
                                                     fonts.small(bold=True), 180),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            bx = inner.x + 190
            mid = bx + bar_w // 2
            w = int(abs(row["beta"]) / bmax * bar_w * 0.5)
            col = config.COL_CYAN if row["beta"] >= 0 else config.COL_DOWN
            pygame.draw.line(surf, config.COL_BORDER, (mid, y), (mid, y + 12))
            pygame.draw.rect(surf, col,
                             pygame.Rect(mid if row["beta"] >= 0 else mid - w,
                                         y + 2, w, 9), border_radius=2)
            widgets.draw_text(surf, f"β {row['beta']:+.2f}",
                              (bx + bar_w + 8, y), fonts.tiny(bold=True), col)
            y += 19
        widgets.draw_text(surf, "β Monde ≈ 1 = suiveur de marché · les β "
                          "secteur/région sont vos paris relatifs · l'alpha est "
                          "le reste.", (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
