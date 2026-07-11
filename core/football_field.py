"""
football_field.py — Agrège plusieurs méthodes de valorisation d'une cible
M&A en une fourchette unique par méthode : le « football field » classique
des banques d'affaires (barres horizontales superposées, une par méthode),
qui donne à voir la valorisation comme une PLAGE plutôt qu'un chiffre unique.

Combine ce qui existe déjà (`core/ma.py::valuation()` calcule déjà comps et
DCF) avec deux lentilles nouvelles :
  - transactions précédentes du secteur (`core/precedent_transactions.py`)
  - comparables PUBLICS du même secteur, décotés d'illiquidité/taille
    (`market.sector_medians()` — la cible est une PME non cotée, on ne peut
    pas lui appliquer tel quel le multiple d'un grand groupe coté).

Logique pure : aucune dépendance à pygame. `market` est optionnel — sans lui,
la méthode "comparables publics" est simplement absente de la fourchette
(headless/tests sans marché instancié).
"""
from core import ma
from core import precedent_transactions as pt

# décote appliquée aux multiples publics pour refléter la taille/liquidité
# d'une PME non cotée par rapport à un grand groupe coté (prime de contrôle
# du côté acheteur, décote de marchabilité du côté du multiple observé)
PUBLIC_COMP_DISCOUNT = 0.35


def _range(target, net_debt, ev_lo, ev_med, ev_hi, label):
    return {
        "label": label,
        "ev_lo": max(0.0, ev_lo), "ev_median": max(0.0, ev_med), "ev_hi": max(0.0, ev_hi),
        "equity_lo": max(0.0, ev_lo - net_debt),
        "equity_median": max(0.0, ev_med - net_debt),
        "equity_hi": max(0.0, ev_hi - net_debt),
    }


def build(target, market=None):
    """Calcule les fourchettes de valorisation de `target` (dict cible ou
    instance détenue) par méthode. Renvoie {"ebitda", "net_debt", "ask_ev",
    "ask_equity", "methods": [ranges...]}."""
    net_debt = target.get("net_debt", target.get("debt_balance", 0.0))
    v = ma.valuation(target)
    ebitda = v["ebitda"]
    methods = []

    # comps privés (spread indicatif ±15% autour du point retenu par ma.py)
    comps_ev = v["comps_ev"]
    methods.append(_range(target, net_debt, comps_ev * 0.85, comps_ev, comps_ev * 1.15,
                           "Comparables (non coté)"))

    # DCF (spread ±10%, incertitude sur WACC/croissance terminale)
    dcf_ev = v["dcf_ev"]
    methods.append(_range(target, net_debt, dcf_ev * 0.90, dcf_ev, dcf_ev * 1.10, "DCF"))

    # transactions précédentes du secteur
    prec = pt.precedent_ev(ebitda, target["sector"])
    methods.append(_range(target, net_debt, prec["lo"], prec["median"], prec["hi"],
                           "Transactions précédentes"))

    # comparables publics décotés (nécessite un marché)
    if market is not None:
        medians = market.sector_medians(target["sector"])
        if medians.get("ev_ebitda"):
            pub_mult = medians["ev_ebitda"] * (1 - PUBLIC_COMP_DISCOUNT)
            pub_ev = ebitda * pub_mult
            methods.append(_range(target, net_debt, pub_ev * 0.85, pub_ev, pub_ev * 1.15,
                                   "Comparables publics (décotés)"))

    ask_ev = ma.ask_price(target)
    return {
        "ebitda": ebitda, "net_debt": net_debt, "fair_ev": v["fair_ev"],
        "ask_ev": ask_ev, "ask_equity": max(0.0, ask_ev - net_debt),
        "methods": methods,
    }
