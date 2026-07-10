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


def practical_item(check_id, player, market, rng=None):
    """Construit un item MCQ « Oui/Non » sur le check `check_id`, résolu contre
    le VRAI état de `player`/`market`. None si l'id est inconnu."""
    from core.missions import _mcq
    rng = rng or random
    entry = next((c for c in PRACTICAL_CHECKS if c[0] == check_id), None)
    if entry is None:
        return None
    _id, prompt_fr, prompt_en, check_fn, expl_fr, expl_en = entry
    ok = bool(check_fn(player, market))
    choices = [_L("Oui, c'est le cas actuellement.", "Yes, that's currently the case."),
               _L("Non, ce n'est pas le cas actuellement.", "No, that's not currently the case.")]
    correct_idx = 0 if ok else 1
    return _mcq(_L(prompt_fr, prompt_en), choices, correct_idx, _L(expl_fr, expl_en), rng)


def practical_items(player, market, count=2, rng=None):
    """Tire `count` checks distincts (sans remise) et renvoie leurs items MCQ."""
    rng = rng or random
    ids = [c[0] for c in PRACTICAL_CHECKS]
    picked = rng.sample(ids, k=min(count, len(ids)))
    return [practical_item(cid, player, market, rng=rng) for cid in picked]
