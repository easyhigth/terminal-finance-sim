"""
app_manual.py — Application « Manuel » du bureau.

Toutes les fiches de fonctionnalités (core/unlock_briefs.FEATURE_BRIEFS)
réunies dans UNE app consultable et cherchable. Jusqu'ici, une fiche n'était
visible qu'au moment de la promotion (carte « Nouveautés ») puis disparaissait
— le Manuel les rend relisibles à tout moment : colonne gauche = liste
filtrable des fonctionnalités (celles encore verrouillées sont marquées),
panneau droit = la fiche complète (quoi / comment / pourquoi / premiers pas).

Zéro contenu nouveau : tout vient des fiches existantes, la couche EN
comprise (unlock_briefs.brief_for résout la langue courante).
"""
import pygame

from apps.base import DesktopApp
from core import audio, config, unlock_briefs, unlocks
from core.i18n import get_lang
from ui import fonts, widgets

ROW_H = 24


def _L(fr, en):
    return en if get_lang() == "en" else fr


class ManualApp(DesktopApp):
    title = "Manuel"
    icon_kind = "help"
    default_size = (760, 500)
    min_size = (560, 320)

    def on_open(self):
        self.search = ""
        self.selected = None       # clé de fonctionnalité affichée à droite
        self.scroll = 0            # défilement de la liste de gauche
        self.body_scroll = 0       # défilement de la fiche de droite
        self._row_rects = {}       # feature -> Rect
        self._list_rect = None
        self._body_rect = None
        entries = self._entries()
        if entries:
            self.selected = entries[0][0]

    def _entries(self):
        """[(feature, titre localisé, verrouillée)] triés par grade requis puis
        titre — mêmes données que la carte « Nouveautés » des promotions."""
        p = self.app.gs.player
        out = []
        for feat in unlock_briefs.FEATURE_BRIEFS:
            brief = unlock_briefs.brief_for(feat)
            if not brief:
                continue
            required = unlocks.effective_required_grade(p, feat)
            locked = p.grade_index < required
            out.append((feat, brief["title"], locked, required))
        out.sort(key=lambda e: (e[3], e[1].lower()))
        q = self.search.strip().lower()
        if q:
            out = [e for e in out if q in e[1].lower() or q in e[0]]
        return [(f, t, lk) for f, t, lk, _r in out]

    # ------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and self.search:
                self.search = ""
                self.scroll = 0
                return True
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self.scroll = 0
                return True
            if event.unicode and event.unicode.isprintable():
                self.search += event.unicode
                self.scroll = 0
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -ROW_H * 2 if event.button == 4 else ROW_H * 2
            if self._body_rect and self._body_rect.collidepoint(event.pos):
                self.body_scroll = max(0, self.body_scroll + delta)
            elif self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, self.scroll + delta)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for feat, r in self._row_rects.items():
                if r.collidepoint(event.pos):
                    self.selected = feat
                    self.body_scroll = 0
                    audio.play("click")
                    return True
        return False

    # --------------------------------------------------------------- draw
    def draw(self, surf, rect):
        pygame.draw.rect(surf, config.COL_BG, rect)
        pad = 10
        list_w = max(220, rect.w // 3)
        list_rect = pygame.Rect(rect.x + pad, rect.y + pad,
                                list_w, rect.h - 2 * pad)
        body_rect = pygame.Rect(list_rect.right + pad, rect.y + pad,
                                rect.right - list_rect.right - 2 * pad,
                                rect.h - 2 * pad)
        self._draw_list(surf, list_rect)
        self._draw_body(surf, body_rect)

    def _draw_list(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, _L("Fiches", "Guides"), config.COL_CYAN)
        # champ de recherche
        q = self.search or _L("Filtrer…", "Filter…")
        q_col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text("⌕ " + q, fonts.tiny(), inner.w),
                          (inner.x, inner.y), fonts.tiny(), q_col)
        list_area = pygame.Rect(inner.x, inner.y + 20, inner.w, inner.h - 20)
        self._list_rect = list_area
        self._row_rects = {}
        entries = self._entries()
        max_scroll = max(0, len(entries) * ROW_H - list_area.h)
        self.scroll = min(self.scroll, max_scroll)
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        mp = pygame.mouse.get_pos()
        for feat, title, locked in entries:
            r = pygame.Rect(list_area.x, y, list_area.w, ROW_H)
            if r.bottom >= list_area.top and r.top <= list_area.bottom:
                self._row_rects[feat] = r
                active = feat == self.selected
                if active:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, r)
                col = (config.COL_TEXT_DIM if locked
                       else widgets.hover_accent(active or r.collidepoint(mp)))
                label = title + (_L("  · verrouillé", "  · locked") if locked else "")
                widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), r.w - 8),
                                  (r.x + 4, r.y + 5), fonts.tiny(), col)
            y += ROW_H
        surf.set_clip(prev_clip)
        if not entries:
            widgets.draw_text(surf, _L("Aucune fiche ne correspond.",
                                       "No guide matches."),
                              (list_area.x, list_area.y), fonts.tiny(),
                              config.COL_TEXT_DIM)

    def _draw_body(self, surf, rect):
        brief = unlock_briefs.brief_for(self.selected) if self.selected else None
        title = brief["title"] if brief else _L("Manuel", "Manual")
        inner = widgets.draw_panel(surf, rect, title, config.COL_AMBER)
        self._body_rect = inner
        if not brief:
            widgets.draw_text_wrapped(
                surf, _L("Sélectionnez une fiche à gauche.",
                         "Select a guide on the left."),
                (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM, inner.w)
            return
        sections = [
            (_L("QUOI", "WHAT"), brief.get("what", "")),
            (_L("COMMENT", "HOW"), brief.get("how", "")),
            (_L("POURQUOI", "WHY"), brief.get("why", "")),
            (_L("PREMIERS PAS", "FIRST STEPS"), brief.get("first", "")),
        ]
        prev_clip = surf.get_clip()
        surf.set_clip(inner)
        y = inner.y - self.body_scroll
        for label, text in sections:
            if not text:
                continue
            widgets.draw_text(surf, label, (inner.x, y), fonts.tiny(bold=True),
                              config.COL_CYAN)
            y += 18
            y += widgets.draw_text_wrapped(surf, text, (inner.x, y), fonts.tiny(),
                                           config.COL_TEXT, inner.w, line_gap=4)
            y += 12
        surf.set_clip(prev_clip)
        content_h = (y + self.body_scroll) - inner.y
        self.body_scroll = max(0, min(self.body_scroll,
                                      max(0, content_h - inner.h)))
