"""
exam.py — Générateur d'examens de promotion (procédural, sans pygame).

Chaque grade tire un examen calibré sur le niveau réel d'un entretien technique
pour le poste visé. Les questions sont GÉNÉRÉES (modèles paramétrés) : l'espace
est immense, donc pas de répétition même en rejouant.

Types de questions :
  mcq    : choix multiple                  (clic)
  fill   : calcul chiffré (tolérance)      (saisie nombre)
  text   : définition à trous / formule    (saisie texte ; mots-clés acceptés)
  graph  : lecture de graphe               (mcq ou fill, avec une courbe)

Item (dict) :
  kind, prompt, expl
  mcq  : choices[], answer (index)
  fill : answer (float), tol|abstol, unit
  text : answers[] (réponses acceptées), keywords[] (mots requis, optionnel)
  graph: + charts {nom: série}, chart (nom à afficher), puis champs mcq/fill
"""
import math
import random
import unicodedata

PASS_THRESHOLD = 0.70


def num_questions(grade_index):
    """20 questions au grade 0, +1 par grade, plafonné à 30."""
    return min(30, 20 + grade_index)


def exam_tier(grade_index):
    """Niveau de difficulté (0 = fondamentaux ... 4 = senior/jugement)."""
    return min(4, grade_index // 2)


def bank_target(grade_index):
    """Taille-cible de la banque par grade : large en bas (variété), réduite en
    haut (questions plus dures, niveau plus rare). 1000 → 900 → ... → 300."""
    return max(300, 1000 - 100 * grade_index)


def estimated_bank(grade_index):
    """Capacité réelle (nombre de questions DISTINCTES) que les modèles du grade
    peuvent produire — somme des variantes de chaque générateur utilisé."""
    gens = TIER_GENERATORS[exam_tier(grade_index)]
    return sum(getattr(g, "variants", 200) for g in dict.fromkeys(gens))


# ---------------------------------------------------------------------------
# Helpers de construction
# ---------------------------------------------------------------------------
def _mcq(prompt, choices, correct_idx, expl, rng, chart=None, charts=None):
    order = list(range(len(choices)))
    rng.shuffle(order)
    return {"kind": "graph" if charts else "mcq", "subkind": "mcq",
            "prompt": prompt, "choices": [choices[i] for i in order],
            "answer": order.index(correct_idx), "expl": expl,
            "chart": chart, "charts": charts}


def _fill(prompt, answer, expl, tol=0.04, abstol=None, unit="", chart=None, charts=None):
    return {"kind": "graph" if charts else "fill", "subkind": "fill",
            "prompt": prompt, "answer": float(answer), "tol": tol, "abstol": abstol,
            "unit": unit, "expl": expl, "chart": chart, "charts": charts}


def _text(prompt, answers, expl, keywords=None):
    return {"kind": "text", "prompt": prompt, "answers": list(answers),
            "keywords": keywords, "expl": expl}


def _norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum())


def check_fill(item, value):
    ans = item["answer"]
    if item.get("abstol") is not None:
        return abs(value - ans) <= item["abstol"]
    return abs(value - ans) <= max(1e-9, abs(ans) * item.get("tol", 0.04))


def check_text(item, raw):
    n = _norm(raw)
    if not n:
        return False
    if item.get("keywords"):
        return all(_norm(k) in n for k in item["keywords"])
    return any(n == _norm(a) or _norm(a) in n for a in item["answers"])


def _money(rng, lo, hi, step=1):
    return rng.randrange(int(lo), int(hi), int(step))


def _walk(rng, n, drift, vol, start):
    s = [start]
    for _ in range(n - 1):
        s.append(max(1.0, s[-1] * math.exp(rng.gauss(drift, vol))))
    return s


def _stdev_logret(series):
    r = [math.log(series[i] / series[i - 1]) for i in range(1, len(series))]
    if len(r) < 2:
        return 0.0
    mu = sum(r) / len(r)
    return math.sqrt(sum((x - mu) ** 2 for x in r) / (len(r) - 1))


