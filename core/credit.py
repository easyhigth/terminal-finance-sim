"""credit.py — Notation de crédit d'entreprise dérivée des fondamentaux.

La notation (échelle AAA..B, alignée sur les ratings obligataires de
core/bonds.py) est déduite du levier net_debt/EBITDA et de la volatilité
idiosyncratique de la société : plus l'entreprise est endettée et instable,
plus sa notation se dégrade. Calculée à la volée (jamais sérialisée) à partir
des fondamentaux DYNAMIQUES du marché (qui évoluent via les earnings), donc
une notation peut migrer en cours de partie.
"""

RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B"]

# Seuils de score (levier + volatilité) délimitant les 6 catégories.
_BOUNDS = [0.5, 1.2, 2.2, 3.5, 5.5]


def rating_for(nd_ebitda, sigma):
    """Notation déduite du levier (dette nette/EBITDA) et de la volatilité
    idiosyncratique. `nd_ebitda` peut être None (EBITDA négatif ou nul) →
    notation la plus basse, faute de capacité de remboursement visible."""
    if nd_ebitda is None:
        return RATINGS[-1]
    score = max(0.0, nd_ebitda) + sigma * 20.0
    for bound, rating in zip(_BOUNDS, RATINGS):
        if score <= bound:
            return rating
    return RATINGS[-1]


def rating_rank(rating):
    """Rang numérique (0 = meilleure note AAA) pour comparer deux notations."""
    return RATINGS.index(rating) if rating in RATINGS else len(RATINGS) - 1
