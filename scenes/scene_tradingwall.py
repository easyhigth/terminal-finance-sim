"""
scene_tradingwall.py — Écran « mur de trading » plein écran : mosaïque de
mini-graphes intraday (indices mondiaux + positions ouvertes du joueur),
pour surveiller le marché en direct d'un coup d'œil. Lecture pure (aucun
ordre ne peut être passé depuis cet écran) ; un clic sur une tuile ouvre la
fiche détaillée (société) ou le graphe (indice). Ouvert via la commande
WALL depuis le terminal.
"""
import pygame

from core import config
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.datawindow import DataWindow
from ui.popups import PopupMixin

_COLS = 4
_TILE_GAP = 10


class TradingWallScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.init_popups()
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._tile_rects = []   # [(rect, kind, key)] pour le clic
        self._flash = widgets.TickFlash()

    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.popups_close_top():
                return
            self.app.scenes.back(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rr, kind, key in self._tile_rects:
                if rr.collidepoint(event.pos):
                    if kind == "stock":
                        self.open_company(key)
                    else:
                        self.popups.append(DataWindow(
                            f"{key} — historique", [], [],
                            pos=self._popup_pos(), accent=config.COL_CYAN,
                            chart=list(self.market.index_history(key)),
                            resizable=True, min_size=(320, 220)))
                    return

    def update(self, dt):
        pass

    def _tiles(self):
        m = self.market
        if not m:
            return []
        day = self.app.gs.player.day
        sim_clock = self.app.sim_clock
        out = []
        for name in sorted(m.index_hist.keys()):
            hist = m.index_history(name, sim_clock, day)
            if hist and len(hist) >= 2:
                out.append(("index", name, hist))
        for tk in sorted(self.app.gs.player.portfolio.keys()):
            hist = m.track_company(tk, sim_clock, day)
            if hist and len(hist) >= 2:
                out.append(("stock", tk, hist))
        return out

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MUR DE TRADING — vue mosaïque en direct", (40, 18),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Indices mondiaux + positions ouvertes — clic = détail",
                          (42, 62), fonts.small(), config.COL_TEXT_DIM)

        tiles = self._tiles()
        self._tile_rects = []
        top = 96
        bottom = config.footer_y() - 10
        area = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, bottom - top)
        if not tiles:
            widgets.draw_text(surf, "Aucune position ouverte — les indices mondiaux s'affichent dès que le marché est chargé.",
                              (area.x, area.y), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        rows = (len(tiles) + _COLS - 1) // _COLS
        tile_w = (area.w - (_COLS - 1) * _TILE_GAP) // _COLS
        tile_h = min(140, (area.h - (rows - 1) * _TILE_GAP) // max(1, rows))
        for idx, (kind, key, hist) in enumerate(tiles):
            col, row = idx % _COLS, idx // _COLS
            x = area.x + col * (tile_w + _TILE_GAP)
            y = area.y + row * (tile_h + _TILE_GAP)
            rect = pygame.Rect(x, y, tile_w, tile_h)
            self._tile_rects.append((rect, kind, key))
            inner = widgets.draw_panel(surf, rect, key, config.COL_AMBER if kind == "stock" else config.COL_CYAN)
            last = hist[-1]
            prev = hist[-2] if len(hist) >= 2 else hist[0]
            chg = (last / hist[0] - 1.0) * 100.0 if hist[0] else 0.0
            base_c = config.COL_UP if chg >= 0 else config.COL_DOWN
            c = self._flash.tick(key, last, config.COL_UP, config.COL_DOWN, base_c)
            widgets.draw_text(surf, f"{last:,.2f}", (inner.right, inner.y), fonts.small(bold=True),
                              c, align="right")
            spark = pygame.Rect(inner.x, inner.y + 18, inner.w, inner.h - 36)
            widgets.draw_series(surf, spark, hist[-40:], base_c, baseline=False, show_extrema=False)
            widgets.draw_text(surf, f"{chg:+.2f}%", (inner.x, inner.bottom - 14), fonts.tiny(), base_c)

        self.back_btn.draw(surf)
        self.popups_draw(surf)
