# TERMINAL — Finance Career Simulator

Prototype jouable — moteur de base + interface Bloomberg + modules financiers réels.

## Contenu actuel

### Écrans
- **Menu principal** avec ticker animé, nouvelle/charger partie.
- **Choix du continent** : globe 3D interactif (Europe/USA/Asia), fiches réglementaires.
- **Terminal Bloomberg** : bandeau joueur, ticker, panneau marchés (indices + sparklines),
  flux de news régional, cadre réglementaire, ligne de commande.
- **Évaluation de promotion** : QCM adaptés au grade et à la voie, seuil 70%, feedback + explications.
- **Glossaire** : 48 termes en 8 catégories, recherche au clavier.
- **Module Portfolio** : frontière efficiente de Markowitz, optimisation Sharpe/min-variance,
  Capital Market Line, ajustement des poids en direct.
- **Module M&A** : modèle LBO (MOIC/IRR) + analyse accretion/dilution.
- **Choix de voie** : Portfolio / M&A / Risk / Quant / Advisory.

### Moteur financier (core/finmath.py) — formules réelles, toutes testées
- Valeur temps de l'argent : PV, FV, NPV, IRR
- Obligations : prix, duration de Macaulay, duration modifiée
- Valorisation : DCF, WACC, valeur terminale
- Options : Black-Scholes + Greeks (delta, gamma, vega, theta, rho)
- Portefeuille : rendement, volatilité, Sharpe, min-variance, max-Sharpe, efficient frontier
- Risque : VaR historique, CVaR, VaR paramétrique
- M&A : accretion/dilution, modèle LBO
- Ratios : ROE, ROA, marge nette, D/E, current ratio, interest coverage...

### Simulation de marché (core/market.py + data/companies.py)
- **320 sociétés fictives** réparties USA / Europe / Asie, sur 14 secteurs.
  Noms volontairement déformés (LVMH→**LWNH**, NVIDIA→**MVC**, S&P 500→**C&D 500**,
  CAC 40→**KAK 40**...). Roster **déterministe** (identique d'une partie à l'autre).
- **Modèle à facteurs** : chaque rendement = dérive + facteur monde + facteur secteur
  + facteur région + bruit propre. Conséquences réalistes *gratuites* :
  - les **indices émergent** de leurs constituants (le KAK 40 dépend de LWNH, le
    C&D 500 de MVC...) ;
  - **corrélations réalistes** entre valeurs et entre régions (~0,70) ;
  - une **crise** = un choc injecté sur les bons facteurs (2008 : monde + finance
    effondrés ; tornade : secteur agro ; etc.).
- Calibré (12 graines, 10 ans) pour une **prime de risque actions positive** :
  action moyenne ~**+7 %/an** (vs cash ~3 %, obligations IG ~5 %), volatilité
  ~**16 %**, indice phare ~**16 %** (dominé par les grandes capi). Une perte sur
  10 ans reste possible selon l'« époque » de marché.
- **Déterministe & léger** : l'état se reconstruit exactement via (graine, nb de pas),
  donc les sauvegardes restent minuscules et les prix sont reproductibles.
- **Carte du monde au centre** du terminal : hubs régionaux affichant l'indice phare,
  sa variation et la 1ʳᵉ société de la région ; les actualités « poppent » par région.
- **Fiches sociétés** type Bloomberg (`COMPANY <ticker>`) : capi, BPA, P/E, EV/EBITDA,
  marges, dette, dividende, bêta, graphe de cours.

### Missions par grade (core/missions.py + scene_mission.py)
Le travail change avec la carrière, et la réputation se gagne en l'effectuant :
- **Intern** : compte-rendu de données — texte à trous (capi, BPA, marge) + QCM sur une vraie société du roster.
- **Analyst** : lecture de graphes — tendance, rendement, volatilité, surperformance.
- **Associate** : décision — acheter / conserver / vendre selon P/E et momentum.
- **VP+** : construction & couverture de portefeuille (hedging, risk parity, bêta).

