"""
app_research.py — Application « Recherche » du bureau (façon Bloomberg/Refinitiv).

Explore les sociétés : recherche libre (nom/ticker), liste des valeurs, et un
panneau de détail avec cours, variation, mini-graphe animé et fondamentaux
clés. C'est le terminal de recherche « épuré » demandé — sans la navigation
« PLUS » du terminal historique : uniquement l'exploration des compagnies.
Réutilise le moteur de marché (`market.suggest/top_companies/metrics/history_of`)
sans dupliquer de logique.
"""
import pygame

from apps.base import DesktopApp
from core import audio, config
from ui import fonts, style, widgets

ROW_H = 22


class ResearchApp(DesktopApp):
    title = "Recherche — Marchés"
    icon_kind = "research"
    default_size = (820, 520)
    min_size = (520, 320)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.search = ""
        self.sel = None            # ticker sélectionné
        self.scroll = 0
        self._max_scroll = 0
        self._row_rects = {}       # ticker -> Rect
        self._row_hover = {}       # ticker -> progression hover [0,1]
        self._list_rect = None
        self._search_rect = None
        self._action_rects = {}    # "trade"|"sheet"|"analyse" -> Rect (liens inter-apps)
        # sélection initiale : plus grosse capi
        top = self.market.top_companies(n=1)
        if top:
            self.sel = top[0]["ticker"]

    # --------------------------------------------------------------- données
    def _rows(self):
        m = self.market
        q = self.search.strip()
        if q:
            hits = m.suggest(q, limit=60)
            tickers = [tk for tk, _ in hits]
        else:
            tickers = [c["ticker"] for c in m.top_companies(n=40)]
        return tickers

    # --------------------------------------------------------------- animation
    def update(self, dt):
        mp = pygame.mouse.get_pos()
        for tk, r in self._row_rects.items():
            target = 1.0 if r.collidepoint(mp) else 0.0
            cur = self._row_hover.get(tk, 0.0)
            speed = 12.0 * dt if dt else 1.0
            self._row_hover[tk] = cur + (target - cur) * min(1.0, speed)

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for kind, r in self._action_rects.items():
                if r.collidepoint(event.pos):
                    self._do_action(kind)
                    return True
            for tk, r in self._row_rects.items():
                if r.collidepoint(event.pos):
                    self.sel = tk
                    return True
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self.scroll = 0
                return True
            from core import clipboard
            if clipboard.is_paste_shortcut(event):
                self.search += clipboard.paste().replace("\n", " ").strip()
                self.scroll = 0
                return True
            if event.unicode and event.unicode.isprintable():
                self.search += event.unicode
                self.scroll = 0
                return True
        return False

    def _do_action(self, kind):
        """Liens inter-apps (cf. DesktopScene) : ouvrir Trading pré-filtré,
        pousser le cours dans le Tableur, suivre la valeur, ou ouvrir la fiche."""
        if not self.sel:
            return
        if kind == "watch":
            wl = self.app.gs.player.watchlist
            if self.sel in wl:
                wl.remove(self.sel)
                audio.play("click")
            elif len(wl) < 10:
                wl.append(self.sel)
                audio.play("click")
            return
        if self.desktop is None:
            return
        if kind == "trade":
            self.desktop.open_trading(self.sel)
            audio.play("click")
        elif kind == "sheet":
            self.desktop.add_quote_to_sheet(self.sel)
            audio.play("click")
        elif kind == "analyse":
            self.desktop._open_scene_window("company", ticker=self.sel)
            audio.play("click")
        elif kind == "alert":
            self.desktop._open_scene_window("alerts", ticker=self.sel)
            audio.play("click")

    # --------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        pad = 10
        # barre de recherche
        sr = pygame.Rect(rect.x + pad, rect.y + pad, min(320, rect.w - 2 * pad), 24)
        self._search_rect = sr
        pygame.draw.rect(surf, config.COL_BG, sr, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, sr, 1, border_radius=4)
        cur = "_" if pygame.time.get_ticks() % 1000 < 500 else " "
        label = (self.search + cur) if self.search else "Rechercher une société (nom, ticker)…"
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), sr.w - 16),
                          (sr.x + 8, sr.y + 4), fonts.small(),
                          config.COL_TEXT if self.search else config.COL_TEXT_DIM)

        list_w = max(220, int(rect.w * 0.42))
        list_x = rect.x + pad
        list_top = sr.bottom + 8
        list_area = pygame.Rect(list_x, list_top, list_w, rect.bottom - list_top - pad)
        self._list_rect = list_area
        style.draw_card(surf, list_area, bg=config.COL_BG, border=config.COL_BORDER,
                        radius=style.RADIUS_MD)

        rows = self._rows()
        self._row_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y + 4 - self.scroll
        for tk in rows:
            if list_area.top - ROW_H < y < list_area.bottom:
                self._draw_row(surf, tk, list_area, y)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = len(rows) * ROW_H + 8
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)

        # panneau détail
        det = pygame.Rect(list_area.right + 8, list_top,
                          rect.right - list_area.right - 8 - pad, list_area.h)
        self._draw_detail(surf, det)

    def _draw_row(self, surf, tk, area, y):
        m = self.market
        i = m.ticker_idx.get(tk)
        if i is None:
            return
        c = m.companies[i]
        price = m.price_of(tk)
        r = pygame.Rect(area.x + 2, y, area.w - 4, ROW_H - 2)
        self._row_rects[tk] = r
        hover_t = self._row_hover.get(tk, 0.0)
        style.draw_hover_row(surf, r, hover=hover_t > 0.01, selected=(tk == self.sel),
                             animation_t=hover_t, radius=style.RADIUS_SM)
        widgets.draw_text(surf, tk, (r.x + 6, r.y + 3), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(c["name"], fonts.tiny(), max(30, r.w - 138)),
                          (r.x + 70, r.y + 4), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{price:,.2f}", (r.right - 6, r.y + 3), fonts.small(),
                          config.COL_WHITE, align="right")

    def _draw_detail(self, surf, rect):
        style.draw_card(surf, rect, bg=config.COL_BG, border=config.COL_BORDER,
                       radius=style.RADIUS_MD)
        self._action_rects = {}
        if not self.sel:
            widgets.draw_text(surf, "Sélectionnez une société.", (rect.x + 12, rect.y + 12),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        m = self.market
        mt = m.metrics(self.sel)
        if not mt:
            return
        x, y = rect.x + 14, rect.y + 12
        widgets.draw_text(surf, mt["ticker"], (x, y), fonts.head(bold=True), config.COL_AMBER)
        # réserve la largeur de « +x.x% (1 an) » (droite, même ligne) au nom
        widgets.draw_text(surf, widgets.fit_text(mt["name"], fonts.small(), max(60, rect.w - 170)),
                          (x, y + 30), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"{mt['sector']} · {mt['region']}", (x, y + 50),
                          fonts.tiny(), config.COL_TEXT_DIM)
        # cours + variation YoY
        widgets.draw_text(surf, f"{mt['price']:,.2f}", (rect.right - 14, y), fonts.head(bold=True),
                          config.COL_WHITE, align="right")
        ccol = config.COL_UP if mt["change_pct"] >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{mt['change_pct']:+.1f}% (1 an)", (rect.right - 14, y + 32),
                          fonts.small(bold=True), ccol, align="right")
        # mini-graphe animé (forward-looking) sur ~3 mois
        gy = y + 74
        gh = max(60, min(150, rect.h - 250))
        graph = pygame.Rect(x, gy, rect.w - 28, gh)
        hist = m.history_of(self.sel, 18, sim_clock=self.app.sim_clock,
                            day=self.app.gs.player.day)
        if len(hist) >= 2:
            gcol = config.COL_UP if hist[-1] >= hist[0] else config.COL_DOWN
            widgets.draw_series(surf, graph, hist, gcol, baseline=False,
                                y_fmt=lambda v: f"{v:,.0f}", show_extrema=False)
        # fondamentaux clés
        fy = graph.bottom + 12
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        fields = [
            ("Capitalisation", widgets.format_money(mt["mktcap"], cur)),
            ("PER", f"{mt['pe']:.1f}" if mt["pe"] else "—"),
            ("VE/EBITDA", f"{mt['ev_ebitda']:.1f}" if mt["ev_ebitda"] else "—"),
            ("Rendement div.", f"{mt['div_yield']*100:.2f}%"),
            ("Marge nette", f"{mt['net_margin']*100:.1f}%"),
            ("Bêta", f"{mt['beta']:.2f}"),
            ("Notation", mt["credit_rating"]),
            ("BPA", f"{mt['eps']:.2f}"),
        ]
        # 2 colonnes si la place le permet, 1 seule en fenêtre étroite (les
        # libellés passaient sous les valeurs à la taille minimale) ; libellé
        # borné à l'espace restant à gauche de la valeur dans tous les cas.
        ncols = 2 if (rect.w - 28) // 2 >= 190 else 1
        col_w = (rect.w - 28) // ncols
        actions_top = rect.bottom - 34   # barre d'actions réservée en bas
        for k, (lbl, val) in enumerate(fields):
            fx = x + (k % ncols) * col_w
            fyy = fy + (k // ncols) * 24
            if fyy + 20 > actions_top:
                break
            val_w = fonts.small(bold=True).size(val)[0]
            widgets.draw_text(surf, widgets.fit_text(lbl, fonts.tiny(), max(30, col_w - val_w - 20)),
                              (fx, fyy), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (fx + col_w - 12, fyy), fonts.small(bold=True),
                              config.COL_TEXT, align="right")
        # barre d'actions (liens inter-apps) — seulement si hébergée sur le bureau
        if self.desktop is not None:
            self._draw_actions(surf, rect)

    def _draw_actions(self, surf, rect):
        watched = self.sel in self.app.gs.player.watchlist
        actions = [("watch", "Suivi" if watched else "Suivre", config.COL_PRESTIGE, watched),
                   ("trade", "Trader", config.COL_UP, False),
                   ("sheet", "→ Tableur", config.COL_CYAN, False),
                   ("analyse", "Analyse", config.COL_AMBER, False),
                   ("alert", "Alerte", config.COL_WARN, False)]
        mp = pygame.mouse.get_pos()
        n = len(actions)
        gap = 6
        bw = (rect.w - 20 - gap * (n - 1)) // n
        bx = rect.x + 10
        by = rect.bottom - 30
        self._action_rects = {}
        for kind, label, acc, active in actions:
            r = pygame.Rect(bx, by, bw, 22)
            self._action_rects[kind] = r
            hov = r.collidepoint(mp)
            bg = acc if active else (config.COL_PANEL_HEAD if hov else config.COL_PANEL)
            pygame.draw.rect(surf, bg, r, border_radius=4)
            pygame.draw.rect(surf, acc, r, 1, border_radius=4)
            txtcol = config.COL_BG if active else acc
            widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(bold=True), bw - 6),
                              r.center, fonts.tiny(bold=True), txtcol, align="center")
            bx += bw + gap
