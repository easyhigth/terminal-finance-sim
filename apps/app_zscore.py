"""
app_zscore.py — Application « Z-Score » du bureau (NATIVE).

Analyse statistique d'une valeur : à combien d'écarts-types son comportement
récent s'écarte-t-il de sa norme historique ? Quatre lectures (chips) :
- PRIX : z-score glissant du cours vs sa moyenne mobile — LE signal de
  retour à la moyenne (z < −2 : très en-dessous de sa norme, z > +2 :
  très au-dessus) ;
- RENDEMENT : z-score du dernier rendement par pas (choc inhabituel ?) ;
- VOLATILITÉ : z-score de la vol glissante (régime de vol anormal ?) ;
- CORRÉLATION : z-score de la corrélation glissante au VRAI indice régional
  (décorrélation/recorrélation inhabituelle ?).

La courbe montre le z-score DANS LE TEMPS avec les bandes ±1σ/±2σ — on voit
les excursions passées et où on se situe aujourd'hui. Sélection par chips
(positions détenues + watchlist) ou saisie libre (Ctrl+V supporté).
Boutons TRADER / ALERTE pour agir sur le signal sans re-saisir le ticker.
"""
import pygame

from apps.base import DesktopApp
from core import clipboard, config
from core import quant_tools as QT
from ui import fonts, widgets

PERIODS = ["3M", "1A", "3A", "5A"]
ANALYSES = [("price", "PRIX"), ("returns", "RENDEMENT"),
            ("vol", "VOLATILITÉ"), ("corr", "CORRÉLATION")]
WINDOW = 18                      # fenêtre glissante (~1 trimestre)