_FIRMS = ["Norfield", "Velcorp", "Arutech", "Kaigen", "Zenith", "Orodyne",
          "Trimark", "Lumen", "Palstone", "Vexa", "Helvia", "Solmont"]


def _firm(rng):
    return rng.choice(_FIRMS)


# ===========================================================================
# GÉNÉRATEURS — fondamentaux (tier 0 : Intern→Junior, entretien junior analyst)
# ===========================================================================
def g_eps(rng):
    ni = _money(rng, 50, 5000, 10)
    sh = _money(rng, 20, 2000, 5)
    return _fill(f"Résultat net {ni}M, {sh}M d'actions. BPA (EPS) ≈ ? (par action)",
                 ni / sh, "BPA = Résultat net / Nombre d'actions.", tol=0.03)


def g_pe(rng):
    price = round(rng.uniform(20, 400), 2)
    eps = round(rng.uniform(2, 25), 2)
    return _fill(f"Cours {price}, BPA {eps}. P/E ≈ ? (en x)",
                 price / eps, "P/E = Cours / BPA.", abstol=0.3, unit="x")


def g_net_margin(rng):
    rev = _money(rng, 200, 9000, 10)
    ni = _money(rng, 5, int(rev * 0.3), 5)
    return _fill(f"Chiffre d'affaires {rev}M, résultat net {ni}M. Marge nette ≈ ? (%)",
                 ni / rev * 100, "Marge nette = Résultat net / Chiffre d'affaires.",
                 abstol=0.6, unit="%")


def g_gross_margin(rng):
    rev = _money(rng, 200, 9000, 10)
    cogs = _money(rng, int(rev * 0.3), int(rev * 0.85), 10)
    return _fill(f"CA {rev}M, coût des ventes {cogs}M. Marge brute ≈ ? (%)",
                 (rev - cogs) / rev * 100, "Marge brute = (CA − COGS) / CA.",
                 abstol=0.6, unit="%")


def g_roe(rng):
    ni = _money(rng, 20, 2000, 10)
    eq = _money(rng, int(ni * 1.5), int(ni * 12), 10)
    return _fill(f"Résultat net {ni}M, capitaux propres {eq}M. ROE ≈ ? (%)",
                 ni / eq * 100, "ROE = Résultat net / Capitaux propres.",
                 abstol=0.6, unit="%")


def g_current_ratio(rng):
    ca = _money(rng, 100, 5000, 10)
    cl = _money(rng, 50, int(ca * 1.5), 10)
    return _fill(f"Actifs courants {ca}M, passifs courants {cl}M. Current ratio ≈ ? (x)",
                 ca / cl, "Current ratio = Actifs courants / Passifs courants.",
                 abstol=0.05, unit="x")


def g_debt_equity(rng):
    debt = _money(rng, 50, 5000, 10)
    eq = _money(rng, 50, 5000, 10)
    return _fill(f"Dette {debt}M, capitaux propres {eq}M. Ratio D/E ≈ ? (x)",
                 debt / eq, "D/E = Dette / Capitaux propres.", abstol=0.05, unit="x")


def g_div_yield(rng):
    price = round(rng.uniform(20, 300), 1)
    dps = round(rng.uniform(0.2, 10), 2)
    return _fill(f"Cours {price}, dividende par action {dps}. Rendement ≈ ? (%)",
                 dps / price * 100, "Rendement = Dividende par action / Cours.",
                 abstol=0.15, unit="%")


def g_marketcap_mcq(rng):
    price = round(rng.uniform(20, 400), 1)
    sh = _money(rng, 50, 4000, 10)
    cap = price * sh
    opts = [f"{cap/1000:.1f}B", f"{cap/1000*0.4:.1f}B",
            f"{cap/1000*1.8:.1f}B", f"{cap/1000*0.12:.1f}B"]
    return _mcq(f"{_firm(rng)} cote {price} pour {sh}M d'actions. Capitalisation ≈ ?",
                opts, 0, "Capitalisation = Cours × Nombre d'actions.", rng)


