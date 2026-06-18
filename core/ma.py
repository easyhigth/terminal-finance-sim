"""
ma.py — Module M&A : acquisition de cibles privées, financement LBO réel
(cash + dette), pilotage d'axes d'amélioration, évolution trimestrielle et
sortie (exit). Logique pure (aucun pygame), testable indépendamment.

Principes de simulation (pensés pour « avoir du sens, comme dans la vraie
vie ») :
  - Une cible a un management, une ambiance (morale) et une efficacité
    opérationnelle. Ces trois scores pilotent la croissance organique et la
    marge — un management/équipe en bonne santé fait mieux performer
    l'entreprise, une équipe démoralisée/mal gérée dégrade la performance et
    expose à des incidents (grève, perte de client clé, défaut qualité…).
  - Sans investissement continu, les scores se ré-érodent vers une moyenne
    (60/100) : l'amélioration n'est pas acquise pour toujours, il faut
    l'entretenir — comme une vraie organisation.
  - L'acquisition est financée en cash + dette (LBO) : la dette est portée
    par la société elle-même (intérêts + amortissement prélevés sur SON flux
    de trésorerie propre, pas directement sur le cash du joueur). Si le cash-
    flow de la cible ne suffit plus, le joueur doit éponger le manque sur son
    propre cash ; à défaut, la société part en défaut et l'equity investi est
    perdu (créanciers reprennent la société) — risque réel du LBO sous-capitalisé.
  - Le surplus de trésorerie au-delà d'un coussin de sécurité est reversé au
    joueur (cash sweep), comme un dividende de LBO.
  - Une seule action d'amélioration (positive ou négative) par trimestre et
    par société détenue.
"""
import random

from core import config
from core import financials as F
from core import finmath as fm
from data.ma_targets import TARGETS_BY_TICKER, all_targets

TAX_RATE = 0.25
CAPEX_PCT = 0.04                 # capex de maintenance (% du CA)
DEBT_RATE_ANNUAL = 0.10          # coût de la dette LBO
DEBT_AMORT_ANNUAL = 0.16         # amortissement annuel cible (% du principal)
MAX_DEBT_PCT = 0.85
CONTROL_PREMIUM = 0.06           # prime de contrôle sur la valorisation de comps
EXIT_FEE = 0.02
CASH_BUFFER_TARGET_PCT = 0.10    # coussin de trésorerie cible (% du CA)
DISTRESS_THRESHOLD_PCT = -0.20   # seuil de détresse (% du CA, cash_buffer négatif)
SCORE_MEAN = 60.0
SCORE_REVERT = 0.06              # part de l'écart à la moyenne résorbée /trimestre


def get_target(ticker):
    return TARGETS_BY_TICKER.get(ticker)


def owned_tickers(player):
    return list(getattr(player, "ma_owned", {}) or {})


def is_taken(player, ticker):
    """Vrai si la cible est déjà détenue, a déjà été acquise puis cédée/perdue
    (catalogue à occasion unique : pas de rachat de la même cible deux fois),
    ou a été revendiquée par un rival (cf. core/rivals.py::act, branche
    "claim_target")."""
    if ticker in (getattr(player, "ma_owned", None) or {}):
        return True
    for h in (getattr(player, "ma_history", None) or []):
        if h["ticker"] == ticker:
            return True
    if ticker in (getattr(player, "rival_owned_targets", None) or []):
        return True
    return False


def available_targets(player):
    return [t for t in all_targets() if not is_taken(player, t["ticker"])]


# --------------------------------------------------------------------- valorisation
def _ebitda(revenue, ebitda_margin):
    return revenue * ebitda_margin


