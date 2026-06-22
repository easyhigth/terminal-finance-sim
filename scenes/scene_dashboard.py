"""
scene_dashboard.py — Mode tableau de bord : grille de mini-widgets (sparkline +
dernier prix + variation) pour les actifs suivis (watchlist), réorganisables
(◀/▶) et cliquables (ouvre la fiche société). Complète la watchlist textuelle
existante (WATCHLIST/QuickAccessWindow) par une vue visuelle d'ensemble.
"""
import pygame

from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

COLS = 3
CARD_W, CARD_H = 280, 132
GAP = 16


class DashboardScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.search = ""
        self.msg = ""
        self._t = 0.0
        self._cards = {}        # ticker -> rect (corps de la carte, clic → fiche)
        self._move_left = {}    # ticker -> rect (◀)
        self._move_right = {}   # ticker -> rect (▶)
        self._remove_rects = {}  # ticker -> rect (✕)
        self._search_box = None
        self._add_btn = None
        self.back_btn = widgets.Button(config.back_button_rect(200),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _tickers(self):
        p = self.app.gs.player
        return [tk for tk in p.watchlist if self.market.metrics(tk) is not None]

    def _add(self):
        p = self.app.gs.player
        tk = self.search.strip().upper()
        if not tk:
            return
        resolved = self.market.resolve(tk) or tk
        if self.market.metrics(resolved) is None:
            self.msg = f"Ticker inconnu : {tk}."
        elif resolved in p.watchlist:
            self.msg = f"{resolved} est déjà au tableau de bord."
        elif len(p.watchlist) >= 10:
            self.msg = "Limite de 10 favoris atteinte. Retirez-en un avant d'en ajouter un autre."
        else:
            p.watchlist.append(resolved)
            self.market.track_company(resolved)
            self.msg = f"{resolved} ajouté."
            self.search = ""

    def _remove(self, ticker):
        p = self.app.gs.player
        if ticker in p.watchlist:
            p.watchlist.remove(ticker)

    def _move(self, ticker, delta):
        p = self.app.gs.player
        if ticker not in p.watchlist:
            return
        i = p.watchlist.index(ticker)
        j = i + delta
        if 0 <= j < len(p.watchlist):
            p.watchlist[i], p.watchlist[j] = p.watchlist[j], p.watchlist[i]

    # --------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.go(self.return_to)
                return
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._add()
                return
            if event.unicode and event.unicode.isprintable():
                self.search += event.unicode
                return

        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_box and self._search_box.collidepoint(event.pos):
                return
            if self._add_btn and self._add_btn.collidepoint(event.pos):
                self._add()
                return
            for tk, rect in self._move_left.items():
                if rect.collidepoint(event.pos):
                    self._move(tk, -1)
                    return
            for tk, rect in self._move_right.items():
                if rect.collidepoint(event.pos):
                    self._move(tk, 1)
                    return
            for tk, rect in self._remove_rects.items():
                if rect.collidepoint(event.pos):
                    self._remove(tk)
                    return
            for tk, rect in self._cards.items():
                if rect.collidepoint(event.pos):
                    self.app.scenes.go("company", ticker=tk, return_to="dashboard")
                    return

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "TABLEAU DE BORD", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Vue d'ensemble de vos actifs suivis. "
                                "Cliquez une carte pour ouvrir la fiche, ◀▶ pour réordonner.",
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)

        x0 = 40
        top = config.content_top()

        # ---- ajout rapide ----
        self._search_box = pygame.Rect(x0, top, 240, 26)
        pygame.draw.rect(surf, config.COL_PANEL, self._search_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self._search_box, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else "Ajouter un ticker…"
        scol = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, label, (self._search_box.x + 8, self._search_box.y + 5),
                          fonts.small(), scol)
        self._add_btn = pygame.Rect(self._search_box.right + 8, top, 70, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._add_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, self._add_btn, 1, border_radius=4)
        widgets.draw_text(surf, "AJOUTER", self._add_btn.center, fonts.tiny(bold=True),
                          config.COL_CYAN, align="center")
        if self.msg:
            widgets.draw_text(surf, self.msg, (self._add_btn.right + 16, top + 6),
                              fonts.tiny(), config.COL_TEXT_DIM)

        grid_top = top + 44
        self._cards = {}
        self._move_left = {}
        self._move_right = {}
        self._remove_rects = {}
        tickers = self._tickers()
        if not tickers:
            widgets.draw_text(surf, "Aucun actif suivi. Ajoutez un ticker ci-dessus pour commencer.",
                              (x0, grid_top + 10), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        for i, tk in enumerate(tickers):
            col = i % COLS
            row = i // COLS
            cx = x0 + col * (CARD_W + GAP)
            cy = grid_top + row * (CARD_H + GAP)
            self._draw_card(surf, tk, pygame.Rect(cx, cy, CARD_W, CARD_H))

        self.back_btn.draw(surf)

    def _draw_card(self, surf, ticker, rect):
        mt = self.market.metrics(ticker)
        pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_BORDER, rect, 1, border_radius=6)
        head = pygame.Rect(rect.x, rect.y, rect.w, 22)
        widgets.draw_text(surf, ticker, (head.x + 8, head.y + 3), fonts.small(bold=True),
                          config.COL_WHITE)
        widgets.draw_text(surf, widgets.fit_text(mt["name"], fonts.tiny(), 130),
                          (head.x + 70, head.y + 6), fonts.tiny(), config.COL_TEXT_DIM)

        lr = pygame.Rect(head.right - 64, head.y, 18, 18)
        rr = pygame.Rect(head.right - 44, head.y, 18, 18)
        xr = pygame.Rect(head.right - 22, head.y, 18, 18)
        for r, lbl in ((lr, "◀"), (rr, "▶"), (xr, "✕")):
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=True), config.COL_TEXT_DIM,
                              align="center")
        self._move_left[ticker] = lr
        self._move_right[ticker] = rr
        self._remove_rects[ticker] = xr

        price = mt["price"]
        chg = mt.get("change_pct")
        col = config.COL_UP if (chg or 0) >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{price:,.2f}", (rect.x + 8, rect.y + 26),
                          fonts.head(bold=True), config.COL_WHITE)
        if chg is not None:
            widgets.draw_text(surf, f"{chg:+.1f}%", (rect.x + 8, rect.y + 50),
                              fonts.small(bold=True), col)

        spark_rect = pygame.Rect(rect.x + 8, rect.y + 74, rect.w - 16, rect.h - 82)
        hist = self.market.history_of(ticker, 60)
        if len(hist) > 1:
            widgets.draw_series(surf, spark_rect, list(hist), color=col, baseline=False,
                                show_extrema=False)
        self._cards[ticker] = rect
