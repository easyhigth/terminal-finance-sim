"""
scene_desktop.py — BUREAU façon « poste de travail » (refonte UI « Jeu PC »,
étape 1).

Écran principal type ordinateur : un fond de bureau, des icônes d'applications,
une barre supérieure (horloge de jeu, trésorerie, vitesse) et une barre des
tâches en bas. Les applications (Recherche, Trading, Tableur) s'ouvrent dans des
FENÊTRES déplaçables cohabitant à l'écran (`ui/window_manager.py`), comme un
vrai bureau où plusieurs outils sont ouverts en même temps.

Le temps continue d'avancer ici (le bureau est une scène « live », cf.
`core/sim_clock.LIVE_SCENE_NAMES`) : les pas de marché bancarisés par l'horloge
sont joués via le terminal historique (`TerminalScene._drain_pending_steps`),
qui reste le moteur de la boucle de jeu (deals, crises, carrière…). Le terminal
classique reste accessible depuis une icône, le temps de migrer toutes les
scènes en fenêtres (étapes suivantes).
"""
import pygame

from apps.app_research import ResearchApp
from apps.app_sheet import SheetApp
from apps.app_trading import TradingApp
from core import config, portfolio as pf_mod
from core.scene_manager import Scene
from core.sim_clock import SPEEDS
from ui import fonts, widgets
from ui.window_manager import WindowManager

TOPBAR_H = 36
TASKBAR_H = 30

# Applications lançables (clé, libellé, icône, fabrique)
APPS = [
    ("research", "Recherche", "🔍", ResearchApp),
    ("trading", "Trading", "💹", TradingApp),
    ("sheet", "Tableur", "▦", SheetApp),
]


