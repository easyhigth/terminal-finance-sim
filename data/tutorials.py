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
        "title": "Obligations : revenu fixe & taux",
        "image": "bonds.png",
        "intro": "Les obligations versent un coupon régulier et remboursent le nominal "
                 "à l'échéance. Ouvrez le marché avec BONDS.",
        "steps": [
            "Affichez le marché obligataire : BONDS (ou le rail).",
            "Repérez l'identifiant (id), le YTM (rendement) et la duration de chaque ligne.",
            "Achetez : BUYBOND <id> <quantité>   ·   Vendez : SELLBOND <id> <qté>.",
            "Encaissez les coupons automatiquement à chaque pas de temps (ADV).",
        ],
        "concept": "Prix et taux varient en SENS INVERSE : si les taux montent, le prix "
                   "des obligations baisse — d'autant plus que la DURATION est longue. "
                   "Un rendement élevé (high yield) rémunère un risque de crédit plus fort.",
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
