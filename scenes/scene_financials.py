"""
scene_financials.py — Santé financière complète d'une société (façon FA Bloomberg).

Analyse complète de l'entreprise : statistiques clés (cours, valorisation,
marges, bêta…), graphe de cours sur 5 ans, puis COMPTE DE RÉSULTAT et BILAN sur
CINQ exercices (N … N-4). Les chiffres sont cohérents (cf. core/financials) et
évoluent avec le temps de jeu. Mêmes informations que la fiche société, vue
sous l'angle « santé financière ». Ouvert via FA <ticker> ou « santé financière ».
"""
import pygame

from core import charts as charts
from core import config
from core import financials as F
from core.scene_manager import Scene
from ui import fonts, widgets

N_YEARS = 5    # historique d'exercices affiché

# lignes mises en avant (sous-totaux / totaux)
_EMPH = {"Marge brute", "EBITDA", "Résultat d'exploitation (EBIT)", "Résultat avant impôt",
         "Résultat net", "Total actifs courants", "TOTAL ACTIF",
         "Total passifs courants", "Total passif (hors CP)", "Capitaux propres",
         "TOTAL PASSIF + CP"}


def _fm(v):
    """Montant en M, séparateur de milliers, négatifs entre parenthèses."""
    if abs(v) < 0.5:
        return "—"
    return f"({abs(v):,.0f})".replace(",", " ") if v < 0 else f"{v:,.0f}".replace(",", " ")


