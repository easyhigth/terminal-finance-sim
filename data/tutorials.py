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
    {
        "id": "crypto",
        "title": "Crypto-actifs & stablecoins",
        "image": "crypto.png",
        "intro": "Une classe d'actifs à part : pas de coupon ni de dividende, "
                 "uniquement une variation de prix — souvent très volatile. Ouvrez "
                 "le marché avec CRYPTO.",
        "steps": [
            "Affichez le marché : CRYPTO — chaque ligne montre le spot, la "
            "volatilité annualisée et le TYPE (Crypto, Stablecoin, CBDC).",
            "Une CRYPTO classique (type « Crypto ») n'a pas d'ancre : son prix peut "
            "doubler ou être divisé par deux sur l'année — lisez bien VOL/AN avant "
            "d'investir.",
            "Un STABLECOIN vise un prix fixe (souvent 1.0). S'il DÉCROCHE (depeg, "
            "marqué ⚠), son prix s'écarte de son ancre — un signal d'alerte, pas "
            "une opportunité de hausse.",
            "Une CBDC (monnaie numérique de banque centrale) verse un rendement "
            "régulier (+%/an affiché), proche d'un cash rémunéré : le profil le "
            "moins risqué de la classe.",
            "Achetez/vendez en cliquant +1/-1 sur chaque ligne, ou au clavier : "
            "BUYCRYPTO <id> <qté>   ·   SELLCRYPTO <id> <qté>.",
        ],
        "concept": "La volatilité (VOL/AN) est l'indicateur clé : une crypto à "
                   "80-150% de vol annuelle peut perdre la moitié de sa valeur en "
                   "quelques semaines, sans aucun flux (coupon/dividende) pour "
                   "compenser l'attente. Un DEPEG de stablecoin est un signal de "
                   "stress (perte de confiance, problème de réserve) : ne pas le "
                   "confondre avec une simple fluctuation — c'est souvent le signe "
                   "qu'il faut sortir, pas qu'il faut moyenner à la baisse.",
    },
    {
        "id": "credit",
        "title": "Titrisation : tranches & waterfall",
        "image": "credit.png",
        "intro": "Le desk crédit (CREDIT) titrise un pool de prêts en plusieurs "
                 "TRANCHES — equity, mezzanine, senior — qui absorbent les pertes "
                 "du pool dans un ordre précis : la « waterfall ».",
        "steps": [
            "Ouvrez le desk : CREDIT — chaque ligne est une tranche avec son "
            "ATTACHE-DÉTACHE, son COUPON et son RATING.",
            "ATTACHE-DÉTACHE définit la plage de pertes du pool que la tranche "
            "absorbe : ex. une tranche « 0%-5% » encaisse les 5 premiers points de "
            "pertes du pool, une tranche « 20%-100% » n'est touchée qu'au-delà de "
            "20% de pertes.",
            "La tranche EQUITY (attache 0%) paie le coupon le plus élevé car elle "
            "saute en PREMIER en cas de défauts — c'est la plus risquée.",
            "La tranche SENIOR (détache à 100%) paie le coupon le plus faible mais "
            "n'est touchée qu'en tout dernier — c'est la plus protégée (souvent "
            "notée AAA).",
            "Investissez : cliquez INVESTIR sur la tranche choisie. Le rendement "
            "réalisé dépend du taux de défaut du pool sur sa durée de vie.",
        ],
        "concept": "C'est le principe de la SUBORDINATION : les pertes du pool "
                   "remontent de bas en haut, des tranches les plus junior (equity) "
                   "vers les plus senior. Une PERTE ATTENDUE de 6% sur le pool ne "
                   "touche quasiment pas une tranche senior qui détache à 20%, mais "
                   "peut consommer l'intégralité d'une tranche equity de 5% "
                   "d'épaisseur. Choisir sa tranche, c'est choisir où se situer dans "
                   "la file d'attente des pertes — du rendement élevé et risqué "
                   "(equity) au rendement faible et protégé (senior).",
    },
    {
        "id": "alm",
        "title": "ALM : gestion actif-passif bancaire",
        "image": "alm.png",
        "intro": "Le desk ALM (ALM) simule le bilan d'une banque : masses et "
                 "durations de l'actif et du passif, puis l'impact d'un choc de "
                 "taux sur la marge d'intérêt (NII) et la valeur économique des "
                 "fonds propres (ΔEVE).",
        "steps": [
            "Ouvrez l'outil : ALM — ajustez les masses (Actifs/Passifs totaux) et "
            "les durations avec les boutons +/-.",
            "Le REPRICING GAP (1 an) = actifs sensibles au taux moins passifs "
            "sensibles au taux sur l'horizon d'un an. Un gap positif = la banque "
            "« asset-sensitive », elle gagne quand les taux montent.",
            "Le DURATION GAP compare la sensibilité-prix de l'actif à celle du "
            "passif, pondérées par leurs masses respectives.",
            "Appliquez un CHOC DE TAUX (boutons -200/-100/+100/+200 bps) et lisez "
            "Δ NII (impact sur la marge d'intérêt à 1 an) et Δ EVE (impact sur la "
            "valeur économique des fonds propres).",
            "Surveillez Δ EVE / fonds propres : au-delà d'environ 15-20%, le "
            "risque de taux du bilan est jugé excessif par les régulateurs "
            "(cf. Bâle III).",
        ],
        "concept": "Un GAP DE REPRICING positif et un DURATION GAP positif "
                   "racontent deux histoires complémentaires : à court terme (NII), "
                   "une hausse des taux profite à la banque si plus d'actifs que de "
                   "passifs se repricent vite. Mais à long terme (EVE), un duration "
                   "gap positif (actifs plus longs que les passifs) signifie que la "
                   "VALEUR de l'actif chute plus que celle du passif quand les taux "
                   "montent — c'est l'inverse du raisonnement NII. Une banque bien "
                   "gérée surveille les DEUX mesures : NII pour le court terme, EVE "
                   "pour la valeur économique long terme.",
    },
    {
        "id": "quant",
        "title": "Pricing d'options (Black-Scholes & Greeks)",
        "image": "quant.png",
        "intro": "Le module QUANT calcule en direct le prix Black-Scholes d'une "
                 "option call/put et ses Greeks (delta, gamma, vega, theta, rho) "
                 "à partir de 5 paramètres.",
        "steps": [
            "Ouvrez l'outil : QUANT — réglez Spot (S), Strike (K), Maturité (T), "
            "Taux (r) et Volatilité (σ) avec les boutons +/-.",
            "Basculez CALL/PUT avec le bouton TYPE pour comparer les deux profils.",
            "Lisez le PRIX affiché en gros : c'est la prime théorique de l'option "
            "selon Black-Scholes, comparée à la VALEUR INTRINSÈQUE sur le graphe "
            "« Prix vs Spot ».",
            "Les GREEKS mesurent la sensibilité du prix : Delta (variation du "
            "sous-jacent), Gamma (variation du delta), Vega (variation de la vol), "
            "Theta (érosion temporelle), Rho (variation du taux).",
            "Le diagramme de PAYOFF (en bas) montre le P&L net de prime à "
            "l'échéance : il révèle la perte maximale (la prime payée) pour un "
            "acheteur d'option.",
        ],
        "concept": "Augmenter la VOLATILITÉ (σ) augmente TOUJOURS le prix d'une "
                   "option (call ou put) : plus le sous-jacent peut bouger, plus "
                   "l'optionnalité a de la valeur — c'est ce que mesure Vega. À "
                   "l'inverse, le THETA est presque toujours négatif pour un "
                   "acheteur d'option : chaque jour qui passe sans mouvement du "
                   "sous-jacent érode la prime, surtout proche de l'échéance. Une "
                   "option proche de la monnaie (S ≈ K) a le GAMMA le plus élevé : "
                   "son delta change vite, donc son risque est le plus difficile à "
                   "couvrir dynamiquement.",
    },
    {
        "id": "risk",
        "title": "VaR, CVaR & stress tests",
        "image": "risk.png",
        "intro": "Le module RISK mesure le risque de votre portefeuille (ou d'un "
                 "book de démo) via la VaR, la CVaR et des scénarios de stress. "
                 "Ouvrez-le avec RISK.",
        "steps": [
            "Ouvrez l'outil : RISK — en MODE PORTEFEUILLE RÉEL, l'exposition vient "
            "de vos positions ; en MODE DÉMO, ajustez vous-même l'exposition par "
            "facteur (Equities, Rates, Credit, FX, Commodities).",
            "Choisissez un NIVEAU DE CONFIANCE (90/95/99%) : plus il est élevé, "
            "plus la VaR affichée est grande (on couvre une queue de distribution "
            "plus large).",
            "Lisez l'HISTOGRAMME : la zone rouge à gauche de la ligne VaR "
            "représente les pires scénarios simulés.",
            "Comparez VaR HISTORIQUE, VaR PARAMÉTRIQUE et CVaR : la CVaR (perte "
            "moyenne au-delà de la VaR) est toujours ≥ la VaR — elle capture la "
            "sévérité de la queue, pas seulement son seuil.",
            "Cliquez un SCÉNARIO DE STRESS (crise actions, choc de taux…) pour "
            "voir l'impact instantané sur votre book, décomposé par facteur.",
        ],
        "concept": "La VaR répond à « quelle perte ne devrait pas être dépassée "
                   "X% du temps ? » mais reste MUETTE sur l'ampleur au-delà de ce "
                   "seuil — deux portefeuilles peuvent avoir la même VaR 95% et des "
                   "pertes extrêmes radicalement différentes. La CVaR (Expected "
                   "Shortfall) comble ce trou en moyennant les pertes DANS la queue. "
                   "Les STRESS TESTS complètent l'approche statistique avec des "
                   "scénarios historiques ou hypothétiques extrêmes (krachs, chocs "
                   "de taux) que la distribution \"normale\" sous-estime souvent — "
                   "la VaR suppose un monde plus calme que la réalité ne l'est lors "
                   "des crises.",
    },
    {
        "id": "structured",
        "title": "Produits structurés : capital garanti, reverse convertible, autocall",
        "image": "structured.png",
        "intro": "Le DESK STRUCTURÉS vend des produits dont le gain final n'est pas "
                 "linéaire avec l'indice sous-jacent : il dépend de seuils, de "
                 "barrières et de l'échéance. Ouvrez-le avec STRUCT.",
        "steps": [
            "Ouvrez le catalogue : STRUCT — chaque produit a un nom, une "
            "description du payoff et une maturité fixe (en années).",
            "Le CAPITAL GARANTI rend le notionnel investi quoi qu'il arrive, "
            "plus une fraction de la hausse de l'indice : sécurité d'abord, "
            "performance ensuite.",
            "Le REVERSE CONVERTIBLE paie un coupon élevé fixe, mais si l'indice "
            "chute sous une barrière, le capital n'est PAS protégé : le coupon "
            "rémunère ce risque de baisse.",
            "L'AUTOCALLABLE peut être remboursé par anticipation (avant "
            "l'échéance) si l'indice dépasse un certain niveau à une date "
            "d'observation — sinon il continue jusqu'à l'échéance suivante.",
            "Souscrivez avec SOUSCRIRE (bouton dans le catalogue) ; le payoff "
            "n'est calculé qu'À L'ÉCHÉANCE, en fonction du niveau final de "
            "l'indice régional sous-jacent.",
        ],
        "concept": "Un produit structuré combine une obligation (ou un dépôt) "
                   "avec une ou plusieurs options pour façonner un profil de "
                   "gain non linéaire : capital protégé en échange d'un "
                   "potentiel de hausse plafonné, ou coupon élevé en échange "
                   "d'un risque de baisse non protégé. Il y a toujours un "
                   "ÉMETTEUR (la banque qui structure le produit) : son risque "
                   "de crédit s'ajoute au risque de marché — si l'émetteur "
                   "fait défaut, le produit ne vaut plus rien, indépendamment "
                   "de la performance de l'indice.",
    },
    {
        "id": "spreadsheet",
        "title": "Le tableur intégré : formules et modèle DCF",
        "image": "spreadsheet.png",
        "intro": "Le TABLEUR (type Excel) permet de construire vos propres "
                 "modèles financiers avec des formules. Un mini-DCF est "
                 "préchargé pour exemple. Ouvrez-le avec SHEET.",
        "steps": [
            "Ouvrez l'outil : SHEET — naviguez avec les flèches ou en cliquant "
            "une cellule ; la barre de formule affiche la référence (ex. B12).",
            "Appuyez sur ENTRÉE ou F2 pour éditer une cellule, ou tapez "
            "directement un caractère pour commencer à écrire.",
            "Une formule commence par = (ex. =B3/POWER(1+B5,2)) et peut "
            "référencer d'autres cellules ; SUM, NPV, IRR, POWER, IF sont "
            "disponibles.",
            "Le modèle préchargé calcule une Enterprise Value par DCF : B5 "
            "est le WACC, B6 la croissance terminale, B12 le résultat final.",
            "Modifiez B5 ou B6 et observez B12 se recalculer aussitôt — "
            "c'est l'intérêt d'un modèle : tester des hypothèses sans tout "
            "refaire à la main.",
        ],
        "concept": "Un modèle DCF (Discounted Cash Flow) valorise une "
                   "entreprise en actualisant ses flux de trésorerie futurs "
                   "au WACC (coût moyen pondéré du capital), puis en ajoutant "
                   "une VALEUR TERMINALE qui représente tous les flux après "
                   "l'horizon explicite (souvent via la formule de Gordon-"
                   "Growth : FCF×(1+g)/(WACC-g)). La valeur terminale domine "
                   "presque toujours le total — d'où la sensibilité extrême "
                   "du résultat au couple (WACC, croissance terminale).",
    },
]

_BY_ID = {t["id"]: t for t in TUTORIALS}


def get(tid):
    return _BY_ID.get(tid)