# ----- définitions à trous (texte) -----
_DEFS = [
    ("Le ___ mesure la rentabilité des capitaux propres (résultat net / capitaux propres).",
     ["ROE", "return on equity"], ["roe"]),
    ("L'___ est le résultat avant intérêts, impôts, dépréciations et amortissements.",
     ["EBITDA"], ["ebitda"]),
    ("La ___ boursière est le cours de l'action multiplié par le nombre d'actions.",
     ["capitalisation"], ["capitalisation"]),
    ("Le ___ rapporte le cours au bénéfice par action et mesure la cherté d'un titre.",
     ["PER", "P/E", "price earnings"], ["per"]),
    ("Dans un bilan, Actif = Passif + ___.",
     ["capitaux propres", "fonds propres", "equity"], ["propres"]),
    ("Le ___ libre (FCF) est le cash généré après les investissements (capex).",
     ["cash-flow", "flux de trésorerie", "free cash flow"], ["cash"]),
    ("La ___ mesure la dispersion des rendements ; c'est une mesure du risque.",
     ["volatilité"], ["volatil"]),
    ("Le ___ mesure la sensibilité d'un actif au marché (risque systématique).",
     ["bêta", "beta"], ["bet"]),
    ("La ___ consiste à répartir le risque sur des actifs peu corrélés.",
     ["diversification"], ["diversif"]),
    ("L'___ Value (EV) ajoute la dette nette à la capitalisation.",
     ["Enterprise", "entreprise"], ["enterprise"]),
]


def g_def(rng):
    prompt, answers, kw = rng.choice(_DEFS)
    return _text("Complétez : " + prompt, answers,
                 "Réponse attendue : " + answers[0] + ".", keywords=kw)


# ----- formules à compléter (sans chiffres) -----
_FORMULAS = [
    ("ROE = Résultat net / ___", ["capitaux propres", "fonds propres", "equity"], ["propres"]),
    ("Marge nette = Résultat net / ___", ["chiffre d'affaires", "ventes", "revenue"], ["affaires"]),
    ("P/E = Cours / ___", ["BPA", "bénéfice par action", "EPS"], ["bpa"]),
    ("EV = Capitalisation + ___", ["dette nette", "net debt"], ["dette"]),
    ("Current ratio = Actifs courants / ___", ["passifs courants", "current liabilities"], ["passif"]),
    ("Rendement du dividende = Dividende par action / ___", ["cours", "prix"], ["cour"]),
    ("D/E = Dette / ___", ["capitaux propres", "fonds propres", "equity"], ["propres"]),
]


def g_formula_basic(rng):
    f, answers, kw = rng.choice(_FORMULAS)
    return _text("Complétez la formule : " + f, answers,
                 "Réponse : " + answers[0] + ".", keywords=kw)


def g_concept0(rng):
    return _concept_from_bank(rng, max_grade=1)


def g_graph_trend(rng):
    n = rng.randint(24, 40)
    ret = rng.uniform(-0.012, 0.012)
    A = _walk(rng, n, ret, rng.uniform(0.02, 0.045), rng.uniform(60, 200))
    r = (A[-1] / A[0] - 1) * 100
    trend = "haussière" if r > 5 else "baissière" if r < -5 else "latérale"
    return _mcq("Quelle est la tendance générale du titre affiché ?",
                ["haussière", "baissière", "latérale"],
                {"haussière": 0, "baissière": 1, "latérale": 2}[trend],
                f"Le titre passe de {A[0]:.0f} à {A[-1]:.0f} ({r:+.1f}%) : {trend}.",
                rng, charts={"A": A}, chart="A")


