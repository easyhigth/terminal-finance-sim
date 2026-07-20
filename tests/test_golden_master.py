"""GOLDEN-MASTER : une session scriptée de 100 pas, comparée à une empreinte
d'état enregistrée.

Les tests unitaires vérifient chaque système isolément ; celui-ci verrouille
leurs INTERACTIONS (registre de pas, frais, dividendes, ordres conditionnels,
échéances, trimestres…) : si un changement anodin décale le moindre flux de
cash de la session de référence, l'empreinte diverge et le diff ci-dessous
dit exactement quel agrégat a bougé.

Si ce test casse APRÈS un changement VOULU de gameplay/équilibrage :
  1. vérifier que le diff est cohérent avec le changement (et rien d'autre) ;
  2. régénérer l'empreinte : `python tests/test_golden_master.py` l'imprime ;
  3. la coller dans EXPECTED en le disant dans le message de commit.
Si ce test casse alors qu'on n'a PAS voulu toucher au gameplay : c'est une
régression — ne pas régénérer l'empreinte, chercher la cause.
"""
import random

from core import bonds
from core import conditional_orders as co
from core import deals as deals_mod
from core import portfolio as pf
from core.game_state import GameState
from core.market import Market

SEED = 424242
STEPS = 100


def _digest(gs, m):
    p = gs.player
    return {
        "day": p.day,
        "quarter": p.quarter,
        "grade_index": p.grade_index,
        "reputation": p.reputation,
        "cash": float(round(p.cash, 2)),
        "net_worth": float(round(pf.net_worth(p, m), 2)),
        "realized_pnl": round(p.realized_pnl, 2),
        "total_fees_paid": round(p.total_fees_paid, 2),
        "total_financing_paid": round(p.total_financing_paid, 2),
        "portfolio": {tk: float(pos["shares"]) for tk, pos in sorted(p.portfolio.items())},
        "bonds": {bid: float(pos["qty"]) for bid, pos in sorted(p.bonds.items())},
        "conditional_orders": len(p.conditional_orders),
        "market_step": m.step_count,
        "last_index": float(round(m.index_value("C&D 500"), 4)),
        "cash_history_len": len(p.cash_history),
        "game_over": p.game_over,
    }


def _play_session():
    """La session de référence : NE PAS MODIFIER sans régénérer l'empreinte
    (toute la valeur du test vient de sa stabilité)."""
    random.seed(SEED)   # events/deals tirent dans le random global
    m = Market(seed=SEED)
    for _ in range(3):
        m.step()
    gs = GameState()
    p = gs.player
    p.grade_index = 6           # accès large aux instruments
    p.cash = 5_000_000.0
    # panier DIVERSIFIÉ (8 actions multi-régions + 3 obligations) : la session
    # doit respecter les limites de risque (core/risklimits) comme un joueur
    # réel, sinon le malus de dépassement persistant (-2 rep/pas) tue le run.
    tks = [m.companies[j]["ticker"] for j in (0, 10, 25, 60, 120, 180, 240, 300)]
    tk0, tk1, tk2 = tks[0], tks[1], tks[2]

    for i in range(STEPS):
        m.step()
        if i == 2:
            for tk in tks:
                pf.buy(p, m, tk, 40)
            for q in bonds.all_quotes(m)[:3]:
                bonds.buy_bond(p, m, q["id"], 25)
        if i == 5:
            co.place(p, m, tk0, "stop", m.price_of(tk0) * 0.85)
            co.place(p, m, tk1, "take", m.price_of(tk1) * 1.20)
        if i == 20:
            pf.buy(p, m, tk2, 30)
        if i == 40 and tk2 in p.portfolio:
            pf.sell(p, m, tk2, 30)
        if i == 60:
            pf.buy(p, m, tk0, 20)
        if i == 80 and tk1 in p.portfolio:
            pf.sell(p, m, tk1, p.portfolio[tk1]["shares"])
        # traite les deals en attente comme un joueur actif (sinon leurs
        # expirations vident la réputation et la session meurt à mi-course) —
        # couvre au passage deals.resolve_deal dans la boucle complète.
        for d in list(p.deals):
            deals_mod.resolve_deal(p, d["id"], rng=random)
        gs.advance_step(market=m)
        p.market_step = m.step_count
    return _digest(gs, m)


EXPECTED = {
    "day": 501,
    "quarter": 6,
    "grade_index": 6,
    "reputation": 84,
    # cash/net_worth recalés : l'objectif trimestriel "pnl" (core/career.py)
    # ajoute un candidat au tirage des objectifs -> le mix (et donc les
    # récompenses cash par trimestre) change de façon déterministe. Le reste de
    # l'empreinte (grade, réputation, positions, market_step…) est INCHANGÉ.
    "cash": 14662260.37,
    "net_worth": 14843501.63,
    "realized_pnl": 5173.7,
    "total_fees_paid": 158.11,
    "total_financing_paid": 0.0,
    "portfolio": {"BTR": 40.0, "KJF": 40.0, "LKTX": 40.0, "LMAG": 40.0,
                  "MVC": 20.0, "SHEL": 40.0, "VNSC": 40.0},
    "bonds": {"BUND10": 25.0, "UST10": 25.0, "UST2": 25.0},
    "conditional_orders": 0,
    "market_step": 103,
    "last_index": 6277.0603,
    "cash_history_len": 80,
    "game_over": False,
}


def test_scripted_session_matches_recorded_digest():
    got = _play_session()
    assert EXPECTED is not None, "empreinte non enregistrée"
    assert got == EXPECTED


if __name__ == "__main__":
    import pprint
    pprint.pprint(_play_session())
