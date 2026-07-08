"""
app_company.py — Application « Fiche société » du bureau (NATIVE).

Migration de `scenes/scene_company.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — l'écran de détail le plus consulté du jeu
(ouvert depuis Recherche, Portefeuille, Marché, notifications…). Contrairement
aux autres apps natives « popup » (Mission/Évaluation), la fiche société
N'A PAS de règle « en cours conservé » : chaque ouverture reconfigure la
fenêtre EXISTANTE sur le nouveau ticker (`configure(ticker=...)`, appelé à
CHAQUE `_open_scene_window("company", ticker=...)`, pas seulement à la
création) — cliquer « Analyse » sur une autre société doit remplacer le
contenu affiché, jamais ouvrir une fenêtre en double ni laisser l'ancienne
fiche périmée. Pas de bouton retour (fenêtre autonome, fermeture via la
barre de titre) ; les onglets « FA »/« GP » ouvrent les écrans détaillés
(encore hébergés) EN FENÊTRE via `desktop._open_scene_window`.
"""
import pygame

from apps.base import DesktopApp
from core import charts as charts
from core import config, intraday, liquidity
from core import financials as F
from core import market_hours as mh_mod
from core import news as N
from scenes.scene_graph_common import PERIODS, stock_series, x_label_positions
from ui import fonts, widgets
from ui.glossary_hint import GlossaryHint

N_YEARS = 5
_EMPH = {"Marge brute", "EBITDA", "Résultat d'exploitation (EBIT)", "Résultat avant impôt",
         "Résultat net", "Total actifs courants", "TOTAL ACTIF",
         "Total passifs courants", "Total passif (hors CP)", "Capitaux propres",
         "TOTAL PASSIF + CP"}

_TABS = [
    ("overview", "VUE D'ENSEMBLE"),
    ("financials", "ÉTATS FINANCIERS"),
    ("chart", "GRAPHIQUE AVANCÉ"),
    ("news", "ACTUALITÉS"),
    ("valuation", "VALORISATION RELATIVE"),
]
_CHART_KINDS = [("line", "LIGNE"), ("candles", "CHANDELLES"), ("vol", "VOLATILITÉ"), ("beta", "BÊTA")]
_KIND_COL = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_CYAN}
_KIND_TAG = {"good": "▲", "bad": "▼", "info": "◆"}
ROW_H = 22


def _fmt(v, suffix="", dec=2, na="n.m."):
    if v is None:
        return na
    return f"{v:.{dec}f}{suffix}"


def _fm(v):
    if abs(v) < 0.5:
        return "—"
    return f"({abs(v):,.0f})".replace(",", " ") if v < 0 else f"{v:,.0f}".replace(",", " ")


