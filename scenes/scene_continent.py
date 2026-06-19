"""
scene_continent.py — Choix du continent de départ.
Affiche le globe interactif + panneaux réglementaires par région.
"""
import pygame

from core import archetypes, config
from core import startscenarios as scen
from core.game_state import GameState, PlayerState
from core.i18n import t
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.globe import Globe


class ContinentScene(Scene):
    def on_enter(self, **kwargs):
        self.globe = Globe((345, 360), 190)
        self.selected = None
        self.hardcore = kwargs.get("hardcore", False)
        self.scen_idx = 0          # scénario de départ sélectionné
        self.arch_idx = 0         # archétype de run sélectionné (philosophie de jeu)
        fy = config.SCREEN_HEIGHT - 50
        self.back_btn = widgets.Button((40, fy, 150, 42), t("common.back"), config.COL_TEXT_DIM)
        self.scen_btn = widgets.Button((460, fy, 300, 42),
                                       "SCÉNARIO : " + scen.SCENARIOS[0]["name"], config.COL_CYAN)
        self.arch_btn = widgets.Button((770, fy, 200, 42),
                                       "ARCHÉTYPE : " + archetypes.ARCHETYPES[0]["name"], config.COL_AMBER)
        self.hardcore_btn = widgets.Button(
            (200, fy, 250, 42), t("continent.hardcore_off"), config.COL_WARN)
        self.confirm_btn = widgets.Button(
            (config.SCREEN_WIDTH-300, fy, 260, 42),
            t("continent.confirm"), config.COL_UP, enabled=False)
        self.card_cursor = 0  # curseur clavier dans la grille de cartes régionales

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            region = self.globe.region_at(event.pos)
            if region:
                self.selected = region
                self.confirm_btn.enabled = True
            # clic sur les cartes de droite
            for name, rect in getattr(self, "_card_rects", {}).items():
                if rect.collidepoint(event.pos):
                    self.selected = name
                    self.confirm_btn.enabled = True

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN,
                                                            pygame.K_RETURN, pygame.K_KP_ENTER):
            names = list(config.CONTINENTS.keys())
            self.card_cursor, activate = widgets.list_key_nav(event, self.card_cursor, len(names))
            if activate and names:
                self.selected = names[self.card_cursor]
                self.confirm_btn.enabled = True

        if self.back_btn.handle(event):
            self.app.scenes.go("menu")
        if self.scen_btn.handle(event):
            self.scen_idx = (self.scen_idx + 1) % len(scen.SCENARIOS)
            self.scen_btn.label = "SCÉNARIO : " + scen.SCENARIOS[self.scen_idx]["name"]
        if self.arch_btn.handle(event):
            self.arch_idx = (self.arch_idx + 1) % len(archetypes.ARCHETYPES)
            self.arch_btn.label = "ARCHÉTYPE : " + archetypes.ARCHETYPES[self.arch_idx]["name"]
        if self.hardcore_btn.handle(event):
            self.hardcore = not self.hardcore
            self.hardcore_btn.label = t("continent.hardcore_on") if self.hardcore else t("continent.hardcore_off")
            self.hardcore_btn.accent = config.COL_DOWN if self.hardcore else config.COL_WARN
        if self.confirm_btn.handle(event) and self.selected:
            gs = GameState()
            gs.player = PlayerState(
                name="Trainee", continent=self.selected,
                grade_index=0, cash=config.START_CASH, reputation=50,
                hardcore=getattr(self, "hardcore", False),
            )
            scen.apply(gs.player, scen.SCENARIOS[self.scen_idx]["id"])  # conditions de départ
            archetypes.apply(gs.player, archetypes.ARCHETYPES[self.arch_idx]["id"])  # philosophie de run
            import random as _r

            from core import market as _mkt
            gs.player.market_seed = _r.randint(1, 2_000_000_000)
            # démarre la carrière après 5 ans de marché : les graphes ont un passé
            gs.player.market_step = _mkt.WARMUP_STEPS
            self.app.gs = gs
            self.app.market = None   # forcera la (re)création du marché
            gs.save(config.AUTOSAVE_SLOT)
            self.app.scenes.go("intro")

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.globe.update(dt, mp)
        self.confirm_btn.update(mp, dt)
        self.back_btn.update(mp, dt)
        self.hardcore_btn.update(mp, dt)
        self.scen_btn.update(mp, dt)
        self.arch_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, t("continent.title"),
                          (40, 30), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, t("continent.subtitle"),
                          (42, 80), fonts.small(), config.COL_TEXT_DIM)

        self.globe.draw(surf)
        widgets.draw_text(surf, t("continent.hint"),
                          (345, 565), fonts.small(), config.COL_TEXT_DIM, align="center")

        # cartes réglementaires à droite, en grille 2 colonnes (7 régions)
        self._card_rects = {}
        names = list(config.CONTINENTS.keys())
        self.card_cursor = min(self.card_cursor, len(names) - 1) if names else 0
        x0 = 700
        y0 = 120
        cw, ch, gx, gy = 280, 124, 16, 12
        for i, (name, info) in enumerate(config.CONTINENTS.items()):
            col = i % 2
            row = i // 2
            x = x0 + col * (cw + gx)
            y = y0 + row * (ch + gy)
            rect = pygame.Rect(x, y, cw, ch)
            self._card_rects[name] = rect
            accent = info["color"]
            selected = (self.selected == name)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if selected else config.COL_PANEL, rect)
            pygame.draw.rect(surf, accent if selected else config.COL_BORDER,
                             rect, 2 if selected else 1)
            widgets.draw_row_selection(surf, rect, i == self.card_cursor)
            widgets.draw_text(surf, name.upper(), (x+12, y+8),
                              fonts.body(bold=True), accent)
            widgets.draw_text(surf, info["regulator"], (x+12, y+34),
                              fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{t('continent.currency')} : {info['currency']}", (x+12, y+54),
                              fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text_wrapped(surf, info["blurb"], (x+12, y+74),
                                      fonts.tiny(), config.COL_NEUTRAL, cw-24, line_gap=2)

        # description du scénario de départ + de l'archétype de run sélectionnés
        sc = scen.SCENARIOS[self.scen_idx]
        arch = archetypes.ARCHETYPES[self.arch_idx]
        widgets.draw_text(surf, f"Scénario : {sc['name']} — capital "
                          f"{widgets.format_money(sc['cash'], '$')}, "
                          f"grade {config.GRADES[sc['grade_index']]}, réputation {sc['reputation']}"
                          f"   ·   Archétype : {arch['name']} — {arch['tagline']}",
                          (40, config.SCREEN_HEIGHT - 132), fonts.tiny(bold=True), config.COL_CYAN)
        widgets.draw_text_wrapped(surf, sc["desc"] + "  —  " + arch["desc"],
                                  (40, config.SCREEN_HEIGHT - 116),
                                  fonts.tiny(), config.COL_TEXT_DIM, 700, line_gap=2)
        self.hardcore_btn.draw(surf)
        self.scen_btn.draw(surf)
        self.arch_btn.draw(surf)
        self.confirm_btn.draw(surf)
        self.back_btn.draw(surf)
