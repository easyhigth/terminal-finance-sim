"""
app_backtester.py — Application « Backtester » du bureau (NATIVE).

Rejoue une règle de trading MÉCANIQUE (core/backtester.py) sur l'historique
RÉEL d'un titre du roster — préhistoire de carrière (5 ans) incluse — pour
juger une stratégie AVANT de la jouer avec du cash réel : total return vs
buy & hold, Sharpe annualisé, drawdown maximal, exposition au marché.

Sélection du titre : chips (positions détenues + watchlist) ou recherche
libre (Ctrl+V supporté), comme les autres outils quant du bureau
(Sharpe/Z-Score). Le résultat se recalcule automatiquement à chaque
changement de stratégie/paramètre/pas de marché (nouvel historique).
"""
import pygame

from apps.base import DesktopApp
from core import backtester as BT
from core import clipboard, config, i18n
from ui import fonts, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


STRATEGY_ORDER = ["buy_hold", "sma_crossover", "momentum", "mean_reversion"]


class BacktesterApp(DesktopApp):
    title = "Backtester"
    icon_kind = "graph"
    default_size = (960, 600)
    min_size = (700, 460)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.ticker = self._default_ticker()
        self.strategy = "sma_crossover"
        self.search = ""
        self._search_active = False
        self.msg = ""
        self._cache_key = None
        self._res = None
        self._chip_rects = {}
        self._strategy_rects = {}
        self._search_rect = None

    def _default_ticker(self):
        p = self.app.gs.player
        for tk, pos in p.portfolio.items():
            if pos["shares"] > 0 and tk in self.market.ticker_idx:
                return tk
        wl = [tk for tk in getattr(p, "watchlist", []) if tk in self.market.ticker_idx]
        if wl:
            return wl[0]
        top = self.market.top_companies(n=1)
        return top[0]["ticker"] if top else None

    def _ensure_computed(self):
        key = (self.market.step_count, self.ticker, self.strategy)
        if key == self._cache_key:
            return
        self._cache_key = key
        self._res = None
        if not self.ticker or self.ticker not in self.market.ticker_idx:
            return
        self._res = BT.backtest_ticker(self.market, self.ticker, strategy=self.strategy)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tk, r in self._chip_rects.items():
                if r.collidepoint(event.pos):
                    self.ticker = tk
                    self.search = ""
                    self._search_active = False
                    self.msg = ""
                    return True
            for strat, r in self._strategy_rects.items():
                if r.collidepoint(event.pos):
                    self.strategy = strat
                    return True
            if self._search_rect and self._search_rect.collidepoint(event.pos):
                self._search_active = True
                return True
            self._search_active = False
        elif event.type == pygame.KEYDOWN and self._search_active:
            if event.key == pygame.K_RETURN:
                tk = self.search.strip().upper()
                if tk in self.market.ticker_idx:
                    self.ticker = tk
                    self.msg = ""
                else:
                    self.msg = _L(f"Ticker inconnu : {tk}.", f"Unknown ticker: {tk}.")
                self.search = ""
                self._search_active = False
                return True
            if event.key == pygame.K_ESCAPE:
                self._search_active = False
                self.search = ""
                return True
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return True
            if clipboard.is_paste_shortcut(event):
                self.search = (self.search + clipboard.paste()).replace("\n", " ")[:16]
                return True
            if event.unicode and event.unicode.isprintable():
                self.search = (self.search + event.unicode).upper()[:16]
                return True
        return False

    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, _L("BACKTESTER — STRATÉGIES SUR L'HISTORIQUE RÉEL", "BACKTESTER — STRATEGIES ON REAL HISTORY"),
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
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
        label = self.search if (self.search or self._search_active) else _L("Autre ticker…", "Other ticker…")
        col = config.COL_TEXT if (self.search or self._search_active) else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), 148),
                          (self._search_rect.x + 6, self._search_rect.y + 4),
                          fonts.tiny(), col)

        y += 26
        x = rect.x + pad
        self._strategy_rects = {}
        for strat in STRATEGY_ORDER:
            lbl = BT.STRATEGY_LABELS[strat]
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            self._strategy_rects[strat] = r
            sel = strat == self.strategy
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        if self.msg:
            widgets.draw_text(surf, self.msg, (rect.x + pad, y + 24),
                              fonts.tiny(), config.COL_DOWN)

        top = y + 30
        if self._res is None:
            widgets.draw_text(surf, _L("Pas assez d'historique pour ce titre.", "Not enough history for this security."),
                              (rect.x + pad, top + 8), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        res = self._res
        mt = self.market.metrics(self.ticker)
        name = mt["name"] if mt else ""
        widgets.draw_text(surf, f"{self.ticker} — {name}", (rect.x + pad, top),
                          fonts.small(bold=True), config.COL_TEXT)

        stat_y = top + 22
        tot_col = config.COL_UP if res["total_return"] >= 0 else config.COL_DOWN
        bh_col = config.COL_UP if res["benchmark_return"] >= 0 else config.COL_DOWN
        stats = [
            (_L("Stratégie", "Strategy"), f"{res['total_return'] * 100:+.1f}%", tot_col),
            ("Buy & hold", f"{res['benchmark_return'] * 100:+.1f}%", bh_col),
            ("Sharpe", f"{res['sharpe']:.2f}", config.COL_CYAN),
            (_L("Drawdown max", "Max drawdown"), f"{res['max_drawdown'] * 100:.1f}%", config.COL_DOWN),
            (_L("Exposition", "Exposure"), f"{res['exposure'] * 100:.0f}%", config.COL_TEXT_DIM),
        ]
        sx = rect.x + pad
        for label, val, col in stats:
            widgets.draw_text(surf, label, (sx, stat_y), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (sx, stat_y + 14), fonts.small(bold=True), col)
            sx += 140

        chart_top = stat_y + 40
        chart = pygame.Rect(rect.x + pad, chart_top, rect.w - 2 * pad,
                            rect.bottom - pad - chart_top)
        self._draw_equity(surf, chart, res["equity"])

    def _draw_equity(self, surf, rect, equity):
        inner = widgets.draw_panel(surf, rect,
                                   _L("Courbe de capital (base 1.0, stratégie vs marché)", "Equity curve (base 1.0, strategy vs market)"),
                                   config.COL_CYAN)
        if inner.h < 40 or len(equity) < 2:
            return
        lo = min(equity + [1.0])
        hi = max(equity + [1.0])
        rng = (hi - lo) or 1.0
        plot = inner.inflate(-8, -16)

        def py(v):
            return plot.bottom - int((v - lo) / rng * plot.h)

        base_y = py(1.0)
        pygame.draw.line(surf, config.COL_BORDER, (plot.x, base_y), (plot.right, base_y))
        pts = [(plot.x + int(i / max(1, len(equity) - 1) * plot.w), py(float(v)))
               for i, v in enumerate(equity)]
        col = config.COL_UP if equity[-1] >= 1.0 else config.COL_DOWN
        pygame.draw.aalines(surf, col, False, pts)
        pygame.draw.circle(surf, config.COL_WHITE, pts[-1], 3)
