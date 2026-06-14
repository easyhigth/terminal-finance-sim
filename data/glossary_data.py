"""
glossary_data.py — Données du glossaire financier.
Chaque entrée : terme -> (catégorie, définition).
Conçu pour être consulté in-game si le joueur a un doute.
"""

GLOSSARY = {
    # --- Valorisation -----------------------------------------------------
    "DCF": ("Valorisation",
        "Discounted Cash Flow. Méthode de valorisation qui actualise les flux "
        "de trésorerie futurs (FCF) à un taux (WACC) et y ajoute une valeur "
        "terminale pour estimer la valeur d'entreprise."),
    "WACC": ("Valorisation",
        "Weighted Average Cost of Capital. Coût moyen pondéré du capital "
        "(dette + fonds propres), net d'impôt sur la dette. Sert de taux "
        "d'actualisation dans un DCF."),
    "Valeur terminale": ("Valorisation",
        "Valeur de l'entreprise au-delà de l'horizon de projection explicite, "
        "souvent estimée par le modèle de Gordon (croissance perpétuelle) ou "
        "un multiple de sortie."),
    "EV/EBITDA": ("Valorisation",
        "Multiple de valorisation : valeur d'entreprise rapportée à l'EBITDA. "
        "Permet de comparer des sociétés indépendamment de leur structure de "
        "capital et de leur fiscalité."),
    "FCF": ("Valorisation",
        "Free Cash Flow. Flux de trésorerie disponible après investissements "
        "(capex), représentant le cash réellement générable pour les apporteurs "
        "de capitaux."),
    "Comparables": ("Valorisation",
        "Méthode de valorisation relative basée sur des multiples de sociétés "
        "cotées comparables (trading comps) ou de transactions précédentes "
        "(transaction comps)."),

    # --- Marchés & instruments -------------------------------------------
    "Obligation": ("Instruments",
        "Titre de créance : l'émetteur verse des coupons périodiques et "
        "rembourse le nominal à l'échéance. Son prix varie en sens inverse "
        "des taux d'intérêt."),
    "YTM": ("Instruments",
        "Yield to Maturity. Taux de rendement actuariel qui égalise la valeur "
        "actuelle des flux de l'obligation à son prix de marché."),
    "Duration": ("Instruments",
        "Sensibilité du prix d'une obligation aux variations de taux. La "
        "duration de Macaulay est la maturité moyenne pondérée des flux ; "
        "la duration modifiée mesure la variation de prix en %."),
    "Action": ("Instruments",
        "Titre de propriété représentant une fraction du capital d'une "
        "entreprise, donnant droit aux dividendes et au vote."),
    "Dérivé": ("Instruments",
        "Instrument dont la valeur dépend d'un sous-jacent (action, taux, "
        "matière première). Exemples : options, futures, swaps."),
    "Option Call": ("Instruments",
        "Droit (non obligation) d'acheter un sous-jacent à un prix d'exercice "
        "(strike) avant/à l'échéance. Gagne de la valeur si le sous-jacent monte."),
    "Option Put": ("Instruments",
        "Droit de vendre un sous-jacent au strike. Gagne de la valeur si le "
        "sous-jacent baisse ; sert souvent de couverture."),
    "Swap": ("Instruments",
        "Contrat d'échange de flux entre deux parties, par ex. taux fixe contre "
        "taux variable (IRS) ou devises (cross-currency swap)."),

    # --- Options / pricing ------------------------------------------------
    "Black-Scholes": ("Options",
        "Modèle de pricing d'options européennes basé sur un mouvement brownien "
        "géométrique du sous-jacent. Inputs : spot, strike, maturité, taux, "
        "volatilité."),
    "Volatilité implicite": ("Options",
        "Volatilité qui, injectée dans Black-Scholes, redonne le prix de marché "
        "de l'option. Reflète l'anticipation du marché sur l'amplitude des mouvements."),
    "Delta": ("Options",
        "Greek : sensibilité du prix de l'option à une variation de 1 du "
        "sous-jacent. Utilisé pour le delta-hedging."),
    "Gamma": ("Options",
        "Greek : taux de variation du delta. Élevé près de la monnaie et près "
        "de l'échéance."),
    "Vega": ("Options",
        "Greek : sensibilité du prix de l'option à une variation de 1 point de "
        "volatilité."),
    "Theta": ("Options",
        "Greek : érosion temporelle (time decay) de la valeur de l'option à "
        "mesure que l'échéance approche."),

    # --- Portefeuille & risque -------------------------------------------
    "Efficient Frontier": ("Portefeuille",
        "Frontière efficiente de Markowitz : ensemble des portefeuilles offrant "
        "le rendement maximal pour un niveau de risque donné (ou le risque "
        "minimal pour un rendement donné)."),
    "Sharpe Ratio": ("Portefeuille",
        "Rendement excédentaire (au-dessus du taux sans risque) par unité de "
        "volatilité. Mesure le rendement ajusté du risque."),
    "Beta": ("Portefeuille",
        "Sensibilité d'un actif aux mouvements du marché. Beta > 1 = plus "
        "volatil que le marché ; composante du CAPM."),
    "CAPM": ("Portefeuille",
        "Capital Asset Pricing Model. Rendement attendu = taux sans risque + "
        "beta × prime de risque de marché."),
    "Diversification": ("Portefeuille",
        "Réduction du risque spécifique en combinant des actifs faiblement "
        "corrélés. Ne réduit pas le risque systématique (de marché)."),
    "VaR": ("Risque",
        "Value at Risk. Perte maximale attendue sur un horizon donné à un "
        "niveau de confiance (ex : VaR 95% 1 jour). Ne capture pas l'ampleur "
        "des pertes extrêmes."),
    "CVaR": ("Risque",
        "Conditional VaR (Expected Shortfall). Perte moyenne dans les scénarios "
        "au-delà de la VaR. Mesure la sévérité de la queue de distribution."),
    "Stress Test": ("Risque",
        "Simulation de scénarios extrêmes (crise, choc de taux) pour évaluer la "
        "résilience d'un portefeuille ou d'une institution."),
    "Hedge": ("Risque",
        "Couverture : prise de position destinée à compenser le risque d'une "
        "autre position (ex : acheter des puts pour protéger un portefeuille actions)."),

    # --- M&A / Corporate --------------------------------------------------
    "M&A": ("M&A",
        "Mergers & Acquisitions. Opérations de fusion (combinaison de deux "
        "sociétés) ou d'acquisition (rachat d'une cible)."),
    "LBO": ("M&A",
        "Leveraged Buyout. Rachat d'une société financé majoritairement par de "
        "la dette, remboursée par les cash flows de la cible. Vise un IRR élevé "
        "sur les fonds propres investis."),
    "Synergies": ("M&A",
        "Gains attendus d'une fusion : réduction de coûts (synergies de coûts) "
        "ou hausse de revenus (synergies de revenus)."),
    "Due Diligence": ("M&A",
        "Audit approfondi d'une cible (financier, juridique, fiscal, "
        "opérationnel) avant une transaction."),
    "Accretion/Dilution": ("M&A",
        "Analyse de l'impact d'une acquisition sur le BPA (EPS) de l'acquéreur : "
        "relutive si le BPA augmente, dilutive s'il diminue."),
    "Goodwill": ("M&A",
        "Écart d'acquisition : excédent du prix payé sur la juste valeur des "
        "actifs nets acquis. Inscrit à l'actif, testé pour dépréciation."),

    # --- Comptabilité -----------------------------------------------------
    "EBITDA": ("Comptabilité",
        "Earnings Before Interest, Taxes, Depreciation & Amortization. Proxy de "
        "la rentabilité opérationnelle avant structure de capital et politique "
        "d'amortissement."),
    "Bilan": ("Comptabilité",
        "État financier : Actif = Passif + Capitaux propres. Photographie du "
        "patrimoine à une date donnée."),
    "Compte de résultat": ("Comptabilité",
        "État qui présente revenus, charges et résultat net sur une période. "
        "Aussi appelé P&L (Profit & Loss)."),
    "Tableau de flux": ("Comptabilité",
        "Cash Flow Statement. Décompose les flux de trésorerie en activités "
        "opérationnelles, d'investissement et de financement."),
    "ROE": ("Comptabilité",
        "Return on Equity. Résultat net rapporté aux capitaux propres. Mesure "
        "la rentabilité pour les actionnaires."),
    "Working Capital": ("Comptabilité",
        "Besoin en fonds de roulement : actifs courants moins passifs courants. "
        "Mesure le financement du cycle d'exploitation."),

    # --- Réglementation ---------------------------------------------------
    "MiFID II": ("Réglementation",
        "Directive européenne encadrant les marchés d'instruments financiers : "
        "transparence, protection investisseur, reporting des transactions."),
    "Bâle III": ("Réglementation",
        "Cadre prudentiel bancaire international : ratios de fonds propres "
        "(CET1), de levier et de liquidité (LCR, NSFR)."),
    "Dodd-Frank": ("Réglementation",
        "Loi américaine post-2008 renforçant la régulation financière (Volcker "
        "Rule, supervision des risques systémiques)."),
    "IFRS": ("Réglementation",
        "International Financial Reporting Standards. Normes comptables "
        "internationales utilisées en Europe et dans de nombreux pays."),
    "US GAAP": ("Réglementation",
        "Generally Accepted Accounting Principles (US). Référentiel comptable "
        "américain, distinct des IFRS sur plusieurs traitements."),
    "SEC": ("Réglementation",
        "Securities and Exchange Commission. Régulateur des marchés financiers "
        "américains : information, lutte contre la fraude, supervision."),
    "Volcker Rule": ("Réglementation",
        "Disposition de Dodd-Frank limitant le trading pour compte propre "
        "(proprietary trading) des banques de dépôt."),
}

