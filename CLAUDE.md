# CLAUDE.md

Instructions projet pour Claude Code (local **et** cloud). Le jeu est un simulateur de
carrière en finance de marché, écrit en Python + pygame. Langue de travail : **français**.

## Lancer le jeu

```bash
pip install -r requirements.txt        # pygame, numpy, scipy
python main.py                         # jeu normal
python main_cheat.py                   # jeu + triches (GRADE/MAXUNLOCK/CASH/REP au terminal)
```

Le jeu a besoin d'un affichage. En environnement sans écran (cloud/CI), on ne **lance** pas
le jeu interactivement : on vérifie via la compilation, les tests, et le harnais headless.

## Tests

```bash
pip install numpy scipy pytest pygame
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest
```

- Suite pytest dans `tests/` (~200 tests). Couvre la logique pure : finmath (formules),
  market (déterminisme, calibration, crises, earnings, régimes, attribution), portfolio
  (levier/short), exam, tracks, deal_game, financials.
- `tests/test_scene_smoke.py` est un test de fumée headless qui visite **chaque** scène
  enregistrée dans `main.py::App` via `on_enter()`/`update()`/`draw()`, pour attraper en CI
  les régressions de rendu (AttributeError...) qu'un simple `py_compile` ne voit pas. Ce
  test nécessite pygame ; la CI (`.github/workflows/tests.yml`) installe donc
  `numpy scipy pytest pygame` avec `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`.
  **Angle mort connu de ce smoke test** : le marché y est fraîchement créé (1-2 points
  d'historique), donc il n'exerce JAMAIS le rendu des graphes avec un historique réel
  (`len(vals) >= 2` dans `ui/datawindow.py`) — c'est ce qui a laissé passer le crash
  `widgets._hover_sync` (cf. plus bas). `tests/test_terminal_desktop_fuzz.py` couvre ce
  cas : marché avancé de 40 pas puis fuzz pseudo-aléatoire (graine fixe, ~150 évènements)
  du terminal/bureau/marché/portefeuille, plus un test ciblé qui clique CHAQUE ligne du
  panneau INDICES et vérifie que chacune ouvre bien SON PROPRE graphe.
- `tests/test_facade_exports.py` verrouille par ANALYSE AST (pas une recherche texte, pour
  ignorer commentaires/docstrings) que toute expression `widgets.<x>` / `pf.<x>` /
  `pf_mod.<x>` / `PF.<x>` réellement présente dans le code résout sur le VRAI module
  (`ui.widgets`/`core.portfolio`) — ces deux modules réexportent explicitement des helpers
  depuis `ui/chart_widgets.py`/`core/portfolio_margin.py`/`core/portfolio_views.py`
  (`from X import (...)`, cf. commentaire « réexport » dans ces fichiers), et un symbole
  oublié de cette liste (`widgets._hover_sync`) a fait planter tout le jeu au clic sur un
  graphe avec historique — invisible à la compilation, seulement à l'exécution.
- `core/crashlog.py` + `main.py::App._safe_call` : la boucle principale (`App.run`) n'attrape
  plus aucune exception qui, avant, fermait le jeu entier (ex. le crash ci-dessus). Chaque
  appel à `handle_event`/`update`/`draw` est absorbé individuellement : l'exception est
  journalisée (fichier `crash.log` sous `config.SAVE_DIR`, borné à 20 entrées, best-effort —
  ne doit jamais lui-même lever) et un toast prévient le joueur (au plus un par 5 s, pour ne
  pas spammer si le même bug se reproduit à chaque frame), mais la partie continue. Ne
  remplace pas la correction des bugs eux-mêmes : un filet, pas une excuse à ne pas tester.

## Vérification d'une modif

1. Syntaxe : `python -m py_compile main.py core/*.py ui/*.py scenes/*.py data/*.py`
2. Logique pure (`core/`) : testable directement, ajouter/lancer les tests pytest.
3. Runtime des scènes (si modif d'une scène/widget) : harnais headless avec
   `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` → instancier `main.App()`, faire
   `app.scenes.go(name)` puis `update()/draw()` sur chaque scène pour attraper les erreurs
   de rendu (AttributeError, draw) que `py_compile` ne voit pas.

## Architecture

- **`main.py`** : `App` (boucle pygame, enregistrement des scènes, `ensure_market()`,
  `sim_clock`/`pending_market_steps`). `core/scene_manager.py` gère la pile de scènes + toasts.
- **Bureau « Jeu PC » (refonte UI, étape 1)** : `scenes/scene_desktop.py` (`DesktopScene`,
  scène `"desktop"`) est un BUREAU façon poste de travail — fond + icônes d'apps, barre
  supérieure (horloge/trésorerie/vitesse/⚙), barre des tâches. Les applications s'ouvrent
  dans des FENÊTRES déplaçables/redimensionnables/minimisables cohabitant à l'écran, gérées
  par `ui/window_manager.py` (`Window` + `WindowManager` : z-order, focus, routage des
  évènements vers l'app focalisée). Chaque app hérite de `apps/base.DesktopApp` et dessine
  dans le rectangle de contenu qu'on lui passe (coords absolues) : `apps/app_research.py`
  (recherche sociétés type Bloomberg), `apps/app_trading.py` (achat/vente actions, réutilise
  `core/portfolio`), `apps/app_sheet.py` (tableur libre + formules, réutilise
  `core/spreadsheet_engine` et partage `app.sheet`). Le bureau est une scène « live »
  (`sim_clock.LIVE_SCENE_NAMES` inclut `"desktop"`) : le temps avance et les pas de marché
  sont joués via `TerminalScene._drain_pending_steps()` (le terminal reste le moteur de la
  boucle de jeu). Accès depuis le terminal (commande `DESKTOP`/`BUREAU`, rail « 🖥 BUREAU »).
  **Étape 2 (« tout en fenêtres »)** : `apps/scene_host.py` (`SceneHostApp`) héberge
  N'IMPORTE QUELLE scène plein écran existante dans une fenêtre — la scène dessine dans une
  surface hors-champ à taille logique pleine, mise à l'échelle dans la fenêtre ; les
  coordonnées souris sont retransformées et `pygame.mouse.get_pos` redirigé pendant
  update/draw/handle_event pour aligner le survol. La navigation des scènes (`app.scenes.go`)
  est interceptée par un routeur (App *proxy* dont `.scenes` route `go()` vers l'ouverture
  d'une fenêtre au lieu de changer de scène). Un **menu Démarrer** (bouton « ⊞ Apps » de la
  barre des tâches) liste toutes les scènes (groupées comme le hub PLUS,
  `scene_more.SECTIONS`) : chaque item ouvre la scène en fenêtre. Le bureau est désormais
  l'**écran d'atterrissage** d'une nouvelle partie (`scene_intro` → `desktop` ; le terminal
  est initialisé au 1er `on_enter` du bureau pour piloter le temps). Le terminal classique
  reste accessible (icône « Terminal »).
  **Étape 3** : app dédiée à la VOIE choisie (`TRACK_APP` dans `scene_desktop.py` — M&A→`ma`,
  Risk→`risk`, Quant→`quant`, Portfolio→`portfolio_unified`, Advisory→`mandates`) : une fois
  `player.track` fixé (hors `"General"`), une icône supplémentaire apparaît sur le bureau et
  ouvre l'écran de la voie en fenêtre, comme les autres apps (ouvrable en même temps —
  ex. suivre le FX pendant que la fenêtre M&A tourne à côté). Les navigations FORCÉES par le
  jeu (pas un clic joueur — ex. un dilemme qui se déclenche pendant que le temps passe) 
  utilisent `App.route_scene(name, **kwargs)` : sur le bureau, ouvre une fenêtre (popup de
  choix parmi les autres) au lieu de basculer tout l'écran ; sinon comportement classique
  (`scenes/scene_terminal_time.py` l'utilise pour le déclenchement d'un dilemme). Le Tableur
  est passé à un **classeur multi-feuilles** (`core/workbook.py::Workbook`, onglets façon
  Excel) partagé par l'app native (`apps/app_sheet.py`, `app.workbook`) : un export (état
  financier, fiche M&A…) remplit la feuille ACTIVE si elle est vierge, sinon ouvre une
  NOUVELLE feuille (`Workbook.import_financial`) — jamais d'écrasement silencieux d'un modèle
  en cours. Toute navigation vers l'ancienne scène plein écran `"spreadsheet"` (bouton
  « → TABLEUR », entrée PLUS) est interceptée par `DesktopScene._open_scene_window` et
  redirigée vers cette app native (`_open_sheet_app`) — un seul tableur sur le bureau. La
  scène plein écran `scene_spreadsheet.py` (et son état `app.sheet`) a depuis été RETIRÉE :
  le nom `"spreadsheet"` reste enregistré comme ALIAS (`scenes/scene_sheet_redirect.py`) qui
  atterrit sur le bureau avec l'app Tableur ouverte — un seul tableur, un seul état
  (`app.workbook`).
  **Étape 4 : le bureau devient l'ÉCRAN MAÎTRE**, et le TERMINAL lui-même devient une fenêtre
  comme les autres (plus de scène plein écran séparée pour jouer). `DesktopScene` crée à
  l'arrivée une instance TERMINAL persistante (`self._terminal_host`, un `SceneHostApp`) qui
  reste le MOTEUR de la boucle de jeu tant que la partie tourne — `_tick_market()` l'utilise
  directement, que sa fenêtre soit ouverte, minimisée (état par défaut au démarrage, bureau
  propre) ou fermée (fermer la fenêtre ne tue pas le moteur : le temps continue de s'écouler ;
  ré-ouvrir via l'icône Terminal retrouve la MÊME instance, jamais de doublon). Comme toute
  navigation interne du terminal (`self.app.scenes.go(...)`, ex. taper SHOP) passe par SA
  PROPRE proxy (le terminal est hébergé comme les autres scènes), taper une commande dans le
  terminal ouvre désormais une FENÊTRE sur le bureau plutôt que de basculer plein écran — le
  terminal se comporte comme n'importe quelle autre app. Les points d'entrée qui atterrissaient
  auparavant sur `"terminal"` (nouvelle partie via `scene_intro`, sandbox, chargement de
  sauvegarde `scene_saves.py`/`SceneManager._quickslot_load`) atterrissent désormais tous sur
  `"desktop"` — `"desktop"` est dans `BREADCRUMB_SKIP` (`core/scene_manager.py`, pas de fil
  d'Ariane à afficher par-dessus, toute la navigation y étant interne aux fenêtres). Seules les
  scènes de flux pré/post-partie (`_FULLSCREEN_EXIT` dans `scene_desktop.py` : menu, gameover,
  intro, continent, runsetup, sandbox, splash) restent une VRAIE bascule plein écran — quitter
  le bureau pour de bon. Icônes du bureau en GRILLE (pas une colonne, `_icon_list`/
  `_draw_desktop_icons`), dessinées en VECTORIEL (`ui/desktop_icons.py`) : les emoji
  (🔍💹▦🖥🤝⚠∑…) ne s'affichent pas de façon fiable dans la police embarquée JetBrains Mono
  (pas de couverture emoji), même défaut déjà rencontré et corrigé pour le bouton pause
  (`ui/simclock_widget.py`, dont le bureau réutilise directement les fonctions de dessin
  `_draw_pause`/`_draw_speed`/`_draw_gear` pour des contrôles identiques). Chrome de fenêtre
  (`ui/window_manager.py`) et titres de fenêtres hébergées (`DesktopApp.icon_kind`,
  `apps/base.py`) migrés au même système d'icônes vectorielles.
  **Étape 5 : le rail latéral du terminal a été RETIRÉ** — ses ~17 accès rapides
  (MARCHÉ/PORTEF./ALERTES/INBOX/NEWS/MISSION/MANDATS/DEALS/DÉCIDE/EXAM-CERTIF/MUR/SHOP/
  EXPLORATEUR/GRAPHES/PLUS/SAUVER/AIDE) sont désormais des ICÔNES DU BUREAU
  (`QUICK_APPS` dans `scene_desktop.py`), ouvrant chacune la scène correspondante EN FENÊTRE
  via `_open_scene_window` (même mécanisme que le menu Démarrer) — "SAUVER" (`"save"`) est la
  seule action instantanée (pas une fenêtre, `_quick_save`). `scenes/scene_terminal.py` n'a
  plus de `self.rail`/`self.rail_w` : la colonne qu'occupait le rail (150px) revient aux 3
  colonnes du terminal (`gx = 2 * M` dans `scene_terminal_render.py`, plus de
  `_draw_rail`/`_rail_rects`) ; la zone clavier `"rail"` a disparu de `ZONE_ORDER` (les
  raccourcis Ctrl+<lettre>, `RAIL_SHORTCUTS`, restent inchangés — indépendants du rendu
  visuel). Le terminal reste accessible en fenêtre (icône « Terminal », cf. étape 4) mais tout
  ce qu'il exposait en boutons latéraux vit maintenant sur le bureau. Les icônes du bureau
  s'organisent en **grille multi-colonnes** (`_draw_desktop_icons`) pour absorber ce volume.
  **Atterrissage sur le bureau généralisé** : `scene_menu.py::_continue()` (bouton CONTINUER,
  reprise de l'autosave) va sur `"desktop"` (plus `"terminal"`) ; `PageManager` — système
  d'onglets, `core/pages.py` — a son `main_scene_name` par défaut à `"desktop"`, et un
  **nouvel onglet** (bouton « + » / Ctrl+T, `PageManager.open_new_tab()`, ex-`duplicate_current`)
  ouvre TOUJOURS sur le bureau plutôt que de dupliquer l'onglet courant.
  **Étape 6** : la **calculatrice** devient une app du bureau (`apps/app_calculator.py`,
  `CalculatorApp`, icône « calc ») — jusqu'ici accessible uniquement en overlay flottant
  depuis les missions/examens (`ui/calculator.py`, toujours utilisé tel quel à cet endroit) ;
  l'app du bureau réutilise sa logique de calcul (`safe_eval`, touches scientifiques) sans le
  cadre/titre du widget d'origine (chrome fourni par la fenêtre). Le **tableur** (`apps/app_sheet.py`)
  devient nettement plus « façon Excel » :
  - **Catalogue de formules** (bouton « fx ▾ » de la barre d'outils) : panneau catégorisé
    (Maths/Statistiques/Finance/Logique) listant chaque fonction du moteur
    (`core/spreadsheet_engine.FUNCTIONS`, complété par `MEDIAN`/`CORREL`/`PV`/`FV`) avec une
    courte description ; cliquer insère `NOM(` dans la formule en cours (`_insert_function`).
  - **Sélection de plage** : glisser la souris sur plusieurs cellules (`range_anchor`/
    `range_end`, mis à jour par `handle_event` sur MOUSEMOTION tant que `_dragging_range`),
    surlignée dans la grille (en-têtes + cellules).
  - **Graphiques insérés sur la feuille** (`core/workbook.SheetChart` — type/plage/position,
    stockés par `WorkbookTab.charts`, PAS persistés) : 3 types depuis la barre d'outils —
    Ligne, Barres (une colonne de valeurs, éventuellement précédée d'une colonne d'étiquettes),
    Nuage de points (exige EXACTEMENT 2 colonnes numériques X;Y, message d'erreur sinon). Les
    données sont relues EN DIRECT depuis la feuille à chaque frame (`_chart_data`) — un
    graphique reflète donc les recalculs de formules. Chaque graphique est une boîte flottante
    par-dessus la grille (positionnée en coordonnées RELATIVES au contenu de la fenêtre, donc
    stable si la fenêtre est déplacée) : titre déplaçable (glisser), bouton fermer (×). Dessin
    par primitives `pygame.draw` directes (`_draw_line`/`_draw_bar`/`_draw_scatter`), pas de
    dépendance à `widgets.draw_series` (pensé pour les séries de prix, pas les données tableur
    génériques). Pas de VBA/macros — uniquement formules + graphiques, l'usage courant d'Excel
    en finance.
  **Étape 7 (polish navigation/lisibilité)** : les graphiques du tableur ont désormais un
  **cadre d'axes avec étiquettes** (min/médiane/max, `SheetApp._axis_frame`) — lisibilité
  chiffrée façon Excel plutôt qu'un tracé nu — et une **poignée de redimensionnement** (coin
  bas-droit, comme les fenêtres du bureau, `_chart_resize_rects`) ; leur position/taille sont
  **bornées à chaque frame** à la zone de contenu courante (`_draw_chart`), donc jamais perdus
  hors champ si la fenêtre est rétrécie après coup. `ui/window_manager.py::WindowManager
  .cycle_focus(reverse=False)` ajoute la navigation **Alt+Tab** entre les fenêtres ouvertes du
  bureau (round-robin déterministe trié par clé, pas par ordre de focus récent — cycle complet
  prévisible même avec beaucoup de fenêtres) ; câblé en tout premier dans
  `DesktopScene.handle_event` (Alt+Maj+Tab = sens inverse).
  **Étape 8 : formules de MARCHÉ EN DIRECT dans le tableur.** Le moteur
  (`core/spreadsheet_engine.py`) reste PUR mais accepte un résolveur de fonctions
  EXTERNES injecté (`Spreadsheet.external = callable(name, args) -> valeur|None`) :
  si une fonction n'est pas dans `FUNCTIONS`, le parseur délègue à ce résolveur. L'app
  (`apps/app_sheet.py::_market_fn`) fournit `PRICE("MVC")`, `INDEX(nom)`, `FX("USD/JPY")`,
  `SHARES("MVC")`, `NETWORTH()`, `CASH()` — lues sur `app.market`/`gs.player`. Comme le
  marché avance par pas déterministes, `_sync_market()` (appelé à chaque `draw`) invalide le
  cache (`Spreadsheet.invalidate()`) quand `market.step_count` change → les cellules et donc
  les graphiques qui en dépendent se recalculent en direct au fil du temps qui passe (un
  modèle « attend le bon moment » tout seul). Un ticker inconnu renvoie `"#N/A"` (pas de
  crash). Catégorie « Marché (en direct) » ajoutée au catalogue `fx ▾`.
  **Étape 9 : liens cliquables entre apps.** Les apps natives reçoivent une back-ref
  `desktop` (posée par `DesktopScene._launch`/`_open_sheet_app`, cf. `apps/base.DesktopApp`).
  L'app Recherche (`apps/app_research.py`) affiche une barre d'actions dans le panneau détail —
  **Trader** (`DesktopScene.open_trading(ticker)` → ouvre/focalise Trading pré-filtré via
  `TradingApp.focus_ticker`), **→ Tableur** (`DesktopScene.add_quote_to_sheet` → `SheetApp
  .add_quote` insère `ticker`/`=PRICE("ticker")` en 1re ligne libre, cours vivant), **Analyse**
  (`_open_scene_window("company", ticker=…)` → fiche Refinitiv en fenêtre). Transforme les
  fenêtres juxtaposées en vrai flux de travail (repérer → trader/modéliser sans re-saisir).
  **Étape 10 : ancrage/maximisation + palette Ctrl+K en fenêtres.** `ui/window_manager.py`
  gère l'**ancrage** (glisser une fenêtre vers un bord de `WindowManager.work_area` → aperçu
  cyan puis, au relâcher, moitié gauche/droite ou plein — `_snap_target`/`_snap_preview`, la
  fenêtre garde `_restore_rect` pour revenir) et la **maximisation** (double-clic sur la barre
  de titre → `maximize_toggle`, re-double-clic restaure). Le bureau règle `wm.work_area` entre
  la barre supérieure et la barre des tâches (`DesktopScene.on_enter`) pour que rien ne passe
  dessous. La **palette Ctrl+K** (`core/scene_manager.py`) route désormais via
  `_palette_navigate` : sur le bureau, ouvre l'entrée choisie EN FENÊTRE (`App.route_scene`)
  au lieu de basculer plein écran ; ailleurs, comportement classique inchangé.
  **Étape 11 : conscience ambiante du bureau.** Trois ajouts pour garder le pouls de la partie
  visible même « toutes fenêtres fermées » : (1) **widget patrimoine ambiant**
  (`DesktopScene._draw_ambient`) dessiné dans le coin bas-droit du bureau (sous les fenêtres,
  au-dessus de la barre des tâches) — patrimoine net (couleur up/down vs `player.cash_history[0]`),
  cash, levier (`core/portfolio_margin.leverage`, ambre >1x / rouge >2x) et une mini-sparkline de
  `cash_history` ; cliquer ouvre le portefeuille en fenêtre (`_open_scene_window("book")`). (2)
  **app Watchlist** (`apps/app_watchlist.py`, icône « star » vectorielle dans `ui/desktop_icons.py`,
  clé `"watchlist"` dans `APPS`) : liste `player.watchlist` (max 10) avec cours + variation du
  dernier pas EN DIRECT ; clic sur une ligne → Trading pré-filtré (`desktop.open_trading`), « × »
  retire la valeur. La watchlist est alimentée par la commande `WATCHLIST` du terminal ET par une
  action **Suivre/Suivi** ajoutée à la barre d'actions de l'app Recherche (`app_research._do_action
  ("watch")`, fond plein quand suivie). (3) **barre des tâches clignotante** : `Window.attention`
  (posé par `_open_scene_window(..., attention=True)`, câblé depuis `App.route_scene` pour les
  popups FORCÉS par le jeu — dilemmes) fait clignoter l'entrée de la fenêtre dans la barre des
  tâches (`_draw_taskbar`) jusqu'au premier `WindowManager.focus` (un coup d'œil éteint le
  clignotement).
  **Étape 12 : découvrabilité (accueil + menus contextuels).** (1) **Accueil du bureau** :
  l'ex-carte d'accueil machine (`_draw_onboarding`) a été FUSIONNÉE dans le guide de démarrage
  de l'étape 19 (sa dernière page couvre le poste de travail : fenêtres/ancrage/Alt+Tab, clic
  droit, terminal-moteur, widget patrimoine, Ctrl+K / Ctrl+/ / F1). `core/desktop_onboarding.py`
  (JSON par machine, distinct de `core/onboarding.py` — parcours guidé du TERMINAL) ne sert plus
  que de porte d'entrée du tutoriel guidé : marqué vu à la fermeture du guide, ou dès l'arrivée
  sur le bureau quand le guide ne s'affichera pas (vétéran/sandbox/déjà lu — cf. `on_enter`).
  (2) **Menus contextuels (clic droit)**
  (`_open_context_menu`/`_handle_ctx_event`/`_draw_context_menu`, état `self._ctx_menu`) selon la
  cible sous le curseur : icône du bureau (Ouvrir / Ouvrir puis ancrer à gauche·droite), barre de
  titre OU entrée de barre des tâches d'une fenêtre (Réduire/Restaurer, Agrandir/Restaurer,
  Ancrer gauche·droite, Fermer), fond du bureau (Menu Applications, Réglages, Fermer toutes les
  fenêtres, Guide de démarrage). L'ancrage réutilise la logique de l'étape 10 (`_snap_window` pose
  `_restore_rect`) ; « Fermer toutes les fenêtres » ne fait que MINIMISER le terminal (jamais
  arrêter le moteur). Le menu se referme au clic sur un item (exécute son action), à tout clic
  hors menu, ou sur Échap ; un clic droit sur le CONTENU d'une fenêtre reste routé vers l'app.
  **Étape 13 : tableur avancé (recherche, mise en forme conditionnelle, CSV, copier/coller,
  annuler/rétablir).** `core/spreadsheet_engine.py` gagne **VLOOKUP** (`Parser._vlookup`,
  correspondance EXACTE uniquement — le 4e argument optionnel façon Excel est accepté mais
  ignoré) : contrairement aux autres fonctions (args déjà aplatis en liste scalaire via
  `_range_values`), VLOOKUP a besoin de la FORME de la plage (colonne de recherche vs colonne de
  retour, même ligne) — `Parser._range_grid` construit une grille `[ligne][colonne]` dédiée, sans
  changer le comportement des agrégats existants (SUM/AVERAGE/NPV… restent order-sensitive là où
  il le faut, cf. tests). `core/workbook.py::ConditionalFormat` (liste `WorkbookTab.cf_rules`) :
  mise en forme conditionnelle simplifiée — un seuil numérique (opérateur `>`, `<`, `>=` ou `<=`) sur une
  plage, résolu en couleur logique (`up`/`down`/`amber`) via `WorkbookTab.cf_color_for` (la
  DERNIÈRE règle qui correspond gagne, comme Excel) ; l'app (`apps/app_sheet.py`, panneau « CF »
  de la barre d'outils) peint la cellule d'un survol translucide (`pygame.SRCALPHA`) sans
  toucher au texte. **Export CSV** (bouton « CSV ») : écrit les VALEURS calculées (pas les
  formules) de la feuille active vers le dossier personnel de l'utilisateur — pas de sélecteur de
  fichier natif (comme la sauvegarde rapide du bureau), le message affiche le chemin écrit.
  **Copier/coller de plage** (Ctrl+C/Ctrl+V, `_copy_range`/`_paste_range`) : copie les FORMULES
  brutes (pas les valeurs) ; au collage, les références sont DÉCALÉES du vecteur copie→collage
  comme dans Excel (`core/spreadsheet_engine.shift_formula` — les ancres `$` de `$A$1`/`$A1`/
  `A$1` figent colonne et/ou ligne, supportées aussi à l'évaluation ; une référence décalée hors
  grille devient `#REF`), bornées aux limites de la feuille. **Annuler/rétablir**
  (Ctrl+Z/Ctrl+Y, `_undo`/`_redo`, pile en mémoire non persistée) : chaque édition/effacement/
  collage empile l'état AVANT modification (`_record_undo`) ; un collage multi-cellules s'annule
  en un seul Ctrl+Z (toute la plage), pas cellule par cellule ; toute NOUVELLE action vide la
  pile de rétablissement. Les raccourcis Ctrl+C/V/Z/Y ne s'activent que HORS édition d'une
  cellule (`not self.editing`) pour ne jamais intercepter la frappe normale dans la barre de
  formule.
  **Étape 14 : ordres conditionnels (stop-loss / take-profit / trailing).**
  `core/conditional_orders.py` (logique pure) : un ordre (`{"id","ticker","kind","trigger",
  "qty","is_short"}`, `kind` = `"stop"`, `"target"` ou `"trailing"`) posé sur une position
  LONGUE **ou COURTE** détenue — les shorts vivent dans `player.portfolio` avec un nombre de
  titres NÉGATIF (cf. `core/portfolio.short`, PAS de dict séparé ; helper `_position`). Sur un
  long, `execute_due(player, market)` vend (`core/portfolio.sell`) au franchissement (`<=` pour
  stop, `>=` pour target) ; sur un short, il COUVRE (`core/portfolio.cover`) avec la logique
  INVERSÉE (stop si le cours monte, target s'il baisse). Le trailing (posé par
  `place_trailing`, seuil suivant le cours à distance % via `update_trailing_stops`, appelé
  AVANT `execute_due`) a la sémantique d'un STOP — surtout pas d'un target, sinon exécution
  immédiate côté favorable. Un ordre dont la position a disparu OU CHANGÉ DE CÔTÉ entre-temps
  est abandonné silencieusement. Câblé dans `GameState.advance_step` : exécuté à CHAQUE pas de
  marché, juste avant `check_margin_call` (un ordre voulu par le joueur passe avant une
  liquidation forcée sur la position déjà réduite), résultat exposé dans
  `summary["conditional_orders_executed"]` et loggé/notifié par `scenes/scene_terminal_time.py`
  (« vendu »/« couvert » selon le côté). Contrairement à l'ALERTE de prix (notifie sans agir),
  un ordre conditionnel EXÉCUTE un ordre réel, même fenêtre Trading fermée (le terminal reste
  le moteur). UI : `apps/app_trading.py` — bouton « ORD » (texte plain, pas de glyphe
  pictographique) sur chaque ligne détenue (longue OU courte — quantité courte affichée en
  rouge) ouvre une boîte de dialogue (choix stop/target/trailing + seuil, avec une ligne
  expliquant le sens de déclenchement selon le côté) ; une bande « ORDRES CONDITIONNELS » sous
  la liste des valeurs récapitule les ordres en cours de la partie (tag « (short) », tous
  titres confondus), avec annulation (×) individuelle — rétrécit dynamiquement la liste de
  valeurs pour rester visible sans la recouvrir.
  **Étape 15 : recherche globale sur les données de partie (Ctrl+/).** `core/global_search.py`
  (logique pure) cherche dans ce que le joueur POSSÈDE/REÇOIT déjà dans sa partie — positions,
  watchlist, inbox, mandats actifs, deals actifs — par opposition à la palette de navigation
  (Ctrl+K, `core/scene_manager.py`) qui cherche du contenu de RÉFÉRENCE (tickers du marché,
  glossaire, leçons, scènes). Raccourci **Ctrl+/** (pas Ctrl+F : déjà pris par le rail du
  terminal pour M&A, cf. `RAIL_SHORTCUTS` dans `scenes/scene_terminal.py`), câblé dans
  `DesktopScene.handle_event` (prioritaire, avant même le menu contextuel). Chaque résultat
  ({"label", "kind", "action"}) navigue selon son type : position/watchlist → Trading pré-filtré
  (`DesktopScene.open_trading`), inbox/mandats/deals → la fenêtre correspondante. Réutilise
  `core/fuzzy.filter_sorted` (même moteur de correspondance floue que Ctrl+K) sur un haystack
  concaténé par entrée (ticker+nom, sujet+expéditeur+corps, nom client, titre de deal).
  **Étape 16 : les clics ne traversent plus les fenêtres + rendu moins flou.**
  `ui/window_manager.py::WindowManager.handle_event` renvoyait `bool(app_obj.handle_event(...))`
  quand un clic tombait dans le CONTENU d'une fenêtre — si l'appli ne réagissait pas à ce clic
  précis (zone morte du Tableur…), la méthode renvoyait `False`, et `DesktopScene.handle_event`
  continuait alors à tester les cibles du bureau EN DESSOUS (icônes, barre des tâches) à ces
  mêmes coordonnées écran, déclenchant potentiellement un élément sans rapport (ex. cliquer
  dans le Tableur activait le Mur posé derrière). Corrigé : dès qu'une fenêtre est trouvée sous
  le clic (`_topmost_at`), l'évènement est transmis à l'appli pour ses effets de bord mais la
  méthode renvoie désormais TOUJOURS `True` — un clic dans les limites d'une fenêtre est
  absorbé, point final, jamais de fallthrough vers ce qu'il y a derrière (même règle pour la
  molette/clic droit, branche `button in (3, 4, 5)`). Par ailleurs, deux causes de flou visuel
  corrigées : (1) `main.py` pose `PYGAME_FORCE_SCALE=photo` avant `pygame.init()` (filtre de
  mise à l'échelle linéaire plutôt que le filtre par défaut pour les modes plein écran/sans
  bordure `pygame.SCALED`) — désactivé quand `SDL_VIDEODRIVER=dummy` (tests headless/CI), le
  driver factice n'ayant pas de renderer matériel et échouant sur `set_mode` avec ce réglage ;
  (2) `apps/scene_host.py::SceneHostApp.default_size` relevé de `(940, 560)` à `(1180, 620)` —
  les scènes hébergées (la grande majorité des écrans du jeu) sont rendues dans une surface
  hors-champ à résolution logique pleine (1280×720) puis réduites par `smoothscale` à la
  taille de la fenêtre ; une fenêtre par défaut plus proche de cette résolution réduit
  nettement le facteur de réduction (donc le flou) sans toucher à la résolution logique
  elle-même (jugé trop risqué à changer globalement, cf. décision précédente).
  **Apps natives Inbox / Alertes (netteté).** Les écrans les plus consultés migrent
  progressivement de l'hébergement de scène (rendu 1280×720 réduit par `smoothscale` → flou,
  cf. `apps/scene_host.py`) vers de vraies apps du bureau dessinées à la résolution de leur
  fenêtre : `apps/app_inbox.py` (`InboxApp`, messagerie — `select_message(idx)` pour cibler un
  message depuis le centre de notifications/recherche globale) et `apps/app_alerts.py`
  (`AlertsApp`, alertes de prix — même logique `core/alerts` + verrou de grade « analyst » que
  la scène, `preselect(ticker)`). Enregistrées dans `APPS` (icônes du bureau, remplacent les
  accès rapides `qinbox`/`qalerts`) ; toute ouverture EN FENÊTRE des scènes `"inbox"`/`"alerts"`
  est redirigée vers l'app native par `DesktopScene._open_scene_window` (même principe que le
  Tableur) — les scènes plein écran restent enregistrées pour la navigation hors bureau.
  **Apps natives Marché / Portefeuille (netteté, suite).** Migration des deux plus gros écrans
  restants : `apps/app_markethub.py` (`MarketHubApp` — onglets Vue d'ensemble/Secteurs/
  Top-Flop/Heatmap/FX/Watchlist ; la plupart des méthodes `_draw_*` de la scène d'origine
  prenaient déjà un `rect` en paramètre, seule la disposition de haut niveau dépendait de
  `config.SCREEN_WIDTH`/`content_top()`/`footer_y()`) et `apps/app_book.py` (`BookApp` —
  table de positions toutes classes + barre de trading rapide + panneau latéral secteur/
  évolution, qui passe SOUS la table plutôt qu'à côté si la fenêtre est trop étroite pour 2
  colonnes). Les deux réutilisent `ui/popups.py::PopupMixin` pour les fiches d'analyse
  flottantes (société/ETF/obligation/matière première/crypto/structuré/crédit/graphe
  d'indice), avec `_popup_pos()` SURCHARGÉE pour ouvrir en cascade près de LA FENÊTRE plutôt
  qu'à une position fixe de l'écran entier (défaut de `PopupMixin`, pensé pour une scène
  plein écran). Enregistrées dans `APPS` avec les clés `"book"`/`"markethub"` (mêmes clés que
  les anciennes scènes, donc mêmes raccourcis Ctrl+P/Ctrl+M) ; les accès rapides
  `qbook`/`qmarket` de `QUICK_APPS` ont été retirés (doublon, même principe qu'Inbox/Alertes).
  **Bug corrigé au passage** : les quatre redirections vers apps natives (Inbox/Alertes/
  Portefeuille/Marché) retournaient tôt dans `_open_scene_window`, AVANT la ligne
  `self.start_open = False` du chemin générique d'hébergement de scène — ouvrir l'une de ces
  apps depuis le menu Démarrer laissait le menu ouvert par-dessus la fenêtre nouvellement
  ouverte (chaque bloc de redirection pose désormais `start_open = False` lui-même).
  **Étape 17 (polish V0) : un seul jeu de contrôles temps/pause.** La topbar du bureau
  (`DesktopScene._draw_topbar`) redessinait pause/vitesse/⚙ (`_pause_rect`/`_speed_rects`/
  `_gear_rect`) JUSTE en dessous du widget d'horloge de la bande d'onglets
  (`ui/simclock_widget.py`, dessiné par `core/pages.py`) — doublon visuel. Retiré : la topbar du
  bureau ne garde que Menu + horloge texte (Jour/heure/trimestre) + cash/patrimoine ; les
  contrôles pause/vitesse/⚙ vivent une seule fois dans la bande d'onglets, TOUJOURS visible
  au-dessus de toute scène pendant une partie (`PageManager._clock_visible()`). Par ailleurs, les
  périodes du graphe (`scenes/scene_graph.py::STEP_PERIODS` — 1M=6, 3M=18, 1A=73, 3A=219, 5A=365
  pas, MAX=None) ont été re-vérifiées : 1 pas de marché = `config.DAYS_PER_STEP` (5) jours, la
  préhistoire de carrière (`market_step = WARMUP_STEPS` = 365 pas au démarrage,
  `scenes/scene_runsetup.py`) garantit que toutes les périodes ont assez d'historique dès le jour 1
  (verrous : `tests/test_market_query.py::test_graph_step_periods_map_to_expected_horizons` et
  `test_history_available_from_career_start_for_all_graph_periods`).
  **Étape 18 (jouabilité/onboarding)** : (1) **tutoriel guidé du bureau**
  (`core/desktop_tutorial.py`, JSON par machine, distinct de `desktop_onboarding`) : 5 étapes
  validées sur l'ÉTAT du bureau (fenêtre ouverte, ancrage…), bandeau + halo pulsé sur l'icône
  cible, bouton « Passer », « Revoir le tutoriel » au menu contextuel ; démarre après la carte
  d'accueil. L'étape « Tapez ADV » du parcours terminal (`core/onboarding.py`) a été reformulée
  (commande supprimée depuis le temps continu). (2) **déblocage progressif des icônes du
  bureau** (`ICON_FEATURE` dans `scene_desktop.py` → `core/unlocks`) : Trading/Mandats/Deals
  n'apparaissent qu'au grade requis (icônes ET quick-launch), toast « Nouvelle app » à
  l'apparition (état vu dans `player.flags`). (3) **widget « À FAIRE »** (`core/todo.py`, pur) :
  actions en attente priorisées (dilemme, revue, stress test, marge, mandats, deals, inbox),
  lignes cliquables, dessiné au-dessus du widget patrimoine. (4) **carte « Bilan du
  trimestre »** : `advance_step` pose `flags['last_quarter_report']`, le bureau affiche une
  carte (objectifs, récompenses, attribution par source) acquittée par trimestre
  (`flags['quarter_report_ack']`). (5) **difficulté + Défi du jour** (`core/difficulty.py`) :
  presets Détendu/Normal/Exigeant (cash de départ, salaire, marge de maintenance — via
  `player.flags['difficulty']`, défaut normal donc saves antérieures inchangées) et graine de
  marché dérivée de la date (`daily_seed()`, marché partagé entre joueurs le même jour),
  choisis dans `scene_runsetup`. (6) **fil d'ordres du Trading** (`apps/app_trading.py`) :
  derniers ordres exécutés en bas de fenêtre, flash + son « order ». (7) **arcs narratifs**
  (`core/story_arcs.py` + `data/story_arcs.py`) : 3 histoires de 3 messages inbox étalées dans
  le temps (cadence déterministe sur le pas de marché, état dans `player.flags`), léger effet
  rep/cash au dénouement, livrées par `scene_terminal_time` ; à chaque déblocage de
  fonctionnalité, un mot du manager arrive aussi dans l'inbox (`scene_evaluation`).
  (8) **panthéon local** (`core/hall_of_fame.py`, JSON persistant entre parties comme
  `core/profile.py`) : chaque VRAI game over classe le run par score composite (top 10) ;
  rang + top 5 affichés dans `scene_gameover`. (9) **bouton CHEAT global** (mode test
  uniquement) : bande d'onglets, à gauche du bouton pause (`ui/simclock_widget.py`), ouvre le
  `CheatPanel` porté par l'app (`app.cheat_panel`) et dessiné/routé par `core/pages.py`
  par-dessus n'importe quelle scène (bureau compris).
  **Étape 19 (tutoriel approfondi)** : contenu dans `core/unlock_briefs.py` (pur, FR/EN).
  (1) **Guide de démarrage multi-pages** (6 pages : but du jeu, boucle
  missions→réputation→examen→promotion, temps/marché, outils du grade 0, poste de travail) :
  carte MODALE du bureau au tout début d'une carrière (`DesktopScene._intro_guide_active` —
  grade 0 et `day <= 3`, jamais en sandbox ni vétéran), état par SAUVEGARDE
  (`flags['intro_guide_done']`, pas par machine) ; « Guide de démarrage » au menu contextuel
  du fond pour le relire. Le refermer marque aussi `desktop_onboarding` vu (sa page 6 couvre
  la carte d'accueil machine). (2) **carte « NOUVEAU PÉRIMÈTRE » à chaque promotion** :
  `scene_evaluation._finish` calcule les fonctionnalités nouvellement débloquées par grade
  EFFECTIF (`unlock_briefs.newly_unlocked` — respecte le raccourci vétéran et les verrous de
  voie, remplace l'ancien test `grade == palier brut`) et pose
  `flags['pending_unlock_briefs']` ; le bureau affiche alors une fiche PAR fonctionnalité
  (ce que c'est / comment y accéder / ce que ça apporte / premiers pas — `FEATURE_BRIEFS`,
  une entrée par clé de `core/unlocks.UNLOCKS`, invariant gardé par
  `tests/test_desktop.py::test_every_unlockable_feature_has_a_brief`), navigable ←/→, avec
  bouton « Tuto détaillé » vers `scene_tutorials` quand `FEATURE_TUTORIAL` en a un.
  Priorité des cartes modales du bureau : bilan de trimestre → nouveautés → résumé d'absence
  (une seule à la fois) ; le guide, lui, passe au-dessus de tout et capture tous les
  évènements tant qu'il est affiché. (3) **auto-pause pendant les activités de carrière** :
  `DesktopScene._sync_auto_pause()` (appelé à chaque `update`) gèle l'horloge
  (`SimClock.set_auto_paused`) tant qu'une carte modale du bureau est affichée OU qu'une
  fenêtre hébergeant une scène « de travail » (`core/sim_clock.FOCUS_SCENE_NAMES` : mission,
  evaluation, dilemma, deal, review, stresstest, examcert, cert, tutorials) est ouverte NON
  minimisée — pas d'intérêts de levier, de crise ni de game over pendant un examen ; minimiser
  la fenêtre relance le temps (geste explicite « je mets ce travail de côté »). En plein
  écran, la même garantie vient déjà de `SceneManager.go` (auto-pause hors
  `LIVE_SCENE_NAMES`).
  **Étape 20 (netteté, suite) : Décision et Revue de performance en apps natives.**
  `apps/app_dilemma.py` (`DilemmaApp`) et `apps/app_review.py` (`ReviewApp`) migrent
  `scenes/scene_dilemma.py`/`scenes/scene_review.py` (popups FORCÉS par le jeu via
  `App.route_scene`, cf. étape 4) hors de l'hébergement flou — même principe que
  Portefeuille/Marché. Particularité par rapport aux autres apps natives : ces deux écrans
  sont RE-DÉCLENCHABLES pendant qu'une fenêtre déjà résolue traîne encore ouverte (un
  deuxième dilemme signature avant d'avoir fermé le premier) ; `DesktopScene._open_scene_window`
  ferme donc l'éventuelle fenêtre existante avant d'en relancer une fraîche plutôt que de
  garder un état "outcome" périmé affiché. Ces deux clés de fenêtre (`"dilemma"`/`"review"`,
  SANS préfixe `"scene:"` contrairement aux scènes encore hébergées) sont désormais
  reconnues par `DesktopScene._engaged_in_focus_work()` (auto-pause) ET par
  `App.route_scene`/`_open_scene_window(attention=True)` (clignotement de barre des tâches
  SANS voler le focus — la version précédente focalisait immédiatement la fenêtre pour
  book/markethub, ce qui aurait annulé le clignotement pour ces popups forcés).
- **`core/clipboard.py`** : lecture/écriture presse-papiers système best-effort
  (`pygame.scrap`), silencieux si le backend est indisponible (headless/CI, plateforme sans
  presse-papiers). `copy(text)` factorise l'ancien `scenes/scene_commands.py::_try_clipboard`
  (conservé comme fine façade de compat) ; `paste()` et `is_paste_shortcut(event)` (Ctrl+V/
  Cmd+V) sont le côté LECTURE, câblés dans la boîte « Importer un code » de
  `scenes/scene_gameover.py` (coller un code de défi partagé plutôt que le retaper caractère
  par caractère) et le chemin d'export/import de `scenes/scene_saves.py`.
- **`core/crashlog.py`** (lecture) + **`ui/crashlogpanel.py`** : visualiseur en jeu du journal
  de plantage (`crashlog.read()`/`clear()`, ajoutés au module déjà existant du filet de
  sécurité), overlay déplaçable/défilable (même pattern que `ui/shortcutspanel.py`) ouvert
  depuis un bouton « ⚠ Journal de plantage » de `scenes/scene_settings.py` — un joueur qui
  rencontre un comportement inattendu peut consulter/copier les tracebacks journalisés SANS
  accès au système de fichiers, pour les transmettre en rapport de bug.
- **`core/sim_clock.py`** : horloge de jeu temps réel (`SimClock`) — vitesse (x1/x2/x3),
  pause manuelle, pause automatique. Cadence : à x1, un jour de jeu dure ~16 s réelles
  (`GAME_MINUTES_PER_REAL_SECOND_AT_X1 = 90`), soit un nouveau pas de marché (5 jours) toutes
  les ~80 s (x1) / ~27 s (x3) ; entre deux pas, l'animation intraday fait bouger les graphes
  par petits paliers plusieurs fois par jour de jeu (cf. `core/intraday.QUANTIZE_MINUTES`),
  pas juste au changement de pas. (Réglage plus rapide, 120, jugé trop expéditif : le
  marché semblait figé malgré des jours qui filaient.)
  Le temps avance en continu (plus de commande « ADV ») :
  `App.run()` convertit le temps réel écoulé en pas de marché bancarisés
  (`App.pending_market_steps`), joués au terminal par `TerminalTimeMixin._drain_pending_steps()`
  (`scenes/scene_terminal_time.py`). `core/scene_manager.py::SceneManager.go()` met
  automatiquement l'horloge en pause (`auto_paused`) dès qu'on quitte la scène `"terminal"`
  (mission, examen, deal, dilemme…) et la reprend exactement au retour — aucune minute de jeu
  n'est comptée pendant l'absence. Widget de contrôle (⏸/▶/▶▶/▶▶▶) : `ui/simclock_widget.py`.
- **`core/market_hours.py`** : sessions de cotation par région (Asie/Europe/Amériques) au
  modèle **par pas de marché** (et non par heure de la journée, sinon ça clignote avec le
  temps accéléré) : à chaque pas, **2 sessions ouvertes / 1 fermée en rotation**
  (`closed_session(step)`), de sorte que chaque paire se croise une fois par cycle de 3 pas ;
  une place fermée rouvre toujours au pas suivant. `is_region_open(region, step)` /
  `is_session_open(session, step)` consommés par `BUY/SELL/SHORT/COVER`
  (`scenes/scene_terminal_trading.py`, refus si fermée), les pastilles A/E/M de la topbar,
  le gel intraday (`core/intraday.region_open_factor(region, step)`) et la commande `HOURS`.
- **`core/market.py`** : moteur de marché **déterministe** à modèle de facteurs
  `r_i = drift + beta·F_monde + b_secteur·F_secteur + b_region·F_region + sigma·bruit`.
  Les indices émergent de leurs constituants pondérés capi. Crises = chocs sur les facteurs.
  **L'état est reconstruit via (seed, nb de pas)** : le save ne stocke que
  `market_seed`/`market_step`, jamais les prix. Ne pas sérialiser les prix.
- **`core/intraday.py`** : animation intraday **déterministe et display-only** des prix,
  organisée autour d'un **CHEMIN DE PRIX CANONIQUE** : toutes les vues (fenêtres 1J/1W du
  graphe, point « en direct » des tickers/sparklines via `live_point`, densification des vues
  par pas via `densify_step_series`) échantillonnent LE MÊME chemin déterministe — comme dans
  une vraie app de trading, chaque période n'est qu'une fenêtre différente sur la même série.
  Convention **forward** : le pont du pas s va de close(s) vers close(s+1) (bruit fBm épinglé
  à 0 aux deux bornes, seedé par `(market_seed, s, clé)` — `canonical_point`/`close_at`) ;
  pendant le pas courant, le pont vers la clôture SUIVANTE (déterministe,
  `Market.next_step_snapshot()`/`next_price_of`/`next_index_value` — clone + un step, jeté,
  caché par pas, passé en `target`) se révèle au fil des minutes de jeu. Invariants garantis
  par construction et verrouillés par `tests/test_graph_canonical.py` : le 1J est exactement
  la QUEUE du 1W ; la courbe passe EXACTEMENT par chaque clôture du moteur (recoupe donc les
  vues 1M/3M/1A…) ; le dernier point de toute fenêtre == le point « en direct » du ticker ;
  un point du PASSÉ ne change JAMAIS quand le temps avance ni selon la vitesse de jeu
  (`speed_factor` déprécié → 1.0 : moduler le bruit par la vitesse réécrivait le passé).
  La progression dans le pas est **quantifiée par paliers** (`quantize_to_day()`,
  `QUANTIZE_MINUTES = 90`, ~1 rafraîchissement/s réelle à x1) : la fenêtre GLISSE sur le
  chemin figé, les points sortent par la gauche sans changer de valeur. Amplitude du bruit
  affiché (`_NOISE_PCT = 0.0035`, `_VOL_MULT_RANGE`) purement visuelle : ne touche jamais au
  prix d'exécution réel (`market.price`/`index_value`, inchangés). Deux mesures de variation :
  `window_pct(series, lookback=18)` = variation CUMULÉE « depuis la durée affichée » (~3 mois,
  ne repart PAS de 0 % à chaque pas — utilisée par les bandeaux d'indices du terminal et du
  hub Marché) ; `live_pct(series)` = variation vs la clôture du pas courant (repart de ~0 %,
  conservée pour compat). Bruit fBm multi-octave en surcouche. Aucun
  état persisté : reconstruit à partir de `(seed, step_count, clé, minute)`. `SimClock.game_minutes_acc`
  fournit la progression dans le pas courant. Branché via des paramètres optionnels
  `sim_clock=None, day=None` sur `core/market_query.py` (`index_history`, `track_company`,
  `history_of` — comportement inchangé si omis), consommé par les sparklines d'indices du
  terminal, le popup société (onglet graphe) et `scenes/scene_graph.py` (qui ajoute des
  fenêtres courtes animées 1J/1W, en plus des périodes par pas 1M/3M/1A/3A/5A/MAX — **3M par
  défaut** — pour les graphes mono-actif
  ligne/bougies/barres/variation). N'affecte jamais les prix d'exécution (`BUY/SELL/...`),
  qui restent sur `market.price[i]`. Amplitude de bruit modulée par la volatilité propre de
  chaque actif (`vol_mult_for_sigma(sigma, scale)`, basé sur `market.sigma`) ; les bougies
  intraday de `scene_graph.py` regroupent les points bruts en 18 bougies réelles (open/high/
  low/close) au lieu d'une bougie dégénérée par point. Le flash couleur vert/rouge sur tick
  (sparklines d'indices, popup société, app Watchlist, cellules `=PRICE()/INDEX()/FX()/...`
  du Tableur, cf. `apps/app_sheet._LIVE_FN_NAMES`) vit dans `ui/widgets.py::TickFlash` — reste
  à PLEINE saturation pendant `HOLD_MS` avant de s'éteindre sur `DECAY_MS` (horloge murale
  `pygame.time.get_ticks()`, pas de dépendance à `dt`), pour un tick bien visible plutôt
  qu'une simple teinte. `apps/app_trading.py::TradingApp._live_price` réutilise désormais ce
  même chemin (`market.history_of(tk, 1, sim_clock=..., day=...)`) pour la colonne COURS de la
  liste de valeurs — elle affichait jusqu'ici le cours STATIQUE du pas (`market.price_of`),
  figé entre deux pas de marché (~80 s réelles à x1) : rien ne semblait bouger à l'écran tant
  que le pas suivant n'arrivait pas. L'EXÉCUTION reste sur `market.price_of`/`fill_price`
  (inchangée, microstructure spread+impact) — seul l'AFFICHAGE devient vivant, cohérent avec
  le reste du jeu (marché fermé ⇒ pas de bruit, cf. `region_open_factor`).
  **Sélecteur de PÉRIODE sur la fiche société** (`scenes/scene_company.py`, onglet
  « GRAPHIQUE AVANCÉ ») : mêmes fenêtres que l'atelier de graphes (`PERIODS` — 1J/1W/1M/3M/1A/
  3A/5A/MAX, défaut 3M), via `scene_graph_common.stock_series` — logique de sélection de série
  factorisée entre `GraphScene._series` et la fiche société (deux calculs indépendants avaient
  déjà dérivé une fois, cf. audit V1.0) pour qu'ils montrent EXACTEMENT la même chose sur la
  même société. Les libellés d'axe X (`scene_graph_common.x_label_positions`, échelle
  adaptative minutes/heures/jours/dates/années) sont de même factorisés et réutilisés par les
  deux écrans.
- **`core/challenge_share.py`** : partage SANS SERVEUR d'un score de « Défi du jour »
  (`core/difficulty.py::daily_seed`) entre joueurs. `encode_entry`/`decode_entry` convertissent
  une entrée de panthéon (`core/hall_of_fame.py::make_entry`) en un code texte compact
  (`"FSC1:..."`, base64 d'un JSON compact + checksum CRC32) qu'un joueur copie/colle
  (Discord, SMS…) et qu'un AUTRE colle dans SON propre jeu — aucune inscription, aucun
  serveur. Le checksum détecte une faute de frappe/un copier-coller tronqué (pas une
  signature anti-triche : l'enjeu, un classement LOCAL entre amis, ne le justifie pas).
  `decode_entry` rejette un code non-`FSC1:`, corrompu, tronqué, ou dont l'entrée n'est PAS
  un run de défi du jour (`daily_date` absent — un run classique n'a pas vocation à être
  comparé). Les scores importés vivent dans un troisième fichier
  (`core/hall_of_fame.py::load_friends`/`hall_of_fame_friends.json`, séparé de
  `hall_of_fame_daily.json` qui ne contient QUE les runs réellement joués sur cette machine)
  via `import_friend_code` (dédoublonne un import répété du même code) ;
  `combined_daily_ranking(date)` fusionne runs locaux + scores d'amis en un seul classement
  trié (entrées d'amis taguées `"friend": True`). UI dans `scenes/scene_gameover.py` (visible
  uniquement pour un run de Défi du jour) : bouton « EXPORTER MON SCORE » (génère le code au
  clic, copie best-effort dans le presse-papiers système via
  `scene_commands._try_clipboard`, l'affiche aussi en clair pour copie manuelle) et
  « IMPORTER UN CODE » (boîte de saisie modale, même pattern que
  `scene_saves.py::path_prompt` — Échap annule la SAISIE sans quitter l'écran, contrairement
  au Échap habituel de cet écran qui renvoie au menu). **Retour social à l'import** :
  `GameOverScene._confirm_code_prompt` compare, quand CE run est lui-même un défi du jour
  (seul cas où le classement s'affiche), mon score (`self.score.total`, déjà calculé à
  `on_enter`) à celui de l'ami tout juste importé (`result["score"]`) et l'annonce dans le
  toast de confirmation (« Vous le devancez de N points ! » / « <Ami> vous devance de N
  points. » / égalité) — sans ça, « score ajouté au classement » laissait deviner qui est
  devant sans aller relire le tableau.
- **`core/anim_settings.py`** : réglage persisté « réduire les animations » (fichier JSON
  séparé sous `config.SAVE_DIR`, distinct de `core/i18n.py`/`settings.json`). Unique point de
  gating dans `core/intraday.py::wiggle()` : si actif, toutes les courbes intraday retombent
  en interpolation linéaire pure (sans bruit), sans toucher les sites d'appel. Bouton dans
  `scenes/scene_menu.py`.
- **`core/display_settings.py`** : mode d'affichage de la fenêtre (`windowed`/`fullscreen`/
  `borderless`), persisté (`display_settings.json` sous `config.SAVE_DIR`). Appliqué par
  `main.App._apply_window_mode()`/`set_window_mode()` : le plein écran utilise
  `pygame.FULLSCREEN|SCALED` (résolution LOGIQUE inchangée, mise à l'échelle du moniteur —
  net sur Retina/Mac), avec repli fenêtré si le driver refuse. F11 bascule rapide.
- **`core/audio.py`** : effets sonores **synthétisés** (numpy, sinus enveloppées : ordre
  exécuté, alerte de prix, cloche de session…) joués par `pygame.mixer`, **robuste headless**
  (no-op si le mixer ne s'initialise pas — CI, `SDL_AUDIODRIVER=dummy`). Volume maître + mute
  persistés (`audio_settings.json`, séparé). `audio.play(name)` est sûr partout.
- **`scenes/scene_settings.py`** (scène `"settings"`) : écran RÉGLAGES regroupant affichage,
  son (sourdine + volume), langue (FR/EN), animations et vitesse de jeu — façade de pilotage
  des modules ci-dessus. Accessible via l'icône ⚙ du terminal (coin haut-droit, dans
  l'espace réservé à droite des boutons d'horloge — cf. `ui/simclock_widget.GEAR_RESERVE`/
  `gear_rect()`), le bouton du menu, la commande `SETTINGS`/`REGLAGES`, ou la palette Ctrl+K.
  Le panneau des raccourcis clavier (`ui/shortcutspanel.py`) a migré ici (bouton dédié dans
  les réglages) ; il n'y a plus de bouton ⌨ dans la barre du terminal. Espace = pause/reprise
  (ligne de commande vide).
- **`scenes/scene_saves.py`** (scène `"saves"`, commande `SAVES`/`LOAD`) : gestion des slots de
  sauvegarde (autosave + `config.SAVE_SLOTS`) — charger/enregistrer/supprimer, ET **exporter/
  importer en fichier portable** (boutons EXPORTER par slot, IMPORTER en haut de l'écran) : un
  chemin arbitraire (pas forcément `config.SAVE_DIR`), pour transporter une partie d'une machine
  à l'autre à la main (clé USB, cloud perso…) sans dépendre d'un service tiers.
  `GameState.export_to(path)`/`GameState.import_from(path)` (`core/game_state.py`) réutilisent le
  même format JSON que `save()`/`load()`, mais à un chemin choisi par le joueur (saisi via une
  boîte de dialogue texte, `self.path_prompt`/`self.path_buf`, même pattern que les champs de
  saisie du reste du jeu) — `export_to` fonctionne même en mode sandbox (contrairement à `save()`,
  no-op en sandbox) car c'est une action explicite du joueur, pas un point de sauvegarde
  automatique. Un import réussi remplace `app.gs` et ramène au bureau, comme un chargement de
  slot classique.
- **`scenes/scene_achievements.py`** (scène `"achievements"`, commande `ACHIEVEMENTS`/`SUCCES`/
  `BADGES`) : écran dédié listant TOUS les badges (`core/badges.py::all_badges()` +
  `all_streak_badges()`), obtenus en couleur (`✓`), VERROUILLÉS grisés (`·`) avec une jauge de
  progression (`widgets.draw_progress`) pour les badges à seuil NUMÉRIQUE clair — distinct de la
  galerie inline de `scene_career.py` (bouton « SUCCÈS → »), qui ne montre que les badges déjà
  obtenus, sans vue d'ensemble de ce qu'il reste à débloquer. La jauge vient d'une clé optionnelle
  `"progress": callable(player, market) -> (actuel, cible)` ajoutée à certaines entrées de
  `BADGES` (résolue sans jamais lever via `badges.progress_for`, absente pour les badges
  binaires/composites comme « avoir un titre » ou « être n°1 » où une jauge n'aurait pas de
  sens) ; les badges à enjeu (`STREAK_BADGES`) réutilisent directement leur `streak_flag`/`target`
  existants comme progression. Accessible aussi depuis le hub PLUS (« Succès (badges) »).
- **`data/companies.py`** : roster fictif déterministe (320 sociétés, `ROSTER_SEED` fixe,
  noms déformés exprès : LVMH→LWNH, NVIDIA→MVC…).
- **`core/`** : systèmes de jeu (career, portfolio, bonds, commodities, crypto, structured,
  securitisation, risk/VaR, alm, missions, exam, certifications, dilemmas, inbox, rivals,
  scenarios, mandates, deals, tracks, unlocks, financials, history…).
- **`scenes/`** : un écran par fichier (`scene_*.py`). **`scenes/scene_terminal.py`** est le
  hub central (rail latéral, carte monde, console de commandes). **`scenes/scene_more.py`**
  (hub PLUS) doit exposer un **bouton** vers chaque scène jouable — invariant gardé par
  `tests/test_more_buttons.py` (seules les scènes de flux menu/intro/gameover… et les vues de
  détail contextuelles ma_target/deal sont exclues). Taux FX visibles en permanence dans le
  ticker du terminal et dans l'onglet « FX / Devises » du hub Marché (`scene_markethub.py`).
- **`ui/`** : widgets (worldmap, globe, datawindow, calculator, notifications…).
- **`data/`** : contenu (companies, lessons, glossary, question_bank, worldmap_geo).

## Conventions

- **Déterminisme** : tout aléa du marché passe par le rng seedé ; ne pas introduire de
  hasard non reproductible. Ajouter un tirage rng dans `step()` décale les saves existants
  (acceptable mais à signaler).
- **i18n** : le *chrome* UI est bilingue FR/EN (`core/i18n.py`, `t()`), le **contenu finance
  profond reste FR** par défaut (glossaire/leçons/examens ont une couche EN dédiée :
  `*_en.py`, `exam._L(fr,en)`).
- **`.gitignore`** exclut `saves/`, `__pycache__/`, `.idea/`, `.DS_Store`, `dist/`, `build/`,
  `.venv/`, `.claude/settings.local.json`. Ne pas committer de fichiers générés ni de saves.
- Commits co-signés `Co-Authored-By: Claude`. Pousser uniquement quand demandé.
