"""
app_sharpe.py — Application « Sharpe Ratio » du bureau (NATIVE).

Performance ajustée au risque du panier d'actions du joueur, avec de VRAIS
chiffres (annualisés via core/quant_tools, benchmark = le VRAI indice
régional du joueur) :
- tuiles : Sharpe / rendement / volatilité annualisés, bêta et alpha de
  Jensen vs l'indice ;
- comparaison en barres : portefeuille, indice, min-variance et max-Sharpe
  (optimisés sur les actions détenues — mêmes estimateurs que la frontière) ;
- courbe de Sharpe GLISSANT (fenêtre ~1 trimestre) — voir la qualité de
  gestion évoluer dans le temps ;
- table par position (poids, rendement, vol, Sharpe individuels).

Tout est recalculé automatiquement quand le marché avance d'un pas (cache
par step_count) — pas de bouton « Calculer », l'app est toujours à jour.
"""
import pygame

from apps.base import DesktopApp
from core import config, i18n
from core import quant_tools as QT
from ui import fonts, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


PERIODS = ["3M", "1A", "3A", "5A"]     # fenêtres d'estimation proposées
RF_MIN, RF_MAX, RF_STEP = 0.0, 0.10, 0.005


class SharpeApp(DesktopApp):
    title = "Sharpe Ratio"
    icon_kind = "graph"
    default_size = (980, 620)
    min_size = (700, 460)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.period = "1A"
        self.rf = 0.02
        self._cache_key = None
        self._res = None
        self._period_rects = {}
        self._rf_minus = None
        self._rf_plus = None
        self._frontier_btn = None
        self._last_rect = pygame.Rect(0, 0, 1, 1)

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        key = (self.market.step_count, self.period, round(self.rf, 4),
               len(self.app.gs.player.portfolio))
        if key == self._cache_key:
            return
        self._cache_key = key
        self._res = self._compute()

    def _compute(self):
        p = self.app.gs.player
        m = self.market
        steps = QT.PERIOD_STEPS[self.period]
        port_r, tickers = QT.portfolio_step_returns(p, m, steps)
        if len(port_r) < QT.MIN_POINTS:
            return None
        idx_name = QT.main_index(m, p)
        bench_r = QT.index_returns(m, idx_name, steps)
        res = {
            "tickers": tickers,
            "port": {"sharpe": QT.sharpe(port_r, self.rf),
                     "ret": QT.ann_return(port_r), "vol": QT.ann_vol(port_r)},
            "rolling": QT.rolling_sharpe(port_r, window=18, rf_annual=self.rf),
            "index_name": idx_name,
            "bench": None, "beta": 0.0, "alpha": 0.0,
            "min_var": None, "max_sharpe": None,
            "rows": [],
        }
        if len(bench_r) >= QT.MIN_POINTS:
            b_ret, b_vol = QT.ann_return(bench_r), QT.ann_vol(bench_r)
            res["bench"] = {"sharpe": QT.sharpe(bench_r, self.rf),
                            "ret": b_ret, "vol": b_vol}
            res["beta"] = QT.beta(port_r, bench_r)
            # alpha de Jensen : rendement au-delà de ce que le bêta explique
            res["alpha"] = (res["port"]["ret"] - self.rf
                            - res["beta"] * (b_ret - self.rf))
        fr = QT.frontier(m, tickers, n_points=25, lookback=steps,
                         rf_annual=self.rf)
        if fr:
            for label, i in (("min_var", fr["i_min_var"]),
                             ("max_sharpe", fr["i_max_sharpe"])):
                ret, vol, sh = QT.point_stats(fr["weights"][i], fr["mean"], fr["cov"],
                                              self.rf)
                res[label] = {"sharpe": sh, "ret": ret, "vol": vol}
        # table par position (poids par valeur longue)
        w, _tot = QT.current_weights(p, m, tickers)
        for tk, wi in zip(tickers, w):
            r = QT.returns_of(m, tk, steps)
            if len(r) < QT.MIN_POINTS:
                continue
            res["rows"].append({"ticker": tk, "weight": wi,
                                "ret": QT.ann_return(r), "vol": QT.ann_vol(r),
                                "sharpe": QT.sharpe(r, self.rf)})
        res["rows"].sort(key=lambda x: x["sharpe"], reverse=True)
        return res

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for period, r in self._period_rects.items():
            if r.collidepoint(pos):
                self.period = period
                return True
        if self._rf_minus and self._rf_minus.collidepoint(pos):
            self.rf = max(RF_MIN, round(self.rf - RF_STEP, 4))
            return True
        if self._rf_plus and self._rf_plus.collidepoint(pos):
            self.rf = min(RF_MAX, round(self.rf + RF_STEP, 4))
            return True
        if self._frontier_btn and self._frontier_btn.collidepoint(pos):
            if self.desktop is not None:
                self.desktop._open_scene_window("frontier")
            return True
        return False

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._last_rect = rect
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, _L("SHARPE RATIO — PERFORMANCE AJUSTÉE AU RISQUE", "SHARPE RATIO — RISK-ADJUSTED PERFORMANCE"),
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        # contrôles : période + taux sans risque + lien frontière
        x = rect.x + pad
        y = rect.y + 34
        self._period_rects = {}
        for period in PERIODS:
            w = fonts.tiny(bold=True).size(period)[0] + 16
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
        x += 12
        _rf_lbl = _L(f"Taux sans risque {self.rf * 100:.1f}%", f"Risk-free rate {self.rf * 100:.1f}%")
        widgets.draw_text(surf, _rf_lbl,
                          (x, y + 3), fonts.tiny(), config.COL_TEXT_DIM)
        x += fonts.tiny().size(_rf_lbl)[0] + 8
        self._rf_minus = pygame.Rect(x, y, 20, 20)
        self._rf_plus = pygame.Rect(x + 24, y, 20, 20)
        for r, sym in ((self._rf_minus, "−"), (self._rf_plus, "+")):
            pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, sym, r.center, fonts.small(bold=True),
                              config.COL_TEXT, align="center")
        _fb_lbl = _L("→ FRONTIÈRE", "→ FRONTIER")
        fb_w = fonts.tiny(bold=True).size(_fb_lbl)[0] + 16
        self._frontier_btn = pygame.Rect(rect.right - pad - fb_w, y, fb_w, 20)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._frontier_btn, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, self._frontier_btn, 1, border_radius=3)
        widgets.draw_text(surf, _fb_lbl, self._frontier_btn.center,
                          fonts.tiny(bold=True), config.COL_CYAN, align="center")

        top = y + 30
        if self._res is None:
            widgets.draw_text(surf, _L("Détenez au moins une action (avec assez "
                              "d'historique) pour mesurer le Sharpe du portefeuille.",
                              "Hold at least one stock (with enough "
                              "history) to measure the portfolio Sharpe."),
                              (rect.x + pad, top + 10), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, _L("Ouvrez Trading (icône du bureau) pour "
                              "construire un panier, puis revenez ici.",
                              "Open Trading (desktop icon) to "
                              "build a basket, then come back here."),
                              (rect.x + pad, top + 32), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        res = self._res
        # tuiles
        tiles = [
            (_L("SHARPE PORTEF.", "PORTF. SHARPE"), f"{res['port']['sharpe']:+.2f}",
             self._sharpe_color(res["port"]["sharpe"])),
            (_L("REND. ANN.", "ANN. RETURN"), f"{res['port']['ret'] * 100:+.1f}%",
             config.COL_UP if res["port"]["ret"] >= 0 else config.COL_DOWN),
            (_L("VOL. ANN.", "ANN. VOL"), f"{res['port']['vol'] * 100:.1f}%", config.COL_TEXT),
            (_L("BÊTA vs INDICE", "BETA vs INDEX"), f"{res['beta']:.2f}", config.COL_TEXT),
            (_L("ALPHA (JENSEN)", "ALPHA (JENSEN)"), f"{res['alpha'] * 100:+.1f}%",
             config.COL_UP if res["alpha"] >= 0 else config.COL_DOWN),
        ]
        tw = min(180, (rect.w - 2 * pad - (len(tiles) - 1) * 8) // len(tiles))
        tx = rect.x + pad
        for label, val, col in tiles:
            tr = pygame.Rect(tx, top, tw, 52)
            pygame.draw.rect(surf, config.COL_PANEL, tr, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, tr, 1, border_radius=4)
            widgets.draw_text(surf, label, (tr.x + 8, tr.y + 6), fonts.tiny(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (tr.x + 8, tr.y + 22),
                              fonts.head(bold=True), col)
            tx += tw + 8

        body_top = top + 62
        col_w = (rect.w - 2 * pad - 12) // 2
        left = pygame.Rect(rect.x + pad, body_top, col_w,
                           rect.bottom - pad - body_top)
        right = pygame.Rect(left.right + 12, body_top, col_w, left.h)
        h_half = (left.h - 10) // 2
        self._draw_bars(surf, pygame.Rect(left.x, left.y, left.w, h_half), res)
        self._draw_rolling(surf, pygame.Rect(left.x, left.y + h_half + 10,
                                             left.w, h_half), res)
        self._draw_table(surf, right, res)

    def _sharpe_color(self, s):
        if s >= 1.0:
            return config.COL_UP
        if s >= 0.3:
            return config.COL_AMBER
        return config.COL_DOWN

    def _draw_bars(self, surf, rect, res):
        inner = widgets.draw_panel(surf, rect, _L("Comparaison (Sharpe annualisé)", "Comparison (annualized Sharpe)"),
                                   config.COL_CYAN)
        data = [(_L("Portf.", "Portf."), res["port"]["sharpe"], config.COL_AMBER)]
        if res["bench"]:
            data.append((res["index_name"], res["bench"]["sharpe"], config.COL_TEXT_DIM))
        if res["min_var"]:
            data.append((_L("Min var", "Min var"), res["min_var"]["sharpe"], config.COL_CYAN))
        if res["max_sharpe"]:
            data.append(("Max Sharpe", res["max_sharpe"]["sharpe"], config.COL_UP))
        if not data:
            return
        vals = [v for _l, v, _c in data]
        lo, hi = min(min(vals), 0.0), max(max(vals), 0.0)
        rng = (hi - lo) or 1.0
        plot = inner.inflate(-8, -30)
        plot.move_ip(0, 4)
        plot.height -= 14  # réserve la place sous les barres pour les étiquettes
        zero_y = plot.bottom - int((0.0 - lo) / rng * plot.h)
        pygame.draw.line(surf, config.COL_BORDER, (plot.x, zero_y),
                         (plot.right, zero_y))
        bw = max(24, (plot.w - (len(data) + 1) * 10) // len(data))
        x = plot.x + 10
        for label, v, col in data:
            h = int(abs(v - 0.0) / rng * plot.h)
            top = zero_y - h if v >= 0 else zero_y
            pygame.draw.rect(surf, col, pygame.Rect(x, top, bw, max(2, h)),
                             border_radius=2)
            widgets.draw_text(surf, f"{v:+.2f}", (x + bw // 2, top - 14 if v >= 0
                              else top + h + 2), fonts.tiny(bold=True), col,
                              align="center")
            widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), bw + 8),
                              (x + bw // 2, inner.bottom - 12), fonts.tiny(),
                              config.COL_TEXT_DIM, align="center")
            x += bw + 10

    def _draw_rolling(self, surf, rect, res):
        inner = widgets.draw_panel(surf, rect,
                                   _L("Sharpe glissant (fenêtre ~1 trimestre)", "Rolling Sharpe (~1 quarter window)"),
                                   config.COL_UP)
        series = res["rolling"]
        if len(series) < 2:
            widgets.draw_text(surf, _L("Historique insuffisant pour la fenêtre glissante.", "Insufficient history for the rolling window."),
                              (inner.x, inner.y + 6), fonts.tiny(), config.COL_TEXT_DIM)
            return
        lo, hi = float(min(series.min(), 0.0)), float(max(series.max(), 0.0))
        rng = (hi - lo) or 1.0
        plot = inner.inflate(-8, -16)
        pts = []
        for i, v in enumerate(series):
            px = plot.x + int(i / max(1, len(series) - 1) * plot.w)
            py = plot.bottom - int((v - lo) / rng * plot.h)
            pts.append((px, py))
        zero_y = plot.bottom - int((0.0 - lo) / rng * plot.h)
        pygame.draw.line(surf, config.COL_BORDER, (plot.x, zero_y),
                         (plot.right, zero_y))
        pygame.draw.aalines(surf, config.COL_UP, False, pts)
        last = float(series[-1])
        widgets.draw_text(surf, f"{last:+.2f}", (pts[-1][0] - 30, pts[-1][1] - 14),
                          fonts.tiny(bold=True),
                          config.COL_UP if last >= 0 else config.COL_DOWN)

    def _draw_table(self, surf, rect, res):
        inner = widgets.draw_panel(surf, rect, _L("Par position", "Per position"), config.COL_AMBER)
        cols = [("TICKER", 0), (_L("POIDS", "WEIGHT"), int(inner.w * 0.30)),
                (_L("REND.", "RET."), int(inner.w * 0.48)), ("VOL", int(inner.w * 0.66)),
                ("SHARPE", int(inner.w * 0.84))]
        for lbl, dx in cols:
            widgets.draw_text(surf, lbl, (inner.x + dx, inner.y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        y = inner.y + 18
        for row in res["rows"]:
            if y > inner.bottom - 14:
                break
            widgets.draw_text(surf, row["ticker"], (inner.x, y),
                              fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{row['weight'] * 100:.0f}%",
                              (inner.x + cols[1][1], y), fonts.small(), config.COL_TEXT)
            rc = config.COL_UP if row["ret"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{row['ret'] * 100:+.0f}%",
                              (inner.x + cols[2][1], y), fonts.small(), rc)
            widgets.draw_text(surf, f"{row['vol'] * 100:.0f}%",
                              (inner.x + cols[3][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{row['sharpe']:+.2f}",
                              (inner.x + cols[4][1], y), fonts.small(bold=True),
                              self._sharpe_color(row["sharpe"]))
            y += 19
        widgets.draw_text(surf,
                          _L("Sharpe = (rendement − taux sans risque) / volatilité, annualisé.", "Sharpe = (return − risk-free rate) / volatility, annualized."),
                          (inner.x, inner.bottom - 12), fonts.tiny(), config.COL_TEXT_DIM)
