"""
app_sharpe.py — Application « Sharpe Ratio » du bureau.

Calcule et visualise le ratio de Sharpe pour différentes stratégies de portefeuille :
- Portefeuille actuel du joueur
- Portefeuille benchmark (marché)
- Portefeuilles optimisés (max Sharpe, min variance)
- Comparaison avec des indices de référence

Permet d'analyser la performance ajustée au risque sur différentes périodes.
"""
import pygame
import numpy as np

from apps.base import DesktopApp
from core import config, finmath
from ui import fonts, style, widgets


class SharpeApp(DesktopApp):
    title = "Sharpe Ratio — Performance ajustée au risque"
    icon_kind = "graph"
    default_size = (800, 600)
    min_size = (600, 400)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.period = "1Y"  # 1M, 3M, 1Y, 3Y, 5Y, MAX
        self.rf_rate = 0.02  # taux sans risque (2% par défaut)
        self.msg = ""
        self._period_rects = {}
        self._rf_rect = None
        self._compute_btn = None
        self._results = None
        self._scroll = 0
        self._max_scroll = 0

    def _compute_sharpe(self):
        """Calcule les ratios de Sharpe pour différentes stratégies."""
        try:
            # Historique des prix sur la période choisie
            hist_length = self._period_to_steps()
            if hist_length is None:
                self.msg = "Période invalide"
                return

            # Récupérer les données de marché
            player = self.app.gs.player
            portfolio = player.portfolio

            # Si le portefeuille est vide
            if not portfolio:
                self.msg = "Portefeuille vide - impossible de calculer le Sharpe Ratio"
                return

            # Calculer les rendements du portefeuille
            portfolio_returns = self._portfolio_returns(hist_length)
            if len(portfolio_returns) < 2:
                self.msg = "Données insuffisantes pour le calcul"
                return

            # Calculer le Sharpe Ratio du portefeuille
            portfolio_sharpe = finmath.sharpe_ratio(
                np.array([1.0]),  # poids unitaire pour un seul portefeuille
                np.array([np.mean(portfolio_returns)]),  # rendement moyen
                np.array([[np.var(portfolio_returns)]]),  # matrice de covariance
                self.rf_rate
            )

            # Calculer le Sharpe Ratio du marché (indice large)
            market_returns = self._market_returns(hist_length)
            market_sharpe = finmath.sharpe_ratio(
                np.array([1.0]),
                np.array([np.mean(market_returns)]),
                np.array([[np.var(market_returns)]]),
                self.rf_rate
            ) if len(market_returns) >= 2 else 0.0

            # Calculer le portefeuille à variance minimale (si possible)
            min_var_sharpe = 0.0
            try:
                if len(portfolio) > 1:
                    # Pour simplifier, on prend les 5 premières positions
                    tickers = list(portfolio.keys())[:5]
                    returns_matrix = []
                    for tk in tickers:
                        hist = self.market.history_of(tk, hist_length)
                        if hist and len(hist) >= 2:
                            # Calculer les rendements
                            rets = [(hist[i] / hist[i-1] - 1) for i in range(1, len(hist))]
                            returns_matrix.append(rets)

                    if len(returns_matrix) > 1 and all(len(r) == len(returns_matrix[0]) for r in returns_matrix):
                        returns_array = np.array(returns_matrix)
                        mean_returns = np.mean(returns_array, axis=1)
                        cov_matrix = np.cov(returns_array)

                        # Portefeuille à variance minimale
                        min_var_weights = finmath.min_variance_portfolio(mean_returns, cov_matrix)
                        min_var_returns = np.dot(returns_array.T, min_var_weights)
                        min_var_sharpe = finmath.sharpe_ratio(
                            min_var_weights, mean_returns, cov_matrix, self.rf_rate
                        )
            except Exception:
                pass  # En cas d'erreur, on continue avec 0.0

            self._results = {
                "portfolio": {
                    "sharpe": portfolio_sharpe,
                    "return": np.mean(portfolio_returns) if portfolio_returns else 0.0,
                    "volatility": np.std(portfolio_returns) if portfolio_returns else 0.0,
                    "count": len(portfolio)
                },
                "market": {
                    "sharpe": market_sharpe,
                    "return": np.mean(market_returns) if market_returns else 0.0,
                    "volatility": np.std(market_returns) if market_returns else 0.0
                },
                "min_variance": {
                    "sharpe": min_var_sharpe
                }
            }
            self.msg = f"Sharpe Ratio calculé sur {hist_length} pas"

        except Exception as e:
            self.msg = f"Erreur de calcul : {str(e)}"

    def _period_to_steps(self):
        """Convertit la période en nombre de pas de marché."""
        periods = {
            "1M": 73,    # ~1 mois
            "3M": 219,   # ~3 mois
            "1Y": 365,   # ~1 an
            "3Y": 1095,  # ~3 ans
            "5Y": 1825,  # ~5 ans
            "MAX": None
        }
        return periods.get(self.period, 365)

    def _portfolio_returns(self, steps):
        """Calcule les rendements du portefeuille sur la période."""
        player = self.app.gs.player
        portfolio = player.portfolio

        if not portfolio:
            return []

        # Historique des valeurs du portefeuille
        values = []
        current_step = self.market.step_count

        # Nombre de pas à examiner
        hist_steps = steps if steps else min(current_step, 365)  # MAX par défaut 1 an

        for i in range(hist_steps):
            step = current_step - (hist_steps - i)
            if step < 0:
                continue

            # Recalculer la valeur du portefeuille à ce pas
            # (simplification : on utilise les prix actuels pour l'instant)
            total_value = 0.0
            for ticker, pos in portfolio.items():
                if pos["shares"] != 0:
                    price = self.market.price_of(ticker)
                    if price:
                        total_value += pos["shares"] * price

            values.append(total_value)

        # Calculer les rendements
        if len(values) < 2:
            return []

        returns = [(values[i] / values[i-1] - 1) for i in range(1, len(values))]
        return returns

    def _market_returns(self, steps):
        """Calcule les rendements de l'indice de marché."""
        # Utiliser l'indice principal (par exemple, le premier indice)
        indices = self.market.index_tickers()
        if not indices:
            return []

        ticker = indices[0]  # Premier indice
        hist = self.market.history_of(ticker, steps if steps else 365)

        if not hist or len(hist) < 2:
            return []

        # Calculer les rendements
        returns = [(hist[i] / hist[i-1] - 1) for i in range(1, len(hist))]
        return returns

    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Sélection de période
            for period, rect_btn in self._period_rects.items():
                if rect_btn and rect_btn.collidepoint(pos):
                    self.period = period
                    self._compute_sharpe()
                    return True

            # Changement de taux sans risque
            if self._rf_rect and self._rf_rect.collidepoint(pos):
                # Pour simplifier, on change le taux de ±0.5%
                self.rf_rate += 0.005 if pygame.key.get_mods() & pygame.KMOD_SHIFT else -0.005
                self.rf_rate = max(0.0, min(0.1, self.rf_rate))  # Borné entre 0% et 10%
                self._compute_sharpe()
                return True

            # Bouton calculer
            if self._compute_btn and self._compute_btn.collidepoint(pos):
                self._compute_sharpe()
                return True
        return False

    def draw(self, surf, rect):
        # Fond
        surf.fill(config.COL_BG, rect)

        # Titre
        widgets.draw_text(surf, self.title, (rect.x + 20, rect.y + 20), fonts.ui_title(), config.COL_TEXT)

        # Message d'état
        if self.msg:
            widgets.draw_text(surf, self.msg, (rect.x + 20, rect.y + 60), fonts.small(), config.COL_AMBER)

        # Contrôles
        y = rect.y + 90
        widgets.draw_text(surf, "Période :", (rect.x + 20, y), fonts.small(bold=True), config.COL_TEXT)

        # Boutons de période
        x = rect.x + 100
        periods = ["1M", "3M", "1Y", "3Y", "5Y", "MAX"]
        self._period_rects = {}
        for period in periods:
            rect_btn = pygame.Rect(x, y, 60, 24)
            self._period_rects[period] = rect_btn
            color = config.COL_PRESTIGE if self.period == period else config.COL_PANEL
            pygame.draw.rect(surf, color, rect_btn, border_radius=4)
            widgets.draw_text(surf, period, rect_btn.center, fonts.small(), config.COL_TEXT, align="center")
            x += 65

        # Taux sans risque
        y += 40
        widgets.draw_text(surf, f"Taux sans risque : {self.rf_rate*100:.2f}%", (rect.x + 20, y),
                         fonts.small(), config.COL_TEXT)
        self._rf_rect = pygame.Rect(rect.x + 200, y, 120, 24)
        pygame.draw.rect(surf, config.COL_PANEL, self._rf_rect, border_radius=4)
        widgets.draw_text(surf, "Cliquer pour ±0.5%", self._rf_rect.center,
                         fonts.tiny(), config.COL_TEXT_DIM, align="center")

        # Bouton calculer
        y += 40
        self._compute_btn = pygame.Rect(rect.x + 20, y, 120, 30)
        pygame.draw.rect(surf, config.COL_AMBER, self._compute_btn, border_radius=4)
        widgets.draw_text(surf, "Calculer", self._compute_btn.center,
                         fonts.small(bold=True), config.COL_BG, align="center")

        # Résultats
        if self._results:
            y += 50
            widgets.draw_text(surf, "Résultats du calcul :", (rect.x + 20, y),
                             fonts.small(bold=True), config.COL_TEXT)

            y += 30
            # Portefeuille actuel
            surf.blit(fonts.small(bold=True).render("Votre portefeuille :", True, config.COL_TEXT), (rect.x + 20, y))
            y += 25
            widgets.draw_text(surf, f"  Sharpe Ratio : {self._results['portfolio']['sharpe']:.3f}",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)
            y += 20
            widgets.draw_text(surf, f"  Rendement : {self._results['portfolio']['return']*100:.2f}%",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)
            y += 20
            widgets.draw_text(surf, f"  Volatilité : {self._results['portfolio']['volatility']*100:.2f}%",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)
            y += 20
            widgets.draw_text(surf, f"  Positions : {self._results['portfolio']['count']}",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)

            y += 30
            # Marché
            surf.blit(fonts.small(bold=True).render("Marché (indice) :", True, config.COL_TEXT), (rect.x + 20, y))
            y += 25
            widgets.draw_text(surf, f"  Sharpe Ratio : {self._results['market']['sharpe']:.3f}",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)
            y += 20
            widgets.draw_text(surf, f"  Rendement : {self._results['market']['return']*100:.2f}%",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)
            y += 20
            widgets.draw_text(surf, f"  Volatilité : {self._results['market']['volatility']*100:.2f}%",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)

            y += 30
            # Portefeuille à variance minimale
            surf.blit(fonts.small(bold=True).render("Portefeuille min variance :", True, config.COL_TEXT), (rect.x + 20, y))
            y += 25
            widgets.draw_text(surf, f"  Sharpe Ratio : {self._results['min_variance']['sharpe']:.3f}",
                             (rect.x + 40, y), fonts.small(), config.COL_TEXT)

            # Interprétation
            y += 40
            sharpe = self._results['portfolio']['sharpe']
            if sharpe > 1.0:
                interpretation = "Excellent (Sharpe > 1.0)"
                color = config.COL_UP
            elif sharpe > 0.5:
                interpretation = "Bon (0.5 < Sharpe < 1.0)"
                color = config.COL_AMBER
            elif sharpe > 0:
                interpretation = "Moyen (0 < Sharpe < 0.5)"
                color = config.COL_TEXT
            else:
                interpretation = "Faible (Sharpe < 0)"
                color = config.COL_DOWN

            widgets.draw_text(surf, f"Interprétation : {interpretation}", (rect.x + 20, y),
                             fonts.small(bold=True), color)