Chaque mission rapporte de la **réputation** (au prorata du score) + un honoraire.
L'**examen de promotion (EVAL) est verrouillé** tant que la réputation n'atteint pas
le seuil du grade (`MISSION` pour la faire monter). Commande : `MISSION`.

### Examens de promotion (refonte) & certifications
- **Examens générés** (core/exam.py) : chaque promotion = un « entretien technique » de
  **20 à 30 questions** (+1 par grade). **Taille de banque décroissante par grade** :
  ~**1000** questions pour Intern→Junior, ~900, … jusqu'à ~**300** aux grades élevés
  (plus de variété en bas, questions plus dures en haut). La capacité procédurale réelle
  dépasse largement ces cibles (8 000–12 000 variantes/grade) → **aucune répétition au rejeu**. Types : **calcul chiffré**, **QCM**, **lecture de graphe**,
  **définition à trous** et **formule à compléter** (sans chiffres) — difficulté calibrée
  sur le poste visé. Calculatrice et bouton SUIVANT intégrés.
- **Certifications** (`CERT`) : **CFA** (Portfolio), **FRM** (Risk), **CQF** (Quant). On paie
  des frais et on passe un examen exigeant ; une certification **liée à votre voie** booste
  fortement la réputation et **réduit les critères de promotion** (accès plus rapide aux hauts
  postes). Titre de prestige + badge à la clé. Certaines voies n'ont pas de certification.

### Confort de jeu
- **Calculatrice** intégrée et déplaçable dans les missions (bouton CALCULATRICE) :
  pavé cliquable, parenthèses, puissance, pour faire les calculs des questions sans quitter l'écran.
- **Évaluation** : après chaque réponse, l'explication s'affiche et un bouton **SUIVANT**
  (toujours visible) fait passer à la question suivante.

### Apprendre la finance & outils Bloomberg
- **Académie** (`LEARN`) : 15 leçons exactes et concises (P/E, EV/EBITDA, DCF, diversification,
  Sharpe, VaR/CVaR, bêta, options, Greeks, taux, courbe des taux, LBO, accretion/dilution,
  réflexes Bloomberg) — chacune avec **formule + exemple chiffré + à retenir**. Lire tout = badge « Diplômé ».
- **Macro-économie** (`ECO`) : taux directeur, inflation, croissance, chômage, confiance —
  qui évoluent et **influencent réellement le marché** (taux ↑ → finance/immobilier sous pression…).
- **Fonctions façon Bloomberg** : `DES`/`FA` (fiche), `GP` (graphe), `RV` (valeur relative vs pairs),
  `WEI` (indices), `EQS` (screener), `ECO`, `PRT` (portefeuille) + `DEFINE <terme>` (glossaire).
- **Fiche société enrichie** : ratios pros (P/S, FCF yield, dette/EBITDA, payout…) en 2 colonnes,
  et `RV <ticker>` situe chaque multiple face à la médiane du secteur (décoté / en ligne / cher).

### Monde élargi & confort
- **7 régions jouables** : USA, Amérique du Nord, Europe, Amérique du Sud, Afrique, Asie,
  Océanie — chacune avec régulateur, devise, indice (C&D 500, TXC 60, KAK 40, BVSP, JT 40,
  NKX 225, AX 200) et ses sociétés. Carte interactive avec 7 hubs (fiche au survol, clic = zoom).
- **Dividendes** : les positions versent un revenu passif à chaque tour (selon le rendement).
- **Secteur du trimestre** : un secteur mis en avant chaque trimestre pour guider l'investissement.
- **Terminal** : historique de commandes (↑/↓), **autocomplétion** (Tab + suggestion fantôme),
  **indices cliquables** ouvrant un graphe d'historique en fenêtre déplaçable.

