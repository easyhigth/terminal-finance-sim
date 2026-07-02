"""
cheatpanel.py — Panneau de triche déplaçable (mode test, main_cheat.py).

Boutons pour ajuster cash/réputation/grade et forcer l'examen sans
remplir les critères de promotion, pour tester rapidement les missions et
examens de chaque niveau. N'est instancié par scene_terminal.py que si
`app.cheats` est actif (jamais en jeu normal).
"""
import pygame

from core import config
from ui import fonts, widgets

TITLE_H = 22
PADX = 10


class CheatPanel:
    def __init__(self, app, pos=(890, 130)):
        self.app = app
        self.closed = False
        self.dragging = False
        self._drag_off = (0, 0)
        self._btn_rects = {}
        self.msg = ""
        self.rect = pygame.Rect(pos[0], pos[1], 250, 300)

    def _title_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, TITLE_H)

    def _close_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H, self.rect.y, TITLE_H, TITLE_H)

    def _press(self, key):
        p = self.app.gs.player
        if key.startswith("cash:"):
            amt = float(key.split(":")[1])
            p.cash += amt
            self.msg = f"Trésorerie +{amt:,.0f}".replace(",", " ")
        elif key.startswith("rep:"):
            amt = int(key.split(":")[1])
            p.reputation = max(0, min(100, p.reputation + amt))
            self.msg = f"Réputation → {p.reputation}/100"
        elif key.startswith("repset:"):
            p.reputation = int(key.split(":")[1])
            self.msg = f"Réputation → {p.reputation}/100"
        elif key.startswith("grade:"):
            if key == "grade:-1":
                gi = max(0, p.grade_index - 1)
            elif key == "grade:+1":
                gi = min(len(config.GRADES) - 1, p.grade_index + 1)
            else:
                gi = len(config.GRADES) - 1
            p.grade_index = gi
            p.grade_deals = 0
            p.grade_missions = 0
            p.grade_start_quarter = p.quarter
            if gi >= 2 and p.track == "General":
                p.flags["can_choose_track"] = True
            self.msg = f"Grade → {config.GRADES[gi]}"
        elif key == "eval":
            self.closed = True
            # route_scene : sur le bureau, ouvre l'examen en FENÊTRE plutôt que
            # de basculer plein écran (le panneau est désormais accessible
            # partout via le bouton CHEAT de la bande d'onglets).
            self.app.route_scene("evaluation", return_to="terminal")

    def handle(self, event):
        """Retourne True si l'event est consommé."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_rect().collidepoint(event.pos):
                self.closed = True
                return True
            if self._title_rect().collidepoint(event.pos):
                self.dragging = True
                self._drag_off = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                return True
            for key, r in self._btn_rects.items():
                if r.collidepoint(event.pos):
                    self._press(key)
                    return True
            if self.rect.collidepoint(event.pos):
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.rect.x = max(0, min(config.SCREEN_WIDTH - self.rect.w,
                                     event.pos[0] - self._drag_off[0]))
            self.rect.y = max(config.TOPBAR_H, min(config.SCREEN_HEIGHT - 40,
                                                    event.pos[1] - self._drag_off[1]))
            return True
        return False

    def _row(self, surf, y, buttons, mp):
        x = self.rect.x + PADX
        avail = self.rect.w - 2 * PADX
        bw = (avail - (len(buttons) - 1) * 6) // len(buttons)
        for key, label in buttons:
            r = pygame.Rect(x, y, bw, 28)
            self._btn_rects[key] = r
            hover = r.collidepoint(mp)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL,
                             r, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN if hover else config.COL_BORDER,
                             r, 1, border_radius=4)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True),
                              config.COL_WHITE, align="center")
            x += bw + 6
        return y + 34

    def draw(self, surf):
        p = self.app.gs.player
        pygame.draw.rect(surf, (0, 0, 0), self.rect.move(0, 3), border_radius=6)
        pygame.draw.rect(surf, config.COL_PANEL, self.rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_DOWN, self.rect, 1, border_radius=6)
        tr = self._title_rect()
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, tr,
                         border_top_left_radius=6, border_top_right_radius=6)
        widgets.draw_text(surf, "🛠 TRICHE (test)", (tr.x + 8, tr.y + 4),
                          fonts.tiny(bold=True), config.COL_DOWN)
        widgets.draw_text(surf, "✕", (self._close_rect().centerx, tr.y + 4),
                          fonts.small(bold=True), config.COL_TEXT_DIM, align="center")

        self._btn_rects = {}
        mp = pygame.mouse.get_pos()
        y = tr.bottom + 8

        widgets.draw_text(surf, "CASH", (self.rect.x + PADX, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 18
        y = self._row(surf, y, [("cash:1000", "+1K"), ("cash:10000", "+10K"),
                                 ("cash:100000", "+100K"), ("cash:1000000", "+1M")], mp)

        widgets.draw_text(surf, "RÉPUTATION", (self.rect.x + PADX, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 18
        y = self._row(surf, y, [("rep:10", "+10"), ("rep:25", "+25"),
                                 ("repset:100", "MAX"), ("repset:0", "0")], mp)

        widgets.draw_text(surf, f"GRADE — {p.grade}", (self.rect.x + PADX, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 18
        y = self._row(surf, y, [("grade:-1", "◂ PRÉCÉDENT"), ("grade:+1", "SUIVANT ▸"),
                                 ("grade:max", "MAX")], mp)

        widgets.draw_text(surf, "EXAMEN", (self.rect.x + PADX, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 18
        r = pygame.Rect(self.rect.x + PADX, y, self.rect.w - 2 * PADX, 30)
        self._btn_rects["eval"] = r
        hover = r.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL, r, border_radius=4)
        pygame.draw.rect(surf, config.COL_DOWN, r, 1, border_radius=4)
        widgets.draw_text(surf, "FORCER L'EXAMEN (skip requis)", r.center,
                          fonts.tiny(bold=True), config.COL_DOWN, align="center")
        y = r.bottom + 10

        if self.msg:
            widgets.draw_text(surf, self.msg, (self.rect.x + PADX, y), fonts.tiny(), config.COL_UP)
            y += 18

        self.rect.h = y - self.rect.y + 8
