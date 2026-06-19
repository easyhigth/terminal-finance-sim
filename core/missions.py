"""
missions.py — Missions par grade (logique pure, sans pygame).

Le contenu des missions évolue avec la carrière :
  - Intern (0)    : COMPTE-RENDU — comprendre/organiser des données (texte à trous + QCM)
  - Analyst (1)   : LECTURE DE GRAPHE — tendance, rendement, volatilité
  - Associate (2) : DÉCISION — acheter / conserver / vendre
  - VP+ (3..)     : PORTEFEUILLE & HEDGING — construction et couverture

Chaque mission rapporte de la RÉPUTATION (proportionnelle au score) et un petit
honoraire. Un seuil de réputation par grade débloque l'examen de promotion (EVAL).

Structures (dicts, transitoires — non sauvegardées) :
  Item  : {kind: "fill"|"mcq", prompt, choices?, answer, tol?/abstol?, unit?, expl, chart?}
  Mission: {grade, kind, title, brief, items, reward_rep, reward_cash, charts}
"""
import math
import random

from data import question_bank


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante du jeu."""
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


# Seuil de réputation requis pour tenter l'EVAL, par grade (croissant).
def reputation_threshold(grade_index):
    return min(92, 58 + grade_index * 2)


def mission_tier(grade_index):
    """Type de mission selon le grade (échelle de 12 grades)."""
    if grade_index <= 1:        # Intern, Junior Analyst
        return "report"
    if grade_index <= 3:        # Analyst, Senior Analyst
        return "graph"
    if grade_index <= 5:        # Associate, Senior Associate
        return "decision"
    return "portfolio"          # VP et au-delà


# Réputation de base accordée pour une mission parfaite (croît avec le grade).
def _rep_base(grade_index):
    return 5 + grade_index // 2


# ---------------------------------------------------------------------------
# Helpers de construction d'items
# ---------------------------------------------------------------------------
def _mcq(prompt, choices, correct_idx, expl, rng, chart=None):
    order = list(range(len(choices)))
    rng.shuffle(order)
    shuffled = [choices[i] for i in order]
    return {"kind": "mcq", "prompt": prompt, "choices": shuffled,
            "answer": order.index(correct_idx), "expl": expl, "chart": chart}


def _fill(prompt, answer, expl, tol=0.05, abstol=None, unit="", chart=None):
    return {"kind": "fill", "prompt": prompt, "answer": float(answer),
            "tol": tol, "abstol": abstol, "unit": unit, "expl": expl, "chart": chart}


def check_fill(item, value):
    """Vrai si la valeur saisie est dans la tolérance de la réponse attendue."""
    ans = item["answer"]
    if item.get("abstol") is not None:
        return abs(value - ans) <= item["abstol"]
    return abs(value - ans) <= max(1e-9, abs(ans) * item.get("tol", 0.05))


def _bank_items(grade_index, rng, count):
    """Pioche `count` questions de la banque d'examens (déjà rng-aware, donc
    déterministe) et les adapte au format d'item de mission, pour casser la
    répétitivité des mêmes templates de question."""
    from core.i18n import get_lang
    picked = question_bank.for_grade(grade_index, "General", count, rng=rng, lang=get_lang())
    return [_mcq(q["q"], list(q["choices"]), q["answer"], q["expl"], rng) for q in picked]


def _money(value_m, cur):
    """Formate un montant exprimé EN MILLIONS, sans dépendre de pygame."""
    if abs(value_m) >= 1000:
        return f"{cur}{value_m/1000:.1f}B"
    return f"{cur}{value_m:.0f}M"


_CURRENCY = {"USA": "$", "Europe": "€", "Asia": "$"}
_SECTOR_LABELS = {
    "Tech": "Technologie", "Semicon": "Semi-conducteurs", "Luxe": "Luxe",
    "Conso": "Consommation", "Finance": "Finance", "Energie": "Énergie",
    "Sante": "Santé", "Industrie": "Industrie", "Agro": "Agroalimentaire",
    "Telecom": "Télécoms", "Utilities": "Services publics",
    "Materiaux": "Matériaux", "Immobilier": "Immobilier", "Auto": "Automobile",
}


def _sector_labels():
    """Libellés de secteur dans la langue courante."""
    from core.i18n import get_lang
    if get_lang() == "en":
        from data.missions_en import SECTOR_LABELS_EN
        return SECTOR_LABELS_EN
    return _SECTOR_LABELS


def _pick_company(market, rng, region=None, need_profit=False):
    """Choisit une société (de préférence dans la région) + ses métriques live."""
    pool = market.companies
    if region:
        regional = [c for c in pool if c["region"] == region]
        pool = regional or pool
    for _ in range(20):
        c = rng.choice(pool)
        mt = market.metrics(c["ticker"])
        if mt and (not need_profit or (mt["pe"] and mt["pe"] > 0)):
            return c, mt
    c = rng.choice(market.companies)
    return c, market.metrics(c["ticker"])


# ---------------------------------------------------------------------------
# Générateurs par type
# ---------------------------------------------------------------------------
def _gen_report(market, rng, region, grade):
    c, mt = _pick_company(market, rng, region)
    cur = _CURRENCY.get(c["region"], "$")
    cap = mt["mktcap"]   # en millions
    labels = _sector_labels()
    # 1) Capitalisation (QCM : prix × actions)
    opts = [_money(cap, cur), _money(cap * 0.45, cur),
            _money(cap * 1.8, cur), _money(cap * 0.12, cur)]
    items = [_mcq(
        _L(f"{c['ticker']} cote {mt['price']:.2f} {cur} pour {c['shares']:.0f}M d'actions. "
           f"Capitalisation boursière ≈ ?",
           f"{c['ticker']} trades at {mt['price']:.2f} {cur} for {c['shares']:.0f}M shares. "
           f"Market capitalization ≈ ?"),
        opts, 0,
        _L("Capitalisation = prix de l'action × nombre d'actions en circulation.",
           "Market cap = share price × number of shares outstanding."), rng)]
    # 2) BPA (texte à trou)
    items.append(_fill(
        _L(f"Résultat net {mt['net_income']:.0f}M {cur}, {c['shares']:.0f}M d'actions. "
           f"BPA (EPS) ≈ ? (en {cur})",
           f"Net income {mt['net_income']:.0f}M {cur}, {c['shares']:.0f}M shares. "
           f"EPS ≈ ? (in {cur})"),
        mt["eps"], _L("BPA = Résultat net / Nombre d'actions.",
                       "EPS = Net income / Number of shares."), tol=0.06, unit=cur))
    # 3) Marge nette (texte à trou)
    items.append(_fill(
        _L(f"Chiffre d'affaires {mt['revenue']:.0f}M, résultat net {mt['net_income']:.0f}M. "
           f"Marge nette ≈ ? (en %)",
           f"Revenue {mt['revenue']:.0f}M, net income {mt['net_income']:.0f}M. "
           f"Net margin ≈ ? (in %)"),
        mt["net_margin"] * 100, _L("Marge nette = Résultat net / Chiffre d'affaires.",
                                    "Net margin = Net income / Revenue."),
        abstol=1.0, unit="%"))
    # 4) Secteur (QCM)
    good = labels.get(c["sector"], c["sector"])
    distract = rng.sample([v for k, v in labels.items() if k != c["sector"]], 3)
    items.append(_mcq(
        _L(f"Dans quel secteur classez-vous {c['name']} ({c['ticker']}) ?",
           f"Which sector would you classify {c['name']} ({c['ticker']}) in?"),
        [good] + distract, 0,
        _L(f"{c['name']} relève du secteur « {good} ».",
           f"{c['name']} belongs to the '{good}' sector."), rng))
    items.extend(_bank_items(grade, rng, 2))
    return {"grade": grade, "kind": "report",
            "title": _L(f"Compte-rendu : {c['ticker']}", f"Report: {c['ticker']}"),
            "brief": _L(f"On vous transmet les données brutes de {c['name']} ({c['region']}). "
                        "Organisez-les, calculez les indicateurs clés et identifiez la société.",
                        f"You're handed raw data for {c['name']} ({c['region']}). "
                        "Organize it, compute the key indicators and identify the company."),
            "items": items, "reward_rep": _rep_base(grade), "reward_cash": 0, "charts": {}}


def _walk(rng, n, drift, vol, start):
    s = [start]
    for _ in range(n - 1):
        s.append(max(1.0, s[-1] * math.exp(rng.gauss(drift, vol))))
    return s


def _stdev_logret(series):
    rets = [math.log(series[i] / series[i - 1]) for i in range(1, len(series))]
    if len(rets) < 2:
        return 0.0
    mu = sum(rets) / len(rets)
    return math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1))


def _gen_graph(market, rng, region, grade):
    A = _walk(rng, 40, rng.uniform(-0.005, 0.007), rng.uniform(0.02, 0.05), rng.uniform(60, 200))
    B = _walk(rng, 40, rng.uniform(-0.005, 0.007), rng.uniform(0.02, 0.05), rng.uniform(60, 200))
    charts = {"A": A, "B": B}
    retA = (A[-1] / A[0] - 1) * 100
    retB = (B[-1] / B[0] - 1) * 100
    volA, volB = _stdev_logret(A), _stdev_logret(B)
    trend_fr = ("haussière" if retA > 5 else "baissière" if retA < -5 else "latérale")
    trend_en = ("upward" if retA > 5 else "downward" if retA < -5 else "sideways")
    trend = _L(trend_fr, trend_en)
    items = [
        _mcq(_L("Quelle est la tendance générale du titre A sur la période ?",
                "What is the overall trend of stock A over the period?"),
             _L(["haussière", "baissière", "latérale"], ["upward", "downward", "sideways"]),
             {"haussière": 0, "baissière": 1, "latérale": 2}.get(
                 trend_fr, {"upward": 0, "downward": 1, "sideways": 2}.get(trend_en, 2)),
             _L(f"Le titre A passe de {A[0]:.0f} à {A[-1]:.0f}, soit {retA:+.1f}% : tendance {trend}.",
                f"Stock A goes from {A[0]:.0f} to {A[-1]:.0f}, i.e. {retA:+.1f}%: {trend} trend."),
             rng, chart="A"),
        _fill(_L("Rendement total du titre A sur la période ? (en %)",
                  "Total return of stock A over the period? (in %)"),
              retA, _L("Rendement = (valeur finale / valeur initiale − 1) × 100.",
                        "Return = (final value / initial value − 1) × 100."),
              abstol=3.0, unit="%", chart="A"),
        _mcq(_L("Lequel des deux titres est le PLUS volatil ?",
                "Which of the two stocks is MORE volatile?"),
             _L(["Titre A", "Titre B"], ["Stock A", "Stock B"]), 0 if volA > volB else 1,
             _L("La volatilité se lit à l'amplitude des oscillations (écart-type des rendements).",
                "Volatility is read from the amplitude of swings (standard deviation of returns)."),
             rng, chart="AB"),
        _mcq(_L("Lequel a le mieux performé sur la période ?",
                "Which one performed better over the period?"),
             _L(["Titre A", "Titre B"], ["Stock A", "Stock B"]), 0 if retA > retB else 1,
             f"A : {retA:+.1f}%   B : {retB:+.1f}%.", rng, chart="AB"),
    ]
    items.extend(_bank_items(grade, rng, 2))
    return {"grade": grade, "kind": "graph",
            "title": _L("Lecture de graphes", "Chart reading"),
            "brief": _L("Analysez les cours fournis : tendance, performance et risque. "
                        "Un analyste doit lire un graphe d'un coup d'oeil.",
                        "Analyze the provided prices: trend, performance and risk. "
                        "An analyst must be able to read a chart at a glance."),
            "items": items, "reward_rep": _rep_base(grade), "reward_cash": 0, "charts": charts}


def _gen_decision(market, rng, region, grade):
    items = []
    cases = 0
    attempts = 0
    while cases < 3 and attempts < 30:
        attempts += 1
        c, mt = _pick_company(market, rng, region, need_profit=True)
        if not mt or not mt["pe"]:
            continue
        pe = mt["pe"]
        mom = round(rng.uniform(-18, 18), 1)   # momentum 3 mois (donné au joueur)
        if pe < 16 and mom > 1:
            ans = 0
            why = _L("P/E raisonnable et momentum positif : signal d'achat.",
                      "Reasonable P/E and positive momentum: buy signal.")
        elif pe > 38 or mom < -9:
            ans = 2
            why = _L(("Valorisation tendue (P/E élevé)" if pe > 38 else
                       "Momentum nettement négatif") + " : alléger / vendre.",
                      ("Stretched valuation (high P/E)" if pe > 38 else
                       "Clearly negative momentum") + ": trim / sell.")
        else:
            ans = 1
            why = _L("Ni signal d'achat franc ni de vente : conserver et surveiller.",
                      "Neither a clear buy nor sell signal: hold and monitor.")
        prompt = _L(
            f"{c['ticker']} ({_sector_labels().get(c['sector'], c['sector'])}) — "
            f"P/E {pe:.1f}, momentum 3 mois {mom:+.1f}%, "
            f"marge nette {mt['net_margin']*100:.0f}%. Votre décision ?",
            f"{c['ticker']} ({_sector_labels().get(c['sector'], c['sector'])}) — "
            f"P/E {pe:.1f}, 3-month momentum {mom:+.1f}%, "
            f"net margin {mt['net_margin']*100:.0f}%. Your decision?")
        items.append(_mcq(prompt, _L(["ACHETER", "CONSERVER", "VENDRE"],
                                       ["BUY", "HOLD", "SELL"]), ans, why, rng))
        cases += 1
    return {"grade": grade, "kind": "decision",
            "title": _L("Décisions d'investissement", "Investment decisions"),
            "brief": _L("Pour chaque dossier, tranchez : acheter, conserver ou vendre. "
                        "Justifiez par la valorisation (P/E) et le momentum.",
                        "For each case, decide: buy, hold or sell. "
                        "Justify using valuation (P/E) and momentum."),
            "items": items, "reward_rep": _rep_base(grade), "reward_cash": 0, "charts": {}}


# Banque de tâches portefeuille / hedging (appliquées). (prompt, choix, idx correct, expl)
_PORTFOLIO_TASKS = [
    ("Portefeuille très concentré sur la tech (bêta 1,4). Pour réduire le risque de marché :",
     ["Vendre des contrats à terme sur indice", "Doubler la position tech",
      "Acheter des small caps tech", "Ne rien faire"], 0,
     "Vendre des futures indice réduit l'exposition directionnelle (bêta) du portefeuille."),
    ("Vous détenez 8M€ d'actions et craignez une baisse court terme sans vouloir vendre. "
     "Couverture la plus ciblée :",
     ["Acheter des puts (options de vente)", "Acheter des calls",
      "Acheter l'indice", "Augmenter le levier"], 0,
     "Les puts offrent une protection à la baisse en conservant le potentiel de hausse."),
    ("Deux actifs corrélés à +0,9. Les combiner réduit-il fortement le risque ?",
     ["Non, corrélation trop élevée", "Oui, très fortement",
      "Cela double le risque", "Aucun effet sur le risque"], 0,
     "La diversification n'est efficace que si la corrélation est faible (voire négative)."),
    ("Approche 'risk parity' : on alloue de sorte que…",
     ["chaque actif contribue également au risque", "les poids en montant soient égaux",
      "le bêta soit nul", "le rendement soit maximal"], 0,
     "Le risk parity égalise les contributions au risque, pas les montants investis."),
    ("Couvrir 10M€ d'actions de bêta 1,3 avec des futures indice (bêta 1). Notionnel ≈ ?",
     ["13M€", "10M€", "7,7M€", "1,3M€"], 0,
     "Notionnel = exposition × bêta = 10M€ × 1,3 = 13M€ (hedge ajusté du bêta)."),
    ("Actifs US détenus par un fonds en euros. Couvrir le risque de change :",
     ["Vendre l'USD à terme", "Acheter des actions US supplémentaires",
      "Acheter de l'or", "Ne rien faire"], 0,
     "Vendre l'USD à terme neutralise l'exposition EUR/USD sur les actifs libellés en dollars."),
    ("Pour réduire le risque SPÉCIFIQUE (idiosyncratique) d'un portefeuille :",
     ["Diversifier sur davantage d'émetteurs", "Concentrer sur une valeur",
      "Augmenter le levier", "Acheter des calls"], 0,
     "Le risque spécifique se diversifie ; le risque de marché, lui, demeure."),
    ("Un portefeuille de bêta 0 est :",
     ["neutre au marché", "sans aucun risque", "à rendement nul", "100% en cash"], 0,
     "Bêta 0 = insensible au marché (market-neutral), mais pas dénué de tout risque."),
]


def _portfolio_tasks():
    """Banque de tâches portefeuille/hedging dans la langue courante."""
    from core.i18n import get_lang
    if get_lang() == "en":
        from data.missions_en import PORTFOLIO_TASKS_EN
        return PORTFOLIO_TASKS_EN
    return _PORTFOLIO_TASKS


def _gen_portfolio(market, rng, region, grade):
    bank = _portfolio_tasks()
    idxs = rng.sample(range(len(bank)), 4)
    chosen = [bank[i] for i in idxs]
    items = [_mcq(p, list(ch), idx, expl, rng) for (p, ch, idx, expl) in chosen]
    items.extend(_bank_items(grade, rng, 1))
    return {"grade": grade, "kind": "portfolio",
            "title": _L("Construction & couverture de portefeuille",
                        "Portfolio construction & hedging"),
            "brief": _L("Décisions d'allocation et de hedging. À ce niveau, vous arbitrez "
                        "l'exposition au risque de marché, de change et de concentration.",
                        "Allocation and hedging decisions. At this level, you manage "
                        "exposure to market, currency and concentration risk."),
            "items": items, "reward_rep": _rep_base(grade),
            "reward_cash": 0, "charts": {}}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def generate(grade_index, market, rng=None, region=None):
    """Génère une mission adaptée au grade courant (selon mission_tier)."""
    rng = rng or random
    tier = mission_tier(grade_index)
    if tier == "report":
        return _gen_report(market, rng, region, grade_index)
    if tier == "graph":
        return _gen_graph(market, rng, region, grade_index)
    if tier == "decision":
        return _gen_decision(market, rng, region, grade_index)
    return _gen_portfolio(market, rng, region, grade_index)


def grade_focus(grade_index):
    """Phrase décrivant l'objectif du grade (pour l'UI), selon le tier."""
    tier = mission_tier(grade_index)
    return _L(
        {
            "report": "Comprendre et organiser les données, produire des comptes-rendus.",
            "graph": "Lire les graphes, mesurer performance et risque.",
            "decision": "Décider d'investir, conserver ou vendre.",
            "portfolio": "Construire et couvrir des portefeuilles, arbitrer le risque.",
        }[tier],
        {
            "report": "Understand and organize data, produce reports.",
            "graph": "Read charts, measure performance and risk.",
            "decision": "Decide whether to buy, hold or sell.",
            "portfolio": "Build and hedge portfolios, manage risk.",
        }[tier],
    )


def compute_rewards(mission, correct, total):
    """Réputation + honoraire en fonction du score (ratio de bonnes réponses)."""
    ratio = correct / max(1, total)
    rep = int(round(mission["reward_rep"] * ratio))
    if correct > 0:
        rep = max(rep, 1)
    # honoraire de conseil, croissant avec le grade
    cash = round(9000 * (1 + mission["grade"]) * ratio, 2)
    return rep, cash
