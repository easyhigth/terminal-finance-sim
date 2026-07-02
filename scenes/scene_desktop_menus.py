"""
scene_desktop_menus.py — Mixin des menus et de la recherche du bureau
(DesktopMenusMixin) : recherche globale (Ctrl+/), menu contextuel (clic
droit), menu Démarrer. Extrait de `scene_desktop.py` pour limiter sa taille
(même principe que les mixins `scenes/scene_terminal_*.py` du terminal) ;
mixé dans `DesktopScene` aux côtés de `DesktopWidgetsMixin`.
"""
import pygame

from core import config, desktop_onboarding, desktop_tutorial
from scenes.scene_desktop_common import _L, TASKBAR_H, TOPBAR_H
from scenes.scene_more import SECTIONS
from ui import fonts, widgets


class DesktopMenusMixin:
    # ------------------------------------------------- recherche globale (Ctrl+/)
    def _open_search(self):
        self._search_open = True
        self._search_query = ""
        self._search_sel = 0
        self.start_open = False

    def _close_search(self):
        self._search_open = False

    def _search_results(self):
        from core import global_search
        m = getattr(self.app, "market", None)
        return global_search.search(self.app.gs.player, m, self._search_query)

    def _search_navigate(self, entry):
        action = entry["action"]
        if action["open"] == "trading":
            self.open_trading(action["ticker"])
        elif action["open"] == "scene":
            self._open_scene_window(action["name"])
        self._close_search()

    def _handle_search_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_search()
                return
            results = self._search_results()
            if event.key == pygame.K_BACKSPACE:
                self._search_query = self._search_query[:-1]
                self._search_sel = 0
                return
            if event.key == pygame.K_DOWN:
                if results:
                    self._search_sel = (self._search_sel + 1) % len(results)
                return
            if event.key == pygame.K_UP:
                if results:
                    self._search_sel = (self._search_sel - 1) % len(results)
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if results:
                    self._search_navigate(results[self._search_sel % len(results)])
                return
            if event.unicode and event.unicode.isprintable():
                self._search_query += event.unicode
                self._search_sel = 0
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, entry in self._search_rects:
                if r.collidepoint(event.pos):
                    self._search_navigate(entry)
                    return
            box = pygame.Rect((config.SCREEN_WIDTH - 560) // 2, (config.SCREEN_HEIGHT - 360) // 2, 560, 360)
            if not box.collidepoint(event.pos):
                self._close_search()

    def _draw_search(self, surf):
        box = pygame.Rect((config.SCREEN_WIDTH - 560) // 2, (config.SCREEN_HEIGHT - 360) // 2, 560, 360)
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surf.blit(shade, (0, 0))
        pygame.draw.rect(surf, config.COL_PANEL, box)
        pygame.draw.rect(surf, config.COL_AMBER, box, 2)
        widgets.draw_text(surf, _L("RECHERCHE (Ctrl+/) — positions, watchlist, inbox, mandats, deals",
                                   "SEARCH (Ctrl+/) — positions, watchlist, inbox, mandates, deals"),
                          (box.x + 14, box.y + 12), fonts.small(bold=True), config.COL_AMBER)
        search_box = pygame.Rect(box.x + 14, box.y + 38, box.w - 28, 26)
        pygame.draw.rect(surf, config.COL_BG, search_box)
        pygame.draw.rect(surf, config.COL_BORDER, search_box, 1)
        cur = "_" if pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, (self._search_query + cur) or _L("tapez pour chercher…", "type to search…"),
                          (search_box.x + 8, search_box.y + 5), fonts.small(),
                          config.COL_WHITE if self._search_query else config.COL_TEXT_DIM)
        results = self._search_results()
        self._search_sel = min(self._search_sel, max(0, len(results) - 1))
        list_y = box.y + 72
        row_h = 28
        max_rows = (box.bottom - 10 - list_y) // row_h
        self._search_rects = []
        if not results:
            widgets.draw_text(surf, _L("Aucun résultat.", "No results."), (box.x + 14, list_y + 6),
                              fonts.small(), config.COL_TEXT_DIM)
        for i, entry in enumerate(results[:max_rows]):
            row = pygame.Rect(box.x + 10, list_y + i * row_h, box.w - 20, row_h)
            self._search_rects.append((row, entry))
            if i == self._search_sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
                pygame.draw.rect(surf, config.COL_AMBER, row, 1)
            widgets.draw_text(surf, widgets.fit_text(entry["label"], fonts.small(), row.w - 16),
                              (row.x + 8, row.y + 6), fonts.small(), config.COL_TEXT)
        if len(results) > max_rows:
            widgets.draw_text(surf, f"… {_L('et', 'and')} {len(results) - max_rows} {_L('autre(s)', 'more')}",
                              (box.x + 14, box.bottom - 22), fonts.tiny(), config.COL_TEXT_DIM)

    # ------------------------------------------------- menus contextuels (clic droit)
    def _snap_window(self, w, side):
        """Ancre une fenêtre sur une moitié de la zone de travail (comme le
        glisser-vers-le-bord), en gardant `_restore_rect` pour revenir."""
        wa = self.wm.work_area
        if w._restore_rect is None:
            w._restore_rect = w.rect.copy()
        if side == "left":
            w.rect = pygame.Rect(wa.x, wa.y, wa.w // 2, wa.h)
        else:
            w.rect = pygame.Rect(wa.x + wa.w // 2, wa.y, wa.w - wa.w // 2, wa.h)

    def _close_all_windows(self):
        """Ferme toutes les fenêtres SAUF le terminal (moteur de la partie) —
        celui-ci est seulement minimisé, pour ne jamais arrêter le temps."""
        for w in list(self.wm.windows):
            if w.key == "scene:terminal":
                w.minimized = True
            else:
                self.wm.close(w)

    def _open_context_menu(self, pos):
        """Construit le menu contextuel selon la cible sous le curseur. Retourne
        True si un menu a été ouvert."""
        items = None
        # 1) entrée de la barre des tâches
        for w, r in self._task_rects.items():
            if r.collidepoint(pos):
                items = self._window_menu_items(w)
                break
        # 2) barre de titre d'une fenêtre (le contenu reste à l'app)
        if items is None:
            w = self.wm._topmost_at(pos)
            if w is not None and w.title_rect.collidepoint(pos):
                items = self._window_menu_items(w)
        # 3) icône du bureau (seulement si aucune fenêtre ne la recouvre)
        if items is None and self.wm._topmost_at(pos) is None:
            for key, (r, _kind, _label) in self._icon_rects.items():
                if r.collidepoint(pos):
                    items = self._icon_menu_items(key)
                    break
        # 4) fond du bureau (ni barre supérieure ni barre des tâches ni fenêtre)
        if items is None:
            area = pygame.Rect(0, TOPBAR_H, config.SCREEN_WIDTH,
                               config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H)
            if area.collidepoint(pos) and self.wm._topmost_at(pos) is None:
                items = self._desktop_menu_items()
        if not items:
            return False
        self._ctx_menu = {"pos": pos, "items": items, "rects": []}
        self.start_open = False
        return True

    def _window_menu_items(self, w):
        maximized = (w.rect == self.wm.work_area)
        return [
            (_L("Restaurer" if w.minimized else "Réduire", "Restore" if w.minimized else "Minimize"),
             lambda: (setattr(w, "minimized", False), self.wm.focus(w)) if w.minimized
             else self.wm.toggle_minimize(w)),
            (_L("Restaurer la taille" if maximized else "Agrandir",
                "Restore size" if maximized else "Maximize"),
             lambda: self.wm.maximize_toggle(w)),
            (_L("Ancrer à gauche", "Snap left"), lambda: self._snap_window(w, "left")),
            (_L("Ancrer à droite", "Snap right"), lambda: self._snap_window(w, "right")),
            (_L("Fermer", "Close"), lambda: self.wm.close(w)),
        ]

    def _icon_menu_items(self, key):
        return [
            (_L("Ouvrir", "Open"), lambda: self._launch(key)),
            (_L("Ouvrir puis ancrer à gauche", "Open and snap left"),
             lambda: self._launch_and_snap(key, "left")),
            (_L("Ouvrir puis ancrer à droite", "Open and snap right"),
             lambda: self._launch_and_snap(key, "right")),
        ]

    def _desktop_menu_items(self):
        return [
            (_L("Menu Applications", "Applications menu"), lambda: setattr(self, "start_open", True)),
            (_L("Réglages", "Settings"), lambda: self.app.scenes.go("settings", return_to="desktop")),
            (_L("Fermer toutes les fenêtres", "Close all windows"), self._close_all_windows),
            (_L("Revoir l'accueil", "Show welcome again"), desktop_onboarding.reset),
            (_L("Revoir le tutoriel", "Replay the tutorial"), desktop_tutorial.reset),
            (_L("Tutoriels (leçons guidées)", "Tutorials (guided lessons)"),
             lambda: self._open_scene_window("tutorials")),
        ]

    def _launch_and_snap(self, key, side):
        w = self._launch(key)
        if w is not None:
            self._snap_window(w, side)
        return w

    def _handle_ctx_event(self, event):
        """Le menu contextuel capture le clic sur un item (exécute son action),
        et se referme à tout autre clic ou sur Échap."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._ctx_menu = None
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            for r, cb in self._ctx_menu["rects"]:
                if r.collidepoint(event.pos):
                    self._ctx_menu = None
                    cb()
                    return True
            self._ctx_menu = None       # clic hors menu : referme (et avale le clic)
            return True
        return False

    def _draw_context_menu(self, surf):
        menu = self._ctx_menu
        items = menu["items"]
        pad, ih, w = 6, 24, 210
        h = pad * 2 + ih * len(items)
        x, y = menu["pos"]
        x = min(x, config.SCREEN_WIDTH - w - 4)
        y = min(y, config.SCREEN_HEIGHT - h - 4)
        panel = pygame.Rect(x, y, w, h)
        shadow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 110))
        surf.blit(shadow, (x + 3, y + 4))
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.rect(surf, config.COL_AMBER, panel, 1)
        mp = pygame.mouse.get_pos()
        menu["rects"] = []
        iy = y + pad
        for label, cb in items:
            r = pygame.Rect(x + 3, iy, w - 6, ih - 2)
            menu["rects"].append((r, cb))
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), w - 20),
                              (r.x + 8, r.y + 4), fonts.small(), config.COL_TEXT)
            iy += ih

    def _draw_launcher(self, surf):
        """Menu Démarrer : toutes les scènes du jeu, ouvrables en fenêtre."""
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 120))
        surf.blit(shade, (0, 0))
        panel = pygame.Rect(30, TOPBAR_H + 20, config.SCREEN_WIDTH - 60,
                           config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H - 40)
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.rect(surf, config.COL_AMBER, panel, 2)
        widgets.draw_text(surf, "APPLICATIONS — ouvrir en fenêtre", (panel.x + 16, panel.y + 10),
                          fonts.head(bold=True), config.COL_AMBER)
        self._launcher_rects = []
        col_w = 236
        item_h = 22
        x0 = panel.x + 16
        y0 = panel.y + 44
        x, y = x0, y0
        max_y = panel.bottom - 16
        prev_clip = surf.get_clip()
        surf.set_clip(panel)
        for title, items in SECTIONS:
            # en-tête de section : force une nouvelle colonne si trop bas
            if y + 18 + item_h > max_y:
                x += col_w
                y = y0
            widgets.draw_text(surf, title.upper(), (x, y), fonts.tiny(bold=True), config.COL_CYAN)
            y += 18
            for label, scene, kw in items:
                if y + item_h > max_y:
                    x += col_w
                    y = y0
                    widgets.draw_text(surf, title.upper() + " (suite)", (x, y), fonts.tiny(bold=True), config.COL_CYAN)
                    y += 18
                r = pygame.Rect(x, y, col_w - 12, item_h - 2)
                self._launcher_rects.append((r, scene, kw))
                hov = r.collidepoint(pygame.mouse.get_pos())
                if hov:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
                    pygame.draw.rect(surf, config.COL_AMBER, r, 1, border_radius=3)
                widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), col_w - 24),
                                  (r.x + 8, r.y + 3), fonts.small(),
                                  config.COL_TEXT if hov else config.COL_TEXT_DIM)
                y += item_h
            y += 8
        surf.set_clip(prev_clip)
