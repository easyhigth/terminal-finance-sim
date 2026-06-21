"""
popups.py — Fenêtres flottantes de contenu (fiche société / graphe), et le
mixin `PopupMixin` qui donne à une scène la capacité d'en ouvrir.

Remplace la navigation systématique vers une nouvelle scène pour consulter
une société ou un graphe : les fenêtres sont déplaçables, redimensionnables
et réductibles (héritées de `ui.datawindow.DataWindow`), et coexistent avec
la scène d'où elles ont été ouvertes — on garde la vue d'ensemble.

Usage dans une scène :
    class MaScene(Scene, PopupMixin):
        def on_enter(self, **kwargs):
            self.init_popups()
        def handle_event(self, event):
            if self.popups_handle_event(event):
                return
            ...
        def draw(self, surf):
            ...
            self.popups_draw(surf)   # en dernier, au-dessus du reste

    self.open_company("MVC")                  # fiche société
    self.open_chart("MVC", kind="change")      # graphe agrandi, à onglets
    self.open_custom_chart("Frontière", fn)    # rendu personnalisé (callback)
"""
import pygame

from core import bonds as bonds_mod
from core import charts as _charts
from core import commodities as commodities_mod
from core import config
from core import crypto as crypto_mod
from core import etfs as etfs_mod
from ui import fonts, widgets
from ui.datawindow import DataWindow

_KIND_TABS = [("Ligne", "line"), ("Chandel.", "candles"), ("Var %", "change"), ("Vol.", "vol")]


def _draw_kind_tabs(surf, rect, kind, accent):
    """Dessine les onglets de type de graphe ; retourne {kind: Rect}."""
    rects = {}
    n = len(_KIND_TABS)
    w = rect.w // n
    x = rect.x
    for label, k in _KIND_TABS:
        r = pygame.Rect(x, rect.y, w - 2, rect.h)
        rects[k] = r
        sel = (k == kind)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, r)
        pygame.draw.rect(surf, accent if sel else config.COL_BORDER, r, 1)
        widgets.draw_text(surf, label, r.center, fonts.tiny(bold=sel),
                          accent if sel else config.COL_TEXT_DIM, align="center")
        x += w
    return rects


def _draw_kind_plot(surf, rect, market, ticker, kind):
    """Dessine le graphe sélectionné pour `ticker`. Retourne un libellé de
    légende (ou None s'il n'y a rien à afficher)."""
    s = market.history_of(ticker, 365) if market else []
    return _draw_series_plot(surf, rect, s, kind)


