"""
scene_desktop.py — BUREAU façon « poste de travail » (refonte UI « Jeu PC »).

C'est désormais l'ÉCRAN MAÎTRE du jeu : un fond de bureau, une grille d'icônes
d'applications, une barre supérieure (horloge de jeu, trésorerie, vitesse) et
une barre des tâches en bas. TOUT se passe dans des FENÊTRES déplaçables
cohabitant sur cet écran (`ui/window_manager.py`) — y compris le TERMINAL
classique, qui n'est plus une scène plein écran à part mais une app comme les
autres, ouvrable/fermable/déplaçable en même temps que le reste (ex. suivre le
FX pendant que le desk M&A tourne à côté, en attendant le bon moment dans le
temps du jeu qui passe). N'IMPORTE QUELLE autre scène du jeu peut aussi
s'ouvrir en fenêtre via le menu Démarrer (`apps/scene_host.py`).

Le terminal reste le MOTEUR de la boucle de jeu (deals, crises, carrière…) :
une instance persistante (`self._terminal_host`) est créée à l'arrivée sur le
bureau et vit tant que la partie est en cours, que sa fenêtre soit ouverte,
minimisée ou fermée — le temps continue de s'écouler (le bureau est une scène
« live », cf. `core/sim_clock.LIVE_SCENE_NAMES`) et les pas de marché
bancarisés par l'horloge sont joués via CETTE instance (`_tick_market`), la
même que celle affichée dans sa fenêtre (pas de double état/log divergent).

Les popups de choix déclenchés par le jeu (pas un clic joueur — ex. un
dilemme) passent par `App.route_scene()` : ouverture en fenêtre plutôt que
bascule plein écran, cohérent avec le principe « tout se passe sur le bureau ».
Les icônes sont dessinées en VECTORIEL (`ui/desktop_icons.py`) : les emoji ne
s'affichent pas de façon fiable dans la police embarquée (cf. ce module).
"""
import pygame

from apps.app_calculator import CalculatorApp
from apps.app_research import ResearchApp
from apps.app_sheet import SheetApp
from apps.app_trading import TradingApp
from apps.app_watchlist import WatchlistApp
from apps.scene_host import SceneHostApp
from core import config, desktop_onboarding, portfolio as pf_mod, portfolio_margin as pm_mod
from core.scene_manager import Scene
from core.sim_clock import SPEEDS
from scenes.scene_more import SECTIONS
from ui import desktop_icons, fonts, widgets
from ui.simclock_widget import _draw_gear, _draw_pause, _draw_speed
from ui.window_manager import WindowManager

TOPBAR_H = 36
TASKBAR_H = 30

# Scènes qui restent une bascule PLEIN ÉCRAN classique (flux pré/post-partie —
# quitter le bureau, ce n'est pas ouvrir une fenêtre dessus) : jamais hébergées.
_FULLSCREEN_EXIT = {"desktop", "gameover", "menu", "splash", "intro",
                    "continent", "runsetup", "sandbox"}

# Applications NATIVES du bureau (dessinées en fenêtre, clé, libellé, icône, fabrique)
APPS = [
    ("research", "Recherche", "research", ResearchApp),
    ("trading", "Trading", "trading", TradingApp),
    ("sheet", "Tableur", "sheet", SheetApp),
    ("watchlist", "Watchlist", "star", WatchlistApp),
    ("calculator", "Calculatrice", "calc", CalculatorApp),
]

# Application supplémentaire propre à la VOIE (track) choisie par le joueur
# (cf. core/tracks.py) : une fois la voie choisie, une icône dédiée apparaît
# sur le bureau et ouvre l'écran correspondant EN FENÊTRE — au même titre que
# les autres apps, ouvrable en même temps (ex. suivre le FX pendant que le
# desk M&A tourne dans une autre fenêtre).
TRACK_APP = {
    "Portfolio": ("portfolio_unified", "Portefeuille", "portfolio"),
    "M&A": ("ma", "M&A", "ma"),
    "Risk": ("risk", "Risque", "risk"),
    "Quant": ("quant", "Quant", "quant"),
    "Advisory": ("mandates", "Mandats", "advisory"),
}

# Anciens boutons du rail latéral du terminal (retiré, refonte UI « Jeu PC ») :
# désormais des icônes du bureau, ouvertes en fenêtre comme n'importe quelle
# autre app — plus rien n'est caché dans un panneau à part. (clé, libellé,
# icon_kind, scène) — "save" (clé "save") est une action instantanée (pas une
# fenêtre), cf. `_quick_save`.
QUICK_APPS = [
    ("qmarket", "Marché", "market", "markethub"),
    ("qbook", "Portef.", "book", "book"),
    ("qalerts", "Alertes", "alert", "alerts"),
    ("qinbox", "Inbox", "inbox", "inbox"),
    ("qnews", "News", "news", "news"),
    ("qmission", "Mission", "mission", "mission"),
    ("qmandates", "Mandats", "advisory", "mandates"),
    ("qdeals", "Deals", "deals", "deals"),
    ("qdecide", "Décide", "decide", "dilemma"),
    ("qexamcert", "Exam/Certif", "examcert", "examcert"),
    ("qwall", "Mur", "wall", "wall"),
    ("qshop", "Shop", "shop", "shop"),
    ("qexplorer", "Explorateur", "explorer", "explorer"),
    ("qgraph", "Graphes", "graph", "graph"),
    ("qmore", "Plus", "apps", "more"),
    ("save", "Sauver", "save", None),
    ("qcommands", "Aide", "help", "commands"),
]

