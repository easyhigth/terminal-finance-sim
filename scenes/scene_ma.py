"""
scene_ma.py — Hub M&A : trois onglets.
  CIBLES      : catalogue des ~50 cibles privées disponibles (filtrable,
                cliquable -> fiche détaillée / acquisition).
  PORTEFEUILLE: sociétés détenues (état courant) + historique des cessions.
  OUTILS      : calculatrices LBO / Accretion-Dilution génériques (existant).
Ouvert via MA, le rail (M&A) ou PLUS.
"""
import pygame

from core import config, unlocks
from core import finmath as fm
from core import ma as M
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


ROW_H = 24
TABS = ["CIBLES", "PORTEFEUILLE", "OUTILS"]  # clés d'état (FR)
_TAB_LABELS = {"CIBLES": ("CIBLES", "TARGETS"), "PORTEFEUILLE": ("PORTEFEUILLE", "PORTFOLIO"),
               "OUTILS": ("OUTILS", "TOOLS")}


class MAScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.tab = kwargs.get("tab", "CIBLES")
        self.search = ""
        self._search_clear_rect = None
        self.sector_filter = None
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self.hist_scroll = 0
        self._hist_max_scroll = 0
        self._hist_list_rect = None
        self._tab_rects = {}
        self._sector_rects = {}
        self._row_rects = {}      # ticker -> Rect (clic -> fiche)
        self._t = 0.0
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._init_tools()

    def _can_ma(self):
        return unlocks.unlocked(self.app.gs.player, "ma")

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.back(self.return_to)
                return
            elif self.tab == "CIBLES" and event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return
            elif self.tab == "CIBLES" and event.unicode and event.unicode.isprintable() \
                    and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -48 if event.button == 4 else 48
            if self._hist_list_rect and self._hist_list_rect.collidepoint(event.pos):
                self.hist_scroll = max(0, min(self._hist_max_scroll, self.hist_scroll + delta))
                return
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll, self.scroll + delta))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self._tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = name
                    self.scroll = 0
                    return
            if self.tab == "CIBLES":
                if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                    self.search = ""
                    return
                for sec, rect in self._sector_rects.items():
                    if rect.collidepoint(event.pos):
                        self.sector_filter = None if self.sector_filter == sec else sec
                        self.scroll = 0
                        return
            for ticker, rect in self._row_rects.items():
                if rect.collidepoint(event.pos):
                    self.app.scenes.go("ma_target", ticker=ticker, return_to="ma")
                    return
            if self.tab == "OUTILS":
                self._tools_click(event.pos)

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("M&A — ACQUISITIONS, PORTEFEUILLE & OUTILS", "M&A — ACQUISITIONS, PORTFOLIO & TOOLS"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can_ma():
            p = self.app.gs.player
            g = unlocks.effective_required_grade(p, "ma")
            widgets.draw_text(surf, _L(f"⊘ M&A débloqué au grade {config.GRADES[g]}.", f"⊘ M&A unlocked at {config.GRADES[g]} grade."),
                              (42, 72), fonts.small(), config.COL_TEXT_DIM)
            note = unlocks.track_lock_note(p, "ma")
            if note:
                widgets.draw_text(surf, note.strip(), (42, 92), fonts.small(), config.COL_TEXT_DIM)
        else:
            widgets.draw_text(surf, _L("Cibles privées non cotées : analyse complète, financement "
                                    "cash + dette (LBO), pilotage et sortie.",
                                    "Private unlisted targets: full analysis, cash + debt (LBO) "
                                    "financing, steering and exit."),
                              (42, 72), fonts.small(), config.COL_TEXT_DIM)

        # ---- onglets ----
        self._tab_rects = {}
        tx = 40
        ty = 96
        for name in TABS:
            w = fonts.small(bold=True).size(_L(*_TAB_LABELS[name]))[0] + 28
            rect = pygame.Rect(tx, ty, w, 28)
            self._tab_rects[name] = rect
            sel = (name == self.tab)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, _L(*_TAB_LABELS[name]), rect.center, fonts.small(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM, align="center")
            tx += w + 8

        top = ty + 40
        if self.tab == "CIBLES":
            self._draw_targets(surf, top)
        elif self.tab == "PORTEFEUILLE":
            self._draw_portfolio(surf, top)
        else:
            self._draw_tools(surf, top)
        self.back_btn.draw(surf)

    # --------------------------------------------------------- onglet CIBLES
    def _draw_targets(self, surf, top):
        p = self.app.gs.player
        search_rect = pygame.Rect(40, top, 260, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + _L("Tapez pour rechercher…", "Type to search…"))
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y, 22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        targets = M.available_targets(p)
        sectors = sorted({t["sector"] for t in targets})
        self._sector_rects = {}
        cx = 40 + search_rect.w + 16
        cy = top
        for sec in sectors:
            w = max(60, fonts.tiny(bold=True).size(sec)[0] + 16)
            rect = pygame.Rect(cx, cy, w, 24)
            if rect.right > config.SCREEN_WIDTH - 40:
                cx = 40
                cy += 28
                rect = pygame.Rect(cx, cy, w, 24)
            self._sector_rects[sec] = rect
            sel = (self.sector_filter == sec)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, sec, rect.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 6

        q = self.search.strip().lower()
        if q:
            targets = [t for t in targets if q in f"{t['name']} {t['ticker']} {t['sector']} {t['region']}".lower()]
        if self.sector_filter:
            targets = [t for t in targets if t["sector"] == self.sector_filter]
        targets.sort(key=lambda t: t["revenue"] * t["ebitda_margin"] * t["ev_multiple"])

        panel_top = cy + 34
        panel = pygame.Rect(40, panel_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - panel_top)
        inner = widgets.draw_panel(surf, panel, _L(f"Cibles disponibles ({len(targets)})", f"Available targets ({len(targets)})"), config.COL_CYAN)
        cols = [(_L("SOCIÉTÉ", "COMPANY"), inner.x), (_L("SECTEUR", "SECTOR"), inner.x + 230), (_L("RÉGION", "REGION"), inner.x + 340),
                (_L("CA", "REV"), inner.x + 430), ("EBITDA%", inner.x + 540), (_L("EV ESTIMÉE", "EST. EV"), inner.x + 630),
                ("MGMT", inner.x + 760), (_L("MORAL", "MORALE"), inner.x + 830)]
        for label, x in cols:
            widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        list_top = inner.y + 22
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 4)
        self._list_rect = list_area
        self._row_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_top - self.scroll
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        for t in targets:
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                ev = t["revenue"] * t["ebitda_margin"] * t["ev_multiple"]
                self._row_rects[t["ticker"]] = pygame.Rect(cols[0][1] - 2, y - 2, inner.w - 4, ROW_H - 2)
                widgets.draw_text(surf, widgets.fit_text(f"{t['name']} ({t['ticker']})", fonts.small(), 220),
                                  (cols[0][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, t["sector"], (cols[1][1], y), fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, t["region"], (cols[2][1], y), fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, widgets.format_money(t["revenue"], cur), (cols[3][1], y), fonts.small(), config.COL_WHITE)
                widgets.draw_text(surf, f"{t['ebitda_margin']*100:.1f}%", (cols[4][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, widgets.format_money(ev, cur), (cols[5][1], y), fonts.small(bold=True), config.COL_AMBER)
                mcol = config.COL_UP if t["management_score"] >= 60 else config.COL_WARN if t["management_score"] >= 40 else config.COL_DOWN
                widgets.draw_text(surf, f"{t['management_score']:.0f}/100", (cols[6][1], y), fonts.tiny(), mcol)
                morcol = config.COL_UP if t["morale"] >= 60 else config.COL_WARN if t["morale"] >= 40 else config.COL_DOWN
                widgets.draw_text(surf, f"{t['morale']:.0f}/100", (cols[7][1], y), fonts.tiny(), morcol)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        if self._max_scroll > 0:
            track = pygame.Rect(panel.right - 8, list_area.y, 6, list_area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = list_area.h / (content_h or 1)
            bar_h = max(24, int(list_area.h * frac))
            bar_y = list_area.y + int((list_area.h - bar_h) * (self.scroll / self._max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

    # ------------------------------------------------------ onglet PORTEFEUILLE
    def _draw_portfolio(self, surf, top):
        p = self.app.gs.player
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        owned = list((getattr(p, "ma_owned", None) or {}).values())
        panel_h = (config.footer_y() - 8 - top - 200)
        panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, max(140, panel_h))
        inner = widgets.draw_panel(surf, panel, _L(f"Sociétés détenues ({len(owned)})", f"Owned companies ({len(owned)})"), config.COL_UP)
        # bandeau de synergies de roll-up (détenir >=2 cibles d'un secteur)
        syns = M.roll_up_summary(p)
        if syns:
            parts = [f"{s['sector']} ×{s['count']} (+{s['growth_bonus']*100:.1f}%)" for s in syns]
            txt = _L("Synergies roll-up : ", "Roll-up synergies: ") + " · ".join(parts)
            widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(bold=True), panel.w - 300),
                              (panel.right - 12, panel.y + 7), fonts.tiny(bold=True),
                              config.COL_CYAN, align="right")
        self._row_rects = {}
        if not owned:
            widgets.draw_text(surf, _L("Aucune société détenue pour le moment — onglet CIBLES pour acquérir.", "No owned company yet — TARGETS tab to acquire."),
                              (inner.x, inner.y + 4), fonts.small(), config.COL_TEXT_DIM)
        else:
            cols = [(_L("SOCIÉTÉ", "COMPANY"), inner.x), (_L("CA", "REV"), inner.x + 220), ("EBITDA%", inner.x + 320),
                    (_L("DETTE RESTANTE", "DEBT LEFT"), inner.x + 420), ("MGMT", inner.x + 580),
                    (_L("MORAL", "MORALE"), inner.x + 650), (_L("EFFIC.", "EFFIC."), inner.x + 720), (_L("CASH BUF.", "CASH BUF."), inner.x + 800)]
            for label, x in cols:
                widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            y = inner.y + 22
            for inst in owned:
                self._row_rects[inst["ticker"]] = pygame.Rect(cols[0][1] - 2, y - 2, inner.w - 4, ROW_H - 2)
                widgets.draw_text(surf, widgets.fit_text(f"{inst['name']} ({inst['ticker']})", fonts.small(), 200),
                                  (cols[0][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, widgets.format_money(inst["revenue"], cur), (cols[1][1], y), fonts.small(), config.COL_WHITE)
                widgets.draw_text(surf, f"{inst['ebitda_margin']*100:.1f}%", (cols[2][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, widgets.format_money(inst["debt_balance"], cur), (cols[3][1], y),
                                  fonts.small(), config.COL_DOWN if inst["debt_balance"] > 0 else config.COL_UP)
                widgets.draw_text(surf, f"{inst['management_score']:.0f}", (cols[4][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{inst['morale']:.0f}", (cols[5][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{inst['efficiency']:.0f}", (cols[6][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, widgets.format_money(inst["cash_buffer"], cur), (cols[7][1], y), fonts.small(), config.COL_TEXT_DIM)
                y += ROW_H

        hist = list(reversed((getattr(p, "ma_history", None) or [])))
        hist_top = panel.bottom + 10
        hist_panel = pygame.Rect(40, hist_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - hist_top)
        hinner = widgets.draw_panel(surf, hist_panel, _L(f"Historique M&A ({len(hist)})", f"M&A history ({len(hist)})"), config.COL_AMBER)
        if not hist:
            widgets.draw_text(surf, _L("Aucune cession ni défaut pour l'instant.", "No divestment or default yet."),
                              (hinner.x, hinner.y + 4), fonts.small(), config.COL_TEXT_DIM)
            self._hist_list_rect = None
            self._hist_max_scroll = 0
        else:
            list_area = pygame.Rect(hinner.x - 4, hinner.y, hinner.w + 8, hinner.h)
            self._hist_list_rect = list_area
            prev_clip = surf.get_clip()
            surf.set_clip(list_area)
            y = hinner.y - self.hist_scroll
            for h in hist:
                col = config.COL_UP if h["pnl"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{h['name']} ({h['ticker']}) — {h['status']}",
                                  (hinner.x, y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"P&L {widgets.format_money(h['pnl'], cur)}  ·  MOIC {h['moic']:.2f}x",
                                  (hinner.right, y), fonts.small(bold=True), col, align="right")
                y += ROW_H
            surf.set_clip(prev_clip)
            content_h = (y + self.hist_scroll) - hinner.y
            self._hist_max_scroll = max(0, content_h - list_area.h)
            self.hist_scroll = max(0, min(self._hist_max_scroll, self.hist_scroll))
            self.hist_scroll = widgets.draw_scrollbar(surf, hist_panel, list_area, self.hist_scroll,
                                   self._hist_max_scroll, content_h)

    # ------------------------------------------------------------- OUTILS (LBO / accretion)
    def _init_tools(self):
        self.entry_ev = 1000.0
        self.entry_ebitda = 100.0
        self.debt_pct = 0.6
        self.exit_multiple = 11.0
        self.years = 5
        self.ebitda_cagr = 0.08
        self.acq_eps = 5.0
        self.acq_shares = 100.0
        self.target_ni = 200.0
        self.new_shares = 30.0
        self.synergies = 50.0
        self._sliders = {}

    def _adj(self, key, delta):
        bounds = {
            "debt_pct": (0.0, 0.85, 0.05), "exit_multiple": (5.0, 18.0, 0.5),
            "years": (3, 8, 1), "ebitda_cagr": (0.0, 0.20, 0.01),
            "synergies": (0.0, 200.0, 10.0), "new_shares": (0.0, 100.0, 5.0),
        }
        lo, hi, _ = bounds[key]
        val = getattr(self, key) + delta
        setattr(self, key, max(lo, min(hi, val)))

    def _tools_click(self, pos):
        for key, (minus, plus, step) in self._sliders.items():
            if minus.collidepoint(pos):
                self._adj(key, -step)
            elif plus.collidepoint(pos):
                self._adj(key, +step)

    def _slider(self, surf, x, y, label, value, key, step, fmt="{:.0f}"):
        widgets.draw_text(surf, label, (x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, fmt.format(value), (x + 250, y), fonts.small(bold=True), config.COL_WHITE)
        minus = pygame.Rect(x + 320, y - 2, 24, 22)
        plus = pygame.Rect(x + 348, y - 2, 24, 22)
        for rect, sym in ((minus, "-"), (plus, "+")):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
            widgets.draw_text(surf, sym, rect.center, fonts.body(bold=True), config.COL_AMBER, align="center")
        self._sliders[key] = (minus, plus, step)

    def _draw_tools(self, surf, top):
        self._sliders = {}
        self._draw_lbo(surf, top)
        self._draw_accretion(surf, top)

    def _draw_lbo(self, surf, top):
        panel = pygame.Rect(40, top, 600, config.footer_y() - 8 - top)
        inner = widgets.draw_panel(surf, panel, _L("Leveraged Buyout (LBO) — générique", "Leveraged Buyout (LBO) — generic"), config.COL_UP)
        x, y = inner.x, inner.y
        widgets.draw_text(surf, _L(f"EV d'entrée : {self.entry_ev:.0f} M  |  EBITDA : {self.entry_ebitda:.0f} M  |  "
                                f"Multiple entrée : {self.entry_ev/self.entry_ebitda:.1f}x",
                                f"Entry EV: {self.entry_ev:.0f} M  |  EBITDA: {self.entry_ebitda:.0f} M  |  "
                                f"Entry multiple: {self.entry_ev/self.entry_ebitda:.1f}x"),
                          (x, y), fonts.small(), config.COL_TEXT_DIM)
        y += 36
        self._slider(surf, x, y, _L("Levier (dette / EV)", "Leverage (debt / EV)"), self.debt_pct, "debt_pct", 0.05, "{:.0%}"); y += 38
        self._slider(surf, x, y, _L("Multiple de sortie", "Exit multiple"), self.exit_multiple, "exit_multiple", 0.5, "{:.1f}x"); y += 38
        self._slider(surf, x, y, _L("Horizon (années)", "Horizon (years)"), self.years, "years", 1, "{:.0f}"); y += 38
        self._slider(surf, x, y, _L("Croissance EBITDA (CAGR)", "EBITDA growth (CAGR)"), self.ebitda_cagr, "ebitda_cagr", 0.01, "{:.0%}"); y += 50

        moic, irr_v, exit_eq = fm.lbo_returns(self.entry_ev, self.entry_ebitda, self.debt_pct,
                                              self.exit_multiple, int(self.years), self.ebitda_cagr)
        res_panel = pygame.Rect(x - 4, y, inner.w - 8, min(258, inner.bottom - y - 4))
        pygame.draw.rect(surf, (10, 22, 14), res_panel)
        pygame.draw.rect(surf, config.COL_UP, res_panel, 1)
        ry = y + 14
        equity_in = self.entry_ev * (1 - self.debt_pct)
        exit_ebitda = self.entry_ebitda * ((1 + self.ebitda_cagr) ** int(self.years))
        rows = [
            (_L("Equity investi (entrée)", "Equity invested (entry)"), f"{equity_in:.0f} M", config.COL_TEXT),
            (_L("EBITDA de sortie", "Exit EBITDA"), f"{exit_ebitda:.0f} M", config.COL_TEXT),
            (_L("EV de sortie", "Exit EV"), f"{exit_ebitda*self.exit_multiple:.0f} M", config.COL_TEXT),
            (_L("Equity de sortie", "Exit equity"), f"{exit_eq:.0f} M", config.COL_WHITE),
            ("", "", config.COL_TEXT),
            (_L("MOIC (multiple)", "MOIC (multiple)"), f"{moic:.2f}x", config.COL_UP if moic >= 2 else config.COL_WARN),
            (_L("IRR (fonds propres)", "IRR (equity)"), f"{irr_v*100:.1f}%",
             config.COL_UP if irr_v >= 0.20 else config.COL_WARN if irr_v >= 0.10 else config.COL_DOWN),
        ]
        for label, val, col in rows:
            if label:
                widgets.draw_text(surf, label, (res_panel.x + 14, ry), fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (res_panel.x + 330, ry), fonts.body(bold=True), col)
            ry += 30

    def _draw_accretion(self, surf, top):
        panel = pygame.Rect(660, top, config.SCREEN_WIDTH - 700, config.footer_y() - 8 - top)
        inner = widgets.draw_panel(surf, panel, _L("Accretion / Dilution (paiement en actions)", "Accretion / Dilution (stock payment)"), config.COL_CYAN)
        x, y = inner.x, inner.y
        widgets.draw_text(surf, _L("Acquéreur", "Acquirer"), (x, y), fonts.small(bold=True), config.COL_AMBER); y += 26
        widgets.draw_text(surf, _L(f"BPA actuel : {self.acq_eps:.2f}   Actions : {self.acq_shares:.0f} M", f"Current EPS: {self.acq_eps:.2f}   Shares: {self.acq_shares:.0f} M"),
                          (x, y), fonts.small(), config.COL_TEXT); y += 26
        widgets.draw_text(surf, _L(f"Résultat net : {self.acq_eps*self.acq_shares:.0f} M", f"Net income: {self.acq_eps*self.acq_shares:.0f} M"),
                          (x, y), fonts.small(), config.COL_TEXT_DIM); y += 40
        widgets.draw_text(surf, _L("Cible & financement", "Target & financing"), (x, y), fonts.small(bold=True), config.COL_AMBER); y += 28
        widgets.draw_text(surf, _L(f"Résultat net cible : {self.target_ni:.0f} M", f"Target net income: {self.target_ni:.0f} M"),
                          (x, y), fonts.small(), config.COL_TEXT); y += 34
        self._slider(surf, x, y, _L("Actions émises (M)", "Shares issued (M)"), self.new_shares, "new_shares", 5.0, "{:.0f}"); y += 38
        self._slider(surf, x, y, _L("Synergies (M)", "Synergies (M)"), self.synergies, "synergies", 10.0, "{:.0f}"); y += 50

        pf_eps, delta = fm.accretion_dilution(self.acq_eps, self.acq_shares * 1e6, self.target_ni * 1e6,
                                              self.new_shares * 1e6, self.synergies * 1e6)
        res = pygame.Rect(x - 4, y, inner.w - 8, min(200, inner.bottom - y - 4))
        accretive = delta >= 0
        bg = (10, 22, 14) if accretive else (24, 12, 14)
        border = config.COL_UP if accretive else config.COL_DOWN
        pygame.draw.rect(surf, bg, res)
        pygame.draw.rect(surf, border, res, 1)
        ry = y + 16
        widgets.draw_text(surf, _L("BPA pro-forma", "Pro-forma EPS"), (res.x + 14, ry), fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{pf_eps:.3f}", (res.x + 260, ry), fonts.body(bold=True), config.COL_WHITE); ry += 36
        widgets.draw_text(surf, _L("Variation du BPA", "EPS change"), (res.x + 14, ry), fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{'+' if delta>=0 else ''}{delta:.2f}%",
                          (res.x + 260, ry), fonts.head(bold=True), border); ry += 44
        verdict = _L("RELUTIF (accretive) ✓", "ACCRETIVE ✓") if accretive else _L("DILUTIF (dilutive) ✗", "DILUTIVE ✗")
        widgets.draw_text(surf, verdict, (res.x + 14, ry), fonts.body(bold=True), border); ry += 34
        note = (_L("Le BPA combiné dépasse celui de l'acquéreur : crée de la valeur par action.",
                   "The combined EPS exceeds the acquirer's: creates value per share.")
                if accretive else
                _L("Le BPA combiné baisse : à justifier par des synergies futures ou stratégie.",
                   "The combined EPS drops: to be justified by future synergies or strategy."))
        widgets.draw_text_wrapped(surf, note, (res.x + 14, ry), fonts.small(), config.COL_TEXT, res.w - 28)
