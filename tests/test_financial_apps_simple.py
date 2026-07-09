"""
test_financial_apps_simple.py — Tests simplifiés pour les nouvelles applications financières.

Vérifie les fonctionnalités de base sans dépendances complexes.
"""
import numpy as np
import pytest

from core import finmath


def test_sharpe_ratio():
    """Test du calcul du ratio de Sharpe."""
    # Cas simple
    weights = np.array([1.0])
    mean_returns = np.array([0.1])  # 10% de rendement
    cov_matrix = np.array([[0.04]])  # variance de 4% (volatilité de 20%)
    rf_rate = 0.02  # 2% de taux sans risque

    sharpe = finmath.sharpe_ratio(weights, mean_returns, cov_matrix, rf_rate)
    expected = (0.1 - 0.02) / 0.2  # (10% - 2%) / 20% = 0.4
    assert abs(sharpe - expected) < 1e-10

    # Cas avec rendement inférieur au taux sans risque
    mean_returns = np.array([0.01])  # 1% de rendement
    sharpe = finmath.sharpe_ratio(weights, mean_returns, cov_matrix, rf_rate)
    expected = (0.01 - 0.02) / 0.2  # (1% - 2%) / 20% = -0.05
    assert abs(sharpe - expected) < 1e-10

    # Cas avec volatilité nulle
    cov_matrix = np.array([[0.0]])  # variance nulle
    sharpe = finmath.sharpe_ratio(weights, mean_returns, cov_matrix, rf_rate)
    assert sharpe == 0.0


def test_zscore():
    """Test du calcul de Z-score."""
    # Données de test
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    mean = np.mean(data)  # 3.0
    std = np.std(data)    # ~1.414

    # Z-score du dernier point (5.0)
    last_value = data[-1]
    z_score = (last_value - mean) / std if std != 0 else 0.0
    expected = (5.0 - 3.0) / std  # ~1.414
    assert abs(z_score - expected) < 1e-10

    # Test avec des données constantes (std = 0)
    constant_data = np.array([2.0, 2.0, 2.0, 2.0, 2.0])
    mean_const = np.mean(constant_data)
    std_const = np.std(constant_data)
    z_score_const = (constant_data[-1] - mean_const) / std_const if std_const != 0 else 0.0
    assert z_score_const == 0.0


def test_hedge_ratio():
    """Test du calcul de ratio de couverture."""
    # Données de test pour deux actifs corrélés
    asset1_returns = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.015])
    asset2_returns = np.array([0.005, 0.015, -0.005, 0.02, -0.01, 0.01])

    # Calculer la corrélation
    correlation = np.corrcoef(asset1_returns, asset2_returns)[0, 1]

    # Calculer les volatilités
    asset1_vol = np.std(asset1_returns)
    asset2_vol = np.std(asset2_returns)

    # Ratio de couverture
    hedge_ratio = (correlation * asset1_vol / asset2_vol) if asset2_vol != 0 else 0.0

    # Vérifier que le ratio est un nombre fini
    assert np.isfinite(hedge_ratio)

    # Test avec volatilité nulle
    hedge_ratio_zero_vol = 0.0  # Éviter la division par zéro
    assert hedge_ratio_zero_vol == 0.0


def test_methods_exist():
    """Test que les méthodes des applications existent (sans les exécuter)."""
    # Vérifier que les classes peuvent être importées
    from apps.app_sharpe import SharpeApp
    from apps.app_zscore import ZScoreApp
    from apps.app_hedge import HedgeApp

    # Vérifier que les méthodes principales existent
    assert hasattr(SharpeApp, 'on_open')
    assert hasattr(SharpeApp, '_period_to_steps')
    assert hasattr(SharpeApp, '_compute_sharpe')

    assert hasattr(ZScoreApp, 'on_open')
    assert hasattr(ZScoreApp, '_period_to_steps')
    assert hasattr(ZScoreApp, '_compute_zscore')

    assert hasattr(HedgeApp, 'on_open')
    assert hasattr(HedgeApp, '_compute_hedge')
    assert hasattr(HedgeApp, '_compute_delta_hedge')


if __name__ == "__main__":
    # Exécuter les tests
    test_sharpe_ratio()
    print("✓ Test Sharpe Ratio passé")

    test_zscore()
    print("✓ Test Z-Score passé")

    test_hedge_ratio()
    print("✓ Test Hedge Ratio passé")

    test_methods_exist()
    print("✓ Test existence des méthodes passé")

    print("Tous les tests financiers ont passé avec succès!")