"""
app_watchlist.py — Application « Watchlist » du bureau.

Mini-Bloomberg des valeurs suivies (`player.watchlist`, alimentée depuis la
commande WATCHLIST du terminal ET l'étoile ✶ de l'app Recherche) : cours et
variation du dernier pas EN DIRECT, sans ouvrir chaque fiche. Cliquer une
ligne ouvre l'app Trading pré-filtrée (lien inter-apps, cf. app_research) ;
« × » retire la valeur de la watchlist. Surveillance ambiante pendant que le
temps passe et qu'on prépare un ordre ailleurs.

Deux modes d'affichage : LISTE (compacte) et GRILLE (tuiles avec sparkline en
direct — reprend l'idée de l'ex-scène « Tableau de bord », scene_dashboard,
désormais retirée : une seule maison pour la watchlist).
"""
import pygame

from apps.base import DesktopApp
from core import config
from ui import fonts, widgets

ROW_H = 26
TILE_W, TILE_H = 180, 92
TILE_GAP = 8


class WatchlistApp(DesktopApp):
    title = "Watchlist"
    icon_kind = "star"
    default_size = (420, 460)
    min_size = (300, 260)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.view = "list"         # "list" ou "grid" (tuiles + sparklines)
        self._view_rects = {}      # mode -> Rect (boutons LISTE/GRILLE)
        self._row_rects = {}       # ticker -> Rect (ligne/tuile cliquable → Trading)
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
            for mode, r in self._view_rects.items():
                if r.collidepoint(event.pos):
                    self.view = mode
                    return True
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
        # bascule LISTE / GRILLE (la grille reprend l'ex-« Tableau de bord »)
        self._view_rects = {}
        mp = pygame.mouse.get_pos()
        bx = rect.right - pad - 62
        for mode, label in (("grid", "GRILLE"), ("list", "LISTE")):
            r = pygame.Rect(bx, rect.y + pad - 2, 58, 20)
            self._view_rects[mode] = r
            active = (self.view == mode)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (active or r.collidepoint(mp))
                             else config.COL_PANEL, r, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER,
                             r, 1, border_radius=4)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            bx -= 62
        area = pygame.Rect(rect.x + pad, rect.y + pad + 24, rect.w - 2 * pad,
                           rect.bottom - rect.y - pad * 2 - 24)
        pygame.draw.rect(surf, config.COL_BG, area)
        pygame.draw.rect(surf, config.COL_BORDER, area, 1)
        self._list_rect = area
        self._row_rects, self._del_rects = {}, {}
        if not wl:
            widgets.draw_text(surf, "Aucune valeur suivie.", (area.x + 10, area.y + 12),
                              fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, "Ajoutez-en avec l'étoile ✶ de l'app Recherche,",
                              (area.x + 10, area.y + 34), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, "ou la commande WATCHLIST du terminal.",
                              (area.x + 10, area.y + 48), fonts.tiny(), config.COL_TEXT_DIM)
            return
        if self.view == "grid":
            self._draw_grid(surf, area, wl, mp)
            return
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

    def _draw_grid(self, surf, area, wl, mp):
        """Mode GRILLE : une tuile par valeur (ticker, cours en direct avec
        flash, variation, sparkline) — vue d'ensemble visuelle, cliquable vers
        Trading comme les lignes de la liste."""
        cols = max(1, (area.w - TILE_GAP) // (TILE_W + TILE_GAP))
        prev_clip = surf.get_clip()
        surf.set_clip(area)
        for idx, tk in enumerate(wl):
            i = self.market.ticker_idx.get(tk)
            if i is None:
                continue
            col, row = idx % cols, idx // cols
            x = area.x + TILE_GAP + col * (TILE_W + TILE_GAP)
            y = area.y + TILE_GAP + row * (TILE_H + TILE_GAP)
            r = pygame.Rect(x, y, TILE_W, TILE_H)
            if r.top > area.bottom:
                break
            self._row_rects[tk] = r
            hov = r.collidepoint(mp)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, r,
                             border_radius=6)
            hist = self._live_hist(tk)
            price = hist[-1] if hist else self.market.price_of(tk)
            chg = self._last_change_pct(hist)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            pygame.draw.rect(surf, ccol if hov else config.COL_BORDER, r, 1, border_radius=6)
            flash_col = self._flash.tick(tk, price, config.COL_UP, config.COL_DOWN,
                                         config.COL_WHITE)
            widgets.draw_text(surf, tk, (r.x + 8, r.y + 6), fonts.small(bold=True),
                              config.COL_AMBER)
            widgets.draw_text(surf, f"{chg:+.2f}%", (r.right - 8, r.y + 6),
                              fonts.tiny(bold=True), ccol, align="right")
            widgets.draw_text(surf, f"{price:,.2f}", (r.x + 8, r.y + 24), fonts.small(),
                              flash_col)
            spark = pygame.Rect(r.x + 8, r.bottom - 26, r.w - 16, 18)
            if len(hist) >= 2:
                widgets.draw_series(surf, spark, hist, ccol, baseline=False,
                                    show_extrema=False, y_fmt=None)
            dr = pygame.Rect(r.right - 18, r.bottom - TILE_H + 24, 14, 14)
            self._del_rects[tk] = dr
            dhov = dr.collidepoint(mp)
            pygame.draw.line(surf, config.COL_DOWN if dhov else config.COL_TEXT_DIM,
                             (dr.x + 3, dr.y + 3), (dr.right - 3, dr.bottom - 3), 2)
            pygame.draw.line(surf, config.COL_DOWN if dhov else config.COL_TEXT_DIM,
                             (dr.x + 3, dr.bottom - 3), (dr.right - 3, dr.y + 3), 2)
        surf.set_clip(prev_clip)
