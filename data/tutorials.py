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
        ],
        "concept": "Prix et taux varient en SENS INVERSE : si les taux montent, le prix "
                   "baisse — d'autant plus que la DURATION est longue. Le RENDEMENT se "
                   "décompose en : courbe (taux directeur) + prime de terme + spread de "
                   "CRÉDIT (rating) + prime de risque PAYS (souverains). Un événement "
                   "politique régional (cf. tutoriel Pays) élargit les spreads de la zone : "
                   "les prix des souverains ET des corporates de la région baissent, puis "
                   "se résorbent — une occasion d'acheter du rendement sur repli.",
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
]

_BY_ID = {t["id"]: t for t in TUTORIALS}


def get(tid):
    return _BY_ID.get(tid)