### ETF — fonds indiciels (core/etfs.py + scene_etfs.py)
- **~80 ETF** couvrant toutes les grandes familles : *broad/monde, régions, pays,
  secteurs, styles factoriels* (value, growth, dividend, quality, momentum, min-vol),
  *thématiques* (IA, semis, robotique, cybersécurité, énergie propre, défense,
  infrastructure, fintech, biotech…), *ESG*, *REIT*, *obligataire* (souverain,
  corporate, high yield, indexé inflation, court/long terme), *commodities*, *devises*,
  et quelques **levier/inverse** clairement signalés « risque élevé ».
- **NAV émergente** : comme les indices, la valeur d'un ETF découle de son **exposition**
  (panier d'actions, taux, commodities…), donc il réagit de façon **cohérente** aux
  facteurs monde/secteur/région/taux/inflation — déterministe, reconstruit depuis les
  historiques du marché (5 ans d'historique dès le départ).
- Pleinement intégrés : recherche/filtres/tri (`ETF`), explorateur unifié, fiche
  flottante, **graphes** (`GP`/`COMP`), **comparaison** (`COMPARE`), portefeuille
  (valeur nette), trading (`BUYETF`/`SELLETF`).

### News & événements (core/news.py + scene_news.py)
- Scène **`NEWS`** : fil d'actualités centralisé, **filtrable par type** (marché, macro,
  entreprises, politique, réglementaire, événements) **et par région**, regroupé par jour.
- **Persistance jusqu'à 3 ans** : on peut revoir tout ce qui s'est passé depuis le début.
- **Carte du monde** : les news du jour s'affichent en **marqueurs persistants** là où
  elles se produisent (plusieurs incidents simultanés), remplacés au tour suivant.
- Les **news de pays** atterrissent dans l'inbox ; des **deals/mandats souverains**
  apparaissent quand c'est cohérent avec l'actualité politique (`DEALS`).
- **Santé financière** (`FA`) : analyse complète d'une société — stats clés, graphe de
  cours 5 ans, et **5 exercices** de compte de résultat & bilan.

### Contenu additionnel
- **Mandats clients** (`MANDATES`) : un client confie un capital avec un **objectif de
  rendement** sur N trimestres et une **limite de bêta** ; réussite → grosse commission +
  réputation, échec → réputation. `MANDATE ACCEPT/DECLINE <id>`. Débloqué dès Associate.
- **Recherche analyste** (`RESEARCH <ticker>`) : estime une **valeur intrinsèque** + une
  reco (ACHAT/NEUTRE/VENTE), affichée sur la fiche société.
- **Alertes de prix** (`ALERT <ticker> <prix>`) : notification (toast + email) au
  franchissement du seuil ; `ALERTS` pour la liste.
- Plus de **dilemmes** (front-running, greenwashing, notes de frais, restructuration),
  de **crises** (sanitaire, resserrement du crédit, vague d'IPO, matières premières) et
  de **badges** (Gestionnaire, Gérant d'élite, Diversifié, Œil de l'analyste).

### Refonte UX (Phase 7)
- **Format large** 1520×740 (plus d'espace horizontal, plus ramassé verticalement),
  layouts responsives et **footer réservé** : les boutons retour ne recouvrent plus le texte.
- **Terminal redessiné** : rail de commandes cliquable à gauche (ADV, MISSION, DEALS,
  MARCHÉ, TOP, PORTEF., INBOX, DÉCIDE, CARRIÈRE, RIVAUX…), 3 colonnes denses, console en bas.
- **Carte interactive zoomable** : clic sur une région → vue régionale avec tous les indices
  et les sociétés (cliquables vers leur fiche), retour ‹ MONDE.
- **Fenêtres de données déplaçables** (style Bloomberg) : `MARKET`, `TOP`, `SECTOR`,
  `SCREEN`, `COMPARE`, `MOVERS`, `WATCHLIST`, `RANKING`, `CALENDAR` ouvrent un tableau
  que l'on déplace par sa barre de titre et que l'on ferme.
- Catalogue de commandes réorganisé en 3 colonnes (plus aucun chevauchement).

### Finition premium (Phase 6)
- **Centre de notifications** : toasts animés (glissement + fondu) en overlay pour
  promotions, badges, crises, décisions, sanctions (`ui/notifications.py`).
- **Badges de prestige** (`core/badges.py`) : 15 succès débloqués par jalons (grade,
  deals, valeur nette, intégrité, crises survécues, 1ʳᵉ place du classement…), affichés
  dans l'écran carrière.
- **Hiérarchie visuelle** : palette de priorité (critique/urgent/bonus), panneaux à
  barre de priorité colorée (le panneau Priorités passe au rouge en cas de danger).
- **Polish** : boutons arrondis avec profondeur/relief, **menu vivant** (chandeliers
  animés en fond), résumé de la dernière partie.

### Décisions & éthique (core/dilemmas.py + scene_dilemma.py)
- **Dilemmes** qui surgissent au fil de la carrière : éthiques (délit d'initié,
  mis-selling), réglementaires (alerte risque ignorée, conflit d'intérêts), stratégiques
  (mandat chronophage, débauchage), et **décisions « signature »** rares et lourdes
  (méga-fusion, sauver la firme, dénoncer une fraude).
- Chaque option a un **coût et une conséquence clairs** : trésorerie, réputation, et
  **scrutin réglementaire** (jauge `heat`). Couper les coins paie à court terme…
- …mais un scrutin élevé peut déclencher une **enquête** : amende + réputation. Les choix
  s'enchaînent en vrais arbitrages cash / réputation / risque / timing.
- Déclenchés à l'`ADV` (ou `DECIDE` pour une décision en attente). Le scrutin s'affiche
  dans les priorités et l'écran carrière.

### Monde vivant (core/inbox.py · rivals.py · scenarios.py)
- **Messagerie** (`INBOX`) : emails contextuels du manager, des clients, de la
  conformité et du desk — félicitations de promotion, revue trimestrielle, alertes
  de risque/concentration, briefs de marché. Badge de non-lus dans le terminal.
- **Concurrents** (`RIVALS`) : banquiers rivaux nommés dont le score évolue avec le
  marché ; ils **raflent les deals** que vous laissez expirer. Classement joueur vs rivaux.
- **Crises déclenchées dans le temps** : krach systémique (type 2008), choc de taux
  (type 2023), catastrophe agricole, éclatement de bulle tech, choc énergétique,
  tensions en Asie… (+ booms). Elles frappent les indices **et votre portefeuille**.
- **Conséquences narratives** : promotions, crises, deals perdus et trimestres
  alimentent le journal de carrière et la messagerie.

### Portefeuille & P&L réel (core/portfolio.py + scene_book.py)
- **Acheter / vendre de vraies sociétés** du roster : `BUY <ticker> <qté>`, `SELL <ticker> <qté|ALL>`.
- **Prix de revient moyen**, commission, **P&L latent et réalisé**, **valeur nette** (cash + positions).
- Les positions **vivent avec le marché** : un krach fait réellement chuter la valeur nette,
  un bon choix la fait grimper (les chocs/crises frappent désormais le portefeuille).
- Commandes décisionnelles : `ALLOCATE <ticker> <pct>` (viser un % de la valeur nette),
  `HEDGE [pct]` (bêta / lever du cash), `REBALANCE` (poids égaux), `PITCH` (décrocher un mandat).
- Écran **PORTFOLIO / BOOK** : positions, P&L par ligne, bêta, répartition sectorielle.
- Liquidité : les coûts opérationnels se paient en cash → rester investi à 100 % est risqué.
- (L'outil frontière efficiente de Markowitz reste accessible via `FRONTIER`.)

### Déblocage progressif des actions (core/unlocks.py)
Pour canaliser le début de carrière puis monter en complexité, les actions se
débloquent par grade :
- **Stagiaire** : missions, apprentissage (LEARN), analyse en lecture (MARKET, COMPANY, ECO).
- **Junior Analyst (1)** : outils d'analyse (WATCHLIST, ALERT, COMPARE, RV, RESEARCH).
- **Analyst (2)** : traiter des **DEALS**, choisir une **voie**.
- **Associate (4)** : **investir** (BUY/SELL/ALLOCATE), démarcher des mandats (PITCH).
- **Vice President (6)** : **mandats clients**, **couverture** (HEDGE).
Les commandes/boutons verrouillés affichent un cadenas et le grade requis ; le terminal
indique le **prochain déblocage**.

### Carrière & progression (core/career.py + scene_career.py)
- **12 grades** : Intern → Junior Analyst → Analyst → Senior Analyst → Associate →
  Senior Associate → VP → Senior VP → Director → Executive Director → MD → Partner
  (début / milieu / fin de carrière).
- **Promotion par critères combinés** (plus seulement le QCM) : réputation **+** missions
  du grade **+** deals conclus **+** ancienneté. L'examen `EVAL` ne s'ouvre que si tous
  les critères sont remplis.
- **Objectifs trimestriels** (2 à 4 cibles : réputation, missions, deals, trésorerie)
  récompensés en réputation + honoraire ; **bonus « trimestre parfait »**.
- **Titres de prestige** liés à la voie (Rainmaker, Risk Guardian, Quant Star…).
- **Journal de carrière** (promotions, deals, crises, objectifs) + **bilan de fin** rétrospectif.
- Écran **CAREER** : échelle des grades, roadmap de promotion, objectifs, stats de run, journal.
- **Panneau « Priorités »** dans le terminal : prochain objectif, promotion, risque, opportunité.

### Système de jeu
- 12 grades, du stagiaire au Partner / C-Suite.
- Réputation, trésorerie, sauvegarde/chargement JSON, autosave.
- **Temps qui avance** (commande `ADV`) : +5 jours par tour, calendrier en trimestres,
  salaire et coûts opérationnels croissants avec le grade.
- **Événements de marché dynamiques** : rallyes, sell-offs, appels de marge, amendes,
  événements régionaux... impactant cash et réputation (cf. `core/events.py`).
- **Deals à délai** (`DEALS`, `DEAL <id>`) : opportunités générées avec échéance ;
  réussite probabiliste selon réputation/difficulté, pénalité si expirées (cf. `core/deals.py`).
- **Faillite / réputation nulle → game over** (écran de fin avec récap de carrière).
- **Mode hardcore** (sélectionnable à la création) : pas de sauvegarde manuelle,
  faillite = run définitivement perdu.
- **Gestion des sauvegardes** : autosave + 3 slots manuels, métadonnées (grade, jour,
  cash, date), chargement et suppression depuis l'UI.
- **Polish visuel** : fondu de transition entre scènes, sparklines d'historique,
  feedback d'appui sur les boutons, marges cohérentes.

## Démarrage
Au lancement d'une **nouvelle carrière**, un **briefing** explique l'objectif du jeu
et son fonctionnement (ADV, missions, EVAL, trading, deals/mandats, décisions, rivaux/crises)
avant d'entrer dans le terminal.

## Installation sur Mac (PyCharm)

```bash
pip install -r requirements.txt
python main.py
```

## Commandes du terminal (in-game)

| Commande   | Effet                                   |
|------------|-----------------------------------------|
| `HELP`     | Aide rapide                             |
| `COMMANDS` / `?` | Catalogue complet des commandes   |
| `STATUS`   | Situation actuelle (grade, cash, rép.)  |
| `ADV`      | Avancer le temps (+5 jours, 1 pas marché)|
| `PORTFOLIO`/`BOOK` | Livre de positions (valeur nette, P&L) |
| `BUY`/`SELL`/`ALLOCATE`/`HEDGE`/`REBALANCE` | Trading |
| `RESEARCH <tk>` / `ALERT <tk> <px>` | Analyse & alertes |
| `MANDATES` / `MANDATE ACCEPT <id>` | Mandats clients |
| `LEARN` / `DEFINE <terme>` | Académie / glossaire |
| `ECO` · `RV <tk>` · `GP <tk>` · `WEI` · `EQS` | Fonctions style Bloomberg |
| `PITCH` / `FRONTIER` | Mandat client / outil Markowitz |
| `MISSION`  | Mission du grade (réputation + honoraire)|
| `INBOX`/`MAIL` | Messagerie (manager, clients, conformité, desk) |
| `RIVALS`   | Classement face aux concurrents          |
| `DECIDE`   | Trancher un dilemme en attente           |
| `CAREER`   | Tableau de bord : roadmap, objectifs, stats, journal |
| `EVAL`     | Examen de promotion (critères combinés)  |
| `WATCHLIST`/`COMPARE`/`SECTOR`/`REGION` | Outils d'analyse |
| `SCREEN`/`RANKING`/`BENCHMARK`/`CALENDAR` | Filtres & repères |
| `MARKET`   | Vue des indices mondiaux                |
| `TOP [region]` | Meilleures sociétés d'une région    |
| `MOVERS`   | Plus fortes hausses / baisses           |
| `COMPANY <tk>` | Fiche société (ex: `COMPANY MVC`)   |
| `SEARCH <txt>` | Rechercher une société              |
| `DEALS`    | Lister les deals en cours               |
| `DEAL <id>`| Traiter un deal avant son échéance      |
| `EVAL`     | Passer l'évaluation de promotion        |
| `PORTFOLIO`| Module portefeuille (efficient frontier)|
| `MA`       | Module M&A (LBO, accretion/dilution)    |
| `RISK`     | Module risque (VaR/CVaR, stress tests)  |
| `QUANT`    | Module quant (Black-Scholes, Greeks)    |
| `SHEET`    | Tableur intégré                         |
| `GLOSSARY` | Ouvrir le glossaire                     |
| `TRACK`    | Choisir une voie de spécialisation      |
| `SAVES`    | Gestion des sauvegardes                  |
| `ETF` / `ETFS` | Marché des ETF (filtres/tri/trading), `BUYETF`/`SELLETF` |
| `BONDS` · `CMDTY` · `CRYPTO` | Marchés obligataire / commodities / crypto |
| `SAVE`     | Sauvegarde manuelle (hors hardcore)     |
| `NEWS`     | Scène News & événements (filtres par type/région, historique 3 ans) |
| `REG`      | Rappel réglementaire de la région       |
| `MENU`     | Retour au menu (ou ESC)                 |

## Structure

```
finance_game/
├── main.py
├── requirements.txt
├── core/
│   ├── config.py        palette, grades, continents
│   ├── game_state.py    joueur + save/load
│   ├── scene_manager.py machine à scènes
│   └── finmath.py       MOTEUR FINANCIER (testé)
├── ui/
│   ├── fonts.py  widgets.py  globe.py
├── data/
│   ├── glossary_data.py    48 termes
│   └── question_bank.py    banque de questions
└── scenes/
    ├── scene_menu / continent / terminal
    ├── scene_evaluation / glossary / track
    └── scene_portfolio / scene_ma
```

## Packaging (.app / .exe)

```bash
pip install -r requirements.txt -r requirements-build.txt
python build.py --clean
```

Résultat dans `dist/` :
- **macOS** : `dist/TERMINAL.app` (bundle double-cliquable)
- **Windows** : `dist/TERMINAL.exe` (lancer la même commande sous Windows)

La recette est dans `terminal.spec` (cross-plateforme). Icônes optionnelles :
déposer `assets/icon.icns` (Mac) ou `assets/icon.ico` (Windows). En version packagée,
les sauvegardes sont écrites dans l'espace utilisateur (`~/Library/Application Support/TERMINAL-FinanceSim`
sur Mac, `%APPDATA%` sur Windows).

## Prochaines étapes
- Davantage de profondeur sur les modules (Risk/Quant interactifs liés aux deals).
- Mini-jeux de résolution de deals (au lieu d'une résolution probabiliste).
- Signature/notarisation du `.app` pour distribution hors développeur.
- Équilibrage fin de l'économie (salaires, amplitude des événements).
