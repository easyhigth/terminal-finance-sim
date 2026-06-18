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
    ]),
    ("Analyse & outils", [
        ("Graphes", "graph", {"kind": "line"}),
        ("Analyse portefeuille", "analytics", {}),
        ("Risque (VaR)", "risk", {}),
        ("Quant (options)", "quant", {}),
        ("M&A (cibles & LBO)", "ma", {}),
        ("Frontière efficiente", "portfolio", {}),
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
        self.back_btn = widgets.Button(config.back_button_rect(180),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
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
            for rect, scene, kw in self._btn_rects:
                if rect.collidepoint(event.pos):
                    self.app.scenes.go(scene, return_to="more", **kw)
                    return

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "PLUS — TOUTES LES PAGES", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Accès rapide à toutes les scènes du jeu. Clic = ouvrir.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        top = config.content_top()
        area = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - top)
        self._list_rect = area
        mp = pygame.mouse.get_pos()
        self._btn_rects = []
        prev_clip = surf.get_clip()
        surf.set_clip(area)
        y = area.y - self.scroll
        for title, items in SECTIONS:
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
                self._btn_rects.append((rect, scene, kw))
                if area.top - BTN_H < rect.y < area.bottom:
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
