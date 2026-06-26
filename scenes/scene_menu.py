"""
scene_menu.py — Écran titre / menu principal.
Bouton CONTINUER (reprend l'autosave) + résumé de la dernière partie.
"""
import math

import pygame

from core import anim_settings, config
from core.game_state import GameState
from core.i18n import get_lang, t, toggle_lang
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.logo import draw_ta_logo

# Ticker décoratif — tickers fictifs cohérents avec l'univers du jeu
_TICKER = ("MVC +1.2%   LWNH -0.4%   C&D500 +0.7%   KAK40 +0.3%   MIRC +0.9%   "
           "TSMX -1.1%   NKX225 +0.5%   POME +0.2%   EURUSD 1.0842   ")


class MenuScene(Scene):
    def on_enter(self, **kwargs):
        cx = config.SCREEN_WIDTH // 2
        bw, bh, gap = 320, 46, 10
        # y0 démarre sous le panneau "dernière partie" (cf. _draw_last_run, qui
        # se termine à panel.bottom = 413) pour éviter le chevauchement bouton/panneau.
        y0 = 427
        self.auto = GameState.slot_meta(config.AUTOSAVE_SLOT)
        self.buttons = {
            "continue": widgets.Button((cx-bw//2, y0,              bw, bh), t("menu.continue"), config.COL_UP),
            "new":      widgets.Button((cx-bw//2, y0+(bh+gap),     bw, bh), t("menu.new"), config.COL_AMBER),
            "load":     widgets.Button((cx-bw//2, y0+(bh+gap)*2,   bw, bh), t("menu.load"), config.COL_CYAN),
            "sandbox":  widgets.Button((cx-bw//2, y0+(bh+gap)*3,   bw, bh), t("menu.sandbox"), config.COL_NEUTRAL),
            "quit":     widgets.Button((cx-bw//2, y0+(bh+gap)*4,   bw, bh), t("menu.quit"), config.COL_DOWN),
        }
        # bouton de langue (en haut à droite)
        self.lang_btn = widgets.Button((config.SCREEN_WIDTH-150, 40, 110, 34),
                                       f"LANG : {get_lang().upper()}", config.COL_CYAN)
        # bouton "réduire les animations" (accessibilité/perf — sous LANG)
        self.anim_btn = widgets.Button((config.SCREEN_WIDTH-150, 80, 110, 34),
                                       self._anim_label(), config.COL_NEUTRAL)
        # bouton réglages complets (affichage, son, langue… — sous ANIM)
        self.settings_btn = widgets.Button((config.SCREEN_WIDTH-150, 120, 110, 34),
                                           "⚙ RÉGLAGES", config.COL_AMBER)
        self.buttons["continue"].enabled = self.auto is not None
        self.buttons["load"].enabled = len(GameState.list_saves()) > 0
        self.t = 0.0

    def _anim_label(self):
        return "ANIM : RÉDUITE" if anim_settings.reduce_motion() else "ANIM : NORMALE"

    def _continue(self):
        gs = GameState.load(config.AUTOSAVE_SLOT)
        if not gs:
            return
        self.app.gs = gs
        self.app.market = None
        self.app.scenes.go("gameover" if gs.player.game_over else "terminal")

    def handle_event(self, event):
        if self.lang_btn.handle(event):
            toggle_lang()
            self.on_enter()       # reconstruit les libellés dans la nouvelle langue
            return
        if self.anim_btn.handle(event):
            anim_settings.toggle_reduce_motion()
            self.anim_btn.label = self._anim_label()
            return
        if self.settings_btn.handle(event):
            self.app.scenes.go("settings", return_to="menu")
            return
        for key, btn in self.buttons.items():
            if btn.handle(event):
                if key == "continue" and btn.enabled:
                    self._continue()
                elif key == "new":
                    self.app.scenes.go("continent")
                elif key == "load" and btn.enabled:
                    self.app.scenes.go("saves", return_to="menu")
                elif key == "sandbox":
                    self.app.scenes.go("sandbox")
                elif key == "quit":
                    self.app.running = False

    def update(self, dt):
        self.t += dt
        mp = pygame.mouse.get_pos()
        for btn in self.buttons.values():
            btn.update(mp, dt)
        self.lang_btn.update(mp, dt)
        self.anim_btn.update(mp, dt)
        self.settings_btn.update(mp, dt)

    def _draw_backdrop(self, surf):
        """Fond animé discret : chandeliers boursiers stylisés qui défilent."""
        import math
        w, h = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        base = h - 120
        n = 46
        step = w / n
        for i in range(n + 1):
            phase = i * 0.6 + self.t * 0.7
            amp = 60 + 40 * math.sin(i * 0.4)
            val = math.sin(phase) + 0.4 * math.sin(phase * 2.3)
            x = int(i * step)
            top = int(base - amp * (val * 0.5 + 0.5))
            bot = int(base + amp * 0.25 * (math.sin(phase + 1) * 0.5 + 0.5))
            up = val >= 0
            col = (16, 40, 30) if up else (40, 18, 22)   # vert/rouge très sombres
            pygame.draw.line(surf, (20, 24, 32), (x, top - 8), (x, bot + 8), 1)  # mèche
            pygame.draw.rect(surf, col, (x - int(step * 0.3), min(top, bot),
                                         max(2, int(step * 0.6)), abs(bot - top) + 1))

    def draw(self, surf):
        surf.fill(config.COL_BG)
        cx = config.SCREEN_WIDTH // 2
        self._draw_backdrop(surf)

        # bandeau ticker
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, (0, 0, config.SCREEN_WIDTH, 28))
        pygame.draw.line(surf, config.COL_AMBER, (0, 28), (config.SCREEN_WIDTH, 28), 1)
        offset = int(self.t * 60) % max(1, fonts.small().size(_TICKER)[0])
        widgets.draw_text(surf, (_TICKER * 8)[offset // 8: offset // 8 + 180],
                          (10, 7), fonts.small(), config.COL_AMBER_DIM)

        # logo / titre
        draw_ta_logo(surf, cx, 104, size=108)
        widgets.draw_text(surf, "TERMINAL", (cx, 185), fonts.huge(bold=True),
                          config.COL_AMBER, align="center")
        widgets.draw_text(surf, "ALPHA", (cx, 257), fonts.title(bold=True),
                          config.COL_CYAN, align="center")
        pulse = 120 + int(60 * (math.sin(self.t * 2) * 0.5 + 0.5))
        pygame.draw.line(surf, (pulse, pulse//2, 0), (cx-220, 310), (cx+220, 310), 1)
        widgets.draw_text(surf, t("menu.tagline"),
                          (cx, 328), fonts.small(), config.COL_TEXT_DIM, align="center")

        # résumé de la dernière partie (autosave)
        if self.auto:
            self._draw_last_run(surf, cx)

        for btn in self.buttons.values():
            btn.draw(surf)
        self.lang_btn.label = f"LANG : {get_lang().upper()}"
        self.lang_btn.draw(surf)
        self.anim_btn.draw(surf)
        self.settings_btn.draw(surf)

        widgets.draw_text(surf, "v0.3.0 — alpha",
                          (config.SCREEN_WIDTH-10, config.SCREEN_HEIGHT-22),
                          fonts.tiny(), config.COL_TEXT_DIM, align="right")

    def _draw_last_run(self, surf, cx):
        m = self.auto
        cur = config.CONTINENTS.get(m["continent"], {}).get("currency", "$")
        panel = pygame.Rect(cx - 250, 352, 500, 58)
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.rect(surf, config.COL_BORDER, panel, 1)
        widgets.draw_text(surf, t("menu.last_run"), (panel.x + 12, panel.y + 8),
                          fonts.tiny(bold=True), config.COL_CYAN)
        status = "GAME OVER" if m["game_over"] else m["grade"]
        line = f"{m['name']} · {status} · {m['continent']} · J{m['day']} · {widgets.format_money(m['cash'], cur)}"
        widgets.draw_text(surf, line, (panel.x + 12, panel.y + 28),
                          fonts.small(bold=True), config.COL_TEXT)
        if m["hardcore"]:
            widgets.draw_badge(surf, "HARDCORE", (panel.right - 12, panel.y + 6),
                               config.COL_WARN, align="right")
