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
        self.scroll = 0
        self._max_scroll = 0
        self._content_rect = None
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
                    self.scroll = 0
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._content_rect and self._content_rect.collidepoint(event.pos):
                if event.button == 4:
                    self.scroll = max(0, self.scroll - 30)
                elif event.button == 5:
                    self.scroll = min(self._max_scroll, self.scroll + 30)

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

        # contenu à droite (panneau scrollable)
        readp = pygame.Rect(380, 100, config.SCREEN_WIDTH - 420, ph)
        rinner = widgets.draw_panel(surf, readp, "Tutoriel", config.COL_AMBER)
        self._content_rect = readp
        tut = T.get(self.sel)
        if not tut:
            return self.back_btn.draw(surf)

        prev_clip = surf.get_clip()
        surf.set_clip(rinner)

        oy = -self.scroll
        cy = rinner.y + oy

        widgets.draw_text(surf, tut["title"], (rinner.x, cy), fonts.head(bold=True),
                          config.COL_WHITE)
        cy += 34
        cy += widgets.draw_text_wrapped(surf, tut["intro"], (rinner.x, cy), fonts.small(),
                                       config.COL_TEXT_DIM, rinner.w) + 8

        img = self._image(tut["image"])
        if img:
            iw = min(560, rinner.w)
            ih = int(iw * img.get_height() / img.get_width())
            scaled = pygame.transform.smoothscale(img, (iw, ih))
            ix = rinner.x
            if cy + ih > rinner.y and cy < rinner.bottom:
                surf.blit(scaled, (ix, cy))
                pygame.draw.rect(surf, config.COL_BORDER, (ix, cy, iw, ih), 1)
            steps_x = ix + iw + 20
            steps_w = rinner.right - steps_x
            if steps_w >= 240:
                cy = self._draw_steps(surf, tut, steps_x, cy, steps_w, rinner)
                cy = max(cy, rinner.y + oy + 34 + ih + 12)
            else:
                cy += ih + 12
                cy = self._draw_steps(surf, tut, rinner.x, cy, rinner.w, rinner)
        else:
            cy = self._draw_steps(surf, tut, rinner.x, cy, rinner.w, rinner)

        cy += 4
        # encart « à comprendre »
        box_h = max(80, rinner.bottom - (cy - oy) - rinner.y + 200)
        box = pygame.Rect(rinner.x, cy, rinner.w, box_h)
        pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, (box.x, box.y, 3, box.h))
        widgets.draw_text(surf, "À COMPRENDRE", (box.x + 12, box.y + 8),
                          fonts.tiny(bold=True), config.COL_CYAN)
        concept_h = widgets.draw_text_wrapped(surf, tut["concept"], (box.x + 12, box.y + 26),
                                  fonts.small(), config.COL_TEXT, box.w - 24)
        cy += concept_h + 40

        surf.set_clip(prev_clip)

        total_content = cy - (rinner.y + oy)
        self._max_scroll = max(0, total_content - rinner.h)
        self.scroll = min(self.scroll, self._max_scroll)

        if self._max_scroll > 0:
            track = pygame.Rect(readp.right - 8, rinner.y, 6, rinner.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = rinner.h / (total_content or 1)
            bar_h = max(24, int(rinner.h * frac))
            bar_y = rinner.y + int((rinner.h - bar_h) * (self.scroll / self._max_scroll)) if self._max_scroll else rinner.y
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

        self.back_btn.draw(surf)

    def _draw_steps(self, surf, t, x, y, w, clip_rect=None):
        widgets.draw_text(surf, "ÉTAPES", (x, y), fonts.tiny(bold=True), config.COL_AMBER)
        y += 20
        for i, step in enumerate(t["steps"], 1):
            widgets.draw_text(surf, f"{i}.", (x, y), fonts.small(bold=True), config.COL_AMBER)
            y += widgets.draw_text_wrapped(surf, step, (x + 22, y), fonts.small(),
                                           config.COL_TEXT, w - 22, line_gap=3) + 8
        return y
