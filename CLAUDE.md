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
- **`core/sim_clock.py`** : horloge de jeu temps réel (`SimClock`) — vitesse (x1/x2/x3),
  pause manuelle, pause automatique. Le temps avance en continu (plus de commande « ADV ») :
  `App.run()` convertit le temps réel écoulé en pas de marché bancarisés
  (`App.pending_market_steps`), joués au terminal par `TerminalTimeMixin._drain_pending_steps()`
  (`scenes/scene_terminal_time.py`). `core/scene_manager.py::SceneManager.go()` met
  automatiquement l'horloge en pause (`auto_paused`) dès qu'on quitte la scène `"terminal"`
  (mission, examen, deal, dilemme…) et la reprend exactement au retour — aucune minute de jeu
  n'est comptée pendant l'absence. Widget de contrôle (⏸/▶/▶▶/▶▶▶) : `ui/simclock_widget.py`.
- **`core/market_hours.py`** : calendrier des sessions de cotation par région (Asie/Europe/
  Amériques, lundi-vendredi, plages horaires partiellement chevauchantes — jamais les 3
  ouvertes en même temps). `SimClock.current_time(player.day)` donne le (jour, minute du
  jour) courant ; `BUY/SELL/SHORT/COVER` (`scenes/scene_terminal_trading.py`) refusent le
  trade actions hors session avec l'heure de réouverture ; commande `HOURS` au terminal pour
  consulter le statut des 3 sessions.
- **`core/market.py`** : moteur de marché **déterministe** à modèle de facteurs
  `r_i = drift + beta·F_monde + b_secteur·F_secteur + b_region·F_region + sigma·bruit`.
  Les indices émergent de leurs constituants pondérés capi. Crises = chocs sur les facteurs.
  **L'état est reconstruit via (seed, nb de pas)** : le save ne stocke que
  `market_seed`/`market_step`, jamais les prix. Ne pas sérialiser les prix.
- **`core/intraday.py`** : animation intraday **déterministe et display-only** des prix
  (pont brownien pinné aux bornes du pas via bruit fBm multi-octave). Aucun état persisté :
  reconstruit à partir de `(seed, step_count, clé, minute)`. `SimClock.game_minutes_acc`
  fournit la progression dans le pas courant. Branché via des paramètres optionnels
  `sim_clock=None, day=None` sur `core/market_query.py` (`index_history`, `track_company`,
  `history_of` — comportement inchangé si omis), consommé par les sparklines d'indices du
  terminal, le popup société (onglet graphe) et `scenes/scene_graph.py` (qui ajoute des
  fenêtres intraday 5M/10M/30M/1H/2H, en plus de 1A/3A/5A/MAX, pour les graphes mono-actif
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
