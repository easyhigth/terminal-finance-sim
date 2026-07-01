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
  Étapes suivantes prévues : migrer toutes les scènes en fenêtres, promouvoir le bureau en
  écran principal. Le terminal classique reste accessible (icône « Terminal »).
- **`core/sim_clock.py`** : horloge de jeu temps réel (`SimClock`) — vitesse (x1/x2/x3),
  pause manuelle, pause automatique. Cadence : à x1, **1 minute réelle = 1 pas de marché**
  (`GAME_MINUTES_PER_REAL_SECOND_AT_X1 = 120`), soit un nouveau pas toutes les ~60 s (x1) /
  ~20 s (x3) ; entre deux pas, l'animation intraday fait glisser les graphes en continu.
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
  La progression dans le pas est **quantifiée au JOUR de jeu** (`quantize_to_day()`,
  paliers de 1440 min) : la valeur animée ne se met à jour qu'une fois par jour de jeu
  écoulé (≈12 s réelles à x1), par paliers vers la destination du prochain pas, au lieu de
  glisser en continu à chaque frame (trop rapide/illisible). Deux mesures de variation :
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
  (sparklines d'indices, popup société) vit dans `ui/widgets.py::TickFlash` (horloge murale
  `pygame.time.get_ticks()`, pas de dépendance à `dt`).
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