def valuation(target_or_inst):
    """Valorisation par comparables + DCF. Renvoie EV (comps, DCF, retenue) et
    valeur des fonds propres (EV − dette nette)."""
    t = target_or_inst
    revenue = t["revenue"]
    ebitda_margin = t["ebitda_margin"]
    growth = t.get("growth_base", 0.04)
    sector = t["sector"]
    net_debt = t.get("net_debt", t.get("debt_balance", 0.0))

    ebitda0 = _ebitda(revenue, ebitda_margin)
    comps_ev = ebitda0 * t["ev_multiple"]

    from data.companies import SECTORS
    beta = SECTORS.get(sector, {}).get("beta", 1.0)
    cost_equity = 0.04 + beta * 0.06
    wacc = fm.wacc(equity=max(comps_ev - net_debt, 1.0), debt=max(net_debt, 0.0),
                   cost_equity=cost_equity, cost_debt=0.06, tax_rate=TAX_RATE)
    fcf_list = []
    rev_t = revenue
    for _ in range(5):
        rev_t *= (1 + growth)
        ebitda_t = rev_t * ebitda_margin
        fcf_t = ebitda_t * (1 - TAX_RATE) - rev_t * CAPEX_PCT
        fcf_list.append(fcf_t)
    terminal_growth = max(0.0, min(0.02, growth / 2))
    dcf_ev = fm.dcf_enterprise_value(fcf_list, wacc, terminal_growth)

    fair_ev = max(0.0, 0.5 * comps_ev + 0.5 * dcf_ev)
    return {
        "ebitda": ebitda0, "comps_ev": comps_ev, "dcf_ev": dcf_ev, "fair_ev": fair_ev,
        "equity_value": max(0.0, fair_ev - net_debt), "wacc": wacc,
    }


def ask_price(target):
    """Prix demandé par le vendeur : juste valeur + prime de contrôle."""
    v = valuation(target)
    return v["fair_ev"] * (1 + CONTROL_PREMIUM)


def financing_terms(price, debt_pct):
    debt_pct = max(0.0, min(MAX_DEBT_PCT, debt_pct))
    debt_amount = price * debt_pct
    equity_cash = price - debt_amount
    return {"price": price, "debt_pct": debt_pct, "debt_amount": debt_amount,
            "equity_cash": equity_cash}


# --------------------------------------------------------------------- acquisition
def acquire(player, ticker, debt_pct):
    target = get_target(ticker)
    if not target:
        return {"ok": False, "reason": "Cible introuvable."}
    if is_taken(player, ticker):
        return {"ok": False, "reason": "Cible déjà acquise (ou cédée) précédemment."}
    price = ask_price(target)
    terms = financing_terms(price, debt_pct)
    if player.cash < terms["equity_cash"]:
        return {"ok": False, "reason": "Trésorerie insuffisante pour l'apport en fonds propres."}

    player.cash -= terms["equity_cash"]
    inst = {
        "ticker": ticker, "name": target["name"], "region": target["region"],
        "sector": target["sector"], "tier": target["tier"],
        "acquired_day": player.day, "purchase_ev": price,
        "equity_invested": terms["equity_cash"], "debt_balance": terms["debt_amount"],
        "debt_initial": terms["debt_amount"],
        "revenue": target["revenue"], "ebitda_margin": target["ebitda_margin"],
        "net_margin": target["net_margin"], "employees": target["employees"],
        "growth_base": target["growth_base"], "ev_multiple": target["ev_multiple"],
        "margin_spread": target["ebitda_margin"] - target["net_margin"],
        "management_score": target["management_score"], "morale": target["morale"],
        "efficiency": target["efficiency"],
        "cash_buffer": target["revenue"] * CASH_BUFFER_TARGET_PCT,
        "cum_dividends": 0.0, "distress_quarters": 0,
        "last_action_quarter": None, "action_log": [],
    }
    if not hasattr(player, "ma_owned") or player.ma_owned is None:
        player.ma_owned = {}
    player.ma_owned[ticker] = inst
    return {"ok": True, "instance": inst, "terms": terms}


