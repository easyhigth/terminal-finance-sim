"""
scene_journal.py — Journal de trading exploitable.

Vue riche des trades passés : recherche, filtres par classe/sens/régime,
tri, statistiques de performance (discipline, win rate, P&L total) et
actions rapides (reprendre un trade, ajouter une note). S'ouvre via la
commande TRADES/TJOURNAL du terminal ou depuis le hub PLUS.
"""
import pygame

from core import config, journal as J
from core.scene_manager import Scene
from ui import fonts, keynav, widgets

ROW_H = 24
SORT_FIELDS = [("day", "JOUR"), ("asset_class", "CLASSE"), ("side", "SENS"),
                ("notional", "TAILLE"), ("realized", "P&L")]
ASSET_CHIPS = [None, "Action", "ETF", "Obligation", "Commodity", "Crypto"]
SIDE_CHIPS = [None, "achat", "vente", "short", "couverture"]


class TradeJournalScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.player = self.app.gs.player
        self.search = ""
        self.asset_filter = None
        self.side_filter = None
        self.sort_key = "day"
        self.sort_dir = -1
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._row_rects = {}
        self._note_rects = {}
        self._replicate_rects = {}
        self._asset_rects = {}
        self._side_rects = {}
        self._sort_rects = {}
        self._search_clear_rect = None
        self.row_cursor = 0
        self._rows = []
        self._note_active = None   # entrée en cours d'annotation (id)
        self._note_text = ""
        self._t = 0.0
        self.back_btn = widgets.Button(config.back_button_rect(200),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _filtered_sorted(self):
        entries = list(reversed(self.player.trade_journal))
        q = self.search.strip().lower()
        if q:
            entries = [e for e in entries
                       if q in e["key"].lower()
                       or q in e.get("label", "").lower()
                       or q in e.get("reason", "").lower()
                       or q in e.get("comment", "").lower()
                       or q in e.get("regime", "").lower()]
        if self.asset_filter:
            entries = [e for e in entries if e["asset_class"] == self.asset_filter]
        if self.side_filter:
            entries = [e for e in entries if e["side"] == self.side_filter]
        rev = self.sort_dir < 0
        if self.sort_key == "day":
            entries.sort(key=lambda e: e["day"], reverse=rev)
        elif self.sort_key == "asset_class":
            entries.sort(key=lambda e: e["asset_class"].lower(), reverse=rev)
        elif self.sort_key == "side":
            entries.sort(key=lambda e: e["side"].lower(), reverse=rev)
        elif self.sort_key == "notional":
            entries.sort(key=lambda e: e.get("notional", 0.0), reverse=rev)
        elif self.sort_key == "realized":
            entries.sort(key=lambda e: e["realized"] if e["realized"] is not None else -1e18,
                         reverse=rev)
        return entries

    def _cur(self):
        return config.CONTINENTS[self.player.continent]["currency"]

    def _toggle_sort(self, key):
        if self.sort_key == key:
            self.sort_dir *= -1
        else:
            self.sort_key = key
            self.sort_dir = -1

    def _start_note(self, entry):
        self._note_active = entry["id"]
        self._note_text = entry.get("comment", "") or entry.get("reason", "")

    def _save_note(self):
        if self._note_active is None:
            return
        J.annotate(self.player, self._note_active, comment=self._note_text)
        self._note_active = None
        self._note_text = ""

    def _replicate(self, entry):
        """Ouvre le Trading pré-filtré sur l'actif avec la quantité d'origine."""
        ticker = entry["key"]
        qty = entry["qty"]
        # on ne pré-remplit que pour les actions (autres classes gérées ailleurs)
        if entry["asset_class"] == "Action" and ticker and qty:
            self.app.pending_input = f"BUY {ticker} {int(qty)}"
        self.app.scenes.go("terminal")

    def handle_event(self, event):
        if self._note_active is not None:
            return self._handle_note_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.back(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._rows))
                if activate and self._rows:
                    self._start_note(self._rows[self.row_cursor])
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            for kind, rect in self._asset_rects.items():
                if rect.collidepoint(event.pos):
                    self.asset_filter = None if kind == self.asset_filter else kind
                    return
            for side, rect in self._side_rects.items():
                if rect.collidepoint(event.pos):
                    self.side_filter = None if side == self.side_filter else side
                    return
            for key, rect in self._sort_rects.items():
                if rect.collidepoint(event.pos):
                    self._toggle_sort(key)
                    return
            for eid, rect in self._replicate_rects.items():
                if rect.collidepoint(event.pos):
                    entry = J.get_entry(self.player, eid)
                    if entry:
                        self._replicate(entry)
                    return
            for eid, rect in self._note_rects.items():
                if rect.collidepoint(event.pos):
                    entry = J.get_entry(self.player, eid)
                    if entry:
                        self._start_note(entry)
                    return

    def _handle_note_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._note_active = None
                self._note_text = ""
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._save_note()
                return True
            if event.key == pygame.K_BACKSPACE:
                self._note_text = self._note_text[:-1]
                return True
            if event.unicode and event.unicode.isprintable():
                self._note_text += event.unicode
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            box = pygame.Rect(0, 0, 520, 140)
            box.center = self.app.screen.get_rect().center
            ok = pygame.Rect(box.x + 12, box.bottom - 38, 80, 28)
            cancel = pygame.Rect(ok.right + 10, box.bottom - 38, 80, 28)
            if ok.collidepoint(event.pos):
                self._save_note()
                return True
            if cancel.collidepoint(event.pos) or not box.collidepoint(event.pos):
                self._note_active = None
                self._note_text = ""
                return True
        return True

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "JOURNAL DE TRADING", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Filtrez, triez et reprenez vos trades passés. Cliquez ✎ pour annoter, ↻ pour répliquer.",
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)

        p = self.player
        cur = self._cur()
        top = config.content_top()
        x0 = 40
        mp = pygame.mouse.get_pos()

        # ---- statistiques ----
        stats = J.performance_stats(p, group_by="regime")
        disc = J.discipline_score(p)
        y_stat = top
        widgets.draw_text(surf, "DISCIPLINE :", (x0, y_stat), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        if disc is not None:
            widgets.draw_text(surf, f"{disc['score']:.0f}/100",
                              (x0 + 80, y_stat), fonts.small(bold=True), config.COL_AMBER)
        total_pnl = sum(g["total_pnl"] for g in stats)
        total_trades = sum(g["count"] for g in stats)
        wins = sum(g["wins"] for g in stats)
        win_rate = (wins / total_trades * 100) if total_trades else 0.0
        sx = x0 + 180
        widgets.draw_text(surf, f"Trades clôturés : {total_trades}  ·  Win rate : {win_rate:.0f}%  ·  P&L total :",
                          (sx, y_stat), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        pnl_col = config.COL_UP if total_pnl >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{total_pnl:+,.0f} {cur}",
                          (sx + 420, y_stat), fonts.small(bold=True), pnl_col)

        # ---- filtres ----
        fy = top + 26
        fx = x0
        self._asset_rects = {}
        widgets.draw_text(surf, "CLASSE :", (fx, fy + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        fx += 60
        for kind in ASSET_CHIPS:
            label = "TOUTES" if kind is None else kind
            w = max(50, fonts.tiny(bold=True).size(label)[0] + 12)
            r = pygame.Rect(fx, fy, w, 20)
            self._asset_rects[kind] = r
            active = self.asset_filter == kind
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            fx += w + 6

        fx = x0 + 500
        self._side_rects = {}
        widgets.draw_text(surf, "SENS :", (fx, fy + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        fx += 50
        for side in SIDE_CHIPS:
            label = "TOUS" if side is None else side.upper()
            w = max(50, fonts.tiny(bold=True).size(label)[0] + 12)
            r = pygame.Rect(fx, fy, w, 20)
            self._side_rects[side] = r
            active = self.side_filter == side
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            fx += w + 6

        # ---- recherche ----
        sry = fy + 30
        sr = pygame.Rect(x0, sry, 260, 24)
        pygame.draw.rect(surf, config.COL_PANEL, sr, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, sr, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        lbl = (self.search + cursor) if self.search else (cursor + "Rechercher (ticker, raison, commentaire…)")
        widgets.draw_text(surf, widgets.fit_text(lbl, fonts.small(), sr.w - 16),
                          (sr.x + 8, sr.y + 4), fonts.small(),
                          config.COL_TEXT if self.search else config.COL_TEXT_DIM)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(sr.right - 22, sr.y, 22, sr.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        # ---- tri ----
        tx = sr.right + 30
        self._sort_rects = {}
        widgets.draw_text(surf, "TRIER :", (tx, sry + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        tx += 56
        for key, label in SORT_FIELDS:
            active = self.sort_key == key
            arrow = (" ▲" if self.sort_dir > 0 else " ▼") if active else ""
            full = label + arrow
            w = max(50, fonts.tiny(bold=True).size(full)[0] + 12)
            r = pygame.Rect(tx, sry, w, 20)
            self._sort_rects[key] = r
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, full, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            tx += w + 6

        # ---- liste ----
        ltop = sry + 34
        ph = config.footer_y() - 8 - ltop
        panel = pygame.Rect(x0, ltop, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Trades", config.COL_CYAN)
        self._rows = self._filtered_sorted()
        self.row_cursor = min(self.row_cursor, len(self._rows) - 1) if self._rows else 0

        # en-têtes
        cols = [
            ("ID", inner.x, 50),
            ("JOUR", inner.x + 50, 50),
            ("ACTIF", inner.x + 100, 70),
            ("CLASSE", inner.x + 170, 80),
            ("SENS", inner.x + 250, 60),
            ("QTÉ", inner.x + 310, 60),
            ("PRIX", inner.x + 370, 80),
            ("P&L", inner.x + 450, 90),
            ("RÉGIME", inner.x + 540, 100),
            ("NOTE", inner.x + 640, inner.w - 640 - 120),
        ]
        for label, cx, _ in cols:
            widgets.draw_text(surf, label, (cx, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)

        list_area = pygame.Rect(inner.x - 6, inner.y + 22, inner.w + 12, inner.h - 26)
        self._list_rect = list_area
        self._replicate_rects = {}
        self._note_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y + 22 - self.scroll
        for i, e in enumerate(self._rows):
            if (list_area.top - ROW_H) < y < list_area.bottom:
                self._draw_row(surf, e, y, inner, mp, i == self.row_cursor)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = len(self._rows) * ROW_H
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)

        if self._note_active is not None:
            self._draw_note_dialog(surf)

    def _draw_row(self, surf, e, y, inner, mp, cursor=False):
        row_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H)
        if row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        keynav.draw_focus_ring(surf, row_rect, cursor)
        cur = self._cur()
        widgets.draw_text(surf, f"#{e['id']}", (inner.x, y), fonts.tiny(), config.COL_AMBER)
        widgets.draw_text(surf, f"j{e['day']}", (inner.x + 50, y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.fit_text(e['key'], fonts.small(bold=True), 68),
                          (inner.x + 100, y), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(e['asset_class'], fonts.tiny(), 78),
                          (inner.x + 170, y + 2), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, e['side'].upper(), (inner.x + 250, y), fonts.tiny(),
                          config.COL_UP if e['side'] == 'achat' else config.COL_DOWN)
        widgets.draw_text(surf, f"{e['qty']:g}", (inner.x + 310, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"{e['price']:.2f}", (inner.x + 370, y), fonts.small(), config.COL_TEXT)
        if e["realized"] is not None:
            pcol = config.COL_UP if e["realized"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{e['realized']:+,.0f}", (inner.x + 450, y),
                              fonts.small(bold=True), pcol)
        else:
            widgets.draw_text(surf, "—", (inner.x + 450, y), fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.fit_text(e.get("regime", ""), fonts.tiny(), 95),
                          (inner.x + 540, y + 2), fonts.tiny(), config.COL_TEXT_DIM)
        note = (e.get("comment") or e.get("reason") or "—")
        widgets.draw_text(surf, widgets.fit_text(note, fonts.tiny(), inner.w - 640 - 120),
                          (inner.x + 640, y + 2), fonts.tiny(), config.COL_TEXT_DIM)

        # actions
        ax = inner.right - 110
        rep = pygame.Rect(ax, y, 48, ROW_H - 4)
        self._replicate_rects[e["id"]] = rep
        hov = rep.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, rep, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, rep, 1, border_radius=3)
        widgets.draw_text(surf, "↻ TRADER", rep.center, fonts.tiny(bold=True), config.COL_CYAN, align="center")
        nt = pygame.Rect(ax + 54, y, 52, ROW_H - 4)
        self._note_rects[e["id"]] = nt
        hov2 = nt.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov2 else config.COL_PANEL, nt, border_radius=3)
        pygame.draw.rect(surf, config.COL_AMBER, nt, 1, border_radius=3)
        widgets.draw_text(surf, "✎ NOTE", nt.center, fonts.tiny(bold=True), config.COL_AMBER, align="center")

    def _draw_note_dialog(self, surf):
        entry = J.get_entry(self.player, self._note_active)
        label = entry["key"] if entry else "?"
        box = pygame.Rect(0, 0, 520, 140)
        box.center = surf.get_rect().center
        overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))
        pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=6)
        pygame.draw.rect(surf, config.COL_AMBER, box, 1, border_radius=6)
        widgets.draw_text(surf, f"NOTE — {label}", (box.x + 12, box.y + 10),
                          fonts.small(bold=True), config.COL_AMBER)
        nr = pygame.Rect(box.x + 12, box.y + 40, box.w - 24, 36)
        pygame.draw.rect(surf, config.COL_BG, nr, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, nr, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else ""
        widgets.draw_text(surf, (self._note_text or "Raison / commentaire…") + cursor,
                          (nr.x + 8, nr.y + 8), fonts.small(),
                          config.COL_TEXT if self._note_text else config.COL_TEXT_DIM)
        ok = pygame.Rect(box.x + 12, box.bottom - 38, 80, 28)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, ok, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, ok, 1, border_radius=4)
        widgets.draw_text(surf, "OK", ok.center, fonts.small(bold=True), config.COL_AMBER, align="center")
        cancel = pygame.Rect(ok.right + 10, box.bottom - 38, 80, 28)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, cancel, border_radius=4)
        pygame.draw.rect(surf, config.COL_TEXT_DIM, cancel, 1, border_radius=4)
        widgets.draw_text(surf, "Annuler", cancel.center, fonts.small(bold=True), config.COL_TEXT_DIM, align="center")
