"""
scene_runsetup.py — Réglages de la partie : scénario de départ, archétype de
run, mode hardcore. Étape intermédiaire entre le choix de région (continent)
et le lancement (intro), pour ne pas entasser tous ces réglages sur l'écran
de sélection de région.
"""
import random

import pygame

from core import archetypes, config
from core import profile as profile_mod
from core import startscenarios as scen
from core.game_state import GameState, PlayerState
from core.i18n import t
from core.scene_manager import Scene
from ui import fonts, widgets

CARD_H = 78
CARD_GAP = 8


class RunSetupScene(Scene):
    def on_enter(self, **kwargs):
        self.continent = kwargs.get("continent") or next(iter(config.CONTINENTS))
        self.scen_idx = 0
        self.arch_idx = 0
        self.hardcore = False
        self._scen_rects = {}
        self._arch_rects = {}
        self._hardcore_rect = None
        fy = config.SCREEN_HEIGHT - 50
        self.back_btn = widgets.Button((40, fy, 200, 42), t("runsetup.back"), config.COL_TEXT_DIM)
        self.confirm_btn = widgets.Button(
            (config.SCREEN_WIDTH-300, fy, 260, 42), t("runsetup.confirm"), config.COL_UP)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go("continent", preselect=self.continent)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go("continent", preselect=self.continent)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for idx, rect in self._scen_rects.items():
                if rect.collidepoint(event.pos):
                    self.scen_idx = idx
                    return
            for idx, rect in self._arch_rects.items():
                if rect.collidepoint(event.pos):
                    self.arch_idx = idx
                    return
            if self._hardcore_rect and self._hardcore_rect.collidepoint(event.pos):
                self.hardcore = not self.hardcore
                return
        if self.confirm_btn.handle(event):
            self._start_run()

    def _start_run(self):
        gs = GameState()
        gs.player = PlayerState(
            name="Trainee", continent=self.continent,
            grade_index=0, cash=config.START_CASH, reputation=50,
            hardcore=self.hardcore,
        )
        scen.apply(gs.player, scen.SCENARIOS[self.scen_idx]["id"])  # conditions de départ
        archetypes.apply(gs.player, archetypes.ARCHETYPES[self.arch_idx]["id"])  # philosophie de run
        # asymétrie novice/expert : un profil qui a déjà prouvé sa maîtrise dans
        # une partie antérieure démarre "vétéran" — complexité ouverte plus vite,
        # onboarding écourté (cf. CLAUDE.md, brief stratégique point 4).
        if profile_mod.is_veteran():
            gs.player.flags["veteran"] = True
            gs.player.onboarding_done = True
        from core import market as _mkt
        gs.player.market_seed = random.randint(1, 2_000_000_000)
        # démarre la carrière après 5 ans de marché : les graphes ont un passé
        gs.player.market_step = _mkt.WARMUP_STEPS
        self.app.gs = gs
        self.app.market = None   # forcera la (re)création du marché
        gs.save(config.AUTOSAVE_SLOT)
        self.app.scenes.go("intro")

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.confirm_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, t("runsetup.title"), (40, 24), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, t("runsetup.subtitle").format(continent=self.continent),
                          (42, 70), fonts.small(), config.COL_TEXT_DIM)

        fy = config.SCREEN_HEIGHT - 50
        hardcore_top = fy - 8 - 60
        top = 104
        bottom = hardcore_top - 12
        col_w = (config.SCREEN_WIDTH - 80 - 20) // 2

        scen_rect = pygame.Rect(40, top, col_w, bottom - top)
        arch_rect = pygame.Rect(40 + col_w + 20, top, col_w, bottom - top)

        self._scen_rects = self._draw_choice_list(
            surf, scen_rect, t("runsetup.scenario"), config.COL_CYAN,
            [(s["name"], self._scen_meta(s)) for s in scen.SCENARIOS], self.scen_idx)
        self._arch_rects = self._draw_choice_list(
            surf, arch_rect, t("runsetup.archetype"), config.COL_AMBER,
            [(a["name"], a["tagline"] + "  " + a["desc"]) for a in archetypes.ARCHETYPES], self.arch_idx)

        self._draw_hardcore_bar(surf, pygame.Rect(40, hardcore_top, config.SCREEN_WIDTH - 80, 60))

        self.back_btn.draw(surf)
        self.confirm_btn.draw(surf)

    @staticmethod
    def _scen_meta(s):
        return (f"Capital {widgets.format_money(s['cash'], '$')} · "
                f"grade {config.GRADES[s['grade_index']]} · réputation {s['reputation']}.  "
                + s["desc"])

    def _draw_choice_list(self, surf, panel_rect, title, accent, items, selected_idx):
        inner = widgets.draw_panel(surf, panel_rect, title, accent)
        rects = {}
        y = inner.y
        for i, (name, desc) in enumerate(items):
            rect = pygame.Rect(inner.x, y, inner.w, CARD_H)
            if rect.bottom > inner.bottom:
                break
            rects[i] = rect
            selected = (i == selected_idx)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if selected else config.COL_PANEL, rect)
            pygame.draw.rect(surf, accent if selected else config.COL_BORDER, rect, 2 if selected else 1)
            widgets.draw_text(surf, name, (rect.x+12, rect.y+8),
                              fonts.small(bold=True), accent if selected else config.COL_TEXT)
            widgets.draw_text_wrapped(surf, desc, (rect.x+12, rect.y+30),
                                      fonts.tiny(), config.COL_TEXT_DIM, rect.w-24, line_gap=2)
            y += CARD_H + CARD_GAP
        return rects

    def _draw_hardcore_bar(self, surf, rect):
        self._hardcore_rect = rect
        accent = config.COL_DOWN if self.hardcore else config.COL_WARN
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if self.hardcore else config.COL_PANEL, rect)
        pygame.draw.rect(surf, accent, rect, 2)
        label = t("runsetup.hardcore_title") + " : " + ("ON" if self.hardcore else "OFF")
        widgets.draw_text(surf, label, (rect.x+14, rect.y+9), fonts.small(bold=True), accent)
        desc = t("runsetup.hardcore_on") if self.hardcore else t("runsetup.hardcore_off")
        widgets.draw_text(surf, desc, (rect.x+14, rect.y+32), fonts.tiny(), config.COL_TEXT_DIM)
