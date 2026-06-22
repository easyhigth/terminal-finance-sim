"""
scene_company.py — Fiche société type Bloomberg.
Affiche prix, capitalisation, multiples (P/E, EV/EBITDA), marges, dette,
dividende, bêta et un graphe de prix. Ouverte via la commande COMPANY <ticker>.
"""
import pygame

from core import config
from core.scene_manager import Scene
from ui import fonts, widgets


def _fmt(v, suffix="", dec=2, na="n.m."):
    if v is None:
        return na
    return f"{v:.{dec}f}{suffix}"


class CompanyScene(Scene):
    def on_enter(self, **kwargs):
        self.ticker = (kwargs.get("ticker") or "").upper()
        self.return_to = kwargs.get("return_to", "terminal")
        self.return_kwargs = kwargs.get("return_kwargs") or {}
        if self.app.market is not None:
            self.app.market.track_company(self.ticker)
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT - 70, 200, 46),
            f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.fa_btn = widgets.Button(
            (250, config.SCREEN_HEIGHT - 70, 220, 46), "ÉTATS FINANCIERS (FA)", config.COL_CYAN)
        self.graph_btn = widgets.Button(
            (480, config.SCREEN_HEIGHT - 70, 160, 46), "GRAPHE (GP)", config.COL_AMBER)
        self.buy_btn = widgets.Button(
            (650, config.SCREEN_HEIGHT - 70, 110, 46), "ACHAT", config.COL_UP)
        self.sell_btn = widgets.Button(
            (770, config.SCREEN_HEIGHT - 70, 110, 46), "VENTE", config.COL_DOWN)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to, **self.return_kwargs)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to, **self.return_kwargs)
        if self.fa_btn.handle(event):
            self.app.scenes.go("financials", ticker=self.ticker, return_to=self.return_to)
        if self.graph_btn.handle(event):
            self.app.scenes.go("graph", kind="line", tickers=[self.ticker], return_to=self.return_to)
        if self.buy_btn.handle(event):
            self.app.pending_input = f"BUY {self.ticker} "
            self.app.scenes.go("terminal")
        if self.sell_btn.handle(event):
            self.app.pending_input = f"SELL {self.ticker} ALL"
            self.app.scenes.go("terminal")

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.fa_btn.update(mp, dt)
        self.graph_btn.update(mp, dt)
        self.buy_btn.update(mp, dt)
        self.sell_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m = self.app.market
        mt = m.metrics(self.ticker) if m else None
        if not mt:
            widgets.draw_error_panel(surf, f"Société introuvable : {self.ticker}",
                                     "Utilisez SEARCH <texte> depuis le terminal.")
            self.back_btn.draw(surf)
            return

        cur = config.CONTINENTS.get(mt["region"], {}).get("currency", "$")
        accent = config.CONTINENTS.get(mt["region"], {}).get("color", config.COL_AMBER)

        # en-tête
        widgets.draw_text(surf, f"{mt['ticker']}", (40, 24),
                          fonts.huge(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, mt["name"], (40, 104), fonts.head(), config.COL_WHITE)
        widgets.draw_badge(surf, mt["sector"], (40, 146), accent)
        widgets.draw_badge(surf, mt["region"], (160, 146), accent)

        # prix + variation
        chg = mt["change_pct"]
        chg_col = config.COL_UP if chg >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{mt['price']:,.2f} {cur}", (config.SCREEN_WIDTH - 40, 30),
                          fonts.title(bold=True), config.COL_WHITE, align="right")
        widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}% (1 an)",
                          (config.SCREEN_WIDTH - 40, 84), fonts.head(), chg_col, align="right")

        # reco de recherche (si disponible) ou invite
        r = self.app.gs.player.research.get(self.ticker)
        if r:
            rcol = (config.COL_UP if r["rating"] == "ACHAT" else
                    config.COL_DOWN if r["rating"] == "VENTE" else config.COL_WARN)
            widgets.draw_text(surf, f"RECO : {r['rating']}  ·  valeur intrinsèque "
                                    f"{r['fair']:.2f} {cur}  ·  potentiel {r['upside']:+.0f}%",
                              (config.SCREEN_WIDTH - 40, 120), fonts.small(bold=True),
                              rcol, align="right")
        else:
            widgets.draw_text(surf, "RESEARCH " + self.ticker + " pour une reco analyste",
                              (config.SCREEN_WIDTH - 40, 120), fonts.small(),
                              config.COL_TEXT_DIM, align="right")

        # derniers résultats trimestriels (surprise beat/miss + guidance)
        le = mt.get("last_earnings")
        if le:
            ecol = config.COL_UP if le["beat"] else config.COL_DOWN
            verb = "BEAT" if le["beat"] else "MISS"
            g_label = le.get("guidance_label")
            g_txt = f"  ·  guidance {g_label}" if g_label else ""
            widgets.draw_text(surf, f"RÉSULTATS : {verb}  surprise {le['surprise']*100:+.0f}%  "
                                    f"·  croissance CA {le['growth']*100:+.1f}%{g_txt}",
                              (config.SCREEN_WIDTH - 40, 150), fonts.small(bold=True),
                              ecol, align="right")

        # indicateurs d'anticipation / drift post-annonce (PEAD), si actifs
        badge_y = 176
        if mt.get("earnings_anticipation"):
            widgets.draw_text(surf, f"⏳ Publication dans {mt['steps_to_earnings']} pas",
                              (config.SCREEN_WIDTH - 40, badge_y), fonts.small(),
                              config.COL_WARN, align="right")
            badge_y += 22
        pead = mt.get("pead_drift_remaining") or 0.0
        if abs(pead) > 1e-4:
            pcol = config.COL_UP if pead > 0 else config.COL_DOWN
            widgets.draw_text(surf, f"↗ Drift post-résultats résiduel : {pead*100:+.2f}%",
                              (config.SCREEN_WIDTH - 40, badge_y), fonts.small(),
                              pcol, align="right")

        # panneau fondamentaux (2 sous-colonnes : valorisation / rentabilité-risque)
        ph = config.footer_y() - 8 - 190
        panel = pygame.Rect(40, 190, 560, ph)
        inner = widgets.draw_panel(surf, panel, "Fondamentaux & valorisation", accent)
        col_valo = [
            ("Capitalisation", widgets.format_money(mt["mktcap"] * 1e6, cur)),
            ("Chiffre d'affaires", widgets.format_money(mt["revenue"] * 1e6, cur)),
            ("EBITDA", widgets.format_money(mt["ebitda"] * 1e6, cur)),
            ("Résultat net", widgets.format_money(mt["net_income"] * 1e6, cur)),
            ("BPA (EPS)", _fmt(mt["eps"], " " + cur, 2)),
            ("P/E", _fmt(mt["pe"], "x", 1)),
            ("EV", widgets.format_money(mt["ev"] * 1e6, cur)),
            ("EV / EBITDA", _fmt(mt["ev_ebitda"], "x", 1)),
            ("P / Sales", _fmt(mt["ps"], "x", 1)),
        ]
        col_risk = [
            ("Marge nette", _fmt(mt["net_margin"] * 100, "%", 1)),
            ("Marge EBITDA", _fmt(mt["ebitda_margin"] * 100, "%", 1)),
            ("FCF yield", _fmt(mt["fcf_yield"], "%", 1)),
            ("Dette nette", widgets.format_money(mt["net_debt"] * 1e6, cur)),
            ("Dette / EBITDA", _fmt(mt["nd_ebitda"], "x", 1)),
            ("Notation crédit", mt["credit_rating"]),
            ("Rendement div.", _fmt(mt["div_yield"] * 100, "%", 2)),
            ("Payout", _fmt(mt["payout"], "%", 0)),
            ("Bêta", _fmt(mt["beta"], "", 2)),
            ("Actions (M)", _fmt(mt["shares"], "", 1)),
        ]
        cw = inner.w // 2
        for ci, col in enumerate((col_valo, col_risk)):
            x = inner.x + ci * cw
            xr = x + cw - 14
            y = inner.y
            for label, val in col:
                widgets.draw_text(surf, label, (x, y), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, str(val), (xr, y), fonts.small(bold=True),
                                  config.COL_WHITE, align="right")
                y += 26

        # panneau graphe de prix (chandeliers + moyennes mobiles)
        chart = pygame.Rect(620, 190, config.SCREEN_WIDTH - 660, ph)
        cinner = widgets.draw_panel(surf, chart, "Cours — chandeliers (5 ans)", accent)
        hist = m.track_company(self.ticker)
        if hist and len(hist) >= 2:
            widgets.draw_candles(surf, pygame.Rect(cinner.x, cinner.y + 22,
                                                   cinner.w, cinner.h - 60), hist,
                                 n_candles=32, sma_windows=(10, 30))
            widgets.draw_text(surf, "MA10", (cinner.x, cinner.y), fonts.tiny(), config.COL_AMBER)
            widgets.draw_text(surf, "MA30", (cinner.x + 52, cinner.y), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"haut {max(hist):,.2f}  bas {min(hist):,.2f}",
                              (cinner.right, cinner.y), fonts.tiny(), config.COL_TEXT_DIM, align="right")
        else:
            widgets.draw_text_wrapped(
                surf, "Historique en cours de constitution. Avancez le temps (ADV) "
                "depuis le terminal pour voir le cours évoluer.",
                (cinner.x, cinner.y), fonts.small(), config.COL_TEXT_DIM, cinner.w)

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.SCREEN_HEIGHT - 56),
                              [("ESC", "retour")])
        self.back_btn.draw(surf)
        self.fa_btn.draw(surf)
        self.graph_btn.draw(surf)
        self.buy_btn.draw(surf)
        self.sell_btn.draw(surf)
