"""
scene_graph.py — Atelier de graphes analytiques (style Bloomberg « G… »).

Un seul écran, plusieurs TYPES de graphes sélectionnables, alimentés par les ~5
ans d'historique du moteur de marché (préhistoire incluse) :

  GP    ligne de prix + moyennes mobiles        (line)
  GPC   chandeliers japonais (OHLC agrégé)       (candles)
  GPO   barres OHLC                              (bars)
  GPCH  variation % depuis une référence         (change)
  COMP  performances comparées (base 0 %)        (compare)
  HS    spread / ratio entre deux actifs         (spread)
  HVOL  volatilité historique annualisée glissante (vol)
  BETA  nuage de points + régression vs indice   (beta)
  CORR  matrice de corrélation (heatmap)         (corr)
  GEG   indicateurs macro superposés             (macro)
  GC    courbe des taux (maturité × rendement)   (curve)

Ouvrable depuis la console (GP/GPC/COMP/...), ou via le bouton GRAPHE des fiches.
"""
import pygame
from core import config, charts
from core import etfs as ETF
from core.scene_manager import Scene
from ui import fonts, widgets


def _asset_exists(market, tk):
    return tk in market.ticker_idx or ETF.exists(tk)

# (code, libellé court, kind, multi-actifs ?)
TYPES = [
    ("GP", "Ligne", "line", False),
    ("GPC", "Chandel.", "candles", False),
    ("GPO", "Barres", "bars", False),
    ("GPCH", "Var %", "change", False),
    ("COMP", "Comparer", "compare", True),
    ("HS", "Spread", "spread", True),
    ("HVOL", "Volatilité", "vol", False),
    ("BETA", "Bêta", "beta", False),
    ("CORR", "Corrél.", "corr", True),
    ("GEG", "Macro", "macro", False),
    ("GC", "Courbe", "curve", False),
]
_KIND_BY_CODE = {c: k for c, _, k, _ in TYPES}
_MULTI = {k for _, _, k, multi in TYPES if multi}
_NO_ASSET = {"macro", "curve"}     # types sans saisie d'actif

PERIODS = [("1A", 73), ("3A", 219), ("5A", 365), ("MAX", None)]
SERIES_COLS = [config.COL_AMBER, config.COL_CYAN, config.COL_UP, config.COL_WARN,
               config.COL_PRESTIGE, config.COL_DOWN]


class GraphScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.kind = kwargs.get("kind", "line")
        self.market = self.app.ensure_market()
        tickers = kwargs.get("tickers")
        self.error = None
        if not tickers:
            top = self.market.top_companies(n=1)
            tickers = [top[0]["ticker"]] if top else []
        else:
            # actifs demandés explicitement (ex. bouton GRAPHE d'une fiche) :
            # un ticker invalide/périmé (société radiée, faute de frappe) ne doit
            # pas planter — on filtre et on signale si rien n'est exploitable.
            requested = [t.upper() for t in tickers]
            valid = [t for t in requested if _asset_exists(self.market, t)]
            if not valid and self.kind not in _NO_ASSET:
                self.error = f"Actif introuvable : {', '.join(requested)}"
            tickers = valid
        self.tickers = [t.upper() for t in tickers][:6]
        self.period = kwargs.get("period", 365)
        self.spread_mode = "ratio"
        self.input = ""
        self._type_rects = {}
        self._period_rects = {}
        self._suggest_rects = []
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.mode_btn = widgets.Button(
            (240, config.SCREEN_HEIGHT - 50, 200, 42), "SPREAD : RATIO", config.COL_CYAN)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.go(self.return_to)
            elif event.key == pygame.K_BACKSPACE:
                self.input = self.input[:-1]
            elif event.key == pygame.K_RETURN:
                self._commit_input()
            elif event.unicode and event.unicode.isprintable() and len(self.input) < 8:
                self.input += event.unicode.upper()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rr, tk in self._suggest_rects:
                if rr.collidepoint(event.pos):
                    self._commit_input(ticker=tk)
                    return
            for code, rect in self._type_rects.items():
                if rect.collidepoint(event.pos):
                    self.kind = _KIND_BY_CODE[code]
                    self.input = ""
            for steps, rect in self._period_rects.items():
                if rect.collidepoint(event.pos):
                    self.period = steps
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.kind == "spread" and self.mode_btn.handle(event):
            self.spread_mode = "diff" if self.spread_mode == "ratio" else "ratio"
            self.mode_btn.label = f"SPREAD : {self.spread_mode.upper()}"

    def _commit_input(self, ticker=None):
        # recherche intelligente : résout un nom/ticker partiel vers un ticker
        q = ticker if ticker is not None else self.input.strip()
        self.input = ""
        if not q:
            return
        if ticker is not None:
            tk = q
        else:
            tk = self.market.resolve(q)
            if not tk and ETF.exists(q.upper()):   # un ticker d'ETF est aussi graphable
                tk = q.upper()
        if not tk:
            self.app.notify(f"Aucun résultat : {q}", "bad")
            return
        if self.kind in _MULTI:
            if tk not in self.tickers:
                self.tickers.append(tk)
                self.tickers = self.tickers[-6:]
        else:
            self.tickers = [tk]

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.mode_btn.update(mp, dt)

    # -------------------------------------------------------------- data
    def _series(self, tk):
        if ETF.exists(tk):
            return ETF.nav_history(self.market, tk, self.period)
        return self.market.history_of(tk, self.period)

    # -------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        if self.error:
            widgets.draw_error_panel(surf, self.error,
                                     "Utilisez SEARCH <texte> depuis le terminal.")
            self.back_btn.draw(surf)
            return
        code = next((c for c, _, k, _ in TYPES if k == self.kind), "GP")
        label = next((l for c, l, k, _ in TYPES if k == self.kind), "")
        widgets.draw_text(surf, f"GRAPHE — {code}  {label}", (40, 18),
                          fonts.title(bold=True), config.COL_AMBER)
        # sous-titre : actifs + période
        per = next((p for p, s in PERIODS if s == self.period), "5A")
        assets = "—" if self.kind in _NO_ASSET else " · ".join(self.tickers) or "—"
        widgets.draw_text(surf, f"{assets}    ·    période {per}", (42, 62),
                          fonts.small(), config.COL_TEXT_DIM)

        self._draw_type_tabs(surf)
        self._draw_controls(surf)

        canvas = pygame.Rect(40, 168, config.SCREEN_WIDTH - 80, config.footer_y() - 178)
        widgets.draw_panel(surf, canvas, None)
        inner = canvas.inflate(-24, -24)
        drawer = getattr(self, f"_draw_{self.kind}", None)
        if drawer:
            drawer(surf, inner)

        self.back_btn.draw(surf)
        if self.kind == "spread":
            self.mode_btn.draw(surf)
        self._draw_suggestions(surf)   # overlay : au-dessus du graphe

    def _draw_type_tabs(self, surf):
        self._type_rects = {}
        x, y, h = 40, 92, 30
        w = (config.SCREEN_WIDTH - 80 - (len(TYPES) - 1) * 4) // len(TYPES)
        for code, _, kind, _ in TYPES:
            rect = pygame.Rect(x, y, w, h)
            self._type_rects[code] = rect
            sel = (kind == self.kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1)
            font = fonts.small(bold=sel)
            img = font.render(code, True, config.COL_AMBER if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            x += w + 4

    def _draw_controls(self, surf):
        # sélecteur de période (gauche)
        self._period_rects = {}
        x, y = 40, 130
        for plabel, steps in PERIODS:
            rect = pygame.Rect(x, y, 56, 26)
            self._period_rects[steps] = rect
            sel = (steps == self.period)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1)
            font = fonts.small(bold=sel)
            img = font.render(plabel, True, config.COL_CYAN if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            x += 60
        # saisie d'actif (droite) + recherche intelligente par nom OU ticker
        if self.kind not in _NO_ASSET:
            hint = "+ NOM/TICKER" if self.kind in _MULTI else "NOM/TICKER"
            box = pygame.Rect(320, y, 300, 26)
            self._input_box = box
            pygame.draw.rect(surf, config.COL_PANEL, box)
            pygame.draw.rect(surf, config.COL_CYAN if self.input else config.COL_BORDER, box, 1)
            widgets.draw_text(surf, f"{hint} ▸ {self.input}_", (box.x + 8, box.y + 5),
                              fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, "tapez un nom, ex. « mavric » → MVC",
                              (box.right + 12, box.y + 5), fonts.tiny(), config.COL_TEXT_DIM)
        else:
            self._input_box = None

    def _draw_suggestions(self, surf):
        """Menu déroulant de recherche intelligente (dessiné EN DERNIER, au-dessus
        du graphe) : nom déformé → ticker, cliquable."""
        self._suggest_rects = []
        box = getattr(self, "_input_box", None)
        if not box or not self.input.strip():
            return
        sy = box.bottom + 2
        for tk, nm in self.market.suggest(self.input, 8):
            rr = pygame.Rect(box.x, sy, box.w + 220, 22)
            self._suggest_rects.append((rr, tk))
            hov = rr.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, rr)
            pygame.draw.rect(surf, config.COL_CYAN if hov else config.COL_BORDER, rr, 1)
            widgets.draw_text(surf, tk, (rr.x + 8, rr.y + 3), fonts.small(bold=True),
                              config.COL_AMBER)
            widgets.draw_text(surf, widgets.fit_text(nm, fonts.tiny(), rr.w - 90),
                              (rr.x + 80, rr.y + 4), fonts.tiny(), config.COL_TEXT_DIM)
            sy += 22

    # ----------------------------------------------------- helpers de tracé
    def _plot_axes(self, surf, rect, lo, hi, y_fmt=lambda v: f"{v:.0f}", rows=5):
        """Grille horizontale + libellés d'axe Y. Retourne (lo, hi, span)."""
        return widgets.draw_chart_axes(surf, rect, lo, hi, y_fmt, rows)

    def _polyline(self, surf, rect, series, lo, span, color):
        n = len(series)
        if n < 2:
            return
        pts = [(rect.x + int(i / (n - 1) * rect.w),
                rect.bottom - int((v - lo) / span * rect.h)) for i, v in enumerate(series)]
        pygame.draw.aalines(surf, color, False, pts)

    def _empty(self, surf, rect, msg="Aucune donnée. Saisissez un ticker."):
        widgets.draw_text(surf, msg, (rect.x, rect.y), fonts.small(), config.COL_TEXT_DIM)

    # ----------------------------------------------------- types : prix
    def _draw_line(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s = self._series(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, "Historique indisponible.")
        ma20, ma50 = charts.sma(s, 20), charts.sma(s, 50)
        allv = [v for v in s]
        lo, hi = min(allv), max(allv)
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:.0f}")
        self._polyline(surf, rect, s, lo, span, config.COL_AMBER)
        for ma, col in ((ma20, config.COL_CYAN), (ma50, config.COL_TEXT_DIM)):
            seg = [v for v in ma if v is not None]
            if len(seg) >= 2:
                # aligne la MA à droite (les None sont au début)
                start = len(s) - len(seg)
                pts = [(rect.x + int((start + i) / (len(s) - 1) * rect.w),
                        rect.bottom - int((v - lo) / span * rect.h)) for i, v in enumerate(seg)]
                pygame.draw.aalines(surf, col, False, pts)
        self._legend(surf, rect, [("Cours", config.COL_AMBER),
                                  ("MM20", config.COL_CYAN), ("MM50", config.COL_TEXT_DIM)])

    def _draw_candles(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s = self._series(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, "Historique indisponible.")
        lo, hi = min(s), max(s)
        self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:.0f}")
        widgets.draw_candles(surf, rect, s, n_candles=min(60, len(s)), sma_windows=(10, 30))

    def _draw_bars(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s = self._series(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, "Historique indisponible.")
        candles = widgets._aggregate_ohlc(s, min(70, len(s)))
        lo = min(c[2] for c in candles)
        hi = max(c[1] for c in candles)
        _, _, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:.0f}")
        slot = rect.w / len(candles)
        yof = lambda v: rect.bottom - int((v - lo) / span * rect.h)
        for k, (o, h, l, c) in enumerate(candles):
            cx = int(rect.x + (k + 0.5) * slot)
            col = config.COL_UP if c >= o else config.COL_DOWN
            pygame.draw.line(surf, col, (cx, yof(h)), (cx, yof(l)), 1)
            pygame.draw.line(surf, col, (cx - 3, yof(o)), (cx, yof(o)), 2)   # ouverture (gauche)
            pygame.draw.line(surf, col, (cx, yof(c)), (cx + 3, yof(c)), 2)   # clôture (droite)

    def _draw_change(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s = self._series(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, "Historique indisponible.")
        pct = charts.normalize(s)
        lo, hi = min(pct), max(pct)
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:+.0f}%")
        self._zero_line(surf, rect, lo, span)
        col = config.COL_UP if pct[-1] >= 0 else config.COL_DOWN
        self._polyline(surf, rect, pct, lo, span, col)

    # ----------------------------------------------------- multi-actifs
    def _draw_compare(self, surf, rect):
        series = [(tk, charts.normalize(self._series(tk))) for tk in self.tickers]
        series = [(tk, s) for tk, s in series if len(s) >= 2]
        if not series:
            return self._empty(surf, rect, "Ajoutez des tickers (Entrée).")
        allv = [v for _, s in series for v in s]
        lo, hi = min(allv), max(allv)
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:+.0f}%")
        self._zero_line(surf, rect, lo, span)
        legend = []
        for i, (tk, s) in enumerate(series):
            col = SERIES_COLS[i % len(SERIES_COLS)]
            self._polyline(surf, rect, s, lo, span, col)
            legend.append((f"{tk} {s[-1]:+.1f}%", col))
        self._legend(surf, rect, legend)

    def _draw_spread(self, surf, rect):
        if len(self.tickers) < 2:
            return self._empty(surf, rect, "Saisissez deux tickers (Entrée).")
        a, b = self._series(self.tickers[0]), self._series(self.tickers[1])
        sp = charts.spread(a, b, self.spread_mode)
        if len(sp) < 2:
            return self._empty(surf, rect, "Historique indisponible.")
        lo, hi = min(sp), max(sp)
        fmt = (lambda v: f"{v:.2f}") if self.spread_mode == "ratio" else (lambda v: f"{v:.0f}")
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, fmt)
        self._polyline(surf, rect, sp, lo, span, config.COL_PRESTIGE)
        op = "/" if self.spread_mode == "ratio" else "−"
        self._legend(surf, rect, [(f"{self.tickers[0]} {op} {self.tickers[1]} = {sp[-1]:.2f}",
                                   config.COL_PRESTIGE)])

    # ----------------------------------------------------- risque / quant
    def _draw_vol(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s = self._series(self.tickers[0])
        vol = [v for v in charts.rolling_vol(s, 20) if v is not None]
        if len(vol) < 2:
            return self._empty(surf, rect, "Historique insuffisant.")
        lo, hi = min(vol), max(vol)
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:.0f}%")
        self._polyline(surf, rect, vol, lo, span, config.COL_WARN)
        self._legend(surf, rect, [(f"Vol. annualisée (20 pas) = {vol[-1]:.1f}%", config.COL_WARN)])

    def _draw_beta(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        tk = self.tickers[0]
        i = self.market.ticker_idx.get(tk)
        if i is None:
            return self._empty(surf, rect, "Ticker inconnu.")
        region = self.market.companies[i]["region"]
        idx_name = next((n for n, r in self.market.index_region.items() if r == region), None)
        s = self._series(tk)
        ridx = self.market.index_history(idx_name)[-self.period:] if (idx_name and self.period) \
            else (self.market.index_history(idx_name) if idx_name else [])
        ry, rx = charts.simple_returns(s), charts.simple_returns(ridx)
        n = min(len(ry), len(rx))
        if n < 5:
            return self._empty(surf, rect, "Historique insuffisant pour le bêta.")
        ry, rx = ry[-n:], rx[-n:]
        beta, alpha, r2 = charts.ols_beta(ry, rx)
        xr = max(abs(min(rx)), abs(max(rx))) or 0.01
        yr = max(abs(min(ry)), abs(max(ry))) or 0.01
        cx0, cy0 = rect.centerx, rect.centery
        sx, sy = rect.w / (2 * xr), rect.h / (2 * yr)
        pygame.draw.line(surf, config.COL_BORDER, (rect.x, cy0), (rect.right, cy0), 1)
        pygame.draw.line(surf, config.COL_BORDER, (cx0, rect.y), (cx0, rect.bottom), 1)
        for k in range(n):
            px = int(cx0 + rx[k] * sx)
            py = int(cy0 - ry[k] * sy)
            pygame.draw.circle(surf, config.COL_CYAN, (px, py), 2)
        # droite de régression y = alpha + beta x
        x1, x2 = -xr, xr
        p1 = (int(cx0 + x1 * sx), int(cy0 - (alpha + beta * x1) * sy))
        p2 = (int(cx0 + x2 * sx), int(cy0 - (alpha + beta * x2) * sy))
        pygame.draw.line(surf, config.COL_AMBER, p1, p2, 2)
        widgets.draw_text(surf, f"{tk} vs {idx_name}", (rect.x, rect.y), fonts.small(bold=True),
                          config.COL_TEXT)
        widgets.draw_text(surf, f"β = {beta:.2f}   α = {alpha*100:.2f}%/pas   R² = {r2:.2f}",
                          (rect.x, rect.y + 20), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "x : rendement indice   ·   y : rendement actif",
                          (rect.centerx, rect.bottom - 4), fonts.tiny(),
                          config.COL_TEXT_DIM, align="center")

    def _draw_corr(self, surf, rect):
        tickers = self.tickers
        if len(tickers) < 2:
            # défaut : positions du joueur, sinon watchlist
            p = self.app.gs.player
            tickers = list(p.portfolio.keys()) or list(p.watchlist) or self.tickers
            tickers = tickers[:8]
        if len(tickers) < 2:
            return self._empty(surf, rect, "Saisissez ≥ 2 tickers (Entrée).")
        smap = {tk: self._series(tk) for tk in tickers}
        labels, corr = charts.correlation_matrix(smap)
        nlab = len(labels)
        cell = min((rect.h - 30) // nlab, (rect.w - 120) // nlab, 64)
        x0, y0 = rect.x + 110, rect.y + 20
        for r in range(nlab):
            widgets.draw_text(surf, widgets.fit_text(labels[r], fonts.tiny(), 100),
                              (rect.x, y0 + r * cell + cell // 2 - 6), fonts.tiny(), config.COL_TEXT)
            for c in range(nlab):
                v = float(corr[r, c])
                # rouge (−1) → noir (0) → vert (+1)
                if v >= 0:
                    col = widgets._lerp_col(config.COL_PANEL, config.COL_UP, v)
                else:
                    col = widgets._lerp_col(config.COL_PANEL, config.COL_DOWN, -v)
                cr = pygame.Rect(x0 + c * cell, y0 + r * cell, cell - 2, cell - 2)
                pygame.draw.rect(surf, col, cr)
                widgets.draw_text(surf, f"{v:.2f}", cr.center, fonts.tiny(),
                                  config.COL_WHITE, align="center")
        for c in range(nlab):
            widgets.draw_text(surf, widgets.fit_text(labels[c], fonts.tiny(), cell),
                              (x0 + c * cell + cell // 2, y0 - 14), fonts.tiny(),
                              config.COL_TEXT, align="center")

    # ----------------------------------------------------- macro / taux
    def _draw_macro(self, surf, rect):
        keys = ["rate", "inflation", "growth", "unemployment"]
        series = [(self.market.macro[k]["label"], self.market.macro_hist[k][-self.period:]
                   if self.period else self.market.macro_hist[k]) for k in keys]
        series = [(lab, s) for lab, s in series if len(s) >= 2]
        if not series:
            return self._empty(surf, rect, "Historique macro indisponible.")
        allv = [v for _, s in series for v in s]
        lo, hi, span = self._plot_axes(surf, rect, min(allv), max(allv), lambda v: f"{v:.1f}%")
        legend = []
        for i, (lab, s) in enumerate(series):
            col = SERIES_COLS[i % len(SERIES_COLS)]
            self._polyline(surf, rect, s, min(allv), span, col)
            legend.append((f"{lab} {s[-1]:.1f}%", col))
        self._legend(surf, rect, legend)

    def _draw_curve(self, surf, rect):
        curve = charts.yield_curve(self.market, "AAA")
        ys = [y for _, y in curve]
        xs = [m for m, _ in curve]
        lo, hi = min(ys) * 0.9, max(ys) * 1.1
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:.1f}%")
        mx = max(xs)
        pts = []
        for (m, y) in curve:
            px = rect.x + int(m / mx * rect.w)
            py = rect.bottom - int((y - lo) / span * rect.h)
            pts.append((px, py))
            pygame.draw.circle(surf, config.COL_AMBER, (px, py), 3)
            widgets.draw_text(surf, f"{m}a", (px, rect.bottom + 2), fonts.tiny(),
                              config.COL_TEXT_DIM, align="center")
        if len(pts) >= 2:
            pygame.draw.aalines(surf, config.COL_AMBER, False, pts)
        self._legend(surf, rect, [("Courbe souveraine AAA — niveau "
                                   f"{charts.yield_curve(self.market,'AAA',(1,))[0][1]:.2f}% (1a)",
                                   config.COL_AMBER)])

    # ----------------------------------------------------- petits helpers
    def _zero_line(self, surf, rect, lo, span):
        widgets.draw_chart_zero_line(surf, rect, lo, span)

    def _legend(self, surf, rect, items):
        widgets.draw_chart_legend(surf, rect, items)
