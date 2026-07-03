"""
scene_team.py — Hub ÉQUIPE : recrutement d'analystes juniors (bonus passif
récurrent contre un coût récurrent par tour). Débloqué à un grade avancé
(cf. core/unlocks.py, clé "team"). Calqué sur scenes/scene_fx.py et
scenes/scene_mandates.py pour le style (panneau gauche = catalogue/action,
panneau droit = liste actuelle + licencier).
"""
import pygame

from core import config, unlocks
from core import team as TEAM
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, keynav, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr

ROW_H = 70        # hauteur de ligne "équipe actuelle" (pas de description longue)
CAT_ROW_H = 92    # hauteur de ligne "profils disponibles" (laisse la place à la description)


class TeamScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "TUTO", config.COL_CYAN)
        self.hire_rects = {}
        self.fire_rects = {}
        self.hire_cursor = 0   # curseur clavier liste "profils disponibles"
        self.fire_cursor = 0   # curseur clavier liste "équipe actuelle"
        self.focus = "hire"    # "hire" ou "fire" — liste qui reçoit HAUT/BAS/ENTRÉE
        self.scroll = 0        # défilement de l'équipe actuelle (sans limite d'effectif)
        self._max_scroll = 0
        self._list_rect = None

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "team")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="team", return_to="team")
            return
        if not self._can():
            return
        p = self.app.gs.player
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.focus = "fire" if self.focus == "hire" else "hire"
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN,
                                                            pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.focus == "hire":
                pids = list(TEAM.available_profiles().keys())
                self.hire_cursor, activate = widgets.list_key_nav(event, self.hire_cursor, len(pids))
                if activate and pids:
                    self._do_hire(pids[self.hire_cursor])
            else:
                count = len(p.analysts)
                self.fire_cursor, activate = widgets.list_key_nav(event, self.fire_cursor, count)
                self._scroll_to_fire_cursor()
                if activate and count:
                    self._do_fire(self.fire_cursor)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for pid, rect in self.hire_rects.items():
                if rect.collidepoint(event.pos):
                    self._do_hire(pid)
                    return
            for idx, rect in self.fire_rects.items():
                if rect.collidepoint(event.pos):
                    self._do_fire(idx)
                    return

    def _do_hire(self, pid):
        p = self.app.gs.player
        r = TEAM.hire(p, pid)
        profile = TEAM.available_profiles().get(pid, {})
        if r["ok"]:
            self.msg = f"{profile.get('label', pid)} recruté(e)."
            if not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        else:
            reasons = {"grade": "grade insuffisant", "budget": "trésorerie insuffisante",
                       "unknown_profile": "profil inconnu"}
            self.msg = f"Refusé ({reasons.get(r['reason'], r['reason'])})."

    def _do_fire(self, idx):
        p = self.app.gs.player
        r = TEAM.fire(p, idx)
        if r["ok"]:
            profile = TEAM.available_profiles().get(r["removed"]["profile_id"], {})
            self.msg = f"{profile.get('label', '?')} licencié(e)."
            if not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)

    def _scroll_to_fire_cursor(self):
        """Ajuste le scroll de l'équipe actuelle pour garder le curseur clavier visible."""
        if not self._list_rect:
            return
        row_top = self.fire_cursor * ROW_H
        row_bottom = row_top + ROW_H
        if row_top < self.scroll:
            self.scroll = row_top
        elif row_bottom > self.scroll + self._list_rect.h:
            self.scroll = row_bottom - self._list_rect.h
        self.scroll = max(0, min(self._max_scroll, self.scroll))

    def _focus_hints(self):
        action = _L("embaucher", "hire") if self.focus == "hire" else _L("licencier", "fire")
        return [("↑↓", _L("analyste", "analyst")), (_L("ENTRÉE", "ENTER"), action),
                ("TAB", _L("volet", "panel"))]

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "ÉQUIPE — ANALYSTES JUNIORS", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "team")
            widgets.draw_text(surf, f"⊘ Recrutement débloqué au grade {config.GRADES[g]}.",
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return

        p = self.app.gs.player
        cur = self._cur()
        intro = "Recrutez des analystes juniors : bonus passif récurrent contre un salaire par tour. " + self.msg
        widgets.draw_text_wrapped(surf, intro, (42, 74), fonts.small(), config.COL_TEXT_DIM,
                                  config.SCREEN_WIDTH - 84, line_gap=4)

        # ---- catalogue (gauche) ----
        cat_rect = pygame.Rect(40, 110, 460, 420)
        inner = widgets.draw_panel(surf, cat_rect, "Profils disponibles", config.COL_CYAN)
        y = inner.y
        self.hire_rects = {}
        profiles = TEAM.available_profiles()
        pids = list(profiles.keys())
        self.hire_cursor = min(self.hire_cursor, len(pids) - 1) if pids else 0
        for i, (pid, profile) in enumerate(profiles.items()):
            row = pygame.Rect(inner.x, y, inner.w, CAT_ROW_H - 8)
            pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
            if self.focus == "hire":
                keynav.draw_focus_ring(surf, row, i == self.hire_cursor)
            hire_btn = pygame.Rect(row.right - 90, row.y + 8, 80, 26)
            widgets.draw_text(surf, profile["label"], (row.x + 10, row.y + 6),
                              fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{widgets.format_money(profile['cost_per_step'], cur)}/tour"
                              f"  ·  embauche {widgets.format_money(TEAM.HIRE_COST, cur)}",
                              (row.x + 10, row.y + 26), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text_wrapped(surf, profile["desc"], (row.x + 10, row.y + 44),
                                      fonts.tiny(), config.COL_TEXT_DIM, row.w - 20, line_gap=2)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, hire_btn, border_radius=4)
            pygame.draw.rect(surf, config.COL_UP, hire_btn, 1, border_radius=4)
            widgets.draw_text(surf, "EMBAUCHER", hire_btn.center, fonts.tiny(bold=True),
                              config.COL_UP, align="center")
            self.hire_rects[pid] = hire_btn
            y += CAT_ROW_H

        # ---- équipe actuelle (droite) ----
        team_rect = pygame.Rect(540, 110, config.SCREEN_WIDTH - 580, 420)
        tinner = widgets.draw_panel(surf, team_rect, f"Équipe actuelle ({len(p.analysts)})", config.COL_PRESTIGE)
        total_cost = TEAM.team_cost_per_step(p)
        total_rep = TEAM.team_bonus_rep_per_step(p)
        footer_h = 26
        list_area = pygame.Rect(tinner.x - 4, tinner.y, tinner.w + 8, tinner.h - footer_h)
        self._list_rect = list_area
        self.fire_rects = {}
        if not p.analysts:
            widgets.draw_text(surf, "Aucun analyste recruté. Embauchez dans le catalogue ci-contre.",
                              (tinner.x, tinner.y), fonts.small(), config.COL_TEXT_DIM)
            self.scroll = self._max_scroll = 0
        else:
            self.fire_cursor = min(self.fire_cursor, len(p.analysts) - 1) if p.analysts else 0
            prev_clip = surf.get_clip()
            surf.set_clip(list_area)
            ty = tinner.y - self.scroll
            for idx, a in enumerate(p.analysts):
                if (list_area.top - ROW_H) < ty < list_area.bottom:
                    profile = profiles.get(a.get("profile_id"), {})
                    row = pygame.Rect(tinner.x, ty, tinner.w, ROW_H - 8)
                    pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
                    pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
                    if self.focus == "fire":
                        keynav.draw_focus_ring(surf, row, idx == self.fire_cursor)
                    widgets.draw_text(surf, profile.get("label", a.get("profile_id", "?")),
                                      (row.x + 10, row.y + 6), fonts.small(bold=True), config.COL_TEXT)
                    widgets.draw_text(surf, f"Coût : {widgets.format_money(profile.get('cost_per_step', 0), cur)}/tour",
                                      (row.x + 10, row.y + 26), fonts.tiny(), config.COL_TEXT_DIM)
                    fire_btn = pygame.Rect(row.right - 100, row.y + 16, 90, 30)
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, fire_btn, border_radius=4)
                    pygame.draw.rect(surf, config.COL_DOWN, fire_btn, 1, border_radius=4)
                    widgets.draw_text(surf, "LICENCIER", fire_btn.center, fonts.tiny(bold=True),
                                      config.COL_DOWN, align="center")
                    self.fire_rects[idx] = fire_btn
                ty += ROW_H
            surf.set_clip(prev_clip)
            content_h = (ty + self.scroll) - tinner.y
            self._max_scroll = max(0, content_h - list_area.h)
            self.scroll = min(self.scroll, self._max_scroll)
            self.scroll = widgets.draw_scrollbar(surf, team_rect, list_area, self.scroll, self._max_scroll, content_h)

        widgets.draw_text(surf, f"Coût total récurrent : {widgets.format_money(total_cost, cur)}/tour"
                          f"  ·  bonus réputation passif : +{total_rep:.2f}/tour",
                          (tinner.x, list_area.bottom + 6), fonts.small(bold=True), config.COL_AMBER)

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14), self._focus_hints())
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