# ===========================================================================
# GÉNÉRATEURS — valorisation (tier 1-2 : Analyst / Senior Analyst)
# ===========================================================================
def g_ev(rng):
    cap = _money(rng, 500, 9000, 10)
    nd = _money(rng, -300, 4000, 10)
    return _fill(f"Capitalisation {cap}M, dette nette {nd}M. EV ≈ ? (M)",
                 cap + nd, "EV = Capitalisation + Dette nette.", abstol=1, unit="M")


def g_ev_ebitda(rng):
    ev = _money(rng, 800, 12000, 10)
    ebitda = _money(rng, 80, int(ev / 5), 10)
    return _fill(f"EV {ev}M, EBITDA {ebitda}M. EV/EBITDA ≈ ? (x)",
                 ev / ebitda, "Multiple = EV / EBITDA.", abstol=0.3, unit="x")


def g_terminal_value(rng):
    fcf = _money(rng, 50, 800, 10)
    wacc = round(rng.uniform(0.07, 0.11), 3)
    g = round(rng.uniform(0.01, 0.03), 3)
    vt = fcf * (1 + g) / (wacc - g)
    return _fill(f"FCF {fcf}M, WACC {wacc*100:.1f}%, croissance terminale {g*100:.1f}%. "
                 f"Valeur terminale (Gordon) ≈ ? (M)",
                 vt, "VT = FCF×(1+g) / (WACC − g).", tol=0.03, unit="M")


def g_wacc(rng):
    we = round(rng.uniform(0.5, 0.8), 2)
    wd = round(1 - we, 2)
    re = round(rng.uniform(0.08, 0.14), 3)
    rd = round(rng.uniform(0.03, 0.07), 3)
    t = round(rng.uniform(0.20, 0.30), 2)
    wacc = we * re + wd * rd * (1 - t)
    return _fill(f"Poids fonds propres {we}, dette {wd} ; coût FP {re*100:.1f}%, "
                 f"coût dette {rd*100:.1f}%, impôt {t*100:.0f}%. WACC ≈ ? (%)",
                 wacc * 100, "WACC = We·Re + Wd·Rd·(1−impôt).", abstol=0.3, unit="%")


def g_cagr(rng):
    v0 = _money(rng, 100, 1000, 10)
    yrs = rng.randint(3, 8)
    growth = rng.uniform(0.03, 0.18)
    vN = v0 * (1 + growth) ** yrs
    return _fill(f"Une valeur passe de {v0} à {vN:.0f} en {yrs} ans. CAGR ≈ ? (%)",
                 ((vN / v0) ** (1 / yrs) - 1) * 100,
                 "CAGR = (Vf/Vi)^(1/n) − 1.", abstol=0.4, unit="%")


def g_dcf2(rng):
    cf1 = _money(rng, 50, 400, 5)
    cf2 = _money(rng, 50, 400, 5)
    r = round(rng.uniform(0.06, 0.12), 3)
    pv = cf1 / (1 + r) + cf2 / (1 + r) ** 2
    return _fill(f"Flux de {cf1} dans 1 an et {cf2} dans 2 ans, taux {r*100:.1f}%. "
                 f"Valeur actuelle ≈ ?",
                 pv, "VA = Σ CF_t / (1+r)^t.", tol=0.03)


def g_def_valo(rng):
    defs = [
        ("Le ___ actualise les flux de trésorerie futurs au WACC (valeur intrinsèque).",
         ["DCF", "discounted cash flow"], ["dcf"]),
        ("Le ___ moyen pondéré du capital sert de taux d'actualisation dans un DCF.",
         ["coût", "WACC"], ["cout"]),
        ("La valeur ___ représente la valeur des flux au-delà de l'horizon de projection.",
         ["terminale"], ["terminal"]),
        ("Une acquisition est ___ si elle augmente le BPA de l'acquéreur.",
         ["relutive", "accretive"], ["relut"]),
    ]
    p, a, k = rng.choice(defs)
    return _text("Complétez : " + p, a, "Réponse : " + a[0] + ".", keywords=k)


