"""
scene_ma_target.py — Fiche détaillée d'une cible / société M&A.
  - Cible non détenue : valorisation (comps + DCF), états financiers 5 ans,
    curseur de financement (dette/cash) et bouton d'acquisition (LBO réel).
  - Société détenue : suivi (management/moral/efficacité/dette/trésorerie),
    axes d'amélioration (une action par trimestre) et cession (exit).
Ouverte via le clic sur une ligne de la scène MA (CIBLES/PORTEFEUILLE).
"""
import pygame

from core import config, unlocks
from core import ma as M
from core.scene_manager import Scene
from ui import fonts, widgets

TABS = ["APERÇU", "ÉTATS FINANCIERS"]
BASE_FISCAL_YEAR = getattr(config, "BASE_FISCAL_YEAR", 2024)

_EMPH = {"Marge brute", "EBITDA", "Résultat d'exploitation (EBIT)", "Résultat avant impôt",
         "Résultat net", "Total actifs courants", "TOTAL ACTIF",
         "Total passifs courants", "Total passif (hors CP)", "Capitaux propres",
         "TOTAL PASSIF + CP"}


def _fm(v):
    if abs(v) < 0.5:
        return "—"
    return f"({abs(v):,.0f})".replace(",", " ") if v < 0 else f"{v:,.0f}".replace(",", " ")


def _score_col(v):
    return config.COL_UP if v >= 60 else config.COL_WARN if v >= 40 else config.COL_DOWN


