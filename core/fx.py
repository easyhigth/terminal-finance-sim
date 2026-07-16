"""
fx.py — Desk FX : trading de paires de devises au comptant (spot) et à terme
(forward), logique pure (sans pygame).

Taux de change déterministes : comme core/crypto.py, chaque paire suit une
marche aléatoire log-normale (drift + vol propres) reconstruite uniquement
depuis (market.seed, pair, market.step_count) — aucun aléa non reproductible.

SPOT : position notionnelle (pas de débit de cash à l'ouverture, comme les
swaps/hedges existants). P&L latent au mark-to-market, réalisé à la fermeture.
Holdings : PlayerState.fx_positions = [ {dict position spot} ].

FORWARD : taux verrouillé à l'ouverture, réglé en cash net à l'échéance
(pas de cash à l'ouverture). Débloqué à partir d'un grade minimal (réductible
par une certification ACI à venir). Holdings : PlayerState.fx_forwards =
[ {dict position forward} ].
"""
import numpy as np

from core import config, crashlog

# (pair, base_price, drift annuel, vol annuelle)
PAIRS_DEF = [
    ("EUR/USD", 1.08, 0.00, 0.07),
    ("USD/JPY", 150.0, 0.01, 0.09),
    ("GBP/USD", 1.27, 0.00, 0.08),
    ("USD/CHF", 0.90, -0.01, 0.07),
    ("AUD/USD", 0.66, 0.00, 0.10),
    ("USD/CAD", 1.36, 0.00, 0.07),
    ("USD/ZAR", 18.5, 0.03, 0.16),
    ("USD/BRL", 5.0, 0.02, 0.18),
]
PAIRS = [p[0] for p in PAIRS_DEF]
_BY_PAIR = {p[0]: p for p in PAIRS_DEF}

STEPS_PER_YEAR = 52
FORWARD_MIN_GRADE = 8
FORWARD_TENORS = [1, 3, 6]   # mois
# conversion mois -> pas de marché (DAYS_PER_STEP jours par pas, ~30j/mois)
STEPS_PER_MONTH = 30.0 / config.DAYS_PER_STEP

_path_cache = {}


def _hash(s):
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def _path(market, pair, n_steps):
    d = _BY_PAIR[pair]
    base, drift, vol = d[1], d[2], d[3]
    seed = (int(getattr(market, "seed", 12345)) + _hash(pair)) & 0xFFFFFFFF
    key = (seed, pair)
    path = _path_cache.get(key)
    if path is None or len(path) <= n_steps:
        rng = np.random.RandomState(seed)
        mu = drift / STEPS_PER_YEAR - 0.5 * (vol / np.sqrt(STEPS_PER_YEAR)) ** 2
        sig = vol / np.sqrt(STEPS_PER_YEAR)
        rets = rng.normal(mu, sig, n_steps + 1)
        path = (base * np.exp(np.cumsum(rets))).tolist()
        path[0] = base
        _path_cache[key] = path
    return path


def tenor_to_steps(tenor_months):
    return int(round(tenor_months * STEPS_PER_MONTH))


def spot(market, pair):
    """Taux de change courant de la paire, déterministe (seed, pair, step)."""
    if pair not in _BY_PAIR:
        return None
    step = int(getattr(market, "step_count", 0))
    p = _path(market, pair, step)
    return p[step]


def history(market, pair, n=120):
    """Série déterministe des taux de change par pas, du début de partie
    jusqu'au pas courant inclus (derniers `n` points). Sert de base aux
    graphes FX — même source que `spot()`, donc parfaitement cohérente."""
    if pair not in _BY_PAIR:
        return []
    step = int(getattr(market, "step_count", 0))
    p = _path(market, pair, step)
    series = p[:step + 1]
    return series[-n:] if n else series


def change_pct(market, pair, lookback=1):
    """Variation en % du taux sur les `lookback` derniers pas (0 si historique
    trop court). `lookback=1` ≈ « variation depuis le pas précédent »."""
    if pair not in _BY_PAIR:
        return 0.0
    step = int(getattr(market, "step_count", 0))
    if step < lookback:
        return 0.0
    p = _path(market, pair, step)
    base = p[step - lookback]
    return (p[step] / base - 1.0) * 100.0 if base else 0.0


def pair_vol(pair):
    """Volatilité annuelle de la paire (paramètre du modèle)."""
    d = _BY_PAIR.get(pair)
    return d[3] if d else 0.08


def quote_spot(market, pair):
    """Cote spot courante de la paire."""
    sp = spot(market, pair)
    if sp is None:
        return {"ok": False, "reason": "pair"}
    d = _BY_PAIR[pair]
    return {"ok": True, "pair": pair, "spot": sp, "vol": d[3]}


def quote_forward(market, pair, tenor_months):
    """Taux forward verrouillé à l'ouverture (= spot courant, pas de courbe
    de taux sophistiquée — simplification volontaire)."""
    sp = spot(market, pair)
    if sp is None:
        return {"ok": False, "reason": "pair"}
    if tenor_months not in FORWARD_TENORS:
        return {"ok": False, "reason": "tenor"}
    return {"ok": True, "pair": pair, "spot": sp, "forward_rate": sp,
            "tenor_months": tenor_months,
            "maturity_step": market.step_count + tenor_to_steps(tenor_months)}


