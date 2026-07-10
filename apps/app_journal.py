"""
app_journal.py — Application « Journal de trading » du bureau (NATIVE).

Migration de `scenes/scene_journal.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — même principe que Portefeuille/Marché/Mission
avant elle. Toutes les positions sont relatives au `rect` de la fenêtre
plutôt qu'à `config.SCREEN_WIDTH`/`footer_y()`. Réutilise `core/journal.py`
tel quel (recherche, filtres classe/sens, tri, statistiques de discipline,
annotation, réplication d'un trade vers Trading). La scène plein écran reste
enregistrée (fallback/tests) ; l'ouverture EN FENÊTRE de "tradejournal" est
redirigée ici (cf. DesktopScene._open_scene_window). Accessible depuis
l'icône dédiée du bureau ET un bouton « JOURNAL » dans Trading/Portefeuille
(apps/app_trading.py, apps/app_book.py).
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import journal as J
from ui import fonts, keynav, widgets

ROW_H = 22
SORT_FIELDS = [("day", "JOUR"), ("asset_class", "CLASSE"), ("side", "SENS"),
                ("notional", "TAILLE"), ("realized", "P&L")]
ASSET_CHIPS = [None, "Action", "ETF", "Obligation", "Commodity", "Crypto"]
SIDE_CHIPS = [None, "achat", "vente", "short", "couverture"]


class JournalApp(DesktopApp):
    title = "Journal de trading"
    icon_kind = "journal"
    default_size = (1020, 640)
    min_size = (680, 420)

    def on_open(self):
        self.player = self.app.gs.player
        self.market = self.app.ensure_market()
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
        self._note_active = None
        self._note_text = ""
        self._t = 0.0
        self._csv_rect = None
        self.msg = ""

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

    def _export_csv(self):
        """Bouton « CSV ↓ » : exporte le journal complet vers le dossier
        personnel — même politique « pas de sélecteur de fichier natif » que
        l'export du Tableur (apps/app_sheet.py)."""
        import os as _os
        if not self.player.trade_journal:
            self.msg = "Journal vide : rien à exporter."
            return
        path = _os.path.join(_os.path.expanduser("~"), "journal_trading.csv")
        if J.export_csv(self.player, path):
            self.msg = f"Exporté vers « {path} »."
        else:
            self.msg = "Échec de l'export CSV (chemin inaccessible)."

    def _replicate(self, entry):
        """Ouvre Trading pré-filtré sur l'actif (achat de la quantité
        d'origine pré-rempli via la ligne de commande du terminal, comme la
        scène d'origine)."""
        ticker = entry["key"]
        qty = entry["qty"]
        if entry["asset_class"] == "Action" and ticker and qty:
            self.app.pending_input = f"BUY {ticker} {int(qty)}"
        if self.desktop is not None:
            self.desktop.open_trading(ticker if entry["asset_class"] == "Action" else None)

    # ------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if self._note_active is not None:
            return self._handle_note_event(event, rect)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    return True
                return False
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._rows))
                if activate and self._rows:
                    self._start_note(self._rows[self.row_cursor])
                return True
            from core import clipboard
            if clipboard.is_paste_shortcut(event):
                self.search += clipboard.paste().replace("\n", " ").strip()
                self.scroll = 0
                return True
            if event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._csv_rect and self._csv_rect.collidepoint(event.pos):
                self._export_csv()
                return True
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return True
            for kind, r in self._asset_rects.items():
                if r.collidepoint(event.pos):
                    self.asset_filter = None if kind == self.asset_filter else kind
                    return True
            for side, r in self._side_rects.items():
                if r.collidepoint(event.pos):
                    self.side_filter = None if side == self.side_filter else side
                    return True
            for key, r in self._sort_rects.items():
                if r.collidepoint(event.pos):
                    self._toggle_sort(key)
                    return True
            for eid, r in self._replicate_rects.items():
                if r.collidepoint(event.pos):
                    entry = J.get_entry(self.player, eid)
                    if entry:
                        self._replicate(entry)
                    return True
            for eid, r in self._note_rects.items():
                if r.collidepoint(event.pos):
                    entry = J.get_entry(self.player, eid)
                    if entry:
                        self._start_note(entry)
                    return True
            return False
        return False

    def _handle_note_event(self, event, rect):
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
            from core import clipboard
            if clipboard.is_paste_shortcut(event):
                self._note_text += clipboard.paste().replace("\n", " ")
                return True
            if event.unicode and event.unicode.isprintable():
                self._note_text += event.unicode
                return True
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            box = pygame.Rect(0, 0, min(520, rect.w - 40), 140)
            box.center = rect.center
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

    # --------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        pad = 12
        widgets.draw_text(surf, "JOURNAL DE TRADING", (rect.x + pad, rect.y + 8),
                          fonts.head(bold=True), config.COL_AMBER)
        sub = self.msg or "Filtrez, triez et reprenez vos trades passés. ✎ annote, ↻ réplique."
        widgets.draw_text(surf, widgets.fit_text(sub, fonts.tiny(), rect.w - 2 * pad - 70),
                          (rect.x + pad, rect.y + 34), fonts.tiny(),
                          config.COL_WARN if self.msg else config.COL_TEXT_DIM)
        # export CSV (coin haut-droit) — symétrique de l'export du Tableur
        self._csv_rect = pygame.Rect(rect.right - pad - 60, rect.y + 8, 60, 22)
        hov = self._csv_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD,
                         self._csv_rect, border_radius=3)
        pygame.draw.rect(surf, config.COL_TEXT_DIM, self._csv_rect, 1, border_radius=3)
        widgets.draw_text(surf, "CSV ↓", self._csv_rect.center, fonts.tiny(bold=True),
                          config.COL_TEXT_DIM, align="center")

        p = self.player
        cur = self._cur()
        mp = pygame.mouse.get_pos()

        # ---- statistiques ----
        stats = J.performance_stats(p, group_by="regime")
        disc = J.discipline_score(p)
        y_stat = rect.y + 56
        widgets.draw_text(surf, "DISCIPLINE :", (rect.x + pad, y_stat), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        if disc is not None:
            widgets.draw_text(surf, f"{disc['score']:.0f}/100",
                              (rect.x + pad + 80, y_stat), fonts.small(bold=True), config.COL_AMBER)
        total_pnl = sum(g["total_pnl"] for g in stats)
        total_trades = sum(g["count"] for g in stats)
        wins = sum(g["wins"] for g in stats)
        win_rate = (wins / total_trades * 100) if total_trades else 0.0
        pnl_col = config.COL_UP if total_pnl >= 0 else config.COL_DOWN
        stat_line = f"Trades clôturés : {total_trades} · Win rate : {win_rate:.0f}% · P&L total : {total_pnl:+,.0f} {cur}"
        widgets.draw_text(surf, widgets.fit_text(stat_line, fonts.tiny(bold=True), rect.w - 2 * pad - 180),
                          (rect.x + pad + 180, y_stat), fonts.tiny(bold=True), pnl_col)

        # ---- filtres ----
        fy = y_stat + 22
        fx = rect.x + pad
        self._asset_rects = {}
        for kind in ASSET_CHIPS:
            label = "TOUTES" if kind is None else kind
            w = max(46, fonts.tiny(bold=True).size(label)[0] + 10)
            r = pygame.Rect(fx, fy, w, 18)
            if r.right > rect.right - pad:
                break
            self._asset_rects[kind] = r
            active = self.asset_filter == kind
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            fx += w + 4

        fy2 = fy + 22
        fx = rect.x + pad
        self._side_rects = {}
        for side in SIDE_CHIPS:
            label = "TOUS" if side is None else side.upper()
            w = max(46, fonts.tiny(bold=True).size(label)[0] + 10)
            r = pygame.Rect(fx, fy2, w, 18)
            if r.right > rect.right - pad:
                break
            self._side_rects[side] = r
            active = self.side_filter == side
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            fx += w + 4

        # ---- recherche + tri ----
        sry = fy2 + 24
        sr = pygame.Rect(rect.x + pad, sry, min(220, rect.w - 2 * pad), 22)
        pygame.draw.rect(surf, config.COL_PANEL, sr, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, sr, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        lbl = (self.search + cursor) if self.search else (cursor + "Rechercher…")
        widgets.draw_text(surf, widgets.fit_text(lbl, fonts.tiny(), sr.w - 14),
                          (sr.x + 6, sr.y + 4), fonts.tiny(),
                          config.COL_TEXT if self.search else config.COL_TEXT_DIM)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(sr.right - 20, sr.y, 20, sr.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.tiny(bold=True),
                              config.COL_TEXT_DIM, align="center")

        tx = sr.right + 14
        self._sort_rects = {}
        for key, label in SORT_FIELDS:
            active = self.sort_key == key
            arrow = (" ▲" if self.sort_dir > 0 else " ▼") if active else ""
            full = label + arrow
            w = max(46, fonts.tiny(bold=True).size(full)[0] + 10)
            r = pygame.Rect(tx, sry, w, 22)
            if r.right > rect.right - pad:
                break
            self._sort_rects[key] = r
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, full, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            tx += w + 4

        # ---- liste (+ courbe de P&L cumulé à droite si la place le permet) ----
        ltop = sry + 30
        pnl_series = J.cumulative_realized_series(p)
        show_curve = rect.w >= 900 and len(pnl_series) >= 2
        curve_w = 250 if show_curve else 0
        panel = pygame.Rect(rect.x + pad, ltop, rect.w - 2 * pad - curve_w - (10 if curve_w else 0),
                            rect.bottom - pad - ltop)
        if show_curve:
            # colonne droite : P&L cumulé en haut, sizing de Kelly en bas
            half = (panel.h - 10) // 2
            curve_panel = pygame.Rect(panel.right + 10, ltop, curve_w, half)
            self._draw_pnl_curve(surf, curve_panel, pnl_series, cur)
            kelly_panel = pygame.Rect(panel.right + 10, ltop + half + 10,
                                      curve_w, panel.h - half - 10)
            self._draw_kelly(surf, kelly_panel, cur)
        inner = widgets.draw_panel(surf, panel, "Trades", config.COL_CYAN)
        self._rows = self._filtered_sorted()
        self.row_cursor = min(self.row_cursor, len(self._rows) - 1) if self._rows else 0

        show_regime = inner.w >= 620
        show_note = inner.w >= 760
        cols_w = {"id": 40, "day": 42, "actif": 62, "classe": 66, "sens": 52,
                  "qte": 50, "prix": 62, "pnl": 74}
        cx = inner.x
        col_x = {}
        for key, label in (("id", "ID"), ("day", "JOUR"), ("actif", "ACTIF"),
                           ("classe", "CLASSE"), ("sens", "SENS"), ("qte", "QTÉ"),
                           ("prix", "PRIX"), ("pnl", "P&L")):
            col_x[key] = cx
            widgets.draw_text(surf, label, (cx, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            cx += cols_w[key]
        if show_regime:
            col_x["regime"] = cx
            widgets.draw_text(surf, "RÉGIME", (cx, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            cx += 90
        if show_note:
            col_x["note"] = cx
            widgets.draw_text(surf, "NOTE", (cx, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)

        list_area = pygame.Rect(inner.x - 6, inner.y + 20, inner.w + 12, inner.h - 24)
        self._list_rect = list_area
        self._replicate_rects = {}
        self._note_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y + 20 - self.scroll
        for i, e in enumerate(self._rows):
            if (list_area.top - ROW_H) < y < list_area.bottom:
                self._draw_row(surf, e, y, inner, col_x, mp, show_regime, show_note, i == self.row_cursor)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = len(self._rows) * ROW_H
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        if self._note_active is not None:
            self._draw_note_dialog(surf, rect)

    def _draw_row(self, surf, e, y, inner, col_x, mp, show_regime, show_note, cursor=False):
        row_rect = pygame.Rect(inner.x - 4, y - 1, inner.w + 8, ROW_H - 2)
        if row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        keynav.draw_focus_ring(surf, row_rect, cursor)
        widgets.draw_text(surf, f"#{e['id']}", (col_x["id"], y), fonts.tiny(), config.COL_AMBER)
        widgets.draw_text(surf, f"j{e['day']}", (col_x["day"], y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.fit_text(e['key'], fonts.tiny(bold=True), 58),
                          (col_x["actif"], y), fonts.tiny(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(e['asset_class'], fonts.tiny(), 62),
                          (col_x["classe"], y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, e['side'].upper()[:4], (col_x["sens"], y), fonts.tiny(),
                          config.COL_UP if e['side'] == 'achat' else config.COL_DOWN)
        widgets.draw_text(surf, f"{e['qty']:g}", (col_x["qte"], y), fonts.tiny(), config.COL_TEXT)
        widgets.draw_text(surf, f"{e['price']:.2f}", (col_x["prix"], y), fonts.tiny(), config.COL_TEXT)
        if e["realized"] is not None:
            pcol = config.COL_UP if e["realized"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{e['realized']:+,.0f}", (col_x["pnl"], y),
                              fonts.tiny(bold=True), pcol)
        else:
            widgets.draw_text(surf, "—", (col_x["pnl"], y), fonts.tiny(), config.COL_TEXT_DIM)
        if show_regime:
            widgets.draw_text(surf, widgets.fit_text(e.get("regime", ""), fonts.tiny(), 84),
                              (col_x["regime"], y), fonts.tiny(), config.COL_TEXT_DIM)
        if show_note:
            note = (e.get("comment") or e.get("reason") or "—")
            note_w = inner.right - col_x["note"] - 110
            widgets.draw_text(surf, widgets.fit_text(note, fonts.tiny(), max(20, note_w)),
                              (col_x["note"], y), fonts.tiny(), config.COL_TEXT_DIM)

        ax = inner.right - 100
        rep = pygame.Rect(ax, y - 1, 44, ROW_H - 4)
        self._replicate_rects[e["id"]] = rep
        hov = rep.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, rep, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, rep, 1, border_radius=3)
        widgets.draw_text(surf, "↻", rep.center, fonts.tiny(bold=True), config.COL_CYAN, align="center")
        nt = pygame.Rect(ax + 48, y - 1, 44, ROW_H - 4)
        self._note_rects[e["id"]] = nt
        hov2 = nt.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov2 else config.COL_PANEL, nt, border_radius=3)
        pygame.draw.rect(surf, config.COL_AMBER, nt, 1, border_radius=3)
        widgets.draw_text(surf, "✎", nt.center, fonts.tiny(bold=True), config.COL_AMBER, align="center")

    def _draw_pnl_curve(self, surf, panel, series, cur):
        """Courbe du P&L réalisé CUMULÉ au fil des trades clôturés
        (core/journal.cumulative_realized_series) — la table seule ne donne
        aucune vue d'ensemble de la trajectoire."""
        inner = widgets.draw_panel(surf, panel, "P&L cumulé", config.COL_PRESTIGE)
        total = series[-1]
        col = config.COL_UP if total >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{total:+,.0f} {cur}", (inner.x, inner.y),
                          fonts.small(bold=True), col)
        widgets.draw_text(surf, f"{len(series)} trades clôturés", (inner.x, inner.y + 18),
                          fonts.tiny(), config.COL_TEXT_DIM)
        chart = pygame.Rect(inner.x, inner.y + 40, inner.w, inner.h - 44)
        if chart.h < 30:
            return
        lo, hi = min(series + [0.0]), max(series + [0.0])
        y_fmt = lambda v: f"{v:+,.0f}"
        widgets.draw_chart_axes(surf, chart, lo, hi, y_fmt=y_fmt, rows=3)
        widgets.draw_series(surf, chart, series, color=col, baseline=True,
                            mouse_pos=pygame.mouse.get_pos(), y_fmt=y_fmt,
                            line_width=2)

    def _draw_kelly(self, surf, panel, cur):
        """Sizing de Kelly sur les stats RÉELLES du journal (core/kelly) :
        f* = p − (1−p)/b, la courbe croissance(f) qui culmine à f* et chute
        au-delà — sur-risquer un edge positif suffit à ruiner."""
        from core import kelly as K
        from core import portfolio as pf
        inner = widgets.draw_panel(surf, panel, "Sizing (critère de Kelly)",
                                   config.COL_AMBER)
        p = self.player
        nw = p.cash + sum(h["value"] for h in pf.holdings(p, self.market))
        reco = K.recommendation(p, nw)
        if reco is None:
            widgets.draw_text(surf, "Aucun trade clôturé — Kelly a besoin de "
                              "votre historique.", (inner.x, inner.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        st = reco["stats"]
        widgets.draw_text(surf, f"p = {st['p'] * 100:.0f}% · b = {st['b']:.2f} "
                          f"({st['n']} trades)", (inner.x, inner.y),
                          fonts.tiny(), config.COL_TEXT_DIM)
        fcol = config.COL_UP if reco["f_star"] > 0 else config.COL_DOWN
        widgets.draw_text(surf, f"Kelly f* = {reco['f_star'] * 100:.0f}% · "
                          f"½-Kelly = {reco['f_half'] * 100:.0f}%",
                          (inner.x, inner.y + 16), fonts.small(bold=True), fcol)
        widgets.draw_text(surf, f"Mise ½-Kelly ≈ {widgets.format_money(reco['stake_half'], cur)}",
                          (inner.x, inner.y + 34), fonts.tiny(), config.COL_TEXT)
        # courbe g(f) : le sommet à f*, la chute au-delà
        chart = pygame.Rect(inner.x, inner.y + 54, inner.w,
                            inner.h - 58 - (14 if reco["warning"] else 0))
        if chart.h >= 26 and reco["curve"]:
            gs = [g for _f, g in reco["curve"] if g > float("-inf")]
            if gs:
                lo, hi = min(gs + [0.0]), max(gs + [0.0])
                rng = (hi - lo) or 1.0
                fmax = reco["curve"][-1][0] or 1.0
                pts = []
                for f, g in reco["curve"]:
                    if g == float("-inf"):
                        continue
                    x0 = chart.x + int(f / fmax * chart.w)
                    y0 = chart.bottom - int((g - lo) / rng * chart.h)
                    pts.append((x0, y0))
                zero_y = chart.bottom - int((0.0 - lo) / rng * chart.h)
                pygame.draw.line(surf, config.COL_BORDER, (chart.x, zero_y),
                                 (chart.right, zero_y))
                if len(pts) >= 2:
                    pygame.draw.aalines(surf, config.COL_AMBER, False, pts)
                if reco["f_star"] > 0:
                    fx = chart.x + int(min(1.0, reco["f_star"] / fmax) * chart.w)
                    pygame.draw.line(surf, config.COL_UP, (fx, chart.y),
                                     (fx, chart.bottom), 1)
        if reco["warning"]:
            widgets.draw_text(surf, widgets.fit_text(reco["warning"], fonts.tiny(),
                                                     inner.w),
                              (inner.x, inner.bottom - 12), fonts.tiny(),
                              config.COL_WARN)

    def _draw_note_dialog(self, surf, rect):
        entry = J.get_entry(self.player, self._note_active)
        label = entry["key"] if entry else "?"
        box = pygame.Rect(0, 0, min(520, rect.w - 40), 140)
        box.center = rect.center
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, rect.topleft)
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
