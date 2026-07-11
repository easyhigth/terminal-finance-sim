"""
portfolio_missions.py — Items de mission « état réel du portefeuille » (logique
pure, sans pygame).

Contrairement aux items classiques (core/missions.py, tirés de la banque de
questions — un quiz générique), CEUX-LÀ interrogent l'ÉTAT VIVANT du book du
joueur au moment où la mission est générée : diversification sectorielle,
levier, coussin de cash, détention d'obligations, couverture en place. Le
joueur doit juger CORRECTEMENT si son propre portefeuille remplit le critère
— pas juste réciter une formule.

Réutilise le format MCQ existant (`core/missions._mcq`) : deux choix
« Oui »/« Non », la bonne réponse est calculée depuis le VRAI player/market à
la génération. Aucune UI dédiée n'est nécessaire (app_mission.py affiche déjà
n'importe quel item "mcq") — juste une source d'items différente.
"""
import random


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def _sector_diversification_ok(player, market, min_sectors=3):
    comp = {c["ticker"]: c for c in market.companies}
    sectors = {comp[tk]["sector"] for tk, pos in player.portfolio.items()
              if pos["shares"] > 0 and tk in comp}
    return len(sectors) >= min_sectors


def _leverage_ok(player, market, max_leverage=1.5):
    from core import portfolio_margin as pm
    return pm.leverage(player, market) <= max_leverage


def _cash_buffer_ok(player, market, min_frac=0.10):
    from core import portfolio_margin as pm
    nw = pm.net_worth(player, market)
    if nw <= 0:
        return False
    return (player.cash / nw) >= min_frac


def _has_bond_ok(player, market):
    return bool(getattr(player, "bonds", None))


def _has_hedge_ok(player, market):
    has_short = any(pos["shares"] < 0 for pos in player.portfolio.values())
    has_put = any(o.get("option_type") == "put" for o in getattr(player, "options", []))
    return has_short or has_put


# (id, prompt_fr, prompt_en, check_fn, expl_fr, expl_en)
PRACTICAL_CHECKS = [
    ("diversify",
     "Votre portefeuille actions détient-il des positions dans au moins 3 secteurs "
     "différents ?",
     "Does your equity book currently hold positions across at least 3 different "
     "sectors?",
     _sector_diversification_ok,
     "La concentration sectorielle est un risque non rémunéré : un choc sur un "
     "seul secteur peut effacer tout le portefeuille.",
     "Sector concentration is an uncompensated risk: a single-sector shock can "
     "wipe out the whole book."),
    ("leverage",
     "Votre levier (valeur du book / patrimoine net) est-il actuellement inférieur "
     "ou égal à 1,5x ?",
     "Is your leverage (book value / net worth) currently at or below 1.5x?",
     _leverage_ok,
     "Un levier élevé amplifie les pertes autant que les gains — et rapproche "
     "l'appel de marge.",
     "High leverage amplifies losses as much as gains — and brings a margin call "
     "closer."),
    ("cash_buffer",
     "Votre trésorerie représente-t-elle au moins 10 % de votre patrimoine net "
     "en ce moment ?",
     "Does your cash currently represent at least 10% of your net worth?",
     _cash_buffer_ok,
     "Un coussin de cash absorbe un appel de marge ou une opportunité sans "
     "liquider une position en catastrophe.",
     "A cash buffer absorbs a margin call or an opportunity without a fire-sale "
     "liquidation."),
    ("has_bond",
     "Détenez-vous actuellement au moins une obligation ?",
     "Do you currently hold at least one bond?",
     _has_bond_ok,
     "Les obligations diversifient un book actions et amortissent une récession.",
     "Bonds diversify an equity book and cushion a recession."),
    ("has_hedge",
     "Avez-vous une couverture en place en ce moment (position courte ou option "
     "put) ?",
     "Do you currently have a hedge in place (a short position or a put option)?",
     _has_hedge_ok,
     "Une couverture réduit l'exposition nette sans liquider les convictions "
     "longues.",
     "A hedge reduces net exposure without liquidating long-term convictions."),
]


