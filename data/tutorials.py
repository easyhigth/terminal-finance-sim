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
        "id": "swaps",
        "title": "Swaps de devises : échanger un différentiel de taux",
        "image": "swaps.png",
        "intro": "Le DESK SWAPS échange le différentiel de taux d'intérêt entre votre "
                 "devise domestique et une devise étrangère, sans jamais échanger le "
                 "principal (le notionnel n'est qu'une référence de calcul). Ouvert "
                 "avec SWAP ou SWAPS.",
        "steps": [
            "Ouvrez le desk : SWAP — choisissez une DEVISE ÉTRANGÈRE parmi les "
            "régions disponibles (toutes sauf la vôtre).",
            "Choisissez le SENS : « Reçoit taux étranger / Paie taux domestique » "
            "si vous pensez que le taux étranger restera plus élevé, ou l'inverse "
            "si vous pensez que c'est votre taux domestique qui rapportera plus.",
            "Fixez la MATURITÉ (2, 3 ou 5 ans) et le NOTIONNEL (+/- par paliers de "
            "100k) : ce notionnel sert uniquement à calculer les flux, il n'est "
            "jamais débité de votre cash à l'entrée.",
            "Cliquez CONCLURE LE SWAP : à chaque tour jusqu'à l'échéance, le "
            "différentiel de taux net (jambe reçue moins jambe payée) est réglé "
            "en cash — positif s'il joue en votre faveur, négatif sinon.",
            "Suivez vos positions dans « Vos swaps » : carry annuel estimé et "
            "temps restant avant expiration, où le swap s'arrête sans autre "
            "règlement.",
        ],
        "concept": "Un swap de devises ne transfère jamais le principal : seul le "
                   "différentiel de taux entre les deux jambes (domestique et "
                   "étrangère) est réglé net, comme un vrai cross-currency swap "
                   "simplifié. Le taux régional réutilise celui des obligations "
                   "souveraines (taux directeur + prime de crédit du pays) : "
                   "conclure un swap revient donc à un PARI SUR L'ÉCART DE TAUX "
                   "entre deux zones, sans exposition directe au taux de change ni "
                   "au marché actions. Le risque : si l'écart de taux évolue contre "
                   "votre position pendant la durée du swap, le carry négatif "
                   "s'accumule à chaque tour jusqu'à l'échéance.",
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
    {
        "id": "hedge",
        "title": "Couverture : acheter un put protecteur",
        "image": "hedge.png",
        "intro": "Le DESK DE COUVERTURE permet d'acheter un PUT sur l'indice phare de "
                 "votre région pour réduire le bêta net de votre portefeuille sans "
                 "vendre vos positions. Ouvert avec PROTECT.",
        "steps": [
            "Ouvrez le desk : PROTECT — choisissez un STRIKE (100% = à la monnaie, "
            "95% ou 90% = hors la monnaie, donc moins cher mais protège plus tard).",
            "Choisissez la MATURITÉ (3, 6 ou 12 mois) : plus elle est longue, plus "
            "la prime est élevée (plus de temps pour que l'indice baisse).",
            "La PRIME affichée est débitée immédiatement de votre cash lors de "
            "l'achat — c'est le coût de l'assurance, perdu si l'indice ne baisse "
            "pas sous le strike à l'échéance.",
            "Cliquez SOUSCRIRE : la couverture est notionnelle (un montant de "
            "référence), pas une vente réelle de vos positions.",
            "À l'échéance, si l'indice termine sous le strike, le put paie la "
            "différence proportionnelle au notionnel, compensant une partie des "
            "pertes de votre book ; sinon il expire sans valeur.",
            "Onglet PAIRE (position) : couvre une position PRÉCISE (pas tout le "
            "book) en shortant un titre corrélé — l'app calcule le ratio de "
            "couverture min-variance et dimensionne le short pour vous.",
        ],
        "concept": "Un put protecteur (protective put) est l'assurance la plus "
                   "classique d'un portefeuille actions : on paie une PRIME "
                   "(calculée par Black-Scholes, comme toute option) pour avoir le "
                   "droit de vendre l'indice au STRIKE à l'échéance, quel que soit "
                   "son niveau réel. Plus le strike est proche du niveau courant, "
                   "plus la protection est large mais plus la prime est chère. "
                   "C'est un compromis : on accepte un coût certain (la prime) pour "
                   "limiter une perte incertaine, sans toucher à ses positions "
                   "sous-jacentes.",
    },
    {
        "id": "options",
        "title": "Options sur actions : calls et puts",
        "image": "options.png",
        "intro": "Le DESK D'OPTIONS permet d'acheter des CALLS (pari à la hausse) ou "
                 "des PUTS (pari à la baisse) sur une action individuelle de votre "
                 "watchlist ou portefeuille. Ouvert avec OPTIONS.",
        "steps": [
            "Ouvrez le desk : OPTIONS — choisissez un titre (watchlist ou "
            "portefeuille).",
            "Choisissez CALL (vous gagnez si l'action monte au-dessus du strike) "
            "ou PUT (vous gagnez si elle baisse sous le strike).",
            "Choisissez le STRIKE (90%, 100% ou 110% du cours actuel) et la "
            "MATURITÉ (3, 6 ou 12 mois).",
            "La PRIME affichée (calculée par Black-Scholes) est débitée "
            "immédiatement — c'est votre mise maximale, votre perte est limitée "
            "à ce montant.",
            "Choisissez le nombre de CONTRATS puis cliquez ACHETER. À l'échéance, "
            "le contrat est réglé automatiquement : payoff intrinsèque crédité en "
            "cash, ou zéro s'il termine hors la monnaie.",
        ],
        "concept": "Une option donne le droit (pas l'obligation) d'acheter (call) "
                   "ou de vendre (put) un actif à un prix fixé (le strike) à une "
                   "échéance donnée. Son prix (la prime) dépend du cours actuel, "
                   "du strike, du temps restant et de la volatilité du titre "
                   "(modèle de Black-Scholes). Contrairement à une position "
                   "actions classique, la perte est plafonnée à la prime payée, "
                   "mais le gain potentiel d'un call est illimité — c'est un "
                   "effet de levier asymétrique.",
    },
    {
        "id": "ipo",
        "title": "IPO : souscrire à une introduction en bourse",
        "image": "ipo.png",
        "intro": "Le DESK D'IPO liste les sociétés qui s'apprêtent à entrer en "
                 "bourse. Vous pouvez souscrire avant la cotation, sans connaître "
                 "le prix final définitif. Ouvert avec IPO.",
        "steps": [
            "Ouvrez le desk : IPO — consultez les offres en cours (fourchette de "
            "prix indicative, sursouscription estimée, sentiment de marché).",
            "Choisissez un montant à investir puis cliquez SOUSCRIRE : le cash "
            "est débité immédiatement, au prix bas de la fourchette (prix "
            "d'introduction de référence).",
            "Si la sursouscription estimée est élevée, votre allocation réelle "
            "est réduite proportionnellement (le surplus non alloué vous est "
            "remboursé tout de suite) : forte demande = moins d'actions par "
            "euro investi.",
            "À la date de cotation, le prix définitif est tiré (influencé par le "
            "sentiment de marché annoncé) : vos actions sont créditées à ce "
            "prix, le solde (gain ou perte vs votre mise) ajusté en cash.",
            "Vous pouvez aussi DÉCLINER une offre pour récupérer votre droit de "
            "souscrire à une autre.",
        ],
        "concept": "Une introduction en bourse (IPO) permet de souscrire des "
                   "actions avant qu'elles ne soient cotées publiquement, "
                   "généralement à un prix décoté pour attirer les investisseurs. "
                   "Le \"pop\" (variation entre le prix de souscription et le "
                   "premier cours coté) peut être positif ou négatif : c'est un "
                   "pari sur l'appétit du marché au moment de la cotation, "
                   "distinct de l'analyse fondamentale classique.",
    },
    {
        "id": "fx",
        "title": "Desk FX : spot et forward sur devises",
        "image": "fx.png",
        "intro": "Le DESK FX permet de prendre position sur des paires de devises "
                 "majeures, en SPOT (position ouverte/fermée librement) ou en "
                 "FORWARD (verrouillée à l'avance, réglée à échéance). Ouvert "
                 "avec FX.",
        "steps": [
            "Ouvrez le desk : FX — choisissez une paire (ex. EUR/USD) et une "
            "direction : LONG (vous gagnez si la devise de base monte) ou "
            "SHORT (vous gagnez si elle baisse).",
            "En SPOT : aucun cash débité à l'ouverture (position notionnelle, "
            "comme une couverture) — le P&L latent suit l'écart entre le taux "
            "courant et le taux d'entrée ; fermez quand vous le souhaitez pour "
            "réaliser le P&L en cash.",
            "En FORWARD : choisissez une maturité (1, 3 ou 6 mois) — le taux "
            "est verrouillé immédiatement, sans débit de cash, et le contrat se "
            "règle automatiquement à l'échéance selon le taux final.",
            "Le FORWARD nécessite un grade plus élevé que le SPOT — la "
            "certification ACI (desk de change) réduit cette exigence.",
        ],
        "concept": "Une position FX SPOT est un pari direct sur le taux de "
                   "change courant, sans levier formel ni débit de cash "
                   "immédiat (le notionnel n'est qu'une référence de calcul). "
                   "Un FORWARD verrouille aujourd'hui un taux pour une date "
                   "future : c'est l'outil de couverture de change classique "
                   "des entreprises exportatrices, mais aussi un instrument "
                   "spéculatif si la direction prise diverge du taux réalisé.",
    },
    {
        "id": "calendar",
        "title": "Calendrier macro : paris sur évènements programmés",
        "image": "calendar.png",
        "intro": "Le CALENDRIER MACRO annonce à l'avance des évènements "
                 "économiques (décision de banque centrale, inflation, "
                 "emploi...) sur lesquels vous pouvez parier une issue avant "
                 "leur résolution. Ouvert avec AGENDA.",
        "steps": [
            "Ouvrez l'agenda : AGENDA — consultez les évènements programmés "
            "(type, nombre de pas restants, probabilités a priori de chaque "
            "issue : positif/neutre/négatif).",
            "Choisissez une issue et une mise : le cash est débité "
            "immédiatement.",
            "Le multiplicateur de gain dépend de la probabilité a priori de "
            "l'issue choisie (plus elle est rare, plus le multiplicateur est "
            "élevé, plafonné).",
            "À la résolution, l'issue réelle est tirée : si elle correspond à "
            "votre pari, le gain (mise × multiplicateur) est crédité ; sinon "
            "la mise est perdue.",
        ],
        "concept": "Ce calendrier est un marché de paris autonome : il ne "
                   "modifie pas le marché réel, il ne fait que matérialiser un "
                   "pari sur l'anticipation collective d'un évènement "
                   "macroéconomique. Le multiplicateur inversement "
                   "proportionnel à la probabilité a priori reproduit la "
                   "logique d'une cote de bookmaker : plus l'issue est "
                   "surprenante, plus elle paie — mais plus elle est rare.",
    },
    {
        "id": "team",
        "title": "Équipe : recruter des analystes juniors",
        "image": "team.png",
        "intro": "À partir d'un grade avancé, vous pouvez monter une petite "
                 "équipe d'analystes juniors : un coût récurrent par tour en "
                 "échange d'un bonus passif (réputation, probabilité d'offre "
                 "de deal). Ouvert avec TEAM.",
        "steps": [
            "Ouvrez l'écran : TEAM — consultez le catalogue de profils "
            "(actions, crédit, quant, macro), chacun avec un coût "
            "d'embauche ponctuel et un coût récurrent par tour.",
            "Embauchez un profil qui vous intéresse : le coût ponctuel est "
            "débité immédiatement, le coût récurrent s'ajoute ensuite à vos "
            "charges à chaque tour.",
            "Chaque analyste apporte un effet passif simple selon son "
            "profil : un peu de réputation par tour, et/ou une probabilité "
            "légèrement accrue de nouvelles offres de deal.",
            "Licenciez un analyste à tout moment si son coût récurrent "
            "devient trop lourd pour le bénéfice qu'il apporte.",
        ],
        "concept": "Une équipe transforme une partie de votre trésorerie "
                   "récurrente en effets passifs cumulés — un calcul "
                   "classique de gestion : le coût fixe doit être justifié "
                   "par un gain marginal (réputation, deal-flow) qui dépasse "
                   "sa charge dans la durée.",
    },
    {
        "id": "stresstest",
        "title": "Stress test réglementaire",
        "image": "stresstest.png",
        "intro": "Périodiquement (environ tous les deux trimestres), un "
                 "superviseur fictif teste la résistance de votre "
                 "portefeuille réel à un scénario de choc tiré au hasard. "
                 "Ouvert avec STRESS quand un test est en attente.",
        "steps": [
            "Le scénario imposé (krach actions, choc de taux, choc de "
            "volatilité, récession) est appliqué instantanément à votre "
            "book pour estimer une perte simulée.",
            "Le verdict dépend du ratio perte/valeur nette : au-delà du "
            "seuil de tolérance, le test est jugé échoué.",
            "Répondez : « Prendre acte » (aucun coût immédiat, mais "
            "sanction de réputation en cas d'échec) ou « Renforcer la "
            "couverture immédiatement » (coût symbolique de couverture, "
            "mais sanction atténuée).",
        ],
        "concept": "Ce stress test reprend le calcul de choc instantané du "
                   "module RISK (VaR/CVaR, exposition) appliqué à votre "
                   "portefeuille réel — une mise en situation du contrôle "
                   "réglementaire qui encadre toute salle de marché : la "
                   "résistance aux scénarios extrêmes compte autant que la "
                   "performance courante.",
    },
    {
        "id": "history",
        "title": "Historique de carrière",
        "image": "history.png",
        "intro": "Un écran consultable à tout moment (pas seulement en fin "
                 "de partie) retraçant l'évolution de votre valeur nette et "
                 "les jalons clés de votre carrière. Ouvert avec TIMELINE.",
        "steps": [
            "Le graphique trace votre valeur nette (cash + positions) au "
            "fil des derniers tours.",
            "La timeline liste vos jalons de carrière (promotions, "
            "certifications, deals marquants...) du plus récent au plus "
            "ancien.",
        ],
        "concept": "Revoir sa trajectoire aide à juger ses décisions a "
                   "posteriori — un réflexe utile pour distinguer la chance "
                   "(un marché porteur) de la compétence (une vraie gestion "
                   "du risque) dans la performance affichée.",
    },
    # ---------------------------------------------------------- outils quant
    {
        "id": "sharpe",
        "title": "Sharpe Ratio : votre performance ajustée au risque",
        "image": "sharpe.png",
        "intro": "Deux portefeuilles avec le même rendement ne se valent pas si l'un "
                 "a pris deux fois plus de risque. L'app SHARPE compare votre book "
                 "réel au benchmark régional et à des allocations de référence.",
        "steps": [
            "Ouvrez l'icône « Sharpe Ratio » du bureau : les tuiles du haut donnent "
            "votre Sharpe annualisé, rendement, volatilité, bêta et alpha de Jensen "
            "vs l'indice de votre région.",
            "Choisissez la période (3M/1A/3A/5A) et le taux sans risque (boutons "
            "−/+) pour voir comment le ratio réagit.",
            "Le graphique COMPARAISON place votre portefeuille à côté du "
            "benchmark, du portefeuille à variance minimale et du portefeuille à "
            "Sharpe maximal (calculés sur le même univers).",
            "La courbe SHARPE GLISSANT montre si votre ratio s'améliore ou se "
            "dégrade dans le temps — pas juste un chiffre figé.",
            "La table PAR POSITION détaille rendement/volatilité/Sharpe de chaque "
            "ligne : repérez celles qui tirent la performance vers le bas.",
            "Bouton « → FRONTIÈRE » : bascule directement vers l'app Frontière "
            "efficiente pour agir sur ce que vous venez de lire.",
        ],
        "concept": "Sharpe = (rendement − taux sans risque) / volatilité, "
                   "annualisé. Un Sharpe élevé signifie un bon rendement PAR UNITÉ "
                   "de risque prise, pas juste un gros rendement brut — un "
                   "portefeuille très risqué peut avoir un rendement flatteur et "
                   "un Sharpe médiocre. L'alpha de Jensen isole ce qui reste une "
                   "fois le bêta de marché retiré : le « vrai » talent, si non nul.",
    },
    {
        "id": "zscore",
        "title": "Z-Score : à combien d'écarts-types de la norme ?",
        "image": "zscore.png",
        "intro": "Le z-score mesure à quel point une valeur s'écarte de son "
                 "comportement RÉCENT — un signal statistique de retour à la "
                 "moyenne ou d'anomalie, sur le prix, le rendement, la volatilité "
                 "ou la corrélation.",
        "steps": [
            "Choisissez un titre par chip (vos positions et votre watchlist "
            "apparaissent en premier) ou tapez un ticker dans « Autre ticker… ».",
            "Sélectionnez la LECTURE : PRIX (z du cours vs sa moyenne mobile), "
            "RENDEMENT (choc inhabituel au dernier pas), VOLATILITÉ (régime de vol "
            "anormal) ou CORRÉLATION (décorrélation inhabituelle vs l'indice).",
            "La grande valeur « z = … » donne le verdict : au-delà de ±2σ, "
            "l'écart est statistiquement rare.",
            "La courbe trace le z-score DANS LE TEMPS avec des bandes ±1σ/±2σ — "
            "regardez si les excursions passées sont revenues vers zéro.",
            "Boutons TRADER / ALERTE : agissez directement sur le signal sans "
            "ressaisir le ticker ailleurs.",
        ],
        "concept": "Un z-score extrême ne dit pas QUOI FAIRE tout seul : sur un "
                   "prix, un z très négatif peut être une occasion (retour à la "
                   "moyenne) ou le début d'une vraie tendance baissière (la "
                   "moyenne elle-même a changé). Croisez toujours avec la "
                   "fiche société avant d'agir sur le seul chiffre.",
    },
    {
        "id": "frontier",
        "title": "Frontière efficiente : optimiser PUIS exécuter",
        "image": "frontier.png",
        "intro": "La frontière efficiente trace, pour chaque niveau de risque, le "
                 "MEILLEUR rendement atteignable avec un panier de titres donné — "
                 "et ici, contrairement à un cours de finance, on peut cliquer "
                 "dessus pour passer les ordres réels.",
        "steps": [
            "Cochez l'univers (colonne de gauche) : vos positions détenues sont "
            "marquées ✶ et cochées par défaut.",
            "La courbe à droite montre le couple rendement/risque annualisés de "
            "chaque combinaison de poids possible, avec MIN VAR et MAX SHARPE "
            "repérés.",
            "Cliquez un point de la courbe (ou les boutons MIN VAR / MAX SHARPE) "
            "pour le choisir comme CIBLE — votre point ACTUEL est aussi affiché "
            "pour comparaison.",
            "Le panneau du bas traduit la cible en poids ACTUELS → CIBLES et en "
            "une LISTE D'ORDRES précise (achats/ventes en quantités entières).",
            "APPLIQUER passe ces ordres réellement (frais et impact de marché du "
            "jeu inclus), après une confirmation.",
        ],
        "concept": "La frontière efficiente illustre la diversification : "
                   "combiner des titres pas parfaitement corrélés réduit le "
                   "risque total sans forcément sacrifier le rendement. MIN VAR "
                   "minimise la volatilité, MAX SHARPE maximise le rendement par "
                   "unité de risque — deux objectifs différents, pas toujours au "
                   "même endroit sur la courbe.",
    },
    # -------------------------------------------------------- salle des marchés
    {
        "id": "greeks",
        "title": "Desk Options : stratégies, modèles, grecques",
        "image": "greeks.png",
        "intro": "Le Desk Options a trois onglets : construire une STRATÉGIE "
                 "(paquet d'options), comparer les MODÈLES de pricing, et suivre "
                 "les GRECQUES de tout votre book.",
        "steps": [
            "Choisissez un titre puis une STRATÉGIE (call/put sec, straddle, "
            "strangle, put protecteur) — jamais de vente à découvert d'option, "
            "seulement des achats.",
            "Réglez la maturité et le nombre de contrats ; le graphique montre le "
            "P&L À L'ÉCHÉANCE vs le cours final, avec le point mort marqué.",
            "Le panneau de droite détaille la prime totale et les grecques du "
            "paquet : Δ (delta, exposition directionnelle), Γ (gamma), v (vega, "
            "P&L pour +1 point de vol) et θ (theta, coût du temps par jour).",
            "Onglet MODÈLES : la MÊME option pricée sous Black-Scholes, binomial "
            "CRR, Monte-Carlo, Merton à sauts et vol implicite — pour voir où ils "
            "divergent (options américaines, marchés à sauts).",
            "Onglet BOOK : toutes vos options en cours, réévaluées au marché du "
            "jour, avec l'edge de vol (implicite payée vs réalisée depuis "
            "l'achat).",
        ],
        "concept": "Un call ou un put seul PARIE sur une direction ; un straddle "
                   "ou un strangle PARIENT sur la VOLATILITÉ (gagnent si le titre "
                   "bouge beaucoup, dans un sens ou l'autre) ; un put protecteur "
                   "ASSURE une position détenue. Le theta est le loyer que vous "
                   "payez chaque jour pour détenir de l'optionalité — il faut que "
                   "le mouvement (ou le gamma) le rembourse.",
    },
    {
        "id": "vardesk",
        "title": "Risque : VaR, CVaR, contributions, backtest",
        "image": "vardesk.png",
        "intro": "La VaR (Value at Risk) répond à : « quelle perte, au pire, avec "
                 "95% (ou 99%) de confiance, sur le prochain pas ? ». Ce desk la "
                 "calcule sur VOTRE book réel et vérifie qu'elle est fiable.",
        "steps": [
            "Choisissez le niveau de confiance (95% ou 99%) : les tuiles du haut "
            "donnent VaR, CVaR (perte moyenne AU-DELÀ de la VaR), la VaR "
            "paramétrique et l'écart-type du P&L simulé.",
            "L'histogramme DISTRIBUTION SIMULÉE montre la forme de vos pertes/gains "
            "possibles ; les barres rouges sont la QUEUE au-delà de la VaR.",
            "VAR PAR POSITION (allocation d'Euler) : la contribution de CHAQUE "
            "ligne à la VaR totale — une contribution NÉGATIVE est une "
            "couverture qui réduit le risque global.",
            "BACKTEST DE KUPIEC : compare le nombre d'exceptions (jours où la "
            "perte a dépassé la VaR annoncée) observées vs attendues — un modèle "
            "« NON rejeté » est bien calibré.",
            "Bouton « STRESS TEST » : bascule vers des scénarios de choc "
            "extrêmes, complémentaires à la VaR (qui suppose un monde « normal »).",
        ],
        "concept": "La VaR ne dit rien sur l'ampleur d'une perte AU-DELÀ du seuil "
                   "— c'est le rôle de la CVaR. L'allocation d'Euler est la seule "
                   "façon mathématiquement cohérente de décomposer une VaR par "
                   "ligne : les contributions SOMMENT exactement au total, contrairement "
                   "à une simple pondération par la taille de position.",
    },
    {
        "id": "rates",
        "title": "Desk Taux : courbe, duration, DV01, chocs",
        "image": "rates.png",
        "intro": "Le Desk Taux couvre la courbe des taux souveraine, votre book "
                 "obligataire (duration/DV01/convexité), les futures sur matières "
                 "premières et vos swaps de taux (IRS).",
        "steps": [
            "Onglet TAUX : la courbe des rendements souverains par maturité — "
            "pentue (normale), plate ou inversée (signal de récession).",
            "CHOCS DE COURBE simule des variations de taux (parallèle, "
            "pentification, aplatissement) et montre le P&L de VOTRE book, "
            "duration ET convexité incluses.",
            "BOOK OBLIGATAIRE (à droite) : chaque ligne avec sa duration "
            "modifiée, sa convexité et son DV01 — le P&L d'une hausse d'1 point "
            "de base.",
            "Boutons RACCOURCIR / ALLONGER : font tourner le book vers des "
            "maturités plus courtes ou longues à DV01 constant (le jeu ne "
            "shorte pas d'obligation — on déplace le risque, pas on le crée).",
            "Onglets FUTURES/IMMUNISATION/SWAPS (IRS) : courbes à terme des "
            "matières premières, appariement duration = horizon d'un passif, et "
            "couverture du DV01 du book par un swap payeur/receveur.",
        ],
        "concept": "DV01 (Dollar Value of 01) est l'unité de compte d'un desk de "
                   "taux : P&L ≈ valeur × duration × 0,0001 pour +1 point de "
                   "base. La CONVEXITÉ adoucit les chocs de taux — une hausse "
                   "fait perdre légèrement MOINS que ce que la duration seule "
                   "prédit, et une baisse fait gagner légèrement PLUS.",
    },
    {
        "id": "attribution",
        "title": "Attribution de performance : bon ou chanceux ?",
        "image": "attribution.png",
        "intro": "Vous battez le marché — mais est-ce parce que vous avez bien "
                 "choisi vos SECTEURS, bien choisi vos TITRES dedans, ou juste eu "
                 "de la chance sur des paris factoriels ?",
        "steps": [
            "Onglet BRINSON : l'écart total (VOUS − MARCHÉ) se décompose en "
            "ALLOCATION (avoir surpondéré les bons secteurs) + SÉLECTION (avoir "
            "choisi les bons titres dedans) + interaction — les trois SOMMENT "
            "exactement à l'écart total.",
            "Le tableau par secteur détaille poids et rendement vous/marché, "
            "avec la contribution allocation et sélection de chacun.",
            "Onglet FACTEURS : régression de votre rendement sur des facteurs "
            "observables (monde, secteur, région) — bêtas, ALPHA annualisé et R².",
            "Un R² très élevé avec un alpha proche de zéro signifie que votre "
            "P&L n'est QUE des paris factoriels (« closet tracker ») — pas de "
            "sélection de titres mesurable.",
        ],
        "concept": "L'allocation récompense d'avoir été dans les bons secteurs "
                   "AVANT qu'ils performent ; la sélection récompense d'avoir "
                   "choisi les bonnes lignes DANS un secteur donné. Un gérant "
                   "peut avoir une bonne allocation et une mauvaise sélection (ou "
                   "l'inverse) — les deux compétences sont différentes.",
    },
    {
        "id": "pairs",
        "title": "Pairs Trading : arbitrage statistique",
        "image": "pairs.png",
        "intro": "Deux titres COINTÉGRÉS forment un élastique : leur écart de "
                 "prix (le spread) oscille autour de zéro. On vend l'écart quand "
                 "il est tendu, on encaisse quand il revient.",
        "steps": [
            "Le SCANNER liste les paires les plus cointégrées du roster (triées "
            "par statistique ADF) — plus ADF est négatif, plus la cointégration "
            "est forte.",
            "Cliquez une paire : le graphique trace le SPREAD (log-prix moins β "
            "fois l'autre log-prix) avec des bandes ±2σ d'entrée.",
            "Le panneau DIAGNOSTIC donne le β (ratio de couverture), l'ADF vs le "
            "seuil −3,0, la corrélation, le verdict COINTÉGRÉE/PAS et la "
            "half-life (temps typique de retour à la moyenne).",
            "z = z-score courant du spread : au-delà de ±2, un signal "
            "d'entrée ; proche de 0, un signal de sortie.",
            "Choisissez un notionnel et EXÉCUTER LA PAIRE : ouvre long un titre "
            "/ short l'autre, dimensionné par le β.",
        ],
        "concept": "Une forte CORRÉLATION ne suffit pas — deux titres corrélés "
                   "peuvent dériver l'un de l'autre indéfiniment. La "
                   "COINTÉGRATION (test d'Engle-Granger : le RÉSIDU de la "
                   "régression des log-prix est stationnaire) garantit que "
                   "l'écart revient, statistiquement, vers sa moyenne — la vraie "
                   "condition pour que la stratégie fonctionne.",
    },
    {
        "id": "creditdesk",
        "title": "Desk Crédit : Merton, CDS, convertibles, titrisation",
        "image": "creditdesk.png",
        "intro": "Le risque de crédit d'une entreprise se voit dans SES ACTIONS : "
                 "le modèle de Merton les traite comme une option sur ses actifs. "
                 "Ce desk en tire probabilité de défaut, CDS, convertibles et "
                 "titrisation.",
        "steps": [
            "Onglet MERTON : le SCANNER classe le roster par PD (probabilité de "
            "défaut) décroissante — cliquez une société pour voir le détail "
            "(actifs, levier, distance au défaut, spread implicite).",
            "Le graphique du bas montre comment la PD réagit à un choc sur le "
            "cours de l'action — le lien direct entre actions et crédit.",
            "Onglet CDS : achetez une protection (payez une prime courue chaque "
            "pas) — son mark-to-market bouge avec le spread ; un évènement de "
            "crédit (action sous 25% de son niveau d'entrée) déclenche le "
            "paiement.",
            "Onglet CONVERTIBLES : le prix se décompose en plancher obligataire "
            "+ valeur d'option — participe à la hausse, protège à la baisse.",
            "Onglet WATERFALL : glissez le curseur de perte du pool titrisé pour "
            "voir la cascade equity → mezzanine → senior s'activer.",
        ],
        "concept": "Merton : à l'échéance, les actionnaires reçoivent max(0, "
                   "actifs − dette) — exactement le payoff d'un CALL sur les "
                   "actifs, strike = la dette. D'où PD = N(−distance au défaut). "
                   "Un CDS ne parie pas sur LE défaut lui-même mais sur la PEUR "
                   "du défaut : son prix bouge bien avant qu'un défaut ne survienne.",
    },
    {
        "id": "crisislab",
        "title": "Labo de crise : réglez votre propre scénario",
        "image": "crisislab.png",
        "intro": "Plutôt que d'attendre une vraie crise, réglez vous-même "
                 "l'ampleur d'un krach actions et d'un choc de taux, et voyez "
                 "IMMÉDIATEMENT l'impact sur chacune de vos positions.",
        "steps": [
            "Glissez les curseurs ACTIONS (jusqu'à −40%) et TAUX (jusqu'à "
            "+300 bp) — le P&L du scénario se met à jour en direct.",
            "La table RÉÉVALUATION LIGNE PAR LIGNE réévalue chaque position "
            "(actions au bêta, obligations en duration+convexité, options et "
            "puts de couverture re-pricés Black-Scholes) — vos puts de "
            "couverture doivent apparaître en VERT (ils gagnent au krach).",
            "Cochez « CORRÉLATIONS → 1 » : simule le moment où, en vraie crise, "
            "tout chute ENSEMBLE (la diversification cesse de protéger) — "
            "comparez le P&L avec et sans.",
            "L'écart entre les deux est le « coût de l'illusion de "
            "diversification » : ce que votre diversification apparente vous "
            "coûterait si elle disparaissait précisément quand vous en avez "
            "besoin.",
        ],
        "concept": "En temps normal, les corrélations entre titres sont "
                   "MODÉRÉES — c'est ce qui rend la diversification efficace. En "
                   "crise systémique, les corrélations montent souvent vers 1 : "
                   "tout baisse en même temps, et un portefeuille qui semblait "
                   "diversifié se comporte comme une seule grosse position.",
    },
    {
        "id": "valuation",
        "title": "Valorisation : DCF, CAPM, pont LBO",
        "image": "valuation.png",
        "intro": "Le cours d'une action est-il justifié par ses fondamentaux ? "
                 "Le DCF actualise les flux de trésorerie futurs pour estimer une "
                 "valeur intrinsèque, indépendante du sentiment de marché.",
        "steps": [
            "Onglet DCF : choisissez une société — le prix par action calculé "
            "s'affiche en grand, comparé au cours réel avec le verdict "
            "SOUS-ÉVALUÉE / SURÉVALUÉE / proche du cours.",
            "Le détail montre le FCF de départ, la croissance explicite sur "
            "5 ans, la valeur actuelle des flux ET de la valeur terminale — "
            "regardez quelle part de l'EV vient de la valeur terminale (souvent "
            "la majorité, donc la plus incertaine).",
            "Réglez WACC et g∞ (croissance perpétuelle) avec les boutons −/+ : "
            "la table de SENSIBILITÉ à droite montre la valeur par action pour "
            "chaque combinaison, avec un cadre blanc sur les cases compatibles "
            "avec le cours actuel.",
            "Onglet SML (CAPM) : place chaque société sur la droite de marché "
            "rendement attendu vs bêta — l'écart à la droite est un alpha.",
            "Onglet PONT LBO : décompose un gain de fonds propres en croissance "
            "+ expansion de multiple + désendettement, à somme exacte.",
        ],
        "concept": "Un DCF est aussi bon que ses hypothèses — WACC et croissance "
                   "perpétuelle (g∞) ont un effet DÉMESURÉ sur le résultat parce "
                   "que la valeur terminale domine souvent l'EV. La table de "
                   "sensibilité existe précisément pour ne jamais présenter un "
                   "chiffre unique comme une certitude.",
    },
    {
        "id": "fxdesk",
        "title": "Desk FX : carry trade & parité des taux",
        "image": "fxdesk.png",
        "intro": "Emprunter dans une devise à taux bas pour prêter dans une "
                 "devise à taux haut encaisse un différentiel quotidien (le "
                 "carry) — au risque d'un décrochage brutal de la paire.",
        "steps": [
            "La table liste les paires triées par |carry| : le taux de chaque "
            "devise, le carry annualisé d'une position longue, et les points de "
            "terme du forward 3 mois.",
            "Cliquez une paire : le panneau de droite affiche le carry, la "
            "volatilité de la paire et le ratio carry/vol (le portage "
            "compense-t-il le risque de décrochage ?).",
            "Choisissez un notionnel puis LONG (parie que le carry continue) ou "
            "SHORT (parie l'inverse) — la position accroît/couvre réellement "
            "votre exposition en devise.",
            "Le carry couru s'ajoute/se retranche de votre cash À CHAQUE PAS "
            "(un vrai revenu ou coût quotidien, pas juste à la clôture).",
        ],
        "concept": "Long la paire = long la devise de BASE : le carry, c'est "
                   "l'écart de taux directeur (r_base − r_cotée). Sans risque de "
                   "change, ce carry devrait disparaître (parité des taux "
                   "couverte) : les points de terme d'un forward compensent "
                   "presque exactement le différentiel — sinon, un arbitrage "
                   "sans risque existerait.",
    },
    {
        "id": "vollab",
        "title": "Labo de vol : GARCH, prévision, régimes",
        "image": "vollab.png",
        "intro": "La volatilité n'est pas constante : elle vient par GRAPPES "
                 "(des périodes calmes suivies de périodes agitées). Le GARCH la "
                 "modélise et la prévoit ; le filtre de régime infère l'état "
                 "caché du marché.",
        "steps": [
            "Onglet GARCH : choisissez un titre — la formule affiche α "
            "(réaction aux chocs récents) et β (mémoire des chocs anciens), et "
            "leur somme α+β mesure la PERSISTANCE de la volatilité.",
            "« Vol chère »/« Vol chère » : compare ce que le GARCH prévoit à ce "
            "que le desk d'options price actuellement dans ses primes.",
            "La courbe de prévision sur 12 pas CONVERGE vers le long terme à "
            "vitesse (α+β)^h — plus α+β est proche de 1, plus les chocs de vol "
            "durent longtemps.",
            "Onglet RÉGIMES : un filtre bayésien à 2 états infère P(stress) au "
            "fil du temps depuis les rendements observés SEULS, comparé à la "
            "vérité réelle du moteur (Expansion/Calme/Volatil/Récession).",
        ],
        "concept": "σ²(t) = ω + α·r²(t−1) + β·σ²(t−1) : la variance de demain "
                   "dépend du choc d'hier ET de la variance d'hier. Un régime "
                   "n'est pas qu'un jour agité isolé — le filtre bayésien exige "
                   "une COHÉRENCE dans le temps (transition collante à 0,95) "
                   "avant de déclarer un changement de régime.",
    },
    # ------------------------------------------------------------ financement
    {
        "id": "funding",
        "title": "Desk Financement : repo, prêt-titres, trésorerie",
        "image": "funding.png",
        "intro": "Trois façons de faire travailler votre bilan : emprunter contre "
                 "des obligations (repo), prêter vos actions détenues aux "
                 "vendeurs à découvert, ou placer le cash oisif.",
        "steps": [
            "Onglet REPO : choisissez un collatéral souverain et une quantité — "
            "vous ne payez que le HAIRCUT en cash, le reste est emprunté au taux "
            "repo (roulé chaque pas). Le CARRY DE L'EQUITY affiché est le "
            "rendement du collatéral moins le coût d'emprunt, amplifié par le "
            "levier implicite.",
            "En crise, haircut ET taux repo montent ensemble — un appel de "
            "marge peut liquider la position au pire moment (cf. LTCM/2008).",
            "Onglet PRÊT-TITRES : cochez « PRÊTER MES TITRES » pour toucher un "
            "revenu sur vos positions longues détenues (part prêteur 40% du "
            "taux de marché) — le tableau montre aussi ce que vous coûtent vos "
            "propres positions courtes en frais d'emprunt.",
            "Onglet TRÉSORERIE : activez le SWEEP (cash oisif au-delà d'un "
            "coussin, placé au jour le jour automatiquement) ou ouvrez un dépôt "
            "à terme (bloqué, mieux payé).",
        ],
        "concept": "Le repo est le levier obligataire classique : un petit "
                   "haircut (souvent 3-10%) permet de porter une position "
                   "obligataire bien plus grosse que le cash engagé. Une petite "
                   "capitalisation est « hard to borrow » (rare au prêt) — son "
                   "coût d'emprunt est élevé, ce qui renchérit la vente à "
                   "découvert dessus.",
    },
    {
        "id": "pnlexplain",
        "title": "P&L Explain : d'où vient chaque euro ?",
        "image": "pnlexplain.png",
        "intro": "Le rituel n°1 d'un desk réel : chaque matin, expliquer d'où "
                 "vient CHAQUE euro d'hier. Cette app décompose le mouvement de "
                 "votre patrimoine net du dernier pas.",
        "steps": [
            "La ligne du haut donne le Δ patrimoine total du dernier pas, en "
            "vert (gain) ou rouge (perte).",
            "Il se décompose en REVENUS PASSIFS (dividendes, coupons, carry FX, "
            "repo, prêt-titres, sweep, flux de dérivés — tout ce que le moteur "
            "a couru automatiquement) et PRIX & RESTE (vos positions qui "
            "bougent, salaire, frais, vos propres ordres).",
            "Le panneau EFFET PRIX DU POT ventile l'effet-prix par SECTEUR — "
            "quels secteurs ont tiré votre patrimoine vers le haut ou le bas ce "
            "pas-ci.",
            "En bas, la jauge BUDGET DE RISQUE DE LA FIRME montre votre VaR "
            "actuelle vs la limite imposée par votre grade — au-delà, "
            "avertissement puis réputation puis réduction forcée de votre plus "
            "grosse ligne après 5 pas de dépassement.",
        ],
        "concept": "Séparer les revenus PASSIFS (qui arrivent que vous tradiez "
                   "ou non) de l'effet PRIX (le vrai risque de marché pris) "
                   "évite de confondre un bon trimestre avec un simple "
                   "portage — un book qui ne gagne QUE du carry sans aucune "
                   "vraie conviction de prix est plus fragile qu'il n'y paraît.",
    },
    {
        "id": "backtester",
        "title": "Backtester : tester une stratégie sur l'historique réel",
        "image": "backtester.png",
        "intro": "Avant de risquer du cash réel, rejouez une règle de trading "
                 "MÉCANIQUE (pas d'IA) sur l'historique RÉEL d'un titre — "
                 "préhistoire de carrière (5 ans) incluse.",
        "steps": [
            "Choisissez un titre (chips positions/watchlist, ou recherche "
            "libre) puis une stratégie : Buy & hold, Croisement de moyennes "
            "mobiles, Momentum, ou Retour à la moyenne.",
            "Les tuiles comparent le rendement total de la stratégie à celui du "
            "simple Buy & hold, avec le Sharpe annualisé, le drawdown maximal et "
            "l'exposition moyenne au marché.",
            "La courbe de capital (base 1,0) trace comment 1€ investi aurait "
            "évolué avec cette règle, sur tout l'historique disponible.",
            "Changez de stratégie pour comparer — une stratégie qui bat le "
            "marché sur UN titre ne le bat pas forcément sur un autre.",
        ],
        "concept": "Chaque signal est décidé avec les données disponibles "
                   "JUSQU'AU pas courant SEULEMENT, puis appliqué au rendement "
                   "SUIVANT — aucun regard vers le futur (look-ahead bias), le "
                   "piège le plus commun d'un backtest mal construit. Un bon "
                   "résultat passé ne garantit jamais un résultat futur : c'est "
                   "un outil de jugement, pas une martingale.",
    },
]

_BY_ID = {t["id"]: t for t in TUTORIALS}


def get(tid):
    return _BY_ID.get(tid)
