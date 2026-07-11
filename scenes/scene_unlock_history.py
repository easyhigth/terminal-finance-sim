"""
scene_unlock_history.py — Écran « Historique des déblocages ».

Depuis le lot d'étalement du calendrier de déblocage (core/unlocks.UNLOCKS,
2-3 fonctionnalités par grade), la carte « NOUVEAU PÉRIMÈTRE » du bureau
(cf. core/unlock_briefs.py) annonce chaque déblocage à la promotion — mais
une fois la carte refermée, rien ne permettait de la reconsulter, ni de voir
ce qui reste à venir. Cet écran liste TOUS les grades avec leurs
fonctionnalités (atteints ✓, grade actuel ▶, à venir grisé — y compris un
aperçu des paliers qui n'ont pas encore été atteints, pour donner un objectif
concret à la prochaine promotion), et signale les modules verrouillés par un
choix de voie incompatible (cf. core.unlocks.track_lock_note).

Ouvert via un bouton dédié de scenes/scene_career.py ; return_to par défaut
"career".
"""
import pygame

from core import config, unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 26
GROUP_GAP = 14


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


class UnlockHistoryScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "career")
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._rebuild()

    def _rebuild(self):
        p = self.app.gs.player
        grades = sorted({unlocks.effective_required_grade(p, f) for f in unlocks.UNLOCKS})
        groups = []
        for g in grades:
            feats = unlocks.features_at_grade(p, g)
            if not feats:
                continue
            reached = p.grade_index >= g and g < unlocks.TRACK_LOCK_GRADE
            current = g == p.grade_index
            label = (config.GRADES[g] if g < len(config.GRADES) else
                     _L("Grade max (reconversion libre)", "Top grade (free reconversion)"))
            rows = []
            for f in feats:
                note = unlocks.track_lock_note(p, f)
                rows.append({"feature": f, "label": unlocks.feature_label(f), "note": note})
            groups.append({"grade": g, "grade_label": label, "reached": reached,
                           "current": current, "rows": rows})
        self.groups = groups

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def _group_height(self, group):
        return 26 + len(group["rows"]) * ROW_H + GROUP_GAP

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, _L("HISTORIQUE DES DÉBLOCAGES", "UNLOCK HISTORY"), (40, 28),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L(
            f"{p.grade} · ce que vous avez débloqué, et ce qui arrive.",
            f"{p.grade} · what you've unlocked, and what's next."),
            (42, 76), fonts.small(), config.COL_TEXT_DIM)

        top = 108
        panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - top)
        list_area = pygame.Rect(panel.x, panel.y, panel.w, panel.h)
        self._list_rect = list_area
        pygame.draw.rect(surf, config.COL_PANEL, list_area)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)

        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        for group in self.groups:
            gh = self._group_height(group)
            visible = (list_area.top - gh) < y < list_area.bottom
            if visible:
                self._draw_group(surf, group, list_area, y)
            y += gh
        surf.set_clip(prev_clip)
        content_h = y - (list_area.y - self.scroll)
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll,
                                             self._max_scroll, content_h)

        self.back_btn.draw(surf)

    def _draw_group(self, surf, group, area, y):
        if group["current"]:
            accent, mark = config.COL_AMBER, "▶"
        elif group["reached"]:
            accent, mark = config.COL_UP, "✓"
        else:
            accent, mark = config.COL_TEXT_DIM, "·"
        header = f"{mark} Grade {group['grade']} — {group['grade_label']}"
        widgets.draw_text(surf, header, (area.x + 8, y), fonts.small(bold=True), accent)
        yy = y + 22
        for r in group["rows"]:
            row = pygame.Rect(area.x + 6, yy - 2, area.w - 12, ROW_H - 4)
            if group["current"]:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            col = config.COL_TEXT if group["reached"] or group["current"] else config.COL_TEXT_DIM
            label = r["label"]
            if r["note"]:
                label += "  " + _L("(voie incompatible)", "(track mismatch)")
                col = config.COL_WARN if not (group["reached"] or group["current"]) else col
            widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), row.w - 16),
                              (row.x + 16, yy), fonts.tiny(), col)
            yy += ROW_H
