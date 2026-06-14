"""
scene_saves.py — Gestion des sauvegardes.
Affiche les slots (autosave + slots manuels), leurs métadonnées (grade, jour,
trésorerie, mode hardcore, date), et permet de charger ou supprimer un slot.
Accessible depuis le menu (CHARGER) et depuis le terminal (commande SAVES).
"""
import time
import pygame
from core import config
from core.scene_manager import Scene
from core.game_state import GameState
from ui import fonts, widgets


class SavesScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "menu")
        self.message = ""
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT - 70, 200, 48),
            f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._refresh()

    def _refresh(self):
        """(Re)construit la liste des slots affichés avec leurs métadonnées."""
        # ordre : autosave en tête, puis slots manuels
        self.slots = [config.AUTOSAVE_SLOT] + list(config.SAVE_SLOTS)
        self.meta = {s: GameState.slot_meta(s) for s in self.slots}
        # rectangles de boutons recalculés au draw
        self._load_rects = {}
        self._del_rects = {}

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for slot, rect in self._load_rects.items():
                if rect.collidepoint(event.pos) and self.meta.get(slot):
                    self._load(slot)
                    return
            for slot, rect in self._del_rects.items():
                if rect.collidepoint(event.pos) and self.meta.get(slot):
                    GameState.delete(slot)
                    self.message = f"Slot '{slot}' supprimé."
                    self._refresh()
                    return

    def _load(self, slot):
        gs = GameState.load(slot)
        if not gs:
            self.message = "Échec du chargement."
            return
        self.app.gs = gs
        if gs.player.game_over:
            self.app.scenes.go("gameover")
        else:
            self.app.scenes.go("terminal")

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "GESTION DES SAUVEGARDES", (40, 28),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Cliquez sur CHARGER pour reprendre une partie, "
                                "ou SUPPRIMER pour libérer un slot.",
                          (42, 80), fonts.small(), config.COL_TEXT_DIM)

        self._load_rects = {}
        self._del_rects = {}
        mp = pygame.mouse.get_pos()
        x, y = 120, 130
        cw, ch, gap = config.SCREEN_WIDTH - 240, 110, 16
        for slot in self.slots:
            meta = self.meta.get(slot)
            rect = pygame.Rect(x, y, cw, ch)
            self._draw_slot(surf, rect, slot, meta, mp)
            y += ch + gap

        if self.message:
            widgets.draw_text(surf, self.message, (120, y + 4),
                              fonts.small(), config.COL_CYAN)

        self.back_btn.draw(surf)

    def _draw_slot(self, surf, rect, slot, meta, mp):
        hover = rect.collidepoint(mp)
        is_auto = (slot == config.AUTOSAVE_SLOT)
        accent = config.COL_CYAN if is_auto else config.COL_AMBER
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL, rect)
        pygame.draw.rect(surf, accent if meta else config.COL_BORDER, rect, 1)

        label = "AUTOSAVE" if is_auto else slot.upper()
        widgets.draw_text(surf, label, (rect.x + 16, rect.y + 12),
                          fonts.head(bold=True), accent)

        if not meta:
            widgets.draw_text(surf, "— slot vide —", (rect.x + 16, rect.y + 52),
                              fonts.body(), config.COL_TEXT_DIM)
            return

        cur = config.CONTINENTS.get(meta["continent"], {}).get("currency", "$")
        line1 = (f"{meta['name']} · {meta['grade']} · {meta['track']} · "
                 f"{meta['continent']}")
        line2 = (f"Jour {meta['day']} · {widgets.format_money(meta['cash'], cur)} · "
                 f"Rép. dispo")
        widgets.draw_text(surf, line1, (rect.x + 16, rect.y + 50),
                          fonts.body(), config.COL_TEXT)
        widgets.draw_text(surf, line2, (rect.x + 16, rect.y + 74),
                          fonts.small(), config.COL_TEXT_DIM)

        # date de sauvegarde
        if meta["last_saved"]:
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(meta["last_saved"]))
            widgets.draw_text(surf, when, (rect.right - 220, rect.y + 12),
                              fonts.tiny(), config.COL_TEXT_DIM)

        # badges d'état
        bx = rect.right - 16
        if meta["game_over"]:
            r = widgets.draw_badge(surf, "GAME OVER", (bx, rect.y + 40),
                                   config.COL_DOWN, align="right")
            bx = r.x - 8
        if meta["hardcore"]:
            widgets.draw_badge(surf, "HARDCORE", (bx, rect.y + 40),
                               config.COL_WARN, align="right")

        # boutons CHARGER / SUPPRIMER
        load_rect = pygame.Rect(rect.right - 230, rect.bottom - 38, 100, 26)
        del_rect = pygame.Rect(rect.right - 120, rect.bottom - 38, 104, 26)
        self._load_rects[slot] = load_rect
        self._del_rects[slot] = del_rect
        self._mini_button(surf, load_rect, "CHARGER", config.COL_UP, mp)
        self._mini_button(surf, del_rect, "SUPPRIMER", config.COL_DOWN, mp)

    def _mini_button(self, surf, rect, label, accent, mp):
        hover = rect.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL, rect)
        pygame.draw.rect(surf, accent, rect, 1)
        col = accent if hover else config.COL_TEXT
        img = fonts.small(bold=hover).render(label, True, col)
        surf.blit(img, img.get_rect(center=rect.center))
