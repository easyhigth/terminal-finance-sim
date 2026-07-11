"""
app_footballfield.py — Application « Football Field » du bureau (NATIVE,
EXCLUSIVE voie M&A, cf. core/unlocks.TRACK_AFFINITY["valuation"]/["creditdesk"]
et scene_desktop_common.TRACK_APP).

Le graphique de valorisation classique des banques d'affaires : une barre
horizontale par méthode (comparables non cotés, DCF, transactions
précédentes du secteur, comparables publics décotés), avec le prix demandé
du vendeur (ask) marqué en repère vertical — pour juger d'un coup d'œil si
CE prix est dans la fourchette raisonnable ou hors des clous, plutôt que de
se fier à une seule méthode. Combine `core/ma.py` (comps+DCF déjà calculés)
avec les deux nouvelles lentilles de `core/football_field.py`.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import football_field as FF
from core import ma
from ui import fonts, widgets

TIER_LABEL = {"small": "Petite", "mid": "Moyenne", "large": "Grande"}


class FootballFieldApp(DesktopApp):
    title = "Football Field"
    icon_kind = "research"
    default_size = (1100, 640)
    min_size = (820, 500)

    def on_open(self):
        self.ticker = self._default_ticker()
        self._cache_key = None
        self._field = None
        self._target = None
        self._chip_rects = {}
        self._acquire_btn = None

    def configure(self, ticker=None, **_kwargs):
        if ticker:
            self.ticker = ticker

    def _candidates(self):
        p = self.app.gs.player
        owned = ma.owned_tickers(p)
        avail = [t["ticker"] for t in ma.available_targets(p)]
        return owned + [t for t in avail if t not in owned]

    def _default_ticker(self):
        p = self.app.gs.player
        cands = self._candidates_for(p)
        return cands[0] if cands else ""

    def _candidates_for(self, p):
        owned = ma.owned_tickers(p)
        avail = [t["ticker"] for t in ma.available_targets(p)]
        return owned + [t for t in avail if t not in owned]

    def _target_for(self, ticker):
        p = self.app.gs.player
        owned = (getattr(p, "ma_owned", None) or {}).get(ticker)
        if owned:
            return owned
        return ma.get_target(ticker)

    def _ensure_computed(self):
        market = self.app.ensure_market()
        key = (self.ticker, market.step_count)
        if key == self._cache_key:
            return
        self._cache_key = key
        self._target = self._target_for(self.ticker) if self.ticker else None
        self._field = FF.build(self._target, market) if self._target else None

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for tk, r in self._chip_rects.items():
            if r.collidepoint(pos):
                self.ticker = tk
                return True
        if self._acquire_btn and self._acquire_btn.collidepoint(pos):
            if self.desktop is not None and self.ticker:
                is_owned = self.ticker in ma.owned_tickers(self.app.gs.player)
                name = "ma" if is_owned else "ma_target"
                kwargs = {} if is_owned else {"ticker": self.ticker, "return_to": "ma"}
                self.desktop._open_scene_window(name, **kwargs)
            return True
        return False

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "FOOTBALL FIELD — valorisation multi-méthodes",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        x, y = rect.x + pad, rect.y + 32
        self._chip_rects = {}
        p = self.app.gs.player
        cands = self._candidates_for(p)
        owned_set = set(ma.owned_tickers(p))
        if not cands:
            widgets.draw_text(surf, "Aucune cible disponible pour le moment.",
                              (x, y + 20), fonts.small(), config.COL_TEXT_DIM)
            return
        for tk in cands[:14]:
            w = fonts.tiny(bold=True).size(tk)[0] + 14
            if x + w > rect.right - pad:
                break
            r = pygame.Rect(x, y, w, 20)
            self._chip_rects[tk] = r
            sel = tk == self.ticker
            col = config.COL_UP if tk in owned_set else config.COL_BORDER
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else col, r, 1, border_radius=3)
            widgets.draw_text(surf, tk, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        body = pygame.Rect(rect.x + pad, y + 28, rect.w - 2 * pad,
                           rect.bottom - pad - y - 28)
        if not self._field or not self._target:
            widgets.draw_text(surf, "Sélectionnez une cible.", (body.x, body.y + 8),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        self._draw_field(surf, body)

    def _draw_field(self, surf, body):
        t = self._target
        f = self._field
        cur = "$"
        try:
            cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        except Exception:
            pass
        head = f"{t['name']} ({t['ticker']}) — {t['sector']} · {TIER_LABEL.get(t.get('tier'), '')}"
        widgets.draw_text(surf, head, (body.x, body.y), fonts.small(bold=True), config.COL_TEXT)
        widgets.draw_text(surf, f"EBITDA {widgets.format_money(f['ebitda'], cur)} · "
                          f"dette nette {widgets.format_money(f['net_debt'], cur)}",
                          (body.x, body.y + 18), fonts.tiny(), config.COL_TEXT_DIM)

        chart = pygame.Rect(body.x, body.y + 42, body.w, body.h - 80)
        inner = widgets.draw_panel(surf, chart, "Fourchette de valorisation "
                                   "(fonds propres) par méthode", config.COL_CYAN)
        methods = f["methods"]
        all_vals = [v for m in methods for v in (m["equity_lo"], m["equity_hi"])]
        all_vals.append(f["ask_equity"])
        vmax = max(all_vals) * 1.05 if all_vals else 1.0
        vmax = vmax or 1.0

        def px(v):
            return inner.x + int(v / vmax * (inner.w - 20))

        row_h = min(46, (inner.h - 20) // max(1, len(methods)))
        yy = inner.y + 6
        for m in methods:
            widgets.draw_text(surf, m["label"], (inner.x, yy), fonts.tiny(bold=True),
                              config.COL_TEXT)
            bar_y = yy + 14
            x0, x1 = px(m["equity_lo"]), px(m["equity_hi"])
            xm = px(m["equity_median"])
            bar_r = pygame.Rect(min(x0, x1), bar_y, max(3, abs(x1 - x0)), 12)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar_r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN, bar_r, 1, border_radius=3)
            pygame.draw.line(surf, config.COL_WHITE, (xm, bar_y - 2), (xm, bar_y + 14), 2)
            widgets.draw_text(surf, widgets.format_money(m["equity_median"], cur),
                              (bar_r.right + 8, bar_y - 1), fonts.tiny(), config.COL_TEXT_DIM)
            yy += row_h
        # repère du prix demandé (ask)
        ax = px(f["ask_equity"])
        pygame.draw.line(surf, config.COL_AMBER, (ax, inner.y + 4), (ax, yy), 2)
        widgets.draw_text(surf, f"PRIX DEMANDÉ {widgets.format_money(f['ask_equity'], cur)}",
                          (min(ax + 6, inner.right - 220), inner.y + 4),
                          fonts.tiny(bold=True), config.COL_AMBER)

        foot_y = chart.bottom + 10
        is_owned = t["ticker"] in ma.owned_tickers(self.app.gs.player)
        verdict = ("dans la fourchette" if any(
            m["equity_lo"] <= f["ask_equity"] <= m["equity_hi"] for m in methods)
            else "hors fourchette — cher" if f["ask_equity"] > max(
                m["equity_hi"] for m in methods)
            else "hors fourchette — décoté")
        widgets.draw_text(surf, f"Verdict : le prix demandé est {verdict}.",
                          (body.x, foot_y), fonts.small(bold=True),
                          config.COL_AMBER if "hors" in verdict else config.COL_UP)
        self._acquire_btn = pygame.Rect(body.right - 190, foot_y - 4, 190, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._acquire_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._acquire_btn, 1, border_radius=4)
        widgets.draw_text(surf, "GÉRER →" if is_owned else "ACQUÉRIR →",
                          self._acquire_btn.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
