"""
scene_calendar.py — Calendrier macro : évènements économiques programmés
(décision de banque centrale, inflation, emploi, croissance) sur lesquels le
joueur peut placer un pari directionnel en cash avant la résolution. Marché
de paris autonome réglé par core/macrocal.py (resolve_due_events, appelé
ailleurs dans le câblage central). Ouvert via CALENDAR.
"""
import pygame

from core import config, unlocks
from core import macrocal as MACRO
from core.scene_manager import Scene
from ui import fonts, widgets

DEFAULT_STAKE = 5_000.0

_OUTCOME_COLORS = {
    "positif": config.COL_UP,
    "neutre": config.COL_TEXT_DIM,
    "négatif": config.COL_DOWN,
}


class CalendarScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.stake_str = f"{DEFAULT_STAKE:.0f}"
        self.stake_focus = False
        self.selected_event = None
        self.selected_outcome = None
        self._t = 0.0
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._select_rects = {}
        self._outcome_rects = {}
        self._bet_rect = None
        self._stake_rect = None
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "TUTO", config.COL_CYAN)

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "calendar")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _stake(self):
        try:
            return float(self.stake_str)
        except ValueError:
            return 0.0

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.stake_focus:
                    self.stake_focus = False
                    return
                self.app.scenes.back(self.return_to)
                return
            if self.stake_focus:
                if event.key == pygame.K_BACKSPACE:
                    self.stake_str = self.stake_str[:-1]
                    return
                if event.key in (pygame.K_RETURN, pygame.K_TAB):
                    self.stake_focus = False
                    return
                if event.unicode and (event.unicode.isdigit() or event.unicode == "."):
                    self.stake_str += event.unicode
                    return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="calendar", return_to="calendar")
            return
        if not self._can():
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._stake_rect and self._stake_rect.collidepoint(event.pos):
                self.stake_focus = True
                return
            self.stake_focus = False
            p = self.app.gs.player
            for eid, rect in self._select_rects.items():
                if rect.collidepoint(event.pos):
                    self.selected_event = eid
                    self.selected_outcome = None
                    return
            for outcome, rect in self._outcome_rects.items():
                if rect.collidepoint(event.pos):
                    self.selected_outcome = outcome
                    return
            if self._bet_rect and self._bet_rect.collidepoint(event.pos):
                if self.selected_event is None:
                    self.msg = "Sélectionnez un évènement."
                    return
                if self.selected_outcome is None:
                    self.msg = "Sélectionnez une issue (positif/neutre/négatif)."
                    return
                stake = self._stake()
                if stake <= 0:
                    self.msg = "Mise invalide."
                    return
                res = MACRO.place_bet(p, self.selected_event, self.selected_outcome, stake)
                if res["ok"]:
                    cur = self._cur()
                    self.msg = (f"Pari placé : {widgets.format_money(stake, cur)} sur "
                                f"« {res['bet']['outcome']} » (x{res['bet']['multiplier']:.2f}).")
                    if not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
                else:
                    reasons = {"cash": "trésorerie insuffisante.", "event": "évènement introuvable.",
                               "stake": "mise invalide.", "outcome": "issue invalide."}
                    self.msg = f"Refusé ({reasons.get(res['reason'], res['reason'])})."
                return

    def update(self, dt):
        self._t += dt
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "CALENDRIER MACRO — ÉVÈNEMENTS ÉCONOMIQUES", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        p = self.app.gs.player
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "calendar")
            widgets.draw_text(surf, f"⊘ Calendrier macro débloqué au grade {config.GRADES[g]}.",
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return
        widgets.draw_text(surf, "Pariez sur l'issue (perçue par le marché) d'un évènement programmé : "
                                "le multiplicateur dépend de la probabilité a priori. " + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        market = self.app.ensure_market()
        cur = self._cur()
        self._select_rects = {}
        self._outcome_rects = {}

        # ---- mise + sélection d'issue ----
        ctrl_y = 104
        widgets.draw_text(surf, "Mise :", (40, ctrl_y + 6), fonts.small(), config.COL_TEXT)
        self._stake_rect = pygame.Rect(95, ctrl_y, 140, 28)
        pygame.draw.rect(surf, config.COL_PANEL, self._stake_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.stake_focus else config.COL_BORDER,
                          self._stake_rect, 1, border_radius=4)
        cursor = "_" if self.stake_focus and int(self._t * 2) % 2 == 0 else ""
        widgets.draw_text(surf, (self.stake_str or "0") + cursor, (self._stake_rect.x + 8, self._stake_rect.y + 5),
                          fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, cur, (self._stake_rect.right + 8, ctrl_y + 6), fonts.small(), config.COL_TEXT_DIM)

        ox = self._stake_rect.right + 60
        for outcome in MACRO.OUTCOMES:
            rect = pygame.Rect(ox, ctrl_y, 100, 28)
            selected = self.selected_outcome == outcome
            col = _OUTCOME_COLORS.get(outcome, config.COL_TEXT_DIM)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if selected else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, col, rect, 2 if selected else 1, border_radius=4)
            widgets.draw_text(surf, outcome.upper(), rect.center, fonts.tiny(bold=True), col, align="center")
            self._outcome_rects[outcome] = rect
            ox += 110

        self._bet_rect = pygame.Rect(ox + 20, ctrl_y, 120, 28)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._bet_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, self._bet_rect, 1, border_radius=4)
        widgets.draw_text(surf, "PARIER", self._bet_rect.center, fonts.small(bold=True), config.COL_AMBER, align="center")
        # les DEUX issues chiffrées AVANT de parier : gain si l'issue choisie
        # sort (mise × multiplicateur - mise), perte sinon (la mise entière)
        if self.selected_event is not None and self.selected_outcome:
            mult = MACRO._multiplier_for(self.selected_event, self.selected_outcome)
            stake = self._stake()
            if mult and stake > 0:
                win = stake * mult - stake
                widgets.draw_text(surf, widgets.fit_text(
                    f"Si « {self.selected_outcome} » sort : +{win:,.0f} · sinon : "
                    f"-{stake:,.0f} (x{mult:.2f})", fonts.tiny(),
                    config.SCREEN_WIDTH - self._bet_rect.right - 40),
                    (self._bet_rect.right + 12, ctrl_y + 8), fonts.tiny(),
                    config.COL_WARN)

        top = 142
        # ---- évènements programmés ----
        events = list(p.macro_events)
        ev_h = 50 + len(events) * 70 if events else 50
        ev_h = min(ev_h, 260)
        ev_panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, ev_h)
        inner = widgets.draw_panel(surf, ev_panel, f"Évènements programmés ({len(events)})", config.COL_CYAN)
        if not events:
            widgets.draw_text(surf, "Aucun évènement programmé. Patientez, le temps avance en direct.",
                              (inner.x, inner.y + 4), fonts.small(), config.COL_TEXT_DIM)
        else:
            y = inner.y
            for e in events:
                row = pygame.Rect(inner.x, y, inner.w, 64)
                selected = self.selected_event == e["id"]
                pygame.draw.rect(surf, config.COL_PANEL_HEAD if selected else config.COL_PANEL, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_CYAN, row, 2 if selected else 1, border_radius=4)
                widgets.draw_text(surf, f"#{e['id']} {e['event_type']}",
                                  (row.x + 12, row.y + 6), fonts.small(bold=True), config.COL_AMBER)
                probs = e["probabilities"]
                prob_str = "  ".join(f"{o}: {probs[o]*100:.0f}%" for o in MACRO.OUTCOMES)
                widgets.draw_text(surf, f"Consensus : {e['consensus']}  ·  {prob_str}  ·  "
                                        f"Résolution dans {max(0, e['resolve_step'] - market.step_count)} pas",
                                  (row.x + 12, row.y + 26), fonts.tiny(), config.COL_TEXT)
                n_bets = len(MACRO.pending_bets_for(p, e["id"]))
                widgets.draw_text(surf, f"Paris en cours sur cet évènement : {n_bets}",
                                  (row.x + 12, row.y + 44), fonts.tiny(), config.COL_TEXT_DIM)
                sel = pygame.Rect(row.right - 130, row.y + 16, 110, 30)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, sel, border_radius=4)
                pygame.draw.rect(surf, config.COL_CYAN, sel, 1, border_radius=4)
                widgets.draw_text(surf, "SÉLECTIONNER", sel.center, fonts.tiny(bold=True), config.COL_CYAN, align="center")
                self._select_rects[e["id"]] = sel
                y += 70

        # ---- paris en cours + historique résolu ----
        pos_top = ev_panel.bottom + 10
        pos_panel = pygame.Rect(40, pos_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - pos_top)
        pinner = widgets.draw_panel(surf, pos_panel, "Paris en cours & historique", config.COL_PRESTIGE)
        list_area = pygame.Rect(pinner.x - 6, pinner.y, pinner.w + 12, pinner.bottom - pinner.y - 4)
        self._list_rect = list_area

        rows = []
        for b in p.macro_bets:
            ev = MACRO.find_event(p, b["event_id"])
            label = ev["event_type"] if ev else f"Évènement #{b['event_id']}"
            rows.append(("pending", f"{label} — pari « {b['outcome']} » : "
                                     f"{widgets.format_money(b['stake'], cur)} (x{b['multiplier']:.2f})"))
        for h in reversed(p.macro_bet_history):
            for br in h["bets_resolved"]:
                status = "GAGNÉ" if br["won"] else "PERDU"
                rows.append(("won" if br["won"] else "lost",
                             f"{h['event']['event_type']} — issue réelle « {h['actual_outcome']} » · "
                             f"pari « {br['outcome']} » : {status} "
                             f"({widgets.format_money(br['payout'], cur)})"))

        if not rows:
            widgets.draw_text(surf, "Aucun pari en cours ni résolu.",
                              (pinner.x, pinner.y + 4), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return

        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        ROW = 36
        row_colors = {"pending": config.COL_TEXT_DIM, "won": config.COL_UP, "lost": config.COL_DOWN}
        for kind, text in rows:
            visible = (list_area.top - ROW) < y < list_area.bottom
            if visible:
                widgets.draw_text(surf, text, (pinner.x + 4, y + 4), fonts.tiny(), row_colors.get(kind, config.COL_TEXT))
            y += ROW
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - list_area.y
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, pos_panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