class FinancialsScene(Scene):
    def on_enter(self, **kwargs):
        self.ticker = (kwargs.get("ticker") or "").upper()
        self.return_to = kwargs.get("return_to", "terminal")
        p = self.app.gs.player
        base = config.BASE_FISCAL_YEAR
        self.fy = F.fiscal_year(p, base)
        m = self.app.market
        self.block = F.statements(m, self.ticker, self.fy, n_years=N_YEARS) if m else []
        self.metrics = m.metrics(self.ticker) if m else None
        self.sector_med = (m.sector_medians(self.metrics["sector"])
                           if m and self.metrics else None)
        # décomposition factorielle du dernier pas, pour 1 action détenue
        # (réutilise m.factor_attribution ; donne la part world/secteur/région/
        # spécifique/dérive du rendement du jour, en devise par action)
        self.attribution = (m.factor_attribution({self.ticker: 1.0})
                            if m and self.metrics else None)
        self.error = None if self.block else f"Société introuvable : {self.ticker}"
        self.name = ""
        self.cur = "$"
        self.accent = config.COL_AMBER
        if m and self.ticker in m.ticker_idx:
            c = m.companies[m.ticker_idx[self.ticker]]
            self.name = c["name"]
            self.cur = config.CONTINENTS.get(c["region"], {}).get("currency", "$")
            self.accent = config.CONTINENTS.get(c["region"], {}).get("color", config.COL_AMBER)
            m.track_company(self.ticker)
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.fiche_btn = widgets.Button((210, config.SCREEN_HEIGHT - 70, 220, 46),
                                        "FICHE COMPLÈTE (DES)", config.COL_CYAN)
        self.graph_btn = widgets.Button((440, config.SCREEN_HEIGHT - 70, 160, 46),
                                        "GRAPHE (GP)", config.COL_AMBER)
        self.sheet_inc_btn = widgets.Button((610, config.SCREEN_HEIGHT - 70, 200, 46),
                                            "→ TABLEUR (CR)", config.COL_UP)
        self.sheet_bal_btn = widgets.Button((820, config.SCREEN_HEIGHT - 70, 200, 46),
                                            "→ TABLEUR (BILAN)", config.COL_UP)
        self.buy_btn = widgets.Button((1030, config.SCREEN_HEIGHT - 70, 100, 46),
                                      "ACHAT", config.COL_UP)
        self.sell_btn = widgets.Button((1140, config.SCREEN_HEIGHT - 70, 100, 46),
                                       "VENTE", config.COL_DOWN)
        self.scroll_inc = 0
        self.scroll_bal = 0
        self._max_scroll_inc = 0
        self._max_scroll_bal = 0
        self._inc_rect = None
        self._bal_rect = None
        self._tooltip = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.fiche_btn.handle(event):
            self.app.scenes.go("company", ticker=self.ticker, return_to=self.return_to)
        if self.graph_btn.handle(event):
            self.app.scenes.go("graph", kind="line", tickers=[self.ticker], return_to=self.return_to)
        if not self.error:
            if self.sheet_inc_btn.handle(event):
                self._open_spreadsheet("income")
            if self.sheet_bal_btn.handle(event):
                self._open_spreadsheet("balance")
            if self.buy_btn.handle(event):
                self.app.pending_input = f"BUY {self.ticker} "
                self.app.scenes.go("terminal")
            if self.sell_btn.handle(event):
                self.app.pending_input = f"SELL {self.ticker} ALL"
                self.app.scenes.go("terminal")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -36 if event.button == 4 else 36
            if self._inc_rect and self._inc_rect.collidepoint(event.pos):
                self.scroll_inc = max(0, min(self._max_scroll_inc, self.scroll_inc + delta))
                return
            if self._bal_rect and self._bal_rect.collidepoint(event.pos):
                self.scroll_bal = max(0, min(self._max_scroll_bal, self.scroll_bal + delta))
                return

    def _open_spreadsheet(self, which):
        years = [b["year"] for b in self.block]
        if which == "income":
            title = f"{self.ticker} — Compte de résultat"
            lines = self.block[0]["income"]["lines"]
            rows = [(line["label"], [b["income"]["lines"][r]["value"] for b in self.block])
                    for r, line in enumerate(lines)]
        else:
            title = f"{self.ticker} — Bilan"
            rows = []
            n_assets = len(self.block[0]["balance"]["assets_lines"])
            for r in range(n_assets):
                rows.append((self.block[0]["balance"]["assets_lines"][r]["label"],
                             [b["balance"]["assets_lines"][r]["value"] for b in self.block]))
            for r in range(len(self.block[0]["balance"]["liab_lines"])):
                rows.append((self.block[0]["balance"]["liab_lines"][r]["label"],
                             [b["balance"]["liab_lines"][r]["value"] for b in self.block]))
        self.app.scenes.go("spreadsheet", return_to="financials",
                           return_kwargs={"ticker": self.ticker, "return_to": self.return_to},
                           import_data={"title": title, "years": years, "rows": rows})

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.fiche_btn.update(mp, dt)
        self.graph_btn.update(mp, dt)
        self.sheet_inc_btn.update(mp, dt)
        self.sheet_bal_btn.update(mp, dt)
        self.buy_btn.update(mp, dt)
        self.sell_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def _draw_table(self, surf, rect, title, rows_by_year, accent, which):
        """rows_by_year : liste de (label, [valeurs par exercice]).

        Hauteur de ligne fixe ; si le tableau (bilan, ~14 lignes) ne tient pas
        dans l'espace disponible, défile (molette) au lieu de déborder sur le
        footer. Les libellés tronqués affichent une bulle au survol."""
        inner = widgets.draw_panel(surf, rect, title, accent)
        years = [b["year"] for b in self.block]
        colw = 84
        x_label = inner.x
        xs = [inner.right - colw * (len(years) - k) for k in range(len(years))]
        label_w = max(10, xs[0] - x_label - 10)   # marge avant la 1ère colonne de chiffres
        # en-tête années
        for k, yr in enumerate(years):
            tag = "N" if k == 0 else f"N-{k}"
            widgets.draw_text(surf, f"{yr} ({tag})", (xs[k] + colw - 8, inner.y),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM, align="right")
        head_h = 22
        row_h = 20
        list_area = pygame.Rect(inner.x - 4, inner.y + head_h, inner.w + 8, inner.h - head_h)
        if which == "inc":
            self._inc_rect = list_area
            scroll = self.scroll_inc
        else:
            self._bal_rect = list_area
            scroll = self.scroll_bal
        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y + head_h - scroll
        for label, vals in rows_by_year:
            if (list_area.top - row_h) < y < list_area.bottom:
                emph = label in _EMPH
                lab_col = config.COL_AMBER if emph else config.COL_TEXT_DIM
                font = fonts.small(bold=emph)
                fitted = widgets.fit_text(label, font, label_w)
                widgets.draw_text(surf, fitted, (x_label, y), font, lab_col)
                if fitted != label:
                    row_rect = pygame.Rect(x_label, y, label_w, row_h)
                    if row_rect.collidepoint(mp):
                        self._tooltip = (label, mp)
                for k, v in enumerate(vals):
                    col = config.COL_WHITE if emph else config.COL_TEXT
                    if v < -0.5 and not emph:
                        col = config.COL_DOWN
                    widgets.draw_text(surf, _fm(v), (xs[k] + colw - 8, y),
                                      fonts.small(bold=emph), col, align="right")
                if emph:
                    pygame.draw.line(surf, config.COL_BORDER, (x_label, y + row_h - 5),
                                     (inner.right, y + row_h - 5), 1)
            y += row_h
        surf.set_clip(prev_clip)
        content_h = (y + scroll) - (inner.y + head_h)
        max_scroll = max(0, content_h - list_area.h)
        scroll = max(0, min(max_scroll, scroll))
        if which == "inc":
            self._max_scroll_inc, self.scroll_inc = max_scroll, scroll
        else:
            self._max_scroll_bal, self.scroll_bal = max_scroll, scroll
        widgets.draw_scrollbar(surf, rect, list_area, scroll, max_scroll, content_h)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        self._tooltip = None
        widgets.draw_text(surf, f"SANTÉ FINANCIÈRE — {self.ticker}", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if self.error:
            widgets.draw_error_panel(surf, self.error,
                                     "Utilisez SEARCH <texte> depuis le terminal.", top=90)
            self.back_btn.draw(surf)
            return
        widgets.draw_text(surf, f"{self.name} · montants en M {self.cur} · analyse complète "
                                f"(stats, résultats, valeur relative, attribution, "
                                f"{N_YEARS} exercices)",
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        # ---- bandeau supérieur : stats clés, résultats/valeur relative, cours+attribution ----
        top = pygame.Rect(40, 100, config.SCREEN_WIDTH - 80, 198)
        self._draw_overview(surf, top)

        ty = top.bottom + 10
        ph = config.footer_y() - 8 - ty
        half = (config.SCREEN_WIDTH - 80 - 20) // 2

        # compte de résultat (gauche)
        inc_rows = []
        for r, line in enumerate(self.block[0]["income"]["lines"]):
            inc_rows.append((line["label"],
                             [b["income"]["lines"][r]["value"] for b in self.block]))
        self._draw_table(surf, pygame.Rect(40, ty, half, ph),
                         "Compte de résultat", inc_rows, config.COL_CYAN, "inc")

        # bilan (droite) : actif puis passif + CP
        bal_rows = []
        n_assets = len(self.block[0]["balance"]["assets_lines"])
        for r in range(n_assets):
            bal_rows.append((self.block[0]["balance"]["assets_lines"][r]["label"],
                             [b["balance"]["assets_lines"][r]["value"] for b in self.block]))
        for r in range(len(self.block[0]["balance"]["liab_lines"])):
            bal_rows.append((self.block[0]["balance"]["liab_lines"][r]["label"],
                             [b["balance"]["liab_lines"][r]["value"] for b in self.block]))
        self._draw_table(surf, pygame.Rect(40 + half + 20, ty, half, ph),
                         "Bilan", bal_rows, config.COL_AMBER, "bal")

        self.back_btn.draw(surf)
        self.fiche_btn.draw(surf)
        self.graph_btn.draw(surf)
        self.sheet_inc_btn.draw(surf)
        self.sheet_bal_btn.draw(surf)
        self.buy_btn.draw(surf)
        self.sell_btn.draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    def _draw_overview(self, surf, rect):
        """Trois panneaux : (1) statistiques clés, (2) résultats/guidance +
        valeur relative vs secteur, (3) graphe de cours 5 ans + attribution
        factorielle du dernier pas. Tout est calculé à partir de m.metrics(),
        m.sector_medians() et m.factor_attribution(), déjà utilisés ailleurs
        (fiche société, commande RV, desk risque) — aucune nouvelle donnée
        fictive n'est introduite ici."""
        mt = self.metrics
        cw = (rect.w - 40) // 3
        stats = pygame.Rect(rect.x, rect.y, cw, rect.h)
        earn = pygame.Rect(rect.x + cw + 20, rect.y, cw, rect.h)
        chart = pygame.Rect(rect.x + 2 * (cw + 20), rect.y, rect.w - 2 * (cw + 20), rect.h)

        self._draw_stats_panel(surf, stats, mt)
        self._draw_earnings_panel(surf, earn, mt)
        self._draw_chart_panel(surf, chart, mt)

    def _draw_stats_panel(self, surf, rect, mt):
        inner = widgets.draw_panel(surf, rect, "Statistiques clés", self.accent)
        if not mt:
            return
        f2 = lambda v, s="", d=2: ("n.m." if v is None else f"{v:.{d}f}{s}")
        chg = mt["change_pct"]
        ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{mt['price']:,.2f} {self.cur}", (inner.x, inner.y),
                          fonts.head(bold=True), config.COL_WHITE)
        widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.1f}% (1 an)",
                          (inner.right, inner.y), fonts.small(bold=True), ccol, align="right")
        rows = [
            ("Capitalisation", widgets.format_money(mt["mktcap"] * 1e6, self.cur)),
            ("P/E", f2(mt["pe"], "x", 1)), ("EV/EBITDA", f2(mt["ev_ebitda"], "x", 1)),
            ("P/Sales", f2(mt["ps"], "x", 1)),
            ("Marge nette", f2(mt["net_margin"] * 100, "%", 1)),
            ("Dette/EBITDA", f2(mt["nd_ebitda"], "x", 1)),
            ("Notation crédit", mt["credit_rating"]),
            ("Rendement div.", f2(mt["div_yield"] * 100, "%", 2)),
            ("Bêta", f2(mt["beta"], "", 2)),
        ]
        y = inner.y + 28
        for label, val in rows:
            widgets.draw_text(surf, label, (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, str(val), (inner.right, y), fonts.small(bold=True),
                              config.COL_WHITE, align="right")
            y += 13

    def _draw_earnings_panel(self, surf, rect, mt):
        """Derniers résultats trimestriels (beat/miss, guidance, anticipation,
        PEAD) puis valeur relative vs médiane du secteur (mêmes champs que la
        commande RV du terminal)."""
        inner = widgets.draw_panel(surf, rect, "Résultats & valeur relative", self.accent)
        if not mt:
            return
        y = inner.y
        le = mt.get("last_earnings")
        if le:
            ecol = config.COL_UP if le["beat"] else config.COL_DOWN
            verb = "BEAT" if le["beat"] else "MISS"
            widgets.draw_text(surf, f"Derniers résultats : {verb}", (inner.x, y),
                              fonts.small(bold=True), ecol)
            y += 17
            widgets.draw_text_fit(surf, f"Surprise {le['surprise']*100:+.1f}%  ·  "
                                        f"croissance CA {le['growth']*100:+.1f}%",
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM,
                                  max_width=inner.w)
            y += 15
            g_label = le.get("guidance_label")
            if g_label:
                widgets.draw_text(surf, f"Guidance {g_label}", (inner.x, y),
                                  fonts.tiny(), config.COL_TEXT_DIM)
                y += 15
        else:
            widgets.draw_text(surf, "Aucun résultat publié pour l'instant.", (inner.x, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            y += 15
        if mt.get("earnings_anticipation"):
            widgets.draw_text(surf, f"⏳ Publication dans {mt['steps_to_earnings']} pas",
                              (inner.x, y), fonts.tiny(), config.COL_WARN)
            y += 15
        pead = mt.get("pead_drift_remaining") or 0.0
        if abs(pead) > 1e-4:
            pcol = config.COL_UP if pead > 0 else config.COL_DOWN
            widgets.draw_text(surf, f"↗ Drift post-résultats résiduel : {pead*100:+.2f}%",
                              (inner.x, y), fonts.tiny(), pcol)
            y += 15

        y += 4
        pygame.draw.line(surf, config.COL_BORDER, (inner.x, y), (inner.right, y), 1)
        y += 5
        med = self.sector_med
        widgets.draw_text(surf, f"Vs secteur {mt['sector']} ({med['n'] if med else 0} pairs)",
                          (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 16

        def fmt(v):
            return f"{v:.1f}x" if v else "n.m."

        def verdict(val, ref):
            if not val or not ref:
                return ("—", config.COL_TEXT_DIM)
            if val < ref * 0.9:
                return ("décoté", config.COL_UP)
            if val > ref * 1.1:
                return ("cher", config.COL_DOWN)
            return ("en ligne", config.COL_TEXT)

        for label, key in [("P/E", "pe"), ("EV/EBITDA", "ev_ebitda"), ("P/S", "ps")]:
            v, r = mt.get(key), (med.get(key) if med else None)
            txt, col = verdict(v, r)
            widgets.draw_text(surf, f"{label} {fmt(v)} / méd. {fmt(r)}", (inner.x, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, txt, (inner.right, y), fonts.tiny(bold=True),
                              col, align="right")
            y += 15

    def _draw_chart_panel(self, surf, rect, mt):
        """Graphe de cours 5 ans + attribution factorielle du dernier pas
        (m.factor_attribution, déjà utilisée pour le P&L du portefeuille,
        appliquée ici à une action détenue de ce titre)."""
        cinner = widgets.draw_panel(surf, rect, "Cours — 5 ans & attribution", self.accent)
        chart_h = cinner.h - 56     # réserve fixe en bas pour la ligne d'attribution
        plot_rect = pygame.Rect(cinner.x, cinner.y, cinner.w, chart_h)
        hist = self.app.market.history_of(self.ticker) if self.app.market else []
        if len(hist) >= 2:
            plot = pygame.Rect(plot_rect.x, plot_rect.y + 4, plot_rect.w, plot_rect.h - 34)
            col = config.COL_UP if hist[-1] >= hist[0] else config.COL_DOWN
            widgets.draw_series(surf, plot, hist, col, mouse_pos=pygame.mouse.get_pos(),
                                y_fmt=lambda v: f"{v:,.2f} {self.cur}", show_pct=True)
            widgets.draw_chart_x_labels(surf, plot, [
                (0.0, "-5 ans"), (0.5, "-2,5 ans"), (1.0, "aujourd'hui"),
            ])
            chg = (hist[-1] / hist[0] - 1) * 100 if hist[0] else 0.0
            widgets.draw_text(surf, f"{hist[-1]:,.2f} {self.cur}  ({chg:+.1f}% sur 5 ans)",
                              (plot_rect.x, plot_rect.bottom - 14), fonts.tiny(),
                              config.COL_TEXT_DIM)
        else:
            widgets.draw_text(surf, "Historique en constitution (ADV).",
                              (plot_rect.x, plot_rect.y), fonts.small(), config.COL_TEXT_DIM)

        # attribution factorielle du dernier pas (drift, monde, secteur, région,
        # spécifique), exprimée en % du rendement total pour rester lisible
        # indépendamment de la taille de la position fictive utilisée au calcul.
        # Réutilise m.factor_attribution (même calcul que le P&L du portefeuille),
        # affiché en une seule ligne compacte pour tenir dans le panneau.
        y = plot_rect.bottom + 8
        pygame.draw.line(surf, config.COL_BORDER, (cinner.x, y), (cinner.right, y), 1)
        y += 6
        widgets.draw_text(surf, "Attribution du dernier pas", (cinner.x, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 16
        attr = self.attribution
        total = attr["total"] if attr else 0.0
        if attr and abs(total) > 1e-9:
            parts = [("Dérive", "drift"), ("Monde", "world"), ("Secteur", "sector"),
                     ("Région", "region"), ("Spécif.", "specific")]
            seg_w = cinner.w // len(parts)
            for k, (label, key) in enumerate(parts):
                share = attr[key] / total * 100.0
                col = config.COL_UP if attr[key] >= 0 else config.COL_DOWN
                x = cinner.x + k * seg_w
                widgets.draw_text(surf, label, (x, y), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"{share:+.0f}%", (x, y + 14),
                                  fonts.tiny(bold=True), col)
        else:
            widgets.draw_text(surf, "Pas de mouvement de cours au dernier pas.",
                              (cinner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
