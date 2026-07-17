"""
impact_phrases.py — UNE PHRASE d'impact par instrument (logique pure).

Chaque desk affiche son jargon (bps, duration, jambes…) ; ce module le
traduit en UNE phrase concrète, dans la devise du joueur, affichée sur le
ticket AVANT de confirmer :

    Obligation : « coupon +X/tour · taux +1 pt → prix −Y % »
    CDS        : « vous payez X/tour ; si défaut, vous touchez ~+Y »
    IRS        : « taux +1 pt = ±X sur ce swap (DV01) »
    Repo       : « X de titres immobilisés → Y de cash, coût net Z/tour »
    FX (carry) : « portage net : ±X/tour sur cette position »
    TRS        : « vous recevez la perf de X, vous payez le financement (~Y/tour) »

Toutes les fonctions retournent une str (ou "" si l'entrée est inconnue) et
ne modifient JAMAIS l'état — appelables à chaque frame d'un ticket.
"""
from core import config
from core.i18n import get_lang

DAYS = config.DAYS_PER_STEP
_YR = DAYS / 365.0


def _L(fr, en):
    return en if get_lang() == "en" else fr


def _money(v):
    return f"{v:,.0f}"


def bond_impact(market, bond_id, qty):
    """Coupon par tour + sensibilité aux taux, pour `qty` obligations."""
    from core import bonds
    q = bonds.quote(market, bond_id)
    if not q or qty <= 0:
        return ""
    coupon_step = bonds.FACE * q["coupon"] * qty * _YR
    dur = q.get("mod_duration") or q.get("duration") or 0.0
    px_move = dur * 1.0   # +1 point de taux → -duration % de prix
    return _L(f"Coupon ~+{_money(coupon_step)}/tour · taux +1 pt → prix −{px_move:.1f}%",
              f"Coupon ~+{_money(coupon_step)}/step · rates +1 pt → price −{px_move:.1f}%")


def cds_impact(market, ticker, notional, years):
    """Prime payée par tour + paiement en cas de défaut."""
    from core import cds
    q = cds.quote(market, ticker, years)
    if not q or notional <= 0:
        return ""
    premium_step = notional * q["spread_bps"] / 10_000.0 * _YR
    payoff = notional * (1.0 - cds.RECOVERY if hasattr(cds, "RECOVERY") else 0.6)
    return _L(f"Vous payez ~{_money(premium_step)}/tour · si défaut de {ticker} : "
              f"~+{_money(payoff)} (PD {q['pd']*100:.1f}%)",
              f"You pay ~{_money(premium_step)}/step · if {ticker} defaults: "
              f"~+{_money(payoff)} (PD {q['pd']*100:.1f}%)")


def irs_impact(notional, years):
    """DV01 en devise : l'effet d'un point de taux sur le swap."""
    if notional <= 0:
        return ""
    dv01 = notional * max(0.5, years) * 0.0001
    move_1pt = dv01 * 100
    return _L(f"Taux +1 pt = ±{_money(move_1pt)} sur ce swap (selon votre jambe)",
              f"Rates +1 pt = ±{_money(move_1pt)} on this swap (by your leg)")


def repo_impact(collateral_value, cash_raised, rate_annual):
    """Ce que le repo immobilise, libère et coûte par tour."""
    if collateral_value <= 0:
        return ""
    cost_step = cash_raised * rate_annual * _YR
    return _L(f"{_money(collateral_value)} de titres immobilisés → "
              f"{_money(cash_raised)} de cash · coût ~{_money(cost_step)}/tour",
              f"{_money(collateral_value)} of collateral pledged → "
              f"{_money(cash_raised)} cash · cost ~{_money(cost_step)}/step")


def fx_carry_impact(notional, rate_diff_annual):
    """Portage net par tour d'une position FX (différentiel de taux)."""
    if notional <= 0:
        return ""
    carry_step = notional * rate_diff_annual * _YR
    if carry_step >= 0:
        return _L(f"Portage : ~+{_money(carry_step)}/tour tant que la paire ne bouge pas",
                  f"Carry: ~+{_money(carry_step)}/step while the pair stands still")
    return _L(f"Portage NÉGATIF : ~{_money(carry_step)}/tour — la position doit "
              f"s'apprécier pour compenser",
              f"NEGATIVE carry: ~{_money(carry_step)}/step — the position must "
              f"appreciate to compensate")


def trs_impact(notional, funding_rate_annual, side="receiver"):
    """Les deux jambes d'un TRS en une phrase."""
    if notional <= 0:
        return ""
    funding_step = notional * funding_rate_annual * _YR
    if side == "receiver":
        return _L(f"Vous RECEVEZ perf + dividendes, vous PAYEZ le financement "
                  f"(~{_money(funding_step)}/tour) — sans mobiliser le notionnel",
                  f"You RECEIVE perf + dividends, you PAY funding "
                  f"(~{_money(funding_step)}/step) — without deploying the notional")
    return _L(f"Vous PAYEZ perf + dividendes, vous RECEVEZ le financement "
              f"(~+{_money(funding_step)}/tour) — équivalent d'un short synthétique",
              f"You PAY perf + dividends, you RECEIVE funding "
              f"(~+{_money(funding_step)}/step) — a synthetic short")


def option_impact(premium, qty, theta_per_step, kind="call"):
    """Le thêta en devise : ce que l'option coûte par tour si rien ne bouge."""
    if qty <= 0:
        return ""
    total_theta = abs(theta_per_step) * qty
    return _L(f"Si rien ne bouge, cette position perd ~{_money(total_theta)}/tour "
              f"(thêta) — le temps joue contre l'acheteur",
              f"If nothing moves, this position loses ~{_money(total_theta)}/step "
              f"(theta) — time works against the buyer")


def merger_arb_impact(price, offer_price, steps_left):
    """Spread d'arbitrage → probabilité implicite de succès de l'OPA."""
    if not price or not offer_price or offer_price <= 0:
        return ""
    spread_pct = (offer_price / price - 1.0) * 100.0
    # approximation pédagogique : prix = proba×offre + (1-proba)×prix_préoffre
    implied = max(0.0, min(1.0, price / offer_price))
    return _L(f"Spread {spread_pct:+.1f}% : le marché price ~{implied*100:.0f}% de "
              f"chances que l'OPA aboutisse ({steps_left} pas restants)",
              f"Spread {spread_pct:+.1f}%: the market prices ~{implied*100:.0f}% "
              f"odds the deal closes ({steps_left} steps left)")