# --------------------------------------------------------------------- axes d'amélioration
IMPROVEMENT_ACTIONS = [
    dict(id="training", label="Formation managériale", kind="positive",
         cost_pct=0.03,
         desc="Programme de formation des cadres : décisions plus posées, "
              "meilleur pilotage des équipes.",
         effects={"management_score": +12, "morale": +4}),
    dict(id="hiring", label="Renforcer l'équipe (recrutement)", kind="positive",
         cost_pct=0.05,
         desc="Recrutement ciblé : capacité de croissance accrue, mais ramp-up "
              "qui pèse temporairement sur l'efficacité.",
         effects={"growth_base": +0.02, "employees_pct": +0.10, "efficiency": -3}),
    dict(id="org", label="Refonte de l'organigramme", kind="positive",
         cost_pct=0.02,
         desc="Clarification des responsabilités et des reportings : gain "
              "d'efficacité, mais la réorganisation crée une perturbation passagère.",
         effects={"efficiency": +10, "management_score": +5, "morale": -3}),
    dict(id="capex", label="Modernisation équipements / IT", kind="positive",
         cost_pct=0.06,
         desc="Investissement en outils et automatisation : gains de productivité "
              "durables et meilleure marge.",
         effects={"efficiency": +15, "ebitda_margin": +0.010}),
    dict(id="incentive", label="Plan d'intéressement salarié", kind="positive",
         cost_pct=0.02,
         desc="Partage de la valeur créée avec les équipes : forte hausse de "
              "l'ambiance, léger coût récurrent sur la marge.",
         effects={"morale": +15, "ebitda_margin": -0.005}),
    dict(id="quality", label="Programme qualité / certification", kind="positive",
         cost_pct=0.025,
         desc="Certification qualité : améliore la réputation commerciale et la "
              "capacité à gagner de nouveaux clients.",
         effects={"growth_base": +0.015, "efficiency": +5}),
    dict(id="layoffs", label="Plan de licenciements", kind="negative",
         cost_pct=-0.04,
         desc="Réduction d'effectifs : économies immédiates, mais coup dur pour "
              "le moral, le management et la croissance future.",
         effects={"management_score": -10, "morale": -20, "growth_base": -0.03,
                   "employees_pct": -0.15}),
    dict(id="budget_cuts", label="Coupes budgétaires (R&D / marketing)", kind="negative",
         cost_pct=-0.03,
         desc="Réduction des budgets discrétionnaires : trésorerie immédiate, "
              "mais croissance future amputée et ambiance dégradée.",
         effects={"growth_base": -0.02, "ebitda_margin": +0.010, "morale": -5}),
    dict(id="wage_freeze", label="Gel des salaires", kind="negative",
         cost_pct=-0.015,
         desc="Économie de masse salariale : impact direct sur le moral et "
              "l'efficacité opérationnelle (départs, désengagement).",
         effects={"morale": -12, "efficiency": -5}),
    dict(id="asset_sale", label="Cession d'actifs non stratégiques", kind="negative",
         cost_pct=-0.08,
         desc="Cession d'actifs annexes : rentrée de cash one-off, mais capacité "
              "productive réduite (marge plus basse durablement).",
         effects={"ebitda_margin": -0.015, "efficiency": -5}),
]
_ACTIONS_BY_ID = {a["id"]: a for a in IMPROVEMENT_ACTIONS}


def available_actions():
    return list(IMPROVEMENT_ACTIONS)


def can_apply_action(player, ticker):
    inst = (getattr(player, "ma_owned", None) or {}).get(ticker)
    if not inst:
        return False, "Société non détenue."
    if inst.get("last_action_quarter") == player.quarter:
        return False, "Une seule action par trimestre par société (déjà utilisée)."
    return True, ""


def apply_action(player, ticker, action_id):
    ok, reason = can_apply_action(player, ticker)
    if not ok:
        return {"ok": False, "reason": reason}
    action = _ACTIONS_BY_ID.get(action_id)
    if not action:
        return {"ok": False, "reason": "Action inconnue."}
    inst = player.ma_owned[ticker]
    cost = action["cost_pct"] * inst["revenue"]
    if cost > 0 and player.cash < cost:
        return {"ok": False, "reason": "Trésorerie insuffisante pour financer cette action."}

    player.cash -= cost   # cost > 0 dépense, cost < 0 encaisse (cession/économies)
    eff = action["effects"]
    for k, dv in eff.items():
        if k == "employees_pct":
            inst["employees"] = max(1, int(round(inst["employees"] * (1 + dv))))
        elif k in ("management_score", "morale", "efficiency"):
            inst[k] = max(0.0, min(100.0, inst[k] + dv))
        elif k == "ebitda_margin":
            inst[k] = max(0.02, min(0.65, inst[k] + dv))
            inst["net_margin"] = max(0.0, inst[k] - inst.get("margin_spread", 0.05))
        elif k == "growth_base":
            inst[k] = max(-0.10, min(0.35, inst[k] + dv))
    inst["last_action_quarter"] = player.quarter
    inst["action_log"].append({"quarter": player.quarter, "id": action_id,
                               "label": action["label"], "cost": cost})
    return {"ok": True, "cost": cost, "instance": inst}


