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

from data.glossary_data import GLOSSARY

PASS_THRESHOLD = 0.70
_GLOSS_ITEMS = list(GLOSSARY.items())


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante du jeu."""
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


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
    return _fill(_L(f"Résultat net {ni}M, {sh}M d'actions. BPA (EPS) ≈ ? (par action)", f"Net income {ni}M, {sh}M shares. EPS ≈ ? (per share)"),
                 ni / sh, _L("BPA = Résultat net / Nombre d'actions.", "EPS = Net income / Shares."), tol=0.03)


def g_pe(rng):
    price = round(rng.uniform(20, 400), 2)
    eps = round(rng.uniform(2, 25), 2)
    return _fill(_L(f"Cours {price}, BPA {eps}. P/E ≈ ? (en x)", f"Price {price}, EPS {eps}. P/E ≈ ? (x)"),
                 price / eps, _L("P/E = Cours / BPA.", "P/E = Price / EPS."), abstol=0.3, unit="x")


def g_net_margin(rng):
    rev = _money(rng, 200, 9000, 10)
    ni = _money(rng, 5, int(rev * 0.3), 5)
    return _fill(_L(f"Chiffre d'affaires {rev}M, résultat net {ni}M. Marge nette ≈ ? (%)", f"Revenue {rev}M, net income {ni}M. Net margin ≈ ? (%)"),
                 ni / rev * 100, _L("Marge nette = Résultat net / Chiffre d'affaires.", "Net margin = Net income / Revenue."),
                 abstol=0.6, unit="%")


def g_gross_margin(rng):
    rev = _money(rng, 200, 9000, 10)
    cogs = _money(rng, int(rev * 0.3), int(rev * 0.85), 10)
    return _fill(_L(f"CA {rev}M, coût des ventes {cogs}M. Marge brute ≈ ? (%)", f"Revenue {rev}M, COGS {cogs}M. Gross margin ≈ ? (%)"),
                 (rev - cogs) / rev * 100, _L("Marge brute = (CA − COGS) / CA.", "Gross margin = (Revenue − COGS) / Revenue."),
                 abstol=0.6, unit="%")


def g_roe(rng):
    ni = _money(rng, 20, 2000, 10)
    eq = _money(rng, int(ni * 1.5), int(ni * 12), 10)
    return _fill(_L(f"Résultat net {ni}M, capitaux propres {eq}M. ROE ≈ ? (%)", f"Net income {ni}M, equity {eq}M. ROE ≈ ? (%)"),
                 ni / eq * 100, _L("ROE = Résultat net / Capitaux propres.", "ROE = Net income / Equity."),
                 abstol=0.6, unit="%")


def g_current_ratio(rng):
    ca = _money(rng, 100, 5000, 10)
    cl = _money(rng, 50, int(ca * 1.5), 10)
    return _fill(_L(f"Actifs courants {ca}M, passifs courants {cl}M. Current ratio ≈ ? (x)", f"Current assets {ca}M, current liabilities {cl}M. Current ratio ≈ ? (x)"),
                 ca / cl, _L("Current ratio = Actifs courants / Passifs courants.", "Current ratio = Current assets / Current liabilities."),
                 abstol=0.05, unit="x")


def g_debt_equity(rng):
    debt = _money(rng, 50, 5000, 10)
    eq = _money(rng, 50, 5000, 10)
    return _fill(_L(f"Dette {debt}M, capitaux propres {eq}M. Ratio D/E ≈ ? (x)", f"Debt {debt}M, equity {eq}M. D/E ≈ ? (x)"),
                 debt / eq, _L("D/E = Dette / Capitaux propres.", "D/E = Debt / Equity."), abstol=0.05, unit="x")


def g_div_yield(rng):
    price = round(rng.uniform(20, 300), 1)
    dps = round(rng.uniform(0.2, 10), 2)
    return _fill(_L(f"Cours {price}, dividende par action {dps}. Rendement ≈ ? (%)", f"Price {price}, dividend per share {dps}. Yield ≈ ? (%)"),
                 dps / price * 100, _L("Rendement = Dividende par action / Cours.", "Yield = Dividend per share / Price."),
                 abstol=0.15, unit="%")


def g_marketcap_mcq(rng):
    price = round(rng.uniform(20, 400), 1)
    sh = _money(rng, 50, 4000, 10)
    cap = price * sh
    opts = [f"{cap/1000:.1f}B", f"{cap/1000*0.4:.1f}B",
            f"{cap/1000*1.8:.1f}B", f"{cap/1000*0.12:.1f}B"]
    return _mcq(_L(f"{_firm(rng)} cote {price} pour {sh}M d'actions. Capitalisation ≈ ?", f"{_firm(rng)} trades at {price} with {sh}M shares. Market cap ≈ ?"),
                opts, 0, _L("Capitalisation = Cours × Nombre d'actions.", "Market cap = Price × Shares."), rng)


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
    prompt, answers, kw = rng.choice(_L(_DEFS, _DEFS_EN))
    return _text(_L("Complétez : ", "Fill in: ") + prompt, answers,
                 _L("Réponse attendue : ", "Expected answer: ") + answers[0] + ".", keywords=kw)


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


# ----- versions EN des banques def/formule -----
_DEFS_EN = [
    ("The ___ measures return on equity (net income / equity).", ["ROE", "return on equity"], ["roe"]),
    ("___ is earnings before interest, taxes, depreciation and amortization.", ["EBITDA"], ["ebitda"]),
    ("Market ___ is the share price times the number of shares.", ["cap", "capitalisation", "capitalization"], ["cap"]),
    ("The ___ ratio relates price to earnings per share and gauges how expensive a stock is.", ["PE", "P/E", "price earnings"], ["pe"]),
    ("On a balance sheet, Assets = Liabilities + ___.", ["equity", "shareholders equity"], ["equity"]),
    ("Free ___ flow (FCF) is the cash generated after capex.", ["cash", "cash flow", "free cash flow"], ["cash"]),
    ("___ measures the dispersion of returns; it is a risk measure.", ["volatility"], ["volat"]),
    ("___ measures an asset's sensitivity to the market (systematic risk).", ["beta"], ["beta"]),
    ("___ spreads risk across weakly-correlated assets.", ["diversification"], ["diversif"]),
    ("___ Value (EV) adds net debt to market cap.", ["Enterprise", "enterprise value"], ["enterprise"]),
]
_FORMULAS_EN = [
    ("ROE = Net income / ___", ["equity", "shareholders equity"], ["equity"]),
    ("Net margin = Net income / ___", ["revenue", "sales"], ["rev"]),
    ("P/E = Price / ___", ["EPS", "earnings per share"], ["eps"]),
    ("EV = Market cap + ___", ["net debt"], ["debt"]),
    ("Current ratio = Current assets / ___", ["current liabilities"], ["liab"]),
    ("Dividend yield = Dividend per share / ___", ["price"], ["price"]),
    ("D/E = Debt / ___", ["equity", "shareholders equity"], ["equity"]),
]


def g_formula_basic(rng):
    f, answers, kw = rng.choice(_L(_FORMULAS, _FORMULAS_EN))
    return _text(_L("Complétez la formule : ", "Complete the formula: ") + f, answers,
                 _L("Réponse : ", "Answer: ") + answers[0] + ".", keywords=kw)


def g_concept0(rng):
    return _concept_from_bank(rng, max_grade=1)


def g_graph_trend(rng):
    n = rng.randint(24, 40)
    ret = rng.uniform(-0.012, 0.012)
    A = _walk(rng, n, ret, rng.uniform(0.02, 0.045), rng.uniform(60, 200))
    r = (A[-1] / A[0] - 1) * 100
    idx = 0 if r > 5 else 1 if r < -5 else 2
    labels = _L(["haussière", "baissière", "latérale"], ["upward", "downward", "sideways"])
    return _mcq(_L("Quelle est la tendance générale du titre affiché ?",
                   "What is the overall trend of the shown stock?"),
                labels, idx,
                _L(f"Le titre passe de {A[0]:.0f} à {A[-1]:.0f} ({r:+.1f}%) : {labels[idx]}.",
                   f"The stock goes from {A[0]:.0f} to {A[-1]:.0f} ({r:+.1f}%): {labels[idx]}."),
                rng, charts={"A": A}, chart="A")


# ===========================================================================
# GÉNÉRATEURS — valorisation (tier 1-2 : Analyst / Senior Analyst)
# ===========================================================================
def g_ev(rng):
    cap = _money(rng, 500, 9000, 10)
    nd = _money(rng, -300, 4000, 10)
    return _fill(_L(f"Capitalisation {cap}M, dette nette {nd}M. EV ≈ ? (M)", f"Market cap {cap}M, net debt {nd}M. EV ≈ ? (M)"),
                 cap + nd, _L("EV = Capitalisation + Dette nette.", "EV = Market cap + Net debt."), abstol=1, unit="M")


def g_ev_ebitda(rng):
    ev = _money(rng, 800, 12000, 10)
    ebitda = _money(rng, 80, int(ev / 5), 10)
    return _fill(f"EV {ev}M, EBITDA {ebitda}M. EV/EBITDA ≈ ? (x)",
                 ev / ebitda, _L("Multiple = EV / EBITDA.", "Multiple = EV / EBITDA."), abstol=0.3, unit="x")


def g_terminal_value(rng):
    fcf = _money(rng, 50, 800, 10)
    wacc = round(rng.uniform(0.07, 0.11), 3)
    g = round(rng.uniform(0.01, 0.03), 3)
    vt = fcf * (1 + g) / (wacc - g)
    return _fill(_L(f"FCF {fcf}M, WACC {wacc*100:.1f}%, croissance terminale {g*100:.1f}%. Valeur terminale (Gordon) ≈ ? (M)", f"FCF {fcf}M, WACC {wacc*100:.1f}%, terminal growth {g*100:.1f}%. Terminal value (Gordon) ≈ ? (M)"),
                 vt, _L("VT = FCF×(1+g) / (WACC − g).", "TV = FCF×(1+g) / (WACC − g)."), tol=0.03, unit="M")


def g_wacc(rng):
    we = round(rng.uniform(0.5, 0.8), 2)
    wd = round(1 - we, 2)
    re = round(rng.uniform(0.08, 0.14), 3)
    rd = round(rng.uniform(0.03, 0.07), 3)
    t = round(rng.uniform(0.20, 0.30), 2)
    wacc = we * re + wd * rd * (1 - t)
    return _fill(_L(f"Poids fonds propres {we}, dette {wd} ; coût FP {re*100:.1f}%, coût dette {rd*100:.1f}%, impôt {t*100:.0f}%. WACC ≈ ? (%)", f"Equity weight {we}, debt {wd}; cost of equity {re*100:.1f}%, cost of debt {rd*100:.1f}%, tax {t*100:.0f}%. WACC ≈ ? (%)"),
                 wacc * 100, _L("WACC = We·Re + Wd·Rd·(1−impôt).", "WACC = We·Re + Wd·Rd·(1−tax)."), abstol=0.3, unit="%")


def g_cagr(rng):
    v0 = _money(rng, 100, 1000, 10)
    yrs = rng.randint(3, 8)
    growth = rng.uniform(0.03, 0.18)
    vN = v0 * (1 + growth) ** yrs
    return _fill(_L(f"Une valeur passe de {v0} à {vN:.0f} en {yrs} ans. CAGR ≈ ? (%)", f"A value goes from {v0} to {vN:.0f} in {yrs} years. CAGR ≈ ? (%)"),
                 ((vN / v0) ** (1 / yrs) - 1) * 100,
                 _L("CAGR = (Vf/Vi)^(1/n) − 1.", "CAGR = (Vf/Vi)^(1/n) − 1."), abstol=0.4, unit="%")


def g_dcf2(rng):
    cf1 = _money(rng, 50, 400, 5)
    cf2 = _money(rng, 50, 400, 5)
    r = round(rng.uniform(0.06, 0.12), 3)
    pv = cf1 / (1 + r) + cf2 / (1 + r) ** 2
    return _fill(_L(f"Flux de {cf1} dans 1 an et {cf2} dans 2 ans, taux {r*100:.1f}%. Valeur actuelle ≈ ?", f"Cash flows {cf1} in 1y and {cf2} in 2y, rate {r*100:.1f}%. Present value ≈ ?"),
                 pv, _L("VA = Σ CF_t / (1+r)^t.", "PV = Σ CF_t / (1+r)^t."), tol=0.03)


def g_def_valo(rng):
    from core.i18n import get_lang
    if get_lang() == "en":
        return g_def(rng)
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
    from core.i18n import get_lang
    if get_lang() == "en":
        return g_formula_basic(rng)
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
    return _fill(_L("Rendement total du titre affiché sur la période ? (%)", "Total return of the shown stock over the period? (%)"),
                 r, _L("Rendement = (Vf/Vi − 1) × 100.", "Return = (Vf/Vi − 1) × 100."), abstol=2.5, unit="%",
                 charts={"A": A}, chart="A")


# ===========================================================================
# GÉNÉRATEURS — avancé (tier 3-4 : Associate / VP+, risque & dérivés)
# ===========================================================================
def g_sharpe(rng):
    rdt = round(rng.uniform(0.04, 0.20), 3)
    rf = round(rng.uniform(0.0, 0.04), 3)
    vol = round(rng.uniform(0.08, 0.25), 3)
    return _fill(_L(f"Rendement {rdt*100:.1f}%, taux sans risque {rf*100:.1f}%, volatilité {vol*100:.1f}%. Ratio de Sharpe ≈ ?", f"Return {rdt*100:.1f}%, risk-free {rf*100:.1f}%, volatility {vol*100:.1f}%. Sharpe ratio ≈ ?"),
                 (rdt - rf) / vol, _L("Sharpe = (rendement − rf) / volatilité.", "Sharpe = (return − rf) / volatility."), abstol=0.05)


def g_lbo_moic(rng):
    entry_eq = _money(rng, 20, 200, 5)
    exit_ev = _money(rng, int(entry_eq * 2), int(entry_eq * 8), 5)
    net_debt = _money(rng, 0, int(exit_ev * 0.5), 5)
    exit_eq = exit_ev - net_debt
    return _fill(_L(f"Equity investi {entry_eq}, EV de sortie {exit_ev}, dette nette à la sortie {net_debt}. MOIC ≈ ? (x)", f"Equity invested {entry_eq}, exit EV {exit_ev}, net debt at exit {net_debt}. MOIC ≈ ? (x)"),
                 exit_eq / entry_eq, _L("MOIC = Equity de sortie / Equity investi.", "MOIC = Exit equity / Invested equity."),
                 abstol=0.1, unit="x")


def g_option_intrinsic(rng):
    K = _money(rng, 50, 200, 5)
    S = _money(rng, 30, 260, 5)
    is_call = rng.random() < 0.5
    val = max(S - K, 0) if is_call else max(K - S, 0)
    typ = "call" if is_call else "put"
    return _fill(_L(f"Un {typ} de strike {K}, sous-jacent à {S}. Valeur intrinsèque à l'échéance ≈ ?", f"A {typ} struck at {K}, underlying at {S}. Intrinsic value at expiry ≈ ?"),
                 val, _L("Call = max(S−K,0) ; Put = max(K−S,0).", "Call = max(S−K,0); Put = max(K−S,0)."), abstol=0.5)


def g_var_param(rng):
    notional = _money(rng, 1, 50, 1)
    vol = round(rng.uniform(0.005, 0.03), 4)
    z = rng.choice([1.65, 2.33])
    var = notional * z * vol
    conf = "95%" if z == 1.65 else "99%"
    return _fill(_L(f"Position {notional}M, volatilité quotidienne {vol*100:.2f}%, z({conf})={z}. VaR 1 jour ≈ ? (M)", f"Position {notional}M, daily volatility {vol*100:.2f}%, z({conf})={z}. 1-day VaR ≈ ? (M)"),
                 var, _L("VaR ≈ notionnel × z × volatilité.", "VaR ≈ notional × z × volatility."), tol=0.04, unit="M")


def g_portfolio_ret(rng):
    wa = round(rng.uniform(0.2, 0.8), 2)
    wb = round(1 - wa, 2)
    ra = round(rng.uniform(0.02, 0.15), 3)
    rb = round(rng.uniform(0.02, 0.15), 3)
    return _fill(_L(f"Poids {wa}/{wb}, rendements {ra*100:.1f}%/{rb*100:.1f}%. Rendement du portefeuille ≈ ? (%)", f"Weights {wa}/{wb}, returns {ra*100:.1f}%/{rb*100:.1f}%. Portfolio return ≈ ? (%)"),
                 (wa * ra + wb * rb) * 100, _L("Rdt portefeuille = Σ w_i · r_i.", "Portfolio return = Σ w_i · r_i."),
                 abstol=0.2, unit="%")


def g_def_adv(rng):
    from core.i18n import get_lang
    if get_lang() == "en":
        return g_def(rng)
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
    from core.i18n import get_lang
    if get_lang() == "en":
        return g_formula_basic(rng)
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
    return _mcq(_L("Lequel des deux titres est le PLUS volatil ?", "Which of the two stocks is the MORE volatile?"),
                _L(["Titre A", "Titre B"], ["Stock A", "Stock B"]),
                0 if va > vb else 1,
                _L("La volatilité se lit à l'amplitude des oscillations (écart-type des rendements).",
                   "Volatility shows in the size of the swings (standard deviation of returns)."),
                rng, charts={"A": A, "B": B}, chart="AB")


# ---------------------------------------------------------------------------
# Banque conceptuelle existante (QCM) réutilisée pour la variété
# ---------------------------------------------------------------------------
def _concept_from_bank(rng, max_grade):
    from core.i18n import get_lang
    from data.question_bank import localized
    pool = [q for q in localized(get_lang()) if q["grade"] <= max_grade]
    if not pool:
        return g_def(rng)
    q = rng.choice(pool)
    return _mcq(q["q"], list(q["choices"]), q["answer"], q["expl"], rng)


# ===========================================================================
# GÉNÉRATEURS — concepts du master (additif) : taux, dérivés, crédit,
# performance avancée, macro, banque, comportement, facteurs, glossaire.
# ===========================================================================
def g_gordon(rng):
    d1 = round(rng.uniform(1.0, 8.0), 2)
    re = rng.choice([0.07, 0.08, 0.09, 0.10, 0.11, 0.12])
    g = rng.choice([0.01, 0.02, 0.03, 0.04])
    return _fill(_L(f"Dividende attendu {d1}, coût des fonds propres {re*100:.0f}%, croissance {g*100:.0f}%. Prix par le modèle de Gordon ≈ ?", f"Expected dividend {d1}, cost of equity {re*100:.0f}%, growth {g*100:.0f}%. Gordon-model price ≈ ?"),
                 d1 / (re - g), _L("Gordon : P = D1 / (re − g).", "Gordon: P = D1 / (re − g)."), tol=0.03)


def g_forward(rng):
    S = _money(rng, 50, 400, 5)
    r = rng.choice([0.02, 0.03, 0.04, 0.05])
    T = rng.choice([1, 2, 3])
    return _fill(_L(f"Spot {S}, taux {r*100:.0f}%, {T} an(s), sans dividende. ", f"Spot {S}, rate {r*100:.0f}%, {T}y, no dividend. ") +
                 _L("Prix forward ≈ ?", "Forward price ≈ ?"), S * ((1 + r) ** T),
                 _L("Cost of carry : F = S·(1+r)^T.", "Cost of carry: F = S·(1+r)^T."), tol=0.02)


def g_real_rate(rng):
    n = rng.choice([3, 4, 5, 6, 7, 8])
    i = rng.choice([1, 2, 3, 4, 5])
    rr = ((1 + n / 100) / (1 + i / 100) - 1) * 100
    return _fill(_L(f"Taux nominal {n}%, inflation {i}%. Taux réel ≈ ? (%)", f"Nominal rate {n}%, inflation {i}%. Real rate ≈ ? (%)"),
                 rr, _L("Fisher : (1+nominal)/(1+inflation) − 1.", "Fisher: (1+nominal)/(1+inflation) − 1."), abstol=0.3, unit="%")


def g_expected_loss(rng):
    pd = rng.choice([1, 2, 3, 5, 8])
    lgd = rng.choice([30, 40, 45, 60])
    ead = _money(rng, 2, 50, 1)
    return _fill(_L(f"PD {pd}%, LGD {lgd}%, EAD {ead}M. Perte attendue (EL) ≈ ? (M)", f"PD {pd}%, LGD {lgd}%, EAD {ead}M. Expected loss (EL) ≈ ? (M)"),
                 pd / 100 * lgd / 100 * ead, _L("EL = PD × LGD × EAD.", "EL = PD × LGD × EAD."), abstol=0.05)


def g_treynor(rng):
    R = rng.choice([8, 10, 12, 14])
    beta = round(rng.uniform(0.6, 1.8), 1)
    return _fill(_L(f"Rendement {R}%, sans risque 2%, bêta {beta}. Ratio de Treynor ≈ ?", f"Return {R}%, risk-free 2%, beta {beta}. Treynor ratio ≈ ?"),
                 (R - 2) / 100 / beta, _L("Treynor = (R − rf) / β.", "Treynor = (R − rf) / β."), abstol=0.004)


def g_dscr(rng):
    cf = _money(rng, 90, 400, 10)
    ds = _money(rng, 40, int(cf), 10)
    return _fill(_L(f"Cash flow disponible {cf}M, service de la dette {ds}M. DSCR ≈ ? (x)", f"Available cash flow {cf}M, debt service {ds}M. DSCR ≈ ? (x)"),
                 cf / ds, _L("DSCR = cash flow disponible / service de la dette.", "DSCR = available cash flow / debt service."),
                 abstol=0.05, unit="x")


def g_cet1(rng):
    cap = _money(rng, 40, 220, 5)
    rwa = _money(rng, 600, 3000, 50)
    return _fill(_L(f"Fonds propres durs {cap}M, RWA {rwa}M. Ratio CET1 ≈ ? (%)", f"Core capital {cap}M, RWA {rwa}M. CET1 ratio ≈ ? (%)"),
                 cap / rwa * 100, _L("CET1 = fonds propres durs / RWA.", "CET1 = core capital / RWA."), abstol=0.3, unit="%")


def g_roll(rng):
    near = _money(rng, 80, 120, 1)
    far = _money(rng, 80, 120, 1)
    while far == near:
        far = _money(rng, 80, 120, 1)
    return _fill(_L(f"Future proche {near}, future lointain {far}. Roll yield ≈ ? (%)", f"Near future {near}, far future {far}. Roll yield ≈ ? (%)"),
                 (near - far) / far * 100,
                 _L("Roll yield = (proche − lointain) / lointain.", "Roll yield = (near − far) / far."), abstol=0.4, unit="%")


def g_drawdown(rng):
    peak = _money(rng, 100, 150, 5)
    trough = _money(rng, 50, int(peak * 0.9), 5)
    return _fill(_L(f"Une valeur nette grimpe à {peak} puis chute à {trough}. Max drawdown ≈ ? (%)", f"Net worth climbs to {peak} then falls to {trough}. Max drawdown ≈ ? (%)"), (peak - trough) / peak * 100,
                 _L("Max drawdown = (pic − creux) / pic.", "Max drawdown = (peak − trough) / peak."), abstol=0.6, unit="%")


def g_contango(rng):
    if rng.random() < 0.5:
        return _mcq(_L("Les futures cotent AU-DESSUS du spot (courbe ascendante). C'est…",
                       "Futures trade ABOVE spot (upward curve). This is…"),
                    _L(["Contango (roll yield négatif)", "Backwardation (roll yield positif)",
                        "Une inversion de la courbe des taux", "Un short squeeze"],
                       ["Contango (negative roll yield)", "Backwardation (positive roll yield)",
                        "A yield-curve inversion", "A short squeeze"]), 0,
                    _L("Futures > spot = contango ; rouler les contrats coûte.",
                       "Futures > spot = contango; rolling contracts costs."), rng)
    return _mcq(_L("Les futures cotent EN DESSOUS du spot (courbe descendante). C'est…",
                   "Futures trade BELOW spot (downward curve). This is…"),
                _L(["Backwardation (roll yield positif)", "Contango (roll yield négatif)",
                    "Un défaut de livraison", "Un dividende exceptionnel"],
                   ["Backwardation (positive roll yield)", "Contango (negative roll yield)",
                    "A delivery default", "A special dividend"]), 0,
                _L("Futures < spot = backwardation ; rouler les contrats rapporte.",
                   "Futures < spot = backwardation; rolling contracts pays."), rng)


def g_behavioural(rng):
    qs = _L([("Un investisseur vend vite ses gagnants et conserve ses perdants. Biais ?",
           ["Disposition effect", "Herding", "Carry", "Convexité"], 0,
           "Vendre les gagnants / garder les perdants = disposition effect."),
          ("Suivre le consensus et amplifier une bulle, c'est…",
           ["Herding", "Ancrage", "Best execution", "Aversion au risque"], 0,
           "Suivre la foule = herding (comportement de troupeau)."),
          ("Rester fixé sur son prix d'achat pour décider de vendre, c'est…",
           ["Biais d'ancrage", "Disposition effect", "Slippage", "Carry"], 0,
           "Se référer à un prix de référence = biais d'ancrage.")],
         [("An investor quickly sells winners and holds losers. Which bias?",
           ["Disposition effect", "Herding", "Carry", "Convexity"], 0,
           "Selling winners / keeping losers = disposition effect."),
          ("Following the consensus and amplifying a bubble is…",
           ["Herding", "Anchoring", "Best execution", "Risk aversion"], 0,
           "Following the crowd = herding."),
          ("Fixating on your purchase price to decide to sell is…",
           ["Anchoring bias", "Disposition effect", "Slippage", "Carry"], 0,
           "Referring to a reference price = anchoring bias.")])
    q = rng.choice(qs)
    return _mcq(q[0], list(q[1]), q[2], q[3], rng)


def g_factor(rng):
    qs = _L([("Un fonds surpondère les sociétés décotées (faible P/B). Style ?",
           ["Value", "Growth", "Momentum", "Quality"], 0,
           "Décoté sur ses fondamentaux = biais value."),
          ("Acheter les titres récemment les plus performants exploite le facteur…",
           ["Momentum", "Value", "Size", "Carry"], 0,
           "Continuation des performances récentes = momentum.")],
         [("A fund overweights cheap stocks (low P/B). Which style?",
           ["Value", "Growth", "Momentum", "Quality"], 0,
           "Cheap on fundamentals = value bias."),
          ("Buying recent top performers exploits the factor…",
           ["Momentum", "Value", "Size", "Carry"], 0,
           "Continuation of recent performance = momentum.")])
    q = rng.choice(qs)
    return _mcq(q[0], list(q[1]), q[2], q[3], rng)


def g_glossary(rng):
    """Pioche un terme du glossaire et demande de l'identifier d'après sa définition.
    Rend les 160+ termes du glossaire examinables."""
    from core.i18n import get_lang
    from data import glossary_data
    lang = get_lang()
    gloss, _ = glossary_data.localized(lang)
    items = list(gloss.items())
    term, (cat, definition) = rng.choice(items)
    correct = glossary_data.display_name(term, lang)
    others = [glossary_data.display_name(t, lang) for t, _ in items if t != term]
    rng.shuffle(others)
    d = definition if len(definition) < 170 else definition[:167] + "…"
    prompt = _L(f"Quel terme correspond à : « {d} »", f"Which term matches: “{d}”")
    expl = _L(f"Réponse : {correct} — catégorie {cat}.", f"Answer: {correct} — category {cat}.")
    return _mcq(prompt, [correct] + others[:3], 0, expl, rng)


# ---------------------------------------------------------------------------
# Composition des examens par tier
# ---------------------------------------------------------------------------
TIER_GENERATORS = {
    0: [g_eps, g_pe, g_net_margin, g_gross_margin, g_roe, g_current_ratio,
        g_debt_equity, g_div_yield, g_marketcap_mcq, g_def, g_def, g_formula_basic,
        g_formula_basic, g_concept0, g_graph_trend, g_graph_trend],
    1: [g_eps, g_pe, g_ev, g_ev_ebitda, g_net_margin, g_div_yield, g_cagr,
        g_terminal_value, g_def, g_def_valo, g_formula_basic, g_formula_valo,
        g_concept2, g_graph_trend, g_graph_return,
        g_forward, g_real_rate, g_glossary],
    2: [g_ev, g_ev_ebitda, g_wacc, g_terminal_value, g_dcf2, g_cagr,
        g_def_valo, g_def_valo, g_formula_valo, g_formula_valo, g_concept2,
        g_graph_return, g_graph_vol,
        g_gordon, g_contango, g_factor, g_real_rate, g_glossary],
    3: [g_wacc, g_dcf2, g_terminal_value, g_lbo_moic, g_sharpe, g_option_intrinsic,
        g_def_adv, g_def_valo, g_formula_adv, g_formula_valo, g_concept_adv,
        g_graph_return, g_graph_vol,
        g_expected_loss, g_treynor, g_roll, g_drawdown, g_behavioural,
        g_contango, g_glossary],
    4: [g_sharpe, g_var_param, g_option_intrinsic, g_portfolio_ret, g_lbo_moic,
        g_dcf2, g_def_adv, g_def_adv, g_formula_adv, g_formula_adv, g_concept_adv,
        g_concept_adv, g_graph_vol,
        g_dscr, g_cet1, g_expected_loss, g_drawdown, g_treynor, g_behavioural,
        g_glossary],
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
    # nouveaux concepts (master)
    g_gordon: 1500, g_forward: 1200, g_real_rate: 900, g_expected_loss: 1200,
    g_treynor: 1000, g_dscr: 1100, g_cet1: 1100, g_roll: 800, g_drawdown: 900,
    g_contango: 2, g_behavioural: 3, g_factor: 2, g_glossary: len(_GLOSS_ITEMS),
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
    # nouveaux concepts -> leçons de l'Académie
    "g_gordon": "dcf", "g_forward": "forwards", "g_real_rate": "rates",
    "g_expected_loss": "credit_el", "g_treynor": "beta", "g_dscr": "bank_ratios",
    "g_cet1": "bank_ratios", "g_roll": "contango", "g_contango": "contango",
    "g_behavioural": "behavioural", "g_factor": "factors", "g_drawdown": "drawdown",
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
