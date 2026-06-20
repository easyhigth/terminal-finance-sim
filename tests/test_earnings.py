"""Tests du moteur d'earnings enrichi (core/market.py) : anticipation /
pré-positionnement, gap d'annonce, guidance, révisions d'analystes et drift
post-annonce (PEAD). Chantier 13/15.

Tous ces mécanismes doivent rester déterministes : (seed, step_count)
reconstruit l'état exact, y compris les nouveaux états (next_surprise,
next_guidance, guidance_bias, pead_state, last_guidance).
"""
import numpy as np
import pytest

from core.market import (
    EARN_ANTICIPATION_WINDOW,
    EARN_PERIOD,
    GUIDANCE_RAISE_THRESH,
    PEAD_DECAY,
    PEAD_HORIZON_STEPS,
    REVISION_PROBA,
    Market,
)


# ------------------------------------------------------------------- déterminisme
def test_earnings_engine_state_is_deterministic():
    """Les nouveaux états (surprise/guidance pré-tirées, biais, PEAD résiduel)
    doivent être identiques pour une même graine après le même nombre de pas."""
    a = Market(seed=11); a.fast_forward(50)
    b = Market(seed=11); b.fast_forward(50)
    assert np.allclose(a.next_surprise, b.next_surprise)
    assert np.allclose(a.next_guidance, b.next_guidance)
    assert np.allclose(a.guidance_bias, b.guidance_bias)
    assert np.allclose(a.pead_state, b.pead_state)
    assert a.last_guidance == b.last_guidance
    assert np.allclose(a.price, b.price)


def test_metrics_anticipation_fields_are_deterministic():
    a = Market(seed=23); a.fast_forward(35)
    b = Market(seed=23); b.fast_forward(35)
    tk = a.companies[5]["ticker"]
    ma, mb = a.metrics(tk), b.metrics(tk)
    assert ma["steps_to_earnings"] == mb["steps_to_earnings"]
    assert ma["earnings_anticipation"] == mb["earnings_anticipation"]
    assert ma["pead_drift_remaining"] == pytest.approx(mb["pead_drift_remaining"])
    assert ma["last_guidance"] == mb["last_guidance"]


# ---------------------------------------------------------------- anticipation
def test_anticipation_drift_oriented_toward_known_next_surprise():
    """Le drift de pré-positionnement doit, EN MOYENNE sur de nombreuses
    sociétés/essais, être orienté dans le même sens que la surprise déjà
    tirée (et connue) du prochain print -- corrélation directionnelle, pas
    une prédiction parfaite."""
    m = Market(seed=77)
    same_sign = 0
    total = 0
    for _ in range(EARN_ANTICIPATION_WINDOW * 6):
        shock = m._step_anticipation()
        idx = np.arange(m.n)
        steps_to_report = (idx - m.step_count) % EARN_PERIOD
        in_window = (steps_to_report >= 1) & (steps_to_report <= EARN_ANTICIPATION_WINDOW)
        for i in np.where(in_window)[0]:
            if abs(m.next_surprise[i]) > 1e-9:
                total += 1
                if np.sign(shock[i]) == np.sign(m.next_surprise[i]):
                    same_sign += 1
        m.step()
    assert total > 100
    # le drift suit le signe de la surprise à venir nettement plus souvent
    # qu'un tirage à pile-ou-face (50%) -- corrélation directionnelle. Le
    # signal combine surprise + guidance_bias (GUIDANCE_TO_ANTICIPATION_K),
    # donc une minorité de cas peut voir le biais de guidance inverser le
    # signe net même quand la surprise seule serait du signe opposé.
    assert same_sign / total > 0.85


def test_anticipation_zero_outside_window():
    m = Market(seed=3)
    m.fast_forward(2)
    idx = np.arange(m.n)
    steps_to_report = (idx - m.step_count) % EARN_PERIOD
    shock = m._step_anticipation()
    out_of_window = (steps_to_report == 0) | (steps_to_report > EARN_ANTICIPATION_WINDOW)
    assert np.allclose(shock[out_of_window], 0.0)


