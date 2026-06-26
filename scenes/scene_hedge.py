"""
scene_hedge.py — Desk de couverture (puts protecteurs sur l'indice régional).

Le joueur réduit l'exposition de son portefeuille sans liquider ses positions
en achetant un put sur l'indice phare de sa région (strike/maturité au choix).
Logique de cotation/dénouement dans core/hedging.py (Black-Scholes, cf.
core.finmath). Ouvert via PROTECT.
"""
import pygame

from core import config, unlocks
from core import hedging as H
from core.scene_manager import Scene
from ui import fonts, keynav, widgets

NOTIONAL = 100_000.0    # notionnel couvert par clic


class HedgeScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.strike_idx = 0     # index dans H.STRIKE_CHOICES
        self.years_idx = 1      # index dans H.MATURITY_CHOICES
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "📘 TUTO", config.COL_CYAN)
        self.buy_btn = None
        self.strike_rects = {}
        self.years_rects = {}
        self._all_rects = {}
        self.focus = "buy"

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "hedge")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _activate_focus(self):
        key = self.focus
        if key is None:
            return
        if isinstance(key, tuple) and key[0] == "strike":
            self.strike_idx = key[1]
        elif isinstance(key, tuple) and key[0] == "years":
            self.years_idx = key[1]
        elif key == "buy" and self.buy_btn:
            p, m = self.app.gs.player, self.app.market
            strike_pct = H.STRIKE_CHOICES[self.strike_idx]
            years = H.MATURITY_CHOICES[self.years_idx]
            r = H.buy_put(p, m, NOTIONAL, strike_pct, years)
            self.msg = (f"Couverture souscrite ({widgets.format_money(NOTIONAL, self._cur())}, "
                        f"prime {widgets.format_money(r['premium'], self._cur())})."
                        if r["ok"] else f"Refusé ({r['reason']}).")
            if r["ok"] and not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="hedge", return_to="hedge")
            return
        if not self._can():
            return
        if event.type == pygame.KEYDOWN:
            self.focus, activate = keynav.grid_nav(event, self._all_rects, self.focus)
            if activate:
                self._activate_focus()
                return
            if event.key in keynav.DIRECTIONS:
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in self.strike_rects.items():
                if rect.collidepoint(event.pos):
                    self.strike_idx = i
                    return
            for i, rect in self.years_rects.items():
                if rect.collidepoint(event.pos):
                    self.years_idx = i
                    return
            if self.buy_btn and self.buy_btn.collidepoint(event.pos):
                p, m = self.app.gs.player, self.app.market
                strike_pct = H.STRIKE_CHOICES[self.strike_idx]
                years = H.MATURITY_CHOICES[self.years_idx]
                r = H.buy_put(p, m, NOTIONAL, strike_pct, years)
                self.msg = (f"Couverture souscrite ({widgets.format_money(NOTIONAL, self._cur())}, "
                            f"prime {widgets.format_money(r['premium'], self._cur())})."
                            if r["ok"] else f"Refusé ({r['reason']}).")
                if r["ok"] and not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "DESK DE COUVERTURE — PUT PROTECTEUR", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "hedge")
            widgets.draw_text(surf, f"⊘ Couverture débloquée au grade {config.GRADES[g]}.",
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return
        widgets.draw_text(surf, "Achetez un put sur l'indice de votre région pour réduire le bêta net "
                                "sans vendre vos positions. " + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        m, p = self.app.market, self.app.gs.player
        cur = self._cur()

        # ---- cotation / souscription (gauche) ----
        quote_rect = pygame.Rect(40, 110, 440, 280)
        inner = widgets.draw_panel(surf, quote_rect, "Nouvelle couverture", config.COL_CYAN)
        y = inner.y
        widgets.draw_text(surf, "Strike (% du niveau courant)", (inner.x, y),
                          fonts.small(), config.COL_TEXT)
        y += 22
        self.strike_rects = {}
        self._all_rects = {}
        x = inner.x
        for i, pct in enumerate(H.STRIKE_CHOICES):
            rect = pygame.Rect(x, y, 90, 28)
            sel = i == self.strike_idx
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, f"{pct*100:.0f}%", rect.center, fonts.small(bold=True),
                              config.COL_CYAN if sel else config.COL_TEXT, align="center")
            self.strike_rects[i] = rect
            fk = ("strike", i)
            self._all_rects[fk] = rect
            keynav.draw_focus_ring(surf, rect, self.focus == fk)
            x += 100
        y += 40

        widgets.draw_text(surf, "Maturité", (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.years_rects = {}
        x = inner.x
        for i, yrs in enumerate(H.MATURITY_CHOICES):
            rect = pygame.Rect(x, y, 90, 28)
            sel = i == self.years_idx
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=4)
            label = f"{yrs*12:.0f}m" if yrs < 1 else f"{yrs:.0f}a"
            widgets.draw_text(surf, label, rect.center, fonts.small(bold=True),
                              config.COL_CYAN if sel else config.COL_TEXT, align="center")
            self.years_rects[i] = rect
            fk = ("years", i)
            self._all_rects[fk] = rect
            keynav.draw_focus_ring(surf, rect, self.focus == fk)
            x += 100
        y += 40

        strike_pct = H.STRIKE_CHOICES[self.strike_idx]
        years = H.MATURITY_CHOICES[self.years_idx]
        q = H.quote(p, m, strike_pct, years)
        premium = NOTIONAL * q["premium_rate"]
        widgets.draw_text(surf, f"Sous-jacent : {q['underlying']} @ {q['spot']:.1f} "
                                f"(strike {q['strike']:.1f}, vol {q['sigma']*100:.0f}%)",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 20
        widgets.draw_text(surf, f"Notionnel couvert : {widgets.format_money(NOTIONAL, cur)}",
                          (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        widgets.draw_text(surf, f"Prime à payer : {widgets.format_money(premium, cur)}",
                          (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
        y += 36
        self.buy_btn = pygame.Rect(inner.x, y, 200, 32)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.buy_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self.buy_btn, 1, border_radius=4)
        widgets.draw_text(surf, "SOUSCRIRE", self.buy_btn.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
        self._all_rects["buy"] = self.buy_btn
        keynav.draw_focus_ring(surf, self.buy_btn, self.focus == "buy")

        # ---- contexte risque (milieu) ----
        risk_rect = pygame.Rect(500, 110, 320, 150)
        rinner = widgets.draw_panel(surf, risk_rect, "Exposition", config.COL_AMBER)
        from core import portfolio as pf
        beta = pf.portfolio_beta(p, m)
        coverage = H.coverage_ratio(p, m)
        bcol = config.COL_DOWN if beta > 1.3 else (config.COL_WARN if beta > 1.0 else config.COL_UP)
        widgets.draw_text(surf, f"Bêta net du portefeuille : {beta:.2f}",
                          (rinner.x, rinner.y), fonts.small(bold=True), bcol)
        widgets.draw_text(surf, "(marché neutre = 1.00 · prudent ≤ 0.80)",
                          (rinner.x, rinner.y + 18), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text_wrapped(surf, f"Couverture en cours : {coverage*100:.0f}% de l'exposition brute",
                          (rinner.x, rinner.y + 40), fonts.small(),
                          config.COL_UP if coverage > 0 else config.COL_TEXT_DIM, rinner.w)

        # ---- positions en cours (droite) ----
        pos_rect = pygame.Rect(840, 110, config.SCREEN_WIDTH - 880, 280)
        pinner = widgets.draw_panel(surf, pos_rect, "Couvertures en cours", config.COL_UP)
        hold = H.holdings(p, m)
        if not hold:
            widgets.draw_text(surf, "Aucune couverture active.", (pinner.x, pinner.y),
                              fonts.small(), config.COL_TEXT_DIM)
        else:
            yy = pinner.y
            for h in hold:
                widgets.draw_text(surf, f"{widgets.format_money(h['notional'], cur)} · "
                                        f"strike {h['strike_pct']*100:.0f}%",
                                  (pinner.x, yy), fonts.small(bold=True), config.COL_TEXT)
                pcol = config.COL_UP if h["in_money"] else config.COL_TEXT_DIM
                widgets.draw_text(surf, f"sous-jacent {h['perf']:+.1f}% · échéance {h['years_left']:.1f} an"
                                        + (" · DANS LA MONNAIE" if h["in_money"] else ""),
                                  (pinner.x, yy + 18), fonts.tiny(), pcol)
                yy += 40

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", "paramètres"), ("ENTRÉE", "couvrir")])
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
