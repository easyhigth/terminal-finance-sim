"""Tests des modèles de pricing d'options (core/option_pricing.py) — les
propriétés de COURS sont vérifiées numériquement : convergence binomial→BS,
prime d'exercice anticipé du put américain (nulle pour le call sans
dividende), Monte-Carlo dans son intervalle d'erreur, prime de saut de
Merton sur les ailes, inversion de la vol implicite."""
import math

import pytest

from core import finmath as fm
from core import option_pricing as OP

S, K, T, R, SIG = 100.0, 100.0, 0.5, 0.03, 0.25


def test_binomial_converges_to_black_scholes():
    bs = OP.bs_price(S, K, T, R, SIG, "call")
    tree = OP.binomial_price(S, K, T, R, SIG, "call", steps=400)
    assert tree == pytest.approx(bs, rel=2e-3)


def test_american_call_no_dividend_equals_european():
    """Résultat classique : sans dividende, on n'exerce JAMAIS un call
    américain avant l'échéance — sa valeur égale l'européen."""
    eu = OP.binomial_price(S, K, T, R, SIG, "call", american=False)
    us = OP.binomial_price(S, K, T, R, SIG, "call", american=True)
    assert us == pytest.approx(eu, rel=1e-9)


def test_american_put_carries_early_exercise_premium():
    eu = OP.binomial_price(S, K, T, R, SIG, "put", american=False)
    us = OP.binomial_price(S, K, T, R, SIG, "put", american=True)
    assert us > eu                                  # prime d'exercice anticipé
    # ...et un put américain très ITM vaut au moins son intrinsèque
    deep = OP.binomial_price(40.0, K, T, R, SIG, "put", american=True)
    assert deep >= (K - 40.0) - 1e-9


def test_monte_carlo_within_stderr_of_bs():
    bs = OP.bs_price(S, K, T, R, SIG, "call")
    mc = OP.monte_carlo_price(S, K, T, R, SIG, "call")
    assert abs(mc["price"] - bs) < 4 * mc["stderr"]
    assert mc["stderr"] > 0
    # déterministe : deux appels identiques → même prix (graine fixe)
    assert OP.monte_carlo_price(S, K, T, R, SIG, "call")["price"] == mc["price"]


def test_merton_jumps_add_premium_on_wings():
    """Avec des sauts NÉGATIFS (crises), un put OTM vaut nettement plus que
    sous BS — c'est le smile ; sans sauts (λ=0), Merton == BS."""
    otm_put_bs = OP.bs_price(S, 85.0, T, R, SIG, "put")
    otm_put_jump = OP.merton_jump_price(S, 85.0, T, R, SIG, "put")
    assert otm_put_jump > otm_put_bs
    no_jump = OP.merton_jump_price(S, K, T, R, SIG, "call", lam=0.0)
    assert no_jump == pytest.approx(OP.bs_price(S, K, T, R, SIG, "call"), rel=1e-9)


def test_implied_vol_inverts_black_scholes():
    price = OP.bs_price(S, K, T, R, 0.32, "call")
    iv = OP.implied_vol(price, S, K, T, R, "call")
    assert iv == pytest.approx(0.32, abs=1e-4)
    assert OP.implied_vol(-1.0, S, K, T, R, "call") is None


def test_compare_models_rows_ordered_and_consistent():
    cmp = OP.compare_models(S, K, T, R, SIG, "call")
    ids = [r["id"] for r in cmp["rows"]]
    assert ids == ["bs", "binom_eu", "binom_us", "mc", "jump"]
    prices = {r["id"]: r["price"] for r in cmp["rows"]}
    assert prices["binom_us"] >= prices["binom_eu"] - 1e-9
    assert cmp["early_exercise"] >= 0.0
    assert prices["jump"] > 0
    # put à sauts : vol implicite du prix Merton > vol d'entrée (smile)
    cmp_put = OP.compare_models(S, 90.0, T, R, SIG, "put")
    assert cmp_put["iv_jump"] is not None and cmp_put["iv_jump"] > SIG


def test_expired_options_return_intrinsic():
    assert OP.binomial_price(110.0, 100.0, 0.0, R, SIG, "call") == 10.0
    assert OP.monte_carlo_price(90.0, 100.0, 0.0, R, SIG, "put")["price"] == 10.0
    assert OP.merton_jump_price(90.0, 100.0, 0.0, R, SIG, "call") == 0.0


def test_put_call_parity_holds_for_bs():
    call = OP.bs_price(S, K, T, R, SIG, "call")
    put = OP.bs_price(S, K, T, R, SIG, "put")
    assert call - put == pytest.approx(S - K * math.exp(-R * T), abs=1e-6)