def g_formula_valo(rng):
    fs = [
        ("Valeur terminale = FCF×(1+g) / (WACC − ___)", ["g", "croissance"], ["g"]),
        ("WACC = We·Re + Wd·Rd·(1 − ___)", ["impôt", "taux d'impôt", "tax"], ["impo"]),
        ("EV/EBITDA : numérateur = ___", ["EV", "enterprise value"], ["ev"]),
        ("VA = CF / (1 + ___)^t", ["r", "WACC", "taux"], ["r"]),
    ]
    f, a, k = rng.choice(fs)
    return _text("Complétez la formule : " + f, a, "Réponse : " + a[0] + ".", keywords=k)


def g_concept2(rng):
    return _concept_from_bank(rng, max_grade=4)


def g_graph_return(rng):
    n = rng.randint(24, 40)
    A = _walk(rng, n, rng.uniform(-0.008, 0.01), rng.uniform(0.02, 0.05), rng.uniform(80, 200))
    r = (A[-1] / A[0] - 1) * 100
    return _fill("Rendement total du titre affiché sur la période ? (%)",
                 r, "Rendement = (Vf/Vi − 1) × 100.", abstol=2.5, unit="%",
                 charts={"A": A}, chart="A")


# ===========================================================================
# GÉNÉRATEURS — avancé (tier 3-4 : Associate / VP+, risque & dérivés)
# ===========================================================================
def g_sharpe(rng):
    rdt = round(rng.uniform(0.04, 0.20), 3)
    rf = round(rng.uniform(0.0, 0.04), 3)
    vol = round(rng.uniform(0.08, 0.25), 3)
    return _fill(f"Rendement {rdt*100:.1f}%, taux sans risque {rf*100:.1f}%, "
                 f"volatilité {vol*100:.1f}%. Ratio de Sharpe ≈ ?",
                 (rdt - rf) / vol, "Sharpe = (rendement − rf) / volatilité.", abstol=0.05)


def g_lbo_moic(rng):
    entry_eq = _money(rng, 20, 200, 5)
    exit_ev = _money(rng, int(entry_eq * 2), int(entry_eq * 8), 5)
    net_debt = _money(rng, 0, int(exit_ev * 0.5), 5)
    exit_eq = exit_ev - net_debt
    return _fill(f"Equity investi {entry_eq}, EV de sortie {exit_ev}, dette nette à la "
                 f"sortie {net_debt}. MOIC ≈ ? (x)",
                 exit_eq / entry_eq, "MOIC = Equity de sortie / Equity investi.",
                 abstol=0.1, unit="x")


def g_option_intrinsic(rng):
    K = _money(rng, 50, 200, 5)
    S = _money(rng, 30, 260, 5)
    is_call = rng.random() < 0.5
    val = max(S - K, 0) if is_call else max(K - S, 0)
    typ = "call" if is_call else "put"
    return _fill(f"Un {typ} de strike {K}, sous-jacent à {S}. Valeur intrinsèque à "
                 f"l'échéance ≈ ?",
                 val, "Call = max(S−K,0) ; Put = max(K−S,0).", abstol=0.5)


def g_var_param(rng):
    notional = _money(rng, 1, 50, 1)
    vol = round(rng.uniform(0.005, 0.03), 4)
    z = rng.choice([1.65, 2.33])
    var = notional * z * vol
    conf = "95%" if z == 1.65 else "99%"
    return _fill(f"Position {notional}M, volatilité quotidienne {vol*100:.2f}%, z({conf})={z}. "
                 f"VaR 1 jour ≈ ? (M)",
                 var, "VaR ≈ notionnel × z × volatilité.", tol=0.04, unit="M")


def g_portfolio_ret(rng):
    wa = round(rng.uniform(0.2, 0.8), 2)
    wb = round(1 - wa, 2)
    ra = round(rng.uniform(0.02, 0.15), 3)
    rb = round(rng.uniform(0.02, 0.15), 3)
    return _fill(f"Poids {wa}/{wb}, rendements {ra*100:.1f}%/{rb*100:.1f}%. "
                 f"Rendement du portefeuille ≈ ? (%)",
                 (wa * ra + wb * rb) * 100, "Rdt portefeuille = Σ w_i · r_i.",
                 abstol=0.2, unit="%")


