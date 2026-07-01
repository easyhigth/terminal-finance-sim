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
  scène `scene_spreadsheet.py` (avec son propre `app.sheet`, distinct de `app.workbook`) reste
  inchangée et n'est plus utilisée QUE hors bureau (terminal classique).
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
  **Étape 12 : découvrabilité (accueil + menus contextuels).** (1) **Carte d'accueil** du bureau
  à la 1re visite (`DesktopScene._draw_onboarding`) : mode d'emploi rapide (icônes = apps en
  fenêtres, ancrage/maximisation, Alt+Tab, le terminal reste le moteur, clic droit, widget
  patrimoine). NON modale — un clic sur « Commencer » (ou ailleurs) la referme ; l'état « vue »
  est persisté à part (`core/desktop_onboarding.py`, JSON dédié — distinct de `core/onboarding.py`
  qui est le parcours guidé du TERMINAL). L'action « Revoir l'accueil » du menu contextuel du
  fond appelle `desktop_onboarding.reset()`. (2) **Menus contextuels (clic droit)**
  (`_open_context_menu`/`_handle_ctx_event`/`_draw_context_menu`, état `self._ctx_menu`) selon la
  cible sous le curseur : icône du bureau (Ouvrir / Ouvrir puis ancrer à gauche·droite), barre de
  titre OU entrée de barre des tâches d'une fenêtre (Réduire/Restaurer, Agrandir/Restaurer,
  Ancrer gauche·droite, Fermer), fond du bureau (Menu Applications, Réglages, Fermer toutes les
  fenêtres, Revoir l'accueil). L'ancrage réutilise la logique de l'étape 10 (`_snap_window` pose
  `_restore_rect`) ; « Fermer toutes les fenêtres » ne fait que MINIMISER le terminal (jamais
  arrêter le moteur). Le menu se referme au clic sur un item (exécute son action), à tout clic
  hors menu, ou sur Échap ; un clic droit sur le CONTENU d'une fenêtre reste routé vers l'app.
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
  **forward-looking** : la courbe simule le chemin de la clôture COURANTE vers la clôture du
  **prochain pas** (déterministe, `Market.next_step_snapshot()`/`next_price_of`/`next_index_value`
  — clone + un step, jeté, caché par pas), passé en `target` à `live_point`/`append_live`.
  La progression dans le pas est **quantifiée par paliers** (`quantize_to_day()`,
  `QUANTIZE_MINUTES = 360`, soit 4 rafraîchissements par jour de jeu — ≈4 s réelles à x1) :
  la valeur animée se met à jour par petits sauts vers la destination du prochain pas, plus
  réactif qu'un unique saut par jour tout en restant lisible (pas un glissement continu à
  chaque frame). Amplitude du bruit affiché (`_NOISE_PCT`, `_VOL_MULT_RANGE`) relevée pour
  que le marché semble vivant à l'écran entre deux pas, sans jamais toucher au prix
  d'exécution réel (`market.price`/`index_value`, inchangés). Deux mesures de variation :
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
  qu'une simple teinte.
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
