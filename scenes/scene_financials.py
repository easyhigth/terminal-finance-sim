"""
scene_financials.py — États financiers complets d'une société (façon FA Bloomberg).

Affiche le COMPTE DE RÉSULTAT et le BILAN sur trois exercices (N, N-1, N-2).
Les chiffres sont cohérents (cf. core/financials) et évoluent avec le temps de
jeu : passé un an, l'exercice courant avance. Ouvert via FA <ticker>.
"""
import pygame
from core import config
from core import financials as F
from core.scene_manager import Scene
from ui import fonts, widgets

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
        self.block = F.statements(m, self.ticker, self.fy) if m else []
        self.name = ""
        self.cur = "$"
        if m and self.ticker in m.ticker_idx:
            c = m.companies[m.ticker_idx[self.ticker]]
            self.name = c["name"]
            self.cur = config.CONTINENTS.get(c["region"], {}).get("currency", "$")
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.fiche_btn = widgets.Button((210, config.SCREEN_HEIGHT - 70, 200, 46),
                                        "FICHE (DES)", config.COL_CYAN)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.fiche_btn.handle(event):
            self.app.scenes.go("company", ticker=self.ticker, return_to=self.return_to)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.fiche_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def _draw_table(self, surf, rect, title, rows_by_year, accent):
        """rows_by_year : liste de (label, [valeurs par exercice])."""
        inner = widgets.draw_panel(surf, rect, title, accent)
        years = [b["year"] for b in self.block]
        colw = 96
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
        widgets.draw_text(surf, f"ÉTATS FINANCIERS — {self.ticker}", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self.block:
            widgets.draw_text(surf, "Société introuvable.", (42, 90),
                              fonts.body(), config.COL_DOWN)
            self.back_btn.draw(surf)
            return
        widgets.draw_text(surf, f"{self.name} · montants en M {self.cur} · "
                                f"exercice courant {self.fy} (avance avec le temps de jeu)",
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        ph = config.footer_y() - 8 - 100
        half = (config.SCREEN_WIDTH - 80 - 20) // 2

        # compte de résultat (gauche)
        inc_rows = []
        for r, line in enumerate(self.block[0]["income"]["lines"]):
            inc_rows.append((line["label"],
                             [b["income"]["lines"][r]["value"] for b in self.block]))
        self._draw_table(surf, pygame.Rect(40, 100, half, ph),
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
        self._draw_table(surf, pygame.Rect(40 + half + 20, 100, half, ph),
                         "Bilan", bal_rows, config.COL_AMBER)

        self.back_btn.draw(surf)
        self.fiche_btn.draw(surf)
