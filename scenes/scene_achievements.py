"""
scene_achievements.py — Écran dédié « Succès » : TOUS les badges (jalons +
séries à enjeu, cf. core/badges.py), obtenus en couleur, VERROUILLÉS grisés
avec une jauge de progression pour ceux à seuil numérique clair.

Distinct de la galerie inline de scenes/scene_career.py, qui ne montre que les
badges déjà obtenus (pas de vue d'ensemble de ce qu'il reste à débloquer).
Ouvert via ACHIEVEMENTS/SUCCES depuis le terminal, ou le hub PLUS.
"""
import pygame

from core import badges as badges_mod
from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 64


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


class AchievementsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._rebuild()

    def _rebuild(self):
        """Construit la liste unifiée (badge classique, obtenu/verrouillé) +
        (badge à enjeu, obtenu/verrouillé/révoqué n'a pas de sens ici — on
        montre juste l'état courant)."""
        p = self.app.gs.player
        m = self.app.market
        rows = []
        for b in badges_mod.all_badges():
            obtained = b["id"] in p.badges
            prog = None if obtained else badges_mod.progress_for(b, p, m)
            rows.append({"name": badges_mod.badge_name(b), "desc": badges_mod.badge_desc(b),
                        "obtained": obtained, "progress": prog, "streak": False})
        for b in badges_mod.all_streak_badges():
            held = b["id"] in getattr(p, "streak_badges", [])
            streak = p.flags.get(b["streak_flag"], 0)
            prog = None if held else (float(streak), float(b["target"]))
            rows.append({"name": badges_mod.streak_badge_name(b), "desc": badges_mod.streak_badge_desc(b),
                        "obtained": held, "progress": prog, "streak": True})
        rows.sort(key=lambda r: (not r["obtained"], r["name"]))
        self.rows = rows

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

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        n_obtained = sum(1 for r in self.rows if r["obtained"])
        widgets.draw_text(surf, _L("SUCCÈS", "ACHIEVEMENTS"), (40, 28),
                          fonts.title(bold=True), config.COL_PRESTIGE)
        widgets.draw_text(surf, f"{n_obtained} / {len(self.rows)}", (42, 76),
                          fonts.small(bold=True), config.COL_TEXT_DIM)

        panel = pygame.Rect(40, 110, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - 110)
        list_area = pygame.Rect(panel.x, panel.y, panel.w, panel.h)
        self._list_rect = list_area
        pygame.draw.rect(surf, config.COL_PANEL, list_area)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)

        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        for r in self.rows:
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                self._draw_row(surf, r, list_area, y)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = len(self.rows) * ROW_H
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)

    def _draw_row(self, surf, r, area, y):
        row = pygame.Rect(area.x + 6, y + 2, area.w - 12, ROW_H - 6)
        obtained = r["obtained"]
        accent = config.COL_PRESTIGE if obtained else config.COL_TEXT_DIM
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if obtained else config.COL_BG, row, border_radius=4)
        pygame.draw.rect(surf, accent, row, 1, border_radius=4)

        mark = "✓" if obtained else "·"
        widgets.draw_text(surf, mark, (row.x + 10, row.y + 8), fonts.head(bold=True), accent)
        name_col = config.COL_PRESTIGE if obtained else config.COL_TEXT
        widgets.draw_text(surf, r["name"], (row.x + 34, row.y + 4), fonts.small(bold=True), name_col)
        if r["streak"]:
            widgets.draw_badge(surf, _L("SÉRIE", "STREAK"), (row.right - 10, row.y + 4),
                               config.COL_CYAN, align="right")
        widgets.draw_text(surf, widgets.fit_text(r["desc"], fonts.tiny(), row.w - 44),
                          (row.x + 34, row.y + 24), fonts.tiny(), config.COL_TEXT_DIM)

        if not obtained and r["progress"] is not None:
            cur, target = r["progress"]
            ratio = 0.0 if target <= 0 else min(1.0, cur / target)
            bar = pygame.Rect(row.x + 34, row.y + 42, row.w - 140, 12)
            widgets.draw_progress(surf, bar, ratio, accent=config.COL_PRESTIGE, bg=config.COL_BG)
            label = f"{cur:,.0f} / {target:,.0f}" if target >= 100 else f"{cur:.0f} / {target:.0f}"
            widgets.draw_text(surf, label, (bar.right + 8, bar.y - 2), fonts.tiny(), config.COL_TEXT_DIM)
