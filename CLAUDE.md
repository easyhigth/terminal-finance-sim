# CLAUDE.md

Instructions projet pour Claude Code (local **et** cloud). Le jeu est un simulateur de
carrière en finance de marché, écrit en Python + pygame. Langue de travail : **français**.

> La CHRONOLOGIE des refontes (étapes du bureau, lots de contenu, bugs historiques et
> leur contexte) vit dans `docs/HISTORY.md` — à consulter avant de revenir sur une
> décision d'architecture. Ce fichier-ci ne garde que ce qu'il faut savoir POUR AGIR :
> commandes, architecture actuelle, conventions et pièges actifs.

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
ruff check .                           # lint (mêmes règles que la CI)
```

- Suite pytest dans `tests/` (~200 fichiers). Couvre la logique pure (finmath, market,
  portfolio, exam, desks…) ET le runtime des scènes/apps en headless.
- `tests/test_scene_smoke.py` visite **chaque** scène enregistrée dans `main.py::App` via
  `on_enter()`/`update()`/`draw()`. **Angle mort connu** : marché fraîchement créé (1-2
  points d'historique) → n'exerce jamais le rendu des graphes avec un historique réel ;
  `tests/test_terminal_desktop_fuzz.py` couvre ce cas (marché avancé de 40 pas + fuzz).
- `tests/test_facade_exports.py` verrouille par ANALYSE AST que toute expression
  `widgets.<x>` / `pf.<x>` présente dans le code résout sur le vrai module : `ui/widgets.py`
  et `core/portfolio.py` RÉEXPORTENT des helpers (`ui/chart_widgets.py`,
  `core/portfolio_margin.py`, `core/portfolio_views.py`) — un symbole oublié de la liste de
  réexport plante à l'exécution, pas à la compilation.
- `tests/test_save_compat.py` + `tests/fixtures/save_v0_*.json` : des sauvegardes
  d'ANCIENNES versions committées en fixtures, chargées et jouées quelques pas. **On
  n'édite JAMAIS une fixture pour faire passer un test** — si le format casse, c'est le
  chargement (`GameState.from_dict` ou une migration à la `alerts._ensure_lists`) qui doit
  devenir tolérant. Un nouveau format = une NOUVELLE fixture.
- `tests/test_step_hooks.py` verrouille l'ORDRE du registre de pas (cf. Architecture).
- CI : `.github/workflows/tests.yml` (pytest headless + ruff).

## Vérification d'une modif

1. Syntaxe : `python -m py_compile main.py core/*.py ui/*.py scenes/*.py apps/*.py data/*.py`
2. Lint : `ruff check .`
3. Logique pure (`core/`) : testable directement, ajouter/lancer les tests pytest.
4. Runtime des scènes (si modif d'une scène/widget) : harnais headless avec
   `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` → instancier `main.App()`, faire
   `app.scenes.go(name)` puis `update()/draw()` sur chaque scène pour attraper les erreurs
   de rendu (AttributeError, draw) que `py_compile` ne voit pas.

## Architecture actuelle

- **`main.py`** : `App` (boucle pygame, enregistrement des scènes, `ensure_market()`,
  `sim_clock`/`pending_market_steps`, `route_scene()` pour les navigations FORCÉES par le
  jeu). `core/scene_manager.py` gère la pile de scènes + toasts + palette Ctrl+K.
- **Le BUREAU est l'écran maître** (`scenes/scene_desktop.py`, scène `"desktop"`) : icônes
  en sections repliables, barre des tâches, menu Démarrer, fenêtres gérées par
  `ui/window_manager.py` (z-order, focus, ancrage aux bords, maximisation, Alt+Tab). Toute
  nouvelle partie / chargement / CONTINUER atterrit sur `"desktop"`. Seules les scènes de
  flux pré/post-partie (`_FULLSCREEN_EXIT` : menu, gameover, intro, continent, runsetup,
  sandbox, splash) basculent réellement en plein écran.
- **Le TERMINAL est le moteur de la boucle de jeu**, hébergé dans une fenêtre persistante
  (`DesktopScene._terminal_host`) : fermer/minimiser sa fenêtre n'arrête jamais le temps ;
  les pas de marché bancarisés sont joués par `TerminalTimeMixin._drain_pending_steps()`
  (`scenes/scene_terminal_time.py`).
- **`apps/`** : les applications du bureau. Deux familles :
  - **apps natives** (héritent de `apps/base.DesktopApp`, dessinent à la résolution de leur
    fenêtre — nettes) : trading, book, markethub, sheet (classeur `app.workbook`), inbox,
    alerts, research, watchlist, mission, evaluation, dilemma, review, deals, journal,
    company, shop, analytics, explorer, tous les desks quant/crédit/taux…
  - **`apps/scene_host.py`** (`SceneHostApp`) : héberge une scène plein écran dans une
    fenêtre (rendu offscreen 1280×720 réduit par smoothscale — flou, d'où la migration
    progressive vers des apps natives). La navigation interne d'une scène hébergée passe
    par un App-proxy (`_Router`) qui route `scenes.go()` vers l'ouverture d'une fenêtre.
- **`core/`** : logique pure, sans pygame (market, portfolio et toutes ses classes d'actifs,
  career, missions, exam, unlocks, desks quant/crédit/taux, step_hooks…).
- **`core/step_hooks.py`** : registre ORDONNÉ des systèmes joués à chaque pas de marché
  (dividendes/coupons/portage, financement, dérivés, ordres automatiques, marge, limites
  VaR, échéances). `GameState.advance_step` ne fait plus qu'orchestrer. **Ajouter un
  instrument = écrire un hook + l'insérer à la bonne place dans `STEP_HOOKS`**, jamais un
  bloc dans `game_state.py`. L'ordre est un invariant de gameplay (ordres conditionnels
  AVANT contrôle de marge ; `net_worth` APRÈS tous les règlements) testé par
  `tests/test_step_hooks.py`.
- **`core/market.py`** : moteur **déterministe** à modèle de facteurs ; les indices émergent
  des constituants pondérés capi ; crises = chocs sur les facteurs. **L'état se reconstruit
  via (seed, nb de pas)** : le save ne stocke que `market_seed`/`market_step`, JAMAIS les
  prix. `core/intraday.py` : animation display-only sur un chemin canonique déterministe —
  ne touche jamais aux prix d'exécution (`market.price_of`/`fill_price`).
- **`core/sim_clock.py`** : temps continu (x1/x2/x3, pause), auto-pause hors scènes live et
  pendant les activités de carrière (`FOCUS_SCENE_NAMES`). Un seul jeu de contrôles
  pause/vitesse, dans la bande d'onglets (`core/pages.py` + `ui/simclock_widget.py`).
- **`scenes/`** : un écran par fichier. `scenes/scene_more.py` (hub PLUS) doit exposer un
  bouton vers chaque scène jouable — invariant gardé par `tests/test_more_buttons.py`.
- **`ui/`** : widgets purs pygame. `ui/fonts.py` porte le **cache de rendu texte**
  (`render_cached`) utilisé par `widgets.draw_text*`.
- **`data/`** : contenu (roster déterministe de 320 sociétés — noms déformés exprès :
  LVMH→LWNH, NVIDIA→MVC —, leçons, glossaire, banques de questions, mirrors `*_en.py`).

## Conventions

- **Déterminisme** : tout aléa du marché passe par le rng seedé ; ne jamais introduire de
  hasard non reproductible. Un nouveau système avec son propre aléa dérive sa graine de
  `(market.seed, index)` avec un rng DÉDIÉ qui ne consomme jamais le rng du marché (sinon
  les saves existants dérivent). Ajouter un tirage dans `step()` décale les saves
  (acceptable mais à signaler).
- **Sauvegardes** : format JSON tolérant (`from_dict` : champ absent → défaut). Un nouveau
  champ de `PlayerState` est auto-sérialisé (dataclass). Si un SCHÉMA interne change
  (ex. les alertes), écrire une migration au point d'entrée du module concerné.
- **`except Exception` best-effort** : jamais un `pass` nu — appeler
  `core.crashlog.swallowed("module.contexte")` (trace en mode FINSIM_DEBUG, ne lève
  jamais, n'écrit pas dans crash.log). Le filet de la boucle principale reste
  `main.py::App._safe_call` + `core/crashlog.record` (crash.log borné à 20 entrées).
- **i18n** : le *chrome* UI est bilingue FR/EN (`core/i18n.py`, `t()`), le **contenu
  finance profond reste FR** (couche EN dédiée : `*_en.py`, `exam._L(fr,en)`).
- **Icônes/glyphes** : JAMAIS d'emoji dans l'UI (pas de couverture emoji dans les polices
  embarquées JetBrains Mono/Inter) — tout pictogramme est dessiné en VECTORIEL
  (`ui/desktop_icons.py`, chevrons, boutons pause/vitesse).
- **Cache de rendu texte** (`ui/fonts.render_cached`) : les Surfaces retournées sont
  PARTAGÉES — à blitter uniquement, jamais muter (`set_alpha`, `fill`…).
- **Raccourcis** : Ctrl+C/V/Z/Y réservés aux conventions copier/coller/annuler ; Ctrl+K =
  palette de navigation (contenu de référence) ; Ctrl+/ = recherche globale (données de la
  partie) ; les raccourcis d'apps du bureau évitent ces lettres.
- **`.gitignore`** exclut `saves/`, `__pycache__/`, `.idea/`, `.DS_Store`, `dist/`,
  `build/`, `.venv/`, `.claude/settings.local.json`. Ne pas committer de fichiers générés.
- Commits co-signés `Co-Authored-By: Claude`. Pousser uniquement quand demandé.

## Pièges actifs (appris à la dure — détail dans docs/HISTORY.md)

- **Apps du bureau** : ajouter une clé à `APPS` crée AUSSI une icône permanente via
  `_icon_list()` — les écrans à ouverture contrôlée (dilemma, review, evaluation, deals,
  company, shop, explorer, analytics…) doivent rester dans
  `DesktopScene._FACTORY_ONLY_APPS` (une icône « Évaluation » cliquable contournerait les
  critères de promotion). Le quick-launch de la barre des tâches exclut aussi cet ensemble.
  Verrouillé par `tests/test_desktop.py`.
- **Règles de ré-ouverture des fenêtres** : Mission/Évaluation EN COURS retrouvent leur
  fenêtre (jamais de perte de progression), un état TERMINÉ est relancé frais ;
  Company/Shop/Explorer reçoivent `configure(**kwargs)` à CHAQUE ouverture (remplace le
  contenu). `configure()` absorbe les kwargs hérités via `**_kwargs` (jamais de TypeError).
- **Navigation depuis une app native** : `self.app` y est le VRAI App global (pas le proxy
  `_Router` des scènes hébergées) — `app.scenes.go(...)` basculerait TOUT l'écran hors du
  bureau. Toujours router par la back-ref `desktop._open_scene_window(...)` /
  `desktop.open_trading(...)` (cf. `ui/popups.py::PopupMixin._consume_popup_signals`).
- **Clics et fenêtres** : `WindowManager.handle_event` renvoie TOUJOURS True pour un clic
  dans les limites d'une fenêtre (jamais de fallthrough vers le bureau derrière).
- **Constantes `MIN_GRADE` dédoublées** : `core/ipo.py`, `core/macrocal.py`,
  `core/mandates.py` portent leur propre `MIN_GRADE`, à resynchroniser À LA MAIN avec
  `core/unlocks.UNLOCKS` à chaque changement de palier — sinon l'UI montre débloqué ce que
  le module refuse encore.
- **Dict literals de contenu** (`data/glossary_data.py`…) : une clé dupliquée garde
  SILENCIEUSEMENT la dernière occurrence — vérifier avant d'ajouter un terme (tests
  d'intégrité).
- **Avant d'ajouter une fonctionnalité « manquante » à un module** : `grep -n "^def "` le
  fichier ENTIER — plusieurs systèmes ont failli être réimplémentés (ex. `rivals.step`
  vs `rivals.step_trading` plus bas dans le même fichier).
- **Capitalisations en MILLIONS** : `metrics()['mktcap']` est en millions — tout seuil
  absolu doit l'être aussi (bug historique des tiers de liquidité).
- **Grilles d'icônes en ordre LIGNE** (`row, col = divmod(i, cols)`) : un ordre colonne
  hérité par copier-coller a déjà fait déborder des icônes sous la barre des tâches.
- **`PYGAME_FORCE_SCALE=photo`** (netteté plein écran) est posé par `main.py` mais
  DÉSACTIVÉ sous `SDL_VIDEODRIVER=dummy` (le driver factice échoue sur `set_mode` avec).
- **Briefs de déblocage** : toute nouvelle clé dans `core/unlocks.UNLOCKS` exige une entrée
  `FEATURE_BRIEFS` (`core/unlock_briefs.py`) — invariant testé — et, si voie-exclusive, une
  entrée `TRACK_AFFINITY` avec sa PROPRE clé (jamais une clé partagée comme `"trade"`).
- **Découvrabilité** : `DesktopScene._launch`/`_open_scene_window` notent chaque app
  ouverte dans le profil machine (`core/profile.record_app_opened`) —
  `profile.apps_never_opened(...)` sert au diagnostic « quelles apps personne ne trouve ».
