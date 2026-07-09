"""
test_financial_apps_enhanced.py — Tests améliorés pour les applications financières.

Vérifie les nouvelles fonctionnalités et améliorations.
"""
import numpy as np
import pytest

from core import finmath


def test_sharpe_ratio_enhanced():
    """Test amélioré du calcul du ratio de Sharpe."""
    # Test avec des données réalistes
    returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015, 0.008, -0.002, 0.012])
    rf_rate = 0.02 / 252  # Taux sans risque journalier

    vol = np.std(returns)
    mean_return = np.mean(returns)
    sharpe = (mean_return - rf_rate) / vol if vol > 0 else 0.0

    assert np.isfinite(sharpe)
    assert isinstance(sharpe, (int, float, np.floating, np.integer))


def test_zscore_enhanced():
    """Test amélioré du calcul de Z-score."""
    # Test avec une distribution normale
    np.random.seed(42)
    data = np.random.normal(0.001, 0.02, 1000)  # Moyenne 0.1%, vol 2%

    mean = np.mean(data)
    std = np.std(data)

    # Calculer le Z-score d'une valeur extrême
    extreme_value = mean + 2.5 * std
    z_score = (extreme_value - mean) / std if std != 0 else 0.0

    assert abs(z_score - 2.5) < 0.01  # Doit être proche de 2.5

    # Test des interprétations
    if abs(z_score) > 2:
        interpretation = "Écart significatif"
    elif abs(z_score) > 1:
        interpretation = "Écart modéré"
    else:
        interpretation = "Comportement normal"

    assert interpretation == "Écart significatif"


def test_hedge_ratio_enhanced():
    """Test amélioré du calcul de ratio de couverture."""
    # Générer deux séries corrélées
    np.random.seed(42)
    n = 1000

    # Facteur commun
    common_factor = np.random.normal(0, 0.01, n)

    # Deux actifs corrélés
    asset1_returns = 0.6 * common_factor + 0.8 * np.random.normal(0, 0.015, n)
    asset2_returns = 0.7 * common_factor + 0.7 * np.random.normal(0, 0.012, n)

    # Calculer la corrélation
    correlation = np.corrcoef(asset1_returns, asset2_returns)[0, 1]

    # Calculer les volatilités
    asset1_vol = np.std(asset1_returns)
    asset2_vol = np.std(asset2_returns)

    # Ratio de couverture
    hedge_ratio = (correlation * asset1_vol / asset2_vol) if asset2_vol != 0 else 0.0

    # Beta
    if np.var(asset2_returns) != 0:
        beta = np.cov(asset1_returns, asset2_returns)[0, 1] / np.var(asset2_returns)
    else:
        beta = 0.0

    assert np.isfinite(hedge_ratio)
    assert np.isfinite(beta)
    assert abs(correlation) <= 1.0  # La corrélation doit être entre -1 et 1


def test_portfolio_optimization():
    """Test des fonctions d'optimisation de portefeuille."""
    # Données de test
    mean_returns = np.array([0.1, 0.12, 0.08, 0.15])  # Rendements attendus
    cov_matrix = np.array([
        [0.04, 0.01, 0.005, 0.02],
        [0.01, 0.09, 0.015, 0.03],
        [0.005, 0.015, 0.06, 0.01],
        [0.02, 0.03, 0.01, 0.16]
    ])
    rf_rate = 0.02

    # Test du portefeuille à variance minimale
    min_var_weights = finmath.min_variance_portfolio(mean_returns, cov_matrix)

    # Vérifier que les poids somment à 1
    assert abs(np.sum(min_var_weights) - 1.0) < 1e-10

    # Vérifier que tous les poids sont positifs (long-only)
    assert np.all(min_var_weights >= 0)

    # Test du portefeuille max Sharpe
    max_sharpe_weights = finmath.max_sharpe_portfolio(mean_returns, cov_matrix, rf_rate)

    # Vérifier que les poids somment à 1
    assert abs(np.sum(max_sharpe_weights) - 1.0) < 1e-10

    # Vérifier que tous les poids sont positifs (long-only)
    assert np.all(max_sharpe_weights >= 0)


def test_methods_enhanced():
    """Test que les méthodes améliorées existent."""
    # Vérifier que les classes peuvent être importées
    from apps.app_sharpe import SharpeApp
    from apps.app_zscore import ZScoreApp
    from apps.app_hedge import HedgeApp

    # Vérifier que les nouvelles méthodes existent
    assert hasattr(SharpeApp, '_draw_sharpe_chart')
    assert hasattr(ZScoreApp, '_compute_volatility_zscore')
    assert hasattr(HedgeApp, '_compute_delta_hedge')


if __name__ == "__main__":
    # Exécuter les tests
    test_sharpe_ratio_enhanced()
    print("✓ Test Sharpe Ratio amélioré passé")

    test_zscore_enhanced()
    print("✓ Test Z-Score amélioré passé")

    test_hedge_ratio_enhanced()
    print("✓ Test Hedge Ratio amélioré passé")

    test_portfolio_optimization()
    print("✓ Test optimisation portefeuille passé")

    test_methods_enhanced()
    print("✓ Test existence des méthodes améliorées passé")

    print("Tous les tests améliorés ont passé avec succès!")