"""
scene_sandbox.py — Configuration du mode BAC À SABLE (sandbox).

Écran de lancement rapide d'un run jetable (PlayerState.sandbox=True) pour
tester portefeuilles, paramètres de marché, scénarios et stress tests SANS
jamais toucher aux sauvegardes réelles (cf. GameState.save() qui court-circuite
toute écriture quand player.sandbox est vrai — chokepoint unique, voir
core/game_state.py).

UI compacte en rangées de puces cliquables (chips), inspirée de FAMILY_CHIPS
dans scenes/scene_structured.py, plutôt qu'une liste de grandes cartes comme
scene_runsetup.py — tout doit tenir sur un seul écran.
"""
import random

import pygame

from core import config
from core.game_state import GameState, PlayerState
from core.i18n import t
from core.scene_manager import Scene
from ui import fonts, widgets

CASH_PRESETS = [250_000.0, 1_000_000.0, 10_000_000.0, 100_000_000.0]
REGIME_CHOICES = ["Aléatoire", "Calme", "Expansion", "Volatil", "Récession"]
CHIP_H = 28


class SandboxScene(Scene):
    def on_enter(self, **kwargs):
        self.continent = next(iter(config.CONTINENTS))
        self.cash_idx = 1          # 1M par défaut
        self.regime_idx = 0        # Aléatoire par défaut
        self.unlock_all = False

        self._continent_rects = {}
        self._cash_rects = {}
        self._regime_rects = {}
        self._unlock_rect = None

        self.back_btn = widgets.Button(config.back_button_rect(160), t("common.back"),
                                        config.COL_TEXT_DIM)
        self.start_btn = widgets.Button(
            (config.SCREEN_WIDTH - 300, config.back_button_rect()[1], 260, 42),
            t("sandbox.launch"), config.COL_UP)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go("menu")
            return
        if self.back_btn.handle(event):
            self.app.scenes.go("menu")
            return
        if self.start_btn.handle(event):
            self._start_sandbox()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self._continent_rects.items():
                if rect.collidepoint(event.pos):
                    self.continent = name
                    return
            for idx, rect in self._cash_rects.items():
                if rect.collidepoint(event.pos):
                    self.cash_idx = idx
                    return
            for idx, rect in self._regime_rects.items():
                if rect.collidepoint(event.pos):
                    self.regime_idx = idx
                    return
            if self._unlock_rect and self._unlock_rect.collidepoint(event.pos):
                self.unlock_all = not self.unlock_all
                return

    def _start_sandbox(self):
        gs = GameState()
        gs.player = PlayerState(
            name="Sandbox", continent=self.continent,
            grade_index=0, cash=CASH_PRESETS[self.cash_idx], reputation=50,
            sandbox=True,
        )
        if self.unlock_all:
            # même portée que la triche MAXUNLOCK (cf. scene_terminal_commands._cmd_cheat) :
            # grade max + réputation haute + déblocage du choix de voie.
            gs.player.grade_index = len(config.GRADES) - 1
            gs.player.reputation = max(gs.player.reputation, 80)
            gs.player.flags["can_choose_track"] = True

        gs.player.market_seed = random.randint(1, 2_000_000_000)
        gs.player.market_step = 0

        self.app.gs = gs
        self.app.market = None   # forcera la (re)création du marché
        market = self.app.ensure_market()

        regime = REGIME_CHOICES[self.regime_idx]
        if regime != "Aléatoire":
            market.regime = regime
            market.regime_since = market.step_count

        # ne JAMAIS appeler gs.save() ici : run jetable, voir docstring du module.
        self.app.scenes.go("desktop")

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.start_btn.update(mp, dt)

    def _draw_chip_row(self, surf, x0, y, label, items, selected_idx_or_key, rects_out,
                        key_fn=None):
        widgets.draw_text(surf, label, (x0, y), fonts.small(bold=True), config.COL_TEXT_DIM)
        y += 22
        fx = x0
        for i, item in enumerate(items):
            key = key_fn(item) if key_fn else i
            text = item if isinstance(item, str) else str(item)
            w = fonts.tiny(bold=True).size(text)[0] + 18
            rect = pygame.Rect(fx, y, w, CHIP_H)
            rects_out[key] = rect
            sel = (key == selected_idx_or_key)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                              rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                              rect, 2 if sel else 1, border_radius=4)
            widgets.draw_text(surf, text, rect.center, fonts.tiny(bold=sel),
                               config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            fx += w + 8
        return y + CHIP_H + 26

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, t("sandbox.title"), (40, 26), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, t("sandbox.subtitle"), (42, 76), fonts.small(), config.COL_TEXT_DIM)

        x0 = 40
        y = 116

        self._continent_rects = {}
        y = self._draw_chip_row(surf, x0, y, t("sandbox.continent"),
                                 list(config.CONTINENTS.keys()), self.continent,
                                 self._continent_rects, key_fn=lambda v: v)

        self._cash_rects = {}
        cash_labels = [widgets.format_money(c, "$") for c in CASH_PRESETS]
        y = self._draw_chip_row(surf, x0, y, t("sandbox.cash"),
                                 cash_labels, self.cash_idx, self._cash_rects,
                                 key_fn=None)
        # _draw_chip_row utilise l'index de la liste comme clé quand key_fn=None,
        # donc self._cash_rects est déjà indexé par cash_idx.

        self._regime_rects = {}
        y = self._draw_chip_row(surf, x0, y, t("sandbox.regime"),
                                 REGIME_CHOICES, self.regime_idx, self._regime_rects,
                                 key_fn=None)

        # toggle "tout débloquer"
        widgets.draw_text(surf, t("sandbox.unlock_label"), (x0, y), fonts.small(bold=True),
                           config.COL_TEXT_DIM)
        y += 22
        toggle_w = fonts.tiny(bold=True).size(t("sandbox.unlock_all"))[0] + 18
        self._unlock_rect = pygame.Rect(x0, y, toggle_w, CHIP_H)
        on = self.unlock_all
        accent = config.COL_DOWN if on else config.COL_BORDER
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if on else config.COL_PANEL,
                          self._unlock_rect, border_radius=4)
        pygame.draw.rect(surf, accent, self._unlock_rect, 2 if on else 1, border_radius=4)
        label = t("sandbox.unlock_all") + " : " + ("ON" if on else "OFF")
        widgets.draw_text(surf, label, self._unlock_rect.center, fonts.tiny(bold=on),
                           config.COL_DOWN if on else config.COL_TEXT_DIM, align="center")
        y += CHIP_H + 30

        widgets.draw_text_wrapped(surf, t("sandbox.hint"), (x0, y), fonts.tiny(),
                                   config.COL_TEXT_DIM, config.SCREEN_WIDTH - 80, line_gap=3)

        self.back_btn.draw(surf)
        self.start_btn.draw(surf)
