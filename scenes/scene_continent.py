"""
scene_continent.py — Choix du continent de départ.
Affiche le globe interactif + panneaux réglementaires par région.
L'étape suivante (scénario, archétype, mode hardcore) se règle dans la scène
"runsetup", pour éviter d'entasser tous les réglages sur un seul écran.
"""
import pygame

from core import config
from core.i18n import t
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.globe import Globe


class ContinentScene(Scene):
    def on_enter(self, **kwargs):
        self.globe = Globe((345, 360), 190)
        self.selected = kwargs.get("preselect")
        fy = config.SCREEN_HEIGHT - 50
        self.back_btn = widgets.Button((40, fy, 150, 42), t("common.back"), config.COL_TEXT_DIM)
        self.confirm_btn = widgets.Button(
            (config.SCREEN_WIDTH-300, fy, 260, 42),
            t("continent.next"), config.COL_UP, enabled=self.selected is not None)
        self.card_cursor = 0  # curseur clavier dans la grille de cartes régionales

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            region = self.globe.region_at(event.pos)
            if region:
                self.selected = region
                self.confirm_btn.enabled = True
            # clic sur les cartes de droite
            for name, rect in getattr(self, "_card_rects", {}).items():
                if rect.collidepoint(event.pos):
                    self.selected = name
                    self.confirm_btn.enabled = True

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN,
                                                            pygame.K_RETURN, pygame.K_KP_ENTER):
            names = list(config.CONTINENTS.keys())
            self.card_cursor, activate = widgets.list_key_nav(event, self.card_cursor, len(names))
            if activate and names:
                self.selected = names[self.card_cursor]
                self.confirm_btn.enabled = True

        if self.back_btn.handle(event):
            self.app.scenes.go("menu")
        if self.confirm_btn.handle(event) and self.selected:
            self.app.scenes.go("runsetup", continent=self.selected)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.globe.update(dt, mp)
        self.confirm_btn.update(mp, dt)
        self.back_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, t("continent.title"),
                          (40, 30), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, t("continent.subtitle"),
                          (42, 80), fonts.small(), config.COL_TEXT_DIM)

        self.globe.draw(surf)
        widgets.draw_text(surf, t("continent.hint"),
                          (345, 565), fonts.small(), config.COL_TEXT_DIM, align="center")

        # cartes réglementaires à droite, en grille 2 colonnes (7 régions)
        self._card_rects = {}
        names = list(config.CONTINENTS.keys())
        self.card_cursor = min(self.card_cursor, len(names) - 1) if names else 0
        x0 = 700
        y0 = 120
        cw, ch, gx, gy = 280, 124, 16, 12
        for i, (name, info) in enumerate(config.CONTINENTS.items()):
            col = i % 2
            row = i // 2
            x = x0 + col * (cw + gx)
            y = y0 + row * (ch + gy)
            rect = pygame.Rect(x, y, cw, ch)
            self._card_rects[name] = rect
            accent = info["color"]
            selected = (self.selected == name)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if selected else config.COL_PANEL, rect)
            pygame.draw.rect(surf, accent if selected else config.COL_BORDER,
                             rect, 2 if selected else 1)
            widgets.draw_row_selection(surf, rect, i == self.card_cursor)
            widgets.draw_text(surf, name.upper(), (x+12, y+8),
                              fonts.body(bold=True), accent)
            widgets.draw_text(surf, info["regulator"], (x+12, y+34),
                              fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{t('continent.currency')} : {info['currency']}", (x+12, y+54),
                              fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text_wrapped(surf, info["blurb"], (x+12, y+74),
                                      fonts.tiny(), config.COL_NEUTRAL, cw-24, line_gap=2)

        self.confirm_btn.draw(surf)
        self.back_btn.draw(surf)
