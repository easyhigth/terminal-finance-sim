# Plan : implémentation des 10 améliorations priorisées

## Contexte
Suite à l'audit du codebase, 10 axes d'amélioration ont été identifiés et validés par le joueur. Ce plan découpe le travail en phases indépendantes, testables et poussables séparément.

---

## Phase 1 — Toasts actionnables + feedback sonore (court terme, gros impact)

### 1.1 Toasts actionnables pour alertes de prix et ordres conditionnels
- **Fichiers** : `core/alerts.py`, `core/conditional_orders.py`, `ui/notifications.py`, `scenes/scene_desktop.py`, `scenes/scene_terminal_time.py`
- **Travail** :
  - Étendre `NotificationCenter.push()` avec `action="trading"` + `action_kwargs={"ticker": ...}` et un handler de clic qui appelle `DesktopScene.open_trading(ticker)`.
  - Dans `alerts.check()` et `conditional_orders.execute_due()`, produire des notifications toast au lieu de simples messages inbox/log.
  - Câbler `scene_terminal_time.py` (où `advance_step` appelle `execute_due`) pour pousser les toasts vers `app.notes`.
  - Dessiner les toasts avec un bouton/action cliquable (tout le toast ou une zone "Trader →").

### 1.2 Feedback sonore contextuel
- **Fichiers** : `ui/window_manager.py`, `apps/app_sheet.py`, `apps/app_trading.py`, `scenes/scene_terminal_time.py`, `apps/app_calculator.py`
- **Travail** :
  - `audio.play("snap")` sur ancrage/maximisation de fenêtre.
  - `audio.play("message")` sur nouvel inbox.
  - `audio.play("conditional")` sur ordre conditionnel exécuté.
  - `audio.play("milestone")` sur bilan trimestriel.
  - `audio.play("click")` sur export CSV, copier/coller, ajout watchlist.

---

## Phase 2 — Performance du bureau (moyen terme)

### 2.1 Skip update/draw sur fenêtres cachées ou minimisées
- **Fichiers** : `ui/window_manager.py`, `apps/scene_host.py`
- **Travail** :
  - Ajouter `Window.is_visible()` et `Window.is_occluded()`.
  - Dans `WindowManager.update()`, appeler `update` seulement sur les fenêtres visibles/non minimisées ; throttle à 500 ms pour les fenêtres partiellement cachées.
  - Dans `WindowManager.draw()`, sauter le draw des fenêtres entièrement couvertes (sauf si c'est la fenêtre active/focus).

### 2.2 Réduction du smoothscale dans SceneHostApp
- **Fichiers** : `apps/scene_host.py`, `ui/window_manager.py`
- **Travail** :
  - Cacher la surface `scaled` dans `SceneHostApp` ; ne rescale que si `rect.size` a changé.

### 2.3 Cache des overlays plein-écran
- **Fichiers** : `scenes/scene_desktop_widgets.py`, `scenes/scene_desktop_menus.py`
- **Travail** :
  - Ajouter `self._overlay_surf` et `self._overlay_size` ; recréer la surface SRCALPHA seulement si la taille change.
  - Appliquer cette logique aux cartes modales (guide, bilan trimestre, nouveautés) et aux menus contextuels/recherche.

---

## Phase 3 — Sauvegarde de l'état UI (qualité de vie)

### 3.1 Persister la disposition du bureau + classeur + watchlist
- **Fichiers** : `core/ui_state.py` (nouveau), `ui/window_manager.py`, `core/pages.py`, `core/workbook.py`, `core/game_state.py`, `scenes/scene_saves.py`
- **Travail** :
  - Créer `core/ui_state.py` : charge/sauvegarde JSON `ui_state.json` dans `SAVE_DIR`.
  - Sauvegarder les rectangles des fenêtres (`WindowManager.save_layout()`), l'état `PageManager` (onglets), le workbook actif (feuilles + formules), la watchlist.
  - Restaurer au chargement de sauvegarde : `GameState` appelle `ui_state.load()` après `load()`.
  - Ne pas écraser l'UI d'une sandbox / nouvelle partie.

---

## Phase 4 — Accessibilité et onboarding

### 4.1 Mode "pause sur événements majeurs"
- **Fichiers** : `core/sim_clock.py`, `core/market.py`, `core/scenarios.py` (crises), `scenes/scene_desktop.py`, `scenes/scene_settings.py`
- **Travail** :
  - Ajouter un flag `auto_pause_on_events` dans `core/sim_clock.py` ou un setting dédié.
  - Détecter les événements majeurs (crise, margin_call, earnings surprise, dilemme forcé) dans `GameState.advance_step`.
  - Appeler `sim_clock.set_auto_paused(True)` + toaster explicatif si l'option est active.
  - Option dans `scene_settings.py`.

### 4.2 Aide contextuelle F1 par app native
- **Fichiers** : `apps/base.py`, `apps/app_trading.py`, `apps/app_sheet.py`, `apps/app_research.py`, `ui/shortcutspanel.py`
- **Travail** :
  - Ajouter `DesktopApp.help_shortcuts()` retournant une liste de `(raccourci, description)`.
  - Implémenter pour Trading, Sheet, Research, Watchlist, Calculator.
  - Overlay léger dans `WindowManager.handle_event` sur F1 : dessiner un panneau translucide avec les raccourcis de l'app focalisée.

---

## Phase 5 — Qualité / robustesse

### 5.1 Tests headless des apps natives
- **Fichiers** : `tests/test_app_trading.py`, `tests/test_app_sheet.py`, `tests/test_app_research.py`, `tests/test_app_watchlist.py`
- **Travail** :
  - Instancier `main.App()`, atterrir sur `desktop`, ouvrir chaque app via `DesktopScene._launch()`.
  - Simuler des événements pygame (clic, clavier) et vérifier l'état (ex. ajout à la watchlist, ordre, formule).
  - Vérifier le routage des événements et l'absence d'exceptions.

### 5.2 Unification des settings persistants
- **Fichiers** : `core/settings_registry.py` (nouveau), `core/audio.py`, `core/anim_settings.py`, `core/display_settings.py`, `core/colorblind_settings.py`, `core/autosave_settings.py`, `scenes/scene_settings.py`
- **Travail** :
  - Créer `SettingsRegistry` avec API `register(key, default, type, path)` + `get/set`.
  - Migrer les 5 modules de settings existants pour utiliser le registre (compatibilité ascendante des fichiers JSON).
  - Nettoyer les helpers `_load/_save` dupliqués.

---

## Ordre de réalisation recommandé

1. Phase 1.1 + 1.2 (impact immédiat, fichiers peu nombreux)
2. Phase 2.1 + 2.3 (performance, petites surfaces)
3. Phase 2.2 (SceneHostApp cache)
4. Phase 3 (sauvegarde UI)
5. Phase 4.1 (pause événements)
6. Phase 4.2 (aide F1)
7. Phase 5.1 (tests apps)
8. Phase 5.2 (settings registry)

Chaque phase fait l'objet d'un commit co-signé et d'un push séparé.

---

## Critères d'acceptation globaux

- `python -m py_compile main.py main_cheat.py core/*.py ui/*.py scenes/*.py data/*.py apps/*.py` passe.
- `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest -q` passe à 0 échec après chaque phase.
- `tests/test_scene_smoke.py` passe.
- Les nouvelles fonctionnalités sont couvertes par des tests quand c'est pertinent.
