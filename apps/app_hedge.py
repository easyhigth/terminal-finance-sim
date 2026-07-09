"""
app_hedge.py — Application « Couverture (Hedge) » du bureau.

Permet de mettre en place des stratégies de couverture pour protéger un portefeuille :
- Couverture delta (options)
- Couverture beta (indices)
- Couverture statistique (pairs trading)
- Calcul des ratios de couverture optimaux

Intègre les coûts de transaction et l'impact de marché.
"""
import pygame
import numpy as np

from apps.base import DesktopApp
from core import config, finmath, portfolio as PF
from ui import fonts, widgets


class HedgeApp(DesktopApp):
    title = "Couverture — Protection de portefeuille"
    icon_kind = "shield"
    default_size = (850, 650)
    min_size = (700, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.player = self.app.gs.player
        self.mode = "delta"  # delta, beta, statistical
        self.ticker = ""  # actif à couvrir
        self.hedge_ticker = ""  # actif de couverture
        self.amount = ""  # montant à couvrir
        self.msg = ""
        self._mode_rects = {}
        self._ticker_rect = None
        self._hedge_ticker_rect = None
        self._amount_rect = None
        self._compute_btn = None
        self._execute_btn = None
        self._results = None
        self._ticker_input_active = False
        self._hedge_ticker_input_active = False
        self._amount_input_active = False
        self._selected_position = None

    def _compute_hedge(self):
        """Calcule la stratégie de couverture optimale."""
        try:
            if not self.ticker:
                self.msg = "Veuillez sélectionner un actif à couvrir"
                return

            if self.mode == "delta":
                self._compute_delta_hedge()
            elif self.mode == "beta":
                self._compute_beta_hedge()
            elif self.mode == "statistical":
                self._compute_statistical_hedge()

        except Exception as e:
            self.msg = f"Erreur de calcul : {str(e)}"

    def _compute_delta_hedge(self):
        """Calcul de couverture delta avec des options."""
        # Pour simplifier, on utilise une approximation basée sur la corrélation
        # Dans un vrai système, on utiliserait les Greeks des options

        if not self.hedge_ticker:
            self.msg = "Veuillez sélectionner un actif de couverture"
            return

        # Historique des deux actifs
        hist_length = 252  # ~1 an
        asset_hist = self.market.history_of(self.ticker, hist_length)
        hedge_hist = self.market.history_of(self.hedge_ticker, hist_length)

        if not asset_hist or not hedge_hist or len(asset_hist) < 30 or len(hedge_hist) < 30:
            self.msg = "Données historiques insuffisantes"
            return

        # Calculer les rendements
        asset_returns = [(asset_hist[i] / asset_hist[i-1] - 1) for i in range(1, len(asset_hist))]
        hedge_returns = [(hedge_hist[i] / hedge_hist[i-1] - 1) for i in range(1, len(hedge_hist))]

        # S'assurer que les séries ont la même longueur
        min_len = min(len(asset_returns), len(hedge_returns))
        if min_len < 30:
            self.msg = "Données insuffisantes pour le calcul"
            return

        asset_returns = asset_returns[-min_len:]
        hedge_returns = hedge_returns[-min_len:]

        # Calculer la corrélation
        correlation = np.corrcoef(asset_returns, hedge_returns)[0, 1] if len(asset_returns) > 1 else 0.0
        correlation = correlation if not np.isnan(correlation) else 0.0

        # Calculer les volatilités
        asset_vol = np.std(asset_returns)
        hedge_vol = np.std(hedge_returns)

        # Ratio de couverture (hedge ratio)
        hedge_ratio = (correlation * asset_vol / hedge_vol) if hedge_vol != 0 else 0.0

        # Calculer le beta (alternative au hedge ratio)
        if np.var(hedge_returns) != 0:
            beta = np.cov(asset_returns, hedge_returns)[0, 1] / np.var(hedge_returns)
            beta = beta if not np.isnan(beta) else 0.0
        else:
            beta = 0.0

        # Montant à couvrir
        try:
            amount_to_hedge = float(self.amount) if self.amount else 0.0
        except ValueError:
            amount_to_hedge = 0.0

        # Position actuelle dans l'actif à couvrir
        portfolio = self.player.portfolio
        position = portfolio.get(self.ticker, {"shares": 0.0})
        current_shares = position["shares"]
        current_value = current_shares * self.market.price_of(self.ticker) if self.market.price_of(self.ticker) else 0.0

        # Calculer le nombre de titres de couverture nécessaires
        hedge_price = self.market.price_of(self.hedge_ticker)
        hedge_shares = -(hedge_ratio * amount_to_hedge / hedge_price) if hedge_price and hedge_price > 0 else 0.0

        # Coût estimé de la couverture
        commission = 0.001  # 10 bps
        hedge_cost = abs(hedge_shares * hedge_price * commission) if hedge_price else 0.0

        # Efficacité de la couverture
        if abs(correlation) > 0.8:
            effectiveness = "Élevée"
        elif abs(correlation) > 0.5:
            effectiveness = "Moyenne"
        else:
            effectiveness = "Faible"

        self._results = {
            "type": "Couverture Delta",
            "correlation": correlation,
            "beta": beta,
            "hedge_ratio": hedge_ratio,
            "current_position": current_shares,
            "current_value": current_value,
            "hedge_shares": hedge_shares,
            "hedge_value": abs(hedge_shares * hedge_price) if hedge_price else 0.0,
            "hedge_cost": hedge_cost,
            "effectiveness": effectiveness,
            "explanation": f"Pour chaque € de {self.ticker}, couvrir avec {abs(hedge_ratio):.2f}€ de {self.hedge_ticker}"
        }
        self.msg = f"Couverture delta calculée (corrélation: {correlation:.2f}, efficacité: {effectiveness})"

    def _compute_beta_hedge(self):
        """Calcul de couverture beta avec un indice."""
        # Utiliser l'indice principal comme benchmark
        indices = self.market.index_tickers()
        if not indices:
            self.msg = "Aucun indice disponible pour la couverture"
            return

        self.hedge_ticker = indices[0]  # Premier indice

        # Historique
        hist_length = 252  # ~1 an
        asset_hist = self.market.history_of(self.ticker, hist_length)
        index_hist = self.market.history_of(self.hedge_ticker, hist_length)

        if not asset_hist or not index_hist or len(asset_hist) < 30 or len(index_hist) < 30:
            self.msg = "Données historiques insuffisantes"
            return

        # Calculer les rendements
        asset_returns = [(asset_hist[i] / asset_hist[i-1] - 1) for i in range(1, len(asset_hist))]
        index_returns = [(index_hist[i] / index_hist[i-1] - 1) for i in range(1, len(index_hist))]

        # S'assurer que les séries ont la même longueur
        min_len = min(len(asset_returns), len(index_returns))
        if min_len < 30:
            self.msg = "Données insuffisantes pour le calcul"
            return

        asset_returns = asset_returns[-min_len:]
        index_returns = index_returns[-min_len:]

        # Calculer le beta
        if np.var(index_returns) == 0:
            beta = 0.0
        else:
            beta = np.cov(asset_returns, index_returns)[0, 1] / np.var(index_returns)
            beta = beta if not np.isnan(beta) else 0.0

        # Montant à couvrir
        try:
            amount_to_hedge = float(self.amount) if self.amount else 0.0
        except ValueError:
            amount_to_hedge = 0.0

        # Position actuelle
        portfolio = self.player.portfolio
        position = portfolio.get(self.ticker, {"shares": 0.0})
        current_shares = position["shares"]
        current_value = current_shares * self.market.price_of(self.ticker) if self.market.price_of(self.ticker) else 0.0

        # Calculer le nombre de titres de l'indice nécessaires
        index_price = self.market.price_of(self.hedge_ticker)
        hedge_shares = -(beta * amount_to_hedge / index_price) if index_price and index_price > 0 else 0.0

        # Coût estimé
        commission = 0.001
        hedge_cost = abs(hedge_shares * index_price * commission) if index_price else 0.0

        self._results = {
            "type": "Couverture Beta",
            "beta": beta,
            "hedge_ratio": beta,
            "current_position": current_shares,
            "current_value": current_value,
            "hedge_shares": hedge_shares,
            "hedge_value": abs(hedge_shares * index_price) if index_price else 0.0,
            "hedge_cost": hedge_cost,
            "explanation": f"Beta de {self.ticker} vs {self.hedge_ticker} = {beta:.2f}"
        }
        self.msg = f"Couverture beta calculée (beta: {beta:.2f})"

    def _compute_statistical_hedge(self):
        """Calcul de couverture statistique (pairs trading)."""
        if not self.hedge_ticker:
            self.msg = "Veuillez sélectionner un actif de couverture"
            return

        # Historique
        hist_length = 252  # ~1 an
        asset1_hist = self.market.history_of(self.ticker, hist_length)
        asset2_hist = self.market.history_of(self.hedge_ticker, hist_length)

        if not asset1_hist or not asset2_hist or len(asset1_hist) < 30 or len(asset2_hist) < 30:
            self.msg = "Données historiques insuffisantes"
            return

        # S'assurer que les séries ont la même longueur
        min_len = min(len(asset1_hist), len(asset2_hist))
        if min_len < 30:
            self.msg = "Données insuffisantes pour le calcul"
            return

        asset1_hist = asset1_hist[-min_len:]
        asset2_hist = asset2_hist[-min_len:]

        # Calculer le ratio de couverture par régression linéaire
        # asset1 = alpha + beta * asset2 + epsilon
        x = np.array(asset2_hist)
        y = np.array(asset1_hist)

        # Calculer beta (slope) et alpha (intercept)
        if np.var(x) == 0:
            beta = 0.0
            alpha = np.mean(y)
        else:
            beta = np.cov(x, y)[0, 1] / np.var(x)
            beta = beta if not np.isnan(beta) else 0.0
            alpha = np.mean(y) - beta * np.mean(x)

        # Calculer le spread
        spread = y - (alpha + beta * x)
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)

        # Montant à couvrir
        try:
            amount_to_hedge = float(self.amount) if self.amount else 0.0
        except ValueError:
            amount_to_hedge = 0.0

        # Position actuelle
        portfolio = self.player.portfolio
        position1 = portfolio.get(self.ticker, {"shares": 0.0})
        position2 = portfolio.get(self.hedge_ticker, {"shares": 0.0})
        current_shares1 = position1["shares"]
        current_shares2 = position2["shares"]

        current_price1 = self.market.price_of(self.ticker)
        current_price2 = self.market.price_of(self.hedge_ticker)
        current_value1 = current_shares1 * current_price1 if current_price1 else 0.0
        current_value2 = current_shares2 * current_price2 if current_price2 else 0.0

        # Calculer le nombre de titres nécessaires pour la couverture
        hedge_shares2 = -(beta * amount_to_hedge / current_price2) if current_price2 and current_price2 > 0 else 0.0

        # Coût estimé
        commission = 0.001
        hedge_cost = abs(hedge_shares2 * current_price2 * commission) if current_price2 else 0.0

        self._results = {
            "type": "Couverture Statistique",
            "alpha": alpha,
            "beta": beta,
            "hedge_ratio": beta,
            "spread_mean": spread_mean,
            "spread_std": spread_std,
            "current_position1": current_shares1,
            "current_position2": current_shares2,
            "current_value1": current_value1,
            "current_value2": current_value2,
            "hedge_shares": hedge_shares2,
            "hedge_value": abs(hedge_shares2 * current_price2) if current_price2 else 0.0,
            "hedge_cost": hedge_cost,
            "explanation": f"Ratio: 1 unité de {self.ticker} = {beta:.2f} unités de {self.hedge_ticker}"
        }
        self.msg = f"Couverture statistique calculée (beta: {beta:.2f})"

    def _execute_hedge(self):
        """Exécute la stratégie de couverture calculée."""
        if not self._results:
            self.msg = "Veuillez d'abord calculer une stratégie de couverture"
            return

        try:
            hedge_shares = self._results.get("hedge_shares", 0.0)
            if abs(hedge_shares) < 0.01:
                self.msg = "Pas de couverture nécessaire"
                return

            # Acheter/vendre l'actif de couverture
            if hedge_shares > 0:
                # Acheter
                result = PF.buy(self.player, self.market, self.hedge_ticker, hedge_shares)
                if result["ok"]:
                    self.msg = f"Couverture exécutée : acheté {hedge_shares:.2f} {self.hedge_ticker}"
                else:
                    self.msg = f"Échec de l'achat : {result.get('reason', 'erreur inconnue')}"
            else:
                # Vendre (ou short si on n'en possède pas)
                abs_shares = abs(hedge_shares)
                position = self.player.portfolio.get(self.hedge_ticker, {"shares": 0.0})
                held_shares = position["shares"]

                if held_shares >= abs_shares:
                    # Vendre les titres détenus
                    result = PF.sell(self.player, self.market, self.hedge_ticker, abs_shares)
                    if result["ok"]:
                        self.msg = f"Couverture exécutée : vendu {abs_shares:.2f} {self.hedge_ticker}"
                    else:
                        self.msg = f"Échec de la vente : {result.get('reason', 'erreur inconnue')}"
                else:
                    # Vendre les titres détenus + short le reste
                    if held_shares > 0:
                        # Vendre les titres détenus
                        PF.sell(self.player, self.market, self.hedge_ticker, held_shares)

                    # Short le reste
                    short_amount = abs_shares - held_shares
                    result = PF.short(self.player, self.market, self.hedge_ticker, short_amount)
                    if result["ok"]:
                        self.msg = f"Couverture exécutée : shorté {short_amount:.2f} {self.hedge_ticker}"
                    else:
                        self.msg = f"Échec du short : {result.get('reason', 'erreur inconnue')}"

        except Exception as e:
            self.msg = f"Erreur d'exécution : {str(e)}"

    def _select_position(self):
        """Sélectionne automatiquement une position du portefeuille."""
        portfolio = self.player.portfolio
        if portfolio:
            # Prendre la première position
            ticker = next(iter(portfolio))
            self.ticker = ticker
            # Estimer le montant à couvrir
            position = portfolio[ticker]
            price = self.market.price_of(ticker)
            if price:
                value = abs(position["shares"] * price)
                self.amount = f"{value:.0f}"

    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Sélection du mode
            for mode, rect_btn in self._mode_rects.items():
                if rect_btn and rect_btn.collidepoint(pos):
                    self.mode = mode
                    return True

            # Zones de saisie
            if self._ticker_rect and self._ticker_rect.collidepoint(pos):
                self._ticker_input_active = True
                self._hedge_ticker_input_active = False
                self._amount_input_active = False
                return True
            elif self._hedge_ticker_rect and self._hedge_ticker_rect.collidepoint(pos):
                self._ticker_input_active = False
                self._hedge_ticker_input_active = True
                self._amount_input_active = False
                return True
            elif self._amount_rect and self._amount_rect.collidepoint(pos):
                self._ticker_input_active = False
                self._hedge_ticker_input_active = False
                self._amount_input_active = True
                return True
            else:
                # Clic en dehors des zones de saisie
                self._ticker_input_active = False
                self._hedge_ticker_input_active = False
                self._amount_input_active = False

            # Sélection automatique d'une position
            if self._selected_position and self._selected_position.collidepoint(pos):
                self._select_position()
                return True

            # Bouton calculer
            if self._compute_btn and self._compute_btn.collidepoint(pos):
                self._compute_hedge()
                return True

            # Bouton exécuter
            if self._execute_btn and self._execute_btn.collidepoint(pos):
                self._execute_hedge()
                return True

        elif event.type == pygame.KEYDOWN:
            # Saisie du ticker
            if self._ticker_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.ticker = self.ticker[:-1]
                elif event.key == pygame.K_RETURN:
                    self._ticker_input_active = False
                elif event.unicode.isalnum() or event.unicode in ".-":
                    if len(self.ticker) < 10:
                        self.ticker += event.unicode.upper()
                return True

            # Saisie du ticker de couverture
            if self._hedge_ticker_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.hedge_ticker = self.hedge_ticker[:-1]
                elif event.key == pygame.K_RETURN:
                    self._hedge_ticker_input_active = False
                elif event.unicode.isalnum() or event.unicode in ".-":
                    if len(self.hedge_ticker) < 10:
                        self.hedge_ticker += event.unicode.upper()
                return True

            # Saisie du montant
            if self._amount_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.amount = self.amount[:-1]
                elif event.key == pygame.K_RETURN:
                    self._amount_input_active = False
                elif event.unicode.isdigit() or event.unicode == ".":
                    if len(self.amount) < 15:
                        self.amount += event.unicode
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

        # Modes de couverture
        y = rect.y + 90
        widgets.draw_text(surf, "Mode de couverture :", (rect.x + 20, y), fonts.small(bold=True), config.COL_TEXT)

        x = rect.x + 200
        modes = [("delta", "Delta"), ("beta", "Beta"), ("statistical", "Statistique")]
        self._mode_rects = {}
        for mode, label in modes:
            rect_btn = pygame.Rect(x, y, 100, 24)
            self._mode_rects[mode] = rect_btn
            color = config.COL_PRESTIGE if self.mode == mode else config.COL_PANEL
            pygame.draw.rect(surf, color, rect_btn, border_radius=4)
            widgets.draw_text(surf, label, rect_btn.center, fonts.small(), config.COL_TEXT, align="center")
            x += 110

        # Sélection automatique d'une position
        self._selected_position = pygame.Rect(rect.x + 20, y + 30, 200, 24)
        pygame.draw.rect(surf, config.COL_PANEL, self._selected_position, border_radius=4)
        widgets.draw_text(surf, "Sélectionner une position", self._selected_position.center,
                         fonts.small(), config.COL_TEXT, align="center")

        # Saisie des paramètres
        y += 70
        widgets.draw_text(surf, "Actif à couvrir :", (rect.x + 20, y), fonts.small(bold=True), config.COL_TEXT)
        self._ticker_rect = pygame.Rect(rect.x + 150, y-5, 100, 30)
        pygame.draw.rect(surf, config.COL_WHITE if self._ticker_input_active else config.COL_PANEL,
                        self._ticker_rect, border_radius=4)
        widgets.draw_text(surf, self.ticker, (rect.x + 155, y+2), fonts.small(), config.COL_TEXT)

        y += 40
        widgets.draw_text(surf, "Actif de couverture :", (rect.x + 20, y), fonts.small(bold=True), config.COL_TEXT)
        self._hedge_ticker_rect = pygame.Rect(rect.x + 180, y-5, 100, 30)
        pygame.draw.rect(surf, config.COL_WHITE if self._hedge_ticker_input_active else config.COL_PANEL,
                        self._hedge_ticker_rect, border_radius=4)
        widgets.draw_text(surf, self.hedge_ticker, (rect.x + 185, y+2), fonts.small(), config.COL_TEXT)

        y += 40
        widgets.draw_text(surf, "Montant à couvrir (€) :", (rect.x + 20, y), fonts.small(bold=True), config.COL_TEXT)
        self._amount_rect = pygame.Rect(rect.x + 200, y-5, 120, 30)
        pygame.draw.rect(surf, config.COL_WHITE if self._amount_input_active else config.COL_PANEL,
                        self._amount_rect, border_radius=4)
        widgets.draw_text(surf, self.amount, (rect.x + 205, y+2), fonts.small(), config.COL_TEXT)

        # Bouton calculer
        y += 50
        self._compute_btn = pygame.Rect(rect.x + 20, y, 120, 30)
        pygame.draw.rect(surf, config.COL_AMBER, self._compute_btn, border_radius=4)
        widgets.draw_text(surf, "Calculer", self._compute_btn.center,
                         fonts.small(bold=True), config.COL_BG, align="center")

        # Résultats
        if self._results:
            y += 60
            widgets.draw_text(surf, f"Stratégie : {self._results['type']}", (rect.x + 20, y),
                             fonts.small(bold=True), config.COL_TEXT)

            y += 30
            # Afficher les résultats
            widgets.draw_text(surf, f"Ratio de couverture : {self._results['hedge_ratio']:.3f}", (rect.x + 40, y),
                             fonts.small(), config.COL_TEXT)
            y += 25

            if "correlation" in self._results:
                widgets.draw_text(surf, f"Corrélation : {self._results['correlation']:.3f}", (rect.x + 40, y),
                                 fonts.small(), config.COL_TEXT)
                y += 25

            if "beta" in self._results:
                widgets.draw_text(surf, f"Beta : {self._results['beta']:.3f}", (rect.x + 40, y),
                                 fonts.small(), config.COL_TEXT)
                y += 25

            widgets.draw_text(surf, f"Position actuelle : {self._results['current_position']:.2f}", (rect.x + 40, y),
                             fonts.small(), config.COL_TEXT)
            y += 25

            widgets.draw_text(surf, f"Titres de couverture nécessaires : {self._results['hedge_shares']:.2f}", (rect.x + 40, y),
                             fonts.small(), config.COL_TEXT)
            y += 25

            widgets.draw_text(surf, f"Coût estimé : {self._results['hedge_cost']:.2f}€", (rect.x + 40, y),
                             fonts.small(), config.COL_TEXT)
            y += 25

            if "effectiveness" in self._results:
                eff_color = config.COL_UP if self._results['effectiveness'] == "Élevée" else (config.COL_AMBER if self._results['effectiveness'] == "Moyenne" else config.COL_DOWN)
                widgets.draw_text(surf, f"Efficacité attendue : {self._results['effectiveness']}", (rect.x + 40, y),
                                 fonts.small(), eff_color)
                y += 25

            y += 10
            widgets.draw_text(surf, self._results['explanation'], (rect.x + 20, y),
                             fonts.small(), config.COL_TEXT_DIM)

            # Recommandations
            y += 35
            if "effectiveness" in self._results:
                if self._results['effectiveness'] == "Élevée":
                    recommendation = "Couverture recommandée - corrélation forte"
                    rec_color = config.COL_UP
                elif self._results['effectiveness'] == "Moyenne":
                    recommendation = "Couverture possible - surveiller la corrélation"
                    rec_color = config.COL_AMBER
                else:
                    recommendation = "Couverture peu efficace - envisager alternatives"
                    rec_color = config.COL_DOWN

                widgets.draw_text(surf, f"Recommandation : {recommendation}", (rect.x + 20, y),
                                 fonts.small(bold=True), rec_color)

            # Bouton exécuter
            y += 40
            self._execute_btn = pygame.Rect(rect.x + 20, y, 120, 30)
            pygame.draw.rect(surf, config.COL_UP, self._execute_btn, border_radius=4)
            widgets.draw_text(surf, "Exécuter", self._execute_btn.center,
                             fonts.small(bold=True), config.COL_BG, align="center")