"""
scene_risk.py — Module Risk : mesure et stress test du risque.
Le joueur gère un portefeuille exposé à plusieurs facteurs de risque.
Outils :
  - VaR historique + paramétrique + CVaR à plusieurs niveaux de confiance
  - Histogramme de la distribution des P&L simulés (Monte-Carlo léger)
  - Scénarios de stress prédéfinis (crise actions, choc de taux, choc de vol)
Basé sur core.finmath (value_at_risk, conditional_var, parametric_var).
"""
import numpy as np
import pygame

from core import config, risklimits, unlocks
from core import finmath as fm
from core import risk as risk_mod
from core.scene_manager import Scene
from ui import fonts, widgets

# Exposition du portefeuille à des facteurs (valeur notionnelle en M)
FACTORS = ["Equities", "Rates", "Credit", "FX", "Commodities"]
DEFAULT_EXPOSURE = np.array([40.0, 25.0, 15.0, 10.0, 10.0])   # M$
# Volatilités quotidiennes par facteur et corrélations (simplifié mais réaliste)
FACTOR_VOL = np.array([0.013, 0.004, 0.006, 0.007, 0.015])    # daily sigma
CORR = np.array([
    [1.00, -0.20, 0.55, 0.25, 0.40],
    [-0.20, 1.00, -0.30, 0.10, -0.10],
    [0.55, -0.30, 1.00, 0.15, 0.30],
    [0.25, 0.10, 0.15, 1.00, 0.20],
    [0.40, -0.10, 0.30, 0.20, 1.00],
])

# Scénarios de stress : choc multiplicatif appliqué à chaque facteur (en sigma)
STRESS_SCENARIOS = {
    "Crise actions (-)": np.array([-6.0, 1.5, -3.0, -1.0, -2.0]),
    "Choc de taux (+)":  np.array([-1.5, -5.0, -2.0, 0.5, -0.5]),
    "Choc de vol":       np.array([-3.0, -1.0, -2.5, -1.5, -3.5]),
    "Stagflation":       np.array([-2.5, -3.0, -1.5, -2.0, 4.0]),
}


class RiskScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.exposure = DEFAULT_EXPOSURE.copy()
        self.confidence = 0.95
        self.scenario = None
        self.scenario_pnl = None
        # mode réel si le joueur a des positions, sinon démo
        p = self.app.gs.player
        self.real = bool(p.portfolio or getattr(p, "bonds", None))
        self.stress_real = None
        self._profile_btns = {}
        self._simulate()
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT-66, 160, 44), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.mode_btn = widgets.Button(
            (210, config.SCREEN_HEIGHT-66, 240, 44), "MODE : —", config.COL_CYAN)
        self.tuto_btn = widgets.Button(
            (460, config.SCREEN_HEIGHT-66, 150, 44), "📘 TUTO", config.COL_WARN)
        self._exp_btns = {}
        self._scenario_btns = {}
        self._conf_btns = {}
        self._reverse_btns = {}
        self._reverse_target = None

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "risk")

    def _cov_matrix(self):
        """Matrice de covariance des P&L des facteurs (en M$)."""
        # sigma_i en $ = exposition_i * vol_i
        dollar_sigma = self.exposure * FACTOR_VOL
        cov = np.outer(dollar_sigma, dollar_sigma) * CORR
        return cov

    def _simulate(self, n=20000):
        if self.real:
            return self._simulate_real()
        return self._simulate_demo(n)

    def _simulate_real(self):
        """VaR/CVaR sur le portefeuille RÉEL via le modèle à facteurs du marché."""
        r = risk_mod.simulate(self.app.gs.player, self.app.market, self.confidence)
        self.total_pnl = r["pnl"]
        self.var, self.cvar = r["var"], r["cvar"]
        self.param_var, self.port_sigma = r["param_var"], r["sigma"]
        self.real_exposures = risk_mod.exposures(self.app.gs.player, self.app.market)
        self.max_dd = risk_mod.net_worth_drawdown(self.app.gs.player)

    def _simulate_demo(self, n=20000):
        """Monte-Carlo : tire des P&L corrélés et calcule les métriques."""
        cov = self._cov_matrix()
        rng = np.random.default_rng(7)
        # décomposition de Cholesky pour générer des chocs corrélés
        try:
            L = np.linalg.cholesky(cov + np.eye(len(cov))*1e-9)
        except np.linalg.LinAlgError:
            L = np.linalg.cholesky(np.diag(np.diag(cov)))
        z = rng.standard_normal((n, len(cov)))
        pnl = z @ L.T                     # P&L par facteur
        self.total_pnl = pnl.sum(axis=1)  # P&L total du portefeuille
        # métriques
        self.var = fm.value_at_risk(self.total_pnl, self.confidence)
        self.cvar = fm.conditional_var(self.total_pnl, self.confidence)
        port_sigma = self.total_pnl.std()
        self.param_var = fm.parametric_var(1.0, 0.0, port_sigma, self.confidence)
        self.port_sigma = port_sigma

    def _run_scenario(self, name):
        """Applique un scénario de stress et calcule la perte instantanée."""
        if self.real:
            self.scenario = name
            self.stress_real = risk_mod.stress(self.app.gs.player, self.app.market, name)
            return
        shocks = STRESS_SCENARIOS[name]           # en nb de sigma
        dollar_sigma = self.exposure * FACTOR_VOL
        pnl_by_factor = shocks * dollar_sigma     # M$ de P&L par facteur
        self.scenario = name
        self.scenario_pnl = pnl_by_factor

    def _adj_exposure(self, i, delta):
        self.exposure[i] = max(0.0, min(100.0, self.exposure[i] + delta))
        self._simulate()
        if self.scenario:
            self._run_scenario(self.scenario)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.mode_btn.handle(event):
            self.real = not self.real
            self.scenario = None
            self.stress_real = None
            self._simulate()
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="risk", return_to="risk")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (minus, plus) in self._exp_btns.items():
                if minus.collidepoint(event.pos):
                    self._adj_exposure(i, -5.0)
                elif plus.collidepoint(event.pos):
                    self._adj_exposure(i, +5.0)
            for name, rect in self._scenario_btns.items():
                if rect.collidepoint(event.pos):
                    self._run_scenario(name)
            for conf, rect in self._conf_btns.items():
                if rect.collidepoint(event.pos):
                    self.confidence = conf
                    self._simulate()
            for pct, rect in self._reverse_btns.items():
                if rect.collidepoint(event.pos):
                    self._reverse_target = None if self._reverse_target == pct else pct
            for name, rect in self._profile_btns.items():
                if rect.collidepoint(event.pos):
                    risklimits.set_profile(self.app.gs.player, name)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp)
        self.mode_btn.label = "MODE : PORTEFEUILLE RÉEL" if self.real else "MODE : DÉMO"
        self.mode_btn.update(mp)
        self.tuto_btn.update(mp)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MODULE RISK — VALUE AT RISK & STRESS TESTS",
                          (40, 24), fonts.title(bold=True), config.COL_AMBER)
        sub = ("Portefeuille RÉEL · modèle à facteurs du marché · horizon 1 pas"
               if self.real else
               "DÉMO · Monte-Carlo corrélé (Cholesky) · horizon 1 jour · "
               "notionnel {:.0f} M$".format(self.exposure.sum()))
        widgets.draw_text(surf, sub, (42, 76), fonts.small(), config.COL_TEXT_DIM)
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "risk")
            widgets.draw_text(surf, f"⊘ Module Risk débloqué au grade {config.GRADES[g]}.",
                              (42, 110), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        self._draw_exposures(surf)
        self._draw_histogram(surf)
        self._draw_sensitivity(surf)
        self._draw_metrics(surf)
        self._draw_stress(surf)
        self._draw_limits(surf)
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("souris", "ajuster les expositions")])
        self.back_btn.draw(surf)
        self.mode_btn.draw(surf)
        self.tuto_btn.draw(surf)

    def _draw_exposures(self, surf):
        panel = pygame.Rect(40, 110, 360, 280)
        self._exp_btns = {}
        if self.real:
            inner = widgets.draw_panel(surf, panel, "Exposition du book réel (M$)", config.COL_CYAN)
            y = inner.y
            for name, val in self.real_exposures.items():
                widgets.draw_text(surf, name, (inner.x, y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{val:,.1f}".replace(",", " "),
                                  (inner.right, y), fonts.small(bold=True),
                                  config.COL_WHITE, align="right")
                y += 34
            widgets.draw_text(surf, f"Max drawdown valeur nette : {self.max_dd*100:.1f}%",
                              (inner.x, inner.bottom - 40), fonts.small(bold=True),
                              widgets.alert_color(self.max_dd * 100, "max_drawdown"))
            widgets.draw_text(surf, "Bascule en MODE DÉMO pour ajuster des expositions.",
                              (inner.x, inner.bottom - 18), fonts.tiny(), config.COL_TEXT_DIM)
            return
        inner = widgets.draw_panel(surf, panel, "Exposition par facteur (M$)", config.COL_CYAN)
        y = inner.y
        for i, name in enumerate(FACTORS):
            widgets.draw_text(surf, name, (inner.x, y), fonts.small(), config.COL_TEXT)
            bar_x, bar_w = inner.x+120, 100
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, (bar_x, y+2, bar_w, 14))
            pygame.draw.rect(surf, config.COL_CYAN,
                             (bar_x, y+2, int(bar_w*self.exposure[i]/100), 14))
            widgets.draw_text(surf, f"{self.exposure[i]:.0f}",
                              (bar_x+bar_w+8, y), fonts.small(), config.COL_WHITE)
            minus = pygame.Rect(inner.x+inner.w-58, y-2, 24, 22)
            plus = pygame.Rect(inner.x+inner.w-30, y-2, 24, 22)
            for rect, sym in ((minus, "-"), (plus, "+")):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
                pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
                img = fonts.body(bold=True).render(sym, True, config.COL_AMBER)
                surf.blit(img, img.get_rect(center=rect.center))
            self._exp_btns[i] = (minus, plus)
            y += 44

    def _draw_histogram(self, surf):
        panel = pygame.Rect(416, 110, 560, 280)
        inner = widgets.draw_panel(surf, panel, "Distribution des P&L simulés (M$)", config.COL_AMBER)
        counts, edges = np.histogram(self.total_pnl, bins=50)
        cmax = counts.max() if counts.max() > 0 else 1
        x0, y0 = inner.x, inner.bottom-20
        w, h = inner.w, inner.h-30
        bw = w / len(counts)
        var_threshold = -self.var
        for i, c in enumerate(counts):
            bx = x0 + i*bw
            bh = (c/cmax)*h
            center = (edges[i]+edges[i+1])/2
            col = config.COL_DOWN if center <= var_threshold else config.COL_UP
            pygame.draw.rect(surf, col, (bx, y0-bh, max(1, bw-1), bh))
        # ligne VaR
        # position x de -VaR
        emin, emax = edges[0], edges[-1]
        if emax > emin:
            vx = x0 + (var_threshold - emin)/(emax-emin)*w
            pygame.draw.line(surf, config.COL_WHITE, (vx, y0-h), (vx, y0), 1)
            widgets.draw_text(surf, f"VaR {int(self.confidence*100)}%",
                              (vx+4, y0-h), fonts.tiny(), config.COL_WHITE)
        widgets.draw_text(surf, "← pertes      gains →", (x0, y0+4),
                          fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_metrics(self, surf):
        panel = pygame.Rect(40, 400, 360, config.footer_y() - 408)
        inner = widgets.draw_panel(surf, panel, "Métriques de risque", config.COL_DOWN)
        # sélecteur de confiance
        self._conf_btns = {}
        widgets.draw_text(surf, "Niveau de confiance :", (inner.x, inner.y),
                          fonts.small(), config.COL_TEXT_DIM)
        cx = inner.x
        for conf in (0.90, 0.95, 0.99):
            rect = pygame.Rect(cx, inner.y+22, 70, 26)
            self._conf_btns[conf] = rect
            sel = (abs(self.confidence-conf) < 1e-6)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1)
            img = fonts.small(bold=sel).render(f"{int(conf*100)}%", True,
                                               config.COL_AMBER if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            cx += 80

        rows = [
            ("VaR historique", f"-{self.var:.2f} M$", config.COL_DOWN),
            ("VaR paramétrique", f"-{self.param_var:.2f} M$", config.COL_WARN),
            ("CVaR (Expected Shortfall)", f"-{self.cvar:.2f} M$", config.COL_DOWN),
            ("Volatilité du P&L (1j)", f"{self.port_sigma:.2f} M$", config.COL_TEXT),
            (f"VaR annualisée (~√{52 if self.real else 252})",
             f"-{self.var*np.sqrt(52 if self.real else 252):.1f} M$", config.COL_NEUTRAL),
        ]
        y = inner.y+58
        for label, val, col in rows:
            widgets.draw_text(surf, label, (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (inner.x+250, y), fonts.body(bold=True), col)
            y += 33

    def _draw_stress(self, surf):
        panel = pygame.Rect(416, 400, 560, config.footer_y() - 408)
        inner = widgets.draw_panel(surf, panel, "Stress Tests — scénarios", config.COL_WARN)
        self._scenario_btns = {}
        names = list(risk_mod.STRESS) if self.real else list(STRESS_SCENARIOS)
        w = max(110, (inner.w - 6 * (len(names) - 1)) // len(names))
        x = inner.x
        for name in names:
            rect = pygame.Rect(x, inner.y, w, 30)
            self._scenario_btns[name] = rect
            sel = (self.scenario == name)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_WARN if sel else config.COL_BORDER, rect, 1)
            font = fonts.tiny(bold=sel)
            img = font.render(widgets.fit_text(name, font, w - 8), True,
                              config.COL_WARN if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            x += w + 6

        if self.real:
            if self.scenario and self.stress_real is not None:
                s = self.stress_real
                y = inner.y + 52
                widgets.draw_text(surf, f"Scénario : {self.scenario} (sur votre book)",
                                  (inner.x, y), fonts.small(bold=True), config.COL_WARN)
                y += 30
                for lab, key in [("Impact actions", "equity"), ("Impact obligations", "bond")]:
                    v = s[key]
                    widgets.draw_text(surf, lab, (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
                    widgets.draw_text(surf, f"{'+' if v>=0 else ''}{v:.2f} M$",
                                      (inner.x+200, y), fonts.small(bold=True),
                                      config.COL_UP if v >= 0 else config.COL_DOWN)
                    y += 26
                tcol = config.COL_UP if s["total"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, "PERTE/GAIN TOTAL", (inner.x, y+6),
                                  fonts.body(bold=True), config.COL_WHITE)
                widgets.draw_text(surf, f"{'+' if s['total']>=0 else ''}{s['total']:.2f} M$",
                                  (inner.x+200, y+6), fonts.head(bold=True), tcol)
            else:
                widgets.draw_text(surf, "Sélectionnez un scénario pour stresser votre book réel.",
                                  (inner.x, inner.y+52), fonts.small(), config.COL_TEXT_DIM)
            return

        if self.scenario and self.scenario_pnl is not None:
            y = inner.y+44
            widgets.draw_text(surf, f"Scénario : {self.scenario}", (inner.x, y),
                              fonts.small(bold=True), config.COL_WARN)
            y += 28
            total = 0.0
            for i, name in enumerate(FACTORS):
                pnl = self.scenario_pnl[i]
                total += pnl
                col = config.COL_UP if pnl >= 0 else config.COL_DOWN
                widgets.draw_text(surf, name, (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"{'+' if pnl>=0 else ''}{pnl:.2f} M$",
                                  (inner.x+180, y), fonts.small(bold=True), col)
                y += 24
            tcol = config.COL_UP if total >= 0 else config.COL_DOWN
            widgets.draw_text(surf, "IMPACT TOTAL", (inner.x, y+4),
                              fonts.body(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, f"{'+' if total>=0 else ''}{total:.2f} M$",
                              (inner.x+180, y+4), fonts.head(bold=True), tcol)
        else:
            widgets.draw_text(surf, "Sélectionnez un scénario pour voir l'impact.",
                              (inner.x, inner.y+50), fonts.small(), config.COL_TEXT_DIM)

    def _draw_sensitivity(self, surf):
        panel = pygame.Rect(992, 110, 248, 280)
        inner = widgets.draw_panel(surf, panel, "Sensibilité facteurs", config.COL_CYAN)
        if not self.real:
            widgets.draw_text(surf, "Disponible en mode portefeuille réel.",
                              (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
            return
        sens = risk_mod.sensitivity(self.app.gs.player, self.app.market)
        y = inner.y
        for label, val in sens.items():
            col = config.COL_DOWN if val < 0 else config.COL_UP
            widgets.draw_text(surf, label, (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{'+' if val >= 0 else ''}{val:.2f} M$",
                              (inner.x, y + 14), fonts.small(bold=True), col)
            y += 38

    def _draw_limits(self, surf):
        panel = pygame.Rect(992, 400, 248, config.footer_y() - 408)
        inner = widgets.draw_panel(surf, panel, "Limites & reverse stress", config.COL_PRESTIGE)
        self._reverse_btns = {}
        self._profile_btns = {}
        if not self.real:
            widgets.draw_text(surf, "Disponible en mode portefeuille réel.",
                              (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
            return
        p = self.app.gs.player
        active = getattr(p, "risk_limit_profile", "default")
        y = inner.y
        bx = inner.x
        for name, label in (("strict", "STRICT"), ("default", "DÉFAUT"), ("souple", "SOUPLE")):
            w = 76
            rect = pygame.Rect(bx, y, w, 22)
            self._profile_btns[name] = rect
            sel = (active == name)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_PRESTIGE if sel else config.COL_BORDER, rect, 1)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              config.COL_PRESTIGE if sel else config.COL_TEXT_DIM, align="center")
            bx += w + 4
        y += 30
        streak = p.flags.get("risk_breach_streak", 0)
        if streak >= 3:
            widgets.draw_text(surf, f"⚠ Réputation impactée (dépassement depuis {streak} tours)",
                              (inner.x, y), fonts.tiny(), config.COL_DOWN)
            y += 16

        res = risklimits.check_limits(p, self.app.market)
        if res["ok"]:
            widgets.draw_badge(surf, "AUCUN DÉPASSEMENT", (inner.x, y), accent=config.COL_UP)
            y += 28
        else:
            breaches = res["breaches"]
            for b in breaches[:3]:
                widgets.draw_text(surf, f"{b['label']} : {b['value']:.1f} > {b['limit']:.1f}",
                                  (inner.x, y), fonts.tiny(), config.COL_DOWN)
                y += 16
            if len(breaches) > 3:
                widgets.draw_text(surf, f"+{len(breaches) - 3} autre(s) dépassement(s)",
                                  (inner.x, y), fonts.tiny(), config.COL_DOWN)
                y += 16
            y += 10

        widgets.draw_text(surf, "Reverse stress (perte cible) :",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 18
        bx = inner.x
        for pct in (10.0, 20.0, 30.0):
            rect = pygame.Rect(bx, y, 70, 24)
            self._reverse_btns[pct] = rect
            sel = (self._reverse_target == pct)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_WARN if sel else config.COL_BORDER, rect, 1)
            img = fonts.tiny(bold=sel).render(f"-{int(pct)}%", True,
                                              config.COL_WARN if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            bx += 76
        y += 32
        if self._reverse_target is not None:
            scen = self.scenario or "Krach actions"
            rs = risk_mod.reverse_stress(self.app.gs.player, self.app.market,
                                         target_loss_pct=self._reverse_target, scenario=scen)
            if rs["ok"]:
                widgets.draw_text(surf, f"Scénario « {scen} »", (inner.x, y),
                                  fonts.tiny(), config.COL_TEXT)
                y += 16
                widgets.draw_text(surf, f"à x{rs['scale']:.2f} pour -{self._reverse_target:.0f}%",
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            else:
                widgets.draw_text(surf, "Pas d'exposition pour ce scénario.",
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
