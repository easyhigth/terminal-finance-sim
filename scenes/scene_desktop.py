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
from apps.scene_host import SceneHostApp
from core import config, portfolio as pf_mod
from core.scene_manager import Scene
from core.sim_clock import SPEEDS
from scenes.scene_more import SECTIONS
from ui import fonts, widgets
from ui.window_manager import WindowManager

TOPBAR_H = 36
TASKBAR_H = 30

# Applications NATIVES du bureau (dessinées en fenêtre, clé, libellé, icône, fabrique)
APPS = [
    ("research", "Recherche", "🔍", ResearchApp),
    ("trading", "Trading", "💹", TradingApp),
    ("sheet", "Tableur", "▦", SheetApp),
]

# Scènes hébergées (menu Démarrer) nécessitant un actif par défaut si non fourni.
_NEEDS_TICKER = {"company", "financials", "ma_target"}
_NEEDS_TICKERS = {"compare", "graph"}

# Libellé lisible d'une scène (repris des sections du hub PLUS).
_SCENE_LABEL = {scene: label for _title, items in SECTIONS for label, scene, _kw in items}


def _scene_label(name):
    return _SCENE_LABEL.get(name, name.capitalize())


class DesktopScene(Scene):
    def on_enter(self, **kwargs):
        self.app.ensure_market()
        if not hasattr(self, "wm"):
            self.wm = WindowManager(self.app)
        self.start_open = False
        self._icon_rects = {}       # clé app -> Rect (icônes du bureau)
        self._launch_rects = {}     # clé app -> Rect (barre des tâches quick-launch)
        self._task_rects = {}       # Window -> Rect (barre des tâches)
        self._speed_rects = {}      # valeur -> Rect (contrôles de vitesse)
        self._start_rect = None     # bouton menu Démarrer
        self._launcher_rects = []   # [(Rect, scene, kwargs)] items du menu Démarrer
        self._pause_rect = None
        self._terminal_rect = None  # icône « Terminal classique »
        self._menu_rect = None
        self._gear_rect = None
        # le terminal reste le MOTEUR de la boucle de jeu : on l'initialise si on
        # atterrit directement sur le bureau (nouvelle partie), pour que le temps
        # s'écoule dès l'arrivée (cf. _tick_market).
        term = self.app.scenes.scenes.get("terminal")
        if term is not None and not hasattr(term, "worldmap"):
            term.on_enter()

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
        # menu Démarrer ouvert : priorité à ses items / fermeture au clic dehors
        if self.start_open and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, name, kw in self._launcher_rects:
                if r.collidepoint(event.pos):
                    self._open_scene_window(name, **kw)
                    return
            if not (self._start_rect and self._start_rect.collidepoint(event.pos)):
                self.start_open = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.start_open:
            self.start_open = False
            return
        if self.wm.handle_event(event):
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        pos = event.pos
        if self._start_rect and self._start_rect.collidepoint(pos):
            self.start_open = not self.start_open
            return
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

    def _open_scene_window(self, name, **kwargs):
        """Ouvre (ou ramène au premier plan) une fenêtre hébergeant la scène
        `name`. C'est aussi le point d'entrée du routeur de navigation des
        scènes hébergées (cf. apps/scene_host.py)."""
        if name not in self.app.scenes.scenes or name in ("desktop", "gameover"):
            # gameover / sorties de flux : bascule plein écran (hors fenêtres)
            if name in self.app.scenes.scenes:
                self.app.scenes.go(name, **kwargs)
            return
        kw = dict(kwargs)
        m = self.app.ensure_market()
        if name in _NEEDS_TICKER and "ticker" not in kw:
            top = m.top_companies(n=1)
            if top:
                kw["ticker"] = top[0]["ticker"]
        if name in _NEEDS_TICKERS and "tickers" not in kw:
            kw["tickers"] = [c["ticker"] for c in m.top_companies(n=2)]
        key = f"scene:{name}"
        existing = next((w for w in self.wm.windows if w.key == key), None)

        def factory():
            host = SceneHostApp(self.app, name, _scene_label(name), kw)
            host.icon = "▣"
            host.bind_opener(self._open_scene_window)
            return host

        w = self.wm.open(key, factory)
        if existing is not None and kw:
            w.app_obj.reenter(**kw)   # met à jour le contexte (ticker…) si déjà ouverte
        self.start_open = False
        return w

    # -------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        self._draw_wallpaper(surf)
        self._draw_desktop_icons(surf)
        self.wm.draw(surf)
        self._draw_topbar(surf)
        self._draw_taskbar(surf)
        if self.start_open:
            self._draw_launcher(surf)

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
        # bouton menu Démarrer (à gauche)
        self._start_rect = pygame.Rect(6, bar.y + 4, 84, TASKBAR_H - 8)
        active = self.start_open
        pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_PANEL, self._start_rect, border_radius=4)
        widgets.draw_text(surf, "⊞ Apps", self._start_rect.center, fonts.small(bold=True),
                          config.COL_BG if active else config.COL_AMBER, align="center")
        pygame.draw.line(surf, config.COL_BORDER, (self._start_rect.right + 4, bar.y + 4),
                         (self._start_rect.right + 4, bar.bottom - 4), 1)
        # quick-launch (à gauche)
        self._launch_rects = {}
        x = self._start_rect.right + 10
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

    def _draw_launcher(self, surf):
        """Menu Démarrer : toutes les scènes du jeu, ouvrables en fenêtre."""
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 120))
        surf.blit(shade, (0, 0))
        panel = pygame.Rect(30, TOPBAR_H + 20, config.SCREEN_WIDTH - 60,
                           config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H - 40)
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.rect(surf, config.COL_AMBER, panel, 2)
        widgets.draw_text(surf, "APPLICATIONS — ouvrir en fenêtre", (panel.x + 16, panel.y + 10),
                          fonts.head(bold=True), config.COL_AMBER)
        self._launcher_rects = []
        col_w = 236
        item_h = 22
        x0 = panel.x + 16
        y0 = panel.y + 44
        x, y = x0, y0
        max_y = panel.bottom - 16
        prev_clip = surf.get_clip()
        surf.set_clip(panel)
        for title, items in SECTIONS:
            # en-tête de section : force une nouvelle colonne si trop bas
            if y + 18 + item_h > max_y:
                x += col_w
                y = y0
            widgets.draw_text(surf, title.upper(), (x, y), fonts.tiny(bold=True), config.COL_CYAN)
            y += 18
            for label, scene, kw in items:
                if y + item_h > max_y:
                    x += col_w
                    y = y0
                    widgets.draw_text(surf, title.upper() + " (suite)", (x, y), fonts.tiny(bold=True), config.COL_CYAN)
                    y += 18
                r = pygame.Rect(x, y, col_w - 12, item_h - 2)
                self._launcher_rects.append((r, scene, kw))
                hov = r.collidepoint(pygame.mouse.get_pos())
                if hov:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
                    pygame.draw.rect(surf, config.COL_AMBER, r, 1, border_radius=3)
                widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), col_w - 24),
                                  (r.x + 8, r.y + 3), fonts.small(),
                                  config.COL_TEXT if hov else config.COL_TEXT_DIM)
                y += item_h
            y += 8
        surf.set_clip(prev_clip)
