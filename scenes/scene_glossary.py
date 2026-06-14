"""
scene_glossary.py — Glossaire interactif consultable in-game.
Navigation par catégorie à gauche, liste des termes au centre,
définition détaillée à droite. Filtre de recherche au clavier.
"""
import pygame
from core import config
from core.scene_manager import Scene
from ui import fonts, widgets
from data.glossary_data import GLOSSARY, CATEGORIES


class GlossaryScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.category = "Tous"
        self.search = ""
        self.selected_term = None
        self.scroll = 0
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT-70, 180, 46), "← RETOUR", config.COL_TEXT_DIM)
        self._rebuild_list()

    def _rebuild_list(self):
        terms = []
        for term, (cat, _) in sorted(GLOSSARY.items()):
            if self.category != "Tous" and cat != self.category:
                continue
            if self.search and self.search.lower() not in term.lower():
                continue
            terms.append(term)
        self.terms = terms
        if self.terms and self.selected_term not in self.terms:
            self.selected_term = self.terms[0]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.go(self.return_to)
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self._rebuild_list()
            elif event.unicode and event.unicode.isprintable():
                self.search += event.unicode
                self._rebuild_list()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # catégories
            for name, rect in getattr(self, "_cat_rects", {}).items():
                if rect.collidepoint(event.pos):
                    self.category = name
                    self._rebuild_list()
            # termes
            for term, rect in getattr(self, "_term_rects", {}).items():
                if rect.collidepoint(event.pos):
                    self.selected_term = term
            if event.button == 4:
                self.scroll = max(0, self.scroll - 1)
            elif event.button == 5:
                self.scroll += 1

        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos())

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "GLOSSAIRE FINANCIER", (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"Recherche : {self.search}_",
                          (42, 74), fonts.small(), config.COL_CYAN)

        # --- Colonne catégories ---
        cat_panel = pygame.Rect(40, 110, 220, 560)
        inner = widgets.draw_panel(surf, cat_panel, "Catégories", config.COL_AMBER)
        self._cat_rects = {}
        y = inner.y
        for name in ["Tous"] + CATEGORIES:
            rect = pygame.Rect(inner.x-4, y-2, inner.w+8, 28)
            self._cat_rects[name] = rect
            sel = (name == self.category)
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            col = config.COL_CYAN if sel else config.COL_TEXT
            widgets.draw_text(surf, name, (inner.x+4, y+2), fonts.small(bold=sel), col)
            y += 30

        # --- Colonne termes ---
        term_panel = pygame.Rect(276, 110, 300, 560)
        inner2 = widgets.draw_panel(surf, term_panel,
                                    f"Termes ({len(self.terms)})", config.COL_CYAN)
        self._term_rects = {}
        y = inner2.y
        visible = self.terms[self.scroll:self.scroll+18]
        for term in visible:
            rect = pygame.Rect(inner2.x-4, y-2, inner2.w+8, 28)
            self._term_rects[term] = rect
            sel = (term == self.selected_term)
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            col = config.COL_AMBER if sel else config.COL_TEXT
            widgets.draw_text(surf, term, (inner2.x+4, y+2), fonts.small(bold=sel), col)
            y += 30

        # --- Définition ---
        def_panel = pygame.Rect(592, 110, config.SCREEN_WIDTH-632, 560)
        inner3 = widgets.draw_panel(surf, def_panel, "Définition", config.COL_AMBER)
        if self.selected_term and self.selected_term in GLOSSARY:
            cat, definition = GLOSSARY[self.selected_term]
            widgets.draw_text(surf, self.selected_term, (inner3.x, inner3.y),
                              fonts.head(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, f"[{cat}]", (inner3.x, inner3.y+34),
                              fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text_wrapped(surf, definition, (inner3.x, inner3.y+70),
                                      fonts.body(), config.COL_TEXT, inner3.w, line_gap=6)

        self.back_btn.draw(surf)