def practical_item(check_id, player, market, rng=None, pool=None):
    """Construit un item MCQ « Oui/Non » sur le check `check_id`, résolu contre
    le VRAI état de `player`/`market`. None si l'id est inconnu dans `pool`
    (par défaut PRACTICAL_CHECKS)."""
    from core.missions import _mcq
    rng = rng or random
    pool = pool if pool is not None else PRACTICAL_CHECKS
    entry = next((c for c in pool if c[0] == check_id), None)
    if entry is None:
        return None
    _id, prompt_fr, prompt_en, check_fn, expl_fr, expl_en = entry
    ok = bool(check_fn(player, market))
    choices = [_L("Oui, c'est le cas actuellement.", "Yes, that's currently the case."),
               _L("Non, ce n'est pas le cas actuellement.", "No, that's not currently the case.")]
    correct_idx = 0 if ok else 1
    return _mcq(_L(prompt_fr, prompt_en), choices, correct_idx, _L(expl_fr, expl_en), rng)


def practical_items(player, market, count=2, rng=None, pool=None):
    """Tire `count` checks distincts (sans remise) dans `pool` (par défaut
    PRACTICAL_CHECKS) et renvoie leurs items MCQ."""
    rng = rng or random
    pool = pool if pool is not None else PRACTICAL_CHECKS
    ids = [c[0] for c in pool]
    picked = rng.sample(ids, k=min(count, len(ids)))
    return [practical_item(cid, player, market, rng=rng, pool=pool) for cid in picked]


# ---------------------------------------------------------------------------
# Checks EXCLUSIFS par voie — pour que les missions « état réel » du tier
# "portfolio" (VP et au-delà, cf. core/missions.py) interrogent l'état
# PROPRE au métier de la voie choisie plutôt qu'un quiz de diversification
# générique identique pour tout le monde : un banquier M&A est jugé sur ses
# LBO, un risk manager sur son budget de VaR, un quant sur son delta, un
# conseiller sur la santé de ses mandats. Un joueur "General"/Portfolio
# continue de recevoir exactement les checks génériques ci-dessus (aucun
# changement pour lui) — cf. `pool_for_track`.
# ---------------------------------------------------------------------------
def _owns_ma_target_ok(player, market):
    from core import ma
    return bool(ma.owned_tickers(player))


def _ma_leverage_ok(player, market, max_ratio=3.0):
    """Vrai si AUCUNE cible détenue n'a une dette qui dépasse `max_ratio`
    fois son CA annuel (vacuously vrai si aucune cible détenue)."""
    owned = (getattr(player, "ma_owned", None) or {}).values()
    if not owned:
        return True
    return all(inst["revenue"] <= 0 or inst["debt_balance"] / inst["revenue"] <= max_ratio
              for inst in owned)


def _var_within_firm_budget_ok(player, market):
    from core import risklimits
    return not risklimits.firm_var_check(player, market)["breach"]


def _holds_option_ok(player, market):
    return bool(getattr(player, "options", None))


def _delta_hedged_ok(player, market, tol=0.25):
    """Vrai si le delta NET (après actions) représente moins de `tol` fois le
    delta BRUT du book d'options (vacuously vrai si aucune option détenue)."""
    from core import delta_hedge
    rows = delta_hedge.book_delta_by_underlying(player, market)
    if not rows:
        return True
    gross = sum(abs(r["delta_shares"]) for r in rows) or 1.0
    net = sum(abs(r["net_shares"]) for r in rows)
    return (net / gross) <= tol


def _has_active_mandate_ok(player, market):
    return bool(getattr(player, "mandates", None))


def _mandate_constraints_ok(player, market):
    """Vrai si TOUS les mandats actifs respectent actuellement leurs
    contraintes (vacuously vrai si aucun mandat actif)."""
    from core import mandates
    active = getattr(player, "mandates", None) or []
    if not active:
        return True
    return all(mandates.check_constraints(player, market, m)["ok"] for m in active)


