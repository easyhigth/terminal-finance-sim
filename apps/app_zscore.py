"""
app_zscore.py — Application « Z-Score » du bureau.

Calcule et visualise les Z-scores pour différentes analyses :
- Z-score des rendements d'un actif (par rapport à sa moyenne historique)
- Z-score de performance relative (actif vs benchmark)
- Z-score de volatilité
- Z-score de corrélation entre actifs

Permet d'identifier les écarts significatifs par rapport aux comportements historiques.
"""
import pygame
import numpy as np

from apps.base import DesktopApp
from core import config
from ui import fonts, widgets


class ZScoreApp(DesktopApp):
    title = "Z-Score — Analyse statistique"
    icon_kind = "graph"
    default_size = (800, 600)
    min_size = (600, 400)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.ticker = ""  # ticker à analyser
        self.period = "1Y"  # période d'analyse
        self.analysis_type = "returns"  # type d'analyse : returns, volatility, correlation
        self.msg = ""
        self._ticker_rect = None
        self._period_rects = {}
        self._analysis_rects = {}
        self._compute_btn = None
        self._results = None
        self._ticker_input_active = False

    def _compute_zscore(self):
        """Calcule les Z-scores selon le type d'analyse choisi."""
        try:
            if not self.ticker:
                self.msg = "Veuillez entrer un ticker"
                return

            # Vérifier que le ticker existe
            if self.ticker not in self.market.ticker_idx:
                self.msg = f"Ticker {self.ticker} introuvable"
                return

            hist_length = self._period_to_steps()
            if hist_length is None:
                self.msg = "Période invalide"
                return

            # Récupérer l'historique
            hist = self.market.history_of(self.ticker, hist_length)
            if not hist or len(hist) < 30:  # Minimum 30 points pour une analyse statistique
                self.msg = "Données insuffisantes pour le calcul"
                return

            if self.analysis_type == "returns":
                self._compute_returns_zscore(hist)
            elif self.analysis_type == "volatility":
                self._compute_volatility_zscore(hist)
            elif self.analysis_type == "correlation":
                self._compute_correlation_zscore(hist)

        except Exception as e:
            self.msg = f"Erreur de calcul : {str(e)}"

    def _compute_returns_zscore(self, hist):
        """Calcule le Z-score des rendements."""
        # Calculer les rendements
        returns = [(hist[i] / hist[i-1] - 1) for i in range(1, len(hist))]

        if len(returns) < 2:
            self.msg = "Données insuffisantes"
            return

        # Calculer moyenne et écart-type
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            self.msg = "Volatilité nulle - Z-score indéfini"
            return

        # Z-score du dernier rendement
        last_return = returns[-1] if returns else 0.0
        z_score = (last_return - mean_return) / std_return if std_return != 0 else 0.0

        # Interprétation
        if abs(z_score) > 2:
            interpretation = "Écart significatif (> 2σ)"
            status = "alert"
        elif abs(z_score) > 1:
            interpretation = "Écart modéré (> 1σ)"
            status = "warning"
        else:
            interpretation = "Comportement normal"
            status = "normal"

        self._results = {
            "type": "Rendements",
            "z_score": z_score,
            "mean": mean_return,
            "std": std_return,
            "last_value": last_return,
            "interpretation": interpretation,
            "status": status
        }
        self.msg = f"Z-score calculé : {z_score:.2f}"

    def _compute_volatility_zscore(self, hist):
        """Calcule le Z-score de volatilité."""
        # Calculer les rendements
        returns = [(hist[i] / hist[i-1] - 1) for i in range(1, len(hist))]

        if len(returns) < 30:
            self.msg = "Données insuffisantes"
            return

        # Calculer la volatilité sur des fenêtres glissantes (30 jours)
        window_size = min(30, len(returns))
        volatilities = []

        for i in range(len(returns) - window_size + 1):
            window = returns[i:i + window_size]
            vol = np.std(window)
            volatilities.append(vol)

        if len(volatilities) < 2:
            self.msg = "Données insuffisantes pour la volatilité"
            return

        # Calculer moyenne et écart-type des volatilités
        mean_vol = np.mean(volatilities)
        std_vol = np.std(volatilities)

        if std_vol == 0:
            self.msg = "Volatilité de volatilité nulle"
            return

        # Z-score de la dernière volatilité
        last_vol = volatilities[-1] if volatilities else 0.0
        z_score = (last_vol - mean_vol) / std_vol if std_vol != 0 else 0.0

        # Interprétation
        if abs(z_score) > 2:
            interpretation = "Volatilité anormalement élevée/basse"
            status = "alert"
        elif abs(z_score) > 1:
            interpretation = "Volatilité modérément élevée/basse"
            status = "warning"
        else:
            interpretation = "Volatilité normale"
            status = "normal"

        self._results = {
            "type": "Volatilité",
            "z_score": z_score,
            "mean": mean_vol,
            "std": std_vol,
            "last_value": last_vol,
            "interpretation": interpretation,
            "status": status
        }
        self.msg = f"Z-score de volatilité calculé : {z_score:.2f}"

    def _compute_correlation_zscore(self, hist):
        """Calcule le Z-score de corrélation avec l'indice de marché."""
        # Utiliser l'indice principal
        indices = self.market.index_tickers()
        if not indices:
            self.msg = "Aucun indice de marché disponible"
            return

        benchmark_ticker = indices[0]
        benchmark_hist = self.market.history_of(benchmark_ticker, len(hist))

        if not benchmark_hist or len(benchmark_hist) != len(hist):
            self.msg = "Données de benchmark incomplètes"
            return

        # Calculer les rendements
        asset_returns = [(hist[i] / hist[i-1] - 1) for i in range(1, len(hist))]
        bench_returns = [(benchmark_hist[i] / benchmark_hist[i-1] - 1) for i in range(1, len(benchmark_hist))]

        if len(asset_returns) != len(bench_returns) or len(asset_returns) < 30:
            self.msg = "Données incomplètes pour corrélation"
            return

        # Calculer la corrélation sur des fenêtres glissantes
        window_size = min(30, len(asset_returns))
        correlations = []

        for i in range(len(asset_returns) - window_size + 1):
            asset_window = asset_returns[i:i + window_size]
            bench_window = bench_returns[i:i + window_size]
            if len(asset_window) > 1 and len(bench_window) > 1:
                corr = np.corrcoef(asset_window, bench_window)[0, 1]
                correlations.append(corr if not np.isnan(corr) else 0.0)

        if len(correlations) < 2:
            self.msg = "Données insuffisantes pour corrélation"
            return

        # Calculer moyenne et écart-type des corrélations
        mean_corr = np.mean(correlations)
        std_corr = np.std(correlations)

        if std_corr == 0:
            self.msg = "Corrélation stable - Z-score indéfini"
            return

        # Z-score de la dernière corrélation
        last_corr = correlations[-1] if correlations else 0.0
        z_score = (last_corr - mean_corr) / std_corr if std_corr != 0 else 0.0

        # Interprétation
        if abs(z_score) > 2:
            interpretation = "Changement significatif de corrélation"
            status = "alert"
        elif abs(z_score) > 1:
            interpretation = "Changement modéré de corrélation"
            status = "warning"
        else:
            interpretation = "Corrélation stable"
            status = "normal"

        self._results = {
            "type": "Corrélation",
            "z_score": z_score,
            "mean": mean_corr,
            "std": std_corr,
            "last_value": last_corr,
            "interpretation": interpretation,
            "status": status,
            "benchmark": benchmark_ticker
        }
        self.msg = f"Z-score de corrélation calculé : {z_score:.2f}"

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

    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Zone de saisie du ticker
            if self._ticker_rect and self._ticker_rect.collidepoint(pos):
                self._ticker_input_active = True
                return True
            elif self._ticker_input_active:
                self._ticker_input_active = False

            # Sélection de période
            for period, rect_btn in self._period_rects.items():
                if rect_btn and rect_btn.collidepoint(pos):
                    self.period = period
                    return True

            # Sélection du type d'analyse
            for analysis_type, rect_btn in self._analysis_rects.items():
                if rect_btn and rect_btn.collidepoint(pos):
                    self.analysis_type = analysis_type
                    return True

            # Bouton calculer
            if self._compute_btn and self._compute_btn.collidepoint(pos):
                self._compute_zscore()
                return True

        elif event.type == pygame.KEYDOWN and self._ticker_input_active:
            if event.key == pygame.K_BACKSPACE:
                self.ticker = self.ticker[:-1]
            elif event.key == pygame.K_RETURN:
                self._ticker_input_active = False
                self._compute_zscore()
            elif event.unicode.isalnum() or event.unicode in ".-":
                # Limiter la longueur du ticker
                if len(self.ticker) < 10:
                    self.ticker += event.unicode.upper()
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

        # Saisie du ticker
        y = rect.y + 90
        widgets.draw_text(surf, "Ticker à analyser :", (rect.x + 20, y), fonts.small(bold=True), config.COL_TEXT)
        self._ticker_rect = pygame.Rect(rect.x + 180, y-5, 100, 30)
        pygame.draw.rect(surf, config.COL_WHITE if self._ticker_input_active else config.COL_PANEL,
                        self._ticker_rect, border_radius=4)
        widgets.draw_text(surf, self.ticker, (rect.x + 185, y+2), fonts.small(), config.COL_TEXT)

        # Contrôles
        y += 50
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

        # Types d'analyse
        y += 40
        widgets.draw_text(surf, "Type d'analyse :", (rect.x + 20, y), fonts.small(bold=True), config.COL_TEXT)

        x = rect.x + 160
        analysis_types = [("returns", "Rendements"), ("volatility", "Volatilité"), ("correlation", "Corrélation")]
        self._analysis_rects = {}
        for analysis_type, label in analysis_types:
            rect_btn = pygame.Rect(x, y, 100, 24)
            self._analysis_rects[analysis_type] = rect_btn
            color = config.COL_PRESTIGE if self.analysis_type == analysis_type else config.COL_PANEL
            pygame.draw.rect(surf, color, rect_btn, border_radius=4)
            widgets.draw_text(surf, label, rect_btn.center, fonts.small(), config.COL_TEXT, align="center")
            x += 110

        # Bouton calculer
        y += 50
        self._compute_btn = pygame.Rect(rect.x + 20, y, 120, 30)
        pygame.draw.rect(surf, config.COL_AMBER, self._compute_btn, border_radius=4)
        widgets.draw_text(surf, "Calculer", self._compute_btn.center,
                         fonts.small(bold=True), config.COL_BG, align="center")

        # Résultats
        if self._results:
            y += 60
            widgets.draw_text(surf, f"Analyse : {self._results['type']}", (rect.x + 20, y),
                             fonts.small(bold=True), config.COL_TEXT)

            y += 30
            # Afficher le Z-score avec coloration selon la signification
            z_score = self._results['z_score']
            if self._results['status'] == "alert":
                color = config.COL_DOWN if z_score < 0 else config.COL_UP
            elif self._results['status'] == "warning":
                color = config.COL_AMBER
            else:
                color = config.COL_TEXT

            widgets.draw_text(surf, f"Z-score : {z_score:.3f}", (rect.x + 40, y),
                             fonts.ui_title(), color)

            y += 35
            widgets.draw_text(surf, f"Moyenne : {self._results['mean']:.4f}", (rect.x + 40, y),
                             fonts.small(), config.COL_TEXT)
            y += 25
            widgets.draw_text(surf, f"Écart-type : {self._results['std']:.4f}", (rect.x + 40, y),
                             fonts.small(), config.COL_TEXT)
            y += 25
            widgets.draw_text(surf, f"Dernière valeur : {self._results['last_value']:.4f}", (rect.x + 40, y),
                             fonts.small(), config.COL_TEXT)

            y += 30
            widgets.draw_text(surf, f"Interprétation : {self._results['interpretation']}", (rect.x + 20, y),
                             fonts.small(bold=True), color)

            # Information supplémentaire pour la corrélation
            if self.analysis_type == "correlation" and "benchmark" in self._results:
                y += 25
                widgets.draw_text(surf, f"Benchmark : {self._results['benchmark']}", (rect.x + 40, y),
                                 fonts.small(), config.COL_TEXT_DIM)