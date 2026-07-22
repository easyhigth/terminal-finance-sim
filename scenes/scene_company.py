"""
scene_company.py — Fiche société type terminal pro (fenêtre à onglets, façon
Refinitiv/Bloomberg). UNE scène commune, paramétrée par `ticker`, qui présente
plusieurs vues sur la même société sans changer de scène : vue d'ensemble,
états financiers (condensés), graphique avancé, actualités filtrées, et
valorisation relative au secteur. Les vues « plein écran » (FA/GP complets)
restent accessibles depuis les onglets correspondants pour le détail maximal.
Ouverte via la commande COMPANY <ticker> ou en cliquant un ticker.
"""
import pygame

from core import charts as charts
from core import config, i18n, intraday, liquidity, market_constants
from core import financials as F
from core import market_hours as mh_mod
from core import news as N
from core.scene_manager import Scene
from scenes.scene_graph_common import PERIODS, stock_series, x_label_positions
from ui import fonts, widgets
from ui.glossary_hint import GlossaryHint

N_YEARS = 5
_EMPH = {"Marge brute", "EBITDA", "Résultat d'exploitation (EBIT)", "Résultat avant impôt",
         "Résultat net", "Total actifs courants", "TOTAL ACTIF",
         "Total passifs courants", "Total passif (hors CP)", "Capitaux propres",
         "TOTAL PASSIF + CP"}

def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


_TABS = [
    ("overview", ("VUE D'ENSEMBLE", "OVERVIEW")),
    ("financials", ("ÉTATS FINANCIERS", "FINANCIALS")),
    ("chart", ("GRAPHIQUE AVANCÉ", "ADVANCED CHART")),
    ("news", ("ACTUALITÉS", "NEWS")),
    ("valuation", ("VALORISATION RELATIVE", "RELATIVE VALUATION")),
]
_CHART_KINDS = [("line", ("LIGNE", "LINE")), ("candles", ("CHANDELLES", "CANDLES")),
                ("vol", ("VOLATILITÉ", "VOLATILITY")), ("beta", ("BÊTA", "BETA"))]
_KIND_COL = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_CYAN}
_KIND_TAG = {"good": "▲", "bad": "▼", "info": "◆"}
ROW_H = 22


def _fmt(v, suffix="", dec=2, na="n.m."):
    if v is None:
        return na
    return f"{v:.{dec}f}{suffix}"


def _fm(v):
    """Montant en M, négatifs entre parenthèses (mêmes conventions que FA)."""
    if abs(v) < 0.5:
        return "—"
    return f"({abs(v):,.0f})".replace(",", " ") if v < 0 else f"{v:,.0f}".replace(",", " ")


