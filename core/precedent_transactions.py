"""
precedent_transactions.py — Transactions M&A précédentes, synthétiques et
déterministes, par secteur (logique pure).

Sert de troisième lentille de valorisation d'une cible privée (avec les
comps et le DCF déjà calculés par `core/ma.py::valuation()`) : « à quel
multiple d'EBITDA et avec quelle prime de contrôle les acquéreurs ont-ils
historiquement payé des sociétés de CE secteur ? » — distinct du multiple de
comps privé (`data/ma_targets._PRIVATE_MULT`), qui reflète une valorisation
« au fil de l'eau » sans transaction réelle, et généralement PLUS ÉLEVÉ (une
transaction se conclut à une prime, pas à la juste valeur).

Déterministe : dérivé de `(TARGETS_SEED, secteur)` — même catalogue de
transactions à chaque partie, comme le catalogue de cibles lui-même. Purement
informatif : n'affecte jamais une transaction réelle du joueur.
"""
import random

from data.ma_targets import TARGETS_SEED, _PRIVATE_MULT

DEALS_PER_SECTOR = 6
# les transactions passées se sont conclues plus cher que la juste valeur
# "comps" au fil de l'eau (chaleur du marché M&A au moment du deal + prime
# de contrôle déjà incluse dans le multiple observé)
PRECEDENT_HEAT = 0.15

_ACQUIRER_KINDS = [
    "fonds de LBO", "concurrent industriel", "groupe diversifié",
    "investisseur stratégique", "family office",
]


def _rng_for(sector):
    return random.Random(f"{TARGETS_SEED}:{sector}")


def deals_for_sector(sector):
    """Liste de transactions précédentes synthétiques pour CE secteur :
    multiple EV/EBITDA payé, prime de contrôle payée, ancienneté (en
    trimestres), type d'acquéreur — triée de la plus récente à la plus
    ancienne."""
    rng = _rng_for(sector)
    lo, hi = _PRIVATE_MULT.get(sector, (4.0, 7.0))
    deals = []
    for i in range(DEALS_PER_SECTOR):
        heat = 1 + PRECEDENT_HEAT * rng.uniform(0.3, 1.4)
        mult = round(rng.uniform(lo, hi) * heat, 2)
        premium = round(rng.uniform(0.04, 0.22), 3)
        age_q = rng.randint(1, 16)
        acquirer = rng.choice(_ACQUIRER_KINDS)
        deals.append({
            "id": f"{sector}-{i + 1}", "sector": sector, "ev_ebitda": mult,
            "control_premium": premium, "age_quarters": age_q,
            "acquirer_kind": acquirer,
        })
    deals.sort(key=lambda d: d["age_quarters"])
    return deals


def multiple_range(sector):
    """Fourchette (min/médiane/max) du multiple EV/EBITDA effectivement payé
    lors des transactions précédentes du secteur, + le détail des deals."""
    deals = deals_for_sector(sector)
    mults = sorted(d["ev_ebitda"] for d in deals)
    n = len(mults)
    median = mults[n // 2] if n % 2 else (mults[n // 2 - 1] + mults[n // 2]) / 2
    return {"lo": mults[0], "hi": mults[-1], "median": median, "deals": deals}


def precedent_ev(ebitda, sector):
    """EV impliqué (lo/médiane/hi) par les transactions précédentes du
    secteur, appliqué à l'EBITDA de la cible actuelle."""
    r = multiple_range(sector)
    return {"lo": ebitda * r["lo"], "median": ebitda * r["median"],
            "hi": ebitda * r["hi"]}
