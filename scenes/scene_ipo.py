"""
scene_ipo.py — Desk d'IPO : introductions en bourse de sociétés privées
fictives. Le joueur souscrit une allocation avant cotation (risque de
sursouscription -> allocation partielle), puis le pop/flop du premier jour
de cotation est réglé par core/ipo.py (evaluate_listings, appelé ailleurs
dans le câblage central). Ouvert via IPO.
"""
import pygame

from core import config, unlocks
from core import ipo as IPO
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, keynav, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


DEFAULT_AMOUNT = 50_000.0


class IPOScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.amount_str = f"{DEFAULT_AMOUNT:.0f}"
        self.amount_focus = False
        self._t = 0.0
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._subscribe_rects = {}
        self._decline_rects = {}
        self._amount_rect = None
        self._all_rects = {}
        self.focus = None
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       _L("TUTO", "GUIDE"), config.COL_CYAN)

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "ipo")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _amount(self):
        try:
            return float(self.amount_str)
        except ValueError:
            return 0.0

    def _activate_focus(self):
        key = self.focus
        if key is None or not isinstance(key, tuple):
            return
        p = self.app.gs.player
        market = self.app.ensure_market()
        if key[0] == "sub":
            amount = self._amount()
            if amount <= 0:
                self.msg = _L("Montant invalide.", "Invalid amount.")
                return
            res = IPO.subscribe(p, key[1], amount, market)
            if res["ok"]:
                cur = self._cur()
                self.msg = (_L(f"Souscrit : {widgets.format_money(res['allocated_cash'], cur)} alloués "
                            f"({res['shares']:.0f} actions {res['offer']['ticker']}), "
                            f"remboursé {widgets.format_money(res['refund'], cur)}.",
                            f"Subscribed: {widgets.format_money(res['allocated_cash'], cur)} allocated "
                            f"({res['shares']:.0f} shares {res['offer']['ticker']}), "
                            f"refunded {widgets.format_money(res['refund'], cur)}."))
                if not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)
            else:
                reasons = {"cash": _L("trésorerie insuffisante.", "insufficient cash."),
                           "offer": _L("offre introuvable.", "offer not found."),
                           "amount": _L("montant invalide.", "invalid amount.")}
                self.msg = _L(f"Refusé ({reasons.get(res['reason'], res['reason'])}).", f"Rejected ({reasons.get(res['reason'], res['reason'])}).")
        elif key[0] == "decline":
            IPO.decline(p, key[1])

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.amount_focus:
                    self.amount_focus = False
                    return
                self.app.scenes.back(self.return_to)
                return
            if self.amount_focus:
                if event.key == pygame.K_BACKSPACE:
                    self.amount_str = self.amount_str[:-1]
                    return
                if event.key in (pygame.K_RETURN, pygame.K_TAB):
                    self.amount_focus = False
                    return
                if event.unicode and (event.unicode.isdigit() or event.unicode == "."):
                    self.amount_str += event.unicode
                    return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="ipo", return_to="ipo")
            return
        if not self._can():
            return
        if event.type == pygame.KEYDOWN and not self.amount_focus:
            self.focus, activate = keynav.grid_nav(event, self._all_rects, self.focus)
            if activate:
                self._activate_focus()
                return
            if event.key in keynav.DIRECTIONS:
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._amount_rect and self._amount_rect.collidepoint(event.pos):
                self.amount_focus = True
                return
            self.amount_focus = False
            p = self.app.gs.player
            market = self.app.ensure_market()
            for oid, rect in self._subscribe_rects.items():
                if rect.collidepoint(event.pos):
                    amount = self._amount()
                    if amount <= 0:
                        self.msg = _L("Montant invalide.", "Invalid amount.")
                        return
                    res = IPO.subscribe(p, oid, amount, market)
                    if res["ok"]:
                        cur = self._cur()
                        self.msg = (_L(f"Souscrit : {widgets.format_money(res['allocated_cash'], cur)} alloués "
                                    f"({res['shares']:.0f} actions {res['offer']['ticker']}), "
                                    f"remboursé {widgets.format_money(res['refund'], cur)}.",
                                    f"Subscribed: {widgets.format_money(res['allocated_cash'], cur)} allocated "
                                    f"({res['shares']:.0f} shares {res['offer']['ticker']}), "
                                    f"refunded {widgets.format_money(res['refund'], cur)}."))
                        if not p.hardcore:
                            self.app.gs.save(config.AUTOSAVE_SLOT)
                    else:
                        reasons = {"cash": _L("trésorerie insuffisante.", "insufficient cash."),
                                   "offer": _L("offre introuvable.", "offer not found."),
                                   "amount": _L("montant invalide.", "invalid amount.")}
                        self.msg = _L(f"Refusé ({reasons.get(res['reason'], res['reason'])}).", f"Rejected ({reasons.get(res['reason'], res['reason'])}).")
                    return
            for oid, rect in self._decline_rects.items():
                if rect.collidepoint(event.pos):
                    IPO.decline(p, oid)
                    return

    def update(self, dt):
        self._t += dt
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("DESK D'IPO — INTRODUCTIONS EN BOURSE", "IPO DESK — PUBLIC LISTINGS"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        p = self.app.gs.player
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "ipo")
            widgets.draw_text(surf, _L(f"⊘ Desk d'IPO débloqué au grade {config.GRADES[g]}.", f"⊘ IPO desk unlocked at {config.GRADES[g]} grade."),
                              (42, 74), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return
        widgets.draw_text(surf, _L("Souscrivez une allocation avant cotation : en cas de sursouscription, "
                                "l'allocation reçue est partielle (le surplus est remboursé). ",
                                "Subscribe to an allocation before listing: if oversubscribed, "
                                "the received allocation is partial (the surplus is refunded). ") + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        market = self.app.ensure_market()
        cur = self._cur()
        self._subscribe_rects = {}
        self._decline_rects = {}
        self._all_rects = {}

        # ---- montant à souscrire ----
        amt_y = 104
        widgets.draw_text(surf, _L("Montant à souscrire :", "Amount to subscribe:"), (40, amt_y + 6), fonts.small(), config.COL_TEXT)
        self._amount_rect = pygame.Rect(230, amt_y, 160, 28)
        pygame.draw.rect(surf, config.COL_PANEL, self._amount_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.amount_focus else config.COL_BORDER,
                          self._amount_rect, 1, border_radius=4)
        cursor = "_" if self.amount_focus and int(self._t * 2) % 2 == 0 else ""
        widgets.draw_text(surf, (self.amount_str or "0") + cursor, (self._amount_rect.x + 8, self._amount_rect.y + 5),
                          fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, cur, (self._amount_rect.right + 8, amt_y + 6), fonts.small(), config.COL_TEXT_DIM)

        top = 142
        # ---- offres en attente ----
        offers = list(p.ipo_offers)
        off_h = 50 + len(offers) * 70 if offers else 50
        off_h = min(off_h, 260)
        off_panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, off_h)
        inner = widgets.draw_panel(surf, off_panel, _L(f"Offres en attente ({len(offers)})", f"Pending offers ({len(offers)})"), config.COL_CYAN)
        if not offers:
            widgets.draw_text(surf, _L("Aucune offre en attente. Patientez, le temps avance en direct.", "No pending offer. Wait, time advances live."),
                              (inner.x, inner.y + 4), fonts.small(), config.COL_TEXT_DIM)
        else:
            y = inner.y
            for o in offers:
                row = pygame.Rect(inner.x, y, inner.w, 64)
                pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_CYAN, row, 1, border_radius=4)
                widgets.draw_text(surf, f"#{o['id']} {o['company_name']} ({o['ticker']}) · {o['sector']}",
                                  (row.x + 12, row.y + 6), fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, _L(f"Fourchette : {o['price_min']:.2f}–{o['price_max']:.2f} {cur}  ·  "
                                        f"Sursouscription estimée : {o['demand_multiple']:.2f}x  ·  "
                                        f"Cotation dans {max(0, o['listing_step'] - market.step_count)} pas",
                                        f"Range: {o['price_min']:.2f}–{o['price_max']:.2f} {cur}  ·  "
                                        f"Estimated oversubscription: {o['demand_multiple']:.2f}x  ·  "
                                        f"Listing in {max(0, o['listing_step'] - market.step_count)} steps"),
                                  (row.x + 12, row.y + 26), fonts.tiny(), config.COL_TEXT)
                sent_col = {"bullish": config.COL_UP, "bearish": config.COL_DOWN,
                            "neutral": config.COL_TEXT_DIM}.get(o["sentiment"], config.COL_TEXT_DIM)
                widgets.draw_text(surf, _L(f"Sentiment marché : {o['sentiment']}", f"Market sentiment: {o['sentiment']}"),
                                  (row.x + 12, row.y + 44), fonts.tiny(), sent_col)
                sub = pygame.Rect(row.right - 196, row.y + 16, 90, 30)
                dec = pygame.Rect(row.right - 100, row.y + 16, 90, 30)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, sub, border_radius=4)
                pygame.draw.rect(surf, config.COL_UP, sub, 1, border_radius=4)
                widgets.draw_text(surf, _L("SOUSCRIRE", "SUBSCRIBE"), sub.center, fonts.tiny(bold=True), config.COL_UP, align="center")
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, dec, border_radius=4)
                pygame.draw.rect(surf, config.COL_DOWN, dec, 1, border_radius=4)
                widgets.draw_text(surf, _L("DÉCLINER", "DECLINE"), dec.center, fonts.tiny(bold=True), config.COL_DOWN, align="center")
                self._subscribe_rects[o["id"]] = sub
                self._decline_rects[o["id"]] = dec
                sub_fk, dec_fk = ("sub", o["id"]), ("decline", o["id"])
                self._all_rects[sub_fk] = sub
                self._all_rects[dec_fk] = dec
                keynav.draw_focus_ring(surf, sub, self.focus == sub_fk)
                keynav.draw_focus_ring(surf, dec, self.focus == dec_fk)
                y += 70

        # ---- positions IPO en cours ----
        pos_top = off_panel.bottom + 10
        pos_panel = pygame.Rect(40, pos_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - pos_top)
        pinner = widgets.draw_panel(surf, pos_panel, _L("Positions IPO", "IPO positions"), config.COL_PRESTIGE)
        list_area = pygame.Rect(pinner.x - 6, pinner.y, pinner.w + 12, pinner.bottom - pinner.y - 4)
        self._list_rect = list_area
        hold = IPO.holdings(p, market)
        if not hold:
            widgets.draw_text(surf, _L("Aucune position IPO en cours.", "No IPO position in progress."),
                              (pinner.x, pinner.y + 4), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return

        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        ROW = 56
        for h in hold:
            visible = (list_area.top - ROW) < y < list_area.bottom
            if visible:
                row = pygame.Rect(pinner.x, y, pinner.w, ROW - 8)
                pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
                widgets.draw_text(surf, f"{h['company_name']} ({h['ticker']})",
                                  (row.x + 12, row.y + 6), fonts.small(bold=True), config.COL_TEXT)
                widgets.draw_text(surf, _L(f"{h['shares']:.0f} actions · coût {widgets.format_money(h['cost_basis'], cur)} ", f"{h['shares']:.0f} shares · cost {widgets.format_money(h['cost_basis'], cur)} ") +
                                        f"@ {h['issue_price']:.2f} {cur}",
                                  (row.x + 12, row.y + 26), fonts.tiny(), config.COL_TEXT_DIM)
                status = _L("Cotation imminente", "Listing imminent") if h["listed"] else _L(f"Cotation dans {h['steps_left']} pas", f"Listing in {h['steps_left']} steps")
                widgets.draw_badge(surf, status, (row.right - 200, row.y + 14),
                                   accent=config.COL_UP if h["listed"] else config.COL_TEXT_DIM)
            y += ROW
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - list_area.y
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, pos_panel, list_area, self.scroll, self._max_scroll, content_h)

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", _L("naviguer", "navigate")), (_L("ENTRÉE", "ENTER"), _L("souscrire", "subscribe"))])
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
