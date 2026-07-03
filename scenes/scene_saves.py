"""
scene_saves.py — Gestion des sauvegardes.
Affiche les slots (autosave + slots manuels), leurs métadonnées (grade, jour,
trésorerie, mode hardcore, date), et permet de charger ou supprimer un slot.
Accessible depuis le menu (CHARGER) et depuis le terminal (commande SAVES).
"""
import os
import time

import pygame

from core import config
from core.game_state import GameState
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, keynav, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


# Dossier par défaut proposé pour l'export (dossier personnel de l'utilisateur,
# visible/accessible depuis n'importe quel explorateur de fichiers du système —
# pertinent pour copier le fichier vers une autre machine).
_DEFAULT_EXPORT_DIR = os.path.expanduser("~")


class SavesScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "menu")
        self.message = ""
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT - 70, 200, 48),
            f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        # une partie en cours peut être enregistrée manuellement dans un slot
        # (hors autosave) ; accessible uniquement quand on vient du jeu, pas
        # du menu principal où il n'y a pas encore de partie à sauvegarder.
        self.can_save = self.return_to != "menu" and not self.app.gs.player.hardcore
        self.confirm = None  # dict {"kind": "delete"/"save", "slot": ...} en attente de validation
        box_bottom = config.SCREEN_HEIGHT // 2 + 80
        self._yes_btn = widgets.Button((config.SCREEN_WIDTH // 2 - 170, box_bottom - 50, 160, 36),
                                       "OUI, CONFIRMER", config.COL_DOWN)
        self._no_btn = widgets.Button((config.SCREEN_WIDTH // 2 + 10, box_bottom - 50, 160, 36),
                                      "ANNULER", config.COL_TEXT_DIM)
        # export/import de sauvegarde en fichier portable (transport entre
        # machines) : self.path_prompt = {"kind": "export"/"import", "slot": ...}
        # en attente de saisie d'un chemin, self.path_buf = texte en cours.
        self.path_prompt = None
        self.path_buf = ""
        self._path_box = pygame.Rect(0, 0, 560, 190)
        self._path_box.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        pb_bottom = self._path_box.bottom
        self._import_btn = widgets.Button((config.SCREEN_WIDTH - 240, 24, 200, 36),
                                          f"⇩ {_L('IMPORTER', 'IMPORT')}", config.COL_CYAN)
        self._path_ok_btn = widgets.Button((self._path_box.centerx - 170, pb_bottom - 50, 160, 36),
                                           _L("VALIDER", "CONFIRM"), config.COL_CYAN)
        self._path_cancel_btn = widgets.Button((self._path_box.centerx + 10, pb_bottom - 50, 160, 36),
                                                _L("ANNULER", "CANCEL"), config.COL_TEXT_DIM)
        self._refresh()

    def _refresh(self):
        """(Re)construit la liste des slots affichés avec leurs métadonnées."""
        # ordre : autosave en tête, puis slots manuels
        self.slots = [config.AUTOSAVE_SLOT] + list(config.SAVE_SLOTS)
        self.meta = {s: GameState.slot_meta(s) for s in self.slots}
        # rectangles de boutons recalculés au draw
        self._load_rects = {}
        self._del_rects = {}
        self._save_rects = {}
        self._export_rects = {}
        self.slot_cursor = 0  # curseur clavier dans la liste des slots

    def handle_event(self, event):
        if self.path_prompt is not None:
            self._handle_path_prompt_event(event)
            return
        if self.confirm is not None:
            self._handle_confirm_event(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self._import_btn.handle(event):
            self.path_prompt = {"kind": "import"}
            self.path_buf = ""
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN,
                                                            pygame.K_RETURN, pygame.K_KP_ENTER):
            self.slot_cursor, activate = widgets.list_key_nav(event, self.slot_cursor, len(self.slots))
            # ENTRÉE charge le slot sélectionné (action primaire) ; la suppression
            # et l'enregistrement restent volontairement souris-uniquement, ce
            # sont des actions destructives qu'on ne veut pas déclencher par
            # accident via la navigation clavier.
            if activate and 0 <= self.slot_cursor < len(self.slots):
                slot = self.slots[self.slot_cursor]
                if self.meta.get(slot):
                    self._load(slot)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for slot, rect in self._load_rects.items():
                if rect.collidepoint(event.pos) and self.meta.get(slot):
                    self._load(slot)
                    return
            for slot, rect in self._save_rects.items():
                if rect.collidepoint(event.pos):
                    if self.meta.get(slot):
                        self.confirm = {"kind": "save", "slot": slot}
                    else:
                        self._save(slot)
                    return
            for slot, rect in self._del_rects.items():
                if rect.collidepoint(event.pos) and self.meta.get(slot):
                    self.confirm = {"kind": "delete", "slot": slot}
                    return
            for slot, rect in self._export_rects.items():
                if rect.collidepoint(event.pos) and self.meta.get(slot):
                    self.path_prompt = {"kind": "export", "slot": slot}
                    default_name = f"{slot}_{self.meta[slot]['name']}.json".replace(" ", "_")
                    self.path_buf = os.path.join(_DEFAULT_EXPORT_DIR, default_name)
                    return

    def _handle_path_prompt_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.path_prompt = None
                return
            if event.key == pygame.K_BACKSPACE:
                self.path_buf = self.path_buf[:-1]
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_path_prompt()
                return
            if event.unicode and event.unicode.isprintable():
                self.path_buf += event.unicode
                return
        if self._path_ok_btn.handle(event):
            self._confirm_path_prompt()
            return
        if self._path_cancel_btn.handle(event):
            self.path_prompt = None
            return

    def _confirm_path_prompt(self):
        kind = self.path_prompt["kind"]
        path = self.path_buf.strip()
        if not path:
            self.message = _L("Chemin vide.", "Empty path.")
            return
        if kind == "export":
            slot = self.path_prompt["slot"]
            gs = GameState.load(slot)
            if not gs:
                self.message = _L("Échec de l'export (slot introuvable).", "Export failed (slot not found).")
                self.path_prompt = None
                return
            try:
                gs.export_to(path)
                self.message = _L(f"Sauvegarde exportée vers « {path} ».",
                                  f"Save exported to “{path}”.")
            except Exception:
                self.message = _L(f"Échec de l'export vers « {path} » (chemin invalide ou inaccessible).",
                                  f"Export to “{path}” failed (invalid or inaccessible path).")
        else:  # import
            gs = GameState.import_from(path)
            if not gs:
                self.message = _L(f"Échec de l'import depuis « {path} » (fichier introuvable ou invalide).",
                                  f"Import from “{path}” failed (file not found or invalid).")
                self.path_prompt = None
                return
            self.app.gs = gs
            self.path_prompt = None
            if gs.player.game_over:
                self.app.scenes.go("gameover")
            else:
                self.app.scenes.go("desktop")
            return
        self.path_prompt = None

    def _handle_confirm_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_n):
            self.confirm = None
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_y:
            self._confirm_yes()
            return
        if self._yes_btn and self._yes_btn.handle(event):
            self._confirm_yes()
            return
        if self._no_btn and self._no_btn.handle(event):
            self.confirm = None
            return

    def _confirm_yes(self):
        kind, slot = self.confirm["kind"], self.confirm["slot"]
        self.confirm = None
        if kind == "delete":
            GameState.delete(slot)
            self.message = f"Slot '{slot}' supprimé."
            self._refresh()
        elif kind == "save":
            self._save(slot)

    def _load(self, slot):
        gs = GameState.load(slot)
        if not gs:
            self.message = "Échec du chargement."
            return
        self.app.gs = gs
        if gs.player.game_over:
            self.app.scenes.go("gameover")
        else:
            self.app.scenes.go("desktop")

    def _save(self, slot):
        self.app.gs.save(slot)
        self.message = f"Partie enregistrée dans '{slot}'."
        self._refresh()

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self._import_btn.update(mp, dt)
        if self.confirm is not None:
            self._yes_btn.update(mp, dt)
            self._no_btn.update(mp, dt)
        if self.path_prompt is not None:
            self._path_ok_btn.update(mp, dt)
            self._path_cancel_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "GESTION DES SAUVEGARDES", (40, 28),
                          fonts.title(bold=True), config.COL_AMBER)
        subtitle = "Cliquez sur CHARGER pour reprendre une partie, ou SUPPRIMER pour libérer un slot."
        if self.can_save:
            subtitle = "Cliquez sur ENREGISTRER pour sauvegarder ici, CHARGER pour reprendre, ou SUPPRIMER pour libérer un slot."
        widgets.draw_text(surf, subtitle, (42, 80), fonts.small(), config.COL_TEXT_DIM)
        self._import_btn.draw(surf)

        self._load_rects = {}
        self._del_rects = {}
        self._save_rects = {}
        self._export_rects = {}
        mp = pygame.mouse.get_pos()
        x, y = 120, 130
        cw, ch, gap = config.SCREEN_WIDTH - 240, 110, 16
        self.slot_cursor = min(self.slot_cursor, len(self.slots) - 1) if self.slots else 0
        for i, slot in enumerate(self.slots):
            meta = self.meta.get(slot)
            rect = pygame.Rect(x, y, cw, ch)
            self._draw_slot(surf, rect, slot, meta, mp, i == self.slot_cursor)
            y += ch + gap

        if self.message:
            widgets.draw_text(surf, self.message, (120, y + 4),
                              fonts.small(), config.COL_CYAN)

        if self.slots:
            hints = [("↑↓", "slot"), (_L("ENTRÉE", "ENTER"), _L("charger", "load")),
                     (_L("(souris)", "(mouse)"), _L("supprimer", "delete"))]
            widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14), hints)
        self.back_btn.draw(surf)

        if self.confirm is not None:
            self._draw_confirm(surf)
        if self.path_prompt is not None:
            self._draw_path_prompt(surf)

    def _draw_path_prompt(self, surf):
        """Boîte de dialogue modale pour saisir un chemin de fichier (export
        vers/import depuis un fichier de sauvegarde portable, transportable
        entre machines)."""
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        is_export = self.path_prompt["kind"] == "export"
        box = self._path_box
        title = _L("EXPORTER LA SAUVEGARDE", "EXPORT SAVE") if is_export else \
            _L("IMPORTER UNE SAUVEGARDE", "IMPORT SAVE")
        widgets.draw_panel(surf, box, title, config.COL_CYAN)
        hint = _L("Chemin du fichier de destination (.json) :", "Destination file path (.json):") if is_export \
            else _L("Chemin du fichier à importer (.json) :", "Path of the file to import (.json):")
        widgets.draw_text(surf, hint, (box.x + 20, box.y + 46), fonts.small(), config.COL_TEXT_DIM)

        field = pygame.Rect(box.x + 20, box.y + 70, box.w - 40, 30)
        pygame.draw.rect(surf, config.COL_BG, field, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, field, 1, border_radius=4)
        cur = "_" if pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, widgets.fit_text(self.path_buf + cur, fonts.small(), field.w - 16),
                          (field.x + 8, field.y + 6), fonts.small(), config.COL_TEXT)

        widgets.draw_text(surf, _L("Copiez ce fichier vers l'autre machine (clé USB, cloud…) puis "
                                   "utilisez IMPORTER là-bas.",
                                   "Copy this file to the other machine (USB, cloud…), then use "
                                   "IMPORT there.") if is_export else
                          _L("Le fichier remplace la partie en cours et vous ramène au bureau.",
                             "The file replaces the current game and takes you back to the desktop."),
                          (box.x + 20, field.bottom + 10), fonts.tiny(), config.COL_TEXT_DIM)

        self._path_ok_btn.draw(surf)
        self._path_cancel_btn.draw(surf)

    def _draw_confirm(self, surf):
        """Boîte de dialogue modale bloquant le reste de l'écran, demandant
        confirmation avant une action destructive (suppression ou écrasement
        d'un slot déjà occupé)."""
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        slot = self.confirm["slot"]
        is_delete = self.confirm["kind"] == "delete"
        label = "AUTOSAVE" if slot == config.AUTOSAVE_SLOT else slot.upper()
        if is_delete:
            msg = f"Supprimer définitivement le slot « {label} » ?"
        else:
            msg = f"Écraser la sauvegarde existante du slot « {label} » ?"

        box = pygame.Rect(0, 0, 480, 160)
        box.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        accent = config.COL_DOWN if is_delete else config.COL_WARN
        widgets.draw_panel(surf, box, "CONFIRMATION", accent)
        widgets.draw_text_wrapped(surf, msg, (box.x + 20, box.y + 50),
                                  fonts.body(), config.COL_TEXT, box.w - 40)
        widgets.draw_text(surf, "Y = confirmer, N/Échap = annuler", (box.x + 20, box.y + 96),
                          fonts.tiny(), config.COL_TEXT_DIM)

        self._yes_btn.accent = accent
        self._yes_btn.draw(surf)
        self._no_btn.draw(surf)

    def _draw_slot(self, surf, rect, slot, meta, mp, cursor=False):
        hover = rect.collidepoint(mp)
        is_auto = (slot == config.AUTOSAVE_SLOT)
        accent = config.COL_CYAN if is_auto else config.COL_AMBER
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL, rect)
        pygame.draw.rect(surf, accent if meta else config.COL_BORDER, rect, 1)
        keynav.draw_focus_ring(surf, rect, cursor)

        label = "AUTOSAVE" if is_auto else slot.upper()
        widgets.draw_text(surf, label, (rect.x + 16, rect.y + 12),
                          fonts.head(bold=True), accent)

        if not meta:
            widgets.draw_text(surf, "— slot vide —", (rect.x + 16, rect.y + 52),
                              fonts.body(), config.COL_TEXT_DIM)
            if self.can_save and not is_auto:
                save_rect = pygame.Rect(rect.right - 120, rect.bottom - 38, 104, 26)
                self._save_rects[slot] = save_rect
                self._mini_button(surf, save_rect, "ENREGISTRER", config.COL_CYAN, mp)
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

        # boutons (ENREGISTRER) / CHARGER / SUPPRIMER / EXPORTER
        del_rect = pygame.Rect(rect.right - 120, rect.bottom - 38, 104, 26)
        load_rect = pygame.Rect(del_rect.x - 108, rect.bottom - 38, 100, 26)
        export_rect = pygame.Rect(load_rect.x - 108, rect.bottom - 38, 100, 26)
        self._load_rects[slot] = load_rect
        self._del_rects[slot] = del_rect
        self._export_rects[slot] = export_rect
        self._mini_button(surf, load_rect, "CHARGER", config.COL_UP, mp)
        self._mini_button(surf, del_rect, "SUPPRIMER", config.COL_DOWN, mp)
        self._mini_button(surf, export_rect, "EXPORTER", config.COL_CYAN, mp)
        if self.can_save and not is_auto:
            save_rect = pygame.Rect(export_rect.x - 124, rect.bottom - 38, 116, 26)
            self._save_rects[slot] = save_rect
            self._mini_button(surf, save_rect, "ENREGISTRER", config.COL_CYAN, mp)

    def _mini_button(self, surf, rect, label, accent, mp):
        hover = rect.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL, rect)
        pygame.draw.rect(surf, accent, rect, 1)
        col = accent if hover else config.COL_TEXT
        img = fonts.small(bold=hover).render(label, True, col)
        surf.blit(img, img.get_rect(center=rect.center))
