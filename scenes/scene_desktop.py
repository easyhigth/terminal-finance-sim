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

Cette classe ne porte que le CŒUR (cycle de vie, navigation, dessin des
icônes/barres) ; les overlays ambiants (accueil, tutoriel, patrimoine,
trimestre, à faire) et les menus/recherche sont deux MIXINS séparés
(`scene_desktop_widgets.py`, `scene_desktop_menus.py`, même principe que les
mixins `scene_terminal_*.py` du terminal) — tous partagent leurs constantes
via `scene_desktop_common.py` pour éviter tout import circulaire entre eux.
"""
import time

import pygame

from apps.scene_host import SceneHostApp
from core import config, desktop_onboarding, desktop_tutorial
from core import difficulty as difficulty_mod
from core import portfolio as pf_mod
from core import unlocks as unlocks_mod
from core.scene_manager import Scene
from scenes.scene_desktop_common import (
    _FULLSCREEN_EXIT,
    _ICON_SHORTCUT,
    _L,
    _NEEDS_TICKER,
    _NEEDS_TICKERS,
    _TRACK_SCENE_ICON,
    APPS,
    DESKTOP_SHORTCUTS,
    ICON_FEATURE,
    ICON_GAP,
    ICON_H,
    ICON_W,
    QUICK_APPS,
    TASKBAR_H,
    TOPBAR_H,
    TRACK_APP,
    _scene_label,
)
from scenes.scene_desktop_menus import DesktopMenusMixin
from scenes.scene_desktop_widgets import DesktopWidgetsMixin
from ui import desktop_icons, fonts, keynav, widgets
from ui.window_manager import WindowManager

_ICON_DRAG_THRESHOLD = 6   # px : sous ce seuil un glisser d'icône reste un simple clic
_CLOSED_STACK_MAX = 8      # profondeur de l'historique « fenêtres fermées » (CTRL+MAJ+Z)


def _saved_ago_label(gs):
    """« Sauvegardé à l'instant / il y a Xs / il y a Xmin », ou "" si aucune
    sauvegarde n'a encore eu lieu cette session (last_saved == 0). Utile
    depuis que la cadence de l'autosave est configurable (core/
    autosave_settings.py) : elle ne se déclenche plus forcément à chaque
    action, ce discret repère confirme qu'une sauvegarde récente existe
    (ou non) sans avoir à ouvrir l'écran Sauvegardes."""
    last_saved = getattr(gs, "last_saved", 0.0)
    if not last_saved:
        return ""
    age = time.time() - last_saved
    if age < 5:
        return "· Sauvegardé à l'instant"
    if age < 60:
        return f"· Sauvegardé il y a {int(age)}s"
    return f"· Sauvegardé il y a {int(age // 60)}min"


