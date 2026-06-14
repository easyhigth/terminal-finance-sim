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

# Catégories pour la navigation
CATEGORIES = sorted(set(cat for cat, _ in GLOSSARY.values()))
