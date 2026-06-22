"""
scene_portfolio_unified.py — Portefeuille unifié : une seule table agrégeant
toutes les positions du joueur (actions, obligations, commodities, crypto,
ETF) avec valeur de marché et P&L latent par ligne, triable par colonne.
Ne couvre pas les produits structurés/titrisés/couvertures/options (formes de
données trop hétérogènes pour une ligne de table simple) ; ces classes restent
consultables depuis leurs propres écrans (menu PLUS).
"""
import pygame

from core import bonds, commodities, crypto, etfs, portfolio_views
from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 26
_CLASS_LABEL = {
    "equity": "Action", "bond": "Obligation", "commodity": "Commodity",
    "crypto": "Crypto", "etf": "ETF",
}
_CLASS_SCENE = {
    "bond": "bonds", "commodity": "commodities", "crypto": "crypto", "etf": "etfs",
}


class PortfolioUnifiedScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.sort_key = "value_abs"
        self.sort_rev = True
        self.scroll = 0
        self._max_scroll = 0
        self._row_rects = []     # [(Rect, row)] lignes visibles
        self._sort_rects = {}    # key -> Rect (en-têtes cliquables)
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _rows(self):
        p = self.app.gs.player
        m = self.market
        out = []
        for h in portfolio_views.holdings(p, m):
            out.append({"cls": "equity", "id": h["ticker"], "name": h["ticker"],
                        "qty": h["shares"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in bonds.holdings(p, m):
            out.append({"cls": "bond", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in commodities.holdings(p, m):
            out.append({"cls": "commodity", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in crypto.holdings(p, m):
            out.append({"cls": "crypto", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in etfs.holdings(p, m):
            out.append({"cls": "etf", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        out.sort(key=lambda r: r[self.sort_key] if isinstance(r[self.sort_key], (int, float))
                  else str(r[self.sort_key]).lower(), reverse=self.sort_rev)
        return out

    def _open_row(self, row):
        if row["cls"] == "equity":
            self.app.scenes.go("company", ticker=row["id"], return_to="portfolio_unified")
        else:
            self.app.scenes.go(_CLASS_SCENE[row["cls"]], return_to="portfolio_unified")

    def _click_sort(self, key):
        if self.sort_key == key:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_key = key
            self.sort_rev = True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            self.scroll = max(0, self.scroll - 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            self.scroll = min(self._max_scroll, self.scroll + 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self._sort_rects.items():
                if rect.collidepoint(event.pos):
                    self._click_sort(key)
                    return
            for rect, row in self._row_rects:
                if rect.collidepoint(event.pos):
                    self._open_row(row)
                    return

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "PORTEFEUILLE UNIFIÉ", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Toutes vos positions (actions, obligations, commodities, "
                                "crypto, ETF) dans une table triable. Clic colonne = trier, "
                                "clic ligne = ouvrir.",
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)

        top = config.content_top()
        panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - top)
        inner = widgets.draw_panel(surf, panel, "Positions", config.COL_CYAN)

        rows = self._rows()
        cols = [("cls", "Classe", 110), ("id", "Actif", 130), ("qty", "Qté", 110),
                ("avg", "PM", 110), ("price", "Cours", 110), ("value", "Valeur", 140),
                ("pnl", "P&L latent", 140)]
        head_y = inner.y
        self._sort_rects = {}
        x = inner.x
        for key, label, w in cols:
            arrow = ""
            if self.sort_key == key or (key == "value" and self.sort_key == "value_abs"):
                arrow = " ▾" if self.sort_rev else " ▴"
            col = config.COL_CYAN if (self.sort_key == key or
                                      (key == "value" and self.sort_key == "value_abs")) else config.COL_TEXT_DIM
            sort_target = "value_abs" if key == "value" else key
            rect = pygame.Rect(x, head_y - 2, w, 18)
            self._sort_rects[sort_target] = rect
            widgets.draw_text(surf, label + arrow, (x, head_y), fonts.tiny(bold=True), col)
            x += w

        list_top = head_y + 22
        list_area = pygame.Rect(inner.x, list_top, inner.w, inner.bottom - list_top)
        if not rows:
            widgets.draw_text(surf, "Aucune position. Achetez des actifs depuis le marché ou la boutique.",
                              (inner.x, list_top + 6), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        self._row_rects = []
        for row in rows:
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H - 2)
                self._row_rects.append((rect, row))
                if rect.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=3)
                x = inner.x
                widgets.draw_text(surf, _CLASS_LABEL[row["cls"]], (x, y), fonts.small(), config.COL_TEXT_DIM)
                x += 110
                widgets.draw_text(surf, widgets.fit_text(str(row["id"]), fonts.small(bold=True), 124),
                                  (x, y), fonts.small(bold=True), config.COL_AMBER)
                x += 130
                widgets.draw_text(surf, f"{row['qty']:,.2f}", (x, y), fonts.small(), config.COL_TEXT)
                x += 110
                widgets.draw_text(surf, f"{row['avg']:,.2f}", (x, y), fonts.small(), config.COL_TEXT)
                x += 110
                widgets.draw_text(surf, f"{row['price']:,.2f}", (x, y), fonts.small(), config.COL_TEXT)
                x += 110
                widgets.draw_text(surf, f"{row['value']:,.0f}", (x, y), fonts.small(bold=True), config.COL_WHITE)
                x += 140
                pcol = config.COL_UP if row["pnl"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{row['pnl']:+,.0f}", (x, y), fonts.small(bold=True), pcol)
            y += ROW_H
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - list_area.y
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)
