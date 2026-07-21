"""
governments.py — Gouvernements souverains (logique pure, sans pygame).

Chaque pays est RÉEL (nom officiel) mais reste un décor de simulation : on s'en
sert pour donner de la profondeur au marché obligataire (souverains), aux
événements politiques régionaux et aux news. Le système est pensé pour être
EXPLOITABLE, pas décoratif :

  - chaque gouvernement émet des obligations souveraines (core/bonds.py) dont le
    rendement exigé dépend de son rating, de sa dette/PIB et de sa stabilité ;
  - les événements politiques (core/politics.py) frappent une RÉGION : ils
    chocent les actions de la zone (modèle à facteurs) ET élargissent
    transitoirement les spreads de crédit régionaux (souverains + corporates),
    donc les prix obligataires bougent → opportunités de portage / achat sur repli ;
  - un historique crédible sur ~5 ans (2021→2025, inspiré du réel) est affiché
    dans l'écran PAYS (scenes/scene_governments.py) et nourrit la cohérence.

Les pays sont rattachés aux 7 RÉGIONS du moteur de marché (data/companies.py) :
USA, Am.Nord, Europe, Am.Sud, Afrique, Asia, Océanie.
"""

# Chaque gouvernement :
#   code        : identifiant court (sert de préfixe aux obligations générées)
#   name/name_en: nom officiel (FR/EN)
#   region      : région du moteur de marché (cf. data/companies.REGIONS)
#   currency    : devise
#   rating      : note souveraine (∈ core/bonds._RATING_SPREAD)
#   debt_gdp    : dette publique en % du PIB
#   stability   : stabilité politique 0..1 (1 = très stable)
#   regime      : type de régime / nature politique (libellé court)
#   gen_mats    : maturités d'obligations à GÉNÉRER (en années) ; vide si le pays
#                 est déjà couvert par une obligation « benchmark » curatée
#   bench_bonds : ids d'obligations benchmark curatées rattachées (core/bonds)
#   history     : chronologie 5 ans [{"y", "kind", "fr", "en"}]
GOVERNMENTS = [
    # ----------------------------------------------------------------- USA
    {"code": "US", "name": "États-Unis", "name_en": "United States",
     "region": "USA", "currency": "USD", "rating": "AAA",
     "debt_gdp": 122, "stability": 0.85, "regime": "République fédérale",
     "gen_mats": [30], "bench_bonds": ["UST2", "UST10"],
     "history": [
        {"y": 2021, "kind": "good", "fr": "Reprise post-pandémie dopée par un vaste plan de relance budgétaire.",
         "en": "Post-pandemic rebound fueled by a vast fiscal stimulus."},
        {"y": 2022, "kind": "bad", "fr": "Inflation au plus haut depuis 40 ans (~9%) ; la Fed enclenche un cycle de hausses agressif.",
         "en": "Inflation at a 40-year high (~9%); the Fed launches an aggressive hiking cycle."},
        {"y": 2023, "kind": "bad", "fr": "Faillites de banques régionales (stress de liquidité) et bras de fer sur le plafond de la dette.",
         "en": "Regional bank failures (liquidity stress) and a debt-ceiling standoff."},
        {"y": 2024, "kind": "good", "fr": "Désinflation et essor de l'IA propulsent les actions ; premières baisses de taux.",
         "en": "Disinflation and the AI surge lift equities; first rate cuts."},
        {"y": 2025, "kind": "info", "fr": "Atterrissage en douceur, mais déficit budgétaire et charge de la dette élevés.",
         "en": "Soft landing, but a large fiscal deficit and high debt-servicing burden."},
     ]},
    # ----------------------------------------------------------------- Am.Nord
    {"code": "CA", "name": "Canada", "name_en": "Canada",
     "region": "Am.Nord", "currency": "CAD", "rating": "AAA",
     "debt_gdp": 106, "stability": 0.88, "regime": "Monarchie parlementaire",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Inflation importée ; la Banque du Canada relève fortement ses taux.",
         "en": "Imported inflation; the Bank of Canada hikes sharply."},
        {"y": 2023, "kind": "bad", "fr": "Marché immobilier sous pression sous l'effet des taux élevés.",
         "en": "Housing market under pressure from high rates."},
        {"y": 2024, "kind": "good", "fr": "Ralentissement de l'inflation ; début des baisses de taux.",
         "en": "Cooling inflation; rate cuts begin."},
        {"y": 2025, "kind": "info", "fr": "Économie dépendante de l'énergie et des matières premières.",
         "en": "Economy dependent on energy and commodities."},
     ]},
    # ----------------------------------------------------------------- Europe
    {"code": "DE", "name": "Allemagne", "name_en": "Germany",
     "region": "Europe", "currency": "EUR", "rating": "AAA",
     "debt_gdp": 64, "stability": 0.88, "regime": "République fédérale",
     "gen_mats": [2], "bench_bonds": ["BUND10"],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Choc énergétique : la fin du gaz russe fait flamber les coûts industriels.",
         "en": "Energy shock: the end of Russian gas sends industrial costs soaring."},
        {"y": 2023, "kind": "bad", "fr": "Récession technique ; l'industrie manufacturière cale.",
         "en": "Technical recession; manufacturing stalls."},
        {"y": 2024, "kind": "info", "fr": "Stagnation et débat sur le frein constitutionnel à l'endettement.",
         "en": "Stagnation and debate over the constitutional debt brake."},
        {"y": 2025, "kind": "good", "fr": "Reprise fragile portée par l'export et la baisse de l'inflation.",
         "en": "Fragile recovery led by exports and falling inflation."},
     ]},
    {"code": "FR", "name": "France", "name_en": "France",
     "region": "Europe", "currency": "EUR", "rating": "AA",
     "debt_gdp": 112, "stability": 0.76, "regime": "République semi-présidentielle",
     "gen_mats": [2], "bench_bonds": ["OAT10"],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Inflation énergétique ; bouclier tarifaire coûteux pour le budget.",
         "en": "Energy inflation; a costly price-cap shield weighs on the budget."},
        {"y": 2023, "kind": "bad", "fr": "Réforme des retraites adoptée sur fond de fortes tensions sociales.",
         "en": "Pension reform passed amid major social unrest."},
        {"y": 2024, "kind": "bad", "fr": "Dégradation budgétaire : le spread OAT-Bund se tend, dette dégradée.",
         "en": "Budget deterioration: the OAT-Bund spread widens, debt downgraded."},
        {"y": 2025, "kind": "info", "fr": "Incertitude politique et débats budgétaires récurrents.",
         "en": "Political uncertainty and recurring budget standoffs."},
     ]},
    {"code": "GB", "name": "Royaume-Uni", "name_en": "United Kingdom",
     "region": "Europe", "currency": "GBP", "rating": "AA",
     "debt_gdp": 100, "stability": 0.74, "regime": "Monarchie parlementaire",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "« Mini-budget » non financé : krach des gilts, intervention de la banque centrale.",
         "en": "Unfunded 'mini-budget': gilt crash, central-bank intervention."},
        {"y": 2023, "kind": "bad", "fr": "Inflation tenace, parmi les plus élevées du G7.",
         "en": "Sticky inflation, among the highest in the G7."},
        {"y": 2024, "kind": "info", "fr": "Élections : alternance et promesse de stabilité budgétaire.",
         "en": "Elections: change of government promising fiscal stability."},
        {"y": 2025, "kind": "good", "fr": "Consolidation budgétaire et désinflation progressive.",
         "en": "Fiscal consolidation and gradual disinflation."},
     ]},
    {"code": "IT", "name": "Italie", "name_en": "Italy",
     "region": "Europe", "currency": "EUR", "rating": "BBB",
     "debt_gdp": 138, "stability": 0.66, "regime": "République parlementaire",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "info", "fr": "Nouveau gouvernement ; les marchés surveillent le spread BTP-Bund.",
         "en": "New government; markets watch the BTP-Bund spread."},
        {"y": 2023, "kind": "bad", "fr": "Dette parmi les plus élevées d'Europe (~140% du PIB).",
         "en": "Debt among the highest in Europe (~140% of GDP)."},
        {"y": 2024, "kind": "good", "fr": "Déploiement des fonds de relance européens (PNRR).",
         "en": "Rollout of EU recovery funds (NRRP)."},
        {"y": 2025, "kind": "info", "fr": "Croissance molle mais spreads contenus.",
         "en": "Sluggish growth but contained spreads."},
     ]},
    {"code": "ES", "name": "Espagne", "name_en": "Spain",
     "region": "Europe", "currency": "EUR", "rating": "A",
     "debt_gdp": 105, "stability": 0.74, "regime": "Monarchie parlementaire",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Inflation poussée par l'énergie ; mesures de soutien au pouvoir d'achat.",
         "en": "Energy-driven inflation; purchasing-power support measures."},
        {"y": 2023, "kind": "info", "fr": "Élections serrées et négociations de coalition.",
         "en": "Tight elections and coalition negotiations."},
        {"y": 2024, "kind": "good", "fr": "Croissance solide tirée par le tourisme et les services.",
         "en": "Solid growth driven by tourism and services."},
        {"y": 2025, "kind": "good", "fr": "Chômage en recul, surperformance dans la zone euro.",
         "en": "Falling unemployment, outperforming the euro area."},
     ]},
    # ----------------------------------------------------------------- Am.Sud
    {"code": "BR", "name": "Brésil", "name_en": "Brazil",
     "region": "Am.Sud", "currency": "BRL", "rating": "BB",
     "debt_gdp": 86, "stability": 0.60, "regime": "République présidentielle",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "info", "fr": "Élection présidentielle très serrée et polarisée.",
         "en": "Very tight and polarized presidential election."},
        {"y": 2023, "kind": "bad", "fr": "Taux directeur (Selic) parmi les plus élevés au monde ; nouveau cadre budgétaire.",
         "en": "Policy rate (Selic) among the world's highest; new fiscal framework."},
        {"y": 2024, "kind": "good", "fr": "Baisses de taux et cours porteurs des matières premières.",
         "en": "Rate cuts and supportive commodity prices."},
        {"y": 2025, "kind": "info", "fr": "Inflation et trajectoire de dette sous surveillance des marchés.",
         "en": "Inflation and debt path under market scrutiny."},
     ]},
    {"code": "AR", "name": "Argentine", "name_en": "Argentina",
     "region": "Am.Sud", "currency": "ARS", "rating": "B",
     "debt_gdp": 85, "stability": 0.42, "regime": "République présidentielle",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Inflation à trois chiffres et contrôle strict des changes.",
         "en": "Triple-digit inflation and strict capital controls."},
        {"y": 2023, "kind": "info", "fr": "Élection : débat sur la dollarisation et un plan de choc.",
         "en": "Election: debate over dollarization and a shock plan."},
        {"y": 2024, "kind": "bad", "fr": "Austérité sévère et dévaluation pour assainir les comptes.",
         "en": "Severe austerity and devaluation to repair public finances."},
        {"y": 2025, "kind": "good", "fr": "Désinflation douloureuse mais réelle ; retour prudent des investisseurs.",
         "en": "Painful but real disinflation; cautious return of investors."},
     ]},
    # ----------------------------------------------------------------- Afrique
    {"code": "ZA", "name": "Afrique du Sud", "name_en": "South Africa",
     "region": "Afrique", "currency": "ZAR", "rating": "BB",
     "debt_gdp": 75, "stability": 0.55, "regime": "République parlementaire",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Délestages électriques massifs : la production d'Eskom étrangle l'activité.",
         "en": "Massive load-shedding: Eskom's power shortfalls choke activity."},
        {"y": 2023, "kind": "bad", "fr": "Croissance quasi nulle et monnaie sous pression.",
         "en": "Near-zero growth and currency under pressure."},
        {"y": 2024, "kind": "info", "fr": "Gouvernement de coalition après des élections charnières.",
         "en": "Coalition government after pivotal elections."},
        {"y": 2025, "kind": "good", "fr": "Réformes du secteur électrique : espoir de reprise.",
         "en": "Power-sector reforms: hopes of a recovery."},
     ]},
    {"code": "NG", "name": "Nigéria", "name_en": "Nigeria",
     "region": "Afrique", "currency": "NGN", "rating": "B",
     "debt_gdp": 47, "stability": 0.45, "regime": "République fédérale présidentielle",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "info", "fr": "Économie très dépendante des recettes pétrolières.",
         "en": "Economy heavily reliant on oil revenues."},
        {"y": 2023, "kind": "bad", "fr": "Fin de la subvention aux carburants et forte dévaluation du naira.",
         "en": "End of fuel subsidies and a sharp naira devaluation."},
        {"y": 2024, "kind": "bad", "fr": "Inflation élevée frappant le pouvoir d'achat.",
         "en": "High inflation hitting purchasing power."},
        {"y": 2025, "kind": "good", "fr": "Réformes soutenues par le FMI ; stabilisation progressive.",
         "en": "IMF-backed reforms; gradual stabilization."},
     ]},
    # ----------------------------------------------------------------- Asia
    {"code": "JP", "name": "Japon", "name_en": "Japan",
     "region": "Asia", "currency": "JPY", "rating": "A",
     "debt_gdp": 255, "stability": 0.82, "regime": "Monarchie constitutionnelle",
     "gen_mats": [2], "bench_bonds": ["JGB10"],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Yen très faible face au dollar sous l'effet de l'écart de taux.",
         "en": "Very weak yen versus the dollar amid the rate gap."},
        {"y": 2023, "kind": "info", "fr": "Retour de l'inflation après des décennies de déflation.",
         "en": "Inflation returns after decades of deflation."},
        {"y": 2024, "kind": "good", "fr": "La Banque du Japon met fin aux taux négatifs : tournant historique.",
         "en": "The Bank of Japan ends negative rates: a historic turn."},
        {"y": 2025, "kind": "info", "fr": "Normalisation monétaire prudente ; dette publique colossale.",
         "en": "Cautious monetary normalization; colossal public debt."},
     ]},
    {"code": "CN", "name": "Chine", "name_en": "China",
     "region": "Asia", "currency": "CNY", "rating": "A",
     "debt_gdp": 84, "stability": 0.70, "regime": "État à parti unique",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Confinements stricts : chaînes d'approvisionnement et consommation grippées.",
         "en": "Strict lockdowns: supply chains and consumption disrupted."},
        {"y": 2023, "kind": "bad", "fr": "Crise immobilière (défauts de promoteurs) ; reprise post-COVID molle.",
         "en": "Property crisis (developer defaults); a weak post-COVID recovery."},
        {"y": 2024, "kind": "info", "fr": "Relances ciblées et tensions commerciales avec l'Occident.",
         "en": "Targeted stimulus and trade tensions with the West."},
        {"y": 2025, "kind": "bad", "fr": "Pressions déflationnistes persistantes sous surveillance.",
         "en": "Persistent deflationary pressures under watch."},
     ]},
    {"code": "IN", "name": "Inde", "name_en": "India",
     "region": "Asia", "currency": "INR", "rating": "BBB",
     "debt_gdp": 82, "stability": 0.70, "regime": "République parlementaire fédérale",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "good", "fr": "Croissance parmi les plus fortes des grandes économies.",
         "en": "Among the fastest growth of the major economies."},
        {"y": 2023, "kind": "info", "fr": "La banque centrale (RBI) relève ses taux pour contenir l'inflation.",
         "en": "The central bank (RBI) hikes rates to contain inflation."},
        {"y": 2024, "kind": "good", "fr": "Élections : continuité des réformes et de l'investissement.",
         "en": "Elections: continuity of reforms and investment."},
        {"y": 2025, "kind": "good", "fr": "Montée en puissance comme hub manufacturier alternatif.",
         "en": "Rising as an alternative manufacturing hub."},
     ]},
    {"code": "KR", "name": "Corée du Sud", "name_en": "South Korea",
     "region": "Asia", "currency": "KRW", "rating": "AA",
     "debt_gdp": 52, "stability": 0.78, "regime": "République présidentielle",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "Won faible et repli du cycle des semi-conducteurs.",
         "en": "Weak won and a downturn in the semiconductor cycle."},
        {"y": 2023, "kind": "bad", "fr": "Ralentissement des exportations de puces, moteur de l'économie.",
         "en": "Slowing chip exports, the economy's engine."},
        {"y": 2024, "kind": "good", "fr": "Rebond porté par la mémoire et la demande liée à l'IA.",
         "en": "Rebound driven by memory chips and AI-related demand."},
        {"y": 2025, "kind": "info", "fr": "Économie très exposée à la demande mondiale et aux tensions régionales.",
         "en": "Economy highly exposed to global demand and regional tensions."},
     ]},
    # ----------------------------------------------------------------- Océanie
    {"code": "AU", "name": "Australie", "name_en": "Australia",
     "region": "Océanie", "currency": "AUD", "rating": "AAA",
     "debt_gdp": 50, "stability": 0.88, "regime": "Monarchie parlementaire fédérale",
     "gen_mats": [2, 10], "bench_bonds": [],
     "history": [
        {"y": 2022, "kind": "bad", "fr": "La banque centrale (RBA) relève ses taux face à l'inflation.",
         "en": "The central bank (RBA) hikes rates against inflation."},
        {"y": 2023, "kind": "info", "fr": "Immobilier sensible aux taux ; ménages endettés.",
         "en": "Rate-sensitive housing; indebted households."},
        {"y": 2024, "kind": "info", "fr": "Économie liée à la demande chinoise (minerai de fer, GNL).",
         "en": "Economy tied to Chinese demand (iron ore, LNG)."},
        {"y": 2025, "kind": "good", "fr": "Transition énergétique et exportations de matières critiques.",
         "en": "Energy transition and critical-mineral exports."},
     ]},
]

_BY_CODE = {g["code"]: g for g in GOVERNMENTS}


def get(code):
    return _BY_CODE.get(code)


def by_region(region):
    return [g for g in GOVERNMENTS if g["region"] == region]


def all_codes():
    return [g["code"] for g in GOVERNMENTS]


def localized_name(gov, lang="fr"):
    return gov["name_en"] if lang == "en" else gov["name"]


def country_premium(gov):
    """Prime de risque pays STATIQUE (en décimal de rendement) ajoutée au spread
    de rating : reflète l'instabilité politique et le poids de la dette.
    Deux pays de même rating peuvent ainsi diverger (ex. Italie vs Espagne)."""
    if gov is None:
        return 0.0
    instab = (1.0 - gov.get("stability", 0.8)) * 0.020      # jusqu'à ~200 bps si très instable
    debt = max(0.0, gov.get("debt_gdp", 60) - 60) / 100.0 * 0.004
    return round(instab + debt, 4)


def stability_label(stability):
    from core.i18n import get_lang
    en = get_lang() == "en"
    if stability >= 0.82:
        return "Very stable" if en else "Très stable"
    if stability >= 0.68:
        return "Stable"
    if stability >= 0.52:
        return "Fragile"
    return "Unstable" if en else "Instable"
