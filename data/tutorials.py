"""
tutorials.py — Tutoriels illustrés « Comment faire » (FR).

Chaque tutoriel a un titre, une capture d'écran (assets/tutorials/<image>),
une intro, des étapes numérotées claires et un encart « à comprendre ».
Affichés par scenes/scene_tutorials.py, ouverts via TUTO ou le bouton de
l'Académie. Objectif : ne jamais être perdu sur les actions clés du jeu.
"""

TUTORIALS = [
    {
        "id": "buy_sell",
        "title": "Acheter & vendre des actions",
        "image": "buy_sell.png",
        "intro": "Tout se pilote au clavier depuis la console (en bas du terminal). "
                 "Les ordres sont insensibles à la casse.",
        "steps": [
            "Trouvez une société : SEARCH <nom>  (ex. SEARCH mavric) ou COMPANY MVC.",
            "Achetez : BUY <ticker> <quantité>   →   ex. BUY MVC 200.",
            "Vendez :  SELL <ticker> <quantité|ALL>   →   ex. SELL MVC ALL.",
            "Parier à la baisse : SHORT <ticker> <qté>, puis COVER pour racheter.",
            "Suivez le résultat : PRT (livre) ou PA (analyse détaillée).",
        ],
        "concept": "À l'achat, une commission est prélevée et le prix d'exécution inclut "
                   "un léger écart. Vous pouvez dépasser votre cash grâce au LEVIER "
                   "(emprunt sur marge) — surveillez MARGIN : trop de levier = appel de "
                   "marge et liquidation forcée.",
    },
    {
        "id": "bonds",
        "title": "Obligations : souverains & corporates",
        "image": "bonds.png",
        "intro": "Une obligation est un PRÊT : vous touchez un coupon régulier et le "
                 "nominal est remboursé à l'échéance. Il en existe deux familles — "
                 "SOUVERAINES (émises par un État/pays) et CORPORATE (émises par une "
                 "entreprise). Ouvrez le marché avec BONDS.",
        "steps": [
            "Affichez le marché : BONDS — la liste sépare SOUVERAINS et CORPORATE.",
            "SOUVERAIN = dette d'un PAYS (ex. Trésor US, Bund allemand). Son rendement "
            "dépend du rating du pays, de sa dette/PIB et de sa stabilité. Tapez GOV "
            "pour voir les pays, leur note et leur historique.",
            "CORPORATE = dette d'une ENTREPRISE (ex. Pomme, Toyota). Plus l'émetteur est "
            "risqué (rating bas), plus le coupon/le rendement exigé est élevé.",
            "Lisez chaque ligne : RATING, COUPON, MAT. (maturité), YTM (rendement), PRIX, "
            "DUR (sensibilité au taux).",
            "Achetez : BUYBOND <id> <qté>   ·   Vendez : SELLBOND <id> <qté>. Les coupons "
            "tombent automatiquement à chaque pas (ADV).",
            "Exemple de ligne lue sur BONDS : « FR-2034  AA  COUPON 3.2%  MAT 8a  YTM 3.6%  "
            "PRIX 97.4  DUR 6.9 ». Le YTM (3.6%) > coupon (3.2%) car le prix (97.4) est sous "
            "le pair (100) — le marché exige un rendement plus élevé que le coupon affiché.",
            "Le SPREAD DE CRÉDIT, c'est l'écart de YTM entre une obligation risquée et une "
            "obligation « sans risque » de même maturité (souvent le souverain le mieux noté "
            "de la région). Ex. : un corporate BBB à 5.1% de YTM contre un souverain AAA à "
            "3.0% sur la même maturité = spread de 2.1 points (210 pb). Plus le rating "
            "baisse, plus le spread s'élargit — c'est la prime exigée pour le risque de défaut.",
        ],
        "concept": "Prix et taux varient en SENS INVERSE : si les taux montent, le prix "
                   "baisse — d'autant plus que la DURATION est longue. Le RENDEMENT se "
                   "décompose en : courbe (taux directeur) + prime de terme + spread de "
                   "CRÉDIT (rating) + prime de risque PAYS (souverains). Un souverain bien "
                   "noté (AAA/AA) a un spread quasi nul ; un corporate spéculatif (BB et "
                   "moins) peut afficher plusieurs points de spread. Un événement politique "
                   "régional (cf. tutoriel Pays) élargit les spreads de la zone : les prix "
                   "des souverains ET des corporates de la région baissent, puis se "
                   "résorbent — une occasion d'acheter du rendement sur repli.",
    },
    {
        "id": "governments",
        "title": "Pays, gouvernements & politique",
        "image": "governments.png",
        "intro": "Le monde est peuplé de vrais pays, regroupés par région. Chaque "
                 "gouvernement a une note souveraine, une dette/PIB, une stabilité "
                 "politique et un historique sur ~5 ans. Ouvrez l'écran avec GOV.",
        "steps": [
            "Tapez GOV : à gauche les pays par région, à droite la fiche détaillée.",
            "Lisez la fiche : NOTE souveraine, DETTE/PIB, STABILITÉ, régime, devise, et "
            "l'HISTORIQUE des 5 dernières années (inspiré du réel).",
            "En bas de la fiche : les OBLIGATIONS du pays, avec leur rendement en direct.",
            "Au fil du jeu, des ÉVÉNEMENTS POLITIQUES surviennent dans un pays et frappent "
            "sa RÉGION : crise budgétaire, élections, tensions géopolitiques, relance…",
            "Surveillez le flux d'actualités (⚑) et la carte : l'événement s'affiche sur "
            "la région concernée.",
        ],
        "concept": "Un événement politique a deux effets RÉELS et exploitables : (1) il "
                   "choque les ACTIONS de la région (les sociétés de la zone montent ou "
                   "baissent via le facteur régional) ; (2) il fait varier le SPREAD de "
                   "crédit de la zone, donc le prix des OBLIGATIONS souveraines et "
                   "corporates de la région. Une mauvaise nouvelle (instabilité, défaut) "
                   "élargit les spreads (prix en baisse) ; une bonne nouvelle (réformes, "
                   "relance) les resserre. Anticiper la région touchée = anticiper qui "
                   "gagne et qui perd.",
    },
    {
        "id": "futures",
        "title": "Futures & matières premières",
        "image": "futures.png",
        "intro": "Un future (ou forward) est un engagement d'acheter/vendre un actif à "
                 "une date future, à un prix fixé aujourd'hui. Ouvrez avec CMDTY.",
        "steps": [
            "Affichez les contrats : CMDTY (or, pétrole, gaz, cuivre, blé…).",
            "Lisez la STRUCTURE : Contango ou Backwardation, et le roll/an.",
            "Achetez : BUYCMDTY <id> <quantité>   ·   Vendez : SELLCMDTY <id> <qté>.",
            "À chaque pas, la position « roule » sur l'échéance suivante (coût/gain).",
        ],
        "concept": "CONTANGO : le future cote au-DESSUS du comptant → en roulant, vous "
                   "vendez bas et rachetez haut = roll NÉGATIF (ça coûte). "
                   "BACKWARDATION : future SOUS le comptant → roll POSITIF (ça rapporte). "
                   "Un forward et un future ont la même idée ; le future est standardisé "
                   "et échangé en bourse.",
    },
    {
        "id": "portfolio",
        "title": "Suivre & analyser son portefeuille",
        "image": "portfolio.png",
        "intro": "La commande PA ouvre l'analyse détaillée de TOUT votre portefeuille "
                 "(actions, obligations, matières, crypto).",
        "steps": [
            "Tapez PA (ou bouton ANALYSE dans le livre PRT).",
            "Lisez les tuiles : valeur nette, P&L, bêta, levier, volatilité, drawdown.",
            "Vérifiez les POIDS et la répartition (classe / secteur / région).",
            "Étudiez les CORRÉLATIONS et la FRONTIÈRE EFFICIENTE (position « VOUS »).",
        ],
        "concept": "Un portefeuille trop CONCENTRÉ (un poids dominant, des actifs très "
                   "corrélés) est fragile. Diversifier rapproche votre point de la "
                   "frontière efficiente : meilleur rendement attendu pour un risque donné.",
    },
    {
        "id": "graph",
        "title": "Lire un graphe (analyse technique)",
        "image": "graph.png",
        "intro": "L'atelier de graphes affiche 5 ans d'historique dès le jour 1. "
                 "Ouvrez-le avec GP <ticker> puis changez de type en haut.",
        "steps": [
            "Ligne + moyennes mobiles : GP <ticker>   (recherche par nom acceptée).",
            "Chandeliers : GPC · Barres OHLC : GPO · Variation % : GPCH.",
            "Comparer plusieurs actifs : COMP · Spread/ratio : HS.",
            "Risque : HVOL (volatilité), BETA (régression), CORR (corrélations).",
        ],
        "concept": "Les moyennes mobiles (MM20/MM50) lissent la tendance ; un croisement "
                   "à la hausse est souvent vu comme un signal positif. Les chandeliers "
                   "montrent ouverture/haut/bas/clôture de chaque période.",
    },
    {
        "id": "short",
        "title": "Vendre à découvert (short / cover)",
        "image": "short.png",
        "intro": "Aller LONG (BUY), c'est parier que le prix MONTE. Aller SHORT, c'est "
                 "parier que le prix BAISSE : vous empruntez des actions, les vendez "
                 "tout de suite, puis devez les RACHETER plus tard pour les rendre. "
                 "Débloqué au grade Levier (cf. badge 🔒 dans COMMANDS).",
        "steps": [
            "Ouvrez la fiche de la société visée : DES <ticker> ou COMPANY <ticker>.",
            "Vendez à découvert : SHORT <ticker> <quantité>   →   ex. SHORT MVC 100. "
            "Le produit de la vente crédite votre cash, mais la position apparaît en "
            "négatif dans PRT.",
            "Surveillez votre marge avec MARGIN : une position courte consomme de la "
            "marge, comme un emprunt sur effet de levier.",
            "Si le prix BAISSE comme prévu, rachetez moins cher : COVER <ticker> <qté|ALL> "
            "→   ex. COVER MVC ALL. La différence (vendu haut − racheté bas) est votre gain.",
            "Si le prix MONTE au contraire, COVER coûte plus cher que ce que vous avez "
            "touché à la vente : c'est une PERTE — clôturez tôt si la thèse échoue.",
        ],
        "concept": "Asymétrie clé : à l'achat (LONG), la perte maximale est limitée à votre "
                   "mise (le prix ne descend jamais sous 0) alors que le gain est, en théorie, "
                   "illimité. Au SHORT, c'est l'INVERSE : le gain maximal est limité (le prix "
                   "ne peut pas descendre sous 0) alors que la PERTE est illimitée — le prix "
                   "peut monter sans plafond. C'est pourquoi le SHORT consomme de la marge et "
                   "peut déclencher un appel de marge si la position part contre vous. Un "
                   "SHORT SQUEEZE survient quand un prix qui monte force de nombreux vendeurs "
                   "à découvert à COVER en urgence pour limiter leurs pertes — leurs achats "
                   "forcés poussent le prix encore plus haut, amplifiant la hausse en boucle.",
    },
    {
        "id": "ma",
        "title": "M&A : cibles, LBO & sortie",
        "image": "ma.png",
        "intro": "Le module M&A (commande MA) permet d'ACQUÉRIR des sociétés privées en "
                 "tout ou partie à crédit (effet de levier), de les détenir, puis de les "
                 "CÉDER (exit) plus tard avec une plus-value. Débloqué au grade M&A.",
        "steps": [
            "Ouvrez le hub : MA — onglet CIBLES liste les sociétés privées disponibles "
            "(filtrables par secteur ou recherche).",
            "Cliquez une cible pour ouvrir sa fiche : prix, EBITDA, multiple d'entrée, "
            "profil de risque.",
            "Réglez le LEVIER : le curseur « dette / EV » fixe la part de la transaction "
            "financée par dette plutôt que par votre cash (jusqu'à un plafond).",
            "Cliquez ACQUÉRIR : votre cash finance la part en fonds propres (equity), le "
            "reste est de la dette portée par la société acquise.",
            "Suivez vos acquisitions dans l'onglet PORTEFEUILLE : valeur courante, dette "
            "restante, dividendes perçus.",
            "Quand le moment est bon, cliquez CÉDER (EXIT) sur la fiche de la cible pour "
            "revendre la société et encaisser la plus-value (ou la perte).",
        ],
        "concept": "C'est le principe du LBO (Leveraged Buy-Out) : plus la part financée par "
                   "DETTE est grande, plus votre mise en fonds propres (equity) est petite — "
                   "et donc plus le MOIC (Multiple On Invested Capital, gain ÷ mise initiale) "
                   "est AMPLIFIÉ si la sortie se fait à un multiple supérieur à l'entrée. "
                   "Mais le levier amplifie aussi les PERTES si l'EBITDA de la cible se "
                   "dégrade ou si le multiple de sortie est inférieur à celui d'entrée — la "
                   "dette, elle, doit être remboursée quoi qu'il arrive. Voir les leçons "
                   "Académie « LBO » et « Accretion/Dilution » pour la mécanique chiffrée.",
    },
]

_BY_ID = {t["id"]: t for t in TUTORIALS}


def get(tid):
    return _BY_ID.get(tid)
