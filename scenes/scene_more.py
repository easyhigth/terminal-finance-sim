"""
scene_more.py — « PLUS » : raccourcis vers toutes les pages du jeu.

Grille de boutons regroupés par thème donnant accès en un clic à chaque scène
(page) navigable : marchés & actifs, analyse & outils, carrière & monde,
apprentissage, système. Ouvert via le bouton PLUS du rail ou la commande MORE.
"""
import pygame

from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

# (titre de section, [(libellé, scène, kwargs)])
SECTIONS = [
    ("Marchés & actifs", [
        ("Marché", "markethub", {}),
        ("Boutique (acheter tout actif)", "shop", {}),
        ("Explorateur", "explorer", {}),
        ("ETF", "etfs", {}),
        ("Obligations", "bonds", {}),
        ("Commodities", "commodities", {}),
        ("Crypto", "crypto", {}),
        ("Produits structurés", "structured", {}),
        ("Titrisation / ABS", "credit", {}),
        ("Swaps de devises", "swaps", {}),
        ("Gouvernements", "governments", {}),
        ("Desk FX", "fx", {}),
        ("Desk d'options (calls/puts)", "options", {}),
        ("IPO", "ipo", {}),
    ]),
    ("Analyse & outils", [
        ("Graphes", "graph", {"kind": "line"}),
        ("Analyse portefeuille", "analytics", {}),
        ("Risque (VaR)", "risk", {}),
        ("Quant (options)", "quant", {}),
        ("M&A (cibles & LBO)", "ma", {}),
        ("Frontière efficiente", "portfolio", {}),
        ("Couverture (hedge)", "hedge", {}),
        ("ALM bancaire", "alm", {}),
        ("Tableur", "spreadsheet", {}),
    ]),
    ("Carrière & monde", [
        ("Portefeuille", "book", {}),
        ("Carrière", "career", {}),
        ("Mission", "mission", {}),
        ("Exam / Certif", "examcert", {}),
        ("Voie (Track)", "track", {}),
        ("Rivaux", "rivals", {}),
        ("Inbox", "inbox", {}),
        ("News & événements", "news", {}),
        ("Calendrier macro", "calendar", {}),
        ("Mandats clients", "mandates", {}),
        ("Deals", "deals", {}),
        ("Historique complet", "history", {}),
        ("Stress test régulateur", "stresstest", {}),
        ("Équipe / analystes", "team", {}),
    ]),
    ("Apprendre", [
        ("Académie", "academy", {}),
        ("Tutoriels", "tutorials", {}),
        ("Glossaire", "glossary", {}),
        ("Certifications", "cert", {}),
        ("Aide / Commandes", "commands", {}),
    ]),
    ("Système", [
        ("Sauvegardes", "saves", {}),
    ]),
]

COLS = 4
BTN_W = 280
BTN_H = 40
BTN_GAP = 12


class MoreScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.scroll = 0
        self._max_scroll = 0
        self._btn_rects = []      # [(Rect, scene, kwargs)]
        self._list_rect = None
        self.search = ""
        self._search_clear_rect = None
        self._t = 0.0
        self.back_btn = widgets.Button(config.back_button_rect(180),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _search_rect(self):
        return pygame.Rect(40, 100, 320, 24)

    def _filtered_sections(self):
        q = self.search.strip().lower()
        if not q:
            return SECTIONS
        out = []
        for title, items in SECTIONS:
            kept = [(label, scene, kw) for label, scene, kw in items if q in label.lower()]
            if kept:
                out.append((title, kept))
        return out

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    self.scroll = 0
                    return
                self.app.scenes.go(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self.scroll = 0
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                self.scroll = 0
                return
            for rect, scene, kw in self._btn_rects:
                if rect.collidepoint(event.pos):
                    self.app.scenes.go(scene, return_to="more", **kw)
                    return

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "PLUS — TOUTES LES PAGES", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Accès rapide à toutes les scènes du jeu. Clic = ouvrir, "
                                "ou recherchez une page par nom.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        search_rect = self._search_rect()
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if self.search else config.COL_BORDER,
                          search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else "Rechercher une page…"
        txt_col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), txt_col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y,
                                                   22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        sections = self._filtered_sections()
        top = search_rect.bottom + 10
        area = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - top)
        self._list_rect = area
        mp = pygame.mouse.get_pos()
        self._btn_rects = []
        prev_clip = surf.get_clip()
        surf.set_clip(area)
        y = area.y - self.scroll
        if not sections:
            widgets.draw_text(surf, "Aucune page ne correspond à cette recherche.",
                              (area.x, area.y), fonts.small(), config.COL_TEXT_DIM)
        for title, items in sections:
            if area.top - 20 < y < area.bottom:
                widgets.draw_text(surf, f"— {title}", (area.x, y), fonts.small(bold=True),
                                  config.COL_PRESTIGE)
            y += 26
            for i, (label, scene, kw) in enumerate(items):
                col = i % COLS
                if col == 0 and i > 0:
                    y += BTN_H + BTN_GAP
                x = area.x + col * (BTN_W + BTN_GAP)
                rect = pygame.Rect(x, y, BTN_W, BTN_H)
                if area.top - BTN_H < rect.y < area.bottom:
                    # rect cliquable = intersection avec la zone visible : un bouton
                    # partiellement masqué par le clip ne doit pas déborder sur le
                    # bouton retour (footer) ni sur le reste de l'UI.
                    self._btn_rects.append((rect.clip(area), scene, kw))
                    hover = rect.collidepoint(mp)
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL,
                                     rect, border_radius=5)
                    pygame.draw.rect(surf, config.COL_AMBER if hover else config.COL_BORDER,
                                     rect, 1, border_radius=5)
                    widgets.draw_text(surf, label, rect.center, fonts.small(bold=hover),
                                      config.COL_AMBER if hover else config.COL_TEXT, align="center")
            y += BTN_H + BTN_GAP + 8
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - area.y
        self._max_scroll = max(0, content_h - area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        if self._max_scroll > 0:
            track = pygame.Rect(area.right + 2, area.y, 6, area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = area.h / (content_h or 1)
            bar_h = max(24, int(area.h * frac))
            bar_y = area.y + int((area.h - bar_h) * (self.scroll / self._max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

        self.back_btn.draw(surf)
