"""
scene_glossary.py — Glossaire interactif consultable in-game.
Navigation par catégorie à gauche, liste des termes au centre,
définition détaillée à droite. Filtre de recherche au clavier.
"""
import pygame

from core import config
from core.i18n import get_lang
from core.scene_manager import Scene
from data import glossary_data
from ui import fonts, widgets


class GlossaryScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.category = "__all__"     # sentinelle indépendante de la langue
        self.search = ""
        self.selected_term = None
        self.scroll = 0
        self.cursor = 0  # curseur clavier dans la liste visible de termes
        from core.i18n import t
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT-70, 180, 46), t("common.back"), config.COL_TEXT_DIM)
        self._rebuild_list()

    def _rebuild_list(self):
        gloss, _cats = glossary_data.localized(get_lang())
        terms = []
        for term, (cat, _) in sorted(gloss.items()):
            if self.category != "__all__" and cat != self.category:
                continue
            if self.search and self.search.lower() not in term.lower():
                continue
            terms.append(term)
        lang = get_lang()
        terms.sort(key=lambda tm: glossary_data.display_name(tm, lang).lower())
        self.terms = terms
        if self.terms and self.selected_term not in self.terms:
            self.selected_term = self.terms[0]

    def _visible_terms(self):
        return self.terms[self.scroll:self.scroll + 18]

    def _scroll_to_cursor(self):
        """Ajuste le scroll pour garder le terme sélectionné au clavier visible."""
        idx = self.scroll + self.cursor
        if idx < self.scroll:
            self.scroll = idx
        elif idx >= self.scroll + 18:
            self.scroll = idx - 17
        self.scroll = max(0, min(max(0, len(self.terms) - 18), self.scroll))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.go(self.return_to)
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self._rebuild_list()
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                visible = self._visible_terms()
                self.cursor, activate = widgets.list_key_nav(event, self.cursor, len(visible))
                if visible:
                    self._scroll_to_cursor()
                if activate and visible:
                    self.selected_term = visible[self.cursor]
                return
            elif event.unicode and event.unicode.isprintable():
                self.search += event.unicode
                self._rebuild_list()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            self.scroll = max(0, self.scroll - 1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            self.scroll = min(max(0, len(self.terms) - 18), self.scroll + 1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # catégories
            for name, rect in getattr(self, "_cat_rects", {}).items():
                if rect.collidepoint(event.pos):
                    self.category = name
                    self.scroll = 0
                    self._rebuild_list()
            # termes
            for term, rect in getattr(self, "_term_rects", {}).items():
                if rect.collidepoint(event.pos):
                    self.selected_term = term
                    visible = self._visible_terms()
                    if term in visible:
                        self.cursor = visible.index(term)

        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos())

    def draw(self, surf):
        surf.fill(config.COL_BG)
        from core.i18n import t
        lang = get_lang()
        gloss, CATEGORIES = glossary_data.localized(lang)
        widgets.draw_text(surf, t("gloss.title"), (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{t('gloss.search')} : {self.search}_",
                          (42, 74), fonts.small(), config.COL_CYAN)

        # --- Colonne catégories ---
        cat_panel = pygame.Rect(40, 110, 220, 560)
        inner = widgets.draw_panel(surf, cat_panel, t("gloss.categories"), config.COL_AMBER)
        self._cat_rects = {}
        cats = [("__all__", t("gloss.all"))] + [(c, c) for c in CATEGORIES]
        # pas adaptatif pour que toutes les catégories tiennent dans le panneau
        cstep = max(22, min(30, (inner.h - 4) // max(1, len(cats))))
        y = inner.y
        for key, label in cats:
            rect = pygame.Rect(inner.x-4, y-2, inner.w+8, cstep-2)
            self._cat_rects[key] = rect
            sel = (key == self.category)
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            col = config.COL_CYAN if sel else config.COL_TEXT
            font = fonts.small(bold=sel)
            widgets.draw_text(surf, widgets.fit_text(label, font, inner.w - 8),
                              (inner.x+4, y+2), font, col)
            y += cstep

        # --- Colonne termes ---
        term_panel = pygame.Rect(276, 110, 300, 560)
        inner2 = widgets.draw_panel(surf, term_panel,
                                    f"{t('gloss.terms')} ({len(self.terms)})", config.COL_CYAN)
        self._term_rects = {}
        y = inner2.y
        visible = self.terms[self.scroll:self.scroll+18]
        self.cursor = min(self.cursor, len(visible) - 1) if visible else 0
        for pos, term in enumerate(visible):
            rect = pygame.Rect(inner2.x-4, y-2, inner2.w+8, 28)
            self._term_rects[term] = rect
            sel = (term == self.selected_term)
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            widgets.draw_row_selection(surf, rect, pos == self.cursor)
            col = config.COL_AMBER if sel else config.COL_TEXT
            font = fonts.small(bold=sel)
            widgets.draw_text(surf, widgets.fit_text(
                glossary_data.display_name(term, lang), font, inner2.w - 8),
                (inner2.x+4, y+2), font, col)
            y += 30

        # --- Définition ---
        def_panel = pygame.Rect(592, 110, config.SCREEN_WIDTH-632, 560)
        inner3 = widgets.draw_panel(surf, def_panel, t("gloss.definition"), config.COL_AMBER)
        _e = glossary_data.entry(self.selected_term, lang) if self.selected_term else None
        if _e:
            cat, definition = _e
            widgets.draw_text(surf, glossary_data.display_name(self.selected_term, lang),
                              (inner3.x, inner3.y),
                              fonts.head(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, f"[{cat}]", (inner3.x, inner3.y+34),
                              fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text_wrapped(surf, definition, (inner3.x, inner3.y+70),
                                      fonts.body(), config.COL_TEXT, inner3.w, line_gap=6)

        self.back_btn.draw(surf)
