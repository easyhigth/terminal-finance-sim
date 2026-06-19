"""
scene_fx.py — Desk FX : trading de paires de devises au comptant (spot) et à
terme (forward).

Le joueur choisit une paire, un sens (long/short), un notionnel, puis ouvre
une position spot (mark-to-market) ou un forward (verrouillé, réglé à
échéance — débloqué à partir d'un grade plus élevé). Logique de
cotation/dénouement dans core/fx.py. Calqué sur scenes/scene_options.py.
"""
import pygame

from core import config, unlocks
from core import fx as FX
from core.scene_manager import Scene
from ui import fonts, widgets

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
                                       "📘 TUTO", config.COL_CYAN)
        self.pair_rects = {}
        self.dir_rects = {}
        self.tenor_rects = {}
        self.notional_minus_btn = None
        self.notional_plus_btn = None
        self.spot_btn = None
        self.forward_btn = None
        self.close_rects = {}

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "fx")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _pair(self):
        return FX.PAIRS[self.pair_idx % len(FX.PAIRS)]

    def _direction(self):
        return "long" if self.dir_idx == 0 else "short"

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="fx", return_to="fx")
            return
        if not self._can():
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
                self.msg = (f"Position spot {direction.upper()} {pair} ouverte "
                            f"(notionnel {widgets.format_money(self.notional, self._cur())})."
                            if r["ok"] else f"Refusé ({r['reason']}).")
                if r["ok"] and not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)
                return
            if self.forward_btn and self.forward_btn.collidepoint(event.pos):
                pair = self._pair()
                direction = self._direction()
                tenor = FX.FORWARD_TENORS[self.tenor_idx % len(FX.FORWARD_TENORS)]
                r = FX.open_forward(p, m, pair, direction, self.notional, tenor)
                self.msg = (f"Forward {direction.upper()} {pair} {tenor}m verrouillé."
                            if r["ok"] else f"Refusé ({r['reason']}).")
                if r["ok"] and not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)
                return
            for pid, rect in self.close_rects.items():
                if rect.collidepoint(event.pos):
                    r = FX.close_spot(p, m, pid)
                    if r["ok"]:
                        self.msg = f"Position fermée, P&L {widgets.format_money(r['pnl'], self._cur())}."
                        if not p.hardcore:
                            self.app.gs.save(config.AUTOSAVE_SLOT)
                    return

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "DESK FX — SPOT / FORWARD", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "fx")
            widgets.draw_text(surf, f"⊘ Desk FX débloqué au grade {config.GRADES[g]}.",
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return
        widgets.draw_text(surf, "Tradez une paire de devises au comptant ou à terme. " + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        m, p = self.app.market, self.app.gs.player
        cur = self._cur()
        fwd_ok = FX.forward_unlocked(p)

        # ---- cotation / ouverture (gauche) ----
        quote_rect = pygame.Rect(40, 110, 460, 420)
        inner = widgets.draw_panel(surf, quote_rect, "Nouvelle position", config.COL_CYAN)
        y = inner.y

        widgets.draw_text(surf, "Paire", (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.pair_rects = {}
        x = inner.x
        for i, pair in enumerate(FX.PAIRS):
            rect = pygame.Rect(x, y, 96, 26)
            sel = i == self.pair_idx
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, pair, rect.center, fonts.tiny(bold=True),
                              config.COL_CYAN if sel else config.COL_TEXT, align="center")
            self.pair_rects[i] = rect
            x += 102
            if x + 102 > inner.right:
                x = inner.x
                y += 30
        y += 36

        widgets.draw_text(surf, "Sens (long = pari sur hausse de la devise de base)",
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
            x += 100
        y += 40

        widgets.draw_text(surf, "Notionnel", (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 22
        self.notional_minus_btn = pygame.Rect(inner.x, y, 32, 28)
        self.notional_plus_btn = pygame.Rect(inner.x + 180, y, 32, 28)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.notional_minus_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self.notional_minus_btn, 1, border_radius=4)
        widgets.draw_text(surf, "-", self.notional_minus_btn.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.notional_plus_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, self.notional_plus_btn, 1, border_radius=4)
        widgets.draw_text(surf, "+", self.notional_plus_btn.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
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
        widgets.draw_text(surf, "OUVRIR SPOT", self.spot_btn.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
        y += 46

        widgets.draw_text(surf, "Tenor forward (mois)", (inner.x, y), fonts.small(), config.COL_TEXT)
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
            x += 76
        y += 36

        if fwd_ok:
            self.forward_btn = pygame.Rect(inner.x, y, 200, 32)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self.forward_btn, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER, self.forward_btn, 1, border_radius=4)
            widgets.draw_text(surf, "VERROUILLER FORWARD", self.forward_btn.center, fonts.small(bold=True),
                              config.COL_AMBER, align="center")
        else:
            g = FX.FORWARD_MIN_GRADE
            grade_label = config.GRADES[g] if g < len(config.GRADES) else str(g)
            widgets.draw_text(surf, f"⊘ Forward débloqué au grade {grade_label}.",
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            self.forward_btn = None

        # ---- positions en cours (droite) ----
        pos_rect = pygame.Rect(540, 110, config.SCREEN_WIDTH - 580, 420)
        pinner = widgets.draw_panel(surf, pos_rect, "Positions en cours", config.COL_UP)
        yy = pinner.y
        self.close_rects = {}
        spot_hold = FX.holdings(p, m)
        if not spot_hold:
            widgets.draw_text(surf, "Aucune position spot ouverte.", (pinner.x, yy),
                              fonts.small(), config.COL_TEXT_DIM)
            yy += 26
        else:
            for h in spot_hold:
                col = config.COL_UP if h["pnl"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{h['direction'].upper()} {h['pair']} · "
                                        f"{widgets.format_money(h['notional'], cur)}",
                                  (pinner.x, yy), fonts.small(bold=True), config.COL_TEXT)
                widgets.draw_text(surf, f"entrée {h['entry_rate']:.4f} → {h['spot']:.4f} · "
                                        f"P&L {widgets.format_money(h['pnl'], cur)}",
                                  (pinner.x, yy + 18), fonts.tiny(), col)
                close_rect = pygame.Rect(pinner.right - 90, yy, 86, 30)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, close_rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_DOWN, close_rect, 1, border_radius=4)
                widgets.draw_text(surf, "FERMER", close_rect.center, fonts.tiny(bold=True),
                                  config.COL_DOWN, align="center")
                self.close_rects[h["id"]] = close_rect
                yy += 42

        yy += 10
        widgets.draw_text(surf, "Forwards en cours", (pinner.x, yy), fonts.small(bold=True), config.COL_AMBER)
        yy += 24
        fwd_hold = FX.forward_holdings(p, m)
        if not fwd_hold:
            widgets.draw_text(surf, "Aucun forward en cours.", (pinner.x, yy),
                              fonts.small(), config.COL_TEXT_DIM)
        else:
            for h in fwd_hold:
                widgets.draw_text(surf, f"{h['direction'].upper()} {h['pair']} {h['tenor_months']}m · "
                                        f"{widgets.format_money(h['notional'], cur)}",
                                  (pinner.x, yy), fonts.small(bold=True), config.COL_TEXT)
                widgets.draw_text(surf, f"verrouillé {h['locked_rate']:.4f} · spot {h['spot']:.4f} · "
                                        f"{h['steps_left']} pas restants",
                                  (pinner.x, yy + 18), fonts.tiny(), config.COL_TEXT_DIM)
                yy += 42

        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