# ===========================================================================
# EXTENSION — concepts issus des bases de connaissances (master finance).
# Ajout purement ADDITIF : on n'enlève rien de l'existant ci-dessus.
# ===========================================================================
GLOSSARY.update({
    # --- Temps & valeur de l'argent -------------------------------------
    "PV / FV": ("Valorisation",
        "Present Value / Future Value. PV = FV/(1+r)^n actualise un flux futur ; "
        "FV = PV·(1+r)^n capitalise un montant présent."),
    "NPV": ("Valorisation",
        "Net Present Value. Somme des flux actualisés d'un projet (le flux initial "
        "est négatif). NPV > 0 = projet créateur de valeur."),
    "IRR": ("Valorisation",
        "Internal Rate of Return. Taux qui annule la NPV. On accepte un projet si "
        "l'IRR dépasse le coût du capital."),
    "EAR": ("Valorisation",
        "Effective Annual Rate. Taux annuel effectif tenant compte de la "
        "capitalisation : EAR = (1 + r/m)^m − 1 pour m périodes par an."),
    "Taux continu": ("Valorisation",
        "Capitalisation en temps continu : FV = PV·e^(r·t). Utilisé en théorie "
        "des dérivés (Black-Scholes)."),

    # --- Valorisation actions -------------------------------------------
    "Modèle de Gordon": ("Valorisation",
        "Gordon Growth. Prix = D1/(re − g) : valorise une action par ses "
        "dividendes croissant à taux g perpétuel, actualisés au coût des fonds "
        "propres re. Très sensible à (re − g)."),
    "FCFE": ("Valorisation",
        "Free Cash Flow to Equity. Flux disponible pour les actionnaires (après "
        "dette). Actualisé au coût des fonds propres → valeur des capitaux propres."),
    "FCFF": ("Valorisation",
        "Free Cash Flow to Firm. Flux disponible pour tous les apporteurs de "
        "capitaux. Actualisé au WACC → valeur d'entreprise (EV)."),
    "P/E": ("Valorisation",
        "Price/Earnings. Cours rapporté au BPA. Nombre d'années de bénéfices "
        "payées ; un P/E élevé reflète de fortes attentes de croissance."),
    "P/B": ("Valorisation",
        "Price/Book. Cours rapporté à l'actif net comptable par action. Utile "
        "pour les financières et les sociétés à forte intensité d'actifs."),
    "P/S": ("Valorisation",
        "Price/Sales. Capitalisation rapportée au chiffre d'affaires. Utile quand "
        "les bénéfices sont négatifs ou volatils."),
    "EV": ("Valorisation",
        "Enterprise Value = capitalisation + dette nette. Coût de rachat de toute "
        "l'entreprise ; base des multiples d'actifs (EV/EBITDA, EV/Sales)."),

    # --- Taux & obligations (fixed income) ------------------------------
    "Convexité": ("Taux & obligations",
        "Courbure de la relation prix/taux d'une obligation. ΔP/P ≈ −D*·Δy + "
        "½·Conv·Δy². Plus la convexité est forte, plus la duration sous-estime "
        "le gain quand les taux baissent."),
    "Clean vs Dirty price": ("Taux & obligations",
        "Prix propre (clean) = prix coté hors coupon couru ; prix sale (dirty) = "
        "clean + coupon couru, c'est-à-dire le montant réellement payé."),
    "Courbe des taux": ("Taux & obligations",
        "Relation taux/maturité. Normale (croissante), aplatie, ou inversée "
        "(court > long) — l'inversion précède souvent une récession."),
    "Taux spot / forward": ("Taux & obligations",
        "Taux spot : taux zéro-coupon pour une maturité. Taux forward : taux "
        "futur implicite entre deux dates, déduit de la courbe spot."),
    "Roll-down": ("Taux & obligations",
        "Effet de vieillissement : sur une courbe croissante, une obligation qui "
        "se rapproche de l'échéance voit son yield baisser → son prix monte, "
        "sans mouvement de la courbe."),
    "Carry": ("Taux & obligations",
        "Rendement attendu si le marché ne bouge pas. Obligataire : coupon + "
        "roll-down. FX : différentiel de taux entre deux devises (carry trade)."),
    "Carry trade": ("Taux & obligations",
        "Stratégie : emprunter dans une devise à taux bas, investir dans une "
        "devise à taux élevé. Profitable tant que le change ne se retourne pas."),

    # --- Macro & politique monétaire ------------------------------------
    "PIB": ("Macro",
        "Produit Intérieur Brut. Mesure de l'activité économique ; sa croissance "
        "réelle (hors inflation) pilote les bénéfices et le cycle."),
    "Inflation": ("Macro",
        "Hausse générale des prix. Guide la banque centrale ; une surprise "
        "d'inflation repricé brutalement actions et obligations."),
    "Taux réel": ("Macro",
        "Taux nominal corrigé de l'inflation : taux réel ≈ taux nominal − "
        "inflation anticipée (relation de Fisher). Ce qui compte pour le pouvoir "
        "d'achat du rendement."),
    "TIPS / OATi": ("Macro",
        "Obligations indexées sur l'inflation : le nominal ou les coupons suivent "
        "un indice de prix. Protègent contre l'inflation mais sensibles aux taux réels."),
    "Output gap": ("Macro",
        "Écart entre PIB réel et PIB potentiel. Positif = surchauffe (pression "
        "inflationniste) ; négatif = sous-utilisation des capacités."),
    "Taux directeur": ("Macro",
        "Taux fixé par la banque centrale. Sa hausse renchérit le crédit : pèse "
        "sur actions de croissance et immobilier, peut aider les marges bancaires."),
    "QE / QT": ("Macro",
        "Quantitative Easing (achats d'actifs, injection de liquidité) / "
        "Tightening (réduction du bilan). Outils non conventionnels de politique "
        "monétaire agissant sur les taux longs."),
    "Hawkish / Dovish": ("Macro",
        "Ton d'une banque centrale : hawkish (restrictif, anti-inflation, taux "
        "↑) vs dovish (accommodant, pro-croissance, taux ↓)."),

    # --- Dérivés & volatilité -------------------------------------------
    "Forward / Future": ("Dérivés & volatilité",
        "Engagement d'acheter/vendre un sous-jacent à une date future à un prix "
        "fixé. Future = standardisé, coté, avec appels de marge ; forward = gré à gré."),
    "Cost of carry": ("Dérivés & volatilité",
        "Prix forward ≈ S0·(1+r)^T (moins dividendes/revenus, plus coûts de "
        "stockage). Relie le prix à terme au spot via le coût de portage."),
    "Contango": ("Dérivés & volatilité",
        "Courbe des futures ascendante (futures > spot). Souvent liée aux coûts "
        "de stockage ; génère un roll yield négatif."),
    "Backwardation": ("Dérivés & volatilité",
        "Courbe des futures descendante (futures < spot). Reflète une pénurie ou "
        "une forte demande immédiate ; roll yield positif."),
    "Roll yield": ("Dérivés & volatilité",
        "Rendement (positif ou négatif) issu du roulement des contrats futures à "
        "l'échéance. Négatif en contango, positif en backwardation."),
    "IRS": ("Dérivés & volatilité",
        "Interest Rate Swap. Échange de flux taux fixe contre taux variable. "
        "Sert à transformer/couvrir l'exposition de taux d'un bilan."),
    "Cross-currency swap": ("Dérivés & volatilité",
        "Échange de principal et d'intérêts libellés dans deux devises "
        "différentes. Gère le risque de change et de financement multidevise."),
    "Volatilité réalisée": ("Dérivés & volatilité",
        "Volatilité effectivement observée sur les rendements passés (écart-type "
        "annualisé), par opposition à la volatilité implicite."),
    "Skew / Smile": ("Dérivés & volatilité",
        "Variation de la volatilité implicite selon le strike. Le skew actions "
        "(puts OTM plus chers) reflète la demande de protection à la baisse."),
    "VIX": ("Dérivés & volatilité",
        "Indice de volatilité implicite (« jauge de la peur ») dérivé des options "
        "sur indice. Bondit lors des chocs de marché."),
    "Moneyness": ("Dérivés & volatilité",
        "Position du sous-jacent vs strike : in-the-money (ITM), at-the-money "
        "(ATM), out-of-the-money (OTM)."),
    "Covered call": ("Dérivés & volatilité",
        "Détenir l'action et vendre un call : encaisse une prime, plafonne le "
        "gain. Stratégie de rendement en marché stable."),
    "Protective put": ("Dérivés & volatilité",
        "Détenir l'action et acheter un put : assurance contre la baisse au prix "
        "d'une prime. Plancher de perte connu."),

    # --- Crédit & titrisation -------------------------------------------
    "PD / LGD / EAD": ("Crédit & titrisation",
        "Probability of Default, Loss Given Default, Exposure at Default. "
        "Briques du risque de crédit : Perte attendue = PD × LGD × EAD."),
    "Expected Loss": ("Crédit & titrisation",
        "Perte attendue d'un crédit : EL = PD × LGD × EAD. Provisionnée ; la "
        "perte inattendue (UL) est la variabilité autour de l'EL (capital)."),
    "Modèle de Merton": ("Crédit & titrisation",
        "Approche structurelle : les fonds propres sont vus comme un call sur "
        "l'actif de la firme ; défaut si l'actif passe sous la dette à l'échéance."),
    "Spread de crédit": ("Crédit & titrisation",
        "Surcroît de rendement d'une obligation risquée vs un taux sans risque. "
        "Rémunère le risque de défaut ; s'élargit en cas de stress."),
    "CDS": ("Crédit & titrisation",
        "Credit Default Swap. Assurance contre le défaut d'un émetteur : "
        "l'acheteur paie une prime, reçoit une compensation en cas d'événement de crédit."),
    "Titrisation": ("Crédit & titrisation",
        "Mise en commun d'actifs (prêts, crédits) dans un SPV qui émet des titres "
        "découpés en tranches (senior/mezzanine/equity)."),
    "Tranches / Waterfall": ("Crédit & titrisation",
        "Cascade de paiements : les pertes frappent d'abord l'equity, puis la "
        "mezzanine, enfin le senior (subordination). Les flux remontent en sens inverse."),
    "Downgrade": ("Crédit & titrisation",
        "Dégradation de notation par une agence. Élargit le spread, peut forcer "
        "des ventes (contraintes d'investissement) et renchérir le financement."),

    # --- Microstructure & liquidité -------------------------------------
    "Carnet d'ordres": ("Microstructure & liquidité",
        "Order book. Liste des ordres limites d'achat (bid) et de vente (ask) par "
        "prix et priorité temporelle ; montre la profondeur du marché."),
    "Bid / Ask / Mid": ("Microstructure & liquidité",
        "Bid = meilleur prix acheteur, Ask = meilleur prix vendeur, Mid = leur "
        "moyenne. L'écart bid-ask mesure le coût de transaction immédiat."),
    "Spread bid-ask": ("Microstructure & liquidité",
        "Écart entre ask et bid. Serré = marché liquide ; large = illiquide. "
        "Coût implicite d'un aller-retour."),
    "Ordre marché / limite": ("Microstructure & liquidité",
        "Marché : exécution immédiate au meilleur prix dispo (pas de contrôle du "
        "prix). Limite : prix fixé, mais exécution non garantie."),
    "Slippage": ("Microstructure & liquidité",
        "Écart entre le prix espéré et le prix d'exécution réel, dû à la taille "
        "de l'ordre ou à un marché qui bouge vite."),
    "Impact de marché": ("Microstructure & liquidité",
        "Effet d'un ordre sur le prix : un gros ordre « mange » plusieurs niveaux "
        "du carnet et déplace le cours contre soi."),
    "Dark pool": ("Microstructure & liquidité",
        "Plateforme à carnet non visible permettant d'exécuter de gros ordres "
        "sans révéler la taille (limite l'impact de marché)."),
    "Circuit breaker": ("Microstructure & liquidité",
        "Mécanisme de suspension (halt) de cotation en cas de mouvement extrême, "
        "destiné à calmer la panique."),
    "Repo": ("Microstructure & liquidité",
        "Vente d'un titre avec engagement de rachat : emprunt garanti par "
        "collatéral. Cœur de la liquidité de financement à court terme."),
    "Haircut": ("Microstructure & liquidité",
        "Décote appliquée à la valeur du collatéral (ex. 2% sur un AAA, 20% sur "
        "du high yield). Augmente avec le risque perçu → plus de collatéral exigé."),
    "Spirale de liquidité": ("Microstructure & liquidité",
        "Baisse des prix → pertes → appels de marge → ventes forcées → nouvelle "
        "baisse. Amplifiée par le levier et la hausse des corrélations en crise."),
    "CCP / IM / VM": ("Microstructure & liquidité",
        "Chambre de compensation (CCP) interposée entre contreparties. Initial "
        "Margin (collatéral de départ) + Variation Margin (ajustement quotidien)."),

    # --- Asset management & frais ---------------------------------------
    "NAV": ("Asset management",
        "Net Asset Value (VNI). Valeur liquidative d'une part de fonds = (actifs "
        "− passifs) / nombre de parts. Base des souscriptions/rachats."),
    "ETF": ("Asset management",
        "Exchange-Traded Fund. Fonds coté en continu ; des market makers "
        "arbitrent l'écart entre prix de marché et NAV."),
    "Management fee": ("Asset management",
        "Frais de gestion annuels, en % de l'encours (ex. 1%/an), prélevés quelle "
        "que soit la performance."),
    "Performance fee": ("Asset management",
        "Commission sur la surperformance (ex. 20%), souvent au-delà d'un hurdle "
        "et d'un high-water mark."),
    "High-water mark": ("Asset management",
        "Plus haut niveau de valeur déjà atteint : la performance fee ne "
        "s'applique qu'au-dessus, pour éviter de facturer deux fois la même hausse."),
    "Hurdle rate": ("Asset management",
        "Rendement minimal à dépasser avant de prélever une commission de "
        "performance."),
    "TWR vs MWR": ("Asset management",
        "Time-Weighted Return : neutralise les flux, mesure la compétence du "
        "gérant. Money-Weighted (IRR) : intègre le timing des apports, reflète "
        "l'expérience de l'investisseur."),
    "Attribution de performance": ("Asset management",
        "Décomposition de la performance : effet allocation vs sélection, "
        "contribution par classe d'actifs, secteur, ou facteur."),
    "Prospectus": ("Asset management",
        "Document décrivant stratégie, risques, frais et contraintes d'un fonds "
        "(concentration, levier max, limites sectorielles/ESG)."),

    # --- Performance & mesures de risque --------------------------------
    "Drawdown": ("Performance",
        "Baisse depuis un plus-haut. Le max drawdown est la pire chute pic-creux "
        "subie ; mesure intuitive de la douleur d'un investisseur."),
    "Sortino": ("Performance",
        "Variante du Sharpe n'utilisant que la volatilité baissière (downside "
        "deviation) : ne pénalise pas la volatilité à la hausse."),
    "Calmar": ("Performance",
        "Rendement annuel moyen rapporté au max drawdown. Compare la performance "
        "ajustée au risque de perte extrême."),
    "Downside deviation": ("Performance",
        "Écart-type calculé uniquement sur les rendements sous un seuil cible. "
        "Mesure le risque baissier, pas la volatilité totale."),
    "Treynor": ("Performance",
        "Rendement excédentaire par unité de risque de marché (bêta) : "
        "(Rp − rf)/βp. Pertinent pour un portefeuille bien diversifié."),
    "Information ratio": ("Performance",
        "Surperformance vs benchmark rapportée à la tracking error. Mesure la "
        "régularité de l'alpha d'un gérant actif."),
    "Tracking error": ("Performance",
        "Écart-type de la différence de rendement entre un portefeuille et son "
        "indice de référence. Mesure l'écart de gestion active."),
    "Rendement log": ("Performance",
        "r = ln(V1/V0). Additif dans le temps, pratique pour annualiser et "
        "modéliser ; proche du rendement simple pour de petites variations."),

    # --- Portefeuille & facteurs ----------------------------------------
    "CML": ("Portefeuille",
        "Capital Market Line. Combinaisons de l'actif sans risque et du "
        "portefeuille tangent (max Sharpe) : meilleur arbitrage rendement/risque accessible."),
    "Facteurs (Fama-French)": ("Portefeuille",
        "Sources de rendement systématiques : marché, taille (small/big), value "
        "(book-to-market), plus profitabilité et investissement. Expliquent les "
        "biais de style d'un portefeuille."),
    "Momentum": ("Portefeuille",
        "Facteur/signal : les actifs récemment performants tendent à continuer à "
        "court-moyen terme. Sujet à des retournements brutaux."),
    "Mean reversion": ("Portefeuille",
        "Signal : les prix/écarts tendent à revenir vers une moyenne. Inverse du "
        "momentum ; pertinent en marché sans tendance (range)."),
    "Value vs Growth": ("Portefeuille",
        "Style : value (décoté sur ses fondamentaux) vs growth (forte croissance "
        "attendue, multiples élevés). Leur surperformance alterne selon les régimes."),
    "Risk parity": ("Portefeuille",
        "Allocation où chaque actif contribue également au risque total (et non "
        "au capital). Souvent associée à du levier sur la poche obligataire."),

    # --- Alternatifs & ESG ----------------------------------------------
    "Private equity": ("Alternatifs & ESG",
        "Investissement en capital non coté (LBO, growth, venture). Capital "
        "bloqué, J-curve, performance mesurée en IRR et multiples (MOIC)."),
    "J-curve": ("Alternatifs & ESG",
        "Profil de performance d'un fonds PE : rendements négatifs au début "
        "(frais, investissements) puis positifs quand les participations mûrissent."),
    "Private debt": ("Alternatifs & ESG",
        "Prêt direct non bancaire (direct lending, mezzanine). Illiquide, "
        "rémunéré par une prime d'illiquidité et de risque."),
    "Hedge fund": ("Alternatifs & ESG",
        "Fonds flexible (long/short, macro, arbitrage, event-driven) utilisant "
        "levier et dérivés ; frais souvent « 2 et 20 »."),
    "REIT": ("Alternatifs & ESG",
        "Real Estate Investment Trust. Foncière cotée distribuant l'essentiel de "
        "ses revenus ; hybride actions/obligations, très sensible aux taux."),
    "Infrastructure": ("Alternatifs & ESG",
        "Actifs réels à cash flows longs et réguliers (souvent régulés/indexés). "
        "Financés via SPV, défensifs, sensibles aux taux."),
    "Project finance / SPV": ("Alternatifs & ESG",
        "Financement d'un projet via une entité dédiée (SPV), remboursé par les "
        "seuls cash flows du projet (non/limited recourse)."),
    "DSCR": ("Alternatifs & ESG",
        "Debt Service Coverage Ratio = cash flow disponible / service de la dette. "
        "Covenant clé : sous un seuil, restrictions de distribution."),
    "ESG": ("Alternatifs & ESG",
        "Critères Environnementaux, Sociaux et de Gouvernance. Approches : "
        "exclusion, best-in-class, engagement, impact investing."),
    "Green bond": ("Alternatifs & ESG",
        "Obligation dont le produit (use of proceeds) finance des projets verts. "
        "Variante : sustainability-linked bond (coupon lié à des objectifs ESG)."),
    "Taxonomie verte": ("Alternatifs & ESG",
        "Classification réglementaire des activités durables, support du reporting "
        "extra-financier et de la lutte contre le greenwashing."),
    "Risque de transition": ("Alternatifs & ESG",
        "Risque lié au passage à une économie bas-carbone (réglementation, prix "
        "du carbone, actifs échoués), distinct du risque physique climatique."),
    "Stablecoin": ("Alternatifs & ESG",
        "Crypto-actif arrimé à une référence (souvent le dollar), collatéralisé "
        "ou algorithmique. Risque majeur : perte de l'ancrage (depeg)."),
    "CBDC": ("Alternatifs & ESG",
        "Central Bank Digital Currency. Monnaie numérique de banque centrale, "
        "alternative publique aux stablecoins privés (enjeux de vie privée et de "
        "politique monétaire)."),
    "Produit structuré": ("Alternatifs & ESG",
        "Combinaison obligation + dérivés créant un payoff non linéaire "
        "(autocallable, reverse convertible, capital garanti). Risque émetteur et de structure."),

    # --- Comportement & cycles ------------------------------------------
    "Biais d'ancrage": ("Comportement",
        "Rester fixé sur un chiffre de référence (prix d'achat, plus-haut) et y "
        "ramener inconsciemment ses décisions."),
    "Aversion aux pertes": ("Comportement",
        "La douleur d'une perte est ressentie plus fortement que le plaisir d'un "
        "gain équivalent ; biaise la prise de risque."),
    "Disposition effect": ("Comportement",
        "Tendance à vendre trop tôt les gagnants et à conserver trop longtemps "
        "les perdants."),
    "Herding": ("Comportement",
        "Comportement de troupeau : suivre le consensus, ce qui amplifie bulles "
        "et krachs."),
    "Biais de confirmation": ("Comportement",
        "Ne rechercher que les informations qui confortent une opinion déjà "
        "formée, en ignorant les signaux contraires."),
    "Régime de marché": ("Comportement",
        "Phase de marché aux propriétés stables : faible vol/tendance, forte "
        "vol/incertitude, ou range sans tendance. Les régimes alternent."),

    # --- Réglementation bancaire & ALM ----------------------------------
    "RWA": ("Réglementation",
        "Risk-Weighted Assets. Actifs pondérés par leur risque ; dénominateur des "
        "ratios de capital (un souverain AAA pèse peu, un crédit corporate beaucoup)."),
    "CET1": ("Réglementation",
        "Common Equity Tier 1. Fonds propres durs / RWA : ratio cœur de la "
        "solidité bancaire sous Bâle III."),
    "LCR / NSFR": ("Réglementation",
        "Liquidity Coverage Ratio (actifs liquides / sorties à 30 j) et Net "
        "Stable Funding Ratio (financement stable / besoins à 1 an). Ratios de liquidité."),
    "Leverage ratio": ("Réglementation",
        "Capital / exposition totale, sans pondération de risque. Borne le levier "
        "global d'une banque."),
    "ALM": ("Réglementation",
        "Asset-Liability Management. Gestion conjointe actifs/passifs du banking "
        "book pour maîtriser les risques de taux et de liquidité (gap de taux/duration)."),
    "Best execution": ("Réglementation",
        "Obligation d'obtenir le meilleur résultat possible pour le client (prix, "
        "coûts, rapidité, probabilité d'exécution)."),
    "Devoir fiduciaire": ("Réglementation",
        "Obligation d'agir dans le seul intérêt du client, avant celui de "
        "l'établissement."),
    "Insider trading": ("Réglementation",
        "Utilisation d'une information privilégiée non publique pour négocier. "
        "Interdit et sévèrement sanctionné."),
    "Muraille de Chine": ("Réglementation",
        "Chinese wall : barrière d'information entre équipes en conflit potentiel "
        "(ex. M&A vs trading) pour prévenir les abus de marché."),
})

# Catégories pour la navigation
CATEGORIES = sorted(set(cat for cat, _ in GLOSSARY.values()))

# ---- accès localisé (FR / EN) ---------------------------------------------
from data.glossary_en import GLOSSARY_EN, display_name
_CATEGORIES_EN = sorted(set(cat for cat, _ in GLOSSARY_EN.values()))


def localized(lang):
    """Renvoie (dict terme->(catégorie, définition), liste catégories) selon la langue."""
    if lang == "en":
        return GLOSSARY_EN, _CATEGORIES_EN
    return GLOSSARY, CATEGORIES


def entry(term, lang):
    """Renvoie (catégorie, définition) d'un terme dans la langue, repli FR."""
    g = GLOSSARY_EN if lang == "en" else GLOSSARY
    return g.get(term) or GLOSSARY.get(term)
