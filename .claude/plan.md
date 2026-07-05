# Plan — Simulation de marché poussée et graphes vivants

## Objectif
Transformer le moteur de marché existant (déjà à facteurs, crises, earnings, macro) en une simulation **financièrement crédible et visuellement lisible** :
- des entreprises avec un passé fondamental et des événements narratifs qui **impactent réellement** les cours ;
- des graphes qui **montrent** ces événements, les anticipations et les chocs ;
- un « forward » interne (consensus, révisions, scénarios) qui guide l’évolution future et se reflète dans les courbes.

Le tout reste **déterministe** (seed + pas) et couvert par des tests.

---

## Phase 1 — Événements d’entreprise et annotations sur les graphes (2-3 sprints)

### 1.1 Moteur d’événements d’entreprise (`core/market_events.py`)
Créer un nouveau module pur qui tire, à chaque pas, des événements **par société** :
- **Opérationnels** : lancement de produit, contrat gagné/perdu, rappel sanitaire, cyberattaque, grève, panne d’usine.
- **Corporate** : changement de CEO, scandale comptable, OPA amicale/hostile, buyback, augmentation de capital.
- **Externes** : perte/gain de commande publique, décision judiciaire, sanction régulatoire ciblée.

Chaque événement a :
- un ticker cible,
- un type et une sévérité (-8 % à +8 % environ, calibré par capitalisation),
- une durée d’impact (choc immédiat + drift résiduel sur 2-8 pas),
- une **narration** (FR/EN via `data/market_events_en.py`).

Intégration dans `Market.step()` :
- consommer un tirage rng déterministe par société à chaque pas (probabilité très faible, ~1-3 %/an par société),
- appliquer le choc de cours dans le rendement du pas sous la forme `event_shock[i]`,
- stocker `self.company_events_log[ticker]` pour l’UI et les graphes.

### 1.2 Annotation des graphes
Modifier `draw_series()` / `GraphRenderMixin` / `scene_company.py` pour afficher :
- des **pastilles verticales** au-dessous du cours aux dates d’événements majeurs,
- une **infobulle** au survol qui montre date, type, impact,
- des **icônes** : 📈 contrat, ⚠ scandale, 🏛 régulation, 🛰 produit, etc.

Cela répond directement au retour "les graphes ne montrent pas les événements".

### 1.3 Tests
- `test_market_events.py` : déterminisme, impact borné, narration présente.
- `test_graph_annotations.py` : pastilles rendues sans crash, infobulle alignée.

---

## Phase 2 — Fondamentaux dynamiques et modèle de valorisation (2-3 sprints)

### 2.1 État fondamental par société
Ajouter sur chaque société des séries temporelles calculées à chaque pas :
- `revenue_growth` (YoY),
- `operating_margin` et `net_margin` (déjà partiellement là, mais lissés),
- `free_cash_flow`,
- `net_debt / ebitda` dynamique,
- `interest_coverage`,
- `dividend_per_share` et `payout_ratio`.

### 2.2 Rating de crédit dynamique
Le rating actuel est instantané. Le rendre **persistant** avec des transitions graduelles (S&P style) : une dégradation est un événement qui a son propre impact de cours et une news.

### 2.3 Modèle de croissance endogène
Les `drift` des sociétés deviennent fonction de :
- leur secteur/région,
- leur `revenue_growth` passé (momentum fondamental),
- leur niveau d’endettement,
- le régime macro.

Cela crée des "cycles de vie" : les grosses capi tech restent growth, les utilities versent des dividendes stables, etc.

### 2.4 Tests
- `test_fundamentals.py` : cohérence comptable (mktcap ≈ price × shares, FCF positif sur moyenne, etc.).
- `test_credit_rating.py` : transitions de rating cohérentes avec la dette.

---

## Phase 3 — Contagion, supply chain et concurrence (2 sprints)

### 3.1 Matrice de liens entre entreprises
Générer de façon déterministe un graphe de relations `supply_links` :
- client/fournisseur (même secteur, proximité de capitalisation),
- concurrent direct (même secteur + même région),
- holding/subsidiaire (cross-holdings dans les grandes capi).

### 3.2 Contagion d’événements
Quand une société subit un événement, les liens subissent un choc secondaire atténué :
- fournisseur perd un gros contrat → client légèrement pénalisé,
- OPA sur une société → concurrents du même secteur réévalués,
- crise d’un fournisseur critique (semicon) → secteur auto/tech impacté.

### 3.3 Part de marché dynamique
Dans chaque secteur/région, introduire un "leader" et un "challenger" dont la croissance relative influe sur le drift relatif (effet gagnant-gagnant).

---

## Phase 4 — Forward, consensus et scénarios (2 sprints)

### 4.1 Consensus analystes
Pour chaque société, maintenir un `consensus_eps` et un `consensus_growth` :
- révisions à chaque pas en fonction des news/earnings,
- écart consensus vs réalité future visible dans l’UI,
- impact sur le cours via l’anticipation.

### 4.2 Projections de graphes
Ajouter une option "scénario" dans l’atelier de graphes :
- Bull / Base / Bear sur 1-3 mois,
- calculée à partir de la volatilité récente + consensus + régime,
- affichée en zone ombrée sur le graphe (fan chart).

### 4.3 Tests
- `test_consensus.py` : révisions déterministes, convergence vers la réalité en moyenne.
- `test_fan_chart.py` : 3 scénarios cohérents avec le passé.

---

## Phase 5 — Calibration avancée et validation statistique (1-2 sprints)

### 5.1 Tests statistiques sur la simulation
Ajouter des tests sur des échantillons de graines :
- distribution des rendements (kurtosis > gaussienne),
- corrélation sectorielle en période calme vs stress,
- mean-reversion des marges,
- calibration rendement/vol annuels plus fine.

### 5.2 Paramètres ajustables
Rendre certains paramètres de calibration (probabilité d’événements, force de contagion, amplitude des jumps) centralisés dans un fichier de config testable.

### 5.3 Documentation
Documenter dans `CLAUDE.md` le nouveau pipeline : facteurs → événements → fondamentaux → consensus → graphes annotés.

---

## Approche technique

1. **Déterminisme strict** : tout nouveau tirage rng est consommé à chaque pas, de manière fixe et indépendante du résultat (comme les sauts existants). Les tests le vérifient.
2. **Modularité** : chaque phase est un module pur (`core/market_events.py`, `core/fundamentals.py`, `core/consensus.py`) qui s’intègre dans `Market.step()` via un appel helper.
3. **Affichage** : les annotations et fan charts sont dessinés dans `ui/widgets.py` et réutilisés par `scene_graph_render.py` / `scene_company.py`.
4. **Tests** : chaque phase a ses tests dédiés + la suite `pytest` globale reste verte.

---

## Livrables intermédiaires

| Phase | Livrable visible pour le joueur |
|-------|--------------------------------|
| 1 | Graphes avec pastilles d’événements + news ciblées par entreprise |
| 2 | Fiches entreprises plus riches (FCF, rating, dette dynamique) |
| 3 | Corrélation visible entre entreprises liées dans les graphes compare/spread |
| 4 | Fan chart Bull/Base/Bear dans l’atelier de graphes |
| 5 | Calibration crédible documentée, tests statistiques |

---

## Priorisation proposée

Commencer par la **Phase 1** : c’est le meilleur rapport impact/effort, elle répond au besoin immédiat ("graphes pas bons", "incidents avec impacts") et pose les fondations pour les phases suivantes.