class ZScoreApp(DesktopApp):
    title = "Z-Score"
    icon_kind = "graph"
    default_size = (960, 600)
    min_size = (700, 460)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.ticker = self._default_ticker()
        self.period = "1A"
        self.analysis = "price"
        self.search = ""
        self.msg = ""
        self._cache_key = None
        self._res = None
        self._chip_rects = {}
        self._period_rects = {}
        self._analysis_rects = {}
        self._search_rect = None
        self._trade_btn = None
        self._alert_btn = None
        self._search_active = False

    def _default_ticker(self):
        p = self.app.gs.player
        for tk, pos in p.portfolio.items():
            if pos["shares"] > 0 and tk in self.market.ticker_idx:
                return tk
        wl = [tk for tk in getattr(p, "watchlist", []) if tk in self.market.ticker_idx]
        if wl:
            return wl[0]
        top = self.market.top_companies(n=1)
        return top[0]["ticker"] if top else ""

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        key = (self.market.step_count, self.ticker, self.period, self.analysis)
        if key == self._cache_key:
            return
        self._cache_key = key
        self._res = self._compute()

    def _compute(self):
        m = self.market
        if not self.ticker or self.ticker not in m.ticker_idx:
            return None
        steps = QT.PERIOD_STEPS[self.period]
        hist = m.history_of(self.ticker, (steps or 365) + WINDOW)
        rets = QT.simple_returns(hist)
        if self.analysis == "price":
            series = QT.rolling_zscore(hist, WINDOW)
            desc = "cours vs sa moyenne mobile"
        elif self.analysis == "returns":
            series = QT.rolling_zscore(rets, WINDOW)
            desc = "dernier rendement vs sa norme"
        elif self.analysis == "vol":
            vols = QT.rolling_volatility(rets, WINDOW)
            series = QT.rolling_zscore(vols, WINDOW)
            desc = "volatilité glissante vs sa norme"
        else:  # corr
            idx = QT.main_index(m, self.app.gs.player)
            bench = QT.index_returns(m, idx, len(rets))
            corrs = QT.rolling_correlation(rets, bench, WINDOW)
            series = QT.rolling_zscore(corrs, WINDOW)
            desc = f"corrélation glissante à {idx} vs sa norme"
        if len(series) < 2:
            return None
        z = float(series[-1])
        if abs(z) > 2:
            verdict, col = "ÉCART EXTRÊME (> 2σ)", config.COL_DOWN
        elif abs(z) > 1:
            verdict, col = "Écart notable (> 1σ)", config.COL_AMBER
        else:
            verdict, col = "Dans la norme (< 1σ)", config.COL_UP
        hint = ""
        if self.analysis == "price":
            if z <= -2:
                hint = "Très en-dessous de sa norme — candidat retour à la moyenne (à confronter aux fondamentaux)."
            elif z >= 2:
                hint = "Très au-dessus de sa norme — prudence sur un achat au plus haut."
        elif self.analysis == "vol" and z >= 2:
            hint = "Régime de volatilité inhabituel — voir l'app Couverture."
        return {"series": series, "z": z, "verdict": verdict, "col": col,
                "desc": desc, "hint": hint, "n": len(series)}

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.KEYDOWN and self._search_active:
            if event.key == pygame.K_ESCAPE:
                self._search_active = False
                self.search = ""
                return True
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._try_select(self.search)
                return True
            if clipboard.is_paste_shortcut(event):
                self.search += clipboard.paste().replace("\n", " ").strip()
                return True
            if event.unicode and event.unicode.isprintable():
                self.search += event.unicode.upper()
                return True
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        self._search_active = bool(self._search_rect
                                   and self._search_rect.collidepoint(pos))
        if self._search_active:
            return True
        for tk, r in self._chip_rects.items():
            if r.collidepoint(pos):
                self.ticker = tk
                self.msg = ""
                return True
        for period, r in self._period_rects.items():
            if r.collidepoint(pos):
                self.period = period
                return True
        for a, r in self._analysis_rects.items():
            if r.collidepoint(pos):
                self.analysis = a
                return True
        if self._trade_btn and self._trade_btn.collidepoint(pos):
            if self.desktop is not None and self.ticker:
                self.desktop.open_trading(self.ticker)
            return True
        if self._alert_btn and self._alert_btn.collidepoint(pos):
            if self.desktop is not None and self.ticker:
                self.desktop._open_scene_window("alerts", ticker=self.ticker)
            return True
        return False

    def _try_select(self, text):
        text = text.strip().upper()
        self._search_active = False
        self.search = ""
        if not text:
            return
        if text in self.market.ticker_idx:
            self.ticker = text
            self.msg = ""
            return
        # correspondance partielle sur ticker ou nom
        for c in self.market.companies:
            if text in c["ticker"] or text in c["name"].upper():
                self.ticker = c["ticker"]
                self.msg = ""
                return
        self.msg = f"« {text} » introuvable."

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "Z-SCORE — ANALYSE STATISTIQUE",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        # sélection : chips positions + watchlist + recherche
        p = self.app.gs.player
        chips = [tk for tk, pos in p.portfolio.items()
                 if pos["shares"] > 0 and tk in self.market.ticker_idx]
        for tk in getattr(p, "watchlist", []):
            if tk not in chips and tk in self.market.ticker_idx:
                chips.append(tk)
        if self.ticker and self.ticker not in chips:
            chips.insert(0, self.ticker)
        x, y = rect.x + pad, rect.y + 34
        self._chip_rects = {}
        for tk in chips[:10]:
            w = fonts.tiny(bold=True).size(tk)[0] + 14
            if x + w > rect.right - pad - 170:
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
        self._search_rect = pygame.Rect(rect.right - pad - 160, y, 160, 20)
        pygame.draw.rect(surf, config.COL_PANEL, self._search_rect, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN if self._search_active
                         else config.COL_BORDER, self._search_rect, 1, border_radius=3)
        label = self.search if (self.search or self._search_active) else "Autre ticker…"
        col = config.COL_TEXT if (self.search or self._search_active) else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), 148),
                          (self._search_rect.x + 6, self._search_rect.y + 4),
                          fonts.tiny(), col)
        # rangée 2 : analyse + période + actions
        y += 26
        x = rect.x + pad
        self._analysis_rects = {}
        for a, lbl in ANALYSES:
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            self._analysis_rects[a] = r
            sel = a == self.analysis
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        x += 10
        self._period_rects = {}
        for period in PERIODS:
            w = fonts.tiny(bold=True).size(period)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            self._period_rects[period] = r
            sel = period == self.period
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, period, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        bw = fonts.tiny(bold=True).size("ALERTE")[0] + 16
        self._alert_btn = pygame.Rect(rect.right - pad - bw, y, bw, 20)
        tw = fonts.tiny(bold=True).size("TRADER")[0] + 16
        self._trade_btn = pygame.Rect(self._alert_btn.x - tw - 6, y, tw, 20)
        for r, lbl, col in ((self._trade_btn, "TRADER", config.COL_UP),
                            (self._alert_btn, "ALERTE", config.COL_AMBER)):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            pygame.draw.rect(surf, col, r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=True), col,
                              align="center")
        if self.msg:
            widgets.draw_text(surf, self.msg, (rect.x + pad, y + 24),
                              fonts.tiny(), config.COL_DOWN)

        top = y + 30
        if self._res is None:
            widgets.draw_text(surf, "Pas assez d'historique pour cette analyse "
                              "(élargissez la période).",
                              (rect.x + pad, top + 8), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        res = self._res
        # tuile z + verdict
        name = ""
        mt = self.market.metrics(self.ticker)
        if mt:
            name = mt["name"]
        widgets.draw_text(surf, f"{self.ticker} — {name}", (rect.x + pad, top),
                          fonts.small(bold=True), config.COL_TEXT)
        widgets.draw_text(surf, f"z = {res['z']:+.2f}", (rect.x + pad, top + 20),
                          fonts.title(bold=True), res["col"])
        widgets.draw_text(surf, res["verdict"], (rect.x + pad + 130, top + 28),
                          fonts.small(bold=True), res["col"])
        widgets.draw_text(surf, f"Mesure : {res['desc']} (fenêtre {WINDOW} pas).",
                          (rect.x + pad, top + 52), fonts.tiny(), config.COL_TEXT_DIM)
        chart_top = top + 72
        chart = pygame.Rect(rect.x + pad, chart_top, rect.w - 2 * pad,
                            rect.bottom - pad - chart_top - (18 if res["hint"] else 0))
        self._draw_zchart(surf, chart, res["series"])
        if res["hint"]:
            widgets.draw_text(surf, res["hint"],
                              (rect.x + pad, rect.bottom - pad - 14),
                              fonts.tiny(), config.COL_AMBER)

    def _draw_zchart(self, surf, rect, series):
        inner = widgets.draw_panel(surf, rect, "Z-score dans le temps (bandes ±1σ / ±2σ)",
                                   config.COL_CYAN)
        if inner.h < 40 or len(series) < 2:
            return
        lo = min(float(series.min()), -2.5)
        hi = max(float(series.max()), 2.5)
        rng = (hi - lo) or 1.0
        plot = inner.inflate(-8, -16)

        def py(v):
            return plot.bottom - int((v - lo) / rng * plot.h)
        # bandes ±1σ / ±2σ + ligne 0
        for lvl, col in ((2, config.COL_DOWN), (1, config.COL_AMBER),
                         (-1, config.COL_AMBER), (-2, config.COL_DOWN)):
            yy = py(lvl)
            for x0 in range(plot.x, plot.right, 8):
                pygame.draw.line(surf, col, (x0, yy), (min(x0 + 4, plot.right), yy))
            widgets.draw_text(surf, f"{lvl:+d}σ", (plot.right - 24, yy - 12),
                              fonts.tiny(), col)
        pygame.draw.line(surf, config.COL_BORDER, (plot.x, py(0)), (plot.right, py(0)))
        pts = [(plot.x + int(i / max(1, len(series) - 1) * plot.w), py(float(v)))
               for i, v in enumerate(series)]
        pygame.draw.aalines(surf, config.COL_CYAN, False, pts)
        pygame.draw.circle(surf, config.COL_WHITE, pts[-1], 3)
