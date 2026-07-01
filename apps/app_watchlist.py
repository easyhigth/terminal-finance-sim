"""
app_watchlist.py — Application « Watchlist » du bureau.

Mini-Bloomberg des valeurs suivies (`player.watchlist`, alimentée depuis la
commande WATCHLIST du terminal ET l'étoile ★ de l'app Recherche) : cours et
variation du dernier pas EN DIRECT, sans ouvrir chaque fiche. Cliquer une
ligne ouvre l'app Trading pré-filtrée (lien inter-apps, cf. app_research) ;
« × » retire la valeur de la watchlist. Surveillance ambiante pendant que le
temps passe et qu'on prépare un ordre ailleurs.
"""
import pygame

from apps.base import DesktopApp
from core import config
from ui import fonts, widgets

ROW_H = 26


class WatchlistApp(DesktopApp):
    title = "Watchlist"
    icon_kind = "star"
    default_size = (420, 460)
    min_size = (300, 260)

    def on_open(self):
        self.market = self.app.ensure_market()
        self._row_rects = {}       # ticker -> Rect (ligne cliquable → Trading)
        self._del_rects = {}       # ticker -> Rect (× retirer)
        self._list_rect = None
        self._flash = widgets.TickFlash()   # flash vert/rouge du cours en direct

    def _live_hist(self, tk):
        """Historique + point animé en direct (cf. core/intraday.py) — bouge
        par petits paliers même entre deux pas du moteur de marché."""
        return self.market.history_of(tk, 18, sim_clock=self.app.sim_clock,
                                      day=self.app.gs.player.day)

    def _last_change_pct(self, hist):
        if len(hist) >= 2 and hist[-2]:
            return (hist[-1] / hist[-2] - 1.0) * 100.0
        return 0.0

    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tk, r in self._del_rects.items():
                if r.collidepoint(event.pos):
                    if tk in self.app.gs.player.watchlist:
                        self.app.gs.player.watchlist.remove(tk)
                    return True
            for tk, r in self._row_rects.items():
                if r.collidepoint(event.pos):
                    if self.desktop is not None:
                        self.desktop.open_trading(tk)
                    return True
        return False

    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        pad = 10
        wl = list(self.app.gs.player.watchlist)
        widgets.draw_text(surf, f"VALEURS SUIVIES ({len(wl)}/10)", (rect.x + pad, rect.y + pad),
                          fonts.small(bold=True), config.COL_AMBER)
        area = pygame.Rect(rect.x + pad, rect.y + pad + 24, rect.w - 2 * pad,
                           rect.bottom - rect.y - pad * 2 - 24)
        pygame.draw.rect(surf, config.COL_BG, area)
        pygame.draw.rect(surf, config.COL_BORDER, area, 1)
        self._list_rect = area
        self._row_rects, self._del_rects = {}, {}
        if not wl:
            widgets.draw_text(surf, "Aucune valeur suivie.", (area.x + 10, area.y + 12),
                              fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, "Ajoutez-en avec l'étoile ★ de l'app Recherche,",
                              (area.x + 10, area.y + 34), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, "ou la commande WATCHLIST du terminal.",
                              (area.x + 10, area.y + 48), fonts.tiny(), config.COL_TEXT_DIM)
            return
        mp = pygame.mouse.get_pos()
        y = area.y + 4
        for tk in wl:
            i = self.market.ticker_idx.get(tk)
            if i is None:
                continue
            r = pygame.Rect(area.x + 2, y, area.w - 4, ROW_H - 2)
            self._row_rects[tk] = r
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r)
            hist = self._live_hist(tk)
            price = hist[-1] if hist else self.market.price_of(tk)
            chg = self._last_change_pct(hist)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            flash_col = self._flash.tick(tk, price, config.COL_UP, config.COL_DOWN, config.COL_WHITE)
            widgets.draw_text(surf, tk, (r.x + 6, r.y + 4), fonts.small(bold=True), config.COL_AMBER)
            name = self.market.companies[i]["name"]
            widgets.draw_text(surf, widgets.fit_text(name, fonts.tiny(), r.w - 210),
                              (r.x + 68, r.y + 5), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{price:,.2f}", (r.right - 118, r.y + 4), fonts.small(),
                              flash_col, align="right")
            widgets.draw_text(surf, f"{chg:+.2f}%", (r.right - 44, r.y + 4), fonts.small(bold=True),
                              ccol, align="right")
            dr = pygame.Rect(r.right - 20, r.y + 3, 16, ROW_H - 8)
            self._del_rects[tk] = dr
            hov = dr.collidepoint(mp)
            pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                             (dr.x + 3, dr.y + 3), (dr.right - 3, dr.bottom - 3), 2)
            pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                             (dr.x + 3, dr.bottom - 3), (dr.right - 3, dr.y + 3), 2)
            y += ROW_H