TRACK_CHECKS_EXTRA = [
    ("owns_target",
     "Détenez-vous actuellement au moins une cible M&A (LBO) ?",
     "Do you currently own at least one M&A target (LBO)?",
     _owns_ma_target_ok,
     "Sans cible détenue, le métier M&A reste théorique — la première "
     "acquisition est le vrai point de départ.",
     "Without a held target, the M&A job stays theoretical — the first "
     "acquisition is the real starting point."),
    ("ma_leverage",
     "Vos cibles M&A détenues ont-elles toutes une dette inférieure à 3x "
     "leur chiffre d'affaires annuel ?",
     "Do all your held M&A targets carry debt below 3x their annual "
     "revenue?",
     _ma_leverage_ok,
     "Un LBO surendetté ne survit pas au premier trimestre de cash-flow "
     "faible — la dette se sert AVANT le joueur.",
     "An over-leveraged LBO doesn't survive the first weak cash-flow "
     "quarter — debt gets serviced BEFORE the player."),
    ("var_budget",
     "Votre VaR actuelle respecte-t-elle le budget de risque imposé par "
     "votre grade ?",
     "Does your current VaR respect the risk budget imposed by your "
     "grade?",
     _var_within_firm_budget_ok,
     "Dépasser le budget de VaR de la firme entraîne un avertissement puis "
     "une réduction forcée de position — mieux vaut l'anticiper.",
     "Breaching the firm's VaR budget triggers a warning, then a forced "
     "position cut — better to anticipate it."),
    ("holds_option",
     "Détenez-vous actuellement au moins une option (call ou put) ?",
     "Do you currently hold at least one option (call or put)?",
     _holds_option_ok,
     "Le desk options est l'outil de prédilection du quant — sans position, "
     "les grecques restent une abstraction.",
     "The options desk is the quant's tool of choice — without a position, "
     "the greeks stay an abstraction."),
    ("delta_hedged",
     "Le delta NET de votre book d'options est-il actuellement faible "
     "(inférieur à 25 % du delta brut) ?",
     "Is your options book's NET delta currently low (under 25% of gross "
     "delta)?",
     _delta_hedged_ok,
     "Un book d'options non couvert en delta parie sur la DIRECTION du "
     "marché, pas sur sa VOLATILITÉ — souvent l'inverse de l'intention.",
     "An un-delta-hedged options book bets on market DIRECTION, not "
     "VOLATILITY — often the opposite of the intent."),
    ("has_mandate",
     "Avez-vous actuellement au moins un mandat client actif ?",
     "Do you currently have at least one active client mandate?",
     _has_active_mandate_ok,
     "Sans mandat actif, le métier de conseil reste sur le papier — un "
     "mandat gagné est le vrai test.",
     "Without an active mandate, the advisory job stays on paper — a won "
     "mandate is the real test."),
    ("mandate_constraints",
     "Tous vos mandats actifs respectent-ils actuellement leurs "
     "contraintes (objectif, bêta max, contraintes supplémentaires) ?",
     "Do all your active mandates currently respect their constraints "
     "(target, max beta, extra constraints)?",
     _mandate_constraints_ok,
     "Un mandat qui dérape n'attend pas toujours l'échéance : un client "
     "« strict » (assureur, institutionnel prudent) résilie dès qu'une "
     "contrainte casse.",
     "A drifting mandate doesn't always wait for the deadline: a "
     "\"strict\" client (insurer, conservative institutional) terminates "
     "as soon as a constraint breaks."),
]
_ALL_CHECKS = PRACTICAL_CHECKS + TRACK_CHECKS_EXTRA


def _pick(*ids):
    return [c for c in _ALL_CHECKS if c[0] in ids]


TRACK_CHECKS = {
    "M&A": _pick("owns_target", "ma_leverage", "leverage", "cash_buffer"),
    "Risk": _pick("var_budget", "has_hedge", "leverage", "diversify"),
    "Quant": _pick("holds_option", "delta_hedged", "leverage", "cash_buffer"),
    "Advisory": _pick("has_mandate", "mandate_constraints", "cash_buffer", "diversify"),
    "Portfolio": PRACTICAL_CHECKS,
}


def pool_for_track(track):
    """Pool de checks pour CETTE voie — les checks génériques (diversify/
    leverage/cash_buffer/has_bond/has_hedge) pour "General"/"Portfolio"/toute
    voie inconnue, un pool exclusif pour M&A/Risk/Quant/Advisory."""
    return TRACK_CHECKS.get(track, PRACTICAL_CHECKS)


def practical_items_for_track(player, market, count=2, rng=None):
    """`practical_items`, mais avec le pool de checks propre à la voie
    ACTUELLE du joueur (cf. `pool_for_track`) — la même mission « état réel »
    interroge un métier différent selon la spécialisation choisie."""
    track = getattr(player, "track", "General")
    return practical_items(player, market, count=count, rng=rng, pool=pool_for_track(track))