def _draw_series_plot(surf, rect, s, kind):
    """Dessine le graphe sélectionné pour une série de valeurs déjà extraite
    (utilisé pour les actifs sans ticker boursier : obligations, commodities).
    Retourne un libellé de légende (ou None s'il n'y a rien à afficher)."""
    if len(s) < 2:
        widgets.draw_text(surf, "Historique insuffisant (avancez le temps).",
                          (rect.x, rect.y), fonts.tiny(), config.COL_TEXT_DIM)
        return None
    if kind == "candles":
        widgets.draw_candles(surf, rect, s, n_candles=min(48, len(s)))
        return None
    if kind == "change":
        pct = _charts.normalize(s)
        col = config.COL_UP if pct[-1] >= 0 else config.COL_DOWN
        widgets.draw_series(surf, rect, pct, col)
        return f"variation cumulée {pct[-1]:+.1f}%"
    if kind == "vol":
        vol = [v for v in _charts.rolling_vol(s, 20) if v is not None]
        if len(vol) < 2:
            widgets.draw_text(surf, "Historique insuffisant.", (rect.x, rect.y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return None
        widgets.draw_series(surf, rect, vol, config.COL_WARN, baseline=False)
        return f"vol. annualisée (20 pas) {vol[-1]:.1f}%"
    # ligne (défaut)
    col = config.COL_UP if s[-1] >= s[0] else config.COL_DOWN
    widgets.draw_series(surf, rect, s, col)
    chg = (s[-1] / s[0] - 1) * 100 if s[0] else 0.0
    return f"{s[-1]:,.2f}  ({'+' if chg>=0 else ''}{chg:.1f}%)"


class CompanyPopup(DataWindow):
    """Fiche société compacte : prix, fondamentaux clés, mini-graphe à onglets
    et bouton d'agrandissement vers un ChartPopup."""

    def __init__(self, ticker, market, pos=(160, 120), accent=None):
        self.ticker = ticker.upper()
        self.market = market
        self.kind = "line"
        self.expand_requested = False
        self.open_ticker = None
        self.nav_request = None
        self._kind_rects = {}
        self._expand_rect = None
        self._name_rect = None
        self._sector_rect = None
        self._region_rect = None
        self._type_rect = None
        mt = market.metrics(self.ticker) if market else None
        if accent is None:
            accent = config.CONTINENTS.get(mt["region"], {}).get("color", config.COL_AMBER) \
                if mt else config.COL_AMBER
        title = f"{self.ticker} — {mt['name']}" if mt else self.ticker
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=(380, 320), resizable=True, min_size=(320, 240))

    def _handle_body(self, pos):
        for k, rr in self._kind_rects.items():
            if rr.collidepoint(pos):
                self.kind = k
                return True
        if self._expand_rect and self._expand_rect.collidepoint(pos):
            self.expand_requested = True
            return True
        if self._name_rect and self._name_rect.collidepoint(pos):
            self.nav_request = {"to": "graph", "tickers": [self.ticker], "kind": "line"}
            return True
        mt = self.market.metrics(self.ticker) if self.market else None
        if mt:
            if self._sector_rect and self._sector_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "Action", "sub_filter": mt["sector"]}
                return True
            if self._region_rect and self._region_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "region_filter": mt["region"]}
                return True
            if self._type_rect and self._type_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "Action"}
                return True
        return False

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        mt = self.market.metrics(self.ticker) if self.market else None
        if not mt:
            widgets.draw_text(surf, f"Société introuvable : {self.ticker}",
                              (content.x, content.y), fonts.small(), config.COL_DOWN)
            return
        cur = config.CONTINENTS.get(mt["region"], {}).get("currency", "$")
        y = content.y
        self._name_rect = pygame.Rect(content.x, y, 90, 20)
        widgets.draw_text(surf, mt["ticker"], (content.x, y), fonts.body(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{mt['price']:,.2f} {cur}", (content.right, y),
                          fonts.body(bold=True), config.COL_WHITE, align="right")
        y += 22
        chg = mt["change_pct"]
        chg_col = config.COL_UP if chg >= 0 else config.COL_DOWN
        widgets.draw_text(surf, widgets.fit_text(mt["name"], fonts.small(), content.w - 90),
                          (content.x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}%", (content.right, y),
                          fonts.small(bold=True), chg_col, align="right")
        y += 22
        self._sector_rect = widgets.draw_badge(surf, mt["sector"], (content.x, y), self.accent)
        self._region_rect = widgets.draw_badge(surf, mt["region"], (content.x + 100, y), self.accent)
        self._type_rect = widgets.draw_badge(surf, "Action", (content.x + 200, y), config.COL_TEXT_DIM)
        y += 28
        # fondamentaux compacts (2 colonnes x 3 lignes)
        col_a = [("P/E", f"{mt['pe']:.1f}x" if mt["pe"] else "n.m."),
                 ("Bêta", f"{mt['beta']:.2f}"),
                 ("Div.", f"{mt['div_yield']*100:.1f}%")]
        col_b = [("Capi", widgets.format_money(mt["mktcap"] * 1e6, cur)),
                 ("Marge nette", f"{mt['net_margin']*100:.1f}%"),
                 ("EV/EBITDA", f"{mt['ev_ebitda']:.1f}x" if mt["ev_ebitda"] else "n.m.")]
        cw = content.w // 2
        for ci, col in enumerate((col_a, col_b)):
            fx = content.x + ci * cw
            fy = y
            for label, val in col:
                widgets.draw_text(surf, label, (fx, fy), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (fx + cw - 16, fy), fonts.tiny(bold=True),
                                  config.COL_WHITE, align="right")
                fy += 15
        y += 15 * 3 + 10
        # onglets + mini-graphe (occupe l'espace restant : s'adapte au resize)
        tabs_rect = pygame.Rect(content.x, y, content.w, 20)
        self._kind_rects = _draw_kind_tabs(surf, tabs_rect, self.kind, self.accent)
        y += 24
        legend_h = 16
        plot_rect = pygame.Rect(content.x, y, content.w, max(20, content.bottom - y - legend_h - 22))
        legend = _draw_kind_plot(surf, plot_rect, self.market, self.ticker, self.kind)
        if legend:
            widgets.draw_text(surf, legend, (content.x, plot_rect.bottom + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        self._expand_rect = pygame.Rect(content.right - 90, content.bottom - 18, 90, 18)
        hov = self._expand_rect.collidepoint(pygame.mouse.get_pos())
        widgets.draw_text(surf, "AGRANDIR ⤢", (self._expand_rect.centerx, self._expand_rect.y + 2),
                          fonts.tiny(bold=True), self.accent if hov else config.COL_TEXT_DIM,
                          align="center")


class ChartPopup(DataWindow):
    """Graphe agrandi et déplaçable, à onglets de type (ligne/chandeliers/
    var%/vol) pour un ticker donné, ou rendu personnalisé via `render_fn`
    (utilisé pour agrandir un visuel existant — frontière, corrélations…)."""

    def __init__(self, title, market=None, ticker=None, kind="line",
                 pos=(200, 130), accent=config.COL_CYAN, render_fn=None,
                 size=(480, 360)):
        self.market = market
        self.ticker = ticker.upper() if ticker else None
        self.kind = kind
        self.render_fn = render_fn
        self._kind_rects = {}
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=size, resizable=True, min_size=(360, 260))

    def _handle_body(self, pos):
        if self.render_fn is None:
            for k, rr in self._kind_rects.items():
                if rr.collidepoint(pos):
                    self.kind = k
                    return True
        return False

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        if self.render_fn is not None:
            self.render_fn(surf, content)
            return
        if not self.ticker:
            widgets.draw_text(surf, "Aucun actif sélectionné.", (content.x, content.y),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        tabs_rect = pygame.Rect(content.x, content.y, content.w, 22)
        self._kind_rects = _draw_kind_tabs(surf, tabs_rect, self.kind, self.accent)
        plot_rect = pygame.Rect(content.x, content.y + 28, content.w, content.h - 28 - 18)
        legend = _draw_kind_plot(surf, plot_rect, self.market, self.ticker, self.kind)
        if legend:
            widgets.draw_text(surf, f"{self.ticker}  {legend}", (content.x, plot_rect.bottom + 4),
                              fonts.tiny(bold=True), config.COL_TEXT)


class CommodityPopup(DataWindow):
    """Fiche commodity compacte : spot, structure de courbe, roll yield et
    mini-graphe de spot à onglets (équivalent de CompanyPopup pour les futures)."""

    def __init__(self, cid, market, pos=(160, 120), accent=None):
        self.cid = cid.upper()
        self.market = market
        self.kind = "line"
        self.expand_requested = False
        self.open_ticker = None
        self.nav_request = None
        self._kind_rects = {}
        self._name_rect = None
        self._sector_rect = None
        self._type_rect = None
        q = commodities_mod.quote(market, self.cid) if market else None
        accent = accent or config.COL_WARN
        title = f"{self.cid} — {q['name']}" if q else self.cid
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=(360, 300), resizable=True, min_size=(300, 220))

    def _handle_body(self, pos):
        for k, rr in self._kind_rects.items():
            if rr.collidepoint(pos):
                self.kind = k
                return True
        if self._name_rect and self._name_rect.collidepoint(pos):
            self.nav_request = {"to": "graph", "tickers": [self.cid], "kind": "line"}
            return True
        q = commodities_mod.quote(self.market, self.cid) if self.market else None
        if q:
            if self._sector_rect and self._sector_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "Commodity", "sub_filter": q["category"]}
                return True
            if self._type_rect and self._type_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "Commodity"}
                return True
        return False

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        q = commodities_mod.quote(self.market, self.cid) if self.market else None
        if not q:
            widgets.draw_text(surf, f"Commodity introuvable : {self.cid}",
                              (content.x, content.y), fonts.small(), config.COL_DOWN)
            return
        y = content.y
        self._name_rect = pygame.Rect(content.x, y, 90, 20)
        widgets.draw_text(surf, self.cid, (content.x, y), fonts.body(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{q['spot']:,.2f}", (content.right, y),
                          fonts.body(bold=True), config.COL_WHITE, align="right")
        y += 22
        widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(), content.w - 90),
                          (content.x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, q["category"], (content.right, y),
                          fonts.tiny(), config.COL_TEXT_DIM, align="right")
        y += 26
        widgets.draw_badge(surf, q["structure"], (content.x, y), self.accent)
        self._sector_rect = widgets.draw_badge(surf, q["category"], (content.x + 100, y), self.accent)
        self._type_rect = widgets.draw_badge(surf, "Commodity", (content.x + 230, y), config.COL_TEXT_DIM)
        y += 28
        col_a = [("Future 1M", f"{q['front']:,.2f}"), ("Roll yield", f"{q['roll_yield']*100:+.1f}%")]
        col_b = [("Vol. annualisée", f"{q['vol']*100:.0f}%"), ("Pente courbe", f"{q['slope']*100:+.1f}%/an")]
        cw = content.w // 2
        for ci, col in enumerate((col_a, col_b)):
            fx = content.x + ci * cw
            fy = y
            for label, val in col:
                widgets.draw_text(surf, label, (fx, fy), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (fx + cw - 16, fy), fonts.tiny(bold=True),
                                  config.COL_WHITE, align="right")
                fy += 15
        y += 15 * 2 + 14
        tabs_rect = pygame.Rect(content.x, y, content.w, 20)
        self._kind_rects = _draw_kind_tabs(surf, tabs_rect, self.kind, self.accent)
        y += 24
        legend_h = 16
        plot_rect = pygame.Rect(content.x, y, content.w, max(20, content.bottom - y - legend_h - 4))
        series = commodities_mod.history(self.market, self.cid, 365) if self.market else []
        legend = _draw_series_plot(surf, plot_rect, series, self.kind)
        if legend:
            widgets.draw_text(surf, legend, (content.x, plot_rect.bottom + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)


class CryptoPopup(DataWindow):
    """Fiche crypto-actif compacte : spot, volatilité, statut (stable/CBDC/risque
    de contagion) et mini-graphe de prix à onglets (équivalent de CompanyPopup
    pour les crypto-actifs)."""

    def __init__(self, cid, market, pos=(160, 120), accent=None):
        self.cid = cid.upper()
        self.market = market
        self.kind = "line"
        self.expand_requested = False
        self.open_ticker = None
        self.nav_request = None
        self._kind_rects = {}
        self._name_rect = None
        self._type_rect = None
        q = crypto_mod.quote(market, self.cid) if market else None
        accent = accent or (config.COL_CYAN if (q and (q["stable"] or q["cbdc"])) else config.COL_DOWN)
        title = f"{self.cid} — {q['name']}" if q else self.cid
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=(360, 300), resizable=True, min_size=(300, 220))

    def _handle_body(self, pos):
        for k, rr in self._kind_rects.items():
            if rr.collidepoint(pos):
                self.kind = k
                return True
        if self._name_rect and self._name_rect.collidepoint(pos):
            self.nav_request = {"to": "graph", "tickers": [self.cid], "kind": "line"}
            return True
        if self._type_rect and self._type_rect.collidepoint(pos):
            self.nav_request = {"to": "explorer", "type_filter": "Crypto"}
            return True
        return False

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        q = crypto_mod.quote(self.market, self.cid) if self.market else None
        if not q:
            widgets.draw_text(surf, f"Crypto-actif introuvable : {self.cid}",
                              (content.x, content.y), fonts.small(), config.COL_DOWN)
            return
        y = content.y
        self._name_rect = pygame.Rect(content.x, y, 90, 20)
        widgets.draw_text(surf, self.cid, (content.x, y), fonts.body(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{q['spot']:,.4f}" if q["spot"] < 10 else f"{q['spot']:,.2f}",
                          (content.right, y), fonts.body(bold=True), config.COL_WHITE, align="right")
        y += 22
        widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(), content.w - 90),
                          (content.x, y), fonts.small(), config.COL_TEXT)
        y += 26
        status = "CBDC" if q["cbdc"] else ("Stablecoin" if q["stable"] else "Volatil")
        widgets.draw_badge(surf, status, (content.x, y), self.accent)
        self._type_rect = widgets.draw_badge(surf, "Crypto", (content.x + 110, y), config.COL_TEXT_DIM)
        risk = crypto_mod.contagion_risk(self.market, self.cid) if self.market else 0.0
        if risk > 0.01:
            widgets.draw_badge(surf, f"Contagion {risk*100:.0f}%", (content.x + 210, y), config.COL_DOWN)
        y += 28
        col_a = [("Vol. annualisée", f"{q['vol']*100:.0f}%")]
        col_b = [("Rendement", f"{q['yield']*100:.1f}%")] if q["cbdc"] else [("Type", status)]
        cw = content.w // 2
        for ci, col in enumerate((col_a, col_b)):
            fx = content.x + ci * cw
            fy = y
            for label, val in col:
                widgets.draw_text(surf, label, (fx, fy), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (fx + cw - 16, fy), fonts.tiny(bold=True),
                                  config.COL_WHITE, align="right")
                fy += 15
        y += 15 + 14
        tabs_rect = pygame.Rect(content.x, y, content.w, 20)
        self._kind_rects = _draw_kind_tabs(surf, tabs_rect, self.kind, self.accent)
        y += 24
        legend_h = 16
        plot_rect = pygame.Rect(content.x, y, content.w, max(20, content.bottom - y - legend_h - 4))
        series = crypto_mod.history(self.market, self.cid, 365) if self.market else []
        legend = _draw_series_plot(surf, plot_rect, series, self.kind)
        if legend:
            widgets.draw_text(surf, legend, (content.x, plot_rect.bottom + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)


class BondPopup(DataWindow):
    """Fiche obligation compacte : YTM, prix, duration et mini-graphe de prix
    (reconstruit depuis l'historique du taux directeur, cf. core.bonds.price_history)."""

    def __init__(self, bond_id, market, pos=(160, 120), accent=None):
        self.bond_id = bond_id
        self.market = market
        self.kind = "line"
        self.expand_requested = False
        self.open_ticker = None
        self.nav_request = None
        self._kind_rects = {}
        self._name_rect = None
        self._sector_rect = None
        self._region_rect = None
        self._type_rect = None
        q = bonds_mod.quote(market, bond_id) if market else None
        accent = accent or config.COL_CYAN
        title = q["name"] if q else bond_id
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=(360, 300), resizable=True, min_size=(300, 220))

    def _handle_body(self, pos):
        for k, rr in self._kind_rects.items():
            if rr.collidepoint(pos):
                self.kind = k
                return True
        if self._name_rect and self._name_rect.collidepoint(pos):
            self.nav_request = {"to": "graph", "tickers": [self.bond_id], "kind": "line"}
            return True
        q = bonds_mod.quote(self.market, self.bond_id) if self.market else None
        if q:
            if self._sector_rect and self._sector_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "Obligation", "sub_filter": q["kind"]}
                return True
            if self._region_rect and self._region_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "region_filter": q["region"]}
                return True
            if self._type_rect and self._type_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "Obligation"}
                return True
        return False

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        q = bonds_mod.quote(self.market, self.bond_id) if self.market else None
        if not q:
            widgets.draw_text(surf, f"Obligation introuvable : {self.bond_id}",
                              (content.x, content.y), fonts.small(), config.COL_DOWN)
            return
        y = content.y
        self._name_rect = pygame.Rect(content.x, y, content.w - 90, 20)
        widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.body(bold=True), content.w - 90),
                          (content.x, y), fonts.body(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{q['price']:.1f}", (content.right, y),
                          fonts.body(bold=True), config.COL_WHITE, align="right")
        y += 22
        widgets.draw_text(surf, widgets.fit_text(q["issuer"], fonts.small(), content.w - 90),
                          (content.x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, q["rating"], (content.right, y),
                          fonts.small(bold=True), self.accent, align="right")
        y += 26
        self._sector_rect = widgets.draw_badge(surf, q["kind"], (content.x, y), self.accent)
        self._region_rect = widgets.draw_badge(surf, q["region"], (content.x + 100, y), self.accent)
        self._type_rect = widgets.draw_badge(surf, "Obligation", (content.x + 200, y), config.COL_TEXT_DIM)
        y += 28
        col_a = [("YTM", f"{q['ytm']*100:.2f}%"), ("Coupon", f"{q['coupon']*100:.1f}%")]
        col_b = [("Duration mod.", f"{q['mod_duration']:.2f}"), ("Maturité", f"{q['years']} ans")]
        cw = content.w // 2
        for ci, col in enumerate((col_a, col_b)):
            fx = content.x + ci * cw
            fy = y
            for label, val in col:
                widgets.draw_text(surf, label, (fx, fy), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (fx + cw - 16, fy), fonts.tiny(bold=True),
                                  config.COL_WHITE, align="right")
                fy += 15
        y += 15 * 2 + 14
        tabs_rect = pygame.Rect(content.x, y, content.w, 20)
        self._kind_rects = _draw_kind_tabs(surf, tabs_rect, self.kind, self.accent)
        y += 24
        legend_h = 16
        plot_rect = pygame.Rect(content.x, y, content.w, max(20, content.bottom - y - legend_h - 4))
        series = bonds_mod.price_history(self.market, self.bond_id, 365) if self.market else []
        legend = _draw_series_plot(surf, plot_rect, series, self.kind)
        if legend:
            widgets.draw_text(surf, legend, (content.x, plot_rect.bottom + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)


_RISK_LABEL = {1: "Très faible", 2: "Faible", 3: "Modéré", 4: "Élevé", 5: "Très élevé"}


class ETFPopup(DataWindow):
    """Fiche ETF compacte : NAV, catégorie, exposition, frais, rendement et
    mini-graphe de NAV à onglets (équivalent de CompanyPopup pour les fonds)."""

    def __init__(self, eid, market, pos=(160, 120), accent=None):
        self.eid = eid.upper()
        self.market = market
        self.kind = "line"
        self.expand_requested = False
        self.open_ticker = None
        self.nav_request = None
        self._kind_rects = {}
        self._name_rect = None
        self._sector_rect = None
        self._type_rect = None
        q = etfs_mod.quote(market, self.eid) if market else None
        accent = accent or (config.COL_DOWN if (q and q["leveraged"]) else config.COL_PRESTIGE)
        title = f"{self.eid} — {q['name']}" if q else self.eid
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=(380, 320), resizable=True, min_size=(320, 240))

    def _handle_body(self, pos):
        for k, rr in self._kind_rects.items():
            if rr.collidepoint(pos):
                self.kind = k
                return True
        if self._name_rect and self._name_rect.collidepoint(pos):
            self.nav_request = {"to": "graph", "tickers": [self.eid], "kind": "line"}
            return True
        q = etfs_mod.quote(self.market, self.eid) if self.market else None
        if q:
            if self._sector_rect and self._sector_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "ETF", "sub_filter": q["category_label"]}
                return True
            if self._type_rect and self._type_rect.collidepoint(pos):
                self.nav_request = {"to": "explorer", "type_filter": "ETF"}
                return True
        return False

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        q = etfs_mod.quote(self.market, self.eid) if self.market else None
        if not q:
            widgets.draw_text(surf, f"ETF introuvable : {self.eid}",
                              (content.x, content.y), fonts.small(), config.COL_DOWN)
            return
        y = content.y
        self._name_rect = pygame.Rect(content.x, y, 90, 20)
        widgets.draw_text(surf, self.eid, (content.x, y), fonts.body(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{q['price']:,.2f}", (content.right, y),
                          fonts.body(bold=True), config.COL_WHITE, align="right")
        y += 22
        chg = q["change_pct"]
        chg_col = config.COL_UP if chg >= 0 else config.COL_DOWN
        widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(), content.w - 90),
                          (content.x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}%", (content.right, y),
                          fonts.small(bold=True), chg_col, align="right")
        y += 22
        self._sector_rect = widgets.draw_badge(surf, q["category_label"], (content.x, y), self.accent)
        self._type_rect = widgets.draw_badge(surf, "ETF", (content.x + 130, y), config.COL_TEXT_DIM)
        if q["leveraged"]:
            widgets.draw_badge(surf, "RISQUE ÉLEVÉ", (content.x + 180, y), config.COL_DOWN)
        y += 26
        widgets.draw_text(surf, "Exposition : " + widgets.fit_text(q["exposure"], fonts.tiny(), content.w - 80),
                          (content.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 18
        col_a = [("Var. 1 an", f"{q['change_1y']:+.1f}%"), ("Rendement", f"{q['yield']*100:.1f}%")]
        col_b = [("Frais", f"{q['expense']*100:.2f}%"), ("Bêta monde", f"{q['beta']:+.2f}")]
        cw = content.w // 2
        for ci, col in enumerate((col_a, col_b)):
            fx = content.x + ci * cw
            fy = y
            for label, val in col:
                widgets.draw_text(surf, label, (fx, fy), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (fx + cw - 16, fy), fonts.tiny(bold=True),
                                  config.COL_WHITE, align="right")
                fy += 15
        y += 15 * 2 + 6
        widgets.draw_text(surf, f"Risque : {_RISK_LABEL.get(q['risk'], '?')}", (content.x, y),
                          fonts.tiny(), config.COL_WARN if q["risk"] >= 4 else config.COL_TEXT_DIM)
        y += 18
        tabs_rect = pygame.Rect(content.x, y, content.w, 20)
        self._kind_rects = _draw_kind_tabs(surf, tabs_rect, self.kind, self.accent)
        y += 24
        plot_rect = pygame.Rect(content.x, y, content.w, max(20, content.bottom - y - 16 - 4))
        series = etfs_mod.nav_history(self.market, self.eid, 365) if self.market else []
        legend = _draw_series_plot(surf, plot_rect, series, self.kind)
        if legend:
            widgets.draw_text(surf, legend, (content.x, plot_rect.bottom + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)


class StructuredPopup(DataWindow):
    """Fiche produit structuré compacte : famille, payoff, sous-jacent et
    performance courante (équivalent de CompanyPopup pour les structurés)."""

    def __init__(self, template_id, market, pos=(160, 120), accent=None):
        from core import structured as structured_mod
        self.template_id = template_id
        self.market = market
        self.nav_request = None
        self._type_rect = None
        t = structured_mod.template_quote(template_id, market) if template_id in structured_mod._BY_ID else None
        accent = accent or config.COL_AMBER
        title = t["name"] if t else template_id
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=(360, 260), resizable=True, min_size=(300, 200))

    def _handle_body(self, pos):
        if self._type_rect and self._type_rect.collidepoint(pos):
            self.nav_request = {"to": "shop", "type_filter": "Structuré"}
            return True
        return False

    def draw(self, surf):
        from core import structured as structured_mod
        content = self._draw_chrome(surf)
        if content is None:
            return
        t = structured_mod.template_quote(self.template_id, self.market) \
            if self.template_id in structured_mod._BY_ID else None
        if not t:
            widgets.draw_text(surf, f"Produit introuvable : {self.template_id}",
                              (content.x, content.y), fonts.small(), config.COL_DOWN)
            return
        y = content.y
        widgets.draw_text(surf, widgets.fit_text(t["name"], fonts.body(bold=True), content.w),
                          (content.x, y), fonts.body(bold=True), config.COL_AMBER)
        y += 24
        widgets.draw_badge(surf, t["family"], (content.x, y), self.accent)
        self._type_rect = widgets.draw_badge(surf, "Structuré", (content.x + 110, y), config.COL_TEXT_DIM)
        y += 28
        widgets.draw_text(surf, f"Maturité : {t['years']} ans", (content.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 24
        widgets.draw_text_wrapped(surf, t["desc"], (content.x, y), fonts.small(),
                                  config.COL_TEXT, content.w, line_gap=3)


class CreditPopup(DataWindow):
    """Fiche tranche de titrisation compacte : attache/détache, coupon, rating
    et perte attendue du pool (équivalent de CompanyPopup pour le crédit)."""

    def __init__(self, tranche_id, market, pos=(160, 120), accent=None):
        from core import securitisation as sec_mod
        self.tranche_id = tranche_id
        self.market = market
        self.nav_request = None
        self._type_rect = None
        q = sec_mod.tranche_quote(tranche_id, market) if tranche_id in sec_mod._BY_ID else None
        accent = accent or config.COL_CYAN
        title = q["name"] if q else tranche_id
        super().__init__(title, [], [], pos=pos, accent=accent,
                         size=(340, 240), resizable=True, min_size=(280, 180))

    def _handle_body(self, pos):
        if self._type_rect and self._type_rect.collidepoint(pos):
            self.nav_request = {"to": "shop", "type_filter": "Crédit"}
            return True
        return False

    def draw(self, surf):
        from core import securitisation as sec_mod
        content = self._draw_chrome(surf)
        if content is None:
            return
        q = sec_mod.tranche_quote(self.tranche_id, self.market) if self.tranche_id in sec_mod._BY_ID else None
        if not q:
            widgets.draw_text(surf, f"Tranche introuvable : {self.tranche_id}",
                              (content.x, content.y), fonts.small(), config.COL_DOWN)
            return
        y = content.y
        widgets.draw_text(surf, q["name"], (content.x, y), fonts.body(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, q["rating"], (content.right, y),
                          fonts.body(bold=True), self.accent, align="right")
        y += 24
        self._type_rect = widgets.draw_badge(surf, "Crédit", (content.x, y), config.COL_TEXT_DIM)
        y += 28
        col_a = [("Attache", f"{q['attach']*100:.0f}%"), ("Détache", f"{q['detach']*100:.0f}%")]
        col_b = [("Coupon", f"{q['coupon']*100:.1f}%"), ("Perte att.", f"{q['exp_loss']*100:.1f}%")]
        cw = content.w // 2
        for ci, col in enumerate((col_a, col_b)):
            fx = content.x + ci * cw
            fy = y
            for label, val in col:
                widgets.draw_text(surf, label, (fx, fy), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (fx + cw - 16, fy), fonts.tiny(bold=True),
                                  config.COL_WHITE, align="right")
                fy += 15


class QuickAccessWindow(DataWindow):
    """« Accès rapide » : gère les actions favorites (watchlist, max 10) —
    clic sur le ticker → fiche, ▲/▼ réordonnent, ✕ retire. Lit/modifie
    directement `player.watchlist` (pas de copie), donc reste à jour même si
    la liste change ailleurs pendant que la fenêtre est ouverte."""

    ROW_H = 26
    CAP = 10

    def __init__(self, player, market, open_company, pos=(160, 110), accent=config.COL_AMBER):
        self.player = player
        self.market = market
        self.open_company = open_company
        self._zones = []
        size = (380, 56 + self.CAP * self.ROW_H + 30)
        super().__init__("ACCÈS RAPIDE — favoris", [], [], pos=pos, accent=accent,
                         size=size, resizable=False, min_size=(320, 140))

    def _handle_body(self, pos):
        wl = self.player.watchlist
        for rect, kind, tk in self._zones:
            if not rect.collidepoint(pos):
                continue
            if kind == "remove" and tk in wl:
                wl.remove(tk)
            elif kind in ("up", "down") and tk in wl:
                i = wl.index(tk)
                j = i - 1 if kind == "up" else i + 1
                if 0 <= j < len(wl):
                    wl[i], wl[j] = wl[j], wl[i]
            elif kind == "open":
                self.open_company(tk)
            return True
        return False

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        self._zones = []
        wl = self.player.watchlist
        widgets.draw_text(surf, f"{len(wl)}/{self.CAP} favoris — clic ticker → fiche · "
                                "▲▼ réordonner · ✕ retirer",
                          (content.x, content.y), fonts.tiny(), config.COL_TEXT_DIM)
        y = content.y + 20
        if not wl:
            widgets.draw_text(surf, "Aucun favori. WATCHLIST ADD <ticker>, ou clic droit "
                                    "dans EXPLORER.", (content.x, y), fonts.small(), config.COL_TEXT_DIM)
            return
        mp = pygame.mouse.get_pos()
        for i, tk in enumerate(wl):
            row = pygame.Rect(content.x - 2, y - 2, content.w + 4, self.ROW_H - 2)
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            mt = self.market.metrics(tk) if self.market else None
            name_rect = pygame.Rect(content.x, y, content.w - 96, self.ROW_H - 4)
            self._zones.append((name_rect, "open", tk))
            label = f"{tk}  {mt['name'][:16]}" if mt else tk
            widgets.draw_text(surf, label, (content.x, y), fonts.small(bold=True), config.COL_AMBER)
            if mt:
                ccol = config.COL_UP if mt["change_pct"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{mt['change_pct']:+.1f}%", (content.x + content.w - 96, y),
                                  fonts.tiny(bold=True), ccol)
            bx = content.right - 64
            up_r = pygame.Rect(bx, y - 1, 20, 18)
            dn_r = pygame.Rect(bx + 22, y - 1, 20, 18)
            rm_r = pygame.Rect(bx + 44, y - 1, 20, 18)
            self._zones.append((up_r, "up", tk))
            self._zones.append((dn_r, "down", tk))
            self._zones.append((rm_r, "remove", tk))
            widgets.draw_text(surf, "▲", up_r.center, fonts.tiny(bold=True),
                              config.COL_TEXT_DIM if i == 0 else config.COL_TEXT, align="center")
            widgets.draw_text(surf, "▼", dn_r.center, fonts.tiny(bold=True),
                              config.COL_TEXT_DIM if i == len(wl) - 1 else config.COL_TEXT, align="center")
            widgets.draw_text(surf, "✕", rm_r.center, fonts.tiny(bold=True), config.COL_DOWN, align="center")
            y += self.ROW_H


class PopupMixin:
    """À inclure dans une Scene pour ouvrir des fenêtres flottantes (fiches
    société, graphes) qui coexistent avec la scène elle-même."""

    _MAX_POPUPS = 5

    def init_popups(self):
        self.popups = []

    def popups_handle_event(self, event):
        for w in reversed(self.popups):
            if w.handle(event):
                self._consume_popup_signals(w)
                self.popups = [x for x in self.popups if not x.closed]
                return True
        return False

    def popups_draw(self, surf):
        for w in self.popups:
            w.draw(surf)

    def popups_close_top(self):
        """Ferme la fenêtre flottante la plus récente. True si une a été fermée."""
        if self.popups:
            self.popups.pop()
            return True
        return False

    def _consume_popup_signals(self, w):
        if getattr(w, "expand_requested", False):
            w.expand_requested = False
            self.open_chart(w.ticker, kind=w.kind, accent=w.accent)
        tk = getattr(w, "open_ticker", None)
        if tk:
            w.open_ticker = None
            self.open_company(tk)
        nav = getattr(w, "nav_request", None)
        if nav:
            w.nav_request = None
            nav = dict(nav)
            target = nav.pop("to")
            nav["return_to"] = getattr(self.app.scenes, "current_name", None) or "terminal"
            self.app.scenes.go(target, **nav)

    def _popup_pos(self):
        n = len(self.popups)
        offset = 24 * (n % 6)
        return (160 + offset, 110 + offset)

    def _popup_market(self):
        return getattr(self, "market", None) or self.app.ensure_market()

    def open_company(self, ticker, accent=None):
        """Ouvre (ou met au premier plan) la fiche flottante d'une société."""
        market = self._popup_market()
        if not market or market.metrics(ticker.upper()) is None:
            return None
        w = CompanyPopup(ticker, market, pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_chart(self, ticker, kind="line", accent=config.COL_CYAN, title=None):
        """Ouvre un graphe agrandi (à onglets) pour un ticker donné."""
        market = self._popup_market()
        title = title or f"GRAPHE — {ticker.upper()}"
        w = ChartPopup(title, market=market, ticker=ticker, kind=kind,
                       pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_commodity(self, cid, accent=None):
        """Ouvre (ou met au premier plan) la fiche flottante d'une commodity."""
        market = self._popup_market()
        if not market or commodities_mod.quote(market, cid.upper()) is None:
            return None
        w = CommodityPopup(cid, market, pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_crypto(self, cid, accent=None):
        """Ouvre (ou met au premier plan) la fiche flottante d'un crypto-actif."""
        market = self._popup_market()
        if not market or crypto_mod.quote(market, cid.upper()) is None:
            return None
        w = CryptoPopup(cid, market, pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_bond(self, bond_id, accent=None):
        """Ouvre (ou met au premier plan) la fiche flottante d'une obligation."""
        market = self._popup_market()
        if not market or bonds_mod.quote(market, bond_id) is None:
            return None
        w = BondPopup(bond_id, market, pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_etf(self, eid, accent=None):
        """Ouvre (ou met au premier plan) la fiche flottante d'un ETF."""
        market = self._popup_market()
        if not market or etfs_mod.quote(market, eid.upper()) is None:
            return None
        w = ETFPopup(eid, market, pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_structured(self, template_id, accent=None):
        """Ouvre (ou met au premier plan) la fiche flottante d'un produit structuré."""
        from core import structured as structured_mod
        if template_id not in structured_mod._BY_ID:
            return None
        market = self._popup_market()
        w = StructuredPopup(template_id, market, pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_credit(self, tranche_id, accent=None):
        """Ouvre (ou met au premier plan) la fiche flottante d'une tranche de titrisation."""
        from core import securitisation as sec_mod
        if tranche_id not in sec_mod._BY_ID:
            return None
        market = self._popup_market()
        w = CreditPopup(tranche_id, market, pos=self._popup_pos(), accent=accent)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_custom_chart(self, title, render_fn, accent=config.COL_AMBER, size=(520, 380)):
        """Agrandit un visuel existant (callback `render_fn(surf, rect)`) dans
        une fenêtre flottante déplaçable/redimensionnable."""
        w = ChartPopup(title, render_fn=render_fn, pos=self._popup_pos(),
                       accent=accent, size=size)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w

    def open_quick_access(self, player, accent=None):
        """Ouvre le gestionnaire « accès rapide » des favoris (watchlist)."""
        market = self._popup_market()
        w = QuickAccessWindow(player, market, self.open_company,
                              pos=self._popup_pos(), accent=accent or config.COL_AMBER)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)
        return w
