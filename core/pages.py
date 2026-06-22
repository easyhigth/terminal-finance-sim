"""
core/pages.py — Système de pages (onglets), façon navigateur / terminal
Bloomberg : nombre illimité de pages ouvertes simultanément, chacune
mémorisant exactement la scène et l'état d'interface où on l'a laissée
(scroll, recherche, filtres, popups internes...). Les pages sont
volatiles : jamais sérialisées dans la sauvegarde.

Chaque Page possède son PROPRE SceneManager (donc ses propres instances
de scènes, totalement indépendantes des autres pages) — c'est ce qui
garantit l'isolation de l'état entre onglets sans toucher au code des
~50 scènes existantes, qui continuent de naviguer via self.app.scenes
comme avant (cette référence pointe vers le SceneManager de la page
active : voir App.scenes en propriété dans main.py).

Une page peut être détachée en mode « popup » : elle continue de
s'afficher (et de se mettre à jour) flottante par-dessus la page active,
au lieu de prendre tout l'écran. Onglet actif uniquement = plein écran ;
onglet en popup = visible simultanément, redimensionné, par-dessus.

Anti-triche : tant que la scène active de l'onglet courant a
`pageable = False` (examen / certification), tout changement d'onglet
(bouton, clic, raccourci) est bloqué — voir can_switch().

La fenêtre réelle (app.screen) fait SCREEN_HEIGHT + TAB_BAR_H de haut :
la barre d'onglets occupe la bande du haut (0..TAB_BAR_H) et les scènes
sont dessinées, intouchées, dans une sous-surface de taille
SCREEN_WIDTH x SCREEN_HEIGHT juste en dessous — donc jamais cachées par
la barre. Les coordonnées souris (en repère fenêtre) sont translatées de
-TAB_BAR_H avant d'être transmises aux scènes/popups (en repère canvas).
"""
import pygame

from core import config
from ui import fonts, widgets

TAB_BAR_H = config.TAB_BAR_H
TAB_W = 168
MIN_TAB_W = 64      # largeur plancher d'un onglet compressé (façon navigateur)
TAB_GAP = 2
NEW_TAB_W = 28
POPUP_TITLE_H = 24

# Beaucoup de scènes lisent directement pygame.mouse.get_pos() (survol au
# draw(), hors handle_event()) en repère canvas (0..SCREEN_HEIGHT). Comme la
# fenêtre réelle est maintenant plus haute de TAB_BAR_H (barre d'onglets),
# on corrige UNE FOIS ici, globalement, sans toucher aux ~50 fichiers de
# scène : tout appel à pygame.mouse.get_pos() renvoie désormais la position
# déjà translatée en repère canvas.
_real_mouse_get_pos = pygame.mouse.get_pos


def _canvas_mouse_get_pos():
    x, y = _real_mouse_get_pos()
    return (x, y - TAB_BAR_H)


pygame.mouse.get_pos = _canvas_mouse_get_pos


class Page:
    """Un onglet : un SceneManager indépendant + sa scène/kwargs d'entrée."""

    _next_id = 1

    def __init__(self, manager, scene_name, kwargs):
        self.id = Page._next_id
        Page._next_id += 1
        self.manager = manager
        self.scene_name = scene_name
        self.kwargs = dict(kwargs)
        self.popup = False
        self.popup_rect = None

    def label(self):
        return f"{self.id}·{self.scene_name.upper()}"


