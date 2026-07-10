"""
regime_inference.py — Inférence bayésienne du régime de marché (logique pure).

Le moteur du jeu a de VRAIS régimes cachés (market.regime : Calme,
Expansion, Récession… — la toile de fond lente qui module dérive et chocs).
Le joueur ne les voit pas directement : il ne voit que les RENDEMENTS. Ce
module fait ce que ferait un quant : un FILTRE BAYÉSIEN à 2 états
(CALME / STRESS) sur les rendements observables de l'indice :

    P(état_t | r_1..t) ∝ N(r_t ; 0, σ_état) · Σ P(transition) · P(état_{t−1})

- les émissions sont deux lois normales (σ_calme < σ_stress), calibrées
  sur l'historique lui-même (écart-type des rendements sous/au-dessus de
  la médiane des |r|) ;
- la matrice de transition est COLLANTE (p_rester = 0,95) : les régimes
  durent — c'est ce qui distingue un régime d'un simple mauvais jour.

Sortie : la probabilité de stress DANS LE TEMPS (la bande qu'affichent les
vrais modèles de régime), le verdict courant, et — pédagogie du jeu — la
VÉRITÉ du moteur (market.regime) à côté, pour voir si le filtre l'a
retrouvée depuis les seuls prix.
"""
import numpy as np

STICKY = 0.95                # P(rester dans le même régime)
STRESS_THRESHOLD = 0.60      # au-dessus : on se déclare « en stress »


def emissions_from_history(returns):
    """Calibre (σ_calme, σ_stress) sur l'historique : écart-type des
    rendements dont |r| est sous / au-dessus de la médiane des |r|.
    Renvoie None si dégénéré."""
    r = np.asarray(returns, dtype=float)
    if len(r) < 20:
        return None
    med = np.median(np.abs(r))
    calm = r[np.abs(r) <= med]
    stress = r[np.abs(r) > med]
    if len(calm) < 5 or len(stress) < 5:
        return None
    s_calm = float(calm.std())
    s_stress = float(stress.std())
    if s_calm <= 0 or s_stress <= s_calm:
        return None
    return s_calm, s_stress


def filter_probabilities(returns, sticky=STICKY):
    """Filtre avant (forward filter) à 2 états. Renvoie None si historique
    court, sinon np.array des P(stress | données jusqu'à t)."""
    em = emissions_from_history(returns)
    if em is None:
        return None
    s_calm, s_stress = em
    r = np.asarray(returns, dtype=float)

    def dens(x, s):
        return np.exp(-0.5 * (x / s) ** 2) / s
    p_stress = 0.5
    out = []
    for x in r:
        # transition collante puis mise à jour bayésienne
        prior = p_stress * sticky + (1.0 - p_stress) * (1.0 - sticky)
        num = prior * dens(x, s_stress)
        den = num + (1.0 - prior) * dens(x, s_calm)
        p_stress = float(num / den) if den > 0 else 0.5
        out.append(p_stress)
    return np.asarray(out)


def infer(market, lookback=104):
    """Analyse complète sur l'indice de référence. Renvoie None si
    historique court, sinon {probs (array P(stress)), p_now, inferred
    ('CALME'|'STRESS'), truth (market.regime), truth_is_stress,
    agreement}."""
    from core import quant_tools as QT
    idx = QT.main_index(market)
    if idx is None:
        return None
    rets = QT.index_returns(market, idx, lookback)
    probs = filter_probabilities(rets)
    if probs is None:
        return None
    p_now = float(probs[-1])
    inferred = "STRESS" if p_now >= STRESS_THRESHOLD else "CALME"
    truth = getattr(market, "regime", "?")
    truth_is_stress = truth in ("Volatil", "Récession")   # cf. market.REGIMES
    agreement = (inferred == "STRESS") == truth_is_stress
    return {"probs": probs, "p_now": p_now, "inferred": inferred,
            "truth": truth, "truth_is_stress": truth_is_stress,
            "agreement": agreement, "index": idx}
