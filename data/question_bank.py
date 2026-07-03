"""
question_bank.py — Banque de questions pour les évaluations de promotion.
Chaque question : dict avec
  q       : énoncé
  choices : liste de réponses
  answer  : index de la bonne réponse
  expl    : explication (affichée après réponse)
  grade   : grade minimal concerné (index dans config.GRADES)
  track   : "General" ou une voie de TRACKS
  diff    : difficulté 1-5

La difficulté augmente avec le grade : les questions de niveau Intern sont
factuelles, celles de niveau MD/Partner exigent du jugement et du calcul.
"""

QUESTIONS = [
    # ===================== INTERN (grade 0) — fondamentaux ==============
    {"id": "q00", "grade": 0, "track": "General", "diff": 1,
     "q": "Que mesure le ratio ROE ?",
     "choices": ["La rentabilité des capitaux propres",
                 "Le niveau d'endettement",
                 "La liquidité à court terme",
                 "La marge brute"],
     "answer": 0,
     "expl": "ROE = Résultat net / Capitaux propres. Mesure la rentabilité pour les actionnaires."},

    {"id": "q01", "grade": 0, "track": "General", "diff": 1,
     "q": "Dans un bilan, quelle égalité fondamentale est toujours vérifiée ?",
     "choices": ["Actif = Passif + Capitaux propres",
                 "Actif = Passif - Capitaux propres",
                 "Revenus = Charges + Résultat",
                 "Actif = Revenus"],
     "answer": 0,
     "expl": "L'équation comptable fondamentale : Actif = Passif + Capitaux propres."},

    {"id": "q02", "grade": 0, "track": "General", "diff": 2,
     "q": "Quand les taux d'intérêt montent, le prix d'une obligation à taux fixe :",
     "choices": ["Baisse", "Monte", "Reste stable", "Double"],
     "answer": 0,
     "expl": "Relation inverse prix/taux : une hausse des taux rend les anciens coupons moins attractifs, le prix baisse."},

    {"id": "q03", "grade": 0, "track": "General", "diff": 2,
     "q": "Que représente l'EBITDA ?",
     "choices": ["Le résultat avant intérêts, impôts, dépréciation et amortissement",
                 "Le résultat net après impôt",
                 "Le chiffre d'affaires brut",
                 "Le free cash flow"],
     "answer": 0,
     "expl": "EBITDA = proxy de la rentabilité opérationnelle, neutre vis-à-vis du financement et de l'amortissement."},

    # ===================== ANALYST (grade 1) ============================
    {"id": "q04", "grade": 1, "track": "General", "diff": 2,
     "q": "Dans un DCF, la valeur terminale est généralement estimée par :",
     "choices": ["Le modèle de Gordon (croissance perpétuelle) ou un multiple de sortie",
                 "La somme des dividendes passés",
                 "Le coût historique des actifs",
                 "La capitalisation boursière actuelle"],
     "answer": 0,
     "expl": "Valeur terminale = FCF×(1+g)/(WACC−g) [Gordon], ou EBITDA de sortie × multiple."},

    {"id": "q05", "grade": 1, "track": "General", "diff": 3,
     "q": "Une société a un WACC de 9% et une croissance terminale de 2,5%. Si la croissance terminale passe à 3,5%, la valeur terminale :",
     "choices": ["Augmente (dénominateur plus petit)",
                 "Diminue",
                 "Reste identique",
                 "Devient négative"],
     "answer": 0,
     "expl": "VT = FCF(1+g)/(WACC−g). Augmenter g réduit (WACC−g), donc augmente la VT."},

    {"id": "q06", "grade": 1, "track": "General", "diff": 3,
     "q": "Quel ratio évalue le mieux la capacité à honorer ses intérêts ?",
     "choices": ["Interest Coverage (EBIT / charges d'intérêts)",
                 "Current Ratio",
                 "ROE",
                 "Inventory Turnover"],
     "answer": 0,
     "expl": "Interest Coverage = EBIT / intérêts. Plus il est élevé, plus la société couvre facilement sa dette."},

    # ===================== ASSOCIATE (grade 2) ==========================
    {"id": "q07", "grade": 2, "track": "General", "diff": 3,
     "q": "Une acquisition payée en actions est dite 'relutive' (accretive) si :",
     "choices": ["Le BPA pro-forma de l'acquéreur augmente",
                 "Le BPA pro-forma diminue",
                 "Le goodwill est nul",
                 "La cible est non rentable"],
     "answer": 0,
     "expl": "Accretive = le BPA (EPS) combiné dépasse le BPA stand-alone de l'acquéreur."},

    {"id": "q08", "grade": 2, "track": "Portfolio", "diff": 4,
     "q": "Sur la frontière efficiente, le portefeuille tangent est celui qui :",
     "choices": ["Maximise le ratio de Sharpe",
                 "Minimise le rendement",
                 "A le beta le plus élevé",
                 "Contient un seul actif"],
     "answer": 0,
     "expl": "Le portefeuille tangent maximise (rendement−rf)/volatilité, soit le Sharpe ; c'est le point de tangence avec la CML."},

    {"id": "q09", "grade": 2, "track": "Risk", "diff": 4,
     "q": "La VaR à 99% sur 1 jour de 1M€ signifie :",
     "choices": ["1% de chance de perdre plus d'1M€ en un jour",
                 "On perdra exactement 1M€",
                 "99% de chance de gagner 1M€",
                 "La perte maximale possible est 1M€"],
     "answer": 0,
     "expl": "VaR 99% 1j = seuil de perte dépassé dans seulement 1% des cas. Elle ne borne pas la perte maximale."},

    # ===================== VP (grade 3) =================================
    {"id": "q10", "grade": 3, "track": "M&A", "diff": 4,
     "q": "Dans un LBO, l'IRR des fonds propres est principalement amplifié par :",
     "choices": ["L'effet de levier (dette) et le désendettement",
                 "Une baisse du multiple de sortie",
                 "Une hausse du capital investi",
                 "L'absence de croissance de l'EBITDA"],
     "answer": 0,
     "expl": "Le levier amplifie les rendements sur fonds propres ; le remboursement de dette transfère de la valeur aux actionnaires."},

    {"id": "q11", "grade": 3, "track": "Quant", "diff": 5,
     "q": "Le gamma d'une option est maximal :",
     "choices": ["À la monnaie, près de l'échéance",
                 "Très en dehors de la monnaie",
                 "Pour une maturité très longue",
                 "Quand la volatilité est nulle"],
     "answer": 0,
     "expl": "Gamma culmine ATM et explose à l'approche de l'échéance — d'où le risque de hedging des books d'options courtes."},

    {"id": "q12", "grade": 3, "track": "Risk", "diff": 5,
     "q": "Pourquoi la CVaR est-elle souvent préférée à la VaR ?",
     "choices": ["Elle mesure la sévérité moyenne des pertes au-delà de la VaR",
                 "Elle est toujours plus faible que la VaR",
                 "Elle ignore les queues de distribution",
                 "Elle ne nécessite aucune hypothèse"],
     "answer": 0,
     "expl": "La CVaR (Expected Shortfall) capture l'ampleur des pertes extrêmes ; elle est cohérente (sous-additive), contrairement à la VaR."},

    # ===================== DIRECTOR (grade 4) ===========================
    {"id": "q13", "grade": 4, "track": "General", "diff": 5,
     "q": "Une banque doit respecter un ratio CET1 minimal. Ce ratio relève de :",
     "choices": ["Bâle III", "MiFID II", "RGPD", "US GAAP"],
     "answer": 0,
     "expl": "Le ratio CET1 (Common Equity Tier 1) est un pilier des exigences de fonds propres de Bâle III."},

    {"id": "q14", "grade": 4, "track": "M&A", "diff": 5,
     "q": "Dans une fusion, le 'goodwill' inscrit correspond à :",
     "choices": ["L'excédent du prix payé sur la juste valeur des actifs nets acquis",
                 "La trésorerie de la cible",
                 "La dette nette combinée",
                 "Le total des synergies de coûts"],
     "answer": 0,
     "expl": "Goodwill = prix d'acquisition − juste valeur des actifs nets identifiables. Testé annuellement pour dépréciation."},

    # ===================== MD / PARTNER (grade 5) =======================
    {"id": "q15", "grade": 5, "track": "General", "diff": 5,
     "q": "Un fonds affiche un Sharpe de 2,5 sur 2 ans avec une stratégie opaque et peu de volatilité déclarée. Le réflexe prudent est de :",
     "choices": ["Mener une due diligence approfondie (risque de tail/fraude caché)",
                 "Investir immédiatement le maximum",
                 "Ignorer, le Sharpe garantit la qualité",
                 "Augmenter le levier sans analyse"],
     "answer": 0,
     "expl": "Un Sharpe anormalement élevé avec opacité peut masquer un risque de queue (vente d'options) ou une fraude. La DD est impérative."},

    # =====================================================================
    # BLOC ÉTENDU — réponses à index variés (anti-pattern)
    # =====================================================================

    # --------------------- INTERN (grade 0) — General -------------------
    {"id": "q16", "grade": 0, "track": "General", "diff": 1,
     "q": "Que mesure la marge nette ?",
     "choices": ["La part du chiffre d'affaires absorbée par les charges",
                 "Le résultat net rapporté au chiffre d'affaires",
                 "Le total des actifs sur les ventes",
                 "Le bénéfice par action"],
     "answer": 1,
     "expl": "Marge nette = Résultat net / Chiffre d'affaires. Elle mesure la rentabilité finale des ventes."},

    {"id": "q17", "grade": 0, "track": "General", "diff": 1,
     "q": "Qu'est-ce que la liquidité d'un actif ?",
     "choices": ["Sa rentabilité attendue",
                 "Son niveau de risque",
                 "La facilité à le convertir en cash sans décote",
                 "Sa duration"],
     "answer": 2,
     "expl": "La liquidité = capacité à vendre rapidement un actif proche de sa juste valeur, sans décote significative."},

    {"id": "q18", "grade": 0, "track": "General", "diff": 1,
     "q": "Dans un compte de résultat, qu'est-ce que le chiffre d'affaires ?",
     "choices": ["Le bénéfice après impôt",
                 "Les ventes totales de biens et services sur la période",
                 "La trésorerie disponible",
                 "Les capitaux propres"],
     "answer": 1,
     "expl": "Le chiffre d'affaires (revenue) correspond aux ventes facturées, en haut du compte de résultat."},

    {"id": "q19", "grade": 0, "track": "General", "diff": 2,
     "q": "Qu'appelle-t-on le 'free cash flow' (FCF) ?",
     "choices": ["Le résultat net",
                 "L'EBITDA",
                 "Le cash généré après investissements (capex)",
                 "Le dividende versé"],
     "answer": 2,
     "expl": "FCF ≈ flux opérationnel − capex : le cash réellement disponible pour les créanciers et actionnaires."},

    {"id": "q20", "grade": 0, "track": "General", "diff": 2,
     "q": "Une action verse un dividende. Cela correspond à :",
     "choices": ["Un remboursement de dette",
                 "Une distribution de bénéfices aux actionnaires",
                 "Une charge d'intérêt",
                 "Une augmentation de capital"],
     "answer": 1,
     "expl": "Le dividende est une distribution d'une partie des bénéfices aux détenteurs d'actions."},

    {"id": "q21", "grade": 0, "track": "General", "diff": 2,
     "q": "Qu'est-ce que la capitalisation boursière d'une société cotée ?",
     "choices": ["Le total de son bilan",
                 "Sa dette nette",
                 "Cours de l'action × nombre d'actions en circulation",
                 "Son chiffre d'affaires annuel"],
     "answer": 2,
     "expl": "Market cap = prix de l'action × nombre d'actions. C'est la valeur des fonds propres au marché."},

    {"id": "q22", "grade": 0, "track": "General", "diff": 2,
     "q": "Diversifier un portefeuille permet surtout de :",
     "choices": ["Réduire le risque spécifique (idiosyncratique)",
                 "Éliminer le risque de marché",
                 "Garantir un rendement positif",
                 "Augmenter le levier"],
     "answer": 0,
     "expl": "La diversification réduit le risque spécifique ; le risque systématique (de marché) demeure non diversifiable."},

    # --------------------- ANALYST (grade 1) — General ------------------
    {"id": "q23", "grade": 1, "track": "General", "diff": 2,
     "q": "Le WACC représente :",
     "choices": ["Le coût marginal de la dette",
                 "Le coût moyen pondéré du capital (dette + fonds propres)",
                 "Le taux sans risque",
                 "Le rendement des dividendes"],
     "answer": 1,
     "expl": "WACC = coût moyen pondéré des sources de financement, utilisé pour actualiser les flux d'un DCF."},

    {"id": "q24", "grade": 1, "track": "General", "diff": 3,
     "q": "Le ratio P/E (PER) élevé d'une société signale généralement :",
     "choices": ["Une société en faillite",
                 "De fortes attentes de croissance ou un titre cher",
                 "Une dette nulle",
                 "Un dividende garanti"],
     "answer": 1,
     "expl": "Un PER élevé reflète des anticipations de croissance des bénéfices — ou une survalorisation."},

    {"id": "q25", "grade": 1, "track": "General", "diff": 3,
     "q": "La duration d'une obligation mesure :",
     "choices": ["Sa maturité résiduelle exacte",
                 "Sa sensibilité du prix aux variations de taux",
                 "Son rendement courant",
                 "Son rating de crédit"],
     "answer": 1,
     "expl": "La duration (modifiée) approxime la variation en % du prix pour une variation de 1% des taux."},

    {"id": "q26", "grade": 1, "track": "General", "diff": 3,
     "q": "Le 'working capital' (BFR) augmente fortement. Cela :",
     "choices": ["Améliore mécaniquement la trésorerie",
                 "Consomme de la trésorerie",
                 "N'a aucun effet sur le cash",
                 "Réduit l'endettement"],
     "answer": 1,
     "expl": "Une hausse du BFR (stocks + créances − dettes fournisseurs) immobilise du cash, donc le consomme."},

    {"id": "q27", "grade": 1, "track": "General", "diff": 3,
     "q": "Le bêta (β) d'une action mesure :",
     "choices": ["Sa volatilité absolue",
                 "Sa sensibilité au marché (risque systématique)",
                 "Son dividende",
                 "Sa liquidité"],
     "answer": 1,
     "expl": "β = covariance(titre, marché)/variance(marché). β>1 = plus sensible que le marché."},

    {"id": "q28", "grade": 1, "track": "General", "diff": 4,
     "q": "Dans le CAPM, le rendement attendu d'un actif s'écrit :",
     "choices": ["rf + β(E[rm] − rf)",
                 "rf × β",
                 "E[rm] − β",
                 "β / rf"],
     "answer": 0,
     "expl": "CAPM : E[r] = rf + β × prime de risque de marché (E[rm] − rf)."},

    # --------------------- ASSOCIATE (grade 2) --------------------------
    {"id": "q29", "grade": 2, "track": "General", "diff": 3,
     "q": "L'Enterprise Value (EV) se calcule comme :",
     "choices": ["Capitalisation + dette nette",
                 "Capitalisation − dette",
                 "Total des actifs",
                 "EBITDA × 10"],
     "answer": 0,
     "expl": "EV = capitalisation boursière + dette nette (+ intérêts minoritaires, − cash). Base des multiples EV/EBITDA."},

    {"id": "q30", "grade": 2, "track": "General", "diff": 4,
     "q": "Pourquoi préfère-t-on souvent EV/EBITDA au P/E pour comparer des sociétés ?",
     "choices": ["Il est plus simple à calculer",
                 "Il neutralise la structure de capital et la fiscalité",
                 "Il ignore la dette",
                 "Il intègre les dividendes"],
     "answer": 1,
     "expl": "EV/EBITDA compare des sociétés indépendamment de leur financement et de leur taux d'imposition."},

    {"id": "q31", "grade": 2, "track": "General", "diff": 4,
     "q": "Un covenant bancaire impose un ratio Dette nette/EBITDA < 3,5x. C'est :",
     "choices": ["Une garantie de l'État",
                 "Une clause de protection du créancier",
                 "Un dividende prioritaire",
                 "Une option de conversion"],
     "answer": 1,
     "expl": "Les covenants encadrent l'emprunteur (levier, couverture d'intérêts) pour protéger les prêteurs."},

    {"id": "q32", "grade": 2, "track": "Portfolio", "diff": 3,
     "q": "Le ratio de Sharpe se définit comme :",
     "choices": ["(rendement − rf) / volatilité",
                 "rendement / bêta",
                 "volatilité / rendement",
                 "alpha × bêta"],
     "answer": 0,
     "expl": "Sharpe = excès de rendement par unité de risque total (écart-type). Plus il est élevé, mieux c'est."},

    {"id": "q33", "grade": 2, "track": "Portfolio", "diff": 4,
     "q": "Le ratio de Sortino diffère du Sharpe car il :",
     "choices": ["Utilise le bêta au dénominateur",
                 "Ne pénalise que la volatilité baissière (downside)",
                 "Ignore le taux sans risque",
                 "Mesure la liquidité"],
     "answer": 1,
     "expl": "Le Sortino ne retient que la semi-déviation des rendements négatifs, jugée plus pertinente que la volatilité totale."},

    {"id": "q34", "grade": 2, "track": "Portfolio", "diff": 4,
     "q": "La corrélation entre deux actifs passe de +0,8 à −0,2. L'effet de diversification :",
     "choices": ["Diminue",
                 "Disparaît",
                 "Augmente (réduction de risque accrue)",
                 "Reste identique"],
     "answer": 2,
     "expl": "Plus la corrélation est faible (voire négative), plus la combinaison réduit la variance du portefeuille."},

    {"id": "q35", "grade": 2, "track": "M&A", "diff": 3,
     "q": "Dans une transaction, la 'due diligence' sert à :",
     "choices": ["Fixer le dividende",
                 "Vérifier en profondeur la cible avant signature",
                 "Émettre des actions",
                 "Calculer le bêta"],
     "answer": 1,
     "expl": "La due diligence (financière, juridique, fiscale...) valide les hypothèses et révèle les risques cachés."},

    {"id": "q36", "grade": 2, "track": "Risk", "diff": 4,
     "q": "La VaR paramétrique suppose souvent :",
     "choices": ["Des rendements suivant une loi normale",
                 "L'absence de corrélations",
                 "Une volatilité nulle",
                 "Un levier infini"],
     "answer": 0,
     "expl": "La VaR variance-covariance suppose la normalité des rendements — limite face aux queues épaisses réelles."},

    {"id": "q37", "grade": 2, "track": "Advisory", "diff": 3,
     "q": "Dans un pitch book, l'analyse de 'comparables' (comps) consiste à :",
     "choices": ["Comparer la cible à des sociétés similaires via des multiples",
                 "Calculer la VaR",
                 "Pricer une option",
                 "Estimer la duration"],
     "answer": 0,
     "expl": "Les trading/transaction comps valorisent une société par les multiples de pairs cotés ou de deals récents."},

    {"id": "q38", "grade": 2, "track": "Advisory", "diff": 4,
     "q": "Une 'fairness opinion' délivrée par une banque atteste :",
     "choices": ["Du caractère équitable du prix d'une transaction",
                 "De la solvabilité de l'acheteur",
                 "Du rating de la dette",
                 "Du montant du dividende"],
     "answer": 0,
     "expl": "La fairness opinion donne un avis indépendant sur le caractère financièrement équitable des termes d'un deal."},

    # --------------------- VP (grade 3) ---------------------------------
    {"id": "q39", "grade": 3, "track": "General", "diff": 4,
     "q": "Une courbe des taux qui s'inverse (long < court) est souvent perçue comme :",
     "choices": ["Un signal de surchauffe durable",
                 "Un signal annonciateur de ralentissement/récession",
                 "Sans signification",
                 "Une garantie de hausse des actions"],
     "answer": 1,
     "expl": "L'inversion de la courbe a historiquement précédé plusieurs récessions ; le marché anticipe des baisses de taux."},

    {"id": "q40", "grade": 3, "track": "M&A", "diff": 4,
     "q": "Dans un LBO, la 'sources & uses' équilibre :",
     "choices": ["Les revenus et les charges",
                 "Les financements mobilisés et leurs emplois (prix, frais)",
                 "Le bilan d'ouverture et de clôture",
                 "La VaR et la CVaR"],
     "answer": 1,
     "expl": "Le tableau Sources & Uses vérifie que dette + equity injectés financent exactement le prix et les frais."},

    {"id": "q41", "grade": 3, "track": "M&A", "diff": 5,
     "q": "Toutes choses égales, augmenter la part de dette dans un LBO tend à :",
     "choices": ["Réduire l'IRR equity",
                 "Augmenter l'IRR equity mais aussi le risque",
                 "N'avoir aucun effet",
                 "Supprimer le goodwill"],
     "answer": 1,
     "expl": "Plus de levier amplifie l'IRR des fonds propres si le deal réussit — au prix d'un risque de défaut accru."},

    {"id": "q42", "grade": 3, "track": "Portfolio", "diff": 4,
     "q": "L'alpha de Jensen d'un gérant représente :",
     "choices": ["Le rendement excédentaire vs ce que prédit le CAPM",
                 "Sa volatilité",
                 "Son bêta",
                 "Son tracking error"],
     "answer": 0,
     "expl": "Alpha = surperformance ajustée du risque de marché : r − [rf + β(rm − rf)]."},

    {"id": "q43", "grade": 3, "track": "Quant", "diff": 5,
     "q": "Le 'delta' d'une option call vanille est :",
     "choices": ["Toujours négatif",
                 "Compris entre 0 et 1",
                 "Égal au gamma",
                 "Indépendant du spot"],
     "answer": 1,
     "expl": "Le delta d'un call ∈ [0,1] : sensibilité du prix de l'option à une variation unitaire du sous-jacent."},

    {"id": "q44", "grade": 3, "track": "Quant", "diff": 5,
     "q": "Le 'theta' d'une option mesure :",
     "choices": ["La sensibilité à la volatilité",
                 "L'érosion de valeur avec le temps (time decay)",
                 "La sensibilité au taux",
                 "La convexité"],
     "answer": 1,
     "expl": "Theta = décroissance de la valeur de l'option à mesure que l'échéance approche, toutes choses égales."},

    {"id": "q45", "grade": 3, "track": "Risk", "diff": 5,
     "q": "Un stress test diffère de la VaR car il :",
     "choices": ["Repose sur des scénarios extrêmes définis, pas sur une probabilité",
                 "Est toujours plus faible que la VaR",
                 "Ignore les pertes",
                 "Ne s'applique qu'aux actions"],
     "answer": 0,
     "expl": "Le stress test évalue l'impact de scénarios sévères mais plausibles, complémentaire des mesures probabilistes."},

    {"id": "q46", "grade": 3, "track": "Advisory", "diff": 4,
     "q": "Dans une introduction en bourse (IPO), le 'greenshoe' permet :",
     "choices": ["De fixer le dividende",
                 "De sur-allouer des titres pour stabiliser le cours",
                 "D'annuler l'opération",
                 "De convertir la dette"],
     "answer": 1,
     "expl": "L'option de surallocation (greenshoe) laisse les banques placer jusqu'à ~15% de titres en plus pour stabiliser le marché."},

    # --------------------- DIRECTOR (grade 4) ---------------------------
    {"id": "q47", "grade": 4, "track": "General", "diff": 5,
     "q": "Le ratio de levier (Leverage Ratio) de Bâle III vise à :",
     "choices": ["Maximiser le ROE",
                 "Limiter l'endettement total indépendamment des pondérations de risque",
                 "Supprimer les fonds propres",
                 "Augmenter la VaR autorisée"],
     "answer": 1,
     "expl": "Le leverage ratio (Tier1/exposition totale) borne le levier brut, en complément des ratios pondérés du risque."},

    {"id": "q48", "grade": 4, "track": "General", "diff": 5,
     "q": "Le LCR (Liquidity Coverage Ratio) impose qu'une banque :",
     "choices": ["Détienne des actifs liquides couvrant 30 jours de sorties stressées",
                 "Ne détienne aucun cash",
                 "Maximise sa duration",
                 "Verse 100% de son résultat en dividende"],
     "answer": 0,
     "expl": "Le LCR exige un stock d'actifs liquides de haute qualité couvrant les sorties nettes sur 30 jours de stress."},

    {"id": "q49", "grade": 4, "track": "Risk", "diff": 5,
     "q": "Le risque de 'wrong-way' désigne :",
     "choices": ["Une erreur de saisie d'ordre",
                 "L'exposition qui augmente quand la qualité de la contrepartie se dégrade",
                 "Un risque de change",
                 "Un risque opérationnel pur"],
     "answer": 1,
     "expl": "Wrong-way risk : corrélation défavorable entre l'exposition et la probabilité de défaut de la contrepartie."},

    {"id": "q50", "grade": 4, "track": "M&A", "diff": 5,
     "q": "Une clause 'MAC' (Material Adverse Change) dans un SPA permet :",
     "choices": ["De renégocier le dividende",
                 "À l'acquéreur de se retirer en cas de dégradation majeure de la cible",
                 "D'augmenter le levier",
                 "De convertir des obligations"],
     "answer": 1,
     "expl": "La clause MAC autorise, sous conditions strictes, l'abandon du deal si un événement défavorable majeur survient avant closing."},

    {"id": "q51", "grade": 4, "track": "Portfolio", "diff": 5,
     "q": "Le 'risk parity' alloue le capital de sorte que :",
     "choices": ["Chaque actif pèse le même montant",
                 "Chaque actif contribue également au risque total",
                 "Le bêta soit nul",
                 "Le rendement soit maximal"],
     "answer": 1,
     "expl": "Le risk parity égalise les contributions au risque (souvent via levier sur les actifs peu volatils comme les obligations)."},

    {"id": "q52", "grade": 4, "track": "Quant", "diff": 5,
     "q": "Le 'volatility smile' désigne le fait que :",
     "choices": ["La vol implicite varie selon le strike",
                 "La vol est constante",
                 "Le delta est nul ATM",
                 "Le theta est positif"],
     "answer": 0,
     "expl": "Le smile/skew traduit que la vol implicite n'est pas constante selon le strike — contredisant l'hypothèse de Black-Scholes."},

    # --------------------- MD / PARTNER (grade 5) -----------------------
    {"id": "q53", "grade": 5, "track": "General", "diff": 5,
     "q": "Un conflit d'intérêts apparaît entre le desk de trading et un client. La conduite attendue est :",
     "choices": ["Privilégier le profit du desk",
                 "Divulguer, ériger des murailles de Chine et prioriser l'intérêt du client",
                 "Ignorer la conformité",
                 "Augmenter le levier"],
     "answer": 1,
     "expl": "La déontologie impose transparence, barrières d'information (Chinese walls) et primauté de l'intérêt du client."},

    {"id": "q54", "grade": 5, "track": "General", "diff": 5,
     "q": "Face à un risque systémique de contagion entre contreparties, un dirigeant doit surtout :",
     "choices": ["Concentrer l'exposition sur une seule contrepartie",
                 "Surveiller les expositions croisées et le collatéral, réduire la concentration",
                 "Supprimer le reporting",
                 "Maximiser le levier global"],
     "answer": 1,
     "expl": "Limiter la concentration, exiger du collatéral et suivre les expositions interconnectées réduit le risque de contagion."},

    {"id": "q55", "grade": 5, "track": "M&A", "diff": 5,
     "q": "Une 'poison pill' est une défense anti-OPA qui :",
     "choices": ["Augmente le dividende",
                 "Dilue l'acquéreur hostile en émettant des titres à prix réduit aux autres actionnaires",
                 "Rachète la dette",
                 "Réduit le capital"],
     "answer": 1,
     "expl": "La pilule empoisonnée permet aux actionnaires (hors raider) d'acheter des actions décotées, diluant l'attaquant."},

    {"id": "q56", "grade": 5, "track": "Risk", "diff": 5,
     "q": "Le 'model risk' correspond au risque :",
     "choices": ["De panne informatique",
                 "Que les modèles utilisés soient erronés ou mal calibrés",
                 "De change",
                 "De liquidité uniquement"],
     "answer": 1,
     "expl": "Le model risk naît d'hypothèses fausses, de calibrations inadaptées ou d'usages hors domaine de validité des modèles."},

    {"id": "q57", "grade": 5, "track": "Quant", "diff": 5,
     "q": "Le phénomène d'overfitting dans un backtest se traduit par :",
     "choices": ["Une stratégie robuste hors échantillon",
                 "Une performance passée flatteuse mais non reproductible en réel",
                 "Une absence totale de signal",
                 "Une volatilité nulle"],
     "answer": 1,
     "expl": "Un modèle sur-ajusté colle au bruit historique : excellent in-sample, décevant out-of-sample et en live."},

    {"id": "q58", "grade": 5, "track": "Portfolio", "diff": 5,
     "q": "Le rééquilibrage systématique d'un portefeuille tend à :",
     "choices": ["Acheter ce qui a monté, vendre ce qui a baissé",
                 "Vendre les gagnants et racheter les perdants (effet contrarian)",
                 "Supprimer tout risque",
                 "Garantir l'alpha"],
     "answer": 1,
     "expl": "Le rebalancing ramène aux poids cibles : il allège mécaniquement ce qui a surperformé et renforce ce qui a baissé."},

    # ===================== ordres conditionnels & structure de marché ====
    {"id": "q59", "grade": 1, "track": "General", "diff": 2,
     "q": "Un ordre stop-loss posé sur une position longue se déclenche quand le cours :",
     "choices": ["Descend jusqu'au seuil fixé, déclenchant une vente automatique",
                 "Monte jusqu'au seuil fixé, déclenchant un achat automatique",
                 "Ne bouge plus pendant une séance entière",
                 "Franchit sa moyenne mobile à 200 jours"],
     "answer": 0,
     "expl": "Le stop-loss vend automatiquement dès que le cours tombe au niveau de déclenchement, pour limiter une perte sans surveiller le marché en continu."},

    {"id": "q60", "grade": 1, "track": "General", "diff": 2,
     "q": "Contrairement à un stop-loss, un ordre take-profit (objectif de gain) :",
     "choices": ["Se déclenche quand le cours monte jusqu'au seuil fixé, pour sécuriser un gain",
                 "Se déclenche quand le cours baisse, pour limiter une perte",
                 "Annule automatiquement toute autre position ouverte",
                 "Ne peut être posé que sur une position courte"],
     "answer": 0,
     "expl": "Le take-profit vend dès que le cours atteint l'objectif haut fixé, verrouillant un gain sans devoir surveiller le marché en continu — symétrique du stop-loss côté hausse."},

    {"id": "q61", "grade": 0, "track": "General", "diff": 1,
     "q": "Sur les marchés actions mondiaux, les séances de cotation d'Asie, d'Europe et des Amériques :",
     "choices": ["Se chevauchent partiellement au fil de la journée, une place ouvrant avant la fermeture d'une autre",
                 "Sont toutes ouvertes exactement aux mêmes heures dans le monde entier",
                 "N'ouvrent jamais le même jour calendaire",
                 "Sont fermées en permanence sauf le vendredi"],
     "answer": 0,
     "expl": "Les fuseaux horaires décalent les séances : quand l'Asie ferme, l'Europe est déjà ouverte, puis les Amériques prennent le relais — la liquidité mondiale ne s'arrête jamais totalement."},
]


