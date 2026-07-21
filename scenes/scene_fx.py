"""
scene_fx.py — Desk FX : trading de paires de devises au comptant (spot) et à
terme (forward).

Le joueur choisit une paire, un sens (long/short), un notionnel, puis ouvre
une position spot (mark-to-market) ou un forward (verrouillé, réglé à
échéance — débloqué à partir d'un grade plus élevé). Logique de
cotation/dénouement dans core/fx.py. Calqué sur scenes/scene_options.py.
"""
import pygame

from core import config, intraday, unlocks
from core import fx as FX
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, keynav, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


NOTIONAL_STEP = 5000


class FXScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.pair_idx = 0
        self.dir_idx = 0           # 0 = long, 1 = short
        self.tenor_idx = 0         # index dans FX.FORWARD_TENORS
        self.notional = 50000
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       _L("TUTO", "GUIDE"), config.COL_CYAN)
        self.pair_rects = {}
        self.dir_rects = {}
        self.tenor_rects = {}
        self.notional_minus_btn = None
        self.notional_plus_btn = None
        self.spot_btn = None
        self.forward_btn = None
        self.close_rects = {}
        self._all_rects = {}
        self.focus = "spot"
        self._flash = widgets.TickFlash()
        self._t = 0.0

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "fx")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _pair(self):
        return FX.PAIRS[self.pair_idx % len(FX.PAIRS)]

    def _direction(self):
        return "long" if self.dir_idx == 0 else "short"

    def _activate_focus(self):
        key = self.focus
        if key is None:
            return
        if isinstance(key, tuple) and key[0] == "pair":
            self.pair_idx = key[1]
        elif isinstance(key, tuple) and key[0] == "dir":
            self.dir_idx = key[1]
        elif isinstance(key, tuple) and key[0] == "tenor":
            self.tenor_idx = key[1]
        elif key == "notional:minus":
            self.notional = max(NOTIONAL_STEP, self.notional - NOTIONAL_STEP)
        elif key == "notional:plus":
            self.notional += NOTIONAL_STEP
        elif key == "spot":
            p, m = self.app.gs.player, self.app.market
            pair = self._pair()
            direction = self._direction()
            r = FX.open_spot(p, m, pair, direction, self.notional)
            self.msg = (_L(f"Position spot {direction.upper()} {pair} ouverte "
                        f"(notionnel {widgets.format_money(self.notional, self._cur())}).",
                        f"Spot position {direction.upper()} {pair} opened "
                        f"(notional {widgets.format_money(self.notional, self._cur())}).")
                        if r["ok"] else _L(f"Refusé ({r['reason']}).", f"Rejected ({r['reason']})."))
            if r["ok"] and not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        elif key == "forward" and self.forward_btn:
            p, m = self.app.gs.player, self.app.market
            pair = self._pair()
            direction = self._direction()
            tenor = FX.FORWARD_TENORS[self.tenor_idx % len(FX.FORWARD_TENORS)]
            r = FX.open_forward(p, m, pair, direction, self.notional, tenor)
            self.msg = (_L(f"Forward {direction.upper()} {pair} {tenor}m verrouillé.", f"Forward {direction.upper()} {pair} {tenor}m locked.")
                        if r["ok"] else _L(f"Refusé ({r['reason']}).", f"Rejected ({r['reason']})."))
            if r["ok"] and not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        elif isinstance(key, tuple) and key[0] == "close":
            p, m = self.app.gs.player, self.app.market
            r = FX.close_spot(p, m, key[1])
            if r["ok"]:
                self.msg = _L(f"Position fermée, P&L {widgets.format_money(r['pnl'], self._cur())}.", f"Position closed, P&L {widgets.format_money(r['pnl'], self._cur())}.")
                if not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="fx", return_to="fx")
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
            for i, rect in self.pair_rects.items():
                if rect.collidepoint(event.pos):
                    self.pair_idx = i
                    return
            for i, rect in self.dir_rects.items():
                if rect.collidepoint(event.pos):
                    self.dir_idx = i
                    return
            for i, rect in self.tenor_rects.items():
                if rect.collidepoint(event.pos):
                    self.tenor_idx = i
                    return
            if self.notional_minus_btn and self.notional_minus_btn.collidepoint(event.pos):
                self.notional = max(NOTIONAL_STEP, self.notional - NOTIONAL_STEP)
                return
            if self.notional_plus_btn and self.notional_plus_btn.collidepoint(event.pos):
                self.notional += NOTIONAL_STEP
                return
            p, m = self.app.gs.player, self.app.market
            if self.spot_btn and self.spot_btn.collidepoint(event.pos):
                pair = self._pair()
                direction = self._direction()
                r = FX.open_spot(p, m, pair, direction, self.notional)
                self.msg = (_L(f"Position spot {direction.upper()} {pair} ouverte "
                            f"(notionnel {widgets.format_money(self.notional, self._cur())}).",
                            f"Spot position {direction.upper()} {pair} opened "
                            f"(notional {widgets.format_money(self.notional, self._cur())}).")
                            if r["ok"] else _L(f"Refusé ({r['reason']}).", f"Rejected ({r['reason']})."))
                if r["ok"] and not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)
                return
            if self.forward_btn and self.forward_btn.collidepoint(event.pos):
                pair = self._pair()
                direction = self._direction()
                tenor = FX.FORWARD_TENORS[self.tenor_idx % len(FX.FORWARD_TENORS)]
                r = FX.open_forward(p, m, pair, direction, self.notional, tenor)
                self.msg = (_L(f"Forward {direction.upper()} {pair} {tenor}m verrouillé.", f"Forward {direction.upper()} {pair} {tenor}m locked.")
                            if r["ok"] else _L(f"Refusé ({r['reason']}).", f"Rejected ({r['reason']})."))
                if r["ok"] and not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)
                return
            for pid, rect in self.close_rects.items():
                if rect.collidepoint(event.pos):
                    r = FX.close_spot(p, m, pid)
                    if r["ok"]:
                        self.msg = _L(f"Position fermée, P&L {widgets.format_money(r['pnl'], self._cur())}.", f"Position closed, P&L {widgets.format_money(r['pnl'], self._cur())}.")
                        if not p.hardcore:
                            self.app.gs.save(config.AUTOSAVE_SLOT)
                    return

    def _draw_fx_graph(self, surf, rect):
        """Graphe du taux de change de la paire sélectionnée : historique par
        pas + point « en direct » animé (pont brownien déterministe, comme les
        actions/indices), cours courant et variation en gros — pour suivre
        l'évolution de la monnaie en temps réel."""
        m = self.app.market
        pair = self._pair()
        inner = widgets.draw_panel(surf, rect, _L(f"{pair} — cours & évolution", f"{pair} — rate & evolution"), config.COL_CYAN)
        hist = FX.history(m, pair, 80)
        if len(hist) < 2:
            widgets.draw_text(surf, _L("Historique en constitution (avancez le temps).", "History building up (advance time)."),
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return
        # amplitude d'animation proportionnelle à la volatilité de la paire
        vmult = max(0.4, min(2.5, FX.pair_vol(pair) / 0.08))
        series = intraday.append_live(m, self.app.sim_clock, self.app.gs.player.day,
                                      pair, hist, vol_mult=vmult)
        cur = series[-1]
        chg = FX.change_pct(m, pair, 1)
        col = config.COL_UP if chg >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{cur:.4f}", (inner.x, inner.y - 2), fonts.head(bold=True), col)
        widgets.draw_text(surf, _L(f"{chg:+.2f}% / pas · vol {FX.pair_vol(pair)*100:.0f}%", f"{chg:+.2f}% / step · vol {FX.pair_vol(pair)*100:.0f}%"),
                          (inner.x + 160, inner.y + 6), fonts.small(), config.COL_TEXT_DIM)
        chart = pygame.Rect(inner.x, inner.y + 36, inner.w, inner.bottom - (inner.y + 36))
        widgets.draw_series(surf, chart, series, col, mouse_pos=pygame.mouse.get_pos(),
                            y_fmt=lambda v: f"{v:.4f}", show_pct=True)

    def update(self, dt):
        self._t += dt
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("DESK FX — SPOT / FORWARD", "FX DESK — SPOT / FORWARD"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "fx")
            widgets.draw_text(surf, _L(f"⊘ Desk FX débloqué au grade {config.GRADES[g]}.", f"⊘ FX desk unlocked at {config.GRADES[g]} grade."),
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return
        widgets.draw_text(surf, _L("Tradez une paire de devises au comptant ou à terme. ", "Trade a currency pair spot or forward. ") + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        m, p = self.app.market, self.app.gs.player
        cur = self._cur()
        fwd_ok = FX.forward_unlocked(p)

        # ---- cotation / ouverture (gauche) ----
        quote_rect = pygame.Rect(40, 110, 460, 420)
        inner = widgets.draw_panel(surf, quote_rect, _L("Nouvelle position", "New position"), config.COL_CYAN)
        y = inner.y

        widgets.draw_text(surf, _L("Paire", "Pair"), (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        # Tableau des paires : chaque case montre la paire, son cours courant et
        # sa variation depuis le pas précédent (indicateur de change permanent).
        self.pair_rects = {}
        self._all_rects = {}
        x = inner.x
        for i, pair in enumerate(FX.PAIRS):
            rect = pygame.Rect(x, y, 108, 38)
            sel = i == self.pair_idx
            sp = FX.spot(m, pair)
            chg = FX.change_pct(m, pair, 1)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            spot_col = self._flash.tick(("fx", pair), sp, config.COL_UP, config.COL_DOWN, config.COL_TEXT)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, pair, (rect.x + 6, rect.y + 3), fonts.tiny(bold=True),
                              config.COL_CYAN if sel else config.COL_TEXT)
            widgets.draw_text(surf, f"{sp:.4f}" if sp else "—", (rect.x + 6, rect.y + 20),
                              fonts.tiny(bold=True), spot_col)
            widgets.draw_text(surf, f"{chg:+.2f}%", (rect.right - 6, rect.y + 20),
                              fonts.tiny(bold=True), ccol, align="right")
            self.pair_rects[i] = rect
            fk = ("pair", i)
            self._all_rects[fk] = rect
            keynav.draw_focus_ring(surf, rect, self.focus == fk)
            x += 114
            if x + 114 > inner.right:
                x = inner.x
                y += 42
        y += 48

        widgets.draw_text(surf, _L("Sens (long = pari sur hausse de la devise de base)",
                          "Direction (long = bet on base currency rising)"),
                          (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.dir_rects = {}
        x = inner.x
        for i, label in enumerate(("LONG", "SHORT")):
            rect = pygame.Rect(x, y, 90, 28)
            sel = i == self.dir_idx
            col = config.COL_UP if i == 0 else config.COL_DOWN
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, col if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, label, rect.center, fonts.small(bold=True),
                              col if sel else config.COL_TEXT, align="center")
            self.dir_rects[i] = rect
            fk = ("dir", i)
            self._all_rects[fk] = rect
            keynav.draw_focus_ring(surf, rect, self.focus == fk)
            x += 100
        y += 40

        widgets.draw_text(surf, _L("Notionnel", "Notional"), (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.notional_minus_btn = pygame.Rect(inner.x, y, 32, 28)
        self.notional_plus_btn = pygame.Rect(inner.x + 180, y, 32, 28)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.notional_minus_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self.notional_minus_btn, 1, border_radius=4)
        widgets.draw_text(surf, "-", self.notional_minus_btn.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        self._all_rects["notional:minus"] = self.notional_minus_btn
        keynav.draw_focus_ring(surf, self.notional_minus_btn, self.focus == "notional:minus")
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.notional_plus_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self.notional_plus_btn, 1, border_radius=4)
        widgets.draw_text(surf, "+", self.notional_plus_btn.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        self._all_rects["notional:plus"] = self.notional_plus_btn
        keynav.draw_focus_ring(surf, self.notional_plus_btn, self.focus == "notional:plus")
        widgets.draw_text(surf, widgets.format_money(self.notional, cur), (inner.x + 42, y + 4),
                          fonts.small(bold=True), config.COL_TEXT)
        y += 40

        pair = self._pair()
        q = FX.quote_spot(m, pair)
        if q.get("ok"):
            widgets.draw_text(surf, f"{pair} spot {q['spot']:.4f} (vol {q['vol']*100:.0f}%)",
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 24
        self.spot_btn = pygame.Rect(inner.x, y, 200, 32)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.spot_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self.spot_btn, 1, border_radius=4)
        widgets.draw_text(surf, _L("OUVRIR SPOT", "OPEN SPOT"), self.spot_btn.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
        self._all_rects["spot"] = self.spot_btn
        keynav.draw_focus_ring(surf, self.spot_btn, self.focus == "spot")
        y += 46

        widgets.draw_text(surf, _L("Tenor forward (mois)", "Forward tenor (months)"), (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.tenor_rects = {}
        x = inner.x
        for i, tenor in enumerate(FX.FORWARD_TENORS):
            rect = pygame.Rect(x, y, 70, 26)
            sel = i == self.tenor_idx
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, f"{tenor}m", rect.center, fonts.tiny(bold=True),
                              config.COL_CYAN if sel else config.COL_TEXT, align="center")
            self.tenor_rects[i] = rect
            fk = ("tenor", i)
            self._all_rects[fk] = rect
            keynav.draw_focus_ring(surf, rect, self.focus == fk)
            x += 76
        y += 36

        if fwd_ok:
            self.forward_btn = pygame.Rect(inner.x, y, 200, 32)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.forward_btn, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER, self.forward_btn, 1, border_radius=4)
            widgets.draw_text(surf, _L("VERROUILLER FORWARD", "LOCK FORWARD"), self.forward_btn.center, fonts.small(bold=True),
                              config.COL_AMBER, align="center")
            self._all_rects["forward"] = self.forward_btn
            keynav.draw_focus_ring(surf, self.forward_btn, self.focus == "forward")
        else:
            g = FX.FORWARD_MIN_GRADE
            grade_label = config.GRADES[g] if g < len(config.GRADES) else str(g)
            widgets.draw_text(surf, _L(f"⊘ Forward débloqué au grade {grade_label}.", f"⊘ Forward unlocked at {grade_label} grade."),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            self.forward_btn = None

        # ---- graphe du taux de la paire sélectionnée (droite, haut) ----
        self._draw_fx_graph(surf, pygame.Rect(540, 110, config.SCREEN_WIDTH - 580, 232))

        # ---- positions en cours (droite, bas) ----
        pos_rect = pygame.Rect(540, 354, config.SCREEN_WIDTH - 580, 176)
        pinner = widgets.draw_panel(surf, pos_rect, _L("Positions en cours", "Open positions"), config.COL_UP)
        yy = pinner.y
        self.close_rects = {}
        spot_hold = FX.holdings(p, m)
        if not spot_hold:
            widgets.draw_text(surf, _L("Aucune position spot ouverte.", "No open spot position."), (pinner.x, yy),
                              fonts.small(), config.COL_TEXT_DIM)
            yy += 26
        else:
            for h in spot_hold:
                col = config.COL_UP if h["pnl"] >= 0 else config.COL_DOWN
                spot_col = self._flash.tick(("fx_pos", h["pair"], h["entry_rate"], h["notional"]), h["spot"],
                                            config.COL_UP, config.COL_DOWN, config.COL_TEXT)
                widgets.draw_text(surf, f"{h['direction'].upper()} {h['pair']} · "
                                        f"{widgets.format_money(h['notional'], cur)}",
                                  (pinner.x, yy), fonts.small(bold=True), config.COL_TEXT)
                widgets.draw_text(surf, _L(f"entrée {h['entry_rate']:.4f} → ", f"entry {h['entry_rate']:.4f} → "),
                                  (pinner.x, yy + 18), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"{h['spot']:.4f}",
                                  (pinner.x + 172, yy + 18), fonts.tiny(), spot_col)
                widgets.draw_text(surf, f" · P&L {widgets.format_money(h['pnl'], cur)}",
                                  (pinner.x + 240, yy + 18), fonts.tiny(), col)
                close_rect = pygame.Rect(pinner.right - 90, yy, 86, 30)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, close_rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_DOWN, close_rect, 1, border_radius=4)
                widgets.draw_text(surf, _L("FERMER", "CLOSE"), close_rect.center, fonts.tiny(bold=True),
                                  config.COL_DOWN, align="center")
                self.close_rects[h["id"]] = close_rect
                fk = ("close", h["id"])
                self._all_rects[fk] = close_rect
                keynav.draw_focus_ring(surf, close_rect, self.focus == fk)
                yy += 42

        yy += 10
        widgets.draw_text(surf, _L("Forwards en cours", "Open forwards"), (pinner.x, yy), fonts.small(bold=True), config.COL_AMBER)
        yy += 24
        fwd_hold = FX.forward_holdings(p, m)
        if not fwd_hold:
            widgets.draw_text(surf, _L("Aucun forward en cours.", "No open forward."), (pinner.x, yy),
                              fonts.small(), config.COL_TEXT_DIM)
        else:
            for h in fwd_hold:
                widgets.draw_text(surf, f"{h['direction'].upper()} {h['pair']} {h['tenor_months']}m · "
                                        f"{widgets.format_money(h['notional'], cur)}",
                                  (pinner.x, yy), fonts.small(bold=True), config.COL_TEXT)
                widgets.draw_text(surf, _L(f"verrouillé {h['locked_rate']:.4f} · spot {h['spot']:.4f} · "
                                        f"{h['steps_left']} pas restants",
                                        f"locked {h['locked_rate']:.4f} · spot {h['spot']:.4f} · "
                                        f"{h['steps_left']} steps left"),
                                  (pinner.x, yy + 18), fonts.tiny(), config.COL_TEXT_DIM)
                yy += 42

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", _L("paire/sens", "pair/dir")), (_L("ENTRÉE", "ENTER"), _L("ouvrir", "open"))])
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
