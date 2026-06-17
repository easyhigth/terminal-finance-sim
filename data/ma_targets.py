"""
ma_targets.py — Catalogue déterministe de cibles privées pour le module M&A.

Ces sociétés sont des PME/ETI FICTIVES, totalement SÉPARÉES du roster public
de `data/companies.py` : on ne peut pas les acheter/vendre en bourse, elles
n'existent QUE pour servir de cibles d'acquisition (LBO réel : cash + dette).
Leur échelle de valorisation est volontairement beaucoup plus petite que le
roster public (qui se compte en milliards) pour rester accessible au capital
du joueur (qui démarre à 250 000 et progresse par paliers de grade).

Chaque cible est un dict statique :
  ticker, name, region, sector, tier      (tier = "small"/"mid"/"large")
  revenue            : CA annuel (devise locale, montant réel — pas en M)
  ebitda_margin, net_margin : marges (0..1)
  net_debt           : dette nette de départ (négatif = trésorerie nette)
  employees           : effectif
  growth_base         : croissance organique annuelle « naturelle » (avant
                         effet des axes d'amélioration et de la conjoncture)
  ev_multiple         : multiple EV/EBITDA de référence (comps, marché du
                         non côté — plus bas que les multiples public/large-cap)
  management_score, morale, efficiency : scores 0-100, état de départ
                         (équipe dirigeante, ambiance, opérationnel)

Tout est généré une fois à l'import via une graine fixe -> reproductible.
"""
import random

from data.companies import REGIONS, SECTORS

TARGETS_SEED = 778899
TARGET_COUNT = 50

# Multiples EV/EBITDA typiques du non côté par secteur (plus bas que le public :
# décote d'illiquidité + risque de PME). (lo, hi)
_PRIVATE_MULT = {
    "Tech":        (5.5, 9.5), "Semicon": (5.0, 8.5), "Luxe": (5.0, 8.0),
    "Conso":       (4.0, 6.5), "Finance": (4.5, 7.0), "Energie": (3.5, 6.0),
    "Sante":       (5.5, 9.0), "Industrie": (4.0, 6.5), "Agro": (3.5, 6.0),
    "Telecom":     (4.5, 7.0), "Utilities": (4.0, 6.5), "Materiaux": (3.5, 6.0),
    "Immobilier":  (4.0, 7.5), "Auto":      (3.5, 6.0),
}

# (nom de tier, part du catalogue, CA min/max, employés min/max)
TIERS = [
    ("small", 0.46, 350_000.0, 2_200_000.0, 8, 55),
    ("mid",   0.34, 2_200_000.0, 9_000_000.0, 55, 220),
    ("large", 0.20, 9_000_000.0, 35_000_000.0, 220, 900),
]

_PREF = ["Nor", "Bel", "Mont", "Castel", "Riv", "Val", "Bos", "Fer", "Lan", "Dor",
         "Mer", "Sol", "Vert", "Hau", "Pra", "Brun", "Clos", "Gar", "Lor", "Mai"]
_SUFF = ["mont", "val", "bois", "rive", "champ", "ville", "ferme", "port", "court",
         "lande", "pierre", "vigne", "cour", "fontaine", "haye", "moulin"]
_KIND = ["Industries", "Group", "Services", "Solutions", "Manufacture", "Negoce",
         "Distribution", "Atelier", "Conseil", "Holding", "Logistique", "Système",
         "Partenaires", "Réseau", "Fabrique"]


def _fp(ticker):
    """Empreinte déterministe (réutilise le même principe que core/financials._fp)."""
    h = 0
    for ch in ticker:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return (h % 1000) / 500.0 - 1.0


def _gen_ticker(rng, used):
    for _ in range(60):
        t = "PT" + "".join(rng.choice("ABCDEFGHJKLMNPRSTVXYZ") for _ in range(3))
        if t not in used:
            used.add(t)
            return t
    t = "PT" + str(len(used))
    used.add(t)
    return t


def _gen_name(rng):
    return f"{rng.choice(_PREF)}{rng.choice(_SUFF)} {rng.choice(_KIND)}"


def _make_target(rng, ticker, name, region, sector, tier, rev_lo, rev_hi, emp_lo, emp_hi):
    prof = SECTORS[sector]
    lo, hi = _PRIVATE_MULT.get(sector, (4.0, 7.0))
    revenue = round(rng.uniform(rev_lo, rev_hi), 0)
    employees = int(round(rng.uniform(emp_lo, emp_hi)))
    ebitda_margin = round(max(0.03, prof["ebitda"] * rng.uniform(0.6, 1.1)), 3)
    net_margin = round(max(0.0, min(ebitda_margin - 0.02, prof["net"] * rng.uniform(0.55, 1.05))), 3)
    # PME : levier de départ plus marqué que le grand public, mais borné
    net_debt = round(revenue * ebitda_margin * rng.uniform(0.5, 2.2), 0)
    growth_base = round(max(-0.02, min(0.18, prof["drift"] * 80 * rng.uniform(0.5, 1.5))), 4)
    ev_multiple = round(rng.uniform(lo, hi), 2)
    management_score = round(rng.uniform(35, 80), 1)
    morale = round(rng.uniform(40, 80), 1)
    efficiency = round(rng.uniform(40, 80), 1)
    return {
        "ticker": ticker, "name": name, "region": region, "sector": sector, "tier": tier,
        "revenue": revenue, "ebitda_margin": ebitda_margin, "net_margin": net_margin,
        "net_debt": net_debt, "employees": employees, "growth_base": growth_base,
        "ev_multiple": ev_multiple, "management_score": management_score,
        "morale": morale, "efficiency": efficiency,
    }


def _build():
    rng = random.Random(TARGETS_SEED)
    sectors = list(SECTORS.keys())
    used = set()
    out = []
    counts = [max(1, round(TARGET_COUNT * share)) for _, share, *_ in TIERS]
    # ajuste pour tomber exactement sur TARGET_COUNT
    diff = TARGET_COUNT - sum(counts)
    counts[0] += diff
    for (tier, _share, rev_lo, rev_hi, emp_lo, emp_hi), n in zip(TIERS, counts):
        for _ in range(n):
            region = rng.choice(REGIONS)
            sector = rng.choice(sectors)
            ticker = _gen_ticker(rng, used)
            name = _gen_name(rng)
            out.append(_make_target(rng, ticker, name, region, sector, tier,
                                     rev_lo, rev_hi, emp_lo, emp_hi))
    return out


TARGETS = _build()
TARGETS_BY_TICKER = {t["ticker"]: t for t in TARGETS}


def get(ticker):
    return TARGETS_BY_TICKER.get(ticker)


def all_targets():
    return list(TARGETS)
