"""
coach.py — COACH COMPORTEMENTAL trimestriel (logique pure).

Le journal de trades (core/journal.py) enregistre déjà tout ; personne ne le
relisait à la place du joueur. Le coach analyse les trades du TRIMESTRE
écoulé et détecte des biais réels de finance comportementale, nommés et
expliqués — le jeu vous apprend quelque chose SUR VOUS :

  - EFFET DE DISPOSITION : vous encaissez vos gains vite mais laissez courir
    vos pertes (ventes gagnantes nombreuses et petites vs pertes rares mais
    grosses) ;
  - SUR-TRADING APRÈS PERTE : votre cadence de trading s'emballe juste après
    un trade perdant (revanche) ;
  - CONCENTRATION RAMPANTE : une part croissante de votre notional se joue
    sur un seul titre ;
  - FRAIS QUI RONGENT : le total des commissions du trimestre dépasse une
    fraction sensible du P&L réalisé.

Rendu : un rapport par trimestre (si assez de trades), livré en message
inbox par le hook de pas "coach" — dict {"quarter", "findings": [...]},
chaque finding = {"bias", "title", "detail", "severity"}. Aucune pénalité :
le coach informe, il ne punit pas.
"""
from core.i18n import get_lang

MIN_TRADES = 6          # en dessous, pas assez de matière pour juger
DISPOSITION_RATIO = 1.6  # perte moyenne > 1.6× gain moyen (avec + de gains encaissés)
OVERTRADE_FACTOR = 2.0   # cadence post-perte > 2× la cadence normale
CONCENTRATION_SHARE = 0.5  # un titre > 50 % du notional tradé
FEE_DRAG_SHARE = 0.25    # frais > 25 % du P&L réalisé positif


def _L(fr, en):
    return en if get_lang() == "en" else fr


def _quarter_trades(player):
    """Trades du trimestre en cours de clôture (fenêtre par jours)."""
    from core import config
    q_start = (player.quarter - 1) * config.DAYS_PER_QUARTER + 1
    return [t for t in getattr(player, "trade_journal", None) or []
            if t.get("day", 0) >= q_start]


def _check_disposition(trades):
    sells = [t for t in trades if t.get("realized") is not None]
    wins = [t["realized"] for t in sells if t["realized"] > 0]
    losses = [-t["realized"] for t in sells if t["realized"] < 0]
    if len(wins) < 3 or not losses:
        return None
    avg_win, avg_loss = sum(wins) / len(wins), sum(losses) / len(losses)
    if len(wins) >= 2 * len(losses) and avg_loss > DISPOSITION_RATIO * avg_win:
        return {
            "bias": "disposition", "severity": "warn",
            "title": _L("Effet de disposition", "Disposition effect"),
            "detail": _L(
                f"Vous avez encaissé {len(wins)} gains (moyenne "
                f"{avg_win:,.0f}) mais vos {len(losses)} pertes sont bien plus "
                f"grosses (moyenne {avg_loss:,.0f}). Classique : on vend ses "
                f"gagnants trop tôt et on laisse courir ses perdants. Posez des "
                f"stops AVANT d'entrer.",
                f"You banked {len(wins)} wins (avg {avg_win:,.0f}) but your "
                f"{len(losses)} losses are far larger (avg {avg_loss:,.0f}). "
                f"Classic: selling winners too early, letting losers run. Set "
                f"stops BEFORE entering."),
        }
    return None


def _check_overtrading(trades):
    if len(trades) < MIN_TRADES:
        return None
    # cadence : trades par jour, comparée juste après un trade perdant
    days = sorted({t["day"] for t in trades})
    if len(days) < 4:
        return None
    base_rate = len(trades) / max(1, days[-1] - days[0] + 1)
    loss_days = {t["day"] for t in trades
                 if t.get("realized") is not None and t["realized"] < 0}
    post_loss = [t for t in trades
                 if any(0 < t["day"] - d <= 5 for d in loss_days)]
    if not loss_days or not post_loss:
        return None
    window = 5 * len(loss_days)
    post_rate = len(post_loss) / max(1, window)
    if post_rate > OVERTRADE_FACTOR * base_rate:
        return {
            "bias": "overtrading", "severity": "warn",
            "title": _L("Sur-trading après perte", "Post-loss overtrading"),
            "detail": _L(
                f"Votre cadence de trading explose dans les jours qui suivent "
                f"une perte ({post_rate:.2f} vs {base_rate:.2f} trades/jour). "
                f"Le « trade de revanche » est le plus cher de tous : imposez-"
                f"vous une pause après une perte.",
                f"Your trading pace explodes in the days after a loss "
                f"({post_rate:.2f} vs {base_rate:.2f} trades/day). Revenge "
                f"trading is the most expensive kind: force a pause after a "
                f"loss."),
        }
    return None


