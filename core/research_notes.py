"""
research_notes.py — Écriture d'une NOTE DE RECHERCHE (logique pure).

Valeur intrinsèque simplifiée (BPA capitalisé à un P/E « juste » sectoriel)
+ reco ACHAT/NEUTRE/VENTE, stockée dans `player.research[ticker]`. Extraite
de la commande RESEARCH du terminal (scenes/scene_terminal_market.py) pour
être RÉUTILISABLE : la même note peut désormais être produite par un
analyste junior AFFECTÉ à la recherche (core/team.assignments_step) — même
modèle, même format, une seule implémentation.
"""

FAIR_PE = {"Tech": 24, "Semicon": 22, "Luxe": 22, "Sante": 19, "Conso": 18,
           "Finance": 11, "Energie": 10, "Industrie": 15, "Agro": 13,
           "Telecom": 12, "Utilities": 14, "Materiaux": 12,
           "Immobilier": 15, "Auto": 9}
DEFAULT_FAIR_PE = 15
BUY_UPSIDE = 12    # au-delà de +12 % de potentiel → ACHAT ; sous -12 % → VENTE


def write_note(player, market, ticker):
    """Écrit la note de recherche de `ticker` dans player.research et la
    retourne ({fair, rating, upside, day}), ou None si ticker inconnu."""
    tk = market.resolve(ticker)
    mt = market.metrics(tk) if tk else None
    if not mt:
        return None
    fair_pe = FAIR_PE.get(mt["sector"], DEFAULT_FAIR_PE)
    fair = max(0.5, mt["eps"] * fair_pe)
    upside = (fair / mt["price"] - 1) * 100
    rating = ("ACHAT" if upside > BUY_UPSIDE
              else "VENTE" if upside < -BUY_UPSIDE else "NEUTRE")
    note = {"fair": round(fair, 2), "rating": rating,
            "upside": round(upside, 1), "day": player.day}
    player.research[tk] = note
    return dict(note, ticker=tk)