class DesktopScene(DesktopWidgetsMixin, DesktopMenusMixin, Scene):
    def on_enter(self, **kwargs):
        self.app.ensure_market()
        if not hasattr(self, "wm"):
            self.wm = WindowManager(self.app)
        # zone utile pour l'ancrage des fenêtres : entre la barre supérieure et
        # la barre des tâches (les fenêtres ancrées ne passent pas dessous).
        self.wm.work_area = pygame.Rect(0, TOPBAR_H, config.SCREEN_WIDTH,
                                        config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H)
        self.wm.on_close = self._record_closed_window
        if not hasattr(self, "_closed_stack"):
            # pile des dernières fenêtres fermées, la plus récente EN FIN de
            # liste — [(kind, key, kwargs), ...]. CTRL+MAJ+Z rouvre la
            # dernière (pop) ; le menu contextuel du fond du bureau liste les
            # 5 dernières pour remonter plus loin dans l'historique.
            self._closed_stack = []
        self.start_open = False
        self._icon_rects = {}       # clé -> (Rect, icon_kind, label) — icônes du bureau
        self._icon_focus = None     # clé de l'icône ayant le focus clavier (ou None)
        self._icon_drag = None      # {"key","start","pos"} pendant un glisser d'icône (réorganisation)
        self._show_desktop_restore = []  # clés des fenêtres à restaurer (CTRL+MAJ+D)
        self._launch_rects = {}     # clé app -> Rect (barre des tâches quick-launch)
        self._task_rects = {}       # Window -> Rect (barre des tâches)
        self._start_rect = None     # bouton menu Démarrer
        self._launcher_rects = []   # [(Rect, scene, kwargs, locked, label, desc)] items VISIBLES
        self._start_all_rects = []  # liste complète (navigation clavier), même format
        self._start_search = ""     # recherche locale du menu Démarrer
        self._start_cursor = 0      # curseur clavier (index dans _start_all_rects)
        self._start_scroll = 0
        self._start_max_scroll = 0
        self._start_tooltip = None  # (texte, pos souris) affiché par _draw_launcher
        self._launcher_list_rect = None
        self._menu_rect = None
        self._ambient_rect = None    # widget patrimoine (clic → portefeuille)
        self._todo_rects = []        # lignes du widget « À faire » (clic → scène)
        self._calendar_rect = None   # widget calendrier macro (clic → calendrier)
        self._ctx_menu = None        # menu contextuel (clic droit) : dict ou None
        self._onboard_card = None    # carte d'accueil (rect) — 1re visite
        self._onboard_btn = None
        self._tuto_skip_rect = None  # bouton « Passer » du tutoriel guidé
        self._qcard_rects = {}       # boutons de la carte « Bilan du trimestre »
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
        self._check_new_icons()
        self._check_tutorial()

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
        # Ctrl+<lettre> : lance l'icône correspondante (mêmes mnémoniques que
        # les raccourcis du terminal) — seulement si l'icône est visible au
        # grade courant.
        if (event.type == pygame.KEYDOWN and (event.mod & pygame.KMOD_CTRL)
                and not (event.mod & (pygame.KMOD_SHIFT | pygame.KMOD_ALT))):
            key = DESKTOP_SHORTCUTS.get(event.key)
            if key and self._icon_visible(key):
                self._launch(key)
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
        # « Afficher le bureau » (façon Windows+D — CTRL+MAJ+D pour éviter tout
        # conflit avec le raccourci OS Windows+D lui-même ET avec CTRL+D
        # ci-dessus, réservé à l'icône Deals) : réduit toutes les fenêtres
        # ouvertes ; un 2ᵉ appui restaure exactement celles qui l'étaient.
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_d
                and (event.mod & pygame.KMOD_CTRL) and (event.mod & pygame.KMOD_SHIFT)):
            self._toggle_show_desktop()
            return
        # « Rouvrir la dernière fenêtre fermée » (CTRL+MAJ+Z, « annuler la
        # fermeture » — complément naturel de CTRL+MAJ+D « Afficher le
        # bureau »). Pas CTRL+MAJ+T : CTRL+T est déjà « nouvel onglet », capté
        # par la bande d'onglets (core/pages.py) AVANT même d'atteindre cette
        # scène, quel que soit MAJ ; et tout CTRL+MAJ+<lettre> par ailleurs
        # réservé par MORE_SHORTCUTS (scenes/scene_terminal.py) quand le
        # terminal a le focus. La fenêtre la plus récemment fermée (chrome
        # ✕, menu contextuel, ou « Fermer toutes les fenêtres ») se rouvre
        # avec son contexte d'origine (ticker, kwargs…) — dépile la pile
        # `_closed_stack` (jusqu'à 8 niveaux) ; remonter plus loin dans
        # l'historique se fait depuis le menu contextuel du fond du bureau
        # (liste des 5 dernières, cf. `_desktop_menu_items`).
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_z
                and (event.mod & pygame.KMOD_CTRL) and (event.mod & pygame.KMOD_SHIFT)):
            self._reopen_last_closed()
            return
        # CTRL+O : bascule le menu Démarrer (même mnémonique que le rail du
        # terminal, RAIL_SHORTCUTS/commande MORE) — l'icône dédiée « Plus » a
        # été retirée, le menu Démarrer couvrant déjà exactement le même
        # besoin (toutes les pages, ouvrables en fenêtre).
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_o
                and (event.mod & pygame.KMOD_CTRL) and not (event.mod & (pygame.KMOD_SHIFT | pygame.KMOD_ALT))):
            self._toggle_start_menu()
            return
        # clic droit : menu contextuel (icône, chrome de fenêtre, barre des
        # tâches ou fond du bureau) — avant le routage classique des fenêtres.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self._open_context_menu(event.pos):
                return
        # menu Démarrer ouvert : capture tout (clavier + souris) en priorité —
        # recherche locale, navigation clavier en grille, verrous par grade
        # (cf. DesktopMenusMixin._handle_start_menu_event).
        if self.start_open:
            self._handle_start_menu_event(event)
            return
        # carte « Bilan du trimestre » (au-dessus des fenêtres) : ses boutons
        # sont prioritaires, un clic ailleurs sur la carte est absorbé.
        if self._quarter_card_pending() is not None \
                and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            card = self._qcard_rects.get("card")
            for key, r in self._qcard_rects.items():
                if key != "card" and r and r.collidepoint(event.pos):
                    self._ack_quarter_card()
                    if key == "career":
                        self._open_scene_window("career")
                    return
            if card and card.collidepoint(event.pos):
                return
        # bouton « Passer » du tutoriel guidé (dessiné au-dessus des fenêtres)
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self._tuto_skip_rect and self._tuto_skip_rect.collidepoint(event.pos)):
            desktop_tutorial.skip()
            self._tuto_skip_rect = None
            return
        # navigation clavier des icônes du bureau : seulement quand aucune
        # fenêtre n'a le focus (une fenêtre ouverte capte normalement le
        # clavier, cf. wm.handle_event ci-dessous — cohérent avec le
        # comportement d'un vrai bureau). TAB/MAJ+TAB parcourt les icônes
        # dans l'ordre d'affichage (grille) ; les flèches naviguent selon la
        # position réelle (cf. ui/keynav.nearest_in_direction, même primitive
        # que le terminal) ; ENTRÉE lance l'icône focalisée ; ÉCHAP efface le
        # focus (liseré blanc, cf. ui/keynav.draw_focus_ring).
        if (event.type == pygame.KEYDOWN and self.wm.focused is None
                and not self.start_open and self._ctx_menu is None):
            if event.key == pygame.K_TAB and not (event.mod & pygame.KMOD_ALT):
                keys = list(self._icon_rects)
                if keys:
                    if self._icon_focus not in keys:
                        self._icon_focus = keys[0]
                    else:
                        step = -1 if (event.mod & pygame.KMOD_SHIFT) else 1
                        self._icon_focus = keys[(keys.index(self._icon_focus) + step) % len(keys)]
                return
            if event.key in keynav.DIRECTIONS:
                rects = {k: r for k, (r, _kind, _label) in self._icon_rects.items()}
                if rects:
                    if self._icon_focus not in rects:
                        self._icon_focus = next(iter(rects))
                    else:
                        self._icon_focus = keynav.nearest_in_direction(
                            rects, self._icon_focus, keynav.DIRECTIONS[event.key])
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self._icon_focus in self._icon_rects:
                self._launch(self._icon_focus)
                return
            if event.key == pygame.K_ESCAPE and self._icon_focus is not None:
                self._icon_focus = None
                return
        if self.wm.handle_event(event):
            return
        # glisser une icône du bureau : le clic (MOUSEBUTTONDOWN) sur une icône
        # ne lance PAS immédiatement — il amorce un glisser candidat (cf. plus
        # bas). MOUSEMOTION met à jour sa position ; MOUSEBUTTONUP tranche :
        # peu/pas de mouvement = un simple clic (lance l'app, comportement
        # historique), mouvement net = dépose pour réorganiser (persisté dans
        # `player.flags["desktop_icon_order"]`, relu par `_icon_list()`).
        if event.type == pygame.MOUSEMOTION and self._icon_drag is not None:
            self._icon_drag["pos"] = event.pos
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._icon_drag is not None:
            drag = self._icon_drag
            self._icon_drag = None
            sx, sy = drag["start"]
            ex, ey = event.pos
            if (ex - sx) ** 2 + (ey - sy) ** 2 < _ICON_DRAG_THRESHOLD ** 2:
                self._launch(drag["key"])
            else:
                self._reorder_icon(drag["key"], event.pos)
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        pos = event.pos
        if self._start_rect and self._start_rect.collidepoint(pos):
            self._toggle_start_menu()
            return
        # icônes du bureau + quick-launch : amorce un glisser (voir plus haut)
        for key, (r, _kind, _label) in self._icon_rects.items():
            if r.collidepoint(pos):
                self._icon_focus = key
                self._icon_drag = {"key": key, "start": pos, "pos": pos}
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
        # widget « À faire » : chaque ligne ouvre la scène concernée en fenêtre
        for r, scene in self._todo_rects:
            if r.collidepoint(pos):
                self._open_scene_window(scene)
                return
        # widget calendrier macro → ouvre l'écran Calendrier en fenêtre
        if self._calendar_rect and self._calendar_rect.collidepoint(pos):
            self._open_scene_window("calendar")
            return
        if self._menu_rect and self._menu_rect.collidepoint(pos):
            self.app.scenes.go("menu")
            return
        # pause/vitesse/⚙ : gérés par la bande d'onglets (simclock_widget), plus
        # de doublon dans la topbar du bureau.

    def _toggle_show_desktop(self):
        """CTRL+MAJ+D : réduit toutes les fenêtres ouvertes (bureau dégagé),
        ou restaure exactement celles qui viennent d'être réduites par ce
        raccourci si aucune fenêtre n'est ouverte — comme Afficher le bureau
        sous Windows/macOS. Ne touche pas aux fenêtres déjà minimisées avant
        l'appel (le terminal, minimisé par défaut, reste tel quel)."""
        open_wins = [w for w in self.wm.windows if not w.minimized]
        if open_wins:
            self._show_desktop_restore = [w.key for w in open_wins]
            for w in open_wins:
                w.minimized = True
        else:
            for w in self.wm.windows:
                if w.key in self._show_desktop_restore:
                    w.minimized = False
            self._show_desktop_restore = []

    def _record_closed_window(self, w):
        """Callback de WindowManager.on_close : empile de quoi rouvrir la
        fenêtre qui vient de se fermer (CTRL+MAJ+Z / menu contextuel). Le
        terminal n'est jamais mémorisé : instance persistante (le moteur
        tourne même fermée), se rouvre toujours par sa propre icône, pas par
        « rouvrir »."""
        if w.key == "scene:terminal":
            return
        if w.key.startswith("scene:"):
            name = w.key[len("scene:"):]
            kwargs = dict(getattr(w.app_obj, "_kwargs", None) or {})
            entry = ("scene", name, kwargs)
        else:
            entry = ("app", w.key, {})
        self._closed_stack.append(entry)
        if len(self._closed_stack) > _CLOSED_STACK_MAX:
            self._closed_stack.pop(0)

    def _reopen_last_closed(self):
        if not self._closed_stack:
            return
        kind, key, kwargs = self._closed_stack.pop()
        if kind == "scene":
            self._open_scene_window(key, **kwargs)
        else:
            self._launch(key)

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
        # « retour » (self.app.scenes.back(...)) DEPUIS cette scène ferme CETTE
        # fenêtre plutôt que d'en ouvrir une autre (cf. apps/scene_host.py::
        # _Router.back) — sans ce câblage, un bouton retour resterait ouvert
        # tout en focalisant la fenêtre cible en plus, encombrant le bureau.
        w.app_obj.bind_closer(lambda: self.wm.close(w))
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
        from apps.app_sheet import SheetApp
        w = self.wm.open("sheet", lambda: SheetApp(self.app))
        w.app_obj.desktop = self
        if import_data:
            w.app_obj.import_data(import_data)
        self.start_open = False
        return w

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
        self._draw_todo(surf)
        self._draw_calendar_widget(surf)
        self.wm.draw(surf)
        self._draw_topbar(surf)
        self._draw_taskbar(surf)
        if desktop_onboarding.seen() and not desktop_tutorial.done():
            self._draw_tutorial(surf)
        else:
            self._tuto_skip_rect = None
        if self._quarter_card_pending() is not None:
            self._draw_quarter_card(surf)
        else:
            self._qcard_rects = {}
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

    def _icon_visible(self, key):
        """Une icône soumise au déblocage progressif (ICON_FEATURE) n'apparaît
        que si la fonctionnalité est ouverte au grade courant. « Décide »
        (qdecide) n'apparaît que quand un dilemme attend réellement une
        décision — sinon l'icône ouvrait un écran vide, redondant avec le
        widget « À FAIRE »."""
        if key == "qdecide":
            return bool(self.app.gs.player.pending_dilemmas)
        feat = ICON_FEATURE.get(key)
        return feat is None or unlocks_mod.unlocked(self.app.gs.player, feat)

    def _icon_list(self):
        """Liste (clé, libellé, icon_kind, couleur accent) des icônes du
        bureau : apps natives + Terminal (toujours) + app de la voie (une fois
        choisie) — dans une grille, pas une colonne, pour rester lisible même
        si la liste s'allonge. Les icônes verrouillées (ICON_FEATURE) sont
        masquées jusqu'au grade requis."""
        items = [(k, lbl, kind, config.COL_AMBER) for k, lbl, kind, _cls in APPS
                 if self._icon_visible(k)]
        items.append(("terminal", "Terminal", "terminal", config.COL_CYAN))
        track = getattr(self.app.gs.player, "track", "General")
        info = TRACK_APP.get(track)
        if info:
            scene_name, label, kind = info
            # pas de doublon : si la scène de la voie a déjà son icône d'accès
            # rapide (ex. Portfolio→book/« Portef. », Advisory→mandates), on ne
            # l'affiche pas une seconde fois en icône de voie.
            quick_scenes = {scene for _k, _l, _kind2, scene in QUICK_APPS}
            if scene_name not in quick_scenes:
                items.append(("track", label, kind, config.COL_PRESTIGE))
        # anciens boutons du rail latéral du terminal : icônes du bureau
        items += [(k, lbl, kind, config.COL_CYAN) for k, lbl, kind, _scene in QUICK_APPS
                  if self._icon_visible(k)]
        return self._apply_icon_order(items)

    def _apply_icon_order(self, items):
        """Réordonne `items` selon `player.flags["desktop_icon_order"]`, une
        disposition libre choisie par le joueur (glisser-déposer, cf.
        `_reorder_icon`). Les clés jamais vues (nouvelle icône débloquée,
        1re partie) gardent l'ordre par défaut et se glissent à la fin — pas
        de trou ni de crash si le joueur n'a jamais réorganisé son bureau."""
        order = self.app.gs.player.flags.get("desktop_icon_order")
        if not order:
            return items
        rank = {k: i for i, k in enumerate(order)}
        ranked = sorted(enumerate(items),
                        key=lambda pair: rank.get(pair[1][0], len(order) + pair[0]))
        return [it for _i, it in ranked]

    def _reorder_icon(self, key, pos):
        """Dépose l'icône `key` près de `pos` (position souris au relâcher) :
        retrouve la case la plus proche parmi les icônes actuellement
        affichées (`self._icon_rects`, peuplé par le dernier dessin) et
        insère `key` à cet emplacement. Persisté dans `player.flags` (comme
        la difficulté ou les apps déjà vues) — survit à une sauvegarde."""
        order = list(self._icon_rects.keys())
        if key not in order:
            return
        order.remove(key)
        target, best_d = None, None
        for k, (r, _kind, _label) in self._icon_rects.items():
            if k == key:
                continue
            d = (r.centerx - pos[0]) ** 2 + (r.centery - pos[1]) ** 2
            if best_d is None or d < best_d:
                best_d, target = d, k
        insert_at = order.index(target) if target in order else len(order)
        order.insert(insert_at, key)
        self.app.gs.player.flags["desktop_icon_order"] = order

    def _check_new_icons(self):
        """Toast « nouvelle app installée » quand une icône verrouillée vient
        d'apparaître (promotion) — l'état vu est persisté dans la sauvegarde
        (player.flags) pour ne notifier qu'une fois par partie."""
        p = self.app.gs.player
        items = self._icon_list()
        keys = [k for k, _lbl, _kind, _acc in items]
        seen = p.flags.get("desktop_seen_apps")
        if seen is None:
            p.flags["desktop_seen_apps"] = keys
            return
        # qdecide apparaît/disparaît au gré des dilemmes : ce n'est pas un
        # déblocage, pas de toast « nouvelle app » pour elle.
        new = [(k, lbl) for k, lbl, _kind, _acc in items
               if k not in seen and k != "qdecide"]
        for _k, label in new:
            self.app.notify(_L(f"Nouvelle app sur le bureau : {label}",
                               f"New desktop app: {label}"), "prestige")
        if new:
            p.flags["desktop_seen_apps"] = keys

    def _dragging_icon(self):
        """True si un glisser d'icône a dépassé le seuil de clic (donc en
        train de réorganiser, pas juste un clic qui n'a pas encore bougé)."""
        d = self._icon_drag
        if d is None:
            return None
        sx, sy = d["start"]
        px, py = d["pos"]
        if (px - sx) ** 2 + (py - sy) ** 2 < _ICON_DRAG_THRESHOLD ** 2:
            return None
        return d["key"]

    def _draw_desktop_icons(self, surf):
        self._icon_rects = {}
        area_h = config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H
        max_rows = max(1, (area_h - 16) // (ICON_H + ICON_GAP))
        mp = pygame.mouse.get_pos()
        dragging_key = self._dragging_icon()
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
            keynav.draw_focus_ring(surf, r, key == self._icon_focus)
            ghost = dragging_key is not None and key == dragging_key
            icon_col = config.COL_TEXT_DIM if ghost else accent
            desktop_icons.draw(surf, (r.centerx, r.y + 28), kind, icon_col)
            widgets.draw_text(surf, widgets.fit_text(label, fonts.small(bold=True), ICON_W - 6),
                              (r.centerx, r.bottom - 18), fonts.small(bold=True),
                              config.COL_TEXT_DIM if ghost else config.COL_TEXT, align="center")
            # tooltip raccourci clavier (seulement si aucune fenêtre ne
            # recouvre l'icône — sinon le survol appartient à la fenêtre)
            sc_label = _ICON_SHORTCUT.get(key)
            if hov and sc_label and self.wm._topmost_at(mp) is None:
                widgets.draw_tooltip(surf, f"{label} · {sc_label}", (r.x, r.bottom + 2))
        # dépôt en cours : liseré pointillé (façon) sur la case cible la plus
        # proche du curseur, pour prévisualiser où l'icône va atterrir.
        if dragging_key is not None:
            best_d, target_r = None, None
            for k, (r, _kind, _label) in self._icon_rects.items():
                if k == dragging_key:
                    continue
                d = (r.centerx - mp[0]) ** 2 + (r.centery - mp[1]) ** 2
                if best_d is None or d < best_d:
                    best_d, target_r = d, r
            if target_r is not None:
                pygame.draw.rect(surf, config.COL_AMBER, target_r, 2, border_radius=8)

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
        saved_txt = _saved_ago_label(self.app.gs)
        line = f"Cash {widgets.format_money(p.cash, cur)}  ·  Patrimoine {widgets.format_money(nw, cur)}"
        widgets.draw_text(surf, line, (300, 9), fonts.small(bold=True), config.COL_AMBER)
        if saved_txt:
            # indicateur DISCRET (petit, gris) — pas une notification, juste
            # la confirmation silencieuse qu'une sauvegarde vient d'avoir
            # lieu (utile depuis que la cadence est configurable, cf.
            # core/autosave_settings.py : on ne sauvegarde plus forcément à
            # chaque action).
            sx = 300 + fonts.small(bold=True).size(line)[0] + 14
            widgets.draw_text(surf, saved_txt, (sx, 12), fonts.tiny(), config.COL_TEXT_DIM)
        # badge difficulté/défi du jour (rappel discret — sinon oublié dès la
        # création de partie passée, cf. core/difficulty.status_label)
        status = difficulty_mod.status_label(p)
        if status:
            widgets.draw_badge(surf, status.upper(), (bar.right - 12, 8),
                               config.COL_PRESTIGE, align="right")

        # NB : les contrôles pause/vitesse/⚙ NE sont PAS redessinés ici — ils
        # vivent une seule fois dans la bande d'onglets (ui/simclock_widget.py,
        # dessinée par core/pages.py), toujours visibles au-dessus du bureau.
        # Les redessiner dans cette topbar faisait doublon juste en dessous.

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
        quick = [(k, kind) for k, _l, kind, _cls in APPS
                 if self._icon_visible(k)] + [("terminal", "terminal")]
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