def g_def_adv(rng):
    defs = [
        ("La ___ (VaR) est la perte non dépassée avec une forte probabilité sur un horizon.",
         ["value at risk", "VaR"], ["risk"]),
        ("La ___ (Expected Shortfall) mesure la perte moyenne au-delà de la VaR.",
         ["CVaR", "expected shortfall"], ["shortfall"]),
        ("Le ___ d'une option mesure sa sensibilité au prix du sous-jacent.",
         ["delta"], ["delta"]),
        ("Le ___ mesure l'érosion de valeur d'une option avec le temps.",
         ["thêta", "theta"], ["thet"]),
        ("Le ratio de ___ rapporte le rendement excédentaire à la volatilité.",
         ["Sharpe"], ["sharpe"]),
        ("Le ___ amplifie le rendement des fonds propres dans un LBO (et le risque).",
         ["levier", "leverage"], ["levi"]),
    ]
    p, a, k = rng.choice(defs)
    return _text("Complétez : " + p, a, "Réponse : " + a[0] + ".", keywords=k)


def g_formula_adv(rng):
    fs = [
        ("Sharpe = (rendement − rf) / ___", ["volatilité", "écart-type", "sigma"], ["volat"]),
        ("CAPM : E[r] = rf + β·(E[rm] − ___)", ["rf", "taux sans risque"], ["rf"]),
        ("MOIC = Equity de sortie / ___", ["equity investi", "capital investi"], ["investi"]),
        ("VaR ≈ notionnel × z × ___", ["volatilité", "sigma", "écart-type"], ["volat"]),
        ("Call à l'échéance = max(S − ___, 0)", ["K", "strike"], ["k"]),
    ]
    f, a, k = rng.choice(fs)
    return _text("Complétez la formule : " + f, a, "Réponse : " + a[0] + ".", keywords=k)


def g_concept_adv(rng):
    return _concept_from_bank(rng, max_grade=5)


def g_graph_vol(rng):
    n = rng.randint(28, 40)
    A = _walk(rng, n, rng.uniform(-0.005, 0.008), rng.uniform(0.015, 0.03), rng.uniform(80, 180))
    B = _walk(rng, n, rng.uniform(-0.005, 0.008), rng.uniform(0.035, 0.06), rng.uniform(80, 180))
    va, vb = _stdev_logret(A), _stdev_logret(B)
    return _mcq("Lequel des deux titres est le PLUS volatil ?", ["Titre A", "Titre B"],
                0 if va > vb else 1,
                "La volatilité se lit à l'amplitude des oscillations (écart-type des rendements).",
                rng, charts={"A": A, "B": B}, chart="AB")


# ---------------------------------------------------------------------------
# Banque conceptuelle existante (QCM) réutilisée pour la variété
# ---------------------------------------------------------------------------
def _concept_from_bank(rng, max_grade):
    from data.question_bank import QUESTIONS
    pool = [q for q in QUESTIONS if q["grade"] <= max_grade]
    if not pool:
        return g_def(rng)
    q = rng.choice(pool)
    return _mcq(q["q"], list(q["choices"]), q["answer"], q["expl"], rng)