# --------------------------------------------------------------------- évolution trimestrielle
def _revert(score):
    return score + (SCORE_MEAN - score) * SCORE_REVERT


def evolve_quarter(player):
    """Appelée à chaque bascule de trimestre : fait évoluer chaque société
    détenue (croissance, marges, service de la dette, incidents aléatoires
    déterministes, cash sweep). Renvoie une liste d'événements (titres)."""
    events = []
    owned = getattr(player, "ma_owned", None) or {}
    to_remove = []
    for ticker, inst in owned.items():
        inst["management_score"] = _revert(inst["management_score"])
        inst["morale"] = _revert(inst["morale"])
        inst["efficiency"] = _revert(inst["efficiency"])

        eff_growth = inst["growth_base"] \
            + (inst["management_score"] - SCORE_MEAN) * 0.0006 \
            + (inst["morale"] - SCORE_MEAN) * 0.0004 \
            + (inst["efficiency"] - SCORE_MEAN) * 0.0004
        eff_growth = max(-0.06, min(0.30, eff_growth))
        inst["revenue"] *= (1 + eff_growth / 4.0)

        margin_drift = (inst["efficiency"] - SCORE_MEAN) * 0.00004
        inst["ebitda_margin"] = max(0.02, min(0.65, inst["ebitda_margin"] + margin_drift))
        inst["net_margin"] = max(0.0, inst["ebitda_margin"] - inst.get("margin_spread", 0.05))

        # incident aléatoire déterministe (seed dérivée du ticker + jour) :
        # plus le management/le moral sont bas, plus le risque est élevé.
        worst = min(inst["morale"], inst["management_score"])
        risk = max(0.0, (55.0 - worst) / 55.0) * 0.10
        rng = random.Random(f"{ticker}:{player.day}")
        if rng.random() < risk:
            inst["revenue"] *= 0.93
            inst["morale"] = max(0.0, inst["morale"] - 8)
            events.append(f"M&A : incident opérationnel chez {inst['name']} "
                          f"({ticker}) — CA et moral en baisse.")

        ebitda = inst["revenue"] * inst["ebitda_margin"]
        fcf = ebitda * (1 - TAX_RATE) - inst["revenue"] * CAPEX_PCT
        quarterly_rate = DEBT_RATE_ANNUAL / 4.0
        interest = inst["debt_balance"] * quarterly_rate
        scheduled_amort = inst["debt_initial"] * (DEBT_AMORT_ANNUAL / 4.0)

        available = inst["cash_buffer"] + fcf
        shortfall = interest - available
        if shortfall > 0:
            available = 0.0
            if player.cash >= shortfall:
                player.cash -= shortfall
                events.append(f"M&A : {inst['name']} ({ticker}) n'a pas généré assez de "
                              f"cash-flow — découvert de {shortfall:,.0f} comblé sur votre trésorerie.")
                inst["distress_quarters"] += 1
            else:
                # défaut : les créanciers reprennent la société, equity perdu
                player.cash = max(player.cash, player.cash)  # rien à ajouter, juste cohérence
                _record_loss(player, inst, reason="défaut sur la dette LBO")
                events.append(f"M&A : DÉFAUT — {inst['name']} ({ticker}) est reprise par ses "
                              f"créanciers. Votre apport en fonds propres est perdu.")
                to_remove.append(ticker)
                continue
        else:
            available -= interest

        amort = min(scheduled_amort, max(0.0, available), inst["debt_balance"])
        inst["debt_balance"] = max(0.0, inst["debt_balance"] - amort)
        available -= amort

        buffer_target = inst["revenue"] * CASH_BUFFER_TARGET_PCT
        inst["cash_buffer"] = available
        if inst["cash_buffer"] > buffer_target:
            sweep = inst["cash_buffer"] - buffer_target
            inst["cash_buffer"] = buffer_target
            player.cash += sweep
            inst["cum_dividends"] += sweep
        elif inst["cash_buffer"] < inst["revenue"] * DISTRESS_THRESHOLD_PCT:
            inst["distress_quarters"] += 1
            if inst["distress_quarters"] >= 3:
                _record_loss(player, inst, reason="détresse financière prolongée")
                events.append(f"M&A : {inst['name']} ({ticker}) est placée en redressement — "
                              f"société perdue après plusieurs trimestres de détresse.")
                to_remove.append(ticker)
                continue
        else:
            inst["distress_quarters"] = 0

        if inst["debt_balance"] <= 0.0 and inst.get("debt_initial", 0) > 0:
            events.append(f"M&A : {inst['name']} ({ticker}) a fini de rembourser sa dette LBO.")
            inst["debt_initial"] = 0.0  # évite de re-logguer chaque trimestre

    for t in to_remove:
        owned.pop(t, None)
    return events


