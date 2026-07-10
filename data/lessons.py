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

    # ============ EXTENSION — concepts du master (additif) ============
    # -------------------------------- Taux ----------------------------------
    {"id": "convexity", "topic": "Taux", "title": "Convexité obligataire",
     "body": "La duration approxime la sensibilité au taux par une droite ; la "
             "convexité corrige par la courbure. Une forte convexité fait gagner "
             "plus quand les taux baissent et perdre moins quand ils montent.",
     "formula": "ΔP/P ≈ −D*·Δy + ½·Convexité·(Δy)²",
     "example": "Deux obligations de même duration : celle qui a la plus forte "
                "convexité surperforme lors d'un grand mouvement de taux.",
     "takeaway": "À duration égale, préférez la convexité quand la volatilité de taux monte."},
    {"id": "carry_roll", "topic": "Taux", "title": "Carry & roll-down",
     "body": "Le carry est le rendement gagné si le marché ne bouge pas : coupon "
             "+ roll-down (le titre « glisse » le long d'une courbe croissante et "
             "voit son yield baisser, donc son prix monter).",
     "formula": "Carry obligataire ≈ coupon + roll-down ;  Carry FX = différentiel de taux",
     "example": "Sur une courbe pentue, détenir du 5 ans rapporte même sans baisse des taux.",
     "takeaway": "Une position peut être rentable par le seul carry — mais le carry trade se retourne brutalement."},
    # ------------------------------- Dérivés --------------------------------
    {"id": "forwards", "topic": "Dérivés", "title": "Forwards, futures & cost of carry",
     "body": "Un contrat à terme fixe aujourd'hui un prix d'échange futur. Le prix "
             "forward se déduit du spot par le coût de portage (financement, "
             "moins les revenus, plus le stockage). Les futures sont standardisés "
             "et appellent de la marge.",
     "formula": "F = S·(1 + r − rendement + stockage)^T",
     "example": "Spot 100, taux 5%, 1 an, sans dividende → forward ≈ 105.",
     "takeaway": "Un écart anormal spot/forward crée une opportunité d'arbitrage (cash-and-carry)."},
    {"id": "contango", "topic": "Dérivés", "title": "Contango, backwardation & roll yield",
     "body": "La courbe des futures relie prix et maturité. En contango (futures > "
             "spot), rouler les contrats coûte (roll yield négatif) ; en "
             "backwardation (futures < spot), il rapporte.",
     "formula": "Roll yield ≈ (prix proche − prix lointain) / prix lointain",
     "example": "Un ETF pétrole en contango sous-performe le spot à cause du roll négatif.",
     "takeaway": "Sur les commodities, la structure de courbe compte autant que le spot."},
    {"id": "structured", "topic": "Dérivés", "title": "Produits structurés",
     "body": "Un produit structuré combine une brique obligataire et des options "
             "pour créer un payoff non linéaire : capital (partiellement) garanti, "
             "coupons conditionnels, barrières. Porte le risque de crédit de l'émetteur.",
     "formula": "Ex. capital garanti = zéro-coupon + call ;  reverse convertible = obligation − put vendu",
     "example": "Un autocallable est rappelé avec coupon si le sous-jacent reste au-dessus d'un seuil.",
     "takeaway": "Vérifiez toujours à QUI le produit profite : payoff, barrières et émetteur."},
    # -------------------------------- Crédit --------------------------------
    {"id": "credit_el", "topic": "Crédit", "title": "Risque de crédit : EL = PD·LGD·EAD",
     "body": "La perte attendue d'un crédit combine la probabilité de défaut (PD), "
             "la perte en cas de défaut (LGD) et l'exposition au défaut (EAD). "
             "L'approche structurelle (Merton) voit les fonds propres comme un "
             "call sur l'actif de la firme.",
     "formula": "Expected Loss = PD × LGD × EAD",
     "example": "PD 2%, LGD 45%, EAD 1M€ → perte attendue 9 000€.",
     "takeaway": "On provisionne la perte ATTENDUE ; le capital couvre la perte INATTENDUE."},
    {"id": "securitisation", "topic": "Crédit", "title": "Titrisation & tranches",
     "body": "Un pool de prêts est logé dans un SPV qui émet des titres en "
             "tranches. La cascade (waterfall) fait absorber les pertes d'abord "
             "par l'equity, puis la mezzanine, enfin le senior (subordination).",
     "formula": "Pertes : equity → mezzanine → senior ;  flux : sens inverse",
     "example": "Une hausse des défauts efface l'equity avant de toucher la mezzanine.",
     "takeaway": "Le senior paraît sûr — sauf si les défauts corrèlent plus que prévu."},
    # -------------------------------- Marché --------------------------------
    {"id": "microstructure", "topic": "Marché", "title": "Carnet d'ordres & exécution",
     "body": "Le carnet affiche bid/ask et la profondeur. Un ordre marché "
             "s'exécute vite mais subit le spread et l'impact ; un ordre limite "
             "contrôle le prix mais peut ne pas passer. Les gros ordres « mangent » "
             "plusieurs niveaux (slippage).",
     "formula": "Spread = ask − bid ;  Mid = (bid + ask)/2",
     "example": "Un ordre trop gros pour la profondeur déplace le cours contre soi.",
     "takeaway": "Adaptez le type d'ordre à la liquidité : marché si urgent, limite si patient."},
    {"id": "liquidity", "topic": "Marché", "title": "Liquidité, repo & spirale",
     "body": "La liquidité de marché (vendre sans impacter) et de financement (se "
             "refinancer via repo) se détériorent ensemble en crise. La hausse "
             "des haircuts force à apporter plus de collatéral.",
     "formula": "Spirale : baisse → pertes → appels de marge → ventes forcées → baisse",
     "example": "Un haircut qui passe de 5% à 20% double presque le collatéral exigé.",
     "takeaway": "Le levier transforme un choc de prix en problème de liquidité mortel."},
    # ----------------------------- Performance ------------------------------
    {"id": "drawdown", "topic": "Performance", "title": "Drawdown, Sortino & Calmar",
     "body": "Le max drawdown est la pire chute pic-creux subie : c'est la douleur "
             "réelle de l'investisseur. Le Sortino ne pénalise que la volatilité "
             "baissière ; le Calmar rapporte le rendement au max drawdown.",
     "formula": "Sortino = (R − cible)/σ_baissière ;  Calmar = rendement annuel / max drawdown",
     "example": "Deux stratégies à Sharpe égal : préférez celle au drawdown plus faible.",
     "takeaway": "Un bon Sharpe ne dit rien de la profondeur des creux : regardez le drawdown."},
    {"id": "twr_mwr", "topic": "Performance", "title": "TWR vs MWR",
     "body": "Le Time-Weighted Return neutralise les apports/retraits et mesure la "
             "compétence du gérant. Le Money-Weighted (IRR) intègre le timing des "
             "flux et reflète l'expérience réelle de l'investisseur.",
     "formula": "TWR = Π(1 + r_période) − 1 ;  MWR = IRR des cash flows",
     "example": "Un bon gérant peut afficher un mauvais MWR si le client investit au pire moment.",
     "takeaway": "Pour juger le gérant : TWR. Pour juger l'expérience client : MWR."},
    # ------------------------------- Facteurs -------------------------------
    {"id": "factors", "topic": "Risque", "title": "Facteurs & styles (Fama-French)",
     "body": "Au-delà du marché, des facteurs expliquent les rendements : taille "
             "(small/big), value (décoté/croissance), profitabilité, "
             "investissement. Un portefeuille porte des biais factoriels.",
     "formula": "R = α + β_marché·MKT + β_size·SMB + β_value·HML + …",
     "example": "Un fonds « value » souffre quand la growth domine, et inversement.",
     "takeaway": "Diagnostiquez les biais de style : ils expliquent la perf plus que le stock-picking."},
    # ----------------------------- Comportement -----------------------------
    {"id": "behavioural", "topic": "Comportement", "title": "Biais & finance comportementale",
     "body": "Les biais dégradent les décisions : ancrage (rester fixé sur un "
             "prix), aversion aux pertes, disposition (vendre les gagnants, garder "
             "les perdants), herding (suivre la foule, amplifier bulles et krachs).",
     "formula": "Aversion aux pertes : douleur d'une perte ≈ 2× le plaisir d'un gain équivalent",
     "example": "Garder une position perdante « pour se refaire » = disposition effect.",
     "takeaway": "Une règle écrite (stop-loss, rééquilibrage) protège de vos propres biais."},
    # --------------------------------- ESG ----------------------------------
    {"id": "esg", "topic": "ESG", "title": "ESG & finance verte",
     "body": "L'intégration ESG (environnement, social, gouvernance) gère risques "
             "et opportunités de durabilité. Les green bonds financent des projets "
             "verts ; le risque de transition vise les actifs carbonés.",
     "formula": "Approches : exclusion · best-in-class · engagement · impact",
     "example": "Un scandale de gouvernance peut faire décrocher un titre du jour au lendemain.",
     "takeaway": "L'ESG est aussi une grille de RISQUE, pas seulement d'éthique."},
    # -------------------------------- Banque --------------------------------
    {"id": "bank_ratios", "topic": "Banque", "title": "Capital, liquidité & ALM",
     "body": "Une banque doit tenir des ratios : CET1 (fonds propres durs / RWA), "
             "LCR/NSFR (liquidité), leverage ratio. L'ALM gère le risque de taux "
             "et de liquidité entre actifs et passifs (gap de duration).",
     "formula": "CET1 = fonds propres durs / RWA ;  DSCR = cash flow / service de la dette",
     "example": "Toucher un seuil réglementaire force à réduire le risque (vendre des RWA).",
     "takeaway": "Le capital absorbe les pertes ; la liquidité évite la mort subite."},
    # ------------------- Salle des marchés avancée (desks du bureau) -------
    {"id": "repo", "topic": "Taux", "title": "Le repo (pension livrée)",
     "body": "Mettre une obligation « en pension » = l'acheter en ne payant cash "
             "que le HAIRCUT (la marge), le reste étant emprunté au taux repo "
             "contre le titre en garantie. C'est le levier obligataire des desks. "
             "En crise, haircut et taux montent ensemble : l'appel de marge force "
             "à vendre au pire moment (LTCM 1998, 2008).",
     "formula": "carry equity ≈ (YTM×valeur − taux repo×emprunt) / marge",
     "example": "Haircut 3% : 1 M de collatéral pour 30 k de marge → levier ×33.",
     "takeaway": "Le repo démultiplie le carry… et le risque de liquidité."},
    {"id": "seclending", "topic": "Marché", "title": "Prêt-emprunt de titres",
     "body": "Vendre à découvert exige d'EMPRUNTER le titre : ça se paie (taux "
             "d'emprunt). Un titre rare au prêt est « hard to borrow » : petites "
             "capis, valeurs très shortées. Symétriquement, prêter ses titres "
             "longs rapporte une fraction du taux (part prêteur).",
     "formula": "coût short = valeur × taux d'emprunt × t ;  revenu prêt = taux × part prêteur",
     "example": "Short 100 k d'une small cap à 3,5%/an → ~9,6 de frais par jour.",
     "takeaway": "Un short n'est jamais gratuit à porter — comptez le borrow."},
    {"id": "money_market", "topic": "Taux", "title": "Marché monétaire & prime de terme",
     "body": "Le cash oisif doit travailler : au jour le jour (liquide, moins "
             "payé) ou en dépôt à terme (bloqué, mieux payé). L'écart entre les "
             "deux est la PRIME DE TERME : le prix de la liquidité abandonnée.",
     "formula": "taux dépôt(T) = taux directeur + prime(T) − spread",
     "example": "JJ à 2,5%, 36 pas à 3,3% : bloquer 6 mois paie 80 bp de plus.",
     "takeaway": "Ne laissez jamais dormir la trésorerie — mais gardez un coussin."},
    {"id": "cds", "topic": "Crédit", "title": "Le CDS (Credit Default Swap)",
     "body": "Assurance contre le défaut : l'acheteur de protection paie une "
             "prime (le spread) et reçoit (1 − recouvrement) × notionnel si "
             "l'évènement de crédit survient. Avant tout défaut, le CDS se trade "
             "en mark-to-market : la protection prend de la valeur quand le "
             "spread s'écarte — on trade la PEUR du défaut.",
     "formula": "MTM ≈ (spread courant − spread payé) × duration risquée × notionnel",
     "example": "Payé 150 bp, coté 250 bp, 3 ans : MTM ≈ +3% du notionnel.",
     "takeaway": "Le spread CDS et le cours de l'action bougent ensemble (Merton)."},
    {"id": "merton_credit", "topic": "Crédit", "title": "Modèle de Merton (crédit)",
     "body": "Les ACTIONS sont un call sur les actifs de l'entreprise (strike = "
             "la dette) : la même formule de Black-Scholes price une option ET "
             "un défaut. La distance au défaut (en écarts-types) donne la "
             "probabilité de défaut, donc le spread de crédit implicite.",
     "formula": "DD = [ln(V/D) + (μ − σ²/2)T] / (σ√T) ;  PD = N(−DD)",
     "example": "V=100, D=60, σ=25% → DD≈2 → PD≈2,3% à 1 an.",
     "takeaway": "Une action qui chute rapproche mécaniquement du défaut."},
    {"id": "irs", "topic": "Taux", "title": "Le swap de taux (IRS)",
     "body": "Échange de taux FIXE contre VARIABLE sur un notionnel, sans "
             "échange de principal. Le payeur de fixe gagne quand les taux "
             "montent : son DV01 est NÉGATIF — c'est la couverture d'un book "
             "obligataire sans le vendre.",
     "formula": "MTM payeur ≈ (taux courant − taux fixé) × duration × notionnel",
     "example": "Book DV01 +500/bp : un payeur 5 ans bien dimensionné l'annule.",
     "takeaway": "Le swap ajuste la duration sans toucher aux titres."},
    {"id": "convertible", "topic": "Crédit", "title": "L'obligation convertible",
     "body": "Une obligation + un call sur l'action : plancher obligataire quand "
             "l'action baisse, participation quand elle monte. Le coupon est "
             "réduit — le droit de conversion se paie. Le DELTA dit dans quel "
             "monde vit le titre (0 = obligation, ratio = action).",
     "formula": "prix = plancher obligataire + ratio × call BS",
     "example": "Arb classique : long convertible / short delta actions.",
     "takeaway": "Bond floor + equity kicker : l'hybride par excellence."},
    {"id": "microstructure_twap", "topic": "Marché", "title": "Impact de marché & TWAP",
     "body": "Un ordre paie le demi-spread ET déplace le prix (impact, croissant "
             "avec la taille rapportée à la profondeur). L'impact étant "
             "NON-LINÉAIRE, découper un gros ordre en tranches (TWAP) réduit le "
             "coût total — c'est pour ça que les desks n'exécutent jamais gros "
             "d'un bloc.",
     "formula": "coût ≈ demi-spread + k×(taille/profondeur)^α  (Almgren-Chriss)",
     "example": "Bloc 40 bp d'impact vs 8 tranches à 12 bp : l'économie se chiffre.",
     "takeaway": "Regardez le carnet (L2) avant de traiter une grosse ligne."},
    {"id": "earnings_vol", "topic": "Dérivés", "title": "Vol d'earnings & crush",
     "body": "Avant une publication de résultats, la vol implicite GONFLE "
             "(l'incertitude de l'évènement se price), puis s'effondre juste "
             "après : le « vol crush ». Acheter un straddle la veille, c'est "
             "payer cette prime — le titre doit bouger PLUS que l'implicite pour "
             "gagner.",
     "formula": "IV pré-annonce ≈ IV normale × (1 + prime d'évènement)",
     "example": "IV 25% → 34% la veille ; le lendemain, retour à 25%.",
     "takeaway": "En vol, on compare implicite PAYÉE et réalisé OBTENU."},
    {"id": "kelly", "topic": "Performance", "title": "Le critère de Kelly",
     "body": "La fraction du capital qui maximise la croissance GÉOMÉTRIQUE : "
             "f* = p − (1−p)/b. Au-delà de f*, plus de risque = MOINS de "
             "croissance ; au double de Kelly, la croissance retombe à zéro. Le "
             "demi-Kelly garde ~75% de la croissance pour bien moins de variance.",
     "formula": "f* = p − (1 − p)/b   (p = taux de réussite, b = gain/perte moyens)",
     "example": "p=55%, b=1,2 → f* ≈ 17,5% ; demi-Kelly ≈ 9%.",
     "takeaway": "Sur-risquer un edge positif suffit à se ruiner."},
    {"id": "garch", "topic": "Risque", "title": "GARCH : les grappes de volatilité",
     "body": "Fait stylisé n°1 des marchés : un jour agité est suivi de jours "
             "agités. Le GARCH(1,1) le modélise : la variance d'aujourd'hui "
             "dépend du choc d'hier (α) et de la variance d'hier (β). La "
             "prévision converge vers le long terme à vitesse (α+β)^h.",
     "formula": "σ²(t) = ω + α·r²(t−1) + β·σ²(t−1)",
     "example": "α+β=0,95 : après un choc, la vol met des semaines à retomber.",
     "takeaway": "Comparez la vol prévue à la vol implicite : cher ou bon marché ?"},
    {"id": "regimes", "topic": "Risque", "title": "Régimes de marché & inférence",
     "body": "Les marchés alternent des RÉGIMES (calme, stress) qui durent. On "
             "ne les observe pas : on les INFÈRE des rendements par un filtre "
             "bayésien à deux états, avec des transitions collantes — un mauvais "
             "jour isolé n'est pas un changement de régime.",
     "formula": "P(état|r) ∝ N(r; 0, σ_état) × Σ P(transition)×P(état précédent)",
     "example": "P(stress) > 60% plusieurs pas de suite : réduisez la voilure.",
     "takeaway": "Gérer, c'est adapter l'exposition au régime, pas au dernier jour."},
    {"id": "brinson", "topic": "Performance", "title": "Attribution Brinson",
     "body": "L'écart de performance vs le benchmark se décompose par secteur : "
             "ALLOCATION (avoir surpondéré les bons secteurs) + SÉLECTION (avoir "
             "choisi les bons titres dedans) + interaction. La somme retombe "
             "exactement sur l'écart total.",
     "formula": "alloc = (w_p−w_b)(r_b,s−r_b) ;  sél = w_b(r_p,s−r_b,s)",
     "example": "+2% d'écart = +1,5% d'allocation + 0,4% de sélection + 0,1%.",
     "takeaway": "Bon ou chanceux ? Brinson répond secteur par secteur."},
    {"id": "factor_model", "topic": "Performance", "title": "Modèle de facteurs & alpha",
     "body": "Régresser ses rendements sur des facteurs observables (marché, "
             "secteurs, régions) sépare ce que les PARIS expliquent (bêtas) de "
             "ce qui reste : l'ALPHA. Un R² très élevé signifie que le P&L n'est "
             "que des paris factoriels — pas du stock picking.",
     "formula": "r_p = α + Σ β_k·F_k + ε ;  R² = part expliquée",
     "example": "R²=95%, α≈0 : un tracker qui s'ignore.",
     "takeaway": "L'alpha se mesure APRÈS avoir retiré les facteurs."},
    {"id": "component_var", "topic": "Risque", "title": "VaR par position (Euler)",
     "body": "La VaR totale se répartit entre les lignes par contribution "
             "marginale : cov(P&L ligne, P&L total)/var(total) × VaR. Les "
             "contributions SOMMENT à la VaR totale ; une contribution négative "
             "est une couverture. Ce n'est pas la taille qui compte, c'est la "
             "corrélation au reste du book.",
     "formula": "VaR_i = β_i × VaR_totale,  β_i = cov(P&L_i, P&L_tot)/var(P&L_tot)",
     "example": "Une petite ligne très corrélée pèse plus qu'une grosse diversifiante.",
     "takeaway": "Cherchez QUI porte le risque, pas qui est le plus gros."},
    {"id": "kupiec", "topic": "Risque", "title": "Backtester sa VaR (Kupiec)",
     "body": "Un modèle de VaR se VALIDE : on compte les exceptions (jours où la "
             "perte dépasse la VaR) et on teste si leur nombre est compatible "
             "avec le niveau de confiance. Trop d'exceptions = modèle laxiste ; "
             "trop peu = modèle trop prudent (faux aussi).",
     "formula": "LR de Kupiec vs χ²(1) : rejet si LR > 3,84 (95%)",
     "example": "12 exceptions sur 100 jours à 95% (attendu 5) : rejeté.",
     "takeaway": "Une VaR jamais dépassée est aussi suspecte qu'une passoire."},
    {"id": "gamma_scalping", "topic": "Dérivés", "title": "Delta-hedge & gamma scalping",
     "body": "Un book d'options delta-hedgé ne dépend plus de la direction : son "
             "P&L = gains de GAMMA (le marché bouge, on re-hedge en achetant bas "
             "et vendant haut) − coût de THETA (le temps passe). On gagne si la "
             "vol RÉALISÉE dépasse la vol IMPLICITE payée.",
     "formula": "P&L ≈ Σ ½Γ(ΔS)² + Σ Θ·Δt   (le Δ est neutralisé)",
     "example": "Straddle hedgé : payé 25% d'IV, réalisé 32% → le gamma paie.",
     "takeaway": "Le trading de vol, c'est réalisé contre implicite."},
    {"id": "fx_carry", "topic": "Macro", "title": "Carry trade & parité couverte",
     "body": "Être long une devise à taux haut contre une devise à taux bas "
             "rapporte le DIFFÉRENTIEL chaque jour — le carry. Mais le forward "
             "cote la devise à haut taux DÉCOTÉE (parité des taux couverte) : "
             "couvert, le carry disparaît. Non couvert, il gagne petit souvent "
             "et perd gros quand la paire décroche.",
     "formula": "F = S × (1 + r_cotée·τ)/(1 + r_base·τ)",
     "example": "Différentiel 4,5%/an : ~60 par jour sur 500 k — jusqu'au −8% en crise.",
     "takeaway": "Le carry est une prime de risque, pas un repas gratuit."},
    {"id": "immunization", "topic": "Taux", "title": "Immuniser un passif",
     "body": "Pour financer un passif futur malgré les taux : construire un book "
             "obligataire dont la DURATION égale l'horizon. Au premier ordre, ce "
             "que le prix perd quand les taux montent, le réinvestissement des "
             "coupons le regagne — et réciproquement.",
     "formula": "w_court·D_court + w_long·D_long = horizon  (barbell)",
     "example": "Passif à 5 ans : 40% d'un 2 ans + 60% d'un 7 ans (durations 1,9/7,1).",
     "takeaway": "Duration = horizon : le choc de taux ne perce plus la couverture."},
    {"id": "cointegration", "topic": "Marché", "title": "Pairs trading & cointégration",
     "body": "Deux titres COINTÉGRÉS sont attachés par un élastique : leur "
             "spread est stationnaire (test d'Engle-Granger sur le résidu de la "
             "régression des log-prix). On short le spread à +2σ, on le rachète "
             "vers 0 — market-neutral. La half-life dit si l'élastique revient "
             "assez vite pour être tradé.",
     "formula": "ln A = α + β ln B + u ;  ADF sur u < −3 ⇒ cointégré",
     "example": "Half-life 8 pas : le spread revient en ~40 jours — tradable.",
     "takeaway": "Sans cointégration prouvée, un « pair » n'est qu'un double pari."},
    {"id": "vol_surface", "topic": "Dérivés", "title": "Le smile de volatilité",
     "body": "Black-Scholes suppose une vol unique ; le marché en cote une PAR "
             "STRIKE ET MATURITÉ : les ailes (surtout les puts OTM) valent plus "
             "cher — les krachs existent, les queues sont grasses. Le smile "
             "s'atténue avec la maturité (term structure).",
     "formula": "IV(K,T) : inversion de BS sur les prix cotés — la surface",
     "example": "Put 80% : IV 32% quand l'ATM cote 25% — la peur du krach se paie.",
     "takeaway": "La surface de vol EST le prix du risque extrême."},

]