# ---------------------------------------------------------------- gating
def forward_unlocked(player):
    """Le forward FX nécessite un grade plus élevé que le spot (réductible par
    une certification ACI à venir — absorbée silencieusement si absente)."""
    grade_needed = FORWARD_MIN_GRADE
    try:
        from core import certifications
        if certifications.is_complete(player, "ACI"):
            grade_needed -= 3
    except Exception:
        crashlog.swallowed("core.fx")
    return player.grade_index >= grade_needed


# ---------------------------------------------------------------- spot trading
def open_spot(player, market, pair, direction, notional):
    """Ouvre une position spot notionnelle (aucun débit de cash à l'ouverture,
    comme les swaps/hedges existants)."""
    if pair not in _BY_PAIR:
        return {"ok": False, "reason": "pair"}
    if direction not in ("long", "short"):
        return {"ok": False, "reason": "direction"}
    if notional <= 0:
        return {"ok": False, "reason": "notional"}
    entry_rate = spot(market, pair)
    pos = {
        "pair": pair, "direction": direction, "notional": float(notional),
        "entry_rate": entry_rate, "opened_step": market.step_count,
    }
    player.fx_positions = getattr(player, "fx_positions", [])
    player.fx_positions.append(pos)
    return {"ok": True, "position": pos}


def mark_to_market(player, market, pos):
    """P&L latent d'une position spot donnée."""
    sp = spot(market, pos["pair"])
    if sp is None or not pos.get("entry_rate"):
        return 0.0
    sign = 1.0 if pos["direction"] == "long" else -1.0
    return pos["notional"] * (sp / pos["entry_rate"] - 1.0) * sign


def close_spot(player, market, position_id):
    """Ferme une position spot (par index dans fx_positions). Crédite/débite
    le P&L réalisé du cash, retire la position."""
    positions = getattr(player, "fx_positions", []) or []
    if position_id < 0 or position_id >= len(positions):
        return {"ok": False, "reason": "position"}
    pos = positions[position_id]
    pnl = mark_to_market(player, market, pos)
    player.cash += pnl
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
    positions.pop(position_id)
    player.fx_positions = positions
    return {"ok": True, "pnl": pnl, "position": pos}


def holdings_value(player, market):
    """Somme des P&L latents de toutes les positions spot ouvertes."""
    total = 0.0
    for pos in getattr(player, "fx_positions", []) or []:
        total += mark_to_market(player, market, pos)
    return total


def holdings(player, market):
    """Détail des positions spot en cours, pour affichage."""
    out = []
    for i, pos in enumerate(getattr(player, "fx_positions", []) or []):
        cur = spot(market, pos["pair"])
        pnl = mark_to_market(player, market, pos)
        out.append({"id": i, "pair": pos["pair"], "direction": pos["direction"],
                     "notional": pos["notional"], "entry_rate": pos["entry_rate"],
                     "spot": cur, "pnl": pnl})
    return out


# ---------------------------------------------------------------- forward trading
def open_forward(player, market, pair, direction, notional, tenor_months):
    """Ouvre un forward FX (aucun débit de cash à l'entrée, comme les swaps).
    Nécessite forward_unlocked(player)."""
    if not forward_unlocked(player):
        return {"ok": False, "reason": "locked"}
    if direction not in ("long", "short"):
        return {"ok": False, "reason": "direction"}
    if notional <= 0:
        return {"ok": False, "reason": "notional"}
    q = quote_forward(market, pair, tenor_months)
    if not q.get("ok"):
        return q
    pos = {
        "pair": pair, "direction": direction, "notional": float(notional),
        "locked_rate": q["forward_rate"], "tenor_months": tenor_months,
        "opened_step": market.step_count, "maturity_step": q["maturity_step"],
    }
    player.fx_forwards = getattr(player, "fx_forwards", [])
    player.fx_forwards.append(pos)
    return {"ok": True, "position": pos}


def evaluate_due(player, market):
    """Dénoue les forwards arrivés à échéance (règlement en cash net).
    Crédite/débite le cash, retire les positions échues. Retourne les
    résultats (payoff, pnl). Les positions non échues sont conservées."""
    results, still = [], []
    for pos in getattr(player, "fx_forwards", []) or []:
        if market.step_count >= pos["maturity_step"]:
            final = spot(market, pos["pair"])
            final = final if final is not None else pos["locked_rate"]
            sign = 1.0 if pos["direction"] == "long" else -1.0
            payoff = pos["notional"] * (final / pos["locked_rate"] - 1.0) * sign
            if payoff:
                player.cash += payoff
            pnl = payoff
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
            results.append({"position": pos, "payoff": payoff, "pnl": pnl, "final": final})
        else:
            still.append(pos)
    player.fx_forwards = still
    return results


def forward_holdings(player, market):
    """Détail des forwards en cours, pour affichage."""
    out = []
    for i, pos in enumerate(getattr(player, "fx_forwards", []) or []):
        cur = spot(market, pos["pair"])
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        out.append({"id": i, "pair": pos["pair"], "direction": pos["direction"],
                     "notional": pos["notional"], "locked_rate": pos["locked_rate"],
                     "tenor_months": pos["tenor_months"], "spot": cur,
                     "steps_left": steps_left})
    return out


def all_quotes(market):
    return [quote_spot(market, p) for p in PAIRS]
