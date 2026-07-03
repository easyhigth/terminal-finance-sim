"""
scene_desktop_menus.py — Mixin des menus et de la recherche du bureau
(DesktopMenusMixin) : recherche globale (Ctrl+/), menu contextuel (clic
droit), menu Démarrer. Extrait de `scene_desktop.py` pour limiter sa taille
(même principe que les mixins `scenes/scene_terminal_*.py` du terminal) ;
mixé dans `DesktopScene` aux côtés de `DesktopWidgetsMixin`.
"""
import pygame

from core import app_catalog, config, desktop_onboarding, desktop_tutorial, fuzzy
from scenes.scene_desktop_common import _L, APPS, TASKBAR_H, TOPBAR_H, _scene_label
from ui import fonts, keynav, widgets

START_COLS = 4
START_BTN_W = 280
START_BTN_H = 40
START_BTN_GAP = 12

_APP_LABEL = {key: label for key, label, _kind, _cls in APPS}


def _app_label(key):
    return _APP_LABEL.get(key, key.capitalize())


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
        glisser-vers-le-bord, même feedback son/visuel via `WindowManager.dock`)."""
        wa = self.wm.work_area
        if side == "left":
            rect = pygame.Rect(wa.x, wa.y, wa.w // 2, wa.h)
        else:
            rect = pygame.Rect(wa.x + wa.w // 2, wa.y, wa.w - wa.w // 2, wa.h)
        self.wm.dock(w, rect)

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
        self._ctx_menu = {"pos": pos, "items": items, "rects": [], "cursor": 0}
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
            (_L("Détacher (premier plan)" if w.pinned else "Épingler (toujours au premier plan)",
                "Unpin" if w.pinned else "Pin (always on top)"),
             lambda: setattr(w, "pinned", not w.pinned)),
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

    def _closed_window_label(self, entry):
        kind, key, _kwargs = entry
        return _scene_label(key) if kind == "scene" else _app_label(key)

    def _reopen_closed_entry(self, entry):
        """Rouvre PRÉCISÉMENT `entry` (pas forcément le plus récent — choisi
        dans la liste du menu contextuel) et le retire de la pile, où qu'il
        s'y trouve."""
        if entry in self._closed_stack:
            self._closed_stack.remove(entry)
        kind, key, kwargs = entry
        if kind == "scene":
            self._open_scene_window(key, **kwargs)
        else:
            self._launch(key)

    def _desktop_menu_items(self):
        items = [
            (_L("Menu Applications", "Applications menu"), self._open_start_menu),
            (_L("Réglages", "Settings"), lambda: self.app.scenes.go("settings", return_to="desktop")),
            (_L("Fermer toutes les fenêtres", "Close all windows"), self._close_all_windows),
            (_L("Revoir l'accueil", "Show welcome again"), desktop_onboarding.reset),
            (_L("Revoir le tutoriel", "Replay the tutorial"), desktop_tutorial.reset),
            (_L("Tutoriels (leçons guidées)", "Tutorials (guided lessons)"),
             lambda: self._open_scene_window("tutorials")),
        ]
        # dernières fenêtres fermées (pile, la plus récente d'abord) : chaque
        # entrée rouvre PRÉCISÉMENT celle-là avec son contexte d'origine —
        # complète CTRL+MAJ+Z (qui ne rouvre que la toute dernière) pour
        # remonter plus loin dans l'historique sans raccourci dédié par rang.
        for entry in reversed(self._closed_stack[-5:]):
            label = self._closed_window_label(entry)
            items.append((_L(f"Rouvrir : {label}", f"Reopen: {label}"),
                          lambda e=entry: self._reopen_closed_entry(e)))
        return items

    def _launch_and_snap(self, key, side):
        w = self._launch(key)
        if w is not None:
            self._snap_window(w, side)
        return w

    def _handle_ctx_event(self, event):
        """Le menu contextuel capture le clic sur un item (exécute son action),
        se referme à tout autre clic ou sur Échap, et se navigue aux flèches
        + Entrée (même primitive de focus clavier que le menu Démarrer/les
        icônes du bureau — liseré blanc, cf. ui.keynav.draw_focus_ring)."""
        items = self._ctx_menu["items"]
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._ctx_menu = None
                return True
            if event.key == pygame.K_DOWN:
                self._ctx_menu["cursor"] = (self._ctx_menu["cursor"] + 1) % len(items)
                return True
            if event.key == pygame.K_UP:
                self._ctx_menu["cursor"] = (self._ctx_menu["cursor"] - 1) % len(items)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                _label, cb = items[self._ctx_menu["cursor"]]
                self._ctx_menu = None
                cb()
                return True
            return False
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
        for i, (label, cb) in enumerate(items):
            r = pygame.Rect(x + 3, iy, w - 6, ih - 2)
            menu["rects"].append((r, cb))
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            keynav.draw_focus_ring(surf, r, i == menu["cursor"])
            widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), w - 20),
                              (r.x + 8, r.y + 4), fonts.small(), config.COL_TEXT)
            iy += ih

    # ------------------------------------------------- menu Démarrer (« PLUS »)
    def _open_start_menu(self):
        self.start_open = True
        self._start_search = ""
        self._start_cursor = 0
        self._start_scroll = 0

    def _toggle_start_menu(self):
        if self.start_open:
            self.start_open = False
        else:
            self._open_start_menu()

    def _start_filtered_sections(self):
        if not self._start_search.strip():
            return app_catalog.SECTIONS
        out = []
        for title, items in app_catalog.SECTIONS:
            kept = fuzzy.filter_sorted(self._start_search, items, key=lambda e: e[0])
            if kept:
                out.append((title, kept))
        return out

    def _start_activate(self, scene, kw, locked, label):
        """Ouvre l'entrée sélectionnée, sauf si verrouillée par le grade : dans
        ce cas un toast explique le seuil requis, sans naviguer (même
        comportement que l'ancien hub PLUS, cf. app_catalog.lock_message)."""
        if locked:
            self.app.notify("⊘ " + app_catalog.lock_message(self.app.gs.player, label, scene), "warn")
            return
        self._open_scene_window(scene, **kw)

    def _start_layout(self, sections, area):
        """Position de TOUS les items (visibles ou non), pour la navigation
        clavier sur la liste complète et le calcul du scroll — même principe
        que l'ancien hub PLUS plein écran."""
        out = []  # [(Rect, scene, kw, locked, label, desc)]
        p = self.app.gs.player
        y = area.y - self._start_scroll
        for title, items in sections:
            y += 26
            for i, (label, scene, kw, desc) in enumerate(items):
                col = i % START_COLS
                if col == 0 and i > 0:
                    y += START_BTN_H + START_BTN_GAP
                x = area.x + col * (START_BTN_W + START_BTN_GAP)
                locked = app_catalog.is_locked(p, scene)
                out.append((pygame.Rect(x, y, START_BTN_W, START_BTN_H), scene, kw, locked, label, desc))
            y += START_BTN_H + START_BTN_GAP + 8
        return out

    def _start_scroll_to_cursor(self, list_rect):
        if not list_rect or not self._start_all_rects:
            return
        rect, *_rest = self._start_all_rects[self._start_cursor]
        row_top = rect.y - list_rect.y + self._start_scroll
        row_bottom = row_top + rect.h
        if row_top < self._start_scroll:
            self._start_scroll = row_top
        elif row_bottom > self._start_scroll + list_rect.h:
            self._start_scroll = row_bottom - list_rect.h
        self._start_scroll = max(0, min(self._start_max_scroll, self._start_scroll))

    def _handle_start_menu_event(self, event):
        """Capture tout (clavier + souris) tant que le menu Démarrer est
        ouvert : recherche locale, navigation clavier en grille (même
        primitive que l'ancien hub PLUS, cf. ui.keynav.grid_nav), clic."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self._start_search:
                    self._start_search = ""
                    self._start_scroll = 0
                else:
                    self.start_open = False
                return
            if event.key == pygame.K_BACKSPACE:
                self._start_search = self._start_search[:-1]
                self._start_scroll = 0
                return
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                             pygame.K_RETURN, pygame.K_KP_ENTER):
                rects = {i: r for i, (r, *_rest) in enumerate(self._start_all_rects)}
                self._start_cursor, activate = keynav.grid_nav(event, rects, self._start_cursor)
                self._start_scroll_to_cursor(self._launcher_list_rect)
                if activate and self._start_all_rects:
                    _r, scene, kw, locked, label, _desc = self._start_all_rects[self._start_cursor]
                    self._start_activate(scene, kw, locked, label)
                return
            if event.key == pygame.K_TAB:
                return
            if event.unicode and event.unicode.isprintable():
                self._start_search += event.unicode
                self._start_scroll = 0
                return
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._launcher_list_rect and self._launcher_list_rect.collidepoint(event.pos):
                self._start_scroll = max(0, min(self._start_max_scroll,
                    self._start_scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, scene, kw, locked, label, _desc in self._launcher_rects:
                if r.collidepoint(event.pos):
                    self._start_activate(scene, kw, locked, label)
                    return
            if not (self._start_rect and self._start_rect.collidepoint(event.pos)):
                self.start_open = False
            return

    def _draw_launcher(self, surf):
        """Menu Démarrer : toutes les scènes du jeu, ouvrables en fenêtre —
        recherche locale, verrous par grade (icône + infobulle explicative,
        même patron que l'ancien hub PLUS) et description d'une ligne pour
        chaque page débloquée, pour qu'un joueur perdu comprenne ce que fait
        une page avant de cliquer dessus."""
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 120))
        surf.blit(shade, (0, 0))
        panel = pygame.Rect(30, TOPBAR_H + 20, config.SCREEN_WIDTH - 60,
                           config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H - 40)
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.rect(surf, config.COL_AMBER, panel, 2)
        widgets.draw_text(surf, _L("APPLICATIONS — ouvrir en fenêtre", "APPLICATIONS — open as a window"),
                          (panel.x + 16, panel.y + 10), fonts.head(bold=True), config.COL_AMBER)

        search_rect = pygame.Rect(panel.x + 16, panel.y + 34, 320, 24)
        pygame.draw.rect(surf, config.COL_BG, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, search_rect, 1, border_radius=4)
        cur = "_" if pygame.time.get_ticks() % 1000 < 500 else ""
        label = (self._start_search + cur) if self._start_search else (
            cur + _L("Rechercher une page…", "Search a page…"))
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 12),
                          (search_rect.x + 6, search_rect.y + 4), fonts.small(),
                          config.COL_TEXT if self._start_search else config.COL_TEXT_DIM)

        sections = self._start_filtered_sections()
        top = search_rect.bottom + 12
        area = pygame.Rect(panel.x + 16, top, panel.w - 32, panel.bottom - 16 - top)
        self._launcher_list_rect = area
        mp = pygame.mouse.get_pos()
        self._start_tooltip = None
        self._launcher_rects = []
        self._start_all_rects = self._start_layout(sections, area)
        if self._start_all_rects:
            self._start_cursor = min(self._start_cursor, len(self._start_all_rects) - 1)
        else:
            self._start_cursor = 0

        prev_clip = surf.get_clip()
        surf.set_clip(area)
        y = area.y - self._start_scroll
        if not sections:
            widgets.draw_text(surf, _L("Aucune page ne correspond à cette recherche.",
                                       "No page matches this search."),
                              (area.x, area.y), fonts.small(), config.COL_TEXT_DIM)
        p = self.app.gs.player
        flat_i = 0
        for title, items in sections:
            if area.top - 20 < y < area.bottom:
                widgets.draw_text(surf, f"— {title}", (area.x, y), fonts.small(bold=True), config.COL_PRESTIGE)
            y += 26
            for i, (label, scene, kw, desc) in enumerate(items):
                col = i % START_COLS
                if col == 0 and i > 0:
                    y += START_BTN_H + START_BTN_GAP
                x = area.x + col * (START_BTN_W + START_BTN_GAP)
                rect = pygame.Rect(x, y, START_BTN_W, START_BTN_H)
                is_cursor = (flat_i == self._start_cursor)
                flat_i += 1
                if area.top - START_BTN_H < rect.y < area.bottom:
                    clipped = rect.clip(area)
                    locked = app_catalog.is_locked(p, scene)
                    self._launcher_rects.append((clipped, scene, kw, locked, label, desc))
                    hover = rect.collidepoint(mp)
                    acc = config.COL_BORDER if locked else widgets.hover_accent(hover)
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD if (hover and not locked) else config.COL_PANEL,
                                     rect, border_radius=5)
                    pygame.draw.rect(surf, acc, rect, 1, border_radius=5)
                    keynav.draw_focus_ring(surf, rect, is_cursor)
                    text_w = rect.w - 16
                    if locked:
                        self._draw_lock_glyph(surf, (rect.x + 12, rect.centery), config.COL_TEXT_DIM)
                        text_w -= 20
                    fitted = widgets.fit_text(label, fonts.small(bold=hover and not locked), text_w)
                    text_x = rect.x + (28 if locked else 8)
                    widgets.draw_text(surf, fitted, (text_x, rect.centery), fonts.small(bold=hover and not locked),
                                      config.COL_TEXT_DIM if locked else (acc if hover else config.COL_TEXT),
                                      align="left")
                    if (hover or is_cursor) and locked:
                        self._start_tooltip = (app_catalog.lock_message(p, label, scene), mp)
                    elif hover or is_cursor:
                        self._start_tooltip = (desc, mp if hover else (rect.right, rect.y))
            y += START_BTN_H + START_BTN_GAP + 8
        surf.set_clip(prev_clip)

        content_h = (y + self._start_scroll) - area.y
        self._start_max_scroll = max(0, content_h - area.h)
        self._start_scroll = min(self._start_scroll, self._start_max_scroll)
        if self._start_max_scroll > 0:
            track = pygame.Rect(area.right + 2, area.y, 6, area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = area.h / (content_h or 1)
            bar_h = max(24, int(area.h * frac))
            bar_y = area.y + int((area.h - bar_h) * (self._start_scroll / self._start_max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

        if self._start_tooltip:
            widgets.draw_tooltip(surf, *self._start_tooltip)

    def _draw_lock_glyph(self, surf, center, color):
        """Petit cadenas VECTORIEL (corps + anse) — pas de glyphe unicode, non
        garanti par la police embarquée (même précaution que ui/desktop_icons.py
        et la case à cocher de scene_runsetup.py)."""
        cx, cy = center
        body = pygame.Rect(cx - 6, cy - 1, 12, 9)
        pygame.draw.rect(surf, color, body, border_radius=2)
        pygame.draw.arc(surf, color, pygame.Rect(cx - 5, cy - 9, 10, 10), 0.15, 2.99, 2)
