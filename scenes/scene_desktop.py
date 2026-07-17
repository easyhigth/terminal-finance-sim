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
mixins `scene_terminal_*.py` du terminal) ; la grille d'icônes et la
persistance du layout d'espace de travail sont deux autres mixins
(`scene_desktop_icons.py`, `scene_desktop_layout.py`) — tous partagent leurs constantes
via `scene_desktop_common.py` pour éviter tout import circulaire entre eux.
"""
import time

import pygame

from apps.scene_host import SceneHostApp
from core import config, desktop_onboarding, desktop_tutorial
from core import difficulty as difficulty_mod
from core import portfolio as pf_mod
from core.scene_manager import Scene
from scenes.scene_desktop_common import (
    _FULLSCREEN_EXIT,
    _L,
    _NEEDS_TICKER,
    _NEEDS_TICKERS,
    APPS,
    DESKTOP_SHORTCUTS,
    ICON_FEATURE,
    QUICK_APPS,
    SCENE_ICON,
    TASKBAR_H,
    TOPBAR_H,
    TRACK_APP,
    _scene_label,
)
from scenes.scene_desktop_icons import DesktopIconsMixin
from scenes.scene_desktop_layout import DesktopLayoutMixin
from scenes.scene_desktop_menus import DesktopMenusMixin
from scenes.scene_desktop_widgets import DesktopWidgetsMixin
from ui import desktop_icons, fonts, keynav, style, widgets
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


class DesktopScene(DesktopWidgetsMixin, DesktopMenusMixin, DesktopIconsMixin,
                   DesktopLayoutMixin, Scene):
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
        self._icon_hover_t = {}     # clé -> progression hover [0,1]
        self._section_header_rects = {}  # libellé de section -> Rect (en-tête repliable)
        self._wallpaper_cache = None  # surface du fond pré-rendue (resize)
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
        self._gsearch_rect = None
        self._ambient_rect = None    # widget patrimoine (clic → portefeuille)
        self._index_ticker_rect = None   # bande d'indices (clic → hub Marché)
        self._todo_rects = []        # lignes du widget « À faire » (clic → scène)
        self._calendar_rect = None   # widget calendrier macro (clic → calendrier)
        self._ctx_menu = None        # menu contextuel (clic droit) : dict ou None
        self._tuto_skip_rect = None  # bouton « Passer » du tutoriel guidé
        self._qcard_rects = {}       # boutons de la carte « Bilan du trimestre »
        self._brief_rects = {}       # boutons de la carte « Nouveautés » (promotion)
        self._brief_page = 0         # page courante de la carte « Nouveautés »
        self._guide_rects = {}       # boutons du guide de démarrage (multi-pages)
        self._guide_page = 0
        self._guide_force = getattr(self, "_guide_force", False)
        # L'ex-carte d'accueil machine a été FUSIONNÉE dans le guide de
        # démarrage (sa dernière page couvre le poste de travail). Quand le
        # guide ne s'affichera pas (vétéran, sandbox, déjà lu), on marque
        # directement l'accueil comme vu pour que le tutoriel guidé puisse
        # démarrer sans étape fantôme.
        if not self._intro_guide_active():
            desktop_onboarding.mark_seen()
        self._assistant_open = False   # carte « Assistant » (F1)
        self._assistant_rects = {}
        self._checklist_rects = []     # lignes du widget « Routine du jour » (clic → coche)
        self._risk_badge_rect = None   # pastille de risque unifiée (barre supérieure)
        self._risk_badge_reasons = ""
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
            # « espace de travail » : disposition pending depuis ui_state
            # (chargement d'une sauvegarde) prioritaire ; sinon dernière
            # disposition dans player.flags (reprise classique / nouvelle
            # partie). Seulement à la toute première arrivée sur le bureau de
            # CETTE App() pour ne pas écraser l'organisation en cours.
            pending = getattr(self.app, "_pending_ui_layout", None)
            if pending:
                self._apply_layout(pending)
                self.app._pending_ui_layout = None
            else:
                self._restore_layout()

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

    def _engaged_in_focus_work(self):
        """Vrai si le joueur est occupé à une activité de carrière qui doit
        GELER le temps : carte modale du bureau (guide de démarrage, bilan de
        trimestre, nouveautés de promotion, résumé d'absence) ou fenêtre
        « de travail » (mission, examen, dilemme, deal, revue, stress test,
        tutoriels — cf. core/sim_clock.FOCUS_SCENE_NAMES) ouverte et non
        minimisée. Évite qu'un examen se paie en intérêts de levier, en
        crise ou en game over pendant que le joueur fait ce que le jeu lui
        demande de faire."""
        if self._intro_guide_active() or self._blocking_card_pending():
            return True
        from core.sim_clock import FOCUS_SCENE_NAMES
        for w in self.wm.windows:
            if w.minimized:
                continue
            # scène hébergée ("scene:<nom>") ou app native migrée (clé nue,
            # ex. "dilemma"/"review") — les deux formes désignent la même
            # activité de carrière du point de vue de l'auto-pause.
            name = w.key[len("scene:"):] if w.key.startswith("scene:") else w.key
            if name in FOCUS_SCENE_NAMES:
                return True
        return False

    def _sync_auto_pause(self):
        """Recalcule la pause automatique à chaque frame tant que le bureau
        est la scène courante (en plein écran, c'est SceneManager.go qui
        pose/lève le même drapeau) : pause dès qu'une activité de carrière
        est en cours, reprise exacte dès qu'elle se termine — aucune minute
        de jeu comptée entre-temps."""
        clock = getattr(self.app, "sim_clock", None)
        if clock is not None:
            clock.set_auto_paused(self._engaged_in_focus_work())

    def update(self, dt):
        self._sync_auto_pause()
        self._tick_market()
        self.wm.update(dt)
        self._check_new_icons()
        self._check_tutorial()
        self._sync_layout_flag()
        # animation hover des icônes du bureau
        mp = pygame.mouse.get_pos()
        for key, (r, _kind, _label) in self._icon_rects.items():
            target = 1.0 if r.collidepoint(mp) and self.wm._topmost_at(mp) is None else 0.0
            cur = self._icon_hover_t.get(key, 0.0)
            speed = 14.0 * dt if dt else 1.0
            self._icon_hover_t[key] = cur + (target - cur) * min(1.0, speed)

    # ------------------------------------------------------------- events
    def _blocking_card_pending(self):
        """True si une carte modale déclenchée PAR LE JEU (pas par un clic
        joueur) attend d'être vue — bilan du trimestre, résumé d'absence.
        Empêche l'Assistant (F1) ou la recherche globale (Ctrl+/) de
        s'ouvrir par-dessus, ce qui superposerait deux cartes au même
        endroit de l'écran et rendrait celle du dessous injoignable tant que
        celle du dessus n'est pas refermée."""
        return (self._quarter_card_pending() is not None
                or self._unlock_brief_pending() is not None)

    def handle_event(self, event):
        # GUIDE DE DÉMARRAGE (début de partie) : entièrement modal — tant
        # qu'il est affiché, il capture tout (souris + clavier). C'est la
        # toute première chose qu'un nouveau joueur voit sur le bureau.
        if self._intro_guide_active():
            self._handle_guide_event(event)
            return
        # carte Assistant ouverte : capture tout en priorité (même règle que
        # les autres cartes modales du bureau — bilan trimestre, recherche…)
        if self._assistant_open:
            self._handle_assistant_event(event)
            return
        # F1 : ouvre l'Assistant « que faire maintenant ? » — LA suggestion la
        # plus prioritaire (core/todo.py), en langage simple, pour le joueur
        # qui ne sait pas par où commencer parmi les nombreuses icônes. Ne
        # s'ouvre PAS par-dessus une carte modale déjà affichée par le jeu
        # (bilan trimestre, résumé d'absence) : sinon les deux cartes se
        # superposent au même endroit de l'écran et celle du dessous devient
        # injoignable tant que l'Assistant n'est pas refermé (bug corrigé —
        # jamais deux cartes modales à la fois).
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            if not self._blocking_card_pending():
                self._assistant_open = True
            return
        # recherche globale ouverte : capture tout en priorité
        if self._search_open:
            self._handle_search_event(event)
            return
        # Ctrl+/ : ouvre la recherche globale (positions/watchlist/inbox/
        # mandats/deals) — prioritaire sur tout le reste. Même garde que F1
        # ci-dessus : ne s'ouvre pas par-dessus une carte modale déjà
        # affichée (bilan trimestre, résumé d'absence) — bug pré-existant
        # (recherche superposée à la carte, injoignable tant que la
        # recherche n'est pas refermée) corrigé au passage.
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_SLASH
                and (event.mod & pygame.KMOD_CTRL)):
            if not self._blocking_card_pending():
                self._open_search()
            return
        # Ctrl+Space : avance le temps d'un pas (raccourci global)
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
                and (event.mod & pygame.KMOD_CTRL)):
            self._tick_market()
            return
        # Ctrl+<lettre> : lance l'icône correspondante (mêmes mnémoniques que
        # les raccourcis du terminal) — seulement si l'icône est visible au
        # grade courant.
        if (event.type == pygame.KEYDOWN and (event.mod & pygame.KMOD_CTRL)
                and not (event.mod & (pygame.KMOD_SHIFT | pygame.KMOD_ALT))):
            key = DESKTOP_SHORTCUTS.get(event.key)
            if key and self._icon_visible(key):
                self._launch(key)
        # F2-F10 : raccourcis rapides vers les apps principales
        _F_KEYS = {
            pygame.K_F2: "sheet", pygame.K_F3: "research", pygame.K_F4: "trading",
            pygame.K_F5: "book", pygame.K_F6: "qgraph", pygame.K_F7: "qnews",
            pygame.K_F8: "inbox", pygame.K_F9: "mission", pygame.K_F10: "deals",
        }
        if event.type == pygame.KEYDOWN and event.key in _F_KEYS:
            key = _F_KEYS[event.key]
            if self._icon_visible(key):
                self._launch(key)
            return
        # menu contextuel ouvert : il capture les clics/échap en priorité
        if self._ctx_menu is not None and self._handle_ctx_event(event):
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
        # carte « NOUVEAUTÉS » de promotion (fiches des fonctionnalités
        # débloquées) : juste après le bilan de trimestre dans l'ordre de
        # priorité — navigation ←/→ entre fiches, acquittement, lien tuto.
        # (La carte « En votre absence » a été RETIRÉE — jugée envahissante :
        # le Centre de notifications couvre déjà l'historique à la demande.)
        elif self._quarter_card_pending() is None \
                and self._unlock_brief_pending() is not None \
                and event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            if self._handle_unlock_brief_event(event):
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
        # en-tête de section repliable (façon dossier) : clic = replier/déplier
        for label, r in self._section_header_rects.items():
            if r.collidepoint(pos):
                self._toggle_section(label)
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
        # bande d'indices ambiante → ouvre le hub Marché en fenêtre
        if self._index_ticker_rect and self._index_ticker_rect.collidepoint(pos):
            self._open_scene_window("markethub")
            return
        # pastille de risque (barre supérieure) → ouvre le portefeuille
        if self._risk_badge_rect and self._risk_badge_rect.collidepoint(pos):
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
        # widget « Routine du jour » : coche/décoche l'action cliquée
        if self._handle_checklist_click(pos):
            return
        if self._menu_rect and self._menu_rect.collidepoint(pos):
            self.app.scenes.go("menu")
            return
        # loupe de la topbar : ouvre la recherche globale (équivalent Ctrl+/,
        # jusqu'ici découvrable uniquement en connaissant le raccourci)
        if self._gsearch_rect and self._gsearch_rect.collidepoint(pos):
            if not self._blocking_card_pending():
                self._open_search()
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
        # diagnostic de découvrabilité : note (par machine) que cette app a
        # été ouverte au moins une fois (cf. core/profile.apps_never_opened) —
        # la TOUTE première ouverture déclenche aussi le bandeau « première
        # ouverture » (cf. _attach_first_open_brief).
        from core import profile as _profile
        first_time = key not in _profile.apps_opened()
        _profile.record_app_opened(key)
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
            if first_time:
                self._attach_first_open_brief(w, key)
            return w
        return None

    def _attach_first_open_brief(self, w, key):
        """Première ouverture d'une app native sur cette machine : accroche à
        sa fenêtre un bandeau de 2-3 lignes (à quoi ça sert, premier pas),
        réutilisant les fiches FEATURE_BRIEFS (core/unlock_briefs.py) via la
        correspondance icône→fonctionnalité ICON_FEATURE. Pas de fiche = pas
        de bandeau (jamais de texte générique inutile)."""
        from core.unlock_briefs import brief_for
        b = brief_for(ICON_FEATURE.get(key, key))
        if not b:
            return
        text = b.get("what", "")
        first = b.get("first", "")
        if first:
            text = (text + "  " + first).strip()
        w.first_open_brief = {"title": b.get("title", ""), "text": text}

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
        from core import profile as _profile
        _profile.record_app_opened(name)
        if name == "terminal":
            return self._open_terminal_window()
        if name == "spreadsheet":
            # le Tableur du bureau est une app NATIVE unique (classeur multi-
            # feuilles, cf. apps/app_sheet.py) : toute navigation vers l'ancien
            # écran plein écran (export d'état financier, bouton PLUS…) est
            # redirigée vers cette app plutôt que d'héberger l'écran
            # historique — un seul tableur sur le bureau, jamais deux.
            return self._open_sheet_app(kwargs.get("import_data"))
        if name == "trading":
            return self.open_trading(kwargs.get("ticker"))
        if name == "inbox":
            # messagerie NATIVE (apps/app_inbox.py) : plus d'hébergement flou
            # de la scène plein écran ; `select_idx` (centre de notifications,
            # recherche globale) cible un message précis.
            w = self._launch("inbox")
            if w is not None:
                if kwargs.get("select_idx") is not None:
                    w.app_obj.select_message(kwargs["select_idx"])
                self.wm.focus(w)
                self.start_open = False
            return w
        if name == "alerts":
            # alertes de prix NATIVES (apps/app_alerts.py), même principe
            w = self._launch("alerts")
            if w is not None:
                if kwargs.get("ticker"):
                    w.app_obj.preselect(kwargs["ticker"])
                self.wm.focus(w)
                self.start_open = False
            return w
        if name == "mission":
            # Mission NATIVE (apps/app_mission.py, netteté). Ré-ouvrir une
            # mission EN COURS retrouve la même fenêtre (ne jamais perdre la
            # progression) ; ré-ouvrir une mission TERMINÉE (état "result")
            # en relance une fraîche.
            existing = next((w for w in self.wm.windows if w.key == "mission"), None)
            if existing is not None and getattr(existing.app_obj, "state", "") == "result":
                self.wm.close(existing)
            w = self._launch("mission")
            if w is not None:
                if attention:
                    w.attention = True
                else:
                    self.wm.focus(w)
                self.start_open = False
            return w
        if name == "evaluation":
            # Évaluation NATIVE (apps/app_evaluation.py, netteté) — même règle
            # de ré-ouverture que Mission : un examen EN COURS retrouve SA
            # fenêtre (jamais de perte de progression, l'état de pause est
            # géré à part via player.eval_state) ; un examen TERMINÉ (état
            # "result") est relancé fraîche. kwargs (mode/program/level/tier,
            # cf. scene_cert.py) transmis via `configure()`.
            existing = next((w for w in self.wm.windows if w.key == "evaluation"), None)
            if existing is not None and getattr(existing.app_obj, "state", "") == "result":
                self.wm.close(existing)
                existing = None
            is_new = existing is None
            w = self._launch("evaluation")
            if w is not None:
                if is_new and kwargs:
                    # nouvelle fenêtre avec un mode précis (ex. certification,
                    # cf. scene_cert.py) : configure AVANT que le joueur la
                    # voie — un examen EN COURS retrouvé (fenêtre déjà
                    # existante) garde son état, jamais réinitialisé ici.
                    w.app_obj.configure(**kwargs)
                self.wm.focus(w)
                self.start_open = False
            return w
        if name == "company":
            # Fiche société NATIVE (apps/app_company.py, netteté) — PAS de
            # règle « en cours conservé » comme Mission/Évaluation : chaque
            # appel RECONFIGURE la fenêtre existante sur le ticker demandé
            # (`configure(**kwargs)`, même si la fenêtre était déjà ouverte
            # sur une AUTRE société) — cliquer « Analyse » sur un autre
            # ticker doit remplacer le contenu affiché, jamais rouvrir une
            # fenêtre en double ni laisser une fiche périmée. Ticker par
            # défaut = plus grosse capitalisation (même repli que l'ancien
            # chemin hébergé, cf. _NEEDS_TICKER).
            kw = dict(kwargs)
            if "ticker" not in kw:
                m = self.app.ensure_market()
                top = m.top_companies(n=1)
                if top:
                    kw["ticker"] = top[0]["ticker"]
            w = self._launch("company")
            if w is not None:
                w.app_obj.configure(**kw)
                self.wm.focus(w)
                self.start_open = False
            return w
        if name == "shop":
            # Boutique NATIVE (apps/app_shop.py, netteté) — même règle que
            # "company" : chaque appel RECONFIGURE la fenêtre existante
            # (recherche/filtre pré-remplis si fournis, ex. le lien retour de
            # l'Explorateur) plutôt que de la préserver en l'état, comme le
            # faisait `on_enter` de la scène hébergée à chaque entrée.
            w = self._launch("shop")
            if w is not None:
                w.app_obj.configure(**kwargs)
                self.wm.focus(w)
                self.start_open = False
            return w
        if name == "explorer":
            # Explorateur NATIF (apps/app_explorer.py, netteté) — même règle
            # que "shop"/"company" : chaque appel RECONFIGURE la fenêtre
            # existante (recherche/filtres pré-remplis si fournis, ex. le
            # lien « → EXPLORATEUR » de la Boutique) plutôt que de la
            # préserver en l'état.
            w = self._launch("explorer")
            if w is not None:
                w.app_obj.configure(**kwargs)
                self.wm.focus(w)
                self.start_open = False
            return w
        if name in ("frontier_lab", "hedge", "frontier", "sharpe", "zscore",
                    "options", "greeks", "vardesk", "rates"):
            # Outils quantitatifs NATIFS (apps/app_frontier.py, app_hedge.py,
            # app_sharpe.py, app_zscore.py, app_greeks.py, app_vardesk.py,
            # app_rates.py) : le labo de frontière (lecture seule) est
            # remplacé par la frontière INTERACTIVE, le desk de couverture
            # plein écran (scene_hedge) par l'app Couverture (même logique
            # core/hedging), et le desk d'options plein écran (scene_options)
            # par le Desk Options (mêmes achats core/options + stratégies
            # multi-jambes/modèles/grecques). Simple ouverture/focus.
            key = {"frontier_lab": "frontier", "options": "greeks"}.get(name, name)
            w = self._launch(key)
            if w is not None:
                self.wm.focus(w)
                self.start_open = False
            return w
        if name in ("tradejournal", "deals", "analytics"):
            # Journal de trading / Deals / Analyse du portefeuille NATIFS
            # (apps/app_journal.py, apps/app_deals.py, apps/app_analytics.py,
            # netteté) — simple ouverture/focus, pas une popup forcée par le jeu.
            w = self._launch(name)
            if w is not None:
                self.wm.focus(w)
                self.start_open = False
            return w
        if name in ("book", "markethub", "dilemma", "review"):
            # Portefeuille/Marché/Décision/Revue NATIFS (apps/app_book.py,
            # apps/app_markethub.py, apps/app_dilemma.py, apps/app_review.py),
            # même principe (netteté — plus de rendu 1280×720 réduit). Une
            # décision/revue en attente peut changer entre deux appels (un
            # nouveau dilemme signature après avoir traité le précédent) : si
            # la fenêtre existe déjà, on la referme et relance une instance
            # fraîche plutôt que de garder un état périmé affiché.
            if name in ("dilemma", "review"):
                existing = next((w for w in self.wm.windows if w.key == name), None)
                if existing is not None:
                    self.wm.close(existing)
            w = self._launch(name)
            if w is not None:
                if attention:
                    w.attention = True   # popup FORCÉ : clignote plutôt que de voler le focus
                else:
                    self.wm.focus(w)
                self.start_open = False
            return w
        if name not in self.app.scenes.scenes or name in _FULLSCREEN_EXIT:
            # essayer une app native (ex. "trading" depuis notification)
            if name not in self.app.scenes.scenes and not name.startswith("scene:"):
                launched = self._launch(name)
                if launched is not None:
                    return launched
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
            host.icon_kind = SCENE_ICON.get(name, "generic")
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
        self._draw_index_ticker(surf)
        self._draw_todo(surf)
        self._draw_calendar_widget(surf)
        self._draw_checklist_widget(surf)
        self.wm.draw(surf)
        self._draw_topbar(surf)
        self._draw_taskbar(surf)
        if desktop_onboarding.seen() and not desktop_tutorial.done():
            self._draw_tutorial(surf)
        else:
            self._tuto_skip_rect = None
        _card_suppressed = self._assistant_open or self._search_open
        self._qcard_rects = {}
        self._brief_rects = {}
        if not _card_suppressed:
            # une seule carte modale à la fois — ordre de priorité : bilan de
            # trimestre, puis nouveautés de promotion.
            if self._quarter_card_pending() is not None:
                self._draw_quarter_card(surf)
            elif self._unlock_brief_pending() is not None:
                self._draw_unlock_brief(surf)
        if self.start_open:
            self._draw_launcher(surf)
        if self._ctx_menu is not None:
            self._draw_context_menu(surf)
        if self._search_open:
            self._draw_search(surf)
        if self._assistant_open:
            self._draw_assistant_card(surf)
        # guide de démarrage : TOUT au-dessus (modal, début de partie)
        if self._intro_guide_active():
            self._draw_intro_guide(surf)

    def _draw_wallpaper(self, surf):
        # Fond de bureau pré-rendu et mis en cache : un dégradé linéaire léger
        # + une texture de bruit tileable étirée + un quadrillage discret.
        area = pygame.Rect(0, TOPBAR_H, config.SCREEN_WIDTH,
                           config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H)
        if self._wallpaper_cache is None or self._wallpaper_cache.get_size() != (area.w, area.h):
            wp = pygame.Surface((area.w, area.h))
            # dégradé linéaire vertical très subtil (plus rapide qu'un radial)
            grad = style.surface_gradient(
                area.w, area.h,
                style._lerp_color(config.COL_PANEL, config.COL_WHITE, 0.02),
                config.COL_BG)
            wp.blit(grad, (0, 0))
            # bruit tileable 128x128 étiré (alpha très faible)
            noise = style.noise_texture(area.w, area.h, intensity=8, seed=42)
            noise.set_alpha(12)
            wp.blit(noise, (0, 0))
            # quadrillage discret
            step = 56
            grid = pygame.Surface((area.w, area.h), pygame.SRCALPHA)
            for gx in range(0, area.w, step):
                pygame.draw.line(grid, (*config.COL_GRID, 45), (gx, 0), (gx, area.h), 1)
            for gy in range(0, area.h, step):
                pygame.draw.line(grid, (*config.COL_GRID, 45), (0, gy), (area.w, gy), 1)
            wp.blit(grid, (0, 0))
            self._wallpaper_cache = wp
        surf.blit(self._wallpaper_cache, area.topleft)
        # watermark discret
        widgets.draw_text(surf, "TERMINAL ALPHA",
                          (config.SCREEN_WIDTH // 2, area.centery),
                          fonts.ui_title(bold=True), (22, 26, 34), align="center")

    def _draw_topbar(self, surf):
        bar = pygame.Rect(0, 0, config.SCREEN_WIDTH, TOPBAR_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar)
        pygame.draw.line(surf, config.COL_AMBER, (0, bar.bottom - 1), (bar.right, bar.bottom - 1), 1)
        # menu (à gauche)
        self._menu_rect = pygame.Rect(8, 5, 66, TOPBAR_H - 10)
        mh = self._menu_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if mh else config.COL_PANEL_HEAD, self._menu_rect, border_radius=4)
        desktop_icons.draw(surf, (self._menu_rect.x + 16, self._menu_rect.centery), "menu", size=18)
        widgets.draw_text(surf, "Menu", (self._menu_rect.x + 28, self._menu_rect.y + 5),
                          fonts.small(bold=True), config.COL_AMBER)
        # loupe : recherche globale (Ctrl+/) — dessinée en VECTORIEL (cercle +
        # manche), même précaution que les icônes du bureau (pas de glyphe
        # emoji, couverture non garantie par la police embarquée)
        self._gsearch_rect = pygame.Rect(self._menu_rect.right + 6, 5, 26, TOPBAR_H - 10)
        gh = self._gsearch_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if gh else config.COL_PANEL_HEAD,
                         self._gsearch_rect, border_radius=4)
        gc = self._gsearch_rect.center
        lens_c = (gc[0] - 2, gc[1] - 2)
        pygame.draw.circle(surf, config.COL_CYAN if gh else config.COL_TEXT_DIM, lens_c, 6, 2)
        pygame.draw.line(surf, config.COL_CYAN if gh else config.COL_TEXT_DIM,
                         (lens_c[0] + 4, lens_c[1] + 4), (gc[0] + 7, gc[1] + 7), 2)

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
        # indicateur de risque unifié (pastille), toujours à l'extrême droite ;
        # le badge difficulté/défi du jour se pousse à sa gauche s'il est présent
        # (cf. core/risk_indicator.py — un seul repère plutôt que d'avoir à
        # interpréter levier/marge/concentration séparément soi-même).
        risk_right = self._draw_risk_badge(surf, bar)
        status = difficulty_mod.status_label(p)
        if status:
            widgets.draw_badge(surf, status.upper(), (risk_right - 14, 8),
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
                           size=18)
        widgets.draw_text(surf, "Apps", (self._start_rect.x + 28, self._start_rect.y + 4),
                          fonts.small(bold=True), config.COL_BG if active else config.COL_AMBER)
        pygame.draw.line(surf, config.COL_BORDER, (self._start_rect.right + 4, bar.y + 4),
                         (self._start_rect.right + 4, bar.bottom - 4), 1)
        # quick-launch (à gauche) : apps natives + Terminal. Les clés
        # _FACTORY_ONLY_APPS en sont EXCLUES comme des icônes du bureau —
        # même raison (cf. commentaire de _FACTORY_ONLY_APPS) : un bouton
        # « Évaluation » ici aurait contourné les critères de promotion, et
        # « Décision »/« Revue » ouvriraient des écrans vides hors popup.
        self._launch_rects = {}
        x = self._start_rect.right + 10
        quick = [(k, kind) for k, _l, kind, _cls in APPS
                 if k not in self._FACTORY_ONLY_APPS and self._icon_visible(k)]
        quick.append(("terminal", "terminal"))
        # le quick-launch est BORNÉ à ~40 % de la barre : au-delà, les icônes
        # supplémentaires restent accessibles par le bureau/menu Démarrer, et
        # la place des FENÊTRES ouvertes (droite) est préservée quel que soit
        # le nombre d'apps enregistrées (le bureau en gagne à chaque version).
        x_limit = int(config.SCREEN_WIDTH * 0.40)
        for key, kind in quick:
            if x + 30 > x_limit:
                break
            r = pygame.Rect(x, bar.y + 4, 26, TASKBAR_H - 8)
            self._launch_rects[key] = r
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD, r, border_radius=4)
            desktop_icons.draw(surf, r.center, kind, size=18)
            x += 30
        pygame.draw.line(surf, config.COL_BORDER, (x + 2, bar.y + 4), (x + 2, bar.bottom - 4), 1)
        x += 10
        # fenêtres ouvertes — largeur d'entrée ADAPTATIVE (façon barre des
        # tâches d'un vrai OS) : avec beaucoup de fenêtres, des entrées à
        # largeur fixe débordaient du bord droit de l'écran et les fenêtres
        # correspondantes devenaient infocalisables/irrestaurables depuis la
        # barre (bug V1.0) ; on rétrécit jusqu'à l'icône seule s'il le faut.
        self._task_rects = {}
        n_win = len(self.wm.windows)
        avail = config.SCREEN_WIDTH - x - 10
        entry_w = 150 if n_win == 0 else max(28, min(150, avail // n_win - 6))
        for w in self.wm.windows:
            r = pygame.Rect(x, bar.y + 4, entry_w, TASKBAR_H - 8)
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
            desktop_icons.draw(surf, (r.x + 12, r.centery), kind, size=16,
                               alpha=150 if w.minimized else 255)
            if r.w > 48:   # trop étroit : icône seule, pas de texte tronqué illisible
                widgets.draw_text(surf, widgets.fit_text(w.app_obj.title, fonts.tiny(), r.w - 26),
                                  (r.x + 22, r.y + 5), fonts.tiny(bold=True), col)
            x += entry_w + 6