def test_anticipation_consumes_no_new_rng_draw():
    """_step_anticipation ne fait aucun tirage rng (pure relecture d'état déjà
    fixé) : appelé deux fois de suite, il doit renvoyer le même résultat."""
    m = Market(seed=9)
    m.fast_forward(5)
    s1 = m._step_anticipation()
    s2 = m._step_anticipation()
    assert np.allclose(s1, s2)


# -------------------------------------------------------------- gap d'annonce
def test_announcement_gap_scales_with_surprise_magnitude():
    """Le choc de cours du jour de publication doit croître avec l'ampleur de
    la surprise -- on le vérifie en imposant des surprises de magnitudes
    croissantes et en lisant le gap produit par _step_earnings."""
    m = Market(seed=5)
    m.fast_forward(1)
    idx = np.arange(m.n)
    due = idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)]
    assert len(due) > 0
    i = int(due[0])
    gaps = []
    for surprise_mag in (0.01, 0.03, 0.06, 0.10):
        m.next_surprise[i] = surprise_mag
        m.next_guidance[i] = 0.0  # isole le gap de surprise de l'impact guidance
        shock = m._step_earnings()
        gaps.append(shock[i])
        # _step_earnings a tiré la prochaine surprise/guidance -> on la remet à 0
        # avant le prochain essai pour rester comparable.
        m.next_surprise[i] = 0.0
        m.next_guidance[i] = 0.0
    assert all(g2 > g1 for g1, g2 in zip(gaps, gaps[1:]))


def test_announcement_gap_sign_matches_surprise_sign():
    m = Market(seed=6)
    m.fast_forward(1)
    idx = np.arange(m.n)
    due = idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)]
    i = int(due[0])
    m.next_surprise[i] = -0.08
    m.next_guidance[i] = 0.0
    shock = m._step_earnings()
    assert shock[i] < 0


# -------------------------------------------------------------------- guidance
def test_guidance_has_distinguishable_price_impact():
    """Pour une MÊME surprise, une guidance positive vs négative doit produire
    des chocs de cours distincts (impact propre, indépendant du gap)."""
    m = Market(seed=8)
    m.fast_forward(1)
    idx = np.arange(m.n)
    due = idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)]
    i = int(due[0])

    m.next_surprise[i] = 0.02
    m.next_guidance[i] = 0.05
    shock_up = m._step_earnings()[i]
    m.next_surprise[i] = 0.02
    m.next_guidance[i] = -0.05
    shock_down = m._step_earnings()[i]

    assert shock_up > shock_down


def test_guidance_label_thresholds():
    m = Market(seed=8)
    m.fast_forward(1)
    idx = np.arange(m.n)
    due = idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)]
    i = int(due[0])
    tk = m.companies[i]["ticker"]

    m.next_surprise[i] = 0.0
    m.next_guidance[i] = GUIDANCE_RAISE_THRESH + 0.01
    m._step_earnings()
    assert m.last_guidance[tk]["label"] == "relevée"

    m.next_surprise[i] = 0.0
    m.next_guidance[i] = -(GUIDANCE_RAISE_THRESH + 0.01)
    m._step_earnings()
    assert m.last_guidance[tk]["label"] == "abaissée"

    m.next_surprise[i] = 0.0
    m.next_guidance[i] = 0.0
    m._step_earnings()
    assert m.last_guidance[tk]["label"] == "maintenue"


def test_guidance_feeds_next_anticipation_bias():
    """La guidance du cycle courant doit devenir le guidance_bias utilisé par
    l'anticipation du cycle SUIVANT (remplacement, pas de cumul)."""
    m = Market(seed=8)
    m.fast_forward(1)
    idx = np.arange(m.n)
    due = idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)]
    i = int(due[0])
    m.next_surprise[i] = 0.0
    m.next_guidance[i] = 0.04
    m._step_earnings()
    assert m.guidance_bias[i] == pytest.approx(0.04)