class MATargetScene(Scene):
    def on_enter(self, **kwargs):
        self.ticker = (kwargs.get("ticker") or "").upper()
        self.return_to = kwargs.get("return_to", "ma")
        self.tab = "APERÇU"
        self._tab_rects = {}
        self._action_rects = {}
        self._debt_minus_rect = None
        self._debt_plus_rect = None
        self._buy_rect = None
        self._exit_rect = None
        self.debt_pct = 0.6
        self._msg = ""
        self._msg_col = config.COL_TEXT_DIM
        self._tooltip = None
        self._refresh()
        back_rect = config.back_button_rect(160)
        btn_y, btn_h = back_rect[1], back_rect[3]
        self.back_btn = widgets.Button(back_rect,
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.sheet_inc_btn = widgets.Button((210, btn_y, 200, btn_h),
                                            "→ TABLEUR (CR)", config.COL_UP)
        self.sheet_bal_btn = widgets.Button((420, btn_y, 200, btn_h),
                                            "→ TABLEUR (BILAN)", config.COL_UP)

    def _refresh(self):
        p = self.app.gs.player
        self.inst = (getattr(p, "ma_owned", None) or {}).get(self.ticker)
        self.target = M.get_target(self.ticker)
        self.owned = self.inst is not None
        self.data = self.inst if self.owned else self.target

    def _can_ma(self):
        return unlocks.unlocked(self.app.gs.player, "ma")

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if not self._can_ma() or not self.data:
            return
        if self.tab == "ÉTATS FINANCIERS":
            if self.sheet_inc_btn.handle(event):
                self._open_spreadsheet("income")
                return
            if self.sheet_bal_btn.handle(event):
                self._open_spreadsheet("balance")
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self._tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = name
                    return
            if self.tab != "APERÇU":
                return
            if not self.owned:
                if self._debt_minus_rect and self._debt_minus_rect.collidepoint(event.pos):
                    self.debt_pct = max(0.0, round(self.debt_pct - 0.05, 2))
                    return
                if self._debt_plus_rect and self._debt_plus_rect.collidepoint(event.pos):
                    self.debt_pct = min(M.MAX_DEBT_PCT, round(self.debt_pct + 0.05, 2))
                    return
                if self._buy_rect and self._buy_rect.collidepoint(event.pos):
                    self._do_acquire()
                    return
            else:
                for action_id, rect in self._action_rects.items():
                    if rect.collidepoint(event.pos):
                        self._do_action(action_id)
                        return
                if self._exit_rect and self._exit_rect.collidepoint(event.pos):
                    self._do_exit()
                    return

    def _do_acquire(self):
        res = M.acquire(self.app.gs.player, self.ticker, self.debt_pct)
        if res["ok"]:
            self._msg = f"Acquisition réussie : {self.target['name']} rejoint votre portefeuille."
            self._msg_col = config.COL_UP
            self._refresh()
        else:
            self._msg = res["reason"]
            self._msg_col = config.COL_DOWN

    def _do_action(self, action_id):
        res = M.apply_action(self.app.gs.player, self.ticker, action_id)
        if res["ok"]:
            self._msg = "Action appliquée."
            self._msg_col = config.COL_UP
            self._refresh()
        else:
            self._msg = res["reason"]
            self._msg_col = config.COL_DOWN

    def _do_exit(self):
        res = M.exit_company(self.app.gs.player, self.ticker)
        if res["ok"]:
            pnl = res["pnl"]
            verb = "plus-value" if pnl >= 0 else "perte"
            self._msg = f"Société cédée — {verb} de {abs(pnl):,.0f}.".replace(",", " ")
            self._msg_col = config.COL_UP if pnl >= 0 else config.COL_DOWN
            self._refresh()
            self.tab = "APERÇU"
        else:
            self._msg = res["reason"]
            self._msg_col = config.COL_DOWN

    def _open_spreadsheet(self, which):
        p = self.app.gs.player
        years_elapsed = (p.day - 1) // 365
        base_year = BASE_FISCAL_YEAR + years_elapsed
        block = M.statements_for(self.data, base_year, n_years=5)
        years = [b["year"] for b in block]
        if which == "income":
            title = f"{self.ticker} — Compte de résultat"
            lines = block[0]["income"]["lines"]
            rows = [(line["label"], [b["income"]["lines"][r]["value"] for b in block])
                    for r, line in enumerate(lines)]
        else:
            title = f"{self.ticker} — Bilan"
            rows = []
            n_assets = len(block[0]["balance"]["assets_lines"])
            for r in range(n_assets):
                rows.append((block[0]["balance"]["assets_lines"][r]["label"],
                             [b["balance"]["assets_lines"][r]["value"] for b in block]))
            for r in range(len(block[0]["balance"]["liab_lines"])):
                rows.append((block[0]["balance"]["liab_lines"][r]["label"],
                             [b["balance"]["liab_lines"][r]["value"] for b in block]))
        self.app.scenes.go("spreadsheet", return_to="ma_target",
                           return_kwargs={"ticker": self.ticker, "return_to": self.return_to},
                           import_data={"title": title, "years": years, "rows": rows})

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        if self.tab == "ÉTATS FINANCIERS":
            mp = pygame.mouse.get_pos()
            self.sheet_inc_btn.update(mp, dt)
            self.sheet_bal_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        self._tooltip = None
        p = self.app.gs.player
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        if not self.data:
            widgets.draw_text(surf, f"Cible introuvable : {self.ticker}", (40, 40),
                              fonts.title(bold=True), config.COL_DOWN)
            self.back_btn.draw(surf)
            return

        name = self.data["name"]
        status = "DÉTENUE" if self.owned else "CIBLE PRIVÉE"
        accent = config.COL_UP if self.owned else config.COL_AMBER
        widgets.draw_text(surf, name, (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{self.ticker} · {self.data['sector']} · {self.data['region']} · {status}",
                          (40, 78), fonts.small(), config.COL_TEXT_DIM)

        if not self._can_ma():
            g = unlocks.effective_required_grade(self.app.gs.player, "ma")
            widgets.draw_text(surf, f"⊘ M&A débloqué au grade {config.GRADES[g]}.",
                              (40, 104), fonts.small(), config.COL_DOWN)
            self.back_btn.draw(surf)
            return

        self._tab_rects = {}
        tx, ty = 40, 104
        for tname in TABS:
            w = fonts.small(bold=True).size(tname)[0] + 28
            rect = pygame.Rect(tx, ty, w, 28)
            self._tab_rects[tname] = rect
            sel = (tname == self.tab)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, tname, rect.center, fonts.small(bold=sel),
                              accent if sel else config.COL_TEXT_DIM, align="center")
            tx += w + 8

        top = ty + 40
        if self._msg:
            widgets.draw_text(surf, self._msg, (40, top - 18), fonts.small(bold=True), self._msg_col)

        if self.tab == "APERÇU":
            self._draw_apercu(surf, top, cur)
        else:
            self._draw_statements(surf, top, cur)
            self.sheet_inc_btn.draw(surf)
            self.sheet_bal_btn.draw(surf)
        self.back_btn.draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    # --------------------------------------------------------- onglet APERÇU
    def _draw_apercu(self, surf, top, cur):
        d = self.data
        val = M.exit_value(self.inst) if self.owned else M.valuation(self.target)
        bottom = config.footer_y() - 8
        half = (config.SCREEN_WIDTH - 80 - 20) // 2

        # ---- panneau valorisation ----
        vpanel = pygame.Rect(40, top, half, 200)
        vinner = widgets.draw_panel(surf, vpanel, "Valorisation (comparables + DCF)", config.COL_CYAN)
        rows = [
            ("EBITDA", widgets.format_money(val["ebitda"], cur)),
            ("EV — comparables", widgets.format_money(val["comps_ev"], cur)),
            ("EV — DCF", widgets.format_money(val["dcf_ev"], cur)),
            ("EV retenue (juste valeur)", widgets.format_money(val["fair_ev"], cur)),
            ("WACC utilisé", f"{val['wacc']*100:.1f}%"),
            ("Valeur des fonds propres", widgets.format_money(val["equity_value"], cur)),
        ]
        y = vinner.y
        for label, value in rows:
            widgets.draw_text(surf, label, (vinner.x, y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, value, (vinner.right, y), fonts.small(bold=True),
                              config.COL_WHITE, align="right")
            y += 28

        # ---- panneau profil / scores ----
        ppanel = pygame.Rect(40 + half + 20, top, half, 200)
        pinner = widgets.draw_panel(surf, ppanel, "Profil opérationnel", config.COL_AMBER)
        py = pinner.y
        widgets.draw_text(surf, "Chiffre d'affaires", (pinner.x, py), fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.format_money(d["revenue"], cur), (pinner.right, py),
                          fonts.small(bold=True), config.COL_WHITE, align="right")
        py += 28
        widgets.draw_text(surf, "Marge EBITDA", (pinner.x, py), fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{d['ebitda_margin']*100:.1f}%", (pinner.right, py),
                          fonts.small(bold=True), config.COL_WHITE, align="right")
        py += 28
        widgets.draw_text(surf, "Effectif", (pinner.x, py), fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{d['employees']:,}".replace(",", " "), (pinner.right, py),
                          fonts.small(bold=True), config.COL_WHITE, align="right")
        py += 28
        for label, key in (("Management", "management_score"), ("Moral des équipes", "morale"),
                            ("Efficacité opérationnelle", "efficiency")):
            v = d[key]
            widgets.draw_text(surf, label, (pinner.x, py), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{v:.0f}/100", (pinner.right, py),
                              fonts.small(bold=True), _score_col(v), align="right")
            py += 28

        lower_top = top + 210
        if not self.owned:
            self._draw_acquisition(surf, pygame.Rect(40, lower_top, config.SCREEN_WIDTH - 80,
                                                       bottom - lower_top), cur, val)
        else:
            self._draw_management(surf, pygame.Rect(40, lower_top, config.SCREEN_WIDTH - 80,
                                                      bottom - lower_top), cur, val)

    def _draw_acquisition(self, surf, rect, cur, val):
        inner = widgets.draw_panel(surf, rect, "Financement & acquisition (LBO réel : cash + dette)",
                                   config.COL_UP)
        price = M.ask_price(self.target)
        terms = M.financing_terms(price, self.debt_pct)
        x, y = inner.x, inner.y
        widgets.draw_text(surf, f"Prix demandé (juste valeur + prime de contrôle {M.CONTROL_PREMIUM*100:.0f}%) : "
                                f"{widgets.format_money(price, cur)}",
                          (x, y), fonts.small(), config.COL_TEXT)
        y += 32

        widgets.draw_text(surf, "Part financée par dette", (x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"{self.debt_pct*100:.0f}%", (x + 260, y), fonts.small(bold=True), config.COL_WHITE)
        self._debt_minus_rect = pygame.Rect(x + 330, y - 2, 24, 22)
        self._debt_plus_rect = pygame.Rect(x + 358, y - 2, 24, 22)
        for r, sym in ((self._debt_minus_rect, "-"), (self._debt_plus_rect, "+")):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, r)
            pygame.draw.rect(surf, config.COL_BORDER, r, 1)
            widgets.draw_text(surf, sym, r.center, fonts.body(bold=True), config.COL_AMBER, align="center")
        y += 36

        rows = [
            ("Montant emprunté (dette LBO)", widgets.format_money(terms["debt_amount"], cur)),
            ("Apport en fonds propres (votre cash)", widgets.format_money(terms["equity_cash"], cur)),
            ("Trésorerie disponible", widgets.format_money(self.app.gs.player.cash, cur)),
        ]
        for label, value in rows:
            widgets.draw_text(surf, label, (x, y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, value, (x + 420, y), fonts.small(bold=True), config.COL_WHITE)
            y += 26

        y += 10
        can_afford = self.app.gs.player.cash >= terms["equity_cash"]
        self._buy_rect = pygame.Rect(x, y, 260, 44)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if can_afford else config.COL_PANEL,
                         self._buy_rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_UP if can_afford else config.COL_BORDER, self._buy_rect, 1, border_radius=6)
        widgets.draw_text(surf, "ACQUÉRIR LA SOCIÉTÉ", self._buy_rect.center, fonts.body(bold=True),
                          config.COL_UP if can_afford else config.COL_TEXT_DIM, align="center")
        widgets.draw_text_wrapped(
            surf, "La dette est portée par la société elle-même : intérêts et amortissement sont "
            "prélevés sur son propre flux de trésorerie. En cas d'insuffisance prolongée, vous "
            "pouvez devoir éponger sur votre trésorerie personnelle, ou perdre la société (défaut).",
            (x + 280, y + 2), fonts.tiny(), config.COL_TEXT_DIM, inner.right - x - 290)

    def _draw_management(self, surf, rect, cur, val):
        half = (rect.w - 20) // 2
        spanel = pygame.Rect(rect.x, rect.y, half, rect.h)
        sinner = widgets.draw_panel(surf, spanel, "Suivi LBO", config.COL_AMBER)
        inst = self.inst
        x, y = sinner.x, sinner.y
        rows = [
            ("Dette restante", widgets.format_money(inst["debt_balance"], cur),
             config.COL_DOWN if inst["debt_balance"] > 0 else config.COL_UP),
            ("Coussin de trésorerie", widgets.format_money(inst["cash_buffer"], cur), config.COL_TEXT),
            ("Dividendes cumulés perçus", widgets.format_money(inst["cum_dividends"], cur), config.COL_UP),
            ("Fonds propres investis", widgets.format_money(inst["equity_invested"], cur), config.COL_TEXT_DIM),
            ("Valeur actuelle des fonds propres", widgets.format_money(max(0.0, val["equity_value"]), cur),
             config.COL_WHITE),
            ("Trimestres en détresse", f"{inst['distress_quarters']}/3",
             config.COL_DOWN if inst["distress_quarters"] > 0 else config.COL_UP),
        ]
        for label, value, col in rows:
            widgets.draw_text(surf, label, (x, y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, value, (sinner.right, y), fonts.small(bold=True), col, align="right")
            y += 28

        y += 12
        moic = ((max(0.0, val["equity_value"]) + inst["cum_dividends"]) / inst["equity_invested"]
                if inst["equity_invested"] else 0.0)
        widgets.draw_text(surf, f"MOIC latent : {moic:.2f}x", (x, y), fonts.body(bold=True),
                          config.COL_UP if moic >= 1 else config.COL_DOWN)
        y += 40
        self._exit_rect = pygame.Rect(x, y, 260, 44)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._exit_rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_AMBER, self._exit_rect, 1, border_radius=6)
        widgets.draw_text(surf, "CÉDER (EXIT)", self._exit_rect.center, fonts.body(bold=True),
                          config.COL_AMBER, align="center")
        widgets.draw_text(surf, f"frais de cession {M.EXIT_FEE*100:.0f}%", (self._exit_rect.right + 14, y + 14),
                          fonts.tiny(), config.COL_TEXT_DIM)

        apanel = pygame.Rect(rect.x + half + 20, rect.y, rect.w - half - 20, rect.h)
        ainner = widgets.draw_panel(surf, apanel, "Axes d'amélioration (1 par trimestre)", config.COL_CYAN)
        can, reason = M.can_apply_action(self.app.gs.player, self.ticker)
        ax, ay = ainner.x, ainner.y
        if not can:
            widgets.draw_text(surf, reason, (ax, ay), fonts.small(), config.COL_WARN)
            ay += 26
        self._action_rects = {}
        row_h = (ainner.h - (ay - ainner.y)) / len(M.IMPROVEMENT_ACTIONS)
        row_h = max(24, min(34, row_h))
        for action in M.IMPROVEMENT_ACTIONS:
            cost = action["cost_pct"] * inst["revenue"]
            kind_col = config.COL_UP if action["kind"] == "positive" else config.COL_DOWN
            rect_a = pygame.Rect(ax - 4, ay - 2, ainner.w - 70, row_h - 4)
            self._action_rects[action["id"]] = rect_a if can else pygame.Rect(0, 0, 0, 0)
            bg = config.COL_PANEL_HEAD if can else config.COL_PANEL
            pygame.draw.rect(surf, bg, rect_a, border_radius=4)
            pygame.draw.rect(surf, kind_col, rect_a, 1, border_radius=4)
            widgets.draw_text(surf, widgets.fit_text(action["label"], fonts.tiny(bold=True), rect_a.w - 16),
                              (rect_a.x + 8, rect_a.y + 3), fonts.tiny(bold=True), config.COL_TEXT)
            cost_txt = (f"-{widgets.format_money(cost, cur)}" if cost >= 0
                        else f"+{widgets.format_money(-cost, cur)}")
            widgets.draw_text(surf, cost_txt, (rect_a.right - 6, rect_a.y + 3), fonts.tiny(bold=True),
                              kind_col, align="right")
            ay += row_h

    # ------------------------------------------------------ onglet ÉTATS FINANCIERS
    def _draw_statements(self, surf, top, cur):
        bottom = config.footer_y() - 8
        p = self.app.gs.player
        years_elapsed = (p.day - 1) // 365
        base_year = BASE_FISCAL_YEAR + years_elapsed
        block = M.statements_for(self.data, base_year, n_years=5)
        widgets.draw_text(surf, f"Montants en {cur} · 5 derniers exercices (N … N-4)",
                          (40, top - 4), fonts.small(), config.COL_TEXT_DIM)
        ttop = top + 20
        ph = bottom - ttop
        half = (config.SCREEN_WIDTH - 80 - 20) // 2

        inc_rows = []
        for r in range(len(block[0]["income"]["lines"])):
            inc_rows.append((block[0]["income"]["lines"][r]["label"],
                             [b["income"]["lines"][r]["value"] for b in block]))
        self._draw_table(surf, pygame.Rect(40, ttop, half, ph), "Compte de résultat",
                         inc_rows, block, config.COL_CYAN)

        bal_rows = []
        for r in range(len(block[0]["balance"]["assets_lines"])):
            bal_rows.append((block[0]["balance"]["assets_lines"][r]["label"],
                             [b["balance"]["assets_lines"][r]["value"] for b in block]))
        for r in range(len(block[0]["balance"]["liab_lines"])):
            bal_rows.append((block[0]["balance"]["liab_lines"][r]["label"],
                             [b["balance"]["liab_lines"][r]["value"] for b in block]))
        self._draw_table(surf, pygame.Rect(40 + half + 20, ttop, half, ph), "Bilan",
                         bal_rows, block, config.COL_AMBER)

    def _draw_table(self, surf, rect, title, rows_by_year, block, accent):
        inner = widgets.draw_panel(surf, rect, title, accent)
        years = [b["year"] for b in block]
        colw = 92
        xs = [inner.right - colw * (len(years) - k) for k in range(len(years))]
        label_w = max(10, xs[0] - inner.x - 10)   # marge avant la 1ère colonne de chiffres
        for k, yr in enumerate(years):
            tag = "N" if k == 0 else f"N-{k}"
            widgets.draw_text(surf, f"{yr} ({tag})", (xs[k] + colw - 8, inner.y),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM, align="right")
        y = inner.y + 22
        mp = pygame.mouse.get_pos()
        for label, vals in rows_by_year:
            emph = label in _EMPH
            lab_col = config.COL_AMBER if emph else config.COL_TEXT_DIM
            font = fonts.small(bold=emph)
            fitted = widgets.fit_text(label, font, label_w)
            widgets.draw_text_fit(surf, label, (inner.x, y), font, lab_col, max_width=label_w)
            if fitted != label:
                row_rect = pygame.Rect(inner.x, y, label_w, 18)
                if row_rect.collidepoint(mp):
                    self._tooltip = (label, mp)
            for k, v in enumerate(vals):
                col = config.COL_WHITE if emph else config.COL_TEXT
                if v < -0.5 and not emph:
                    col = config.COL_DOWN
                widgets.draw_text(surf, _fm(v), (xs[k] + colw - 8, y),
                                  fonts.small(bold=emph), col, align="right")
            if emph:
                pygame.draw.line(surf, config.COL_BORDER, (inner.x, y + 18),
                                 (inner.right, y + 18), 1)
            y += 23
