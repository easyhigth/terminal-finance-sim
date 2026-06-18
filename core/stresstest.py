"""
stresstest.py — Stress test réglementaire périodique (sanction/récompense).

Tous les `STRESSTEST_PERIOD_QUARTERS` trimestres, un superviseur fictif (régulateur)
teste la résistance du portefeuille du joueur à un scénario de choc choisi au hasard
parmi ceux de `core.risk.STRESS`. Cadence choisie : 2 trimestres (~un stress test par
semestre) — plus fréquent qu'une revue de performance annuelle (`core.review`, 4
trimestres), pour donner un rythme de contrôle réglementaire distinct et plus serré.

Le verdict est basé sur le RATIO perte/valeur nette (pas un montant absolu), pour
rester cohérent à toute taille de portefeuille :
  - perte/net_worth <= FAIL_RATIO  -> réussite (résistance jugée suffisante)
  - perte/net_worth >  FAIL_RATIO  -> échec (sanction : réputation, éventuellement cash)

Une fois le résultat connu, le joueur répond via `acknowledge(player, action)` avec
`action` ∈ {"accept", "hedge_now"} :
  - "accept"    : prend acte du résultat. Aucun coût si réussite. En cas d'échec,
                  légère perte de réputation (négligence actée par le régulateur).
  - "hedge_now" : s'engage à réduire son exposition. Coût symbolique immédiat (petite
                  perte de cash, frais de couverture) mais limite la perte de
                  réputation en cas d'échec (geste proactif reconnu par le régulateur),
                  et donne un petit bonus de réputation en cas de réussite déjà
                  confortable. Pas de liquidation réelle de positions (MVP simple,
                  cohérent avec les primitives existantes) : effet réputation+cash.

Logique pure, sans pygame — testable headless. Aléa via `random` (non seedé), comme
`core.review`/`core.mandates` pour des mécaniques de jeu non liées au marché.
"""
import random

from core import portfolio as pf
from core import risk

STRESSTEST_PERIOD_QUARTERS = 2   # un stress test tous les 2 trimestres (~semestriel)

FAIL_RATIO = 0.15    # perte > 15% de la valeur nette => échec du stress test
HISTORY_CAP = 10


# ---------------------------------------------------------------------------
# Déclenchement
# ---------------------------------------------------------------------------
def maybe_trigger(player, quarter_changed, market=None):
    """Déclenche éventuellement un stress test réglementaire.

    Appelée chaque tour par l'orchestrateur avec `quarter_changed` (vrai quand le
    trimestre vient de changer, cf. `summary["quarter_changed"]` de
    `GameState.advance_step`) et `market` (le moteur de marché courant, nécessaire
    pour évaluer les positions réelles). Si la période est écoulée et qu'aucun test
    n'est déjà en attente, choisit un scénario au hasard parmi `core.risk.STRESS`,
    calcule l'impact via `risk.stress` (et `risk.simulate` pour contextualiser avec
    la VaR/CVaR du book), assigne le résultat à `player.pending_stresstest` et le
    retourne. Sinon retourne None.
    """
    if not quarter_changed:
        return None
    if player.pending_stresstest is not None:
        return None
    if player.quarter - player.last_stresstest_quarter < STRESSTEST_PERIOD_QUARTERS:
        return None
    if market is None:
        return None

    scenario = random.choice(list(risk.STRESS))
    impact = risk.stress(player, market, scenario)
    net_worth = pf.net_worth(player, market)
    loss = max(0.0, -impact["total"]) * 1e6   # impact["total"] est en M, loss en valeur monétaire
    loss_ratio = (loss / net_worth) if net_worth > 0 else 1.0
    passed = loss_ratio <= FAIL_RATIO

    try:
        sim = risk.simulate(player, market)
        var_m = sim.get("var")
    except Exception:
        var_m = None

    test = {
        "quarter": player.quarter,
        "scenario": scenario,
        "impact_total": impact["total"],     # en M, signé (négatif = perte)
        "impact_equity": impact["equity"],
        "impact_bond": impact["bond"],
        "net_worth": net_worth,
        "loss": loss,                        # perte en valeur monétaire, >= 0
        "loss_ratio": loss_ratio,
        "fail_ratio": FAIL_RATIO,
        "var": var_m,                         # VaR du book pour contexte, ou None
        "passed": passed,
    }
    player.pending_stresstest = test
    return test


def has_pending(player):
    """Utilitaire pour l'orchestrateur : un stress test attend-il une réponse ?"""
    return bool(player.pending_stresstest)


# ---------------------------------------------------------------------------
# Résolution
# ---------------------------------------------------------------------------
def acknowledge(player, action):
    """Résout le stress test en attente selon `action` ∈ {"accept", "hedge_now"}.

    Retourne un dict résultat :
      {ok, action, rep_delta, cash_delta, message}
    ou {"ok": False, "reason": "no_pending"} si aucun test n'est en attente.
    """
    test = player.pending_stresstest
    if test is None:
        return {"ok": False, "reason": "no_pending"}

    passed = test["passed"]
    scenario = test["scenario"]

    if action == "accept":
        if passed:
            rep_delta = random.choice([0, 1])
            cash_delta = 0.0
            message = (f"Le régulateur prend acte : votre portefeuille résiste au "
                       f"scénario « {scenario} ». Aucune sanction.")
        else:
            rep_delta = -random.choice([2, 3, 4])
            cash_delta = 0.0
            message = (f"Le régulateur constate que votre portefeuille ne résiste "
                       f"pas au scénario « {scenario} » (perte de "
                       f"{test['loss_ratio']*100:.1f}% de la valeur nette). "
                       "Aucune action correctrice engagée : un avertissement est noté.")
        ok = passed

    elif action == "hedge_now":
        hedge_cost = max(500.0, 0.002 * test["net_worth"])   # frais de couverture symbolique
        cash_delta = -hedge_cost
        player.adjust_cash(cash_delta)
        if passed:
            rep_delta = random.choice([1, 2])
            message = (f"Vous renforcez vos couvertures par prudence malgré un "
                       f"résultat satisfaisant au scénario « {scenario} ». Le "
                       f"régulateur salue la démarche proactive (coût : "
                       f"{hedge_cost:,.0f}).")
        else:
            rep_delta = -random.choice([0, 1])
            message = (f"Vous échouez au scénario « {scenario} » mais vous engagez "
                       f"immédiatement à réduire votre exposition. Le régulateur "
                       f"reconnaît le geste et limite la sanction (coût de "
                       f"couverture : {hedge_cost:,.0f}).")
        ok = passed

    else:
        return {"ok": False, "reason": "invalid_action"}

    player.adjust_reputation(rep_delta)
    if action != "hedge_now":
        cash_delta = 0.0

    result = {"ok": ok, "action": action, "rep_delta": rep_delta,
              "cash_delta": cash_delta, "message": message,
              "scenario": scenario, "passed": passed}

    player.stresstest_history.append({
        "quarter": test["quarter"],
        "scenario": scenario,
        "passed": passed,
        "loss_ratio": test["loss_ratio"],
        "action": action,
        "rep_delta": rep_delta,
        "cash_delta": cash_delta,
    })
    if len(player.stresstest_history) > HISTORY_CAP:
        player.stresstest_history = player.stresstest_history[-HISTORY_CAP:]

    player.last_stresstest_quarter = player.quarter
    player.pending_stresstest = None
    return result