class DesktopScene(Scene):
    def on_enter(self, **kwargs):
        self.app.ensure_market()
        if not hasattr(self, "wm"):
            self.wm = WindowManager(self.app)
        self._icon_rects = {}       # clé app -> Rect (icônes du bureau)
        self._launch_rects = {}     # clé app -> Rect (barre des tâches quick-launch)
        self._task_rects = {}       # Window -> Rect (barre des tâches)
        self._speed_rects = {}      # valeur -> Rect (contrôles de vitesse)
        self._pause_rect = None
        self._terminal_rect = None  # icône « Terminal classique »
        self._menu_rect = None
        self._gear_rect = None

    # ------------------------------------------------------ temps (marché)
    def _tick_market(self):
        """Fait avancer la boucle de jeu via le terminal historique (déjà
        initialisé quand on arrive du terminal). Robuste si le terminal n'a
        pas encore été visité : on n'avance pas (les pas restent bancarisés)."""
        term = self.app.scenes.scenes.get("terminal")
        if term is None or not hasattr(term, "worldmap"):
            return
        if getattr(self.app, "pending_market_steps", 0) and not self.app.gs.player.game_over:
            term._drain_pending_steps()

    def update(self, dt):
        self._tick_market()
        self.wm.update(dt)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if self.wm.handle_event(event):
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        pos = event.pos
        # icônes du bureau + quick-launch : ouvrir/ramener l'app
        for key, r in list(self._icon_rects.items()) + list(self._launch_rects.items()):
            if r.collidepoint(pos):
                self._launch(key)
                return
        # barre des tâches : restaurer/focaliser une fenêtre
        for w, r in self._task_rects.items():
            if r.collidepoint(pos):
                if w.minimized:
                    w.minimized = False
                self.wm.focus(w)
                return
        if self._terminal_rect and self._terminal_rect.collidepoint(pos):
            self.app.scenes.go("terminal")
            return
        if self._menu_rect and self._menu_rect.collidepoint(pos):
            self.app.scenes.go("menu")
            return
        if self._gear_rect and self._gear_rect.collidepoint(pos):
            self.app.scenes.go("settings", return_to="desktop")
            return
        if self._pause_rect and self._pause_rect.collidepoint(pos):
            self.app.sim_clock.toggle_pause()
            return
        for val, r in self._speed_rects.items():
            if r.collidepoint(pos):
                self.app.sim_clock.set_speed(val)
                return

    def _launch(self, key):
        factory = next((cls for k, _, _, cls in APPS if k == key), None)
        if factory is not None:
            self.wm.open(key, lambda: factory(self.app))

    # -------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        self._draw_wallpaper(surf)
        self._draw_desktop_icons(surf)
        self.wm.draw(surf)
        self._draw_topbar(surf)
        self._draw_taskbar(surf)

    def _draw_wallpaper(self, surf):
        # léger quadrillage « poste de travail »
        area = pygame.Rect(0, TOPBAR_H, config.SCREEN_WIDTH,
                           config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H)
        step = 48
        for gx in range(0, config.SCREEN_WIDTH, step):
            pygame.draw.line(surf, config.COL_GRID, (gx, area.y), (gx, area.bottom), 1)
        for gy in range(area.y, area.bottom, step):
            pygame.draw.line(surf, config.COL_GRID, (0, gy), (config.SCREEN_WIDTH, gy), 1)
        widgets.draw_text(surf, "TERMINAL ALPHA — POSTE DE TRAVAIL",
                          (config.SCREEN_WIDTH // 2, area.centery),
                          fonts.title(bold=True), (22, 26, 34), align="center")

    def _draw_desktop_icons(self, surf):
        self._icon_rects = {}
        x, y = 24, TOPBAR_H + 24
        for key, label, icon, _cls in APPS:
            r = pygame.Rect(x, y, 92, 78)
            self._icon_rects[key] = r
            hov = r.collidepoint(pygame.mouse.get_pos())
            if hov:
                pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=8)
                pygame.draw.rect(surf, config.COL_AMBER, r, 1, border_radius=8)
            widgets.draw_text(surf, icon, (r.centerx, r.y + 26), fonts.title(), config.COL_AMBER, align="center")
            widgets.draw_text(surf, label, (r.centerx, r.bottom - 18), fonts.small(bold=True),
                              config.COL_TEXT, align="center")
            y += 96
        # icône terminal classique
        r = pygame.Rect(x, y, 92, 78)
        self._terminal_rect = r
        hov = r.collidepoint(pygame.mouse.get_pos())
        if hov:
            pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=8)
            pygame.draw.rect(surf, config.COL_CYAN, r, 1, border_radius=8)
        widgets.draw_text(surf, "▣", (r.centerx, r.y + 26), fonts.title(), config.COL_CYAN, align="center")
        widgets.draw_text(surf, "Terminal", (r.centerx, r.bottom - 18), fonts.small(bold=True),
                          config.COL_TEXT, align="center")

    def _draw_topbar(self, surf):
        bar = pygame.Rect(0, 0, config.SCREEN_WIDTH, TOPBAR_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar)
        pygame.draw.line(surf, config.COL_AMBER, (0, bar.bottom - 1), (bar.right, bar.bottom - 1), 1)
        # menu (à gauche)
        self._menu_rect = pygame.Rect(8, 5, 66, TOPBAR_H - 10)
        mh = self._menu_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if mh else config.COL_PANEL_HEAD, self._menu_rect, border_radius=4)
        widgets.draw_text(surf, "☰ Menu", self._menu_rect.center, fonts.small(bold=True), config.COL_AMBER, align="center")

        p = self.app.gs.player
        m = self.app.market
        cur = config.CONTINENTS[p.continent]["currency"]
        # horloge de jeu
        day, minute = self.app.sim_clock.current_time(p.day)
        hh, mm = divmod(minute, 60)
        clock_txt = f"Jour {day}  {hh:02d}:{mm:02d}  ·  T{p.quarter}"
        widgets.draw_text(surf, clock_txt, (90, 9), fonts.small(bold=True), config.COL_TEXT)
        # trésorerie / patrimoine net
        nw = pf_mod.net_worth(p, m) if m else p.cash
        widgets.draw_text(surf, f"Cash {widgets.format_money(p.cash, cur)}  ·  "
                                f"Patrimoine {widgets.format_money(nw, cur)}",
                          (300, 9), fonts.small(bold=True), config.COL_AMBER)

        # contrôles de vitesse (à droite) + réglages
        x = config.SCREEN_WIDTH - 8
        self._gear_rect = pygame.Rect(x - 30, 5, 26, TOPBAR_H - 10)
        gh = self._gear_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if gh else config.COL_PANEL_HEAD, self._gear_rect, border_radius=4)
        widgets.draw_text(surf, "⚙", self._gear_rect.center, fonts.body(), config.COL_TEXT, align="center")
        x = self._gear_rect.x - 8
        self._speed_rects = {}
        for val in reversed(SPEEDS):
            r = pygame.Rect(x - 30, 5, 30, TOPBAR_H - 10)
            self._speed_rects[val] = r
            active = (self.app.sim_clock.speed == val and self.app.sim_clock.is_running())
            pygame.draw.rect(surf, config.COL_PANEL if active else config.COL_PANEL_HEAD, r, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=4)
            widgets.draw_text(surf, "▶" * val, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            x = r.x - 4
        self._pause_rect = pygame.Rect(x - 30, 5, 30, TOPBAR_H - 10)
        paused = not self.app.sim_clock.is_running()
        pygame.draw.rect(surf, config.COL_DOWN if paused else config.COL_PANEL_HEAD, self._pause_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self._pause_rect, 1, border_radius=4)
        widgets.draw_text(surf, "⏸", self._pause_rect.center, fonts.small(bold=True),
                          config.COL_WHITE if paused else config.COL_TEXT_DIM, align="center")

    def _draw_taskbar(self, surf):
        bar = pygame.Rect(0, config.SCREEN_HEIGHT - TASKBAR_H, config.SCREEN_WIDTH, TASKBAR_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar)
        pygame.draw.line(surf, config.COL_BORDER, (0, bar.y), (bar.right, bar.y), 1)
        # quick-launch (à gauche)
        self._launch_rects = {}
        x = 8
        for key, label, icon, _cls in APPS:
            r = pygame.Rect(x, bar.y + 4, 26, TASKBAR_H - 8)
            self._launch_rects[key] = r
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD, r, border_radius=4)
            widgets.draw_text(surf, icon, r.center, fonts.small(), config.COL_AMBER, align="center")
            x += 30
        pygame.draw.line(surf, config.COL_BORDER, (x + 2, bar.y + 4), (x + 2, bar.bottom - 4), 1)
        x += 10
        # fenêtres ouvertes
        self._task_rects = {}
        for w in self.wm.windows:
            r = pygame.Rect(x, bar.y + 4, 150, TASKBAR_H - 8)
            self._task_rects[w] = r
            focused = (w is self.wm.focused)
            bg = config.COL_PANEL if (focused and not w.minimized) else config.COL_PANEL_HEAD
            pygame.draw.rect(surf, bg, r, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if focused and not w.minimized else config.COL_BORDER,
                             r, 1, border_radius=4)
            col = config.COL_TEXT_DIM if w.minimized else config.COL_TEXT
            widgets.draw_text(surf, widgets.fit_text(f"{w.app_obj.icon} {w.app_obj.title}", fonts.tiny(), r.w - 12),
                              (r.x + 6, r.y + 5), fonts.tiny(bold=True), col)
            x += 156