class CompanyScene(Scene):
    def on_enter(self, **kwargs):
        self.ticker = (kwargs.get("ticker") or "").upper()
        self.return_to = kwargs.get("return_to", "terminal")
        self.return_kwargs = kwargs.get("return_kwargs") or {}
        self.tab = "overview"
        self.chart_kind = "line"
        self.chart_period = 18   # 3M par défaut (cf. STEP_PERIODS, même défaut que GraphScene)
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
        self.attribution = (m.factor_attribution({self.ticker: 1.0})
                            if m and self.metrics else None)
        self.block = F.statements(m, self.ticker, self._fiscal_year(), n_years=N_YEARS) \
            if m and self.metrics else []
        self.name = self.metrics["name"] if self.metrics else ""
        self.cur = config.CONTINENTS.get(self.metrics["region"], {}).get("currency", "$") \
            if self.metrics else "$"
        self.accent = config.CONTINENTS.get(self.metrics["region"], {}).get("color", config.COL_AMBER) \
            if self.metrics else config.COL_AMBER

        # mode recherche : actif quand on arrive sans ticker valide (depuis PLUS,
        # ou ticker introuvable) — permet de choisir une société sans changer
        # de scène ni passer par le terminal.
        self.search = kwargs.get("search", "")
        if self.ticker and not self.metrics and not self.search:
            self.search = self.ticker
        self._picker_cursor = 0
        self._picker_rects = []
        self._search_clear_rect = None
        self._t = 0.0

        self.back_btn = widgets.Button(config.back_button_rect(180),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.buy_btn = widgets.Button(
            (config.SCREEN_WIDTH - 320, config.SCREEN_HEIGHT - 70, 130, 46), _L("ACHAT", "BUY"), config.COL_UP)
        self.sell_btn = widgets.Button(
            (config.SCREEN_WIDTH - 180, config.SCREEN_HEIGHT - 70, 140, 46), _L("VENTE", "SELL"), config.COL_DOWN)
        self.fa_btn = widgets.Button((230, config.SCREEN_HEIGHT - 70, 200, 46),
                                     _L("PLEIN ÉCRAN (FA)", "FULLSCREEN (FA)"), config.COL_CYAN)
        self.graph_btn = widgets.Button((230, config.SCREEN_HEIGHT - 70, 200, 46),
                                        _L("PLEIN ÉCRAN (GP)", "FULLSCREEN (GP)"), config.COL_AMBER)

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
        self.app.scenes.go("company", ticker=ticker, return_to=self.return_to,
                           return_kwargs=self.return_kwargs)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if not self.metrics:
            self._handle_picker_event(event)
            return
        if self._gloss.handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to, **self.return_kwargs)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to, **self.return_kwargs)
            return
        if self.buy_btn.handle(event):
            self.app.pending_input = f"BUY {self.ticker} "
            self.app.scenes.go("terminal")
            return
        if self.sell_btn.handle(event):
            self.app.pending_input = f"SELL {self.ticker} ALL"
            self.app.scenes.go("terminal")
            return
        if self.tab == "financials" and self.fa_btn.handle(event):
            self.app.scenes.go("financials", ticker=self.ticker, return_to=self.return_to)
            return
        if self.tab == "chart" and self.graph_btn.handle(event):
            self.app.scenes.go("graph", kind="line", tickers=[self.ticker], return_to=self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab_id, rect in self._tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = tab_id
                    return
            for kind, rect in self._chart_kind_rects.items():
                if rect.collidepoint(event.pos):
                    self.chart_kind = kind
                    return
            for period, rect in self._chart_period_rects.items():
                if rect.collidepoint(event.pos):
                    self.chart_period = period
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -36 if event.button == 4 else 36
            if self.tab == "financials":
                if self._inc_rect and self._inc_rect.collidepoint(event.pos):
                    self.scroll_inc = max(0, min(self._max_scroll_inc, self.scroll_inc + delta))
                elif self._bal_rect and self._bal_rect.collidepoint(event.pos):
                    self.scroll_bal = max(0, min(self._max_scroll_bal, self.scroll_bal + delta))
            elif self.tab == "news" and self._news_list_rect and \
                    self._news_list_rect.collidepoint(event.pos):
                self.news_scroll = max(0, min(self._news_max_scroll, self.news_scroll + delta))

    def _handle_picker_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    self._picker_cursor = 0
                else:
                    self.app.scenes.back(self.return_to, **self.return_kwargs)
                return
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self._picker_cursor = 0
                return
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                items = self._picker_items()
                if items:
                    d = -1 if event.key == pygame.K_UP else 1
                    self._picker_cursor = max(0, min(len(items) - 1, self._picker_cursor + d))
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                items = self._picker_items()
                if items:
                    self._select_company(items[min(self._picker_cursor, len(items) - 1)]["ticker"])
                return
            if event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self._picker_cursor = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to, **self.return_kwargs)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                self._picker_cursor = 0
                return
            for rect, tk in self._picker_rects:
                if rect.collidepoint(event.pos):
                    self._select_company(tk)
                    return

    def update(self, dt):
        self._t += dt
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        if self.metrics:
            self.buy_btn.update(mp, dt)
            self.sell_btn.update(mp, dt)
            if self.tab == "financials":
                self.fa_btn.update(mp, dt)
            elif self.tab == "chart":
                self.graph_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        self._gloss.begin_frame()
        mt = self.metrics
        if not mt:
            self._draw_picker(surf)
            self.back_btn.draw(surf)
            return

        self._tooltip = None
        cur, accent = self.cur, self.accent

        # en-tête compact (commun à tous les onglets)
        widgets.draw_text(surf, mt["ticker"], (40, 18), fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(mt["name"], fonts.small(), 280),
                          (40, 52), fonts.small(), config.COL_WHITE)
        widgets.draw_badge(surf, mt["sector"], (40, 74), accent)
        widgets.draw_badge(surf, mt["region"], (158, 74), accent)
        chg = mt["change_pct"]
        chg_col = config.COL_UP if chg >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{mt['price']:,.2f} {cur}", (config.SCREEN_WIDTH - 40, 14),
                          fonts.head(bold=True), config.COL_WHITE, align="right")
        widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}% (1 an)",
                          (config.SCREEN_WIDTH - 40, 48), fonts.small(bold=True), chg_col, align="right")

        # barre d'onglets
        tab_y = 100
        self._draw_tabs(surf, tab_y)

        content = pygame.Rect(40, tab_y + 38, config.SCREEN_WIDTH - 80,
                              config.footer_y() - 8 - (tab_y + 38))
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

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.SCREEN_HEIGHT - 56),
                              [("ESC", _L("retour", "back"))])
        self.back_btn.draw(surf)
        self.buy_btn.draw(surf)
        self.sell_btn.draw(surf)
        if self.tab == "financials":
            self.fa_btn.draw(surf)
        elif self.tab == "chart":
            self.graph_btn.draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)
        from core.i18n import get_lang
        self._gloss.draw_popup(surf, get_lang())

    # ------------------------------------------------------ mode recherche
    def _draw_picker(self, surf):
        widgets.draw_text(surf, _L("FICHE SOCIÉTÉ", "COMPANY SHEET"), (40, 22), fonts.title(bold=True), config.COL_AMBER)
        if self.ticker and self.search == self.ticker:
            msg = _L(f"Société introuvable : {self.ticker}. Recherchez-en une ci-dessous.", f"Company not found: {self.ticker}. Search for one below.")
        else:
            msg = _L("Recherchez une société par ticker ou nom pour ouvrir sa fiche.", "Search a company by ticker or name to open its sheet.")
        widgets.draw_text(surf, msg, (42, 72), fonts.small(), config.COL_TEXT_DIM)

        search_rect = pygame.Rect(40, config.content_top(), 360, 26)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + _L("Ticker ou nom…", "Ticker or name…"))
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
        panel = pygame.Rect(40, list_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - list_top)
        inner = widgets.draw_panel(
            surf, panel, _L("Résultats", "Results") if self.search else _L("Plus grandes capitalisations", "Largest market caps"),
            config.COL_AMBER)
        self._picker_rects = []
        if not items:
            widgets.draw_text(surf, _L("Aucune société ne correspond.", "No company matches."), (inner.x, inner.y),
                              fonts.small(), config.COL_TEXT_DIM)
        row_h = 26
        mp = pygame.mouse.get_pos()
        self._picker_cursor = min(self._picker_cursor, max(0, len(items) - 1))
        for i, c in enumerate(items):
            rect = pygame.Rect(inner.x, inner.y + i * row_h, inner.w, row_h - 4)
            self._picker_rects.append((rect, c["ticker"]))
            hover = rect.collidepoint(mp) or i == self._picker_cursor
            if hover:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=3)
            widgets.draw_text(surf, c["ticker"], (rect.x + 8, rect.y + 4),
                              fonts.small(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, widgets.fit_text(c["name"], fonts.small(), 260),
                              (rect.x + 90, rect.y + 4), fonts.small(), config.COL_WHITE)
            widgets.draw_text(surf, c["sector"], (rect.x + 360, rect.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, c["region"], (rect.x + 500, rect.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
            cur = config.CONTINENTS.get(c["region"], {}).get("currency", "$")
            widgets.draw_text(surf, f"{c['price']:,.2f} {cur}", (rect.right - 8, rect.y + 4),
                              fonts.small(), config.COL_TEXT, align="right")
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.SCREEN_HEIGHT - 56),
                              [("↑↓", _L("naviguer", "navigate")), (_L("ENTRÉE", "ENTER"), _L("ouvrir", "open")), ("ESC", _L("retour", "back"))])

    def _draw_tabs(self, surf, y):
        self._tab_rects = {}
        x, h = 40, 30
        w = (config.SCREEN_WIDTH - 80 - (len(_TABS) - 1) * 4) // len(_TABS)
        for tab_id, _pair in _TABS:
            label = _L(*_pair)
            rect = pygame.Rect(x, y, w, h)
            self._tab_rects[tab_id] = rect
            sel = (tab_id == self.tab)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1)
            font = fonts.tiny(bold=sel)
            widgets.draw_text(surf, widgets.fit_text(label, font, w - 8), rect.center,
                              font, config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            x += w + 4

    # --------------------------------------------------------- onglet 1
    def _draw_overview(self, surf, rect, mt, cur, accent):
        y = rect.y
        r = self.app.gs.player.research.get(self.ticker)
        if r:
            rcol = (config.COL_UP if r["rating"] == "ACHAT" else
                    config.COL_DOWN if r["rating"] == "VENTE" else config.COL_WARN)
            widgets.draw_text(surf, _L(f"RECO : {r['rating']}  ·  valeur intrinsèque {r['fair']:.2f} {cur}  ·  potentiel {r['upside']:+.0f}%",
                                       f"RATING: {r['rating']}  ·  intrinsic value {r['fair']:.2f} {cur}  ·  upside {r['upside']:+.0f}%"),
                              (rect.x, y), fonts.small(bold=True), rcol)
        else:
            widgets.draw_text(surf, "RESEARCH " + self.ticker + _L(" pour une reco analyste", " for an analyst rating"),
                              (rect.x, y), fonts.small(), config.COL_TEXT_DIM)
        y += 22

        le = mt.get("last_earnings")
        if le:
            ecol = config.COL_UP if le["beat"] else config.COL_DOWN
            verb = "BEAT" if le["beat"] else "MISS"
            g_label = market_constants.guidance_label_display(le.get("guidance_label"))
            g_txt = f"  ·  guidance {g_label}" if g_label else ""
            widgets.draw_text(surf, _L(f"RÉSULTATS : {verb}  surprise {le['surprise']*100:+.0f}%  ·  croissance CA {le['growth']*100:+.1f}%{g_txt}",
                                       f"EARNINGS: {verb}  surprise {le['surprise']*100:+.0f}%  ·  revenue growth {le['growth']*100:+.1f}%{g_txt}"),
                              (rect.x, y), fonts.small(bold=True), ecol)
            y += 20
        if mt.get("earnings_anticipation"):
            widgets.draw_text(surf, _L(f"» Publication dans {mt['steps_to_earnings']} pas", f"» Earnings in {mt['steps_to_earnings']} steps"),
                              (rect.x, y), fonts.small(), config.COL_WARN)
            y += 20
        pead = mt.get("pead_drift_remaining") or 0.0
        if abs(pead) > 1e-4:
            pcol = config.COL_UP if pead > 0 else config.COL_DOWN
            widgets.draw_text(surf, _L(f"↗ Drift post-résultats résiduel : {pead*100:+.2f}%", f"↗ Residual post-earnings drift: {pead*100:+.2f}%"),
                              (rect.x, y), fonts.small(), pcol)
            y += 20

        # Événements d'entreprise récents (core/market_events.py)
        mkt = self.app.market
        if mkt is not None:
            events = mkt.company_events_log.get(self.ticker, [])
            if events:
                recent = events[-3:]  # 3 derniers événements
                y += 4
                for ev in reversed(recent):
                    icon = ev.get("icon", "•")
                    title = ev.get("title", "")
                    desc = ev.get("desc", "")
                    ago = mkt.step_count - ev["step"]
                    ago_str = _L(f"il y a {ago} pas", f"{ago} steps ago") if ago > 0 else _L("ce pas", "this step")
                    ecol = _KIND_COL.get(ev.get("kind", "info"), config.COL_CYAN)
                    line = f"{icon}  {title} — {ago_str}"
                    widgets.draw_text(surf, line, (rect.x, y), fonts.tiny(bold=True), ecol)
                    # tooltip avec description complète au survol
                    mp = pygame.mouse.get_pos()
                    tw = fonts.tiny().size(line)[0]
                    if pygame.Rect(rect.x, y, tw, 16).collidepoint(mp):
                        self._tooltip = (mp[0] + 12, mp[1] - 28, desc)
                    y += 18
                y += 2

        ph_top = y + 8
        ph = rect.bottom - ph_top
        panel = pygame.Rect(rect.x, ph_top, 560, ph)
        inner = widgets.draw_panel(surf, panel, _L("Fondamentaux & valorisation", "Fundamentals & valuation"), accent)
        # 3e élément optionnel : terme du glossaire (data/glossary_data.py) à
        # ouvrir en un clic sur le libellé — cf. ui/glossary_hint.py. None
        # quand il n'y a pas d'entrée de glossaire pertinente (le libellé
        # reste alors un simple texte, non cliquable).
        col_valo = [
            (_L("Capitalisation", "Market cap"), widgets.format_money(mt["mktcap"] * 1e6, cur), None),
            (_L("Chiffre d'affaires", "Revenue"), widgets.format_money(mt["revenue"] * 1e6, cur), None),
            ("EBITDA", widgets.format_money(mt["ebitda"] * 1e6, cur), "EBITDA"),
            (_L("Résultat net", "Net income"), widgets.format_money(mt["net_income"] * 1e6, cur), None),
            (_L("BPA (EPS)", "EPS"), _fmt(mt["eps"], " " + cur, 2), None),
            ("P/E", _fmt(mt["pe"], "x", 1), "P/E"),
            ("EV", widgets.format_money(mt["ev"] * 1e6, cur), "EV"),
            ("EV / EBITDA", _fmt(mt["ev_ebitda"], "x", 1), "EV/EBITDA"),
            ("P / Sales", _fmt(mt["ps"], "x", 1), "P/S"),
        ]
        col_risk = [
            (_L("Marge nette", "Net margin"), _fmt(mt["net_margin"] * 100, "%", 1), None),
            (_L("Marge EBITDA", "EBITDA margin"), _fmt(mt["ebitda_margin"] * 100, "%", 1), None),
            ("FCF yield", _fmt(mt["fcf_yield"], "%", 1), "FCF"),
            (_L("Dette nette", "Net debt"), widgets.format_money(mt["net_debt"] * 1e6, cur), None),
            (_L("Dette / EBITDA", "Debt / EBITDA"), _fmt(mt["nd_ebitda"], "x", 1), None),
            (_L("Notation crédit", "Credit rating"), mt["credit_rating"], None),
            (_L("Rendement div.", "Div. yield"), _fmt(mt["div_yield"] * 100, "%", 2), None),
            ("Payout", _fmt(mt["payout"], "%", 0), None),
            (_L("Bêta", "Beta"), _fmt(mt["beta"], "", 2), "Beta"),
            (_L("Actions (M)", "Shares (M)"), _fmt(mt["shares"], "", 1), None),
        ]
        cw = inner.w // 2
        for ci, col in enumerate((col_valo, col_risk)):
            x = inner.x + ci * cw
            xr = x + cw - 14
            yy = inner.y
            for label, val, term in col:
                self._gloss.label(surf, (x, yy), label, fonts.tiny(), config.COL_TEXT_DIM, term=term)
                widgets.draw_text(surf, str(val), (xr, yy), fonts.small(bold=True),
                                  config.COL_WHITE, align="right")
                yy += 26

        chart = pygame.Rect(rect.x + 580, ph_top, rect.w - 580, ph)
        cinner = widgets.draw_panel(surf, chart, _L("Cours — chandeliers", "Price — candles"), accent)
        m = self.app.market
        hist = (m.track_company(self.ticker, self.app.sim_clock, self.app.gs.player.day)
                if m else [])
        if hist and len(hist) >= 2:
            widgets.draw_candles(surf, pygame.Rect(cinner.x, cinner.y + 22,
                                                   cinner.w, cinner.h - 60), hist,
                                 n_candles=32, sma_windows=(10, 30))
            widgets.draw_text(surf, "MA10", (cinner.x, cinner.y), fonts.tiny(), config.COL_AMBER)
            widgets.draw_text(surf, "MA30", (cinner.x + 52, cinner.y), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, _L(f"haut {max(hist):,.2f}  bas {min(hist):,.2f}", f"high {max(hist):,.2f}  low {min(hist):,.2f}"),
                              (cinner.right, cinner.y), fonts.tiny(), config.COL_TEXT_DIM, align="right")
        else:
            widgets.draw_text_wrapped(
                surf, _L("Historique en cours de constitution. Laissez le temps avancer (le marché évolue en direct) pour voir le cours évoluer.",
                         "History still building. Let time advance (the market moves live) to watch the price evolve."),
                (cinner.x, cinner.y), fonts.small(), config.COL_TEXT_DIM, cinner.w)

    # --------------------------------------------------------- onglet 2
    def _draw_financials(self, surf, rect):
        if not self.block:
            widgets.draw_text(surf, _L("États financiers indisponibles.", "Financial statements unavailable."), (rect.x, rect.y),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        half = (rect.w - 20) // 2
        inc_rows = []
        for r, line in enumerate(self.block[0]["income"]["lines"]):
            inc_rows.append((line["label"],
                             [b["income"]["lines"][r]["value"] for b in self.block]))
        self._draw_table(surf, pygame.Rect(rect.x, rect.y, half, rect.h),
                         _L("Compte de résultat", "Income statement"), inc_rows, config.COL_CYAN, "inc")

        bal_rows = []
        n_assets = len(self.block[0]["balance"]["assets_lines"])
        for r in range(n_assets):
            bal_rows.append((self.block[0]["balance"]["assets_lines"][r]["label"],
                             [b["balance"]["assets_lines"][r]["value"] for b in self.block]))
        for r in range(len(self.block[0]["balance"]["liab_lines"])):
            bal_rows.append((self.block[0]["balance"]["liab_lines"][r]["label"],
                             [b["balance"]["liab_lines"][r]["value"] for b in self.block]))
        self._draw_table(surf, pygame.Rect(rect.x + half + 20, rect.y, half, rect.h),
                         _L("Bilan", "Balance sheet"), bal_rows, config.COL_AMBER, "bal")

    def _draw_table(self, surf, rect, title, rows_by_year, accent, which):
        inner = widgets.draw_panel(surf, rect, title, accent)
        years = [b["year"] for b in self.block]
        colw = 84
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
        for kind, _pair in _CHART_KINDS:
            label = _L(*_pair)
            kr = pygame.Rect(x, y, w, h)
            self._chart_kind_rects[kind] = kr
            sel = (kind == self.chart_kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, kr)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, kr, 1)
            font = fonts.small(bold=sel)
            widgets.draw_text(surf, label, kr.center, font,
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            x += w + 4

        # sélecteur de PÉRIODE (1J/1W/1M/3M/1A/3A/5A/MAX) — même liste que
        # l'atelier de graphes (scene_graph.py), pour naviguer d'un coup d'œil
        # entre l'échelle intraday et l'historique long sans changer d'écran.
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
        header = widgets.draw_panel(surf, panel_rect, _L("Graphique", "Chart"), self.accent)
        m = self.app.market
        hist = stock_series(m, self.app.sim_clock, self.app.gs.player.day, self.ticker,
                            self.chart_period) if m else []
        if not hist or len(hist) < 2:
            widgets.draw_text(surf, _L("Historique en cours de constitution.", "History still building."),
                              (header.x, header.y), fonts.small(), config.COL_TEXT_DIM)
            return
        # bande de badges (prix, volatilité, ouverture du marché) sous l'en-tête
        # « Graphique » — RÉSERVÉE à part (inner de draw_panel colle sinon au
        # titre : le texte s'y superposait).
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
            widgets.draw_text(surf, _L(f"Volatilité relative ×{vol_mult:.1f}", f"Relative volatility ×{vol_mult:.1f}"),
                              (badge_x, badge_y), fonts.tiny(), config.COL_TEXT_DIM)
            badge_x += 170
            region = m.companies[i].get("region")
            if region and not mh_mod.is_region_open(region, m.step_count):
                widgets.draw_text(surf, _L("MARCHÉ FERMÉ — prix gelé", "MARKET CLOSED — price frozen"), (badge_x, badge_y),
                                  fonts.tiny(bold=True), config.COL_WARN)
                badge_x += 180
            recent = hist[-12:]
            if len(recent) >= 6:
                rets = [abs(recent[k] / recent[k - 1] - 1) for k in range(1, len(recent))]
                avg_ret = sum(rets) / len(rets)
                if avg_ret > 0.0009 * vol_mult * 1.6:
                    widgets.draw_text(surf, _L("! forte variation", "! large move"), (badge_x, badge_y),
                                      fonts.tiny(bold=True), config.COL_DOWN)
        if self.chart_kind == "candles":
            widgets.draw_candles(surf, inner, hist, n_candles=32, sma_windows=(10, 30))
            self._x_labels(surf, inner, len(hist))
            lo_c, hi_c = min(hist), max(hist)
            self._draw_event_markers(surf, inner, hist, lo_c, hi_c - lo_c or 1.0)
        elif self.chart_kind == "line":
            # Couleur de tendance pour le trait, mais remplissage très subtil
            # (presque transparent) pour éviter l'aspect « gros bloc de couleur »
            # quand le cours a beaucoup baissé.
            trend_col = config.COL_UP if hist[-1] >= hist[0] else config.COL_DOWN
            tier = liquidity.equity_tier(m, self.ticker)
            half_spread = liquidity.params(tier)[0]
            widgets.draw_series(surf, inner, hist, trend_col, baseline=False,
                                mouse_pos=pygame.mouse.get_pos(),
                                y_fmt=lambda v: f"{v:,.2f} {self.cur}", show_pct=True,
                                show_current_line=True,
                                line_width=2, area_fill=False)
            # Carnet déplacé à droite du graphe pour ne pas masquer le début de
            # la courbe ; affiché avant les labels d'axe X.
            self._draw_orderbook(surf, inner, hist[-1], tier, half_spread)
            self._x_labels(surf, inner, len(hist))
            lo_line, hi_line = min(hist), max(hist)
            self._draw_event_markers(surf, inner, hist, lo_line, hi_line - lo_line or 1.0)
        elif self.chart_kind == "vol":
            vol = [v for v in charts.rolling_vol(hist, 20) if v is not None]
            if len(vol) < 2:
                widgets.draw_text(surf, _L("Historique insuffisant.", "Not enough history."), (inner.x, inner.y),
                                  fonts.small(), config.COL_TEXT_DIM)
            else:
                widgets.draw_series(surf, inner, vol, config.COL_WARN,
                                    mouse_pos=pygame.mouse.get_pos(),
                                    y_fmt=lambda v: f"{v:.1f}%",
                                    line_width=2, area_alpha=25)
                widgets.draw_text(surf, _L(f"Vol. annualisée (20 pas) = {vol[-1]:.1f}%", f"Annualized vol (20 steps) = {vol[-1]:.1f}%"),
                                  (inner.x, inner.y), fonts.tiny(bold=True), config.COL_WARN)
                self._x_labels(surf, inner, len(vol))
        elif self.chart_kind == "beta":
            self._draw_beta(surf, inner, m, hist)

    def _x_labels(self, surf, rect, n):
        """Libellés d'axe X à échelle humaine — même échelle adaptative que
        l'atelier de graphes (scene_graph_common.x_label_positions)."""
        labels = x_label_positions(self.chart_period, n, self.app.gs.player.day)
        if labels:
            widgets.draw_chart_x_labels(surf, rect, labels)

    def _draw_event_markers(self, surf, rect, hist, lo, span):
        """Dessine des icônes d'événements d'entreprise sur la courbe de prix.
        Les événements sont positionnés à leur pas de marché correspondant
        sur la série densifiée (intraday)."""
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
            # Clip aux bords du graphe
            if not rect.collidepoint(x, y):
                continue
            icon = ev.get("icon", "•")
            ecol = _KIND_COL.get(ev.get("kind", "info"), config.COL_CYAN)
            # Petit cercle de fond + icône
            r = 6
            pygame.draw.circle(surf, (8, 10, 14), (x, y), r + 1)
            pygame.draw.circle(surf, ecol, (x, y), r, 1)
            widgets.draw_text(surf, icon, (x, y - 7), fonts.tiny(), ecol, align="center")
            # Tooltip au survol
            mp = pygame.mouse.get_pos()
            if (x - mp[0]) ** 2 + (y - mp[1]) ** 2 < 144:  # 12px radius
                self._tooltip = (mp[0] + 12, mp[1] - 28,
                                 f"{ev.get('title', '')}: {ev.get('desc', '')}")

    # Tailles indicatives (en lots) du carnet simulé par tier de liquidité :
    # un carnet liquide est profond, un carnet illiquide est mince — cohérent
    # avec core/liquidity (la profondeur conditionne l'impact de marché).
    _DEPTH_LOTS = {"Liquide": (140, 90, 55), "Peu liquide": (45, 28, 16),
                   "Illiquide": (9, 6, 4)}

    def _draw_orderbook(self, surf, rect, mid, tier, half):
        """Mini carnet d'ordres simulé (#4) : 3 niveaux bid/ask déterministes
        autour du prix, avec une barre proportionnelle à la profondeur du tier.
        Lecture seule, purement illustrative — donne l'intuition de la
        profondeur de marché avant un gros ordre."""
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
        for k in range(2, -1, -1):     # asks décroissants (le meilleur en bas)
            price = mid * (1 + half * (k + 1))
            self._ob_row(surf, panel, yy, price, lots[k], maxlot, config.COL_DOWN)
            yy += rh
        widgets.draw_text(surf, f"{mid:,.2f}", (panel.centerx, yy), fonts.tiny(bold=True),
                          config.COL_WHITE, align="center")
        yy += rh
        for k in range(0, 3):          # bids
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
            widgets.draw_text(surf, _L("Historique insuffisant pour le bêta.", "Not enough history for beta."), (rect.x, rect.y),
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
        inner = widgets.draw_panel(surf, rect, _L(f"Actualités — {self.ticker} ({len(items)})", f"News — {self.ticker} ({len(items)})"), self.accent)
        list_area = pygame.Rect(inner.x - 6, inner.y, inner.w + 12, inner.h)
        self._news_list_rect = list_area
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = list_area.top - self.news_scroll
        last_day = None
        if not items:
            widgets.draw_text(surf, _L("Aucune actualité mentionnant cette société pour l'instant.", "No news mentioning this company yet."),
                              (inner.x, inner.y + 4), fonts.body(), config.COL_TEXT_DIM)
        for e in items:
            if e["day"] != last_day:
                last_day = e["day"]
                if (list_area.top - ROW_H) < ry < list_area.bottom:
                    q = (e["day"] - 1) // config.DAYS_PER_QUARTER + 1
                    widgets.draw_text(surf, _L(f"— Jour {e['day']}  (T{q})", f"— Day {e['day']}  (Q{q})"),
                                      (inner.x, ry + 2), fonts.tiny(bold=True), config.COL_AMBER)
                ry += ROW_H
            if (list_area.top - ROW_H) < ry < list_area.bottom:
                col = _KIND_COL.get(e["kind"], config.COL_TEXT)
                tag = _KIND_TAG.get(e["kind"], "•")
                cat = N.category_label(e["cat"])
                widgets.draw_text(surf, tag, (inner.x + 8, ry), fonts.small(bold=True), col)
                widgets.draw_text(surf, widgets.fit_text(cat, fonts.tiny(), 90),
                                  (inner.x + 26, ry + 1), fonts.tiny(), config.COL_PRESTIGE)
                widgets.draw_text(surf, e["region"] or _L("Monde", "World"), (inner.x + 122, ry + 1),
                                  fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, widgets.fit_text(e["text"], fonts.small(), inner.w - 200),
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
        half = (rect.w - 20) // 2
        left = pygame.Rect(rect.x, rect.y, half, rect.h)
        inner = widgets.draw_panel(surf, left, _L("Multiples vs médiane secteur", "Multiples vs sector median"), self.accent)
        med = self.sector_med
        widgets.draw_text(surf, _L(f"Secteur {mt['sector']} ({med['n'] if med else 0} pairs comparables)", f"Sector {mt['sector']} ({med['n'] if med else 0} comparable peers)"),
                          (inner.x, inner.y), fonts.small(bold=True), config.COL_TEXT_DIM)
        y = inner.y + 30

        def fmt(v):
            return f"{v:.1f}x" if v else "n.m."

        def verdict(val, ref):
            if not val or not ref:
                return ("—", config.COL_TEXT_DIM)
            if val < ref * 0.9:
                return (_L("décoté", "cheap"), config.COL_UP)
            if val > ref * 1.1:
                return (_L("cher", "expensive"), config.COL_DOWN)
            return (_L("en ligne", "in line"), config.COL_TEXT)

        for label, key, term in [("P/E", "pe", "P/E"), ("EV/EBITDA", "ev_ebitda", "EV/EBITDA"),
                                 ("P/S", "ps", "P/S")]:
            v, r = mt.get(key), (med.get(key) if med else None)
            txt, col = verdict(v, r)
            self._gloss.label(surf, (inner.x, y), label, fonts.small(bold=True), config.COL_WHITE, term=term)
            widgets.draw_text(surf, _L(f"{fmt(v)}  /  méd. secteur {fmt(r)}", f"{fmt(v)}  /  sector med. {fmt(r)}"), (inner.x, y + 18),
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

        widgets.draw_text(surf, _L("La barre représente le multiple de la société ; le repère vertical marque la médiane du secteur (2× = bord droit).",
                                   "The bar shows the company multiple; the vertical marker is the sector median (2× = right edge)."),
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)

        right = pygame.Rect(rect.x + half + 20, rect.y, rect.w - half - 20, rect.h)
        rinner = widgets.draw_panel(surf, right, _L("Profil rentabilité / risque", "Profitability / risk profile"), self.accent)
        rows = [
            (_L("Marge nette", "Net margin"), _fmt(mt["net_margin"] * 100, "%", 1), None),
            (_L("Marge EBITDA", "EBITDA margin"), _fmt(mt["ebitda_margin"] * 100, "%", 1), None),
            ("FCF yield", _fmt(mt["fcf_yield"], "%", 1), "FCF"),
            (_L("Dette / EBITDA", "Debt / EBITDA"), _fmt(mt["nd_ebitda"], "x", 1), None),
            (_L("Notation crédit", "Credit rating"), mt["credit_rating"], None),
            (_L("Rendement dividende", "Dividend yield"), _fmt(mt["div_yield"] * 100, "%", 2), None),
            ("Payout", _fmt(mt["payout"], "%", 0), None),
            (_L("Bêta", "Beta"), _fmt(mt["beta"], "", 2), "Beta"),
        ]
        yy = rinner.y
        for label, val, term in rows:
            self._gloss.label(surf, (rinner.x, yy), label, fonts.small(), config.COL_TEXT_DIM, term=term)
            widgets.draw_text(surf, str(val), (rinner.right, yy), fonts.small(bold=True),
                              config.COL_WHITE, align="right")
            yy += 26