def _record_loss(player, inst, reason):
    if not hasattr(player, "ma_history") or player.ma_history is None:
        player.ma_history = []
    player.ma_history.append({
        "ticker": inst["ticker"], "name": inst["name"], "status": "perdue",
        "reason": reason, "equity_invested": inst["equity_invested"],
        "proceeds": 0.0, "cum_dividends": inst["cum_dividends"],
        "pnl": -inst["equity_invested"] + inst["cum_dividends"],
        "moic": (inst["cum_dividends"] / inst["equity_invested"]
                 if inst["equity_invested"] else 0.0),
        "day": player.day,
    })


# --------------------------------------------------------------------- sortie (exit)
def exit_value(inst):
    """EV/equity actuels d'une société détenue, pour décider/afficher l'exit."""
    return valuation({**inst, "net_debt": inst["debt_balance"]})


def exit_company(player, ticker):
    inst = (getattr(player, "ma_owned", None) or {}).get(ticker)
    if not inst:
        return {"ok": False, "reason": "Société non détenue."}
    v = exit_value(inst)
    proceeds = max(0.0, v["equity_value"]) * (1 - EXIT_FEE)
    player.cash += proceeds
    if not hasattr(player, "ma_history") or player.ma_history is None:
        player.ma_history = []
    total_in = inst["equity_invested"]
    total_out = proceeds + inst["cum_dividends"]
    player.ma_history.append({
        "ticker": ticker, "name": inst["name"], "status": "cédée",
        "reason": "exit", "equity_invested": total_in, "proceeds": proceeds,
        "cum_dividends": inst["cum_dividends"], "pnl": total_out - total_in,
        "moic": (total_out / total_in) if total_in else 0.0,
        "day": player.day,
    })
    player.ma_owned.pop(ticker, None)
    return {"ok": True, "proceeds": proceeds, "pnl": total_out - total_in}


# --------------------------------------------------------------------- divers
def holdings_value(player):
    """Valeur (fonds propres) des sociétés détenues, pour le calcul de net worth."""
    total = 0.0
    for inst in (getattr(player, "ma_owned", None) or {}).values():
        v = exit_value(inst)
        total += max(0.0, v["equity_value"])
    return total


def statements_for(inst_or_target, base_year, n_years=5):
    """États financiers 5 ans (façon `core.financials.statements`) pour une
    cible/société M&A, à partir de ses fondamentaux propres (hors Market)."""
    rev_n = inst_or_target["revenue"]
    net_margin = inst_or_target["net_margin"]
    ebitda_margin = inst_or_target["ebitda_margin"]
    net_debt = inst_or_target.get("net_debt", inst_or_target.get("debt_balance", 0.0))
    sector = inst_or_target["sector"]
    ticker = inst_or_target["ticker"]
    growth = inst_or_target.get("growth_base")
    out = []
    for offset in range(n_years):
        out.append({
            "year": base_year - offset,
            "income": F.income_statement_for(rev_n, net_margin, ebitda_margin, net_debt,
                                              sector, ticker, offset, growth=growth),
            "balance": F.balance_sheet_for(rev_n, net_margin, ebitda_margin, net_debt,
                                           sector, ticker, offset, growth=growth),
        })
    return out