def _check_concentration(trades):
    if len(trades) < MIN_TRADES:
        return None
    by_key = {}
    total = 0.0
    for t in trades:
        by_key[t["key"]] = by_key.get(t["key"], 0.0) + t.get("notional", 0.0)
        total += t.get("notional", 0.0)
    if total <= 0:
        return None
    key, worst = max(by_key.items(), key=lambda kv: kv[1])
    share = worst / total
    if share > CONCENTRATION_SHARE and len(by_key) > 1:
        return {
            "bias": "concentration", "severity": "warn",
            "title": _L("Concentration rampante", "Creeping concentration"),
            "detail": _L(
                f"{share:.0%} de votre volume tradé ce trimestre s'est joué sur "
                f"{key}. Une conviction, très bien — une dépendance, non : votre "
                f"P&L respire au rythme d'un seul titre.",
                f"{share:.0%} of your traded volume this quarter was on {key}. "
                f"Conviction is fine — dependence is not: your P&L breathes "
                f"with a single name."),
        }
    return None


def _check_fee_drag(trades):
    fees = sum(t.get("fee", 0.0) for t in trades)
    realized = sum(t["realized"] for t in trades if t.get("realized") is not None)
    if fees <= 0 or realized <= 0:
        return None
    if fees > FEE_DRAG_SHARE * realized:
        return {
            "bias": "fees", "severity": "info",
            "title": _L("Les frais rongent le résultat", "Fees eat the result"),
            "detail": _L(
                f"{fees:,.0f} de commissions pour {realized:,.0f} de P&L "
                f"réalisé ce trimestre ({fees / realized:.0%}). Chaque "
                f"aller-retour paie spread + impact + commission : tradez "
                f"moins, tradez plus gros, ou laissez porter.",
                f"{fees:,.0f} in commissions for {realized:,.0f} of realized "
                f"P&L this quarter ({fees / realized:.0%}). Every round trip "
                f"pays spread + impact + commission: trade less, size up, or "
                f"let it ride."),
        }
    return None


def quarterly_review(player):
    """Analyse les trades du trimestre. Retourne le rapport (dict) ou None si
    pas assez de matière. Sans effet de bord (livraison : cf. hook de pas)."""
    trades = _quarter_trades(player)
    if len(trades) < MIN_TRADES:
        return None
    findings = [f for f in (
        _check_disposition(trades),
        _check_overtrading(trades),
        _check_concentration(trades),
        _check_fee_drag(trades),
    ) if f]
    return {"quarter": player.quarter, "n_trades": len(trades),
            "findings": findings}


def deliver(player, report):
    """Livre le rapport en message inbox (du desk « coach interne »). Un
    trimestre SANS biais détecté envoie aussi un mot — le renforcement
    positif fait partie du coaching."""
    from core import inbox as _inbox
    if report["findings"]:
        body = _L(f"Revue de vos {report['n_trades']} trades du trimestre :\n\n",
                  f"Review of your {report['n_trades']} trades this quarter:\n\n")
        for f in report["findings"]:
            body += f"• {f['title']} — {f['detail']}\n\n"
        subject = _L("Coach : vos biais du trimestre", "Coach: your biases this quarter")
    else:
        subject = _L("Coach : trimestre discipliné", "Coach: a disciplined quarter")
        body = _L(f"{report['n_trades']} trades passés en revue : pas de biais "
                  f"flagrant ce trimestre. Gains et pertes coupés proprement, "
                  f"volume réparti. Continuez exactement comme ça.",
                  f"{report['n_trades']} trades reviewed: no glaring bias this "
                  f"quarter. Wins and losses cut cleanly, volume spread out. "
                  f"Keep doing exactly this.")
    _inbox.push(player, "desk", _L("Coach interne", "Internal coach"),
                subject, body)
