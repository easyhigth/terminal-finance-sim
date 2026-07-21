"""
scene_options.py — Desk d'options sur actions individuelles (CALL / PUT).

Le joueur choisit un titre suivi (watchlist ou portefeuille), un sens
(call/put), un strike et une maturité, puis achète des contrats. Logique de
cotation/dénouement dans core/options.py (Black-Scholes, cf. core.finmath).
Calqué sur scenes/scene_hedge.py (puts protecteurs sur indice).
"""
import pygame

from core import config, unlocks
from core import options as O
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, keynav, widgets

CONTRACTS_STEP = 10


def _L(fr, en):
    return en if get_lang() == "en" else fr


class OptionsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.ticker_idx = 0          # index dans la liste de tickers proposés
        self.type_idx = 0            # 0 = call, 1 = put
        self.strike_idx = 1          # index dans O.STRIKE_CHOICES (1.00 = ATM)
        self.years_idx = 1           # index dans O.MATURITY_CHOICES
        self.contracts = 100
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       _L("TUTO", "GUIDE"), config.COL_CYAN)
        self.buy_btn = None
        self.ticker_rects = {}
        self.type_rects = {}
        self.strike_rects = {}
        self.years_rects = {}
        self.contract_minus_btn = None
        self.contract_plus_btn = None
        self._all_rects = {}
        self.focus = "buy"

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "options")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _tickers(self):
        p = self.app.gs.player
        out = list(p.watchlist)
        for tk in p.portfolio:
            if tk not in out:
                out.append(tk)
        return out

    def _shown_tickers(self):
        return self._tickers()[:15]

    def _ticker(self):
        tickers = self._shown_tickers()
        if not tickers:
            return None
        i = min(self.ticker_idx, len(tickers) - 1)
        return tickers[i]

    def _activate_focus(self):
        key = self.focus
        if key is None:
            return
        if isinstance(key, tuple) and key[0] == "ticker":
            self.ticker_idx = key[1]
        elif isinstance(key, tuple) and key[0] == "type":
            self.type_idx = key[1]
        elif isinstance(key, tuple) and key[0] == "strike":
            self.strike_idx = key[1]
        elif isinstance(key, tuple) and key[0] == "years":
            self.years_idx = key[1]
        elif key == "contracts:minus":
            self.contracts = max(CONTRACTS_STEP, self.contracts - CONTRACTS_STEP)
        elif key == "contracts:plus":
            self.contracts += CONTRACTS_STEP
        elif key == "buy" and self.buy_btn:
            p, m = self.app.gs.player, self.app.market
            ticker = self._ticker()
            if ticker is None:
                self.msg = _L("Aucun titre suivi (ajoutez-en un à la watchlist).", "No watched security (add one to the watchlist).")
                return
            option_type = "call" if self.type_idx == 0 else "put"
            strike_pct = O.STRIKE_CHOICES[self.strike_idx]
            years = O.MATURITY_CHOICES[self.years_idx]
            r = O.buy(p, m, ticker, option_type, strike_pct, years, self.contracts)
            self.msg = (_L(f"{self.contracts} {option_type} {ticker} achetés "
                        f"(prime {widgets.format_money(r['premium'], self._cur())}).",
                        f"{self.contracts} {option_type} {ticker} bought "
                        f"(premium {widgets.format_money(r['premium'], self._cur())}).")
                        if r["ok"] else _L(f"Refusé ({r['reason']}).", f"Rejected ({r['reason']})."))
            if r["ok"] and not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="options", return_to="options")
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
            for i, rect in self.ticker_rects.items():
                if rect.collidepoint(event.pos):
                    self.ticker_idx = i
                    return
            for i, rect in self.type_rects.items():
                if rect.collidepoint(event.pos):
                    self.type_idx = i
                    return
            for i, rect in self.strike_rects.items():
                if rect.collidepoint(event.pos):
                    self.strike_idx = i
                    return
            for i, rect in self.years_rects.items():
                if rect.collidepoint(event.pos):
                    self.years_idx = i
                    return
            if self.contract_minus_btn and self.contract_minus_btn.collidepoint(event.pos):
                self.contracts = max(CONTRACTS_STEP, self.contracts - CONTRACTS_STEP)
                return
            if self.contract_plus_btn and self.contract_plus_btn.collidepoint(event.pos):
                self.contracts += CONTRACTS_STEP
                return
            if self.buy_btn and self.buy_btn.collidepoint(event.pos):
                p, m = self.app.gs.player, self.app.market
                ticker = self._ticker()
                if ticker is None:
                    self.msg = _L("Aucun titre suivi (ajoutez-en un à la watchlist).", "No watched security (add one to the watchlist).")
                    return
                option_type = "call" if self.type_idx == 0 else "put"
                strike_pct = O.STRIKE_CHOICES[self.strike_idx]
                years = O.MATURITY_CHOICES[self.years_idx]
                r = O.buy(p, m, ticker, option_type, strike_pct, years, self.contracts)
                self.msg = (_L(f"{self.contracts} {option_type} {ticker} achetés "
                            f"(prime {widgets.format_money(r['premium'], self._cur())}).",
                            f"{self.contracts} {option_type} {ticker} bought "
                            f"(premium {widgets.format_money(r['premium'], self._cur())}).")
                            if r["ok"] else _L(f"Refusé ({r['reason']}).", f"Rejected ({r['reason']})."))
                if r["ok"] and not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("DESK D'OPTIONS — CALLS / PUTS ACTIONS", "OPTIONS DESK — EQUITY CALLS / PUTS"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can():
            p = self.app.gs.player
            g = unlocks.effective_required_grade(p, "options")
            widgets.draw_text(surf, _L(f"⊘ Desk d'options débloqué au grade {config.GRADES[g]}.", f"⊘ Options desk unlocked at {config.GRADES[g]} grade."),
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            note = unlocks.track_lock_note(p, "options")
            if note:
                widgets.draw_text(surf, note.strip(), (42, 94), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return
        widgets.draw_text(surf, _L("Achetez un call ou un put sur un titre suivi pour parier sur sa "
                                "direction avec un risque borné à la prime. ",
                                "Buy a call or a put on a watched security to bet on its "
                                "direction with risk capped at the premium. ") + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        m, p = self.app.market, self.app.gs.player
        cur = self._cur()
        all_tickers = self._tickers()
        tickers = self._shown_tickers()

        # ---- cotation / souscription (gauche) ----
        quote_rect = pygame.Rect(40, 110, 460, 410)
        inner = widgets.draw_panel(surf, quote_rect, _L("Nouvelle position", "New position"), config.COL_CYAN)
        y = inner.y

        widgets.draw_text(surf, _L("Titre (watchlist / portefeuille)", "Security (watchlist / portfolio)"), (inner.x, y),
                          fonts.small(), config.COL_TEXT)
        y += 22
        self.ticker_rects = {}
        self._all_rects = {}
        if not tickers:
            widgets.draw_text(surf, _L("Aucun titre suivi — ajoutez-en via WATCH <ticker>.", "No watched security — add one via WATCH <ticker>."),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 30
        else:
            x = inner.x
            for i, tk in enumerate(tickers):
                rect = pygame.Rect(x, y, 70, 26)
                sel = i == min(self.ticker_idx, len(tickers) - 1)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=4)
                widgets.draw_text(surf, tk, rect.center, fonts.tiny(bold=True),
                                  config.COL_CYAN if sel else config.COL_TEXT, align="center")
                self.ticker_rects[i] = rect
                fk = ("ticker", i)
                self._all_rects[fk] = rect
                keynav.draw_focus_ring(surf, rect, self.focus == fk)
                x += 76
                if x + 76 > inner.right:
                    x = inner.x
                    y += 30
            y += 30
            if len(all_tickers) > len(tickers):
                widgets.draw_text(surf, _L(f"+{len(all_tickers) - len(tickers)} autre(s) titre(s) suivi(s) "
                                        "(gérez votre watchlist pour réduire la liste).",
                                        f"+{len(all_tickers) - len(tickers)} more watched security(ies) "
                                        "(manage your watchlist to shorten the list)."),
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
                y += 14
            y += 6

        widgets.draw_text(surf, _L("Sens", "Direction"), (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.type_rects = {}
        x = inner.x
        for i, label in enumerate(("CALL", "PUT")):
            rect = pygame.Rect(x, y, 90, 28)
            sel = i == self.type_idx
            col = config.COL_UP if i == 0 else config.COL_DOWN
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, col if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, label, rect.center, fonts.small(bold=True),
                              col if sel else config.COL_TEXT, align="center")
            self.type_rects[i] = rect
            fk = ("type", i)
            self._all_rects[fk] = rect
            keynav.draw_focus_ring(surf, rect, self.focus == fk)
            x += 100
        y += 40

        widgets.draw_text(surf, _L("Strike (% du spot)", "Strike (% of spot)"), (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.strike_rects = {}
        x = inner.x
        for i, pct in enumerate(O.STRIKE_CHOICES):
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

        widgets.draw_text(surf, _L("Maturité", "Maturity"), (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.years_rects = {}
        x = inner.x
        for i, yrs in enumerate(O.MATURITY_CHOICES):
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

        widgets.draw_text(surf, _L("Contrats (1 = 1 action)", "Contracts (1 = 1 share)"), (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.contract_minus_btn = pygame.Rect(inner.x, y, 32, 28)
        self.contract_plus_btn = pygame.Rect(inner.x + 150, y, 32, 28)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.contract_minus_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self.contract_minus_btn, 1, border_radius=4)
        widgets.draw_text(surf, "-", self.contract_minus_btn.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        self._all_rects["contracts:minus"] = self.contract_minus_btn
        keynav.draw_focus_ring(surf, self.contract_minus_btn, self.focus == "contracts:minus")
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.contract_plus_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self.contract_plus_btn, 1, border_radius=4)
        widgets.draw_text(surf, "+", self.contract_plus_btn.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        self._all_rects["contracts:plus"] = self.contract_plus_btn
        keynav.draw_focus_ring(surf, self.contract_plus_btn, self.focus == "contracts:plus")
        widgets.draw_text(surf, str(self.contracts), (inner.x + 60, y + 4),
                          fonts.small(bold=True), config.COL_TEXT)
        y += 40

        ticker = self._ticker()
        if ticker is not None:
            option_type = "call" if self.type_idx == 0 else "put"
            strike_pct = O.STRIKE_CHOICES[self.strike_idx]
            years = O.MATURITY_CHOICES[self.years_idx]
            q = O.quote(p, m, ticker, option_type, strike_pct, years)
            if q.get("ok"):
                total_premium = q["premium"] * self.contracts
                widgets.draw_text(surf, f"{ticker} @ {q['spot']:.2f} (strike {q['strike']:.2f}, "
                                        f"vol {q['sigma']*100:.0f}%)",
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
                y += 20
                widgets.draw_text(surf, _L(f"Prime totale : {widgets.format_money(total_premium, cur)}", f"Total premium: {widgets.format_money(total_premium, cur)}"),
                                  (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
                y += 22
                g = q["greeks"]
                widgets.draw_text(surf, f"Δ {g['delta']:+.2f}  Γ {g['gamma']:.3f}  "
                                        f"V {g['vega']:+.3f}  Θ {g['theta']:+.3f}  ρ {g['rho']:+.3f}",
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
                y += 18
                # le thêta traduit en devise PAR TOUR + point mort : ce que
                # l'option coûte si rien ne bouge, et où elle devient gagnante
                from core import config as _cfg
                theta_step = abs(g["theta"]) * self.contracts * _cfg.DAYS_PER_STEP / 365.0
                if option_type == "call":
                    breakeven = q["strike"] + q["premium"]
                else:
                    breakeven = q["strike"] - q["premium"]
                be_pct = (breakeven / q["spot"] - 1.0) * 100.0 if q["spot"] else 0.0
                widgets.draw_text(surf, widgets.fit_text(
                    _L(f"Si rien ne bouge : ~-{theta_step:,.0f}/tour (thêta) · "
                    f"point mort : {breakeven:.2f} ({be_pct:+.1f}%)",
                    f"If nothing moves: ~-{theta_step:,.0f}/step (theta) · "
                    f"breakeven: {breakeven:.2f} ({be_pct:+.1f}%)"),
                    fonts.tiny(), inner.w),
                    (inner.x, y), fonts.tiny(), config.COL_WARN)
                y += 22
                self.buy_btn = pygame.Rect(inner.x, y, 200, 32)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.buy_btn, border_radius=4)
                pygame.draw.rect(surf, config.COL_UP, self.buy_btn, 1, border_radius=4)
                widgets.draw_text(surf, _L("ACHETER", "BUY"), self.buy_btn.center, fonts.small(bold=True),
                                  config.COL_UP, align="center")
                self._all_rects["buy"] = self.buy_btn
                keynav.draw_focus_ring(surf, self.buy_btn, self.focus == "buy")
            else:
                self.buy_btn = None
        else:
            self.buy_btn = None

        # ---- positions en cours (droite) ----
        pos_rect = pygame.Rect(540, 110, config.SCREEN_WIDTH - 580, 410)
        pinner = widgets.draw_panel(surf, pos_rect, _L("Positions en cours", "Open positions"), config.COL_UP)
        hold = O.holdings(p, m)
        if not hold:
            widgets.draw_text(surf, _L("Aucune position ouverte.", "No open position."), (pinner.x, pinner.y),
                              fonts.small(), config.COL_TEXT_DIM)
        else:
            yy = pinner.y
            for h in hold:
                col = config.COL_UP if h["option_type"] == "call" else config.COL_DOWN
                widgets.draw_text(surf, f"{h['contracts']:.0f}x {h['option_type'].upper()} "
                                        f"{h['ticker']} · strike {h['strike_pct']*100:.0f}%",
                                  (pinner.x, yy), fonts.small(bold=True), col)
                widgets.draw_text(surf, _L(f"spot {h['spot']:.2f} ({h['perf']:+.1f}%) · échéance "
                                        f"{h['years_left']:.2f} an",
                                        f"spot {h['spot']:.2f} ({h['perf']:+.1f}%) · expiry "
                                        f"{h['years_left']:.2f}y")
                                        + (_L(" · DANS LA MONNAIE", " · IN THE MONEY") if h["in_money"] else ""),
                                  (pinner.x, yy + 18), fonts.tiny(),
                                  config.COL_UP if h["in_money"] else config.COL_TEXT_DIM)
                g = h["greeks"]
                widgets.draw_text(surf, f"Δ {g['delta']:+.2f}  Γ {g['gamma']:.3f}  "
                                        f"V {g['vega']:+.3f}  Θ {g['theta']:+.3f}",
                                  (pinner.x, yy + 34), fonts.tiny(), config.COL_TEXT_DIM)
                yy += 56

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", _L("paramètres", "settings")), (_L("ENTRÉE", "ENTER"), _L("ouvrir", "open"))])
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
