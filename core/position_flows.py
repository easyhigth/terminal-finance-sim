"""
position_flows.py — FLUX PAR TOUR de chaque position (logique pure).

Répond, ligne par ligne du Portefeuille, à « qu'est-ce que cette position me
rapporte/coûte à chaque tour ? » : dividende, coupon, roll, intérêt CBDC,
frais d'emprunt d'un short… Mesuré par ISOLATION : on rejoue les vrais
accruals du moteur (trade_preview.step_flow) sur une copie du joueur qui ne
détient QUE cette position, moins le flux d'une copie vide — pas d'estimation
parallèle qui divergerait du moteur.

Coût : un clone + accruals par position — à mettre en CACHE par pas de
marché côté UI (cf. apps/app_book.py), jamais recalculé à chaque frame.

Classes couvertes (mêmes clés que core/analytics.holdings_table) :
    Actions, Obligations, Matières, Crypto, ETF.
"""
from core import trade_preview as tp

# champs de position du PlayerState à VIDER pour isoler une ligne
_POSITION_FIELDS = ("portfolio", "bonds", "commodities", "crypto", "etfs",
                    "fx_positions", "repo_positions", "cds_positions",
                    "irs_positions", "trs_positions", "convertibles",
                    "currency_swaps", "mm_deposits", "structured",
                    "securitised", "hedges", "options")

_CLS_FIELD = {"Actions": "portfolio", "Obligations": "bonds",
              "Matières": "commodities", "Crypto": "crypto", "ETF": "etfs"}


def _stripped_clone(player):
    q = tp.clone_player(player)
    for f in _POSITION_FIELDS:
        current = getattr(q, f, None)
        if isinstance(current, dict):
            setattr(q, f, {})
        elif isinstance(current, list):
            setattr(q, f, [])
    return q


def per_position(player, market):
    """{(cls, label): flux_par_tour} pour chaque ligne dict-portée du
    portefeuille (Actions/Obligations/Matières/Crypto/ETF). Les classes en
    liste (options, structurés…) ont leurs propres écrans dédiés."""
    out = {}
    base_flow = tp.step_flow(_stripped_clone(player), market)
    for cls, field in _CLS_FIELD.items():
        book = getattr(player, field, None)
        if not book:
            continue
        for label, pos in book.items():
            q = _stripped_clone(player)
            getattr(q, field)[label] = dict(pos)
            out[(cls, label)] = tp.step_flow(q, market) - base_flow
    return out


def position_story(player, market, cls, label):
    """« Pourquoi cette ligne a bougé » : décomposition honnête à partir des
    données réellement disponibles — effet prix latent, P&L réalisé et frais
    cumulés sur CE titre (journal de trades), flux par tour courant. Retourne
    un dict ou None si la position est inconnue."""
    field = _CLS_FIELD.get(cls)
    if field is None:
        return None
    pos = (getattr(player, field, None) or {}).get(label)
    if not pos:
        return None
    qty = pos.get("shares", pos.get("qty", 0.0))
    avg = pos.get("avg", 0.0)
    price = market.price_of(label) if cls == "Actions" else None
    if price is None:
        # classes non-actions : le prix courant vient de la table de l'UI,
        # l'appelant peut le fournir via story["price"] — on met l'avg en repli
        price = avg
    price_effect = (price - avg) * qty
    realized = fees = 0.0
    trades = 0
    for t in getattr(player, "trade_journal", None) or []:
        if t.get("key") != label:
            continue
        trades += 1
        fees += t.get("fee", 0.0)
        if t.get("realized") is not None:
            realized += t["realized"]
    q = _stripped_clone(player)
    getattr(q, field)[label] = dict(pos)
    flux = tp.step_flow(q, market) - tp.step_flow(_stripped_clone(player), market)
    return {"cls": cls, "label": label, "qty": qty, "avg": avg, "price": price,
            "price_effect": price_effect, "realized": realized, "fees": fees,
            "trades": trades, "flux": flux}
