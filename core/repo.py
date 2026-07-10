"""
repo.py — Marché du REPO (pension livrée), logique pure.

LA plomberie de financement des marchés : le desk achète des obligations
« en pension » — il ne paie CASH que le HAIRCUT (la marge), le reste est
emprunté au taux repo contre le titre lui-même mis en garantie. C'est le
levier obligataire réel :

- rendement de l'equity ≈ (YTM×valeur − taux repo×emprunt) / marge — le
  carry de courbe démultiplié ;
- le taux repo est ROULÉ chaque pas (taux directeur + spread, élargi par
  le stress de marché) ; les coupons du titre restent acquis (nets de
  perte de crédit, même convention que core/bonds.coupons) ;
- le HAIRCUT dépend du collatéral (souverain < corporate) et S'ÉLARGIT en
  crise — la leçon 2008/LTCM : quand le collatéral baisse ET que le
  haircut monte, l'**appel de marge** force la liquidation au pire moment
  (`mark_and_call`, câblé dans advance_step : liquidation forcée si
  l'equity de la position passe sous la marge de maintenance).

Position auto-contenue ({bond_id, qty, borrowed, entry_price…} dans
player.repo_positions) : les titres en pension ne se mélangent pas au book
obligataire libre (player.bonds) — pas de vente accidentelle du collatéral.
"""
from core import bonds as B

HAIRCUT_BASE = {"Souverain": 0.03, "Corporate": 0.10}
HAIRCUT_STRESS_MULT = 2.0        # haircut ×(1 + 2×stress) en crise
REPO_SPREAD = 0.002              # au-dessus du taux directeur
REPO_STRESS_SPREAD = 0.015      # spread additionnel à stress max
MAINTENANCE_FRAC = 0.5           # marge de maintenance = haircut courant / 2
MAX_POSITIONS = 12


def _stress(market):
    return min(1.0, max(0.0, getattr(market, "last_stress_level", 0.0)))


def repo_rate(market):
    """Taux repo courant (annuel) : directeur + spread, élargi en crise."""
    return (B.base_yield_level(market) + REPO_SPREAD
            + REPO_STRESS_SPREAD * _stress(market))


def haircut(market, bond_kind):
    """Haircut courant du collatéral — s'élargit avec le stress."""
    base = HAIRCUT_BASE.get(bond_kind, 0.10)
    return min(0.50, base * (1.0 + HAIRCUT_STRESS_MULT * _stress(market)))


def quote(market, bond_id, qty):
    """Devis d'ouverture : valeur, haircut, marge cash, emprunt, taux repo
    et carry de l'equity ((YTM×V − repo×emprunt)/marge). None si inconnu."""
    q = B.quote(market, bond_id)
    if not q or qty < 1:
        return None
    value = q["price"] * qty
    h = haircut(market, q["kind"])
    margin = value * h
    borrowed = value - margin
    rate = repo_rate(market)
    carry = ((q["ytm"] * value - rate * borrowed) / margin) if margin > 0 else 0.0
    return {"bond_id": bond_id, "name": q["name"], "kind": q["kind"],
            "qty": qty, "value": value, "haircut": h, "margin": margin,
            "borrowed": borrowed, "rate": rate, "ytm": q["ytm"],
            "equity_carry": carry}


def open_repo(player, market, bond_id, qty):
    """Ouvre une pension : débite la MARGE seulement, le reste est emprunté.
    {ok, position} ou {ok: False, reason}."""
    player.repo_positions = getattr(player, "repo_positions", [])
    if len(player.repo_positions) >= MAX_POSITIONS:
        return {"ok": False, "reason": "max_positions"}
    dv = quote(market, bond_id, qty)
    if dv is None:
        return {"ok": False, "reason": "bond"}
    if dv["margin"] > player.cash:
        return {"ok": False, "reason": "cash"}
    player.cash -= dv["margin"]
    pos = {"id": max((p["id"] for p in player.repo_positions), default=0) + 1,
           "bond_id": bond_id, "qty": qty, "borrowed": dv["borrowed"],
           "entry_price": dv["value"] / qty, "entry_margin": dv["margin"]}
    player.repo_positions.append(pos)
    return {"ok": True, "position": pos, "quote": dv}


def position_state(market, pos):
    """État courant d'une pension : valeur, equity, marge de maintenance,
    en appel de marge ou non."""
    q = B.quote(market, pos["bond_id"])
    if not q:
        return None
    value = q["price"] * pos["qty"]
    equity = value - pos["borrowed"]
    maint = value * haircut(market, q["kind"]) * MAINTENANCE_FRAC
    return {"value": value, "equity": equity, "maintenance": maint,
            "in_call": equity < maint, "name": q["name"], "kind": q["kind"],
            "ytm": q["ytm"]}


def close_repo(player, market, pos_id):
    """Dénoue une pension : vend le collatéral, rembourse l'emprunt, rend
    l'equity au cash. {ok, proceeds, pnl} ou {ok: False, reason}."""
    for pos in getattr(player, "repo_positions", []) or []:
        if pos["id"] == pos_id:
            st = position_state(market, pos)
            if st is None:
                return {"ok": False, "reason": "bond"}
            player.cash += st["equity"]
            pnl = st["equity"] - pos["entry_margin"]
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
            player.repo_positions.remove(pos)
            return {"ok": True, "proceeds": st["equity"], "pnl": pnl}
    return {"ok": False, "reason": "notfound"}


def accrue(player, market, days):
    """Flux d'un pas : coupons du collatéral (nets, convention
    core/bonds.coupons) − intérêt repo sur l'emprunt. Montant net (signé)."""
    total = 0.0
    rate = repo_rate(market)
    for pos in getattr(player, "repo_positions", []) or []:
        b = B._BY_ID.get(pos["bond_id"])
        if b:
            net_coupon = b["coupon"] - B._RATING_LOSS.get(b["rating"], 0.0)
            total += B.FACE * net_coupon * pos["qty"] * (days / 365.0)
        total -= pos["borrowed"] * rate * (days / 365.0)
    return total


def mark_and_call(player, market):
    """Contrôle de marge (chaque pas) : toute pension dont l'equity passe
    sous la maintenance est LIQUIDÉE DE FORCE (l'equity restante, même
    négative, est réglée en cash). Renvoie la liste des liquidations
    [{bond_id, name, equity}] pour notification."""
    events = []
    for pos in list(getattr(player, "repo_positions", []) or []):
        st = position_state(market, pos)
        if st is None:
            continue
        if st["in_call"]:
            player.cash += st["equity"]              # peut être négatif
            pnl = st["equity"] - pos["entry_margin"]
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
            player.repo_positions.remove(pos)
            events.append({"bond_id": pos["bond_id"], "name": st["name"],
                           "equity": st["equity"]})
    return events


def holdings(player, market):
    """Détail des pensions en cours, pour affichage."""
    out = []
    for pos in getattr(player, "repo_positions", []) or []:
        st = position_state(market, pos)
        if st:
            out.append({**pos, **st,
                        "pnl": st["equity"] - pos["entry_margin"]})
    return out


def holdings_value(player, market):
    """Equity totale des pensions (valeur collatéral − emprunts) — la part
    du patrimoine réellement à nous."""
    total = 0.0
    for pos in getattr(player, "repo_positions", []) or []:
        st = position_state(market, pos)
        if st:
            total += st["equity"]
    return total
