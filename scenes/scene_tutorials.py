"""
scene_tutorials.py — Tutoriels illustrés « Comment faire ».

Liste des tutoriels à gauche, contenu détaillé à droite : capture d'écran réelle
du jeu, étapes numérotées et encart « à comprendre ». Ouvert via la commande
TUTO (ou le bouton TUTORIELS de l'Académie). Pensé pour ne jamais être perdu.
"""
import os
import pygame
from core import config
from core.scene_manager import Scene
from data import tutorials as T
from ui import fonts, widgets

_IMG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tutorials")


class TutorialsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.sel = kwargs.get("tid", T.TUTORIALS[0]["id"])
        self._img_cache = {}
        self._rows = {}
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _image(self, name):
        if name not in self._img_cache:
            path = os.path.join(_IMG_DIR, name)
            try:
                self._img_cache[name] = pygame.image.load(path).convert()
            except Exception:
                self._img_cache[name] = None
        return self._img_cache[name]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tid, rect in self._rows.items():
                if rect.collidepoint(event.pos):
                    self.sel = tid

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "TUTORIELS — COMMENT FAIRE", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Guides illustrés des actions clés du terminal.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        ph = config.footer_y() - 8 - 100
        # liste à gauche
        listp = pygame.Rect(40, 100, 320, ph)
        linner = widgets.draw_panel(surf, listp, "Guides", config.COL_CYAN)
        self._rows = {}
        y = linner.y
        for t in T.TUTORIALS:
            rect = pygame.Rect(linner.x - 4, y - 2, linner.w + 8, 34)
            self._rows[t["id"]] = rect
            sel = (t["id"] == self.sel)
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
                pygame.draw.rect(surf, config.COL_AMBER, (linner.x - 4, y - 2, 3, 34))
            widgets.draw_text(surf, widgets.fit_text(t["title"], fonts.small(bold=sel), linner.w),
                              (linner.x + 6, y + 6), fonts.small(bold=sel),
                              config.COL_WHITE if sel else config.COL_TEXT)
            y += 38

        # contenu à droite
        readp = pygame.Rect(380, 100, config.SCREEN_WIDTH - 420, ph)
        rinner = widgets.draw_panel(surf, readp, "Tutoriel", config.COL_AMBER)
        t = T.get(self.sel)
        if not t:
            return self.back_btn.draw(surf)

        widgets.draw_text(surf, t["title"], (rinner.x, rinner.y), fonts.head(bold=True),
                          config.COL_WHITE)
        y = rinner.y + 34
        y += widgets.draw_text_wrapped(surf, t["intro"], (rinner.x, y), fonts.small(),
                                       config.COL_TEXT_DIM, rinner.w) + 8

        # capture d'écran (mise à l'échelle pour tenir dans la colonne)
        img = self._image(t["image"])
        if img:
            iw = min(560, rinner.w)
            ih = int(iw * img.get_height() / img.get_width())
            scaled = pygame.transform.smoothscale(img, (iw, ih))
            ix = rinner.x
            surf.blit(scaled, (ix, y))
            pygame.draw.rect(surf, config.COL_BORDER, (ix, y, iw, ih), 1)
            # étapes à droite de l'image si la place le permet, sinon dessous
            steps_x = ix + iw + 20
            steps_w = rinner.right - steps_x
            if steps_w >= 240:
                self._draw_steps(surf, t, steps_x, y, steps_w)
                y += ih + 12
            else:
                y += ih + 12
                y = self._draw_steps(surf, t, rinner.x, y, rinner.w)
        else:
            y = self._draw_steps(surf, t, rinner.x, y, rinner.w)

        # encart « à comprendre »
        box = pygame.Rect(rinner.x, y, rinner.w, rinner.bottom - y)
        if box.h > 40:
            pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN, (box.x, box.y, 3, box.h))
            widgets.draw_text(surf, "À COMPRENDRE", (box.x + 12, box.y + 8),
                              fonts.tiny(bold=True), config.COL_CYAN)
            widgets.draw_text_wrapped(surf, t["concept"], (box.x + 12, box.y + 26),
                                      fonts.small(), config.COL_TEXT, box.w - 24)

        self.back_btn.draw(surf)

    def _draw_steps(self, surf, t, x, y, w):
        widgets.draw_text(surf, "ÉTAPES", (x, y), fonts.tiny(bold=True), config.COL_AMBER)
        y += 20
        for i, step in enumerate(t["steps"], 1):
            widgets.draw_text(surf, f"{i}.", (x, y), fonts.small(bold=True), config.COL_AMBER)
            y += widgets.draw_text_wrapped(surf, step, (x + 22, y), fonts.small(),
                                           config.COL_TEXT, w - 22, line_gap=3) + 8
        return y