# Scènes hébergées (menu Démarrer) nécessitant un actif par défaut si non fourni.
_NEEDS_TICKER = {"company", "financials", "ma_target"}
_NEEDS_TICKERS = {"compare", "graph"}

# Libellé lisible d'une scène (repris des sections du hub PLUS).
_SCENE_LABEL = {scene: label for _title, items in SECTIONS for label, scene, _kw in items}

ICON_W, ICON_H = 88, 78
ICON_GAP = 6


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def _scene_label(name):
    return _SCENE_LABEL.get(name, name.capitalize())


class DesktopScene(Scene):
    def on_enter(self, **kwargs):
        self.app.ensure_market()
        if not hasattr(self, "wm"):
            self.wm = WindowManager(self.app)
        # zone utile pour l'ancrage des fenêtres : entre la barre supérieure et
        # la barre des tâches (les fenêtres ancrées ne passent pas dessous).
        self.wm.work_area = pygame.Rect(0, TOPBAR_H, config.SCREEN_WIDTH,
                                        config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H)
        self.start_open = False
        self._icon_rects = {}       # clé -> (Rect, icon_kind, label) — icônes du bureau
        self._launch_rects = {}     # clé app -> Rect (barre des tâches quick-launch)
        self._task_rects = {}       # Window -> Rect (barre des tâches)
        self._speed_rects = {}      # valeur -> Rect (contrôles de vitesse)
        self._start_rect = None     # bouton menu Démarrer
        self._launcher_rects = []   # [(Rect, scene, kwargs)] items du menu Démarrer
        self._pause_rect = None
        self._menu_rect = None
        self._gear_rect = None
        self._ambient_rect = None    # widget patrimoine (clic → portefeuille)
        self._ctx_menu = None        # menu contextuel (clic droit) : dict ou None
        self._onboard_card = None    # carte d'accueil (rect) — 1re visite
        self._onboard_btn = None
        # recherche globale (Ctrl+/ — Ctrl+F est déjà pris par le rail du
        # terminal pour M&A, cf. RAIL_SHORTCUTS) : cherche dans les DONNÉES DE
        # PARTIE (positions, watchlist, inbox, mandats, deals), pas le contenu
        # de référence déjà couvert par la palette Ctrl+K.
        self._search_open = False
        self._search_query = ""
        self._search_sel = 0
        self._search_rects = []
        # le terminal reste le MOTEUR de la boucle de jeu : instance persistante,
        # créée une seule fois par partie, hébergée dans SA PROPRE fenêtre (comme
        # les autres apps) — le temps s'écoule qu'elle soit ouverte ou non.
        if getattr(self, "_terminal_host", None) is None:
            self._terminal_host = SceneHostApp(self.app, "terminal", "Terminal", {})
            self._terminal_host.icon_kind = "terminal"
            self._terminal_host.bind_opener(self._open_scene_window)
            w = self.wm.open("scene:terminal", lambda: self._terminal_host)
            w.minimized = True   # bureau propre au démarrage ; icône Terminal pour l'ouvrir

    # ------------------------------------------------------ temps (marché)
    def _tick_market(self):
        """Fait avancer la boucle de jeu via l'instance TERMINAL persistante
        (`self._terminal_host.scene`) — la même que celle affichée dans sa
        fenêtre, qu'elle soit ouverte, minimisée ou fermée."""
        host = getattr(self, "_terminal_host", None)
        if host is None:
            return
        term = host.scene
        if not hasattr(term, "worldmap"):
            return
        if getattr(self.app, "pending_market_steps", 0) and not self.app.gs.player.game_over:
            term._drain_pending_steps()

    def update(self, dt):
        self._tick_market()
        self.wm.update(dt)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        # recherche globale ouverte : capture tout en priorité
        if self._search_open:
            self._handle_search_event(event)
            return
        # Ctrl+/ : ouvre la recherche globale (positions/watchlist/inbox/
        # mandats/deals) — prioritaire sur tout le reste.
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_SLASH
                and (event.mod & pygame.KMOD_CTRL)):
            self._open_search()
            return
        # menu contextuel ouvert : il capture les clics/échap en priorité
        if self._ctx_menu is not None and self._handle_ctx_event(event):
            return
        # carte d'accueil (1re visite) : NON modale — un clic sur son bouton (ou
        # ailleurs) la referme ; les clics sur la carte elle-même sont avalés,
        # les autres continuent (on peut ouvrir une app du même clic).
        if not desktop_onboarding.seen():
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._onboard_btn and self._onboard_btn.collidepoint(event.pos):
                    desktop_onboarding.mark_seen()
                    return
                if self._onboard_card and self._onboard_card.collidepoint(event.pos):
                    return
                desktop_onboarding.mark_seen()
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                desktop_onboarding.mark_seen()
                return
        # Alt+Tab : passe à la fenêtre suivante (façon OS), prioritaire sur tout
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB and (event.mod & pygame.KMOD_ALT):
            self.wm.cycle_focus(reverse=bool(event.mod & pygame.KMOD_SHIFT))
            return
        # clic droit : menu contextuel (icône, chrome de fenêtre, barre des
        # tâches ou fond du bureau) — avant le routage classique des fenêtres.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self._open_context_menu(event.pos):
                return
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
        for key, (r, _kind, _label) in self._icon_rects.items():
            if r.collidepoint(pos):
                self._launch(key)
                return
        for key, r in self._launch_rects.items():
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
        # widget patrimoine ambiant → ouvre le portefeuille en fenêtre
        if self._ambient_rect and self._ambient_rect.collidepoint(pos):
            self._open_scene_window("book")
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
        if key == "terminal":
            return self._open_terminal_window()
        if key == "track":
            if self._track_scene:
                return self._open_scene_window(self._track_scene)
            return None
        if key == "save":
            self._quick_save()
            return None
        quick = next((scene for k, _l, _kind, scene in QUICK_APPS if k == key), None)
        if quick is not None:
            return self._open_scene_window(quick)
        factory = next((cls for k, _, _, cls in APPS if k == key), None)
        if factory is not None:
            w = self.wm.open(key, lambda: factory(self.app))
            w.app_obj.desktop = self   # back-ref pour les liens inter-apps
            return w
        return None

    # ------------------------------------------------- liens entre apps (PR2)
    def open_trading(self, ticker=None):
        """Ouvre/focalise l'app Trading, optionnellement pré-filtrée sur un
        ticker (clic « Trader » depuis Recherche)."""
        w = self._launch("trading")
        if w is not None and ticker:
            w.app_obj.focus_ticker(ticker)
            self.wm.focus(w)
        return w

    def add_quote_to_sheet(self, ticker):
        """Ouvre le Tableur et y ajoute une ligne « ticker · =PRICE(ticker) »
        (cours EN DIRECT) — clic « → Tableur » depuis Recherche."""
        w = self._open_sheet_app()
        if w is not None:
            w.app_obj.add_quote(ticker)
            self.wm.focus(w)
            self.app.notify(_L(f"{ticker} ajouté au tableur (cours en direct).",
                               f"{ticker} added to the sheet (live price)."), "good")
        return w

    def _quick_save(self):
        """Sauvegarde rapide (slot 1) — reprend le comportement de l'ancienne
        commande SAVE du rail latéral, désormais une icône du bureau."""
        p = self.app.gs.player
        if p.hardcore:
            self.app.notify(_L("Mode hardcore : sauvegarde manuelle désactivée.",
                               "Hardcore mode: manual save disabled."), "warn")
            return
        self.app.gs.save(config.SAVE_SLOTS[0])
        self.app.notify(_L(f"Partie sauvegardée (slot {config.SAVE_SLOTS[0]}).",
                           f"Game saved (slot {config.SAVE_SLOTS[0]})."), "good")

    # --------------------------------------------------------- navigation
    def _open_terminal_window(self):
        """Ouvre/ramène au premier plan la fenêtre TERMINAL (instance unique et
        persistante — moteur de la boucle de jeu). Rejoue `on_enter` (comme le
        ferait un `scenes.go("terminal")` classique) pour rafraîchir l'état,
        ex. après un chargement de sauvegarde — la scène gère déjà
        l'idempotence d'une ré-entrée (cf. scenes/scene_terminal.py)."""
        w = self.wm.open("scene:terminal", lambda: self._terminal_host)
        self._terminal_host.reenter()
        w.minimized = False
        self.wm.focus(w)
        self.start_open = False
        return w

    def _open_scene_window(self, name, attention=False, **kwargs):
        """Ouvre (ou ramène au premier plan) une fenêtre hébergeant la scène
        `name`. C'est aussi le point d'entrée du routeur de navigation des
        scènes hébergées (cf. apps/scene_host.py). `attention=True` (popup
        FORCÉ par le jeu, cf. App.route_scene) fait clignoter son entrée dans
        la barre des tâches jusqu'à ce qu'elle soit focalisée."""
        if name == "terminal":
            return self._open_terminal_window()
        if name == "spreadsheet":
            # le Tableur du bureau est une app NATIVE unique (classeur multi-
            # feuilles, cf. apps/app_sheet.py) : toute navigation vers l'ancien
            # écran plein écran (export d'état financier, bouton PLUS…) est
            # redirigée vers cette app plutôt que d'héberger l'écran
            # historique — un seul tableur sur le bureau, jamais deux.
            return self._open_sheet_app(kwargs.get("import_data"))
        if name not in self.app.scenes.scenes or name in _FULLSCREEN_EXIT:
            # flux pré/post-partie : bascule plein écran (hors fenêtres) — on
            # quitte alors vraiment le bureau (ex. MENU, fin de partie).
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
            host.icon_kind = _TRACK_SCENE_ICON.get(name, "generic")
            host.bind_opener(self._open_scene_window)
            return host

        w = self.wm.open(key, factory)
        if existing is not None and kw:
            w.app_obj.reenter(**kw)   # met à jour le contexte (ticker…) si déjà ouverte
        if attention:
            w.attention = True        # clignote dans la barre des tâches jusqu'au 1er
                                      # coup d'œil (popup FORCÉ, éteint par wm.focus)
        self.start_open = False
        return w

    def _open_sheet_app(self, import_data=None):
        """Ouvre/ramène l'app Tableur ; si `import_data` est fourni (export
        depuis un état financier/une fiche M&A…), le classeur reçoit les
        données — feuille active si vierge, sinon une NOUVELLE feuille
        (cf. core/workbook.Workbook.import_financial)."""
        w = self.wm.open("sheet", lambda: SheetApp(self.app))
        w.app_obj.desktop = self
        if import_data:
            w.app_obj.import_data(import_data)
        self.start_open = False
        return w

    # ------------------------------------------------- recherche globale (Ctrl+/)
    def _open_search(self):
        self._search_open = True
        self._search_query = ""
        self._search_sel = 0
        self.start_open = False

    def _close_search(self):
        self._search_open = False

    def _search_results(self):
        from core import global_search
        m = getattr(self.app, "market", None)
        return global_search.search(self.app.gs.player, m, self._search_query)

    def _search_navigate(self, entry):
        action = entry["action"]
        if action["open"] == "trading":
            self.open_trading(action["ticker"])
        elif action["open"] == "scene":
            self._open_scene_window(action["name"])
        self._close_search()

    def _handle_search_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_search()
                return
            results = self._search_results()
            if event.key == pygame.K_BACKSPACE:
                self._search_query = self._search_query[:-1]
                self._search_sel = 0
                return
            if event.key == pygame.K_DOWN:
                if results:
                    self._search_sel = (self._search_sel + 1) % len(results)
                return
            if event.key == pygame.K_UP:
                if results:
                    self._search_sel = (self._search_sel - 1) % len(results)
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if results:
                    self._search_navigate(results[self._search_sel % len(results)])
                return
            if event.unicode and event.unicode.isprintable():
                self._search_query += event.unicode
                self._search_sel = 0
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, entry in self._search_rects:
                if r.collidepoint(event.pos):
                    self._search_navigate(entry)
                    return
            box = pygame.Rect((config.SCREEN_WIDTH - 560) // 2, (config.SCREEN_HEIGHT - 360) // 2, 560, 360)
            if not box.collidepoint(event.pos):
                self._close_search()

    def _draw_search(self, surf):
        box = pygame.Rect((config.SCREEN_WIDTH - 560) // 2, (config.SCREEN_HEIGHT - 360) // 2, 560, 360)
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surf.blit(shade, (0, 0))
        pygame.draw.rect(surf, config.COL_PANEL, box)
        pygame.draw.rect(surf, config.COL_AMBER, box, 2)
        widgets.draw_text(surf, _L("RECHERCHE (Ctrl+/) — positions, watchlist, inbox, mandats, deals",
                                   "SEARCH (Ctrl+/) — positions, watchlist, inbox, mandates, deals"),
                          (box.x + 14, box.y + 12), fonts.small(bold=True), config.COL_AMBER)
        search_box = pygame.Rect(box.x + 14, box.y + 38, box.w - 28, 26)
        pygame.draw.rect(surf, config.COL_BG, search_box)
        pygame.draw.rect(surf, config.COL_BORDER, search_box, 1)
        cur = "_" if pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, (self._search_query + cur) or _L("tapez pour chercher…", "type to search…"),
                          (search_box.x + 8, search_box.y + 5), fonts.small(),
                          config.COL_WHITE if self._search_query else config.COL_TEXT_DIM)
        results = self._search_results()
        self._search_sel = min(self._search_sel, max(0, len(results) - 1))
        list_y = box.y + 72
        row_h = 28
        max_rows = (box.bottom - 10 - list_y) // row_h
        self._search_rects = []
        if not results:
            widgets.draw_text(surf, _L("Aucun résultat.", "No results."), (box.x + 14, list_y + 6),
                              fonts.small(), config.COL_TEXT_DIM)
        for i, entry in enumerate(results[:max_rows]):
            row = pygame.Rect(box.x + 10, list_y + i * row_h, box.w - 20, row_h)
            self._search_rects.append((row, entry))
            if i == self._search_sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
                pygame.draw.rect(surf, config.COL_AMBER, row, 1)
            widgets.draw_text(surf, widgets.fit_text(entry["label"], fonts.small(), row.w - 16),
                              (row.x + 8, row.y + 6), fonts.small(), config.COL_TEXT)
        if len(results) > max_rows:
            widgets.draw_text(surf, f"… {_L('et', 'and')} {len(results) - max_rows} {_L('autre(s)', 'more')}",
                              (box.x + 14, box.bottom - 22), fonts.tiny(), config.COL_TEXT_DIM)

    # ------------------------------------------------- menus contextuels (clic droit)
    def _snap_window(self, w, side):
        """Ancre une fenêtre sur une moitié de la zone de travail (comme le
        glisser-vers-le-bord), en gardant `_restore_rect` pour revenir."""
        wa = self.wm.work_area
        if w._restore_rect is None:
            w._restore_rect = w.rect.copy()
        if side == "left":
            w.rect = pygame.Rect(wa.x, wa.y, wa.w // 2, wa.h)
        else:
            w.rect = pygame.Rect(wa.x + wa.w // 2, wa.y, wa.w - wa.w // 2, wa.h)

    def _close_all_windows(self):
        """Ferme toutes les fenêtres SAUF le terminal (moteur de la partie) —
        celui-ci est seulement minimisé, pour ne jamais arrêter le temps."""
        for w in list(self.wm.windows):
            if w.key == "scene:terminal":
                w.minimized = True
            else:
                self.wm.close(w)

    def _open_context_menu(self, pos):
        """Construit le menu contextuel selon la cible sous le curseur. Retourne
        True si un menu a été ouvert."""
        items = None
        # 1) entrée de la barre des tâches
        for w, r in self._task_rects.items():
            if r.collidepoint(pos):
                items = self._window_menu_items(w)
                break
        # 2) barre de titre d'une fenêtre (le contenu reste à l'app)
        if items is None:
            w = self.wm._topmost_at(pos)
            if w is not None and w.title_rect.collidepoint(pos):
                items = self._window_menu_items(w)
        # 3) icône du bureau (seulement si aucune fenêtre ne la recouvre)
        if items is None and self.wm._topmost_at(pos) is None:
            for key, (r, _kind, _label) in self._icon_rects.items():
                if r.collidepoint(pos):
                    items = self._icon_menu_items(key)
                    break
        # 4) fond du bureau (ni barre supérieure ni barre des tâches ni fenêtre)
        if items is None:
            area = pygame.Rect(0, TOPBAR_H, config.SCREEN_WIDTH,
                               config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H)
            if area.collidepoint(pos) and self.wm._topmost_at(pos) is None:
                items = self._desktop_menu_items()
        if not items:
            return False
        self._ctx_menu = {"pos": pos, "items": items, "rects": []}
        self.start_open = False
        return True

    def _window_menu_items(self, w):
        maximized = (w.rect == self.wm.work_area)
        return [
            (_L("Restaurer" if w.minimized else "Réduire", "Restore" if w.minimized else "Minimize"),
             lambda: (setattr(w, "minimized", False), self.wm.focus(w)) if w.minimized
             else self.wm.toggle_minimize(w)),
            (_L("Restaurer la taille" if maximized else "Agrandir",
                "Restore size" if maximized else "Maximize"),
             lambda: self.wm.maximize_toggle(w)),
            (_L("Ancrer à gauche", "Snap left"), lambda: self._snap_window(w, "left")),
            (_L("Ancrer à droite", "Snap right"), lambda: self._snap_window(w, "right")),
            (_L("Fermer", "Close"), lambda: self.wm.close(w)),
        ]

    def _icon_menu_items(self, key):
        return [
            (_L("Ouvrir", "Open"), lambda: self._launch(key)),
            (_L("Ouvrir puis ancrer à gauche", "Open and snap left"),
             lambda: self._launch_and_snap(key, "left")),
            (_L("Ouvrir puis ancrer à droite", "Open and snap right"),
             lambda: self._launch_and_snap(key, "right")),
        ]

    def _desktop_menu_items(self):
        return [
            (_L("Menu Applications", "Applications menu"), lambda: setattr(self, "start_open", True)),
            (_L("Réglages", "Settings"), lambda: self.app.scenes.go("settings", return_to="desktop")),
            (_L("Fermer toutes les fenêtres", "Close all windows"), self._close_all_windows),
            (_L("Revoir l'accueil", "Show welcome again"), desktop_onboarding.reset),
        ]

    def _launch_and_snap(self, key, side):
        w = self._launch(key)
        if w is not None:
            self._snap_window(w, side)
        return w

    def _handle_ctx_event(self, event):
        """Le menu contextuel capture le clic sur un item (exécute son action),
        et se referme à tout autre clic ou sur Échap."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._ctx_menu = None
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            for r, cb in self._ctx_menu["rects"]:
                if r.collidepoint(event.pos):
                    self._ctx_menu = None
                    cb()
                    return True
            self._ctx_menu = None       # clic hors menu : referme (et avale le clic)
            return True
        return False

    def _draw_context_menu(self, surf):
        menu = self._ctx_menu
        items = menu["items"]
        pad, ih, w = 6, 24, 210
        h = pad * 2 + ih * len(items)
        x, y = menu["pos"]
        x = min(x, config.SCREEN_WIDTH - w - 4)
        y = min(y, config.SCREEN_HEIGHT - h - 4)
        panel = pygame.Rect(x, y, w, h)
        shadow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 110))
        surf.blit(shadow, (x + 3, y + 4))
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.rect(surf, config.COL_AMBER, panel, 1)
        mp = pygame.mouse.get_pos()
        menu["rects"] = []
        iy = y + pad
        for label, cb in items:
            r = pygame.Rect(x + 3, iy, w - 6, ih - 2)
            menu["rects"].append((r, cb))
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), w - 20),
                              (r.x + 8, r.y + 4), fonts.small(), config.COL_TEXT)
            iy += ih

    def _draw_onboarding(self, surf):
        """Carte d'accueil (1re visite du bureau) : quelques repères pour
        comprendre le poste de travail. NON modale — se referme au clic."""
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surf.blit(shade, (0, 0))
        W, H = 560, 320
        x = (config.SCREEN_WIDTH - W) // 2
        y = (config.SCREEN_HEIGHT - H) // 2
        card = pygame.Rect(x, y, W, H)
        self._onboard_card = card
        pygame.draw.rect(surf, config.COL_PANEL, card, border_radius=8)
        pygame.draw.rect(surf, config.COL_AMBER, card, 2, border_radius=8)
        widgets.draw_text(surf, _L("Bienvenue sur votre poste de travail",
                                   "Welcome to your workstation"),
                          (x + 24, y + 20), fonts.head(bold=True), config.COL_AMBER)
        lines = [
            _L("• Les icônes ouvrent des APPLICATIONS en fenêtres déplaçables.",
               "• Icons open APPLICATIONS as draggable windows."),
            _L("• Glissez une fenêtre vers un bord pour l'ancrer ; double-clic sur",
               "• Drag a window to an edge to snap it; double-click the title bar"),
            _L("  la barre de titre pour l'agrandir. Alt+Tab pour changer de fenêtre.",
               "  to maximize. Alt+Tab to switch windows."),
            _L("• Le TERMINAL (icône dédiée) reste le moteur : le temps s'écoule même",
               "• The TERMINAL (its own icon) stays the engine: time flows even when"),
            _L("  fenêtre fermée. ⏸/▶▶ en haut à droite règlent la vitesse.",
               "  its window is closed. ⏸/▶▶ top-right control speed."),
            _L("• Clic DROIT sur une icône, une fenêtre ou le fond : menu d'actions.",
               "• RIGHT-click an icon, a window or the background: action menu."),
            _L("• Le widget en bas à droite suit votre patrimoine en direct.",
               "• The bottom-right widget tracks your net worth live."),
            _L("• Ctrl+/ cherche dans vos positions, watchlist, inbox, mandats et deals.",
               "• Ctrl+/ searches your positions, watchlist, inbox, mandates and deals."),
        ]
        ly = y + 58
        for ln in lines:
            widgets.draw_text(surf, ln, (x + 24, ly), fonts.small(), config.COL_TEXT)
            ly += 24
        btn = pygame.Rect(x + W - 160, y + H - 44, 136, 30)
        self._onboard_btn = btn
        hov = btn.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_AMBER if hov else config.COL_PANEL_HEAD, btn, border_radius=5)
        pygame.draw.rect(surf, config.COL_AMBER, btn, 1, border_radius=5)
        widgets.draw_text(surf, _L("Commencer", "Get started"), btn.center,
                          fonts.small(bold=True), config.COL_BG if hov else config.COL_AMBER,
                          align="center")

    # -------------------------------------------------------------- draw
    @property
    def _track_scene(self):
        track = getattr(self.app.gs.player, "track", "General")
        info = TRACK_APP.get(track)
        return info[0] if info else None

    def draw(self, surf):
        surf.fill(config.COL_BG)
        self._draw_wallpaper(surf)
        self._draw_desktop_icons(surf)
        self._draw_ambient(surf)
        self.wm.draw(surf)
        self._draw_topbar(surf)
        self._draw_taskbar(surf)
        if self.start_open:
            self._draw_launcher(surf)
        if self._ctx_menu is not None:
            self._draw_context_menu(surf)
        if self._search_open:
            self._draw_search(surf)
        if not desktop_onboarding.seen():
            self._draw_onboarding(surf)

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

    def _icon_list(self):
        """Liste (clé, libellé, icon_kind, couleur accent) des icônes du
        bureau : apps natives + Terminal (toujours) + app de la voie (une fois
        choisie) — dans une grille, pas une colonne, pour rester lisible même
        si la liste s'allonge."""
        items = [(k, lbl, kind, config.COL_AMBER) for k, lbl, kind, _cls in APPS]
        items.append(("terminal", "Terminal", "terminal", config.COL_CYAN))
        track = getattr(self.app.gs.player, "track", "General")
        info = TRACK_APP.get(track)
        if info:
            _scene_name, label, kind = info
            items.append(("track", label, kind, config.COL_PRESTIGE))
        # anciens boutons du rail latéral du terminal : icônes du bureau
        items += [(k, lbl, kind, config.COL_CYAN) for k, lbl, kind, _scene in QUICK_APPS]
        return items

    def _draw_desktop_icons(self, surf):
        self._icon_rects = {}
        area_h = config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H
        max_rows = max(1, (area_h - 16) // (ICON_H + ICON_GAP))
        mp = pygame.mouse.get_pos()
        for i, (key, label, kind, accent) in enumerate(self._icon_list()):
            col, row = divmod(i, max_rows)
            x = 16 + col * (ICON_W + ICON_GAP)
            y = TOPBAR_H + 12 + row * (ICON_H + ICON_GAP)
            r = pygame.Rect(x, y, ICON_W, ICON_H)
            self._icon_rects[key] = (r, kind, label)
            hov = r.collidepoint(mp)
            if hov:
                pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=8)
                pygame.draw.rect(surf, accent, r, 1, border_radius=8)
            desktop_icons.draw(surf, (r.centerx, r.y + 28), kind, accent)
            widgets.draw_text(surf, widgets.fit_text(label, fonts.small(bold=True), ICON_W - 6),
                              (r.centerx, r.bottom - 18), fonts.small(bold=True),
                              config.COL_TEXT, align="center")

    def _draw_ambient(self, surf):
        """Widget « ambiant » du bureau (coin bas-droit, au-dessus de la barre
        des tâches, sous les fenêtres) : patrimoine net, cash, levier et une
        mini-courbe de `player.cash_history` — le pouls du compte reste visible
        même quand toutes les fenêtres sont fermées ou minimisées. Cliquer ouvre
        le portefeuille (fenêtre « book »)."""
        p = self.app.gs.player
        m = self.app.market
        cur = config.CONTINENTS[p.continent]["currency"]
        W, H = 208, 96
        x = config.SCREEN_WIDTH - W - 16
        y = config.SCREEN_HEIGHT - TASKBAR_H - H - 12
        r = pygame.Rect(x, y, W, H)
        self._ambient_rect = r
        hov = r.collidepoint(pygame.mouse.get_pos())
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((*config.COL_PANEL, 232))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, config.COL_AMBER if hov else config.COL_BORDER, r, 1, border_radius=6)
        nw = pm_mod.net_worth(p, m) if m else p.cash
        lev = pm_mod.leverage(p, m) if m else 0.0
        widgets.draw_text(surf, "PATRIMOINE NET", (x + 10, y + 8), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        # variation depuis le début de l'historique (couleur up/down)
        hist = [v for v in (p.cash_history or []) if v]
        base = hist[0] if hist else nw
        up = nw >= base
        widgets.draw_text(surf, widgets.format_money(nw, cur), (x + 10, y + 20),
                          fonts.small(bold=True), config.COL_UP if up else config.COL_DOWN)
        widgets.draw_text(surf, f"Cash {widgets.format_money(p.cash, cur)}", (x + 10, y + 40),
                          fonts.tiny(), config.COL_TEXT)
        levcol = config.COL_DOWN if lev > 2.0 else config.COL_AMBER if lev > 1.0 else config.COL_TEXT_DIM
        widgets.draw_text(surf, f"Levier {lev:.2f}x", (x + 10, y + 54), fonts.tiny(bold=True), levcol)
        # mini-sparkline du patrimoine
        spark = pygame.Rect(x + 10, y + H - 20, W - 20, 14)
        if len(hist) >= 2:
            gcol = config.COL_UP if hist[-1] >= hist[0] else config.COL_DOWN
            widgets.draw_series(surf, spark, hist[-40:], gcol, baseline=False,
                                show_extrema=False, y_fmt=None)

    def _draw_topbar(self, surf):
        bar = pygame.Rect(0, 0, config.SCREEN_WIDTH, TOPBAR_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar)
        pygame.draw.line(surf, config.COL_AMBER, (0, bar.bottom - 1), (bar.right, bar.bottom - 1), 1)
        # menu (à gauche)
        self._menu_rect = pygame.Rect(8, 5, 66, TOPBAR_H - 10)
        mh = self._menu_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if mh else config.COL_PANEL_HEAD, self._menu_rect, border_radius=4)
        desktop_icons.draw(surf, (self._menu_rect.x + 16, self._menu_rect.centery), "menu", config.COL_AMBER)
        widgets.draw_text(surf, "Menu", (self._menu_rect.x + 28, self._menu_rect.y + 5),
                          fonts.small(bold=True), config.COL_AMBER)

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

        # contrôles de vitesse (à droite) + réglages — dessin vectoriel partagé
        # avec la bande d'onglets classique (cf. ui/simclock_widget.py) : mêmes
        # icônes (barres de pause, triangles de vitesse, roue dentée) partout.
        x = config.SCREEN_WIDTH - 8
        self._gear_rect = pygame.Rect(x - 30, 5, 26, TOPBAR_H - 10)
        gh = self._gear_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if gh else config.COL_PANEL_HEAD, self._gear_rect, border_radius=4)
        _draw_gear(surf, self._gear_rect, config.COL_AMBER if gh else config.COL_TEXT_DIM)
        x = self._gear_rect.x - 8
        self._speed_rects = {}
        for val in reversed(SPEEDS):
            r = pygame.Rect(x - 30, 5, 30, TOPBAR_H - 10)
            self._speed_rects[val] = r
            active = (self.app.sim_clock.speed == val and self.app.sim_clock.is_running())
            pygame.draw.rect(surf, config.COL_PANEL if active else config.COL_PANEL_HEAD, r, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=4)
            _draw_speed(surf, r, val, config.COL_AMBER if active else config.COL_TEXT_DIM)
            x = r.x - 4
        self._pause_rect = pygame.Rect(x - 30, 5, 30, TOPBAR_H - 10)
        paused = not self.app.sim_clock.is_running()
        pygame.draw.rect(surf, config.COL_DOWN if paused else config.COL_PANEL_HEAD, self._pause_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self._pause_rect, 1, border_radius=4)
        _draw_pause(surf, self._pause_rect, config.COL_WHITE if paused else config.COL_TEXT_DIM)

    def _draw_taskbar(self, surf):
        bar = pygame.Rect(0, config.SCREEN_HEIGHT - TASKBAR_H, config.SCREEN_WIDTH, TASKBAR_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar)
        pygame.draw.line(surf, config.COL_BORDER, (0, bar.y), (bar.right, bar.y), 1)
        # bouton menu Démarrer (à gauche)
        self._start_rect = pygame.Rect(6, bar.y + 4, 84, TASKBAR_H - 8)
        active = self.start_open
        pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_PANEL, self._start_rect, border_radius=4)
        desktop_icons.draw(surf, (self._start_rect.x + 16, self._start_rect.centery), "apps",
                           config.COL_BG if active else config.COL_AMBER)
        widgets.draw_text(surf, "Apps", (self._start_rect.x + 28, self._start_rect.y + 4),
                          fonts.small(bold=True), config.COL_BG if active else config.COL_AMBER)
        pygame.draw.line(surf, config.COL_BORDER, (self._start_rect.right + 4, bar.y + 4),
                         (self._start_rect.right + 4, bar.bottom - 4), 1)
        # quick-launch (à gauche) : apps natives + Terminal
        self._launch_rects = {}
        x = self._start_rect.right + 10
        quick = [(k, kind) for k, _l, kind, _cls in APPS] + [("terminal", "terminal")]
        for key, kind in quick:
            r = pygame.Rect(x, bar.y + 4, 26, TASKBAR_H - 8)
            self._launch_rects[key] = r
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD, r, border_radius=4)
            desktop_icons.draw(surf, r.center, kind, config.COL_AMBER)
            x += 30
        pygame.draw.line(surf, config.COL_BORDER, (x + 2, bar.y + 4), (x + 2, bar.bottom - 4), 1)
        x += 10
        # fenêtres ouvertes
        self._task_rects = {}
        for w in self.wm.windows:
            r = pygame.Rect(x, bar.y + 4, 150, TASKBAR_H - 8)
            self._task_rects[w] = r
            focused = (w is self.wm.focused)
            # fenêtre qui réclame l'attention (popup FORCÉ non encore regardé) :
            # clignote (cf. Window.attention, éteint au focus).
            flash = getattr(w, "attention", False) and (pygame.time.get_ticks() % 900 < 450)
            bg = (config.COL_DOWN if flash
                  else config.COL_PANEL if (focused and not w.minimized) else config.COL_PANEL_HEAD)
            pygame.draw.rect(surf, bg, r, border_radius=4)
            border = (config.COL_WHITE if flash
                      else config.COL_AMBER if focused and not w.minimized else config.COL_BORDER)
            pygame.draw.rect(surf, border, r, 1, border_radius=4)
            col = config.COL_WHITE if flash else config.COL_TEXT_DIM if w.minimized else config.COL_TEXT
            kind = getattr(w.app_obj, "icon_kind", "generic")
            desktop_icons.draw(surf, (r.x + 12, r.centery), kind, col)
            widgets.draw_text(surf, widgets.fit_text(w.app_obj.title, fonts.tiny(), r.w - 26),
                              (r.x + 22, r.y + 5), fonts.tiny(bold=True), col)
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


# scène -> icon_kind (façade visuelle des fenêtres hébergées de la voie choisie)
_TRACK_SCENE_ICON = {scene: kind for _track, (scene, _label, kind) in TRACK_APP.items()}