# ------------------------------------------------------------------- révisions
def test_revisions_occur_and_are_bounded():
    """Sur un grand nombre de pas, des révisions doivent se produire (proba
    REVISION_PROBA par société/pas hors fenêtre d'annonce) avec un impact
    petit et borné (pas de saut comparable à un vrai gap)."""
    m = Market(seed=15)
    nonzero = 0
    max_abs = 0.0
    n_steps = 60
    for _ in range(n_steps):
        shock = m._step_revisions()
        hits = shock[shock != 0.0]
        nonzero += len(hits)
        if len(hits):
            max_abs = max(max_abs, float(np.max(np.abs(hits))))
        m.step()
    expected = m.n * n_steps * REVISION_PROBA
    assert nonzero > 0
    # ordre de grandeur cohérent avec la probabilité tirée (tolérance large)
    assert 0.3 * expected < nonzero < 2.0 * expected
    # impact borné : nettement plus petit qu'un gap de surprise typique
    assert max_abs < 0.10


def test_revisions_never_hit_companies_reporting_this_step():
    m = Market(seed=15)
    m.fast_forward(3)
    idx = np.arange(m.n)
    due = set(idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)].tolist())
    shock = m._step_revisions()
    hit_idx = set(np.where(shock != 0.0)[0].tolist())
    assert hit_idx.isdisjoint(due)


def test_revisions_consume_rng_unconditionally_for_determinism():
    """Le tirage de révision doit être consommé À CHAQUE pas, même si aucune
    société n'est "due" -- sinon la séquence rng se désynchroniserait selon
    le chemin. On vérifie juste que deux marchés identiques restent
    synchronisés après plusieurs pas (déterminisme bout-à-bout)."""
    a = Market(seed=21); a.fast_forward(20)
    b = Market(seed=21); b.fast_forward(20)
    assert np.allclose(a.price, b.price)


# ------------------------------------------------------------------------ PEAD
def test_pead_decays_toward_zero_over_horizon():
    m = Market(seed=12)
    m.fast_forward(1)
    idx = np.arange(m.n)
    due = idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)]
    i = int(due[0])
    m.next_surprise[i] = 0.07
    m.next_guidance[i] = 0.0
    m._step_earnings()
    initial = abs(m.pead_state[i])
    assert initial > 0
    for _ in range(PEAD_HORIZON_STEPS):
        m._step_pead()
    remaining = abs(m.pead_state[i])
    assert remaining < initial * (PEAD_DECAY ** PEAD_HORIZON_STEPS) * 1.5
    assert remaining < initial * 0.15  # quasi-extinction après l'horizon


def test_pead_sign_matches_surprise_sign_on_average():
    """Sur de nombreuses sociétés/cycles, le drift résiduel PEAD juste après
    publication doit être du même signe que la surprise qui l'a généré."""
    m = Market(seed=33)
    matches = 0
    total = 0
    for _ in range(EARN_PERIOD * 4):
        m.step()
        for rep in m.last_earnings:
            i = m.ticker_idx[rep["ticker"]]
            if abs(rep["surprise"]) > 1e-9:
                total += 1
                if np.sign(m.pead_state[i]) == np.sign(rep["surprise"]):
                    matches += 1
    assert total > 50
    assert matches == total  # PEAD_K * surprise -> signe garanti identique


def test_pead_shock_decreases_each_step_in_magnitude():
    m = Market(seed=12)
    m.fast_forward(1)
    idx = np.arange(m.n)
    due = idx[(idx % EARN_PERIOD) == (m.step_count % EARN_PERIOD)]
    i = int(due[0])
    m.next_surprise[i] = 0.07
    m.next_guidance[i] = 0.0
    m._step_earnings()
    prev = abs(m.pead_state[i])
    for _ in range(5):
        m._step_pead()
        cur = abs(m.pead_state[i])
        assert cur <= prev + 1e-12
        prev = cur