TOPICS = ["Valorisation", "Risque", "Taux", "Dérivés", "Crédit", "Marché",
          "Performance", "Macro", "M&A", "Comportement", "ESG", "Banque", "Bloomberg"]


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


# ---- accès localisé (FR / EN) ---------------------------------------------
from data.lessons_en import LESSONS_EN, TOPIC_EN


def _localize_lesson(l):
    e = LESSONS_EN.get(l["id"], {})
    return {"id": l["id"], "topic": TOPIC_EN.get(l["topic"], l["topic"]),
            "title": e.get("title", l["title"]), "body": e.get("body", l["body"]),
            "formula": e.get("formula", l["formula"]),
            "example": e.get("example", l["example"]),
            "takeaway": e.get("takeaway", l["takeaway"])}


def localized(lang):
    """Renvoie (liste de leçons, liste de thèmes) dans la langue."""
    if lang == "en":
        return [_localize_lesson(l) for l in LESSONS], [TOPIC_EN.get(t, t) for t in TOPICS]
    return LESSONS, TOPICS


def get_localized(lesson_id, lang):
    l = get(lesson_id)
    if l and lang == "en":
        return _localize_lesson(l)
    return l


def title_for(lesson_id, lang):
    l = get_localized(lesson_id, lang)
    return l["title"] if l else lesson_id
