"""
scene_graph_render.py — GraphRenderMixin : les 11 renderers de types de
graphe (ligne, chandeliers, barres, variation %, comparaison, spread,
volatilité, bêta, corrélation, macro, courbe des taux) + leurs helpers de
tracé communs (axes, libellés X, polyligne, légende…). Extrait de
scene_graph.py (découpage en mixins, même principe que scene_terminal_*.py/
scene_desktop_*.py) — GraphScene garde le cœur (cycle de vie, données,
chrome).
"""
import pygame

from core import charts, config, indicators
from core.i18n import get_lang
from scenes.scene_graph_common import SERIES_COLS, x_label_positions
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


class GraphRenderMixin:
    # ----------------------------------------------------- helpers de tracé
    def _plot_axes(self, surf, rect, lo, hi, y_fmt=lambda v: f"{v:.0f}", rows=5,
                   right_labels=False, pad_pct=0.0):
        """Grille horizontale + libellés d'axe Y. Retourne (lo, hi, span).
        `pad_pct` ajoute un padding autour de la série (p. ex. 1.5%) pour que
        les micro-variations ne soient pas écrasées sur le bord du graphe."""
        if pad_pct:
            span = (hi - lo) or 1.0
            pad = max(span * pad_pct, abs(hi) * pad_pct * 0.5, abs(lo) * pad_pct * 0.5, 0.01)
            lo -= pad
            hi += pad
        return widgets.draw_chart_axes(surf, rect, lo, hi, y_fmt, rows,
                                       right_labels=right_labels)

    def _x_labels(self, surf, rect, n):
        """Libellés d'axe X sous une série temporelle de `n` points (le plus à
        droite = le plus récent) — cf. `scene_graph_common.x_label_positions`
        pour l'échelle adaptative (minutes/heures/jours/dates/années),
        factorisée avec `scene_company.py` (fiche société)."""
        labels = x_label_positions(self.period, n, self.app.gs.player.day)
        if labels:
            widgets.draw_chart_x_labels(surf, rect, labels)

    def _polyline(self, surf, rect, series, lo, span, color, y_fmt=None, cursor=None,
                  show_pct=False, area_fill=False, show_current_line=False,
                  line_width=1, area_alpha=None, baseline=True):
        n = len(series)
        if n < 2:
            return
        widgets.draw_series(surf, rect, series, color, baseline=baseline, mouse_pos=None,
                              y_fmt=y_fmt, show_pct=show_pct, show_extrema=False,
                              area_fill=area_fill, show_current_line=show_current_line,
                              line_width=line_width, area_alpha=area_alpha,
                              lo=lo, hi=lo + span)
        if cursor is not None:
            cursor.draw(surf, rect, series, lo, span, mouse_pos=pygame.mouse.get_pos(),
                       y_fmt=y_fmt, color=color, show_pct=show_pct)
        else:
            widgets.draw_chart_crosshair(surf, rect, series, lo, span, pygame.mouse.get_pos(),
                                         y_fmt=y_fmt, color=color)
            widgets.draw_chart_extrema(surf, rect, series, lo, span, y_fmt=y_fmt)

    def _empty(self, surf, rect, msg=None):
        if msg is None:
            msg = _L("Aucune donnée. Saisissez un ticker.", "No data. Enter a ticker.")
        widgets.draw_text(surf, msg, (rect.x, rect.y), fonts.small(), config.COL_TEXT_DIM)

    def _draw_event_markers(self, surf, rect, series, lo, span, pps=None):
        """Dessine des icônes d'événements d'entreprise sur la courbe de prix.
        Les événements sont positionnés à leur pas de marché correspondant
        sur la série densifiée (intraday). `pps` est le nombre de points
        intermédiaires par pas utilisé pour générer `series` ; s'il est None
        (fenêtre intraday), on le déduit du nombre de points par pas."""
        mkt = self.market
        if mkt is None or not self.tickers:
            return
        tk = self.tickers[0]
        events = mkt.company_events_log.get(tk, [])
        if not events:
            return
        from core import intraday
        n = len(series)
        if n < 2:
            return
        if pps is None:
            # Graphes ligne/vol/bêta/etc. qui utilisent `_series()` standard :
            # retomber sur la densification par défaut du moteur. Fenêtres
            # intraday : on infère grossièrement le pps depuis la longueur.
            if self.period is not None and self.period > 0:
                pps = intraday.points_per_segment_for_n_steps(self.period)
            else:
                steps_in_series = 1
                pps = max(1, (n - 1) // max(1, steps_in_series) - 1)
        if pps <= 0:
            return
        current_step = mkt.step_count
        _KIND_COL = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_CYAN}
        for ev in events:
            steps_back = current_step - ev["step"]
            if steps_back < 0 or steps_back > (self.period or 9999):
                continue
            idx = n - 1 - steps_back * (pps + 1)
            if idx < 0 or idx >= n:
                continue
            price = series[int(idx)]
            if lo is None or span == 0:
                continue
            y = rect.y + rect.h - int((price - lo) / span * rect.h)
            x = rect.x + int(idx / (n - 1) * rect.w)
            if not rect.collidepoint(x, y):
                continue
            icon = ev.get("icon", "•")
            ecol = _KIND_COL.get(ev.get("kind", "info"), config.COL_CYAN)
            r = 6
            pygame.draw.circle(surf, (8, 10, 14), (x, y), r + 1)
            pygame.draw.circle(surf, ecol, (x, y), r, 1)
            widgets.draw_text(surf, icon, (x, y - 7), fonts.tiny(), ecol, align="center")

    # ----------------------------------------------------- types : prix
    def _draw_line(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s = self._series(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, _L("Historique indisponible.", "History unavailable."))
        ma20, ma50 = charts.sma(s, 20), charts.sma(s, 50)
        # indicateurs techniques optionnels (overlay, lecture seule) : élargissent
        # les bornes Y si besoin (bandes de Bollinger peuvent dépasser le prix).
        boll = indicators.bollinger_bands(s, period=20, num_std=2.0) if self.show_bollinger else None
        sma_ind = indicators.sma(s, 20) if self.show_sma else None
        allv = [v for v in s]
        if boll:
            allv += [v for v in boll[0] if v is not None]
            allv += [v for v in boll[2] if v is not None]
        lo, hi = min(allv), max(allv)
        # Style « vraie appli de trading » : labels de prix à droite, pas de
        # baseline au premier point, courbe cyan épaisse avec dégradé très
        # transparent — les piques et zigzags du chemin canonique restent visibles.
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:.0f}",
                                       right_labels=True, pad_pct=0.015)
        self._x_labels(surf, rect, len(s))
        line_col = config.COL_CYAN
        legend = [(_L("Cours", "Price"), line_col),
                  ("MM20", config.COL_WHITE), ("MM50", config.COL_TEXT_DIM)]
        if boll:
            lower, mid, upper = boll
            self._overlay_aligned(surf, rect, lower, lo, span, (150, 150, 160), width=1)
            self._overlay_aligned(surf, rect, upper, lo, span, (150, 150, 160), width=1)
            legend.append(("Bollinger 20·2σ", (150, 150, 160)))
        self._polyline(surf, rect, s, lo, span, line_col, y_fmt=lambda v: f"{v:,.2f}",
                       cursor=self._cursor, show_pct=True, area_fill=True,
                       show_current_line=True, line_width=2, area_alpha=45,
                       baseline=False)
        for ma, col in ((ma20, config.COL_WHITE), (ma50, config.COL_TEXT_DIM)):
            seg = [v for v in ma if v is not None]
            if len(seg) >= 2:
                # aligne la MA à droite (les None sont au début)
                start = len(s) - len(seg)
                pts = [(rect.x + int((start + i) / (len(s) - 1) * rect.w),
                        rect.bottom - int((v - lo) / span * rect.h)) for i, v in enumerate(seg)]
                pygame.draw.aalines(surf, col, False, pts)
        if sma_ind:
            self._overlay_aligned(surf, rect, sma_ind, lo, span, config.COL_WARN, width=2)
            legend.append(("SMA20 (indicators)", config.COL_WARN))
        self._legend(surf, rect, legend)
        self._draw_event_markers(surf, rect, s, lo, span)

    def _overlay_aligned(self, surf, rect, series, lo, span, color, width=1):
        """Trace une série alignée sur l'axe x du graphe principal (même longueur,
        `None` autorisés en tête/au milieu) — ne dessine que les segments
        contigus définis, en suivant exactement le même mapping pixel que
        `_polyline`/`_draw_line` pour ne pas décaler l'overlay."""
        n = len(series)
        if n < 2:
            return
        seg = []
        for i, v in enumerate(series):
            if v is None:
                if len(seg) >= 2:
                    pygame.draw.lines(surf, color, False, seg, width)
                seg = []
                continue
            x = rect.x + int(i / (n - 1) * rect.w)
            y = rect.bottom - int((v - lo) / span * rect.h)
            seg.append((x, y))
        if len(seg) >= 2:
            pygame.draw.lines(surf, color, False, seg, width)

    def _draw_rsi_panel(self, surf, rect):
        """Panneau RSI(14) sous le graphique principal, échelle fixe 0-100 avec
        repères survente/surachat à 30/70."""
        if not self.tickers:
            return self._empty(surf, rect, "")
        s = self._series(self.tickers[0])
        vals = indicators.rsi(s, period=14)
        lo, hi, span = self._plot_axes(surf, rect, 0, 100, lambda v: f"{v:.0f}", rows=4)
        for level, col in ((30, config.COL_DOWN), (70, config.COL_UP)):
            yy = rect.bottom - int((level - lo) / span * rect.h)
            pygame.draw.line(surf, col, (rect.x, yy), (rect.right, yy), 1)
        if any(v is not None for v in vals):
            self._overlay_aligned(surf, rect, vals, lo, span, config.COL_PRESTIGE, width=2)
            widgets.draw_chart_crosshair(surf, rect, vals, lo, span, pygame.mouse.get_pos(),
                                         y_fmt=lambda v: f"{v:.1f}", color=config.COL_PRESTIGE)
            widgets.draw_chart_extrema(surf, rect, vals, lo, span, y_fmt=lambda v: f"{v:.1f}",
                                       color=config.COL_PRESTIGE)
            last = next((v for v in reversed(vals) if v is not None), None)
            if last is not None:
                self._legend(surf, rect, [(f"RSI(14) = {last:.1f}", config.COL_PRESTIGE)])
        else:
            widgets.draw_text(surf, "Historique insuffisant pour le RSI(14).",
                              (rect.x, rect.y), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_candles(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s, pps = self._series_for_ohlc(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, _L("Historique indisponible.", "History unavailable."))
        lo, hi = min(s), max(s)
        y_fmt = self._ohlc_y_fmt(lo, hi)
        self._plot_axes(surf, rect, lo, hi, y_fmt,
                         right_labels=True, pad_pct=0.01)
        # Nombre de bougies adapté à la période : plus on zoome, plus on voit
        # de bougies avec du détail. Les fenêtres intraday utilisent déjà un
        # chemin canonique fin ; les périodes par pas sont densifiées par
        # `_series_for_ohlc` pour donner à chaque bougie une vraie texture.
        n_candles = self._ohlc_n_buckets(s, default_intraday=24,
                                          default_step=min(60, len(s)))
        widgets.draw_candles(surf, rect, s, n_candles=n_candles, sma_windows=(10, 30))
        self._x_labels(surf, rect, n_candles)
        self._track_candle_rects(rect, s, n_candles)
        self._draw_event_markers(surf, rect, s, lo, hi - lo or 1.0, pps=pps)

    def _ohlc_y_fmt(self, lo, hi):
        """Format de prix adapté à la plage affichée : centimes quand on zoome
        (plage étroite), décimal puis entier quand on dézoome."""
        span = hi - lo
        if span < 1.0:
            return lambda v: f"{v:,.2f}"
        if span < 10.0:
            return lambda v: f"{v:,.1f}"
        return lambda v: f"{v:,.0f}"

    def _ohlc_n_buckets(self, s, default_intraday, default_step):
        """Nombre de buckets (bougies/barres) à afficher selon la période."""
        n = len(s)
        if self.period is None:
            return min(default_step, n)
        if self.period < 0:
            window = -self.period
            if window <= 1440:       # 1J
                return min(24, n)
            if window <= 10080:     # 1W
                return min(48, n)
            return min(default_intraday, n)
        if self.period <= 6:         # 1M
            return min(30, n)
        if self.period <= 18:        # 3M
            return min(60, n)
        return min(default_step, n)

    def _track_candle_rects(self, rect, closes, n_candles):
        """Mémorise le rect écran + le détail brut (sous-échantillon) de
        chaque bougie affichée, pour permettre un drill-down au clic (idée
        « zoom bougie ») sans recalculer la moindre donnée de marché."""
        n = len(closes)
        n_c = max(1, min(n_candles, n))
        bucket = max(1, n // n_c)
        candles = widgets._aggregate_ohlc(closes, n_candles)
        n_actual = len(candles)
        slot = rect.w / n_actual
        self._candle_rects = []
        for k in range(n_actual):
            cx = rect.x + (k + 0.5) * slot
            click_rect = pygame.Rect(int(cx - slot / 2), rect.y, max(1, int(slot)), rect.h)
            sub = closes[k * bucket:(k + 1) * bucket] or closes[k * bucket:k * bucket + 1]
            self._candle_rects.append((click_rect, sub))

    def _draw_bars(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s, pps = self._series_for_ohlc(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, _L("Historique indisponible.", "History unavailable."))
        n_bars = self._ohlc_n_buckets(s, default_intraday=30,
                                       default_step=min(70, len(s)))
        candles = widgets._aggregate_ohlc(s, n_bars)
        lo = min(c[2] for c in candles)
        hi = max(c[1] for c in candles)
        y_fmt = self._ohlc_y_fmt(lo, hi)
        _, _, span = self._plot_axes(surf, rect, lo, hi, y_fmt,
                                       right_labels=True, pad_pct=0.01)
        self._x_labels(surf, rect, len(candles))
        slot = rect.w / len(candles)
        yof = lambda v: rect.bottom - int((v - lo) / span * rect.h)
        for k, (o, h, l, c) in enumerate(candles):
            cx = int(rect.x + (k + 0.5) * slot)
            col = config.COL_UP if c >= o else config.COL_DOWN
            pygame.draw.line(surf, col, (cx, yof(h)), (cx, yof(l)), 1)
            pygame.draw.line(surf, col, (cx - 3, yof(o)), (cx, yof(o)), 2)   # ouverture (gauche)
            pygame.draw.line(surf, col, (cx, yof(c)), (cx + 3, yof(c)), 2)   # clôture (droite)
        self._draw_event_markers(surf, rect, s, lo, span, pps=pps)

    def _draw_change(self, surf, rect):
        if not self.tickers:
            return self._empty(surf, rect)
        s = self._series(self.tickers[0])
        if len(s) < 2:
            return self._empty(surf, rect, _L("Historique indisponible.", "History unavailable."))
        pct = charts.normalize(s)
        lo, hi = min(pct), max(pct)
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:+.0f}%")
        self._x_labels(surf, rect, len(pct))
        self._zero_line(surf, rect, lo, span)
        col = config.COL_UP if pct[-1] >= 0 else config.COL_DOWN
        self._polyline(surf, rect, pct, lo, span, col, y_fmt=lambda v: f"{v:+.1f}%",
                       cursor=self._cursor)

    # ----------------------------------------------------- multi-actifs
    def _draw_compare(self, surf, rect):
        series = [(tk, charts.normalize(self._series(tk))) for tk in self.tickers]
        series = [(tk, s) for tk, s in series if len(s) >= 2]
        if not series:
            return self._empty(surf, rect, _L("Ajoutez des tickers (Entrée).", "Add tickers (Enter)."))
        allv = [v for _, s in series for v in s]
        lo, hi = min(allv), max(allv)
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, lambda v: f"{v:+.0f}%")
        self._x_labels(surf, rect, max(len(s) for _, s in series))
        self._zero_line(surf, rect, lo, span)
        legend = []
        for i, (tk, s) in enumerate(series):
            col = SERIES_COLS[i % len(SERIES_COLS)]
            self._polyline(surf, rect, s, lo, span, col, y_fmt=lambda v: f"{v:+.1f}%")
            legend.append((f"{tk} {s[-1]:+.1f}%", col))
        self._legend(surf, rect, legend)

    def _draw_spread(self, surf, rect):
        if len(self.tickers) < 2:
            return self._empty(surf, rect, _L("Saisissez deux tickers (Entrée).", "Enter two tickers (Enter)."))
        a, b = self._series(self.tickers[0]), self._series(self.tickers[1])
        sp = charts.spread(a, b, self.spread_mode)
        if len(sp) < 2:
            return self._empty(surf, rect, _L("Historique indisponible.", "History unavailable."))
        lo, hi = min(sp), max(sp)
        fmt = (lambda v: f"{v:.2f}") if self.spread_mode == "ratio" else (lambda v: f"{v:.0f}")
        lo, hi, span = self._plot_axes(surf, rect, lo, hi, fmt)
        self._x_labels(surf, rect, len(sp))
        self._polyline(surf, rect, sp, lo, span, config.COL_PRESTIGE, y_fmt=fmt,
                       cursor=self._cursor)
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
        self._x_labels(surf, rect, len(vol))
        self._polyline(surf, rect, vol, lo, span, config.COL_WARN, y_fmt=lambda v: f"{v:.1f}%",
                       cursor=self._cursor)
        self._legend(surf, rect, [(_L(f"Vol. annualisée (20 pas) = {vol[-1]:.1f}%", f"Annualized vol (20 steps) = {vol[-1]:.1f}%"), config.COL_WARN)])

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
            return self._empty(surf, rect, _L("Historique insuffisant pour le bêta.", "Insufficient history for beta."))
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
            return self._empty(surf, rect, _L("Saisissez ≥ 2 tickers (Entrée).", "Enter ≥ 2 tickers (Enter)."))
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
        self._x_labels(surf, rect, max(len(s) for _, s in series))
        legend = []
        for i, (lab, s) in enumerate(series):
            col = SERIES_COLS[i % len(SERIES_COLS)]
            self._polyline(surf, rect, s, min(allv), span, col, y_fmt=lambda v: f"{v:.1f}%")
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