class CompanyApp(DesktopApp):
    title = "Fiche société"
    icon_kind = "research"
    default_size = (1080, 680)
    min_size = (680, 460)

    def on_open(self):
        self.configure()

    def reenter(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, ticker=None, search="", **_kwargs):
        # **_kwargs absorbe silencieusement un éventuel "return_to"/
        # "return_kwargs" hérité des anciens appelants de la scène hébergée
        # (plus de bouton retour sur une fenêtre native — fermeture via sa
        # barre de titre) : ne jamais lever pour un kwarg inconnu.
        self.ticker = (ticker or "").upper()
        self.tab = "overview"
        self.chart_kind = "line"
        self.chart_period = 18
        self._chart_period_rects = {}
        self.news_scroll = 0
        self._news_max_scroll = 0
        self._news_list_rect = None
        self.scroll_inc = 0
        self.scroll_bal = 0
        self._max_scroll_inc = 0
        self._max_scroll_bal = 0
        self._inc_rect = None
        self._bal_rect = None
        self._tooltip = None
        self._tab_rects = {}
        self._chart_kind_rects = {}
        self._chart_flash = widgets.TickFlash()
        self._gloss = GlossaryHint()
        m = self.app.market
        if m is not None:
            m.track_company(self.ticker)
        self.metrics = m.metrics(self.ticker) if m else None
        self.sector_med = (m.sector_medians(self.metrics["sector"])
                           if m and self.metrics else None)
        self.block = F.statements(m, self.ticker, self._fiscal_year(), n_years=N_YEARS) \
            if m and self.metrics else []
        self.name = self.metrics["name"] if self.metrics else ""
        self.cur = config.CONTINENTS.get(self.metrics["region"], {}).get("currency", "$") \
            if self.metrics else "$"
        self.accent = config.CONTINENTS.get(self.metrics["region"], {}).get("color", config.COL_AMBER) \
            if self.metrics else config.COL_AMBER

        self.search = search
        if self.ticker and not self.metrics and not self.search:
            self.search = self.ticker
        self._picker_cursor = 0
        self._picker_rects = []
        self._search_clear_rect = None
        self._t = 0.0
        self._buy_rect = None
        self._sell_rect = None
        self._fa_rect = None
        self._graph_rect = None

    def _fiscal_year(self):
        p = self.app.gs.player
        return F.fiscal_year(p, config.BASE_FISCAL_YEAR)

    def _picker_items(self):
        m = self.app.market
        if not m:
            return []
        q = self.search.strip()
        if q:
            return [mt for tk, _nm in m.suggest(q, limit=12)
                   if (mt := m.metrics(tk))]
        return m.top_companies(n=12, by="mktcap")

    def _select_company(self, ticker):
        self.configure(ticker=ticker)

    # ------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if not self.metrics:
            return self._handle_picker_event(event, rect)
        if self._gloss.handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._buy_rect and self._buy_rect.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop.open_trading(self.ticker)
                return True
            if self._sell_rect and self._sell_rect.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop.open_trading(self.ticker)
                return True
            if self.tab == "financials" and self._fa_rect and self._fa_rect.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop._open_scene_window("financials", ticker=self.ticker)
                return True
            if self.tab == "chart" and self._graph_rect and self._graph_rect.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop._open_scene_window("graph", kind="line", tickers=[self.ticker])
                return True
            for tab_id, r in self._tab_rects.items():
                if r.collidepoint(event.pos):
                    self.tab = tab_id
                    return True
            for kind, r in self._chart_kind_rects.items():
                if r.collidepoint(event.pos):
                    self.chart_kind = kind
                    return True
            for period, r in self._chart_period_rects.items():
                if r.collidepoint(event.pos):
                    self.chart_period = period
                    return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -36 if event.button == 4 else 36
            if self.tab == "financials":
                if self._inc_rect and self._inc_rect.collidepoint(event.pos):
                    self.scroll_inc = max(0, min(self._max_scroll_inc, self.scroll_inc + delta))
                    return True
                if self._bal_rect and self._bal_rect.collidepoint(event.pos):
                    self.scroll_bal = max(0, min(self._max_scroll_bal, self.scroll_bal + delta))
                    return True
            elif self.tab == "news" and self._news_list_rect and \
                    self._news_list_rect.collidepoint(event.pos):
                self.news_scroll = max(0, min(self._news_max_scroll, self.news_scroll + delta))
                return True
        return False

    def _handle_picker_event(self, event, rect):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    self._picker_cursor = 0
                return True
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self._picker_cursor = 0
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                items = self._picker_items()
                if items:
                    d = -1 if event.key == pygame.K_UP else 1
                    self._picker_cursor = max(0, min(len(items) - 1, self._picker_cursor + d))
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                items = self._picker_items()
                if items:
                    self._select_company(items[min(self._picker_cursor, len(items) - 1)]["ticker"])
                return True
            from core import clipboard
            if clipboard.is_paste_shortcut(event):
                self.search += clipboard.paste().replace("\n", " ").strip()
                self._picker_cursor = 0
                return True
            if event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self._picker_cursor = 0
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                self._picker_cursor = 0
                return True
            for r, tk in self._picker_rects:
                if r.collidepoint(event.pos):
                    self._select_company(tk)
                    return True
        return False

    def update(self, dt):
        self._t += dt

    # ------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        self._gloss.begin_frame()
        mt = self.metrics
        if not mt:
            self._draw_picker(surf, rect)
            return

        self._tooltip = None
        cur, accent = self.cur, self.accent
        pad = 16

        widgets.draw_text(surf, mt["ticker"], (rect.x + pad, rect.y + 8), fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(mt["name"], fonts.small(), rect.w - 2 * pad - 220),
                          (rect.x + pad, rect.y + 34), fonts.small(), config.COL_WHITE)
        widgets.draw_badge(surf, mt["sector"], (rect.x + pad, rect.y + 52), accent)
        widgets.draw_badge(surf, mt["region"], (rect.x + pad + 118, rect.y + 52), accent)
        chg = mt["change_pct"]
        chg_col = config.COL_UP if chg >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{mt['price']:,.2f} {cur}", (rect.right - pad, rect.y + 6),
                          fonts.head(bold=True), config.COL_WHITE, align="right")
        widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}% (1 an)",
                          (rect.right - pad, rect.y + 34), fonts.small(bold=True), chg_col, align="right")

        tab_y = rect.y + 78
        self._draw_tabs(surf, rect, tab_y)

        footer_h = 44
        content = pygame.Rect(rect.x + pad, tab_y + 34, rect.w - 2 * pad,
                              rect.bottom - footer_h - (tab_y + 34))
        if self.tab == "overview":
            self._draw_overview(surf, content, mt, cur, accent)
        elif self.tab == "financials":
            self._draw_financials(surf, content)
        elif self.tab == "chart":
            self._draw_chart_tab(surf, content)
        elif self.tab == "news":
            self._draw_news_tab(surf, content)
        elif self.tab == "valuation":
            self._draw_valuation_tab(surf, content, mt)

        self._draw_footer(surf, rect)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)
        from core.i18n import get_lang
        self._gloss.draw_popup(surf, get_lang())

    def _draw_footer(self, surf, rect):
        by = rect.bottom - 38
        self._buy_rect = pygame.Rect(rect.right - 220, by, 100, 30)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._buy_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._buy_rect, 2, border_radius=4)
        widgets.draw_text(surf, "ACHAT", self._buy_rect.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
        self._sell_rect = pygame.Rect(rect.right - 110, by, 100, 30)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._sell_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_DOWN, self._sell_rect, 2, border_radius=4)
        widgets.draw_text(surf, "VENTE", self._sell_rect.center, fonts.small(bold=True),
                          config.COL_DOWN, align="center")
        if self.tab == "financials":
            self._fa_rect = pygame.Rect(rect.x + 16, by, 180, 30)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._fa_rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN, self._fa_rect, 1, border_radius=4)
            widgets.draw_text(surf, "PLEIN ÉCRAN (FA)", self._fa_rect.center, fonts.tiny(bold=True),
                              config.COL_CYAN, align="center")
        elif self.tab == "chart":
            self._graph_rect = pygame.Rect(rect.x + 16, by, 180, 30)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._graph_rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER, self._graph_rect, 1, border_radius=4)
            widgets.draw_text(surf, "PLEIN ÉCRAN (GP)", self._graph_rect.center, fonts.tiny(bold=True),
                              config.COL_AMBER, align="center")

    # ------------------------------------------------------ mode recherche
    def _draw_picker(self, surf, rect):
        pad = 16
        widgets.draw_text(surf, "FICHE SOCIÉTÉ", (rect.x + pad, rect.y + 10), fonts.head(bold=True), config.COL_AMBER)
        if self.ticker and self.search == self.ticker:
            msg = f"Société introuvable : {self.ticker}. Recherchez-en une ci-dessous."
        else:
            msg = "Recherchez une société par ticker ou nom pour ouvrir sa fiche."
        widgets.draw_text(surf, msg, (rect.x + pad, rect.y + 40), fonts.small(), config.COL_TEXT_DIM)

        search_rect = pygame.Rect(rect.x + pad, rect.y + 66, min(360, rect.w - 2 * pad), 26)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + "Ticker ou nom…")
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 5), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 24, search_rect.y,
                                                   24, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        items = self._picker_items()
        list_top = search_rect.bottom + 16
        panel = pygame.Rect(rect.x + pad, list_top, rect.w - 2 * pad, rect.bottom - 12 - list_top)
        inner = widgets.draw_panel(
            surf, panel, "Résultats" if self.search else "Plus grandes capitalisations",
            config.COL_AMBER)
        self._picker_rects = []
        if not items:
            widgets.draw_text(surf, "Aucune société ne correspond.", (inner.x, inner.y),
                              fonts.small(), config.COL_TEXT_DIM)
        row_h = 26
        mp = pygame.mouse.get_pos()
        self._picker_cursor = min(self._picker_cursor, max(0, len(items) - 1))
        wide = inner.w >= 560
        for i, c in enumerate(items):
            r = pygame.Rect(inner.x, inner.y + i * row_h, inner.w, row_h - 4)
            if r.bottom > inner.bottom:
                break
            self._picker_rects.append((r, c["ticker"]))
            hover = r.collidepoint(mp) or i == self._picker_cursor
            if hover:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, c["ticker"], (r.x + 8, r.y + 4),
                              fonts.small(bold=True), config.COL_AMBER)
            name_w = 260 if wide else max(60, r.w - 220)
            widgets.draw_text(surf, widgets.fit_text(c["name"], fonts.small(), name_w),
                              (r.x + 90, r.y + 4), fonts.small(), config.COL_WHITE)
            if wide:
                widgets.draw_text(surf, c["sector"], (r.x + 360, r.y + 4),
                                  fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, c["region"], (r.x + 500, r.y + 4),
                                  fonts.tiny(), config.COL_TEXT_DIM)
            pcur = config.CONTINENTS.get(c["region"], {}).get("currency", "$")
            widgets.draw_text(surf, f"{c['price']:,.2f} {pcur}", (r.right - 8, r.y + 4),
                              fonts.small(), config.COL_TEXT, align="right")

    def _draw_tabs(self, surf, rect, y):
        self._tab_rects = {}
        x, h = rect.x + 16, 28
        w = (rect.w - 32 - (len(_TABS) - 1) * 4) // len(_TABS)
        for tab_id, label in _TABS:
            r = pygame.Rect(x, y, w, h)
            self._tab_rects[tab_id] = r
            sel = (tab_id == self.tab)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, r)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, r, 1)
            font = fonts.tiny(bold=sel)
            widgets.draw_text(surf, widgets.fit_text(label, font, w - 8), r.center,
                              font, config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            x += w + 4

    # --------------------------------------------------------- onglet 1
    def _draw_overview(self, surf, rect, mt, cur, accent):
        y = rect.y
        r = self.app.gs.player.research.get(self.ticker)
        if r:
            rcol = (config.COL_UP if r["rating"] == "ACHAT" else
                    config.COL_DOWN if r["rating"] == "VENTE" else config.COL_WARN)
            widgets.draw_text(surf, f"RECO : {r['rating']}  ·  valeur intrinsèque "
                                    f"{r['fair']:.2f} {cur}  ·  potentiel {r['upside']:+.0f}%",
                              (rect.x, y), fonts.small(bold=True), rcol)
        else:
            widgets.draw_text(surf, "RESEARCH " + self.ticker + " pour une reco analyste",
                              (rect.x, y), fonts.small(), config.COL_TEXT_DIM)
        y += 22

        le = mt.get("last_earnings")
        if le:
            ecol = config.COL_UP if le["beat"] else config.COL_DOWN
            verb = "BEAT" if le["beat"] else "MISS"
            g_label = le.get("guidance_label")
            g_txt = f"  ·  guidance {g_label}" if g_label else ""
            widgets.draw_text(surf, f"RÉSULTATS : {verb}  surprise {le['surprise']*100:+.0f}%  "
                                    f"·  croissance CA {le['growth']*100:+.1f}%{g_txt}",
                              (rect.x, y), fonts.small(bold=True), ecol)
            y += 20
        if mt.get("earnings_anticipation"):
            widgets.draw_text(surf, f"» Publication dans {mt['steps_to_earnings']} pas",
                              (rect.x, y), fonts.small(), config.COL_WARN)
            y += 20
        pead = mt.get("pead_drift_remaining") or 0.0
        if abs(pead) > 1e-4:
            pcol = config.COL_UP if pead > 0 else config.COL_DOWN
            widgets.draw_text(surf, f"↗ Drift post-résultats résiduel : {pead*100:+.2f}%",
                              (rect.x, y), fonts.small(), pcol)
            y += 20

        mkt = self.app.market
        if mkt is not None:
            events = mkt.company_events_log.get(self.ticker, [])
            if events:
                recent = events[-3:]
                y += 4
                for ev in reversed(recent):
                    icon = ev.get("icon", "•")
                    title = ev.get("title", "")
                    desc = ev.get("desc", "")
                    ago = mkt.step_count - ev["step"]
                    ago_str = f"il y a {ago} pas" if ago > 0 else "ce pas"
                    ecol = _KIND_COL.get(ev.get("kind", "info"), config.COL_CYAN)
                    line = f"{icon}  {title} — {ago_str}"
                    widgets.draw_text(surf, line, (rect.x, y), fonts.tiny(bold=True), ecol)
                    mp = pygame.mouse.get_pos()
                    tw = fonts.tiny().size(line)[0]
                    if pygame.Rect(rect.x, y, tw, 16).collidepoint(mp):
                        self._tooltip = (mp[0] + 12, mp[1] - 28, desc)
                    y += 18
                y += 2

        stacked = rect.w < 900
        ph_top = y + 8
        ph = rect.bottom - ph_top
        fund_w = rect.w if stacked else 560
        fund_h = ph if not stacked else max(160, int(ph * 0.6))
        panel = pygame.Rect(rect.x, ph_top, fund_w, fund_h)
        inner = widgets.draw_panel(surf, panel, "Fondamentaux & valorisation", accent)
        col_valo = [
            ("Capitalisation", widgets.format_money(mt["mktcap"] * 1e6, cur), None),
            ("Chiffre d'affaires", widgets.format_money(mt["revenue"] * 1e6, cur), None),
            ("EBITDA", widgets.format_money(mt["ebitda"] * 1e6, cur), "EBITDA"),
            ("Résultat net", widgets.format_money(mt["net_income"] * 1e6, cur), None),
            ("BPA (EPS)", _fmt(mt["eps"], " " + cur, 2), None),
            ("P/E", _fmt(mt["pe"], "x", 1), "P/E"),
            ("EV", widgets.format_money(mt["ev"] * 1e6, cur), "EV"),
            ("EV / EBITDA", _fmt(mt["ev_ebitda"], "x", 1), "EV/EBITDA"),
            ("P / Sales", _fmt(mt["ps"], "x", 1), "P/S"),
        ]
        col_risk = [
            ("Marge nette", _fmt(mt["net_margin"] * 100, "%", 1), None),
            ("Marge EBITDA", _fmt(mt["ebitda_margin"] * 100, "%", 1), None),
            ("FCF yield", _fmt(mt["fcf_yield"], "%", 1), "FCF"),
            ("Dette nette", widgets.format_money(mt["net_debt"] * 1e6, cur), None),
            ("Dette / EBITDA", _fmt(mt["nd_ebitda"], "x", 1), None),
            ("Notation crédit", mt["credit_rating"], None),
            ("Rendement div.", _fmt(mt["div_yield"] * 100, "%", 2), None),
            ("Payout", _fmt(mt["payout"], "%", 0), None),
            ("Bêta", _fmt(mt["beta"], "", 2), "Beta"),
            ("Actions (M)", _fmt(mt["shares"], "", 1), None),
        ]
        ncols = 1 if inner.w < 320 else 2
        cw = inner.w // ncols
        cols = (col_valo + col_risk) if ncols == 1 else (col_valo, col_risk)
        col_iter = [cols] if ncols == 1 else cols
        for ci, colvals in enumerate(col_iter):
            x = inner.x + ci * cw
            xr = x + cw - 14
            yy = inner.y
            for label, val, term in colvals:
                if yy + 20 > inner.bottom:
                    break
                self._gloss.label(surf, (x, yy), label, fonts.tiny(), config.COL_TEXT_DIM, term=term)
                widgets.draw_text(surf, str(val), (xr, yy), fonts.small(bold=True),
                                  config.COL_WHITE, align="right")
                yy += 26

        if stacked:
            chart = pygame.Rect(rect.x, panel.bottom + 10, rect.w, rect.bottom - panel.bottom - 10)
        else:
            chart = pygame.Rect(rect.x + fund_w + 20, ph_top, rect.w - fund_w - 20, ph)
        if chart.h < 40:
            return
        cinner = widgets.draw_panel(surf, chart, "Cours — chandeliers", accent)
        m = self.app.market
        hist = (m.track_company(self.ticker, self.app.sim_clock, self.app.gs.player.day)
                if m else [])
        if hist and len(hist) >= 2:
            widgets.draw_candles(surf, pygame.Rect(cinner.x, cinner.y + 22,
                                                   cinner.w, max(20, cinner.h - 60)), hist,
                                 n_candles=32, sma_windows=(10, 30))
            widgets.draw_text(surf, "MA10", (cinner.x, cinner.y), fonts.tiny(), config.COL_AMBER)
            widgets.draw_text(surf, "MA30", (cinner.x + 52, cinner.y), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"haut {max(hist):,.2f}  bas {min(hist):,.2f}",
                              (cinner.right, cinner.y), fonts.tiny(), config.COL_TEXT_DIM, align="right")
        else:
            widgets.draw_text_wrapped(
                surf, "Historique en cours de constitution. Laissez le temps avancer "
                "(le marché évolue en direct) pour voir le cours évoluer.",
                (cinner.x, cinner.y), fonts.small(), config.COL_TEXT_DIM, cinner.w)

    # --------------------------------------------------------- onglet 2
    def _draw_financials(self, surf, rect):
        if not self.block:
            widgets.draw_text(surf, "États financiers indisponibles.", (rect.x, rect.y),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        stacked = rect.w < 700
        if stacked:
            half_h = (rect.h - 20) // 2
            inc_rect = pygame.Rect(rect.x, rect.y, rect.w, half_h)
            bal_rect = pygame.Rect(rect.x, rect.y + half_h + 20, rect.w, half_h)
        else:
            half = (rect.w - 20) // 2
            inc_rect = pygame.Rect(rect.x, rect.y, half, rect.h)
            bal_rect = pygame.Rect(rect.x + half + 20, rect.y, half, rect.h)
        inc_rows = []
        for r, line in enumerate(self.block[0]["income"]["lines"]):
            inc_rows.append((line["label"],
                             [b["income"]["lines"][r]["value"] for b in self.block]))
        self._draw_table(surf, inc_rect, "Compte de résultat", inc_rows, config.COL_CYAN, "inc")

        bal_rows = []
        n_assets = len(self.block[0]["balance"]["assets_lines"])
        for r in range(n_assets):
            bal_rows.append((self.block[0]["balance"]["assets_lines"][r]["label"],
                             [b["balance"]["assets_lines"][r]["value"] for b in self.block]))
        for r in range(len(self.block[0]["balance"]["liab_lines"])):
            bal_rows.append((self.block[0]["balance"]["liab_lines"][r]["label"],
                             [b["balance"]["liab_lines"][r]["value"] for b in self.block]))
        self._draw_table(surf, bal_rect, "Bilan", bal_rows, config.COL_AMBER, "bal")

    def _draw_table(self, surf, rect, title, rows_by_year, accent, which):
        inner = widgets.draw_panel(surf, rect, title, accent)
        years = [b["year"] for b in self.block]
        colw = min(84, max(50, (inner.w - 140) // max(1, len(years))))
        x_label = inner.x
        xs = [inner.right - colw * (len(years) - k) for k in range(len(years))]
        label_w = max(10, xs[0] - x_label - 10)
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
        scroll = widgets.draw_scrollbar(surf, rect, list_area, scroll, max_scroll, content_h)
        if which == "inc":
            self._max_scroll_inc, self.scroll_inc = max_scroll, scroll
        else:
            self._max_scroll_bal, self.scroll_bal = max_scroll, scroll

    # --------------------------------------------------------- onglet 3
    def _draw_chart_tab(self, surf, rect):
        self._chart_kind_rects = {}
        x, y, h = rect.x, rect.y, 28
        w = (rect.w - (len(_CHART_KINDS) - 1) * 4) // len(_CHART_KINDS)
        for kind, label in _CHART_KINDS:
            kr = pygame.Rect(x, y, w, h)
            self._chart_kind_rects[kind] = kr
            sel = (kind == self.chart_kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, kr)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, kr, 1)
            font = fonts.small(bold=sel)
            widgets.draw_text(surf, label, kr.center, font,
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            x += w + 4

        py, ph = y + h + 6, 24
        self._chart_period_rects = {}
        pw = (rect.w - (len(PERIODS) - 1) * 4) // len(PERIODS)
        px = rect.x
        for label, period in PERIODS:
            pr = pygame.Rect(px, py, pw, ph)
            self._chart_period_rects[period] = pr
            sel = (period == self.chart_period)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, pr)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, pr, 1)
            widgets.draw_text(surf, label, pr.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM, align="center")
            px += pw + 4

        top = py + ph + 8
        panel_rect = pygame.Rect(rect.x, top, rect.w, rect.bottom - top)
        header = widgets.draw_panel(surf, panel_rect, "Graphique", self.accent)
        m = self.app.market
        hist = stock_series(m, self.app.sim_clock, self.app.gs.player.day, self.ticker,
                            self.chart_period) if m else []
        if not hist or len(hist) < 2:
            widgets.draw_text(surf, "Historique en cours de constitution.",
                              (header.x, header.y), fonts.small(), config.COL_TEXT_DIM)
            return
        badge_y = header.y
        inner = pygame.Rect(header.x, header.y + 18, header.w, header.h - 18)
        flash_col = self._chart_flash.tick(self.ticker, hist[-1], config.COL_UP, config.COL_DOWN,
                                            config.COL_WHITE)
        widgets.draw_text(surf, f"{hist[-1]:,.2f} {self.cur}", (panel_rect.right - 12, badge_y),
                          fonts.small(bold=True), flash_col, align="right")
        i = m.ticker_idx.get(self.ticker)
        badge_x = panel_rect.x
        if i is not None:
            vol_mult = intraday.vol_mult_for_sigma(float(m.sigma[i]))
            widgets.draw_text(surf, f"Volatilité relative ×{vol_mult:.1f}",
                              (badge_x, badge_y), fonts.tiny(), config.COL_TEXT_DIM)
            badge_x += 170
            region = m.companies[i].get("region")
            if region and not mh_mod.is_region_open(region, m.step_count):
                widgets.draw_text(surf, "MARCHÉ FERMÉ — prix gelé", (badge_x, badge_y),
                                  fonts.tiny(bold=True), config.COL_WARN)
                badge_x += 180
            recent = hist[-12:]
            if len(recent) >= 6:
                rets = [abs(recent[k] / recent[k - 1] - 1) for k in range(1, len(recent))]
                avg_ret = sum(rets) / len(rets)
                if avg_ret > 0.0009 * vol_mult * 1.6:
                    widgets.draw_text(surf, "! forte variation", (badge_x, badge_y),
                                      fonts.tiny(bold=True), config.COL_DOWN)
        if self.chart_kind == "candles":
            widgets.draw_candles(surf, inner, hist, n_candles=32, sma_windows=(10, 30))
            self._x_labels(surf, inner, len(hist))
            lo_c, hi_c = min(hist), max(hist)
            self._draw_event_markers(surf, inner, hist, lo_c, hi_c - lo_c or 1.0)
        elif self.chart_kind == "line":
            trend_col = config.COL_UP if hist[-1] >= hist[0] else config.COL_DOWN
            tier = liquidity.equity_tier(m, self.ticker)
            half_spread = liquidity.params(tier)[0]
            widgets.draw_series(surf, inner, hist, trend_col, baseline=False,
                                mouse_pos=pygame.mouse.get_pos(),
                                y_fmt=lambda v: f"{v:,.2f} {self.cur}", show_pct=True,
                                show_current_line=True,
                                line_width=2, area_fill=False)
            self._draw_orderbook(surf, inner, hist[-1], tier, half_spread)
            self._x_labels(surf, inner, len(hist))
            lo_line, hi_line = min(hist), max(hist)
            self._draw_event_markers(surf, inner, hist, lo_line, hi_line - lo_line or 1.0)
        elif self.chart_kind == "vol":
            vol = [v for v in charts.rolling_vol(hist, 20) if v is not None]
            if len(vol) < 2:
                widgets.draw_text(surf, "Historique insuffisant.", (inner.x, inner.y),
                                  fonts.small(), config.COL_TEXT_DIM)
            else:
                widgets.draw_series(surf, inner, vol, config.COL_WARN,
                                    mouse_pos=pygame.mouse.get_pos(),
                                    y_fmt=lambda v: f"{v:.1f}%",
                                    line_width=2, area_alpha=25)
                widgets.draw_text(surf, f"Vol. annualisée (20 pas) = {vol[-1]:.1f}%",
                                  (inner.x, inner.y), fonts.tiny(bold=True), config.COL_WARN)
                self._x_labels(surf, inner, len(vol))
        elif self.chart_kind == "beta":
            self._draw_beta(surf, inner, m, hist)

    def _x_labels(self, surf, rect, n):
        labels = x_label_positions(self.chart_period, n, self.app.gs.player.day)
        if labels:
            widgets.draw_chart_x_labels(surf, rect, labels)

    def _draw_event_markers(self, surf, rect, hist, lo, span):
        mkt = self.app.market
        if mkt is None:
            return
        events = mkt.company_events_log.get(self.ticker, [])
        if not events:
            return
        pps = intraday.points_per_segment_for_n_steps(self.chart_period)
        if pps <= 0:
            return
        current_step = mkt.step_count
        n = len(hist)
        if n < 2:
            return
        for ev in events:
            steps_back = current_step - ev["step"]
            if steps_back < 0 or steps_back > (self.chart_period or 9999):
                continue
            idx = n - 1 - steps_back * pps
            if idx < 0 or idx >= n:
                continue
            price = hist[int(idx)]
            if lo is None or span == 0:
                continue
            y = rect.y + rect.h - int((price - lo) / span * rect.h)
            x = rect.x + int(idx / (n - 1) * rect.w)
            if not rect.collidepoint(x, y):
                continue
            icon = ev.get("icon", "•")
            ecol = _KIND_COL.get(ev.get("kind", "info"), config.COL_CYAN)
            r = 6
            pygame.draw.circle(surf, (8, 10, 14), (x, y), r + 1)
            pygame.draw.circle(surf, ecol, (x, y), r, 1)
            widgets.draw_text(surf, icon, (x, y - 7), fonts.tiny(), ecol, align="center")
            mp = pygame.mouse.get_pos()
            if (x - mp[0]) ** 2 + (y - mp[1]) ** 2 < 144:
                self._tooltip = (mp[0] + 12, mp[1] - 28,
                                 f"{ev.get('title', '')}: {ev.get('desc', '')}")

    _DEPTH_LOTS = {"Liquide": (140, 90, 55), "Peu liquide": (45, 28, 16),
                   "Illiquide": (9, 6, 4)}

    def _draw_orderbook(self, surf, rect, mid, tier, half):
        lots = self._DEPTH_LOTS.get(tier, self._DEPTH_LOTS["Peu liquide"])
        bw, rh = 116, 13
        panel = pygame.Rect(rect.right - bw - 6, rect.y + 6, bw, rh * 7 + 6)
        bg = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        bg.fill((10, 12, 18, 180))
        surf.blit(bg, panel.topleft)
        pygame.draw.rect(surf, config.COL_BORDER, panel, 1)
        widgets.draw_text(surf, f"CARNET · {tier}", (panel.x + 5, panel.y + 3),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        maxlot = max(lots)
        yy = panel.y + 3 + rh
        for k in range(2, -1, -1):
            price = mid * (1 + half * (k + 1))
            self._ob_row(surf, panel, yy, price, lots[k], maxlot, config.COL_DOWN)
            yy += rh
        widgets.draw_text(surf, f"{mid:,.2f}", (panel.centerx, yy), fonts.tiny(bold=True),
                          config.COL_WHITE, align="center")
        yy += rh
        for k in range(0, 3):
            price = mid * (1 - half * (k + 1))
            self._ob_row(surf, panel, yy, price, lots[k], maxlot, config.COL_UP)
            yy += rh

    def _ob_row(self, surf, panel, y, price, lot, maxlot, col):
        bar_w = max(1, int((panel.w - 56) * lot / maxlot))
        bar = pygame.Surface((bar_w, 9), pygame.SRCALPHA)
        bar.fill((*col[:3], 90))
        surf.blit(bar, (panel.right - 4 - bar_w, y + 1))
        widgets.draw_text(surf, f"{price:,.2f}", (panel.x + 5, y), fonts.tiny(), col)

    def _draw_beta(self, surf, rect, m, hist):
        i = m.ticker_idx.get(self.ticker)
        region = m.companies[i]["region"] if i is not None else None
        idx_name = next((n for n, r in m.index_region.items() if r == region), None)
        ridx = (m.index_history(idx_name, self.app.sim_clock, self.app.gs.player.day)
                if idx_name else [])
        ry, rx = charts.simple_returns(hist), charts.simple_returns(ridx)
        n = min(len(ry), len(rx))
        if n < 5:
            widgets.draw_text(surf, "Historique insuffisant pour le bêta.", (rect.x, rect.y),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        ry, rx = ry[-n:], rx[-n:]
        beta, alpha, r2 = charts.ols_beta(ry, rx)
        xr = max(abs(min(rx)), abs(max(rx))) or 0.01
        yr = max(abs(min(ry)), abs(max(ry))) or 0.01
        cx0, cy0 = rect.centerx, rect.centery
        sx, sy = rect.w / (2 * xr), rect.h / (2 * yr)
        pygame.draw.line(surf, config.COL_BORDER, (rect.x, cy0), (rect.right, cy0), 1)
        pygame.draw.line(surf, config.COL_BORDER, (cx0, rect.y), (cx0, rect.bottom), 1)
        for k in range(n):
            px = int(cx0 + rx[k] * sx)
            py = int(cy0 - ry[k] * sy)
            pygame.draw.circle(surf, config.COL_CYAN, (px, py), 2)
        x1, x2 = -xr, xr
        p1 = (int(cx0 + x1 * sx), int(cy0 - (alpha + beta * x1) * sy))
        p2 = (int(cx0 + x2 * sx), int(cy0 - (alpha + beta * x2) * sy))
        pygame.draw.line(surf, config.COL_AMBER, p1, p2, 2)
        widgets.draw_text(surf, f"{self.ticker} vs {idx_name or '—'}", (rect.x, rect.y),
                          fonts.small(bold=True), config.COL_TEXT)
        widgets.draw_text(surf, f"β = {beta:.2f}   α = {alpha*100:.2f}%/pas   R² = {r2:.2f}",
                          (rect.x, rect.y + 20), fonts.small(bold=True), config.COL_AMBER)

    # --------------------------------------------------------- onglet 4
    def _draw_news_tab(self, surf, rect):
        p = self.app.gs.player
        items = N.query(p)
        needles = {self.ticker.lower(), (self.name or "").lower()}
        items = [e for e in items if any(nd and nd in e["text"].lower() for nd in needles)]
        inner = widgets.draw_panel(surf, rect, f"Actualités — {self.ticker} ({len(items)})", self.accent)
        list_area = pygame.Rect(inner.x - 6, inner.y, inner.w + 12, inner.h)
        self._news_list_rect = list_area
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = list_area.top - self.news_scroll
        last_day = None
        if not items:
            widgets.draw_text(surf, "Aucune actualité mentionnant cette société pour l'instant.",
                              (inner.x, inner.y + 4), fonts.body(), config.COL_TEXT_DIM)
        for e in items:
            if e["day"] != last_day:
                last_day = e["day"]
                if (list_area.top - ROW_H) < ry < list_area.bottom:
                    q = (e["day"] - 1) // config.DAYS_PER_QUARTER + 1
                    widgets.draw_text(surf, f"— Jour {e['day']}  (T{q})",
                                      (inner.x, ry + 2), fonts.tiny(bold=True), config.COL_AMBER)
                ry += ROW_H
            if (list_area.top - ROW_H) < ry < list_area.bottom:
                col = _KIND_COL.get(e["kind"], config.COL_TEXT)
                tag = _KIND_TAG.get(e["kind"], "•")
                cat = N.category_label(e["cat"])
                widgets.draw_text(surf, tag, (inner.x + 8, ry), fonts.small(bold=True), col)
                widgets.draw_text(surf, widgets.fit_text(cat, fonts.tiny(), 90),
                                  (inner.x + 26, ry + 1), fonts.tiny(), config.COL_PRESTIGE)
                widgets.draw_text(surf, e["region"] or "Monde", (inner.x + 122, ry + 1),
                                  fonts.tiny(), config.COL_TEXT_DIM)
                text_w = max(20, inner.w - 200)
                widgets.draw_text(surf, widgets.fit_text(e["text"], fonts.small(), text_w),
                                  (inner.x + 202, ry), fonts.small(), config.COL_TEXT)
            ry += ROW_H
        surf.set_clip(prev_clip)
        content_h = (ry + self.news_scroll) - list_area.top
        self._news_max_scroll = max(0, content_h - list_area.h)
        self.news_scroll = max(0, min(self._news_max_scroll, self.news_scroll))
        self.news_scroll = widgets.draw_scrollbar(surf, rect, list_area, self.news_scroll,
                                                  self._news_max_scroll, content_h)

    # --------------------------------------------------------- onglet 5
    def _draw_valuation_tab(self, surf, rect, mt):
        stacked = rect.w < 700
        if stacked:
            half_h = (rect.h - 20) // 2
            left = pygame.Rect(rect.x, rect.y, rect.w, half_h)
            right = pygame.Rect(rect.x, rect.y + half_h + 20, rect.w, half_h)
        else:
            half = (rect.w - 20) // 2
            left = pygame.Rect(rect.x, rect.y, half, rect.h)
            right = pygame.Rect(rect.x + half + 20, rect.y, rect.w - half - 20, rect.h)
        inner = widgets.draw_panel(surf, left, "Multiples vs médiane secteur", self.accent)
        med = self.sector_med
        widgets.draw_text(surf, f"Secteur {mt['sector']} ({med['n'] if med else 0} pairs comparables)",
                          (inner.x, inner.y), fonts.small(bold=True), config.COL_TEXT_DIM)
        y = inner.y + 30

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

        for label, key, term in [("P/E", "pe", "P/E"), ("EV/EBITDA", "ev_ebitda", "EV/EBITDA"),
                                 ("P/S", "ps", "P/S")]:
            if y + 60 > inner.bottom:
                break
            v, r = mt.get(key), (med.get(key) if med else None)
            txt, col = verdict(v, r)
            self._gloss.label(surf, (inner.x, y), label, fonts.small(bold=True), config.COL_WHITE, term=term)
            widgets.draw_text(surf, f"{fmt(v)}  /  méd. secteur {fmt(r)}", (inner.x, y + 18),
                              fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, txt, (inner.right, y + 6), fonts.head(bold=True),
                              col, align="right")
            if v and r:
                bw = inner.w
                bar = pygame.Rect(inner.x, y + 42, bw, 8)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar)
                frac = max(0.0, min(1.0, v / (r * 2))) if r else 0.0
                pygame.draw.rect(surf, col, (bar.x, bar.y, int(bw * frac), bar.h))
                mid_x = bar.x + bw // 2
                pygame.draw.line(surf, config.COL_TEXT_DIM, (mid_x, bar.y - 2),
                                 (mid_x, bar.bottom + 2), 1)
            y += 64

        if y + 20 <= inner.bottom:
            widgets.draw_text_wrapped(surf, "La barre représente le multiple de la société ; le repère "
                                    "vertical marque la médiane du secteur (2× = bord droit).",
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM, inner.w)

        rinner = widgets.draw_panel(surf, right, "Profil rentabilité / risque", self.accent)
        rows = [
            ("Marge nette", _fmt(mt["net_margin"] * 100, "%", 1), None),
            ("Marge EBITDA", _fmt(mt["ebitda_margin"] * 100, "%", 1), None),
            ("FCF yield", _fmt(mt["fcf_yield"], "%", 1), "FCF"),
            ("Dette / EBITDA", _fmt(mt["nd_ebitda"], "x", 1), None),
            ("Notation crédit", mt["credit_rating"], None),
            ("Rendement dividende", _fmt(mt["div_yield"] * 100, "%", 2), None),
            ("Payout", _fmt(mt["payout"], "%", 0), None),
            ("Bêta", _fmt(mt["beta"], "", 2), "Beta"),
        ]
        yy = rinner.y
        for label, val, term in rows:
            if yy + 20 > rinner.bottom:
                break
            self._gloss.label(surf, (rinner.x, yy), label, fonts.small(), config.COL_TEXT_DIM, term=term)
            widgets.draw_text(surf, str(val), (rinner.right, yy), fonts.small(bold=True),
                              config.COL_WHITE, align="right")
            yy += 26