class PageManager:
    """Gère la liste (illimitée) des pages ouvertes et l'onglet actif."""

    def __init__(self, app, main_manager, main_scene_name="terminal"):
        self.app = app
        self.pages = [Page(main_manager, main_scene_name, {})]
        self.active = 0
        self._drag_page = None     # Page en cours de déplacement (popup)
        self._drag_off = (0, 0)
        self._tab_scroll_x = 0     # défilement horizontal de la barre d'onglets (px)
        self._tab_max_scroll_x = 0

    # ------------------------------------------------------------ accès
    @property
    def current_page(self):
        return self.pages[self.active]

    @property
    def manager(self):
        """Le SceneManager de l'onglet actif — c'est lui que main.py expose
        comme app.scenes pour que tout le code de navigation existant
        (self.app.scenes.go(...)) agisse sur l'onglet courant."""
        return self.current_page.manager

    def _build_manager(self, scene_name, kwargs):
        from main import build_scene_manager
        m = build_scene_manager(self.app)
        m.go(scene_name, **kwargs)
        return m

    # ------------------------------------------------------------ anti-triche
    def can_switch(self):
        cur = self.manager.current
        return cur is None or getattr(cur, "pageable", True)

    # ------------------------------------------------------------ actions
    def open_page(self, scene_name, **kwargs):
        if not self.can_switch():
            return None
        m = self._build_manager(scene_name, kwargs)
        page = Page(m, scene_name, kwargs)
        self.pages.append(page)
        self.active = len(self.pages) - 1
        return page

    def open_popup(self, scene_name, **kwargs):
        """Ouvre directement une page en mode popup flottant, par-dessus
        l'onglet actif courant (qui reste actif) — utilisé pour les vues
        « laboratoire » ouvertes depuis une autre scène (ex. frontière
        efficiente depuis l'analyse de portefeuille)."""
        if not self.can_switch():
            return None
        m = self._build_manager(scene_name, kwargs)
        page = Page(m, scene_name, kwargs)
        page.popup = True
        w, h = config.SCREEN_WIDTH * 4 // 5, config.SCREEN_HEIGHT * 4 // 5
        page.popup_rect = pygame.Rect((config.SCREEN_WIDTH - w) // 2,
                                      (config.SCREEN_HEIGHT - h) // 2 + 10, w, h)
        self.pages.append(page)
        sc = page.manager.current
        if sc is not None:
            sc.refresh_data()
        return page

    def duplicate_current(self):
        cur = self.current_page
        return self.open_page(cur.manager.current_name or "terminal", **cur.kwargs)

    def close_page(self, index=None):
        if index is None:
            index = self.active
        if len(self.pages) <= 1 or not (0 <= index < len(self.pages)):
            return
        if not self.can_switch():
            return
        del self.pages[index]
        if self.active >= len(self.pages):
            self.active = len(self.pages) - 1
        self._refresh_active()

    def switch_to(self, index):
        if not self.can_switch():
            return
        if 0 <= index < len(self.pages) and index != self.active:
            self.active = index
            self._refresh_active()

    def next_page(self):
        if not self.can_switch() or len(self.pages) < 2:
            return
        self.active = (self.active + 1) % len(self.pages)
        self._refresh_active()

    def prev_page(self):
        if not self.can_switch() or len(self.pages) < 2:
            return
        self.active = (self.active - 1) % len(self.pages)
        self._refresh_active()

    def toggle_popup(self, index):
        if index == self.active or not (0 <= index < len(self.pages)):
            return
        page = self.pages[index]
        page.popup = not page.popup
        if page.popup and page.popup_rect is None:
            w, h = config.SCREEN_WIDTH * 2 // 3, config.SCREEN_HEIGHT * 2 // 3
            page.popup_rect = pygame.Rect((config.SCREEN_WIDTH - w) // 2,
                                          (config.SCREEN_HEIGHT - h) // 2 + 10, w, h)
        if page.popup:
            sc = page.manager.current
            if sc is not None:
                sc.refresh_data()

    def _refresh_active(self):
        sc = self.manager.current
        if sc is not None:
            sc.refresh_data()

    # ------------------------------------------------------------ frame
    def update(self, dt):
        self.manager.update(dt)
        for i, page in enumerate(self.pages):
            if i != self.active and page.popup:
                page.manager.update(dt)

    def _tab_viewport_w(self):
        """Largeur disponible pour les onglets, avant le bouton « + »."""
        return config.SCREEN_WIDTH - NEW_TAB_W - 8

    def _tab_metrics(self):
        """Largeur d'un onglet et défilement max : les onglets se compressent
        (façon navigateur) jusqu'à MIN_TAB_W pour tenir dans la largeur
        disponible ; au-delà, ils restent à MIN_TAB_W et la barre devient
        défilable horizontalement (molette / glisser le slider du bas)."""
        n = len(self.pages)
        avail = self._tab_viewport_w()
        if n <= 0:
            return TAB_W, 0
        full_w = n * TAB_W + max(0, n - 1) * TAB_GAP
        if full_w <= avail:
            return TAB_W, 0
        w = max(MIN_TAB_W, (avail - max(0, n - 1) * TAB_GAP) // n)
        total_w = n * w + max(0, n - 1) * TAB_GAP
        return w, max(0, total_w - avail)

    def _tab_rects(self):
        w, max_scroll = self._tab_metrics()
        self._tab_max_scroll_x = max_scroll
        self._tab_scroll_x = max(0, min(max_scroll, self._tab_scroll_x))
        rects = []
        x = -self._tab_scroll_x
        for page in self.pages:
            rects.append(pygame.Rect(x, 0, w, TAB_BAR_H))
            x += w + TAB_GAP
        avail = self._tab_viewport_w()
        new_x = avail if max_scroll > 0 else min(x, avail)
        new_rect = pygame.Rect(new_x, 0, NEW_TAB_W, TAB_BAR_H)
        return rects, new_rect

    def handle_event(self, event):
        raw_pos = getattr(event, "pos", None)

        # barre d'onglets (toujours visible, en haut de la fenêtre, en repère
        # fenêtre non translaté) — prioritaire sur tout le reste
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5) and raw_pos and raw_pos[1] < TAB_BAR_H:
            self._tab_rects()  # rafraîchit _tab_max_scroll_x
            delta = -40 if event.button == 4 else 40
            self._tab_scroll_x = max(0, min(self._tab_max_scroll_x, self._tab_scroll_x + delta))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and raw_pos and raw_pos[1] < TAB_BAR_H:
            tab_rects, new_rect = self._tab_rects()
            if new_rect.collidepoint(raw_pos):
                if self.can_switch():
                    self.duplicate_current()
                return
            for i, rect in enumerate(tab_rects):
                close_rect = pygame.Rect(rect.right - 18, rect.y + 4, 14, 14)
                pop_rect = pygame.Rect(rect.right - 36, rect.y + 4, 14, 14)
                if close_rect.collidepoint(raw_pos):
                    self.close_page(i)
                    return
                if i != self.active and pop_rect.collidepoint(raw_pos):
                    self.toggle_popup(i)
                    return
                if rect.collidepoint(raw_pos):
                    self.switch_to(i)
                    return
            return

        if event.type == pygame.KEYDOWN and (event.mod & pygame.KMOD_CTRL):
            if event.key == pygame.K_t:
                if self.can_switch():
                    self.duplicate_current()
                return
            if event.key == pygame.K_w:
                self.close_page()
                return
            if event.key == pygame.K_TAB:
                if event.mod & pygame.KMOD_SHIFT:
                    self.prev_page()
                else:
                    self.next_page()
                return

        # à partir d'ici, on travaille en repère "canvas de jeu" (sous la
        # barre d'onglets) : on translate les coordonnées souris une fois.
        if raw_pos is not None:
            attrs = {k: getattr(event, k) for k in event.dict}
            attrs["pos"] = (raw_pos[0], raw_pos[1] - TAB_BAR_H)
            event = pygame.event.Event(event.type, attrs)

        # déplacement d'un popup en cours : prioritaire sur tout le reste
        if event.type == pygame.MOUSEMOTION and self._drag_page is not None:
            self._drag_page.popup_rect.topleft = (event.pos[0] - self._drag_off[0],
                                                   event.pos[1] - self._drag_off[1])
            return
        if event.type == pygame.MOUSEBUTTONUP and self._drag_page is not None:
            self._drag_page = None
            return

        # popups : la souris au-dessus d'un popup a priorité sur la page active
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            for i, page in enumerate(self.pages):
                if i == self.active or not page.popup or page.popup_rect is None:
                    continue
                title_rect = pygame.Rect(page.popup_rect.x, page.popup_rect.y,
                                         page.popup_rect.w, POPUP_TITLE_H)
                close_rect = pygame.Rect(page.popup_rect.right - 22, page.popup_rect.y + 2, 18, 18)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if close_rect.collidepoint(event.pos):
                        page.popup = False
                        return
                    if title_rect.collidepoint(event.pos):
                        self._drag_page = page
                        self._drag_off = (event.pos[0] - page.popup_rect.x,
                                          event.pos[1] - page.popup_rect.y)
                        return
                body_rect = pygame.Rect(page.popup_rect.x, page.popup_rect.y + POPUP_TITLE_H,
                                        page.popup_rect.w, page.popup_rect.h - POPUP_TITLE_H)
                if body_rect.collidepoint(event.pos):
                    self._forward_to_popup(page, body_rect, event)
                    return

        self.manager.handle_event(event)

    def _forward_to_popup(self, page, body_rect, event):
        sx = config.SCREEN_WIDTH / body_rect.w
        sy = config.SCREEN_HEIGHT / body_rect.h
        if hasattr(event, "pos"):
            local = ((event.pos[0] - body_rect.x) * sx, (event.pos[1] - body_rect.y) * sy)
            attrs = {k: getattr(event, k) for k in event.dict}
            attrs["pos"] = (int(local[0]), int(local[1]))
            translated = pygame.event.Event(event.type, attrs)
            page.manager.handle_event(translated)
        else:
            page.manager.handle_event(event)

    # ------------------------------------------------------------ rendu
    def draw(self, surf):
        # canvas de jeu : sous-surface sous la barre d'onglets, jamais cachée
        game_surf = surf.subsurface((0, TAB_BAR_H, config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.manager.draw(game_surf)
        for i, page in enumerate(self.pages):
            if i != self.active and page.popup:
                self._draw_popup(game_surf, page)
        self._draw_tab_bar(surf)

    def _draw_popup(self, surf, page):
        full = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        page.manager.draw(full)
        rect = page.popup_rect
        scaled = pygame.transform.smoothscale(full, (rect.w, rect.h - POPUP_TITLE_H))
        surf.blit(scaled, (rect.x, rect.y + POPUP_TITLE_H))
        title_rect = pygame.Rect(rect.x, rect.y, rect.w, POPUP_TITLE_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, title_rect)
        pygame.draw.rect(surf, config.COL_CYAN, rect, 2)
        widgets.draw_text(surf, page.label(), (title_rect.x + 8, title_rect.y + 5),
                          fonts.tiny(bold=True), config.COL_CYAN)
        close_rect = pygame.Rect(rect.right - 22, rect.y + 2, 18, 18)
        pygame.draw.rect(surf, config.COL_DOWN, close_rect, 1)
        widgets.draw_text(surf, "×", (close_rect.x + 4, close_rect.y - 1), fonts.small(), config.COL_DOWN)

    def _draw_tab_bar(self, surf):
        tab_rects, new_rect = self._tab_rects()
        bar = pygame.Rect(0, 0, surf.get_width(), TAB_BAR_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar)
        blocked = not self.can_switch()
        viewport = pygame.Rect(0, 0, self._tab_viewport_w(), TAB_BAR_H)
        prev_clip = surf.get_clip()
        surf.set_clip(viewport)
        for i, (page, rect) in enumerate(zip(self.pages, tab_rects)):
            if rect.right < 0 or rect.x > viewport.right:
                continue
            active = i == self.active
            col_bg = config.COL_PANEL if active else config.COL_BG
            pygame.draw.rect(surf, col_bg, rect)
            border_col = config.COL_CYAN if active else config.COL_BORDER
            pygame.draw.rect(surf, border_col, rect, 1)
            label = page.label()
            if page.popup:
                label = "⧉ " + label
            # icônes fermer/popup masquées si l'onglet est trop compressé
            # pour leur laisser de la place sans écraser le libellé.
            show_close = len(self.pages) > 1 and rect.w >= 50
            show_pop = i != self.active and rect.w >= 70
            n_icons = int(show_close) + int(show_pop)
            label_w = max(8, rect.w - 8 - 18 * n_icons)
            widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), label_w),
                              (rect.x + 6, rect.y + 6), fonts.tiny(),
                              config.COL_TEXT if not blocked else config.COL_TEXT_DIM)
            if show_close:
                close_rect = pygame.Rect(rect.right - 18, rect.y + 4, 14, 14)
                widgets.draw_text(surf, "×", (close_rect.x + 3, close_rect.y - 2), fonts.small(),
                                  config.COL_TEXT_DIM)
            if show_pop:
                pop_rect = pygame.Rect(rect.right - 36, rect.y + 4, 14, 14)
                widgets.draw_text(surf, "⧉", (pop_rect.x, pop_rect.y - 1), fonts.tiny(),
                                  config.COL_TEXT_DIM)
        surf.set_clip(prev_clip)
        new_col = config.COL_TEXT_DIM if blocked else config.COL_CYAN
        pygame.draw.rect(surf, config.COL_BG, new_rect)
        pygame.draw.rect(surf, new_col, new_rect, 1)
        widgets.draw_text(surf, "+", (new_rect.x + 9, new_rect.y + 4), fonts.small(bold=True), new_col)
        if self._tab_max_scroll_x > 0:
            track = pygame.Rect(0, TAB_BAR_H - 3, viewport.w, 3)
            pygame.draw.rect(surf, config.COL_PANEL, track)
            bar_w = max(20, int(viewport.w * (viewport.w / (viewport.w + self._tab_max_scroll_x))))
            bar_x = int((viewport.w - bar_w) * (self._tab_scroll_x / self._tab_max_scroll_x))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (bar_x, TAB_BAR_H - 3, bar_w, 3))
        if blocked:
            widgets.draw_text(surf, "🔒 examen en cours — onglets verrouillés",
                              (new_rect.right + 12, 6), fonts.tiny(), config.COL_WARN)