import random

# ---- accès localisé (FR / EN) ----------------------------------------------
from data.question_bank_en import QUESTIONS_EN


def _localize_question(q):
    e = QUESTIONS_EN.get(q["id"], {})
    out = dict(q)
    out["q"] = e.get("q", q["q"])
    out["choices"] = e.get("choices", q["choices"])
    out["expl"] = e.get("expl", q["expl"])
    return out


def localized(lang):
    """Renvoie la liste de questions dans la langue demandée."""
    if lang == "en":
        return [_localize_question(q) for q in QUESTIONS]
    return QUESTIONS


def available_pool(grade_index, track="General", lang="fr"):
    """Pool de questions éligibles (General + voie, jusqu'au grade visé)."""
    pool = localized(lang)
    return [q for q in pool
            if q["grade"] <= grade_index
            and (q["track"] == "General" or q["track"] == track)]


def for_grade(grade_index, track="General", count=5, rng=None, lang="fr"):
    """
    Retourne une sélection variée de questions adaptées au grade visé.

    On privilégie les questions proches du grade courant (poids plus élevé)
    tout en introduisant de l'aléatoire : deux évaluations successives au même
    grade ne posent donc pas la même série. Inclut les questions 'General' et
    celles de la voie choisie, de manière cumulative.
    """
    rng = rng or random
    pool = available_pool(grade_index, track, lang)
    if not pool:
        return []
    # poids : plus la question est proche du grade visé, plus elle est probable ;
    # on favorise aussi une difficulté en phase avec le grade.
    def weight(q):
        proximity = 1.0 / (1 + abs(q["grade"] - grade_index))
        return proximity * (1 + 0.15 * q["diff"])
    weights = [weight(q) for q in pool]
    # tirage sans remise pondéré
    chosen = []
    remaining = list(zip(pool, weights))
    n = min(count, len(pool))
    for _ in range(n):
        items, w = zip(*remaining)
        pick = rng.choices(range(len(items)), weights=w, k=1)[0]
        chosen.append(items[pick])
        remaining.pop(pick)
    return chosen
