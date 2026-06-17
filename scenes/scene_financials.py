"""
scene_financials.py — Santé financière complète d'une société (façon FA Bloomberg).

Analyse complète de l'entreprise : statistiques clés (cours, valorisation,
marges, bêta…), graphe de cours sur 5 ans, puis COMPTE DE RÉSULTAT et BILAN sur
CINQ exercices (N … N-4). Les chiffres sont cohérents (cf. core/financials) et
évoluent avec le temps de jeu. Mêmes informations que la fiche société, vue
sous l'angle « santé financière ». Ouvert via FA <ticker> ou « santé financière ».
"""
import pygame
from core import config
from core import financials as F
from core import charts as charts
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

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.fiche_btn.handle(event):
            self.app.scenes.go("company", ticker=self.ticker, return_to=self.return_to)
        if self.graph_btn.handle(event):
            self.app.scenes.go("graph", kind="line", tickers=[self.ticker], return_to=self.return_to)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.fiche_btn.update(mp, dt)
        self.graph_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def _draw_table(self, surf, rect, title, rows_by_year, accent):
        """rows_by_year : liste de (label, [valeurs par exercice])."""
        inner = widgets.draw_panel(surf, rect, title, accent)
        years = [b["year"] for b in self.block]
        colw = 84
        x_label = inner.x
        xs = [inner.right - colw * (len(years) - k) for k in range(len(years))]
        # en-tête années
        for k, yr in enumerate(years):
            tag = "N" if k == 0 else f"N-{k}"
            widgets.draw_text(surf, f"{yr} ({tag})", (xs[k] + colw - 8, inner.y),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM, align="right")
        y = inner.y + 22
        for label, vals in rows_by_year:
            emph = label in _EMPH
            lab_col = config.COL_AMBER if emph else config.COL_TEXT_DIM
            widgets.draw_text(surf, label, (x_label, y),
                              fonts.small(bold=emph), lab_col)
            for k, v in enumerate(vals):
                col = config.COL_WHITE if emph else config.COL_TEXT
                if v < -0.5 and not emph:
                    col = config.COL_DOWN
                widgets.draw_text(surf, _fm(v), (xs[k] + colw - 8, y),
                                  fonts.small(bold=emph), col, align="right")
            if emph:
                pygame.draw.line(surf, config.COL_BORDER, (x_label, y + 18),
                                 (inner.right, y + 18), 1)
            y += 23

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, f"SANTÉ FINANCIÈRE — {self.ticker}", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if self.error:
            widgets.draw_error_panel(surf, self.error,
                                     "Utilisez SEARCH <texte> depuis le terminal.", top=90)
            self.back_btn.draw(surf)
            return
        widgets.draw_text(surf, f"{self.name} · montants en M {self.cur} · analyse complète "
                                f"(stats, graphe 5 ans, {N_YEARS} exercices)",
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        # ---- bandeau supérieur : statistiques clés + graphe de cours 5 ans ----
        top = pygame.Rect(40, 100, config.SCREEN_WIDTH - 80, 150)
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
                         "Compte de résultat", inc_rows, config.COL_CYAN)

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
                         "Bilan", bal_rows, config.COL_AMBER)

        self.back_btn.draw(surf)
        self.fiche_btn.draw(surf)
        self.graph_btn.draw(surf)

    def _draw_overview(self, surf, rect):
        """Statistiques clés (mêmes que la fiche) + graphe de cours sur 5 ans."""
        mt = self.metrics
        half = (rect.w - 20) // 2
        stats = pygame.Rect(rect.x, rect.y, half, rect.h)
        inner = widgets.draw_panel(surf, stats, "Statistiques clés", self.accent)
        if mt:
            f2 = lambda v, s="", d=2: ("n.m." if v is None else f"{v:.{d}f}{s}")
            chg = mt["change_pct"]
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{mt['price']:,.2f} {self.cur}", (inner.x, inner.y),
                              fonts.head(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.1f}% (1 an)",
                              (inner.right, inner.y), fonts.small(bold=True), ccol, align="right")
            cols = [
                [("Capitalisation", widgets.format_money(mt["mktcap"] * 1e6, self.cur)),
                 ("P/E", f2(mt["pe"], "x", 1)), ("EV/EBITDA", f2(mt["ev_ebitda"], "x", 1)),
                 ("P/Sales", f2(mt["ps"], "x", 1))],
                [("Marge nette", f2(mt["net_margin"] * 100, "%", 1)),
                 ("Dette/EBITDA", f2(mt["nd_ebitda"], "x", 1)),
                 ("Rendement div.", f2(mt["div_yield"] * 100, "%", 2)),
                 ("Bêta", f2(mt["beta"], "", 2))],
            ]
            cw = inner.w // 2
            for ci, col in enumerate(cols):
                x = inner.x + ci * cw
                y = inner.y + 30
                for label, val in col:
                    widgets.draw_text(surf, label, (x, y), fonts.tiny(), config.COL_TEXT_DIM)
                    widgets.draw_text(surf, str(val), (x + cw - 16, y), fonts.small(bold=True),
                                      config.COL_WHITE, align="right")
                    y += 24
        # graphe de cours 5 ans (droite)
        chart = pygame.Rect(rect.x + half + 20, rect.y, rect.w - half - 20, rect.h)
        cinner = widgets.draw_panel(surf, chart, "Cours — 5 ans", self.accent)
        hist = self.app.market.history_of(self.ticker) if self.app.market else []
        if len(hist) >= 2:
            plot = pygame.Rect(cinner.x, cinner.y + 4, cinner.w, cinner.h - 20)
            col = config.COL_UP if hist[-1] >= hist[0] else config.COL_DOWN
            widgets.draw_series(surf, plot, hist, col)
            chg = (hist[-1] / hist[0] - 1) * 100 if hist[0] else 0.0
            widgets.draw_text(surf, f"{hist[-1]:,.2f} {self.cur}  ({chg:+.1f}% sur 5 ans)",
                              (cinner.x, cinner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)
        else:
            widgets.draw_text(surf, "Historique en constitution (ADV).",
                              (cinner.x, cinner.y), fonts.small(), config.COL_TEXT_DIM)
