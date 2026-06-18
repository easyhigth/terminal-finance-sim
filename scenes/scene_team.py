"""
scene_team.py — Hub ÉQUIPE : recrutement d'analystes juniors (bonus passif
récurrent contre un coût récurrent par tour). Débloqué à un grade avancé
(cf. core/unlocks.py, clé "team"). Calqué sur scenes/scene_fx.py et
scenes/scene_mandates.py pour le style (panneau gauche = catalogue/action,
panneau droit = liste actuelle + licencier).
"""
import pygame
from core import config
from core import team as TEAM
from core import unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 70


class TeamScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "📘 TUTO", config.COL_CYAN)
        self.hire_rects = {}
        self.fire_rects = {}

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "team")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="team", return_to="team")
            return
        if not self._can():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = self.app.gs.player
            for pid, rect in self.hire_rects.items():
                if rect.collidepoint(event.pos):
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
                    return
            for idx, rect in self.fire_rects.items():
                if rect.collidepoint(event.pos):
                    r = TEAM.fire(p, idx)
                    if r["ok"]:
                        profile = TEAM.available_profiles().get(r["removed"]["profile_id"], {})
                        self.msg = f"{profile.get('label', '?')} licencié(e)."
                        if not p.hardcore:
                            self.app.gs.save(config.AUTOSAVE_SLOT)
                    return

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "ÉQUIPE — ANALYSTES JUNIORS", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can():
            g = unlocks.required_grade("team")
            widgets.draw_text(surf, f"⊘ Recrutement débloqué au grade {config.GRADES[g]}.",
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return

        p = self.app.gs.player
        cur = self._cur()
        widgets.draw_text(surf, "Recrutez des analystes juniors : bonus passif récurrent contre un salaire par tour. "
                          + self.msg, (42, 74), fonts.small(), config.COL_TEXT_DIM)

        # ---- catalogue (gauche) ----
        cat_rect = pygame.Rect(40, 110, 460, 420)
        inner = widgets.draw_panel(surf, cat_rect, "Profils disponibles", config.COL_CYAN)
        y = inner.y
        self.hire_rects = {}
        profiles = TEAM.available_profiles()
        for pid, profile in profiles.items():
            row = pygame.Rect(inner.x, y, inner.w, ROW_H - 8)
            pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
            widgets.draw_text(surf, profile["label"], (row.x + 10, row.y + 6),
                              fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{widgets.format_money(profile['cost_per_step'], cur)}/tour"
                              f"  ·  embauche {widgets.format_money(TEAM.HIRE_COST, cur)}",
                              (row.x + 10, row.y + 26), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, profile["desc"], (row.x + 10, row.y + 42),
                              fonts.tiny(), config.COL_TEXT_DIM)
            hire_btn = pygame.Rect(row.right - 90, row.y + 16, 80, 30)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, hire_btn, border_radius=4)
            pygame.draw.rect(surf, config.COL_UP, hire_btn, 1, border_radius=4)
            widgets.draw_text(surf, "EMBAUCHER", hire_btn.center, fonts.tiny(bold=True),
                              config.COL_UP, align="center")
            self.hire_rects[pid] = hire_btn
            y += ROW_H

        # ---- équipe actuelle (droite) ----
        team_rect = pygame.Rect(540, 110, config.SCREEN_WIDTH - 580, 420)
        tinner = widgets.draw_panel(surf, team_rect, f"Équipe actuelle ({len(p.analysts)})", config.COL_PRESTIGE)
        ty = tinner.y
        self.fire_rects = {}
        total_cost = TEAM.team_cost_per_step(p)
        total_rep = TEAM.team_bonus_rep_per_step(p)
        if not p.analysts:
            widgets.draw_text(surf, "Aucun analyste recruté. Embauchez dans le catalogue ci-contre.",
                              (tinner.x, ty), fonts.small(), config.COL_TEXT_DIM)
            ty += 26
        else:
            for idx, a in enumerate(p.analysts):
                profile = profiles.get(a.get("profile_id"), {})
                row = pygame.Rect(tinner.x, ty, tinner.w, ROW_H - 8)
                pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
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

        ty += 8
        widgets.draw_text(surf, f"Coût total récurrent : {widgets.format_money(total_cost, cur)}/tour"
                          f"  ·  bonus réputation passif : +{total_rep:.2f}/tour",
                          (tinner.x, ty), fonts.small(bold=True), config.COL_AMBER)

        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
