"""
lessons.py — Académie : leçons courtes et exactes pour apprendre la finance
et les réflexes d'un terminal type Bloomberg.

Chaque leçon : id, topic, title, body (explication), formula, example, takeaway.
Le contenu est volontairement concis mais juste (formules réelles).
"""

LESSONS = [
    # ----------------------------- Valorisation -----------------------------
    {"id": "pe", "topic": "Valorisation", "title": "Le P/E (PER)",
     "body": "Le Price/Earnings rapporte le cours au bénéfice par action. Il dit "
             "combien d'années de bénéfices on paie pour une action. Un P/E élevé "
             "reflète de fortes attentes de croissance — ou un titre cher.",
     "formula": "P/E = Cours / BPA   (BPA = Résultat net / Nb d'actions)",
     "example": "Action à 200, BPA 10 → P/E = 20x (on paie 20 ans de bénéfices).",
     "takeaway": "Comparez toujours un P/E à ceux du même secteur (cf. RV)."},
    {"id": "ev_ebitda", "topic": "Valorisation", "title": "EV / EBITDA",
     "body": "L'Enterprise Value inclut la dette nette : c'est le coût de rachat "
             "de toute l'entreprise. Rapportée à l'EBITDA, elle neutralise la "
             "structure de capital et la fiscalité — idéale pour comparer des sociétés.",
     "formula": "EV = Capitalisation + Dette nette ;  multiple = EV / EBITDA",
     "example": "Capi 800, dette nette 200 → EV 1000 ; EBITDA 100 → 10x.",
     "takeaway": "EV/EBITDA > P/E pour comparer des sociétés à dettes différentes."},
    {"id": "dcf", "topic": "Valorisation", "title": "Le DCF",
     "body": "Le Discounted Cash Flow actualise les flux de trésorerie futurs au "
             "WACC, puis ajoute une valeur terminale. C'est la valeur intrinsèque, "
             "indépendante des humeurs du marché.",
     "formula": "VT = FCF×(1+g) / (WACC − g) ;  Valeur = Σ FCF/(1+WACC)^t + VT actualisée",
     "example": "FCF 100, g 2,5%, WACC 9% → VT = 100×1,025/(0,065) ≈ 1577.",
     "takeaway": "Le DCF est très sensible au WACC et à g : testez plusieurs scénarios."},
    {"id": "capvsev", "topic": "Valorisation", "title": "Capitalisation vs EV",
     "body": "La capitalisation = valeur des actions (cours × nb d'actions). "
             "L'Enterprise Value = valeur de toute l'entreprise (actions + dette − cash). "
             "Deux sociétés de même capi peuvent avoir des EV très différentes.",
     "formula": "Capi = Cours × Actions ;  EV = Capi + Dette nette",
     "example": "Capi 500 + dette nette 300 = EV 800.",
     "takeaway": "Les multiples d'actifs (EBITDA, ventes) s'utilisent avec l'EV."},
    # -------------------------------- Risque --------------------------------
    {"id": "diversification", "topic": "Risque", "title": "Diversification & corrélation",
     "body": "Combiner des actifs peu corrélés réduit le risque sans sacrifier le "
             "rendement attendu. C'est le « seul repas gratuit » de la finance. "
             "Plus la corrélation est faible (voire négative), plus l'effet est fort.",
     "formula": "σ²(A+B) = w²σ²A + w²σ²B + 2w²·ρ·σA·σB",
     "example": "Deux actifs corrélés à +0,9 : peu d'effet. À −0,2 : forte réduction.",
     "takeaway": "Diversifiez les secteurs ET les régions (cf. ALLOCATE, REBALANCE)."},
    {"id": "sharpe", "topic": "Risque", "title": "Ratio de Sharpe",
     "body": "Le Sharpe mesure le rendement excédentaire par unité de risque total. "
             "Il permet de comparer des stratégies de risques différents.",
     "formula": "Sharpe = (rendement − taux sans risque) / volatilité",
     "example": "Rdt 12%, sans risque 2%, vol 16% → (0,12−0,02)/0,16 = 0,63.",
     "takeaway": "Un Sharpe anormalement élevé doit éveiller les soupçons (risque caché)."},
    {"id": "var", "topic": "Risque", "title": "VaR & CVaR",
     "body": "La Value-at-Risk est la perte qui ne sera dépassée qu'avec une faible "
             "probabilité sur un horizon donné. La CVaR (Expected Shortfall) mesure "
             "la perte MOYENNE au-delà de la VaR : elle capte les queues extrêmes.",
     "formula": "VaR 99% 1j : 1% de chances de perdre plus que ce montant en un jour",
     "example": "VaR 99% 1j = 1M€ : 1 jour sur 100, la perte dépasse 1M€.",
     "takeaway": "La VaR ne borne pas la perte maximale ; surveillez la CVaR et stressez (RISK)."},
    {"id": "beta", "topic": "Risque", "title": "Bêta & risque de marché",
     "body": "Le bêta mesure la sensibilité d'un actif au marché. Bêta 1 = bouge "
             "comme le marché ; >1 = amplifie ; <1 = amortit. Le risque de marché "
             "(systématique) ne se diversifie pas, contrairement au risque spécifique.",
     "formula": "E[r] = rf + β·(E[rm] − rf)   (CAPM)",
     "example": "Bêta 1,4 : si le marché fait +10%, l'actif tend vers +14%.",
     "takeaway": "Réduisez le bêta pour couvrir le risque de marché (cf. HEDGE)."},
    # -------------------------------- Dérivés -------------------------------
    {"id": "options", "topic": "Dérivés", "title": "Options : call & put",
     "body": "Un call donne le droit d'ACHETER à un prix d'exercice ; un put, de "
             "VENDRE. On les utilise pour spéculer avec levier ou se couvrir. "
             "L'acheteur paie une prime ; sa perte est limitée à cette prime.",
     "formula": "Call à l'échéance = max(S − K, 0) ;  Put = max(K − S, 0)",
     "example": "Call K=100, prime 5. À S=120 : gain 120−100−5 = 15.",
     "takeaway": "Acheter des puts protège un portefeuille à la baisse (assurance)."},
    {"id": "greeks", "topic": "Dérivés", "title": "Les Greeks",
     "body": "Les Greeks mesurent la sensibilité du prix d'une option. Delta (au "
             "sous-jacent), Gamma (variation du delta), Vega (volatilité), Theta "
             "(temps), Rho (taux). Indispensables pour gérer un book d'options.",
     "formula": "Delta ∈ [0,1] pour un call ; Gamma max à la monnaie près de l'échéance",
     "example": "Theta négatif : une option perd de la valeur chaque jour qui passe.",
     "takeaway": "Le module QUANT calcule Black-Scholes et les Greeks en direct."},
    # --------------------------------- Macro --------------------------------
    {"id": "rates", "topic": "Macro", "title": "Taux d'intérêt & marchés",
     "body": "Quand la banque centrale monte ses taux, l'argent coûte plus cher : "
             "les obligations existantes baissent, les valeurs de croissance et "
             "l'immobilier souffrent, les banques peuvent profiter de marges accrues.",
     "formula": "Prix d'une obligation ↓ quand les taux ↑ (relation inverse)",
     "example": "Taux 2%→4% : l'immobilier et la tech non rentable décrochent.",
     "takeaway": "Suivez la macro avec ECO : taux, inflation, croissance pilotent tout."},
    {"id": "yield_curve", "topic": "Macro", "title": "Courbe des taux & inversion",
     "body": "La courbe des taux relie les taux aux maturités. Normalement croissante "
             "(le long terme rapporte plus). Quand elle s'INVERSE (court > long), "
             "le marché anticipe un ralentissement : signal historique de récession.",
     "formula": "Spread 10 ans − 2 ans < 0  →  courbe inversée",
     "example": "10a à 3,5% et 2a à 4,2% : spread −0,7% = inversion.",
     "takeaway": "Une inversion durable précède souvent un retournement économique."},
    # ---------------------------------- M&A ---------------------------------
    {"id": "lbo", "topic": "M&A", "title": "Le LBO",
     "body": "Un Leveraged Buy-Out rachète une société surtout avec de la dette. "
             "Le levier amplifie le rendement des fonds propres (IRR) si tout se "
             "passe bien — et les pertes sinon. Le désendettement crée de la valeur.",
     "formula": "IRR amplifié par le levier ;  MOIC = valeur de sortie / capital investi",
     "example": "Entrée 100 (20 equity + 80 dette), sortie 160, dette remboursée à 40 "
                "→ equity = 120 pour 20 investis = MOIC 6x.",
     "takeaway": "Plus de levier = plus d'IRR potentiel mais plus de risque de défaut."},
    {"id": "accretion", "topic": "M&A", "title": "Relutif / dilutif",
     "body": "Une acquisition est relutive (accretive) si elle augmente le BPA de "
             "l'acquéreur, dilutive si elle le réduit. Payer en actions chères pour "
             "acheter moins cher tend à être relutif.",
     "formula": "Comparer le BPA pro-forma (combiné) au BPA stand-alone de l'acquéreur",
     "example": "Acquéreur P/E 25 rachète une cible P/E 15 en actions → relutif.",
     "takeaway": "Le module MA simule l'accretion/dilution et le LBO."},
    # ------------------------------- Bloomberg ------------------------------
    {"id": "bbg", "topic": "Bloomberg", "title": "Réflexes type Bloomberg",
     "body": "Un terminal se pilote par codes-fonctions au clavier. Apprenez les "
             "raccourcis : ils font gagner un temps fou et structurent l'analyse.",
     "formula": "DES fiche · FA fondamentaux · GP graphe · RV pairs · WEI indices · "
                "EQS screener · ECO macro · PRT portefeuille",
     "example": "Taper « DES MVC » ouvre la fiche ; « RV MVC » la compare à ses pairs.",
     "takeaway": "Tape COMMANDS pour le catalogue, et utilise Tab pour autocompléter."},
]

TOPICS = ["Valorisation", "Risque", "Dérivés", "Macro", "M&A", "Bloomberg"]


def by_topic():
    out = {t: [] for t in TOPICS}
    for l in LESSONS:
        out.setdefault(l["topic"], []).append(l)
    return out


def get(lesson_id):
    for l in LESSONS:
        if l["id"] == lesson_id:
            return l
    return None