# ---------------------------------------------------------------------------
# Composition des examens par tier
# ---------------------------------------------------------------------------
TIER_GENERATORS = {
    0: [g_eps, g_pe, g_net_margin, g_gross_margin, g_roe, g_current_ratio,
        g_debt_equity, g_div_yield, g_marketcap_mcq, g_def, g_def, g_formula_basic,
        g_formula_basic, g_concept0, g_graph_trend, g_graph_trend],
    1: [g_eps, g_pe, g_ev, g_ev_ebitda, g_net_margin, g_div_yield, g_cagr,
        g_terminal_value, g_def, g_def_valo, g_formula_basic, g_formula_valo,
        g_concept2, g_graph_trend, g_graph_return],
    2: [g_ev, g_ev_ebitda, g_wacc, g_terminal_value, g_dcf2, g_cagr,
        g_def_valo, g_def_valo, g_formula_valo, g_formula_valo, g_concept2,
        g_graph_return, g_graph_vol],
    3: [g_wacc, g_dcf2, g_terminal_value, g_lbo_moic, g_sharpe, g_option_intrinsic,
        g_def_adv, g_def_valo, g_formula_adv, g_formula_valo, g_concept_adv,
        g_graph_return, g_graph_vol],
    4: [g_sharpe, g_var_param, g_option_intrinsic, g_portfolio_ret, g_lbo_moic,
        g_dcf2, g_def_adv, g_def_adv, g_formula_adv, g_formula_adv, g_concept_adv,
        g_concept_adv, g_graph_vol],
}


# Capacité de variantes par générateur (nombre de questions distinctes possibles).
# Les calculs randomisés ont un espace énorme ; def/formule/concept sont finis.
_VARIANTS = {
    g_eps: 1800, g_pe: 1400, g_net_margin: 1500, g_gross_margin: 1500,
    g_roe: 1400, g_current_ratio: 1200, g_debt_equity: 1200, g_div_yield: 1200,
    g_marketcap_mcq: 1000, g_graph_trend: 600, g_graph_return: 600, g_graph_vol: 600,
    g_ev: 1500, g_ev_ebitda: 1200, g_terminal_value: 1500, g_wacc: 1600,
    g_cagr: 1200, g_dcf2: 1500, g_sharpe: 1600, g_lbo_moic: 1400,
    g_option_intrinsic: 1500, g_var_param: 900, g_portfolio_ret: 1400,
    g_def: len(_DEFS), g_formula_basic: len(_FORMULAS),
    g_def_valo: 4, g_formula_valo: 4, g_def_adv: 6, g_formula_adv: 5,
    g_concept0: 11, g_concept2: 25, g_concept_adv: 45,
}
for _fn, _v in _VARIANTS.items():
    _fn.variants = _v


# Mapping générateur -> leçon de l'Académie (pour le débrief des erreurs).
# Les générateurs « variés » (def/formule/concept/graphe) restent sans leçon dédiée.
GEN_LESSON = {
    "g_eps": "pe", "g_pe": "pe",
    "g_ev": "ev_ebitda", "g_ev_ebitda": "ev_ebitda", "g_marketcap_mcq": "capvsev",
    "g_terminal_value": "dcf", "g_dcf2": "dcf", "g_wacc": "dcf", "g_cagr": "dcf",
    "g_sharpe": "sharpe", "g_var_param": "var", "g_option_intrinsic": "options",
    "g_lbo_moic": "lbo", "g_portfolio_ret": "diversification", "g_graph_vol": "beta",
}


def lesson_for_item(item):
    """Renvoie l'id de leçon associé à un item (ou None)."""
    return item.get("lesson")


def generate(grade_index, rng=None, n=None, difficulty=None):
    """Génère un examen : liste d'items variés, calibrés sur le grade.
    `difficulty` force un tier (utilisé par les certifications)."""
    rng = rng or random
    tier = difficulty if difficulty is not None else exam_tier(grade_index)
    gens = TIER_GENERATORS[max(0, min(4, tier))]
    n = n or num_questions(grade_index)
    items = []
    seen = set()
    attempts = 0
    while len(items) < n and attempts < n * 12:
        attempts += 1
        gen = rng.choice(gens)
        it = gen(rng)
        if not it:
            continue
        key = it["prompt"]
        if key in seen:
            continue
        seen.add(key)
        it["lesson"] = GEN_LESSON.get(gen.__name__)   # tag pour le débrief
        items.append(it)
    return items
