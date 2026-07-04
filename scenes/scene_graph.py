"""
scene_graph.py — Atelier de graphes analytiques (style Bloomberg « G… »).

Un seul écran, plusieurs TYPES de graphes sélectionnables, alimentés par les ~5
ans d'historique du moteur de marché (préhistoire incluse) :

  GP    ligne de prix + moyennes mobiles        (line)
  GPC   chandeliers japonais (OHLC agrégé)       (candles)
  GPO   barres OHLC                              (bars)
  GPCH  variation % depuis une référence         (change)
  COMP  performances comparées (base 0 %)        (compare)
  HS    spread / ratio entre deux actifs         (spread)
  HVOL  volatilité historique annualisée glissante (vol)
  BETA  nuage de points + régression vs indice   (beta)
  CORR  matrice de corrélation (heatmap)         (corr)
  GEG   indicateurs macro superposés             (macro)
  GC    courbe des taux (maturité × rendement)   (curve)

Ouvrable depuis la console (GP/GPC/COMP/...), ou via le bouton GRAPHE des fiches.
"""
import pygame

from core import bonds as BND
from core import commodities as CMD
from core import config, intraday
from core import crypto as CRY
from core import etfs as ETF
from core.scene_manager import Scene
from scenes.scene_graph_common import (
    _INTRADAY_KINDS,
    _KIND_BY_CODE,
    _MAX_TICKERS,
    _MULTI,
    _NO_ASSET,
    PERIODS,
    STEP_PERIODS,
    TYPES,
    _asset_exists,
    _asset_kind,
)
from scenes.scene_graph_render import GraphRenderMixin
from ui import fonts, widgets
from ui.popups import ChartPopup, PopupMixin


class GraphScene(GraphRenderMixin, Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        # type de graphe : explicite (kwargs) sinon dernier choisi (mémoire),
        # sinon "line" par défaut.
        self.kind = kwargs.get("kind") or getattr(self, "_mem_kind", None) or "line"
        self.market = self.app.ensure_market()
        self.init_popups()
        tickers = kwargs.get("tickers")
        self.error = None
        if not tickers:
            top = self.market.top_companies(n=1)
            tickers = [top[0]["ticker"]] if top else []
        else:
            # actifs demandés explicitement (ex. bouton GRAPHE d'une fiche) :
            # un ticker invalide/périmé (société radiée, faute de frappe) ne doit
            # pas planter — on filtre et on signale si rien n'est exploitable.
            requested = [t.upper() for t in tickers]
            valid = [t for t in requested if _asset_exists(self.market, t)]
            if not valid and self.kind not in _NO_ASSET:
                self.error = f"Actif introuvable : {', '.join(requested)}"
            tickers = valid
        self.tickers = [t.upper() for t in tickers][:_MAX_TICKERS]
        # Par défaut : 3 mois (18 pas) — vue « par pas » assez large pour lire une
        # vraie tendance, tout en restant animée jour par jour via la couche
        # intraday forward-looking (le dernier point glisse vers le prochain pas).
        # Sans objet pour les graphes statistiques/multi-actifs (vol/bêta/
        # corrélation/macro/courbe/spread/comparer) : retombent aussi sur 3M.
        default_period = 18
        if "period" not in kwargs and getattr(self, "_mem_period", None) is not None:
            default_period = self._mem_period   # restitue la dernière fenêtre choisie
        self.period = kwargs.get("period", default_period)
        if self.kind not in _INTRADAY_KINDS and self.period is not None and self.period < 0:
            self.period = 73
        self._cursor = widgets.ChartCursor()
        self.spread_mode = "ratio"
        self.input = ""
        self._type_rects = {}
        self._period_rects = {}
        self._candle_rects = []
        self._suggest_rects = []
        self._chip_rects = []
        self._quickadd_rects = []
        self._info_name_rect = None
        self._type_badge_rect = None
        self._region_badge_rect = None
        self._sector_badge_rect = None
        self._controls_bottom = 178
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.mode_btn = widgets.Button(
            (240, config.SCREEN_HEIGHT - 50, 200, 42), "SPREAD : RATIO", config.COL_CYAN)
        # indicateurs techniques superposables (lecture seule, purement analytique) :
        # désactivés par défaut, jamais persistés (pas de champ de sauvegarde).
        self.show_sma = False
        self.show_bollinger = False
        self.show_rsi = False
        self.sma_btn = widgets.Button((0, 0, 96, 26), "SMA20", config.COL_AMBER)
        self.boll_btn = widgets.Button((0, 0, 110, 26), "BOLLINGER", config.COL_TEXT_DIM)
        self.rsi_btn = widgets.Button((0, 0, 80, 26), "RSI", config.COL_PRESTIGE)
        # (attribut d'état, bouton, couleur active "à elle" — restaurée quand activé)
        self._indicator_btns = (
            ("show_sma", self.sma_btn, config.COL_AMBER),
            ("show_bollinger", self.boll_btn, config.COL_TEXT_DIM),
            ("show_rsi", self.rsi_btn, config.COL_PRESTIGE))

    def _open_popup_for(self, tk):
        """Ouvre la fiche d'analyse flottante (persistante) de l'actif `tk`,
        selon sa classe — même mécanisme que les autres scènes (analyse,
        portefeuille...)."""
        kind = _asset_kind(tk)
        if kind == "stock":
            self.open_company(tk)
        elif kind == "etf":
            self.open_etf(tk)
        elif kind == "bond":
            self.open_bond(tk)
        elif kind == "commodity":
            self.open_commodity(tk)
        elif kind == "crypto":
            self.open_crypto(tk)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if self._cursor.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            choices = self._period_choices()
            idx = next((i for i, (_, s) in enumerate(choices) if s == self.period), 2)
            if event.button == 4 and idx > 0:
                self.period = choices[idx - 1][1]
            elif event.button == 5 and idx < len(choices) - 1:
                self.period = choices[idx + 1][1]
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return
                self.app.scenes.back(self.return_to)
            elif event.key == pygame.K_BACKSPACE:
                self.input = self.input[:-1]
            elif event.key == pygame.K_RETURN:
                self._commit_input()
            elif event.unicode and event.unicode.isprintable() and len(self.input) < 8:
                self.input += event.unicode.upper()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # clic droit sur un nom affiché (suggestion / sélection / ajout
            # rapide / actif principal) -> fiche d'analyse flottante persistante,
            # sans perturber le clic gauche (ajout/retrait/sélection d'actif).
            for rr, tk in self._suggest_rects:
                if rr.collidepoint(event.pos):
                    self._open_popup_for(tk)
                    return
            for rr, tk in self._chip_rects:
                if rr.collidepoint(event.pos):
                    self._open_popup_for(tk)
                    return
            for rr, tk in self._quickadd_rects:
                if rr.collidepoint(event.pos):
                    self._open_popup_for(tk)
                    return
            if self._info_name_rect and self._info_name_rect.collidepoint(event.pos) and self.tickers:
                self._open_popup_for(self.tickers[0])
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rr, tk in self._suggest_rects:
                if rr.collidepoint(event.pos):
                    self._commit_input(ticker=tk)
                    return
            for rr, tk in self._chip_rects:
                if rr.collidepoint(event.pos):
                    if tk in self.tickers:
                        self.tickers.remove(tk)
                    return
            for rr, tk in self._quickadd_rects:
                if rr.collidepoint(event.pos):
                    self._commit_input(ticker=tk)
                    return
            for code, rect in self._type_rects.items():
                if rect.collidepoint(event.pos):
                    self.kind = _KIND_BY_CODE[code]
                    self.input = ""
                    if self.kind not in _INTRADAY_KINDS and self.period is not None and self.period < 0:
                        self.period = 365
            for steps, rect in self._period_rects.items():
                if rect.collidepoint(event.pos):
                    self.period = steps
            if self.kind == "candles":
                for click_rect, sub in getattr(self, "_candle_rects", []):
                    if click_rect.collidepoint(event.pos) and len(sub) >= 2:
                        self._open_candle_zoom(sub)
                        return
            if self._info_name_rect and self._info_name_rect.collidepoint(event.pos) and self.tickers:
                self.app.scenes.go("explorer", return_to=self.return_to, search=self.tickers[0])
                return
            if self._type_badge_rect and self._type_badge_rect.collidepoint(event.pos):
                info = self._info_for(self.tickers[0])
                self.app.scenes.go("explorer", return_to=self.return_to, type_filter=info["type"])
                return
            if self._region_badge_rect and self._region_badge_rect.collidepoint(event.pos):
                info = self._info_for(self.tickers[0])
                self.app.scenes.go("explorer", return_to=self.return_to, region_filter=info["region"])
                return
            if self._sector_badge_rect and self._sector_badge_rect.collidepoint(event.pos):
                info = self._info_for(self.tickers[0])
                self.app.scenes.go("explorer", return_to=self.return_to, sub_filter=info["sector"])
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if self.kind == "spread" and self.mode_btn.handle(event):
            self.spread_mode = "diff" if self.spread_mode == "ratio" else "ratio"
            self.mode_btn.label = f"SPREAD : {self.spread_mode.upper()}"
        if self.kind == "line":
            for attr, btn, _ in self._indicator_btns:
                if btn.handle(event):
                    setattr(self, attr, not getattr(self, attr))

    def _open_candle_zoom(self, sub):
        """Ouvre une fenêtre flottante affichant le chemin de prix détaillé
        sous-jacent à une bougie cliquée (drill-down) — réutilise les valeurs
        déjà bucketées par `_track_candle_rects`, sans nouvel appel marché."""
        col = config.COL_UP if sub[-1] >= sub[0] else config.COL_DOWN

        def render(surf, content, vals=sub, color=col):
            widgets.draw_series(surf, content, vals, color, show_pct=True,
                                mouse_pos=pygame.mouse.get_pos())

        tk = self.tickers[0] if self.tickers else "?"
        w = ChartPopup(f"ZOOM BOUGIE — {tk}", pos=self._popup_pos(), accent=col, render_fn=render)
        self.popups.append(w)
        if len(self.popups) > self._MAX_POPUPS:
            self.popups.pop(0)

    def _commit_input(self, ticker=None):
        # recherche intelligente : résout un nom/ticker partiel vers un ticker
        q = ticker if ticker is not None else self.input.strip()
        self.input = ""
        if not q:
            return
        if ticker is not None:
            tk = q
        else:
            tk = self.market.resolve(q)
            if not tk and ETF.exists(q.upper()):   # un ticker d'ETF est aussi graphable
                tk = q.upper()
        if not tk:
            self.app.notify(f"Aucun résultat : {q}", "bad")
            return
        if self.kind in _MULTI:
            if tk not in self.tickers:
                self.tickers.append(tk)
                self.tickers = self.tickers[-_MAX_TICKERS:]
        else:
            self.tickers = [tk]

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.mode_btn.update(mp, dt)
        if self.kind == "line":
            for _, btn, _accent in self._indicator_btns:
                btn.update(mp, dt)
        # mémorise le dernier type de graphe + fenêtre choisis, pour les
        # restituer à la prochaine ouverture (instance de scène réutilisée).
        self._mem_kind, self._mem_period = self.kind, self.period

    # -------------------------------------------------------------- data
    def _info_for(self, tk):
        """Infos clés de l'actif `tk` pour la barre au-dessus des onglets de
        graphe : type, région, secteur et valeurs clés — None si non disponible."""
        kind = _asset_kind(tk)
        if kind == "stock":
            mt = self.market.metrics(tk)
            if not mt:
                return None
            return {"type": "Action", "region": mt["region"], "sector": mt["sector"],
                    "values": [("Cours", f"{mt['price']:,.2f}"), ("Var.", f"{mt['change_pct']:+.2f}%"),
                               ("Bêta", f"{mt['beta']:.2f}")]}
        if kind == "etf":
            q = ETF.quote(self.market, tk)
            if not q:
                return None
            return {"type": "ETF", "region": None, "sector": q["category_label"],
                    "values": [("VL", f"{q['price']:,.2f}"), ("Var.", f"{q['change_pct']:+.2f}%"),
                               ("Bêta monde", f"{q['beta']:+.2f}")]}
        if kind == "bond":
            q = BND.quote(self.market, tk)
            if not q:
                return None
            return {"type": "Obligation", "region": q["region"], "sector": q["kind"],
                    "values": [("Prix", f"{q['price']:.1f}"), ("YTM", f"{q['ytm']*100:.2f}%"),
                               ("Duration", f"{q['mod_duration']:.2f}")]}
        if kind == "commodity":
            q = CMD.quote(self.market, tk)
            if not q:
                return None
            return {"type": "Commodity", "region": None, "sector": q["category"],
                    "values": [("Spot", f"{q['spot']:,.2f}"), ("Roll yield", f"{q['roll_yield']*100:+.1f}%"),
                               ("Vol.", f"{q['vol']*100:.0f}%")]}
        if kind == "crypto":
            q = CRY.quote(self.market, tk)
            if not q:
                return None
            return {"type": "Crypto", "region": None,
                    "sector": "Stablecoin" if q["stable"] else "Crypto-actif",
                    "values": [("Spot", f"{q['spot']:,.4f}" if q["spot"] < 10 else f"{q['spot']:,.2f}"),
                               ("Vol.", f"{q['vol']*100:.0f}%")]}
        return None

    def _period_choices(self):
        """Périodes proposées pour le type de graphe courant — les fenêtres
        courtes animées (1J/1W) n'ont de sens que pour les graphes à série unique
        (ligne/chandeliers/barres/variation %)."""
        if self.kind in _INTRADAY_KINDS:
            return PERIODS
        return STEP_PERIODS

    def _region_of(self, tk):
        i = self.market.ticker_idx.get(tk)
        return self.market.companies[i].get("region") if i is not None else None

    def _series(self, tk):
        kind = _asset_kind(tk)
        i = self.market.ticker_idx.get(tk)
        vol_mult = intraday.vol_mult_for_sigma(float(self.market.sigma[i])) if i is not None else 1.0
        if self.period is not None and self.period < 0:
            # fenêtre intraday animée (Round 11 Phase 3) : uniquement pour les
            # actions (seule classe avec un historique par pas exploitable
            # tel quel + une région de cotation pour le gel hors session) ;
            # les autres classes d'actifs retombent sur la vue "MAX".
            if kind == "stock":
                # historique couvrant la fenêtre demandée (+ marge : le point
                # le plus ancien de la fenêtre peut tomber dans le pas d'avant)
                window_days = -self.period / (24 * 60)
                steps_needed = max(2, int(window_days / config.DAYS_PER_STEP) + 2)
                hist = self.market.history_of(tk, steps_needed)
                # target = clôture suivante déterministe : le pont du pas
                # COURANT (révélé au fil des minutes de jeu) est le même que
                # celui de live_point — le dernier point du graphe 1J/1W et le
                # prix « en direct » affiché partout ailleurs coïncident.
                return intraday.intraday_series(
                    self.market, self.app.sim_clock, self.app.gs.player.day, tk, hist,
                    window_minutes=-self.period, n_points=60, region=self._region_of(tk),
                    vol_mult=vol_mult, target=self.market.next_price_of(tk))
            n = None
        else:
            n = self.period
        pps = intraday.points_per_segment_for_n_steps(n)
        if kind == "bond":
            hist = BND.price_history(self.market, tk, n)
            return intraday.densify_step_series(self.market, tk, hist, pps)
        if kind == "commodity":
            hist = CMD.history(self.market, tk, n)
            return intraday.densify_step_series(self.market, tk, hist, pps)
        if kind == "crypto":
            hist = CRY.history(self.market, tk, n)
            return intraday.densify_step_series(self.market, tk, hist, pps)
        if kind == "etf":
            hist = ETF.nav_history(self.market, tk, n)
            return intraday.densify_step_series(self.market, tk, hist, pps)
        # action, période « par pas » (1M/3M/1A/…) : la courbe entre deux
        # clôtures réelles est "densifiée" par du bruit épinglé (pont
        # brownien déterministe, jamais une droite nue), plus dense pour les
        # fenêtres courtes/zoomées que pour les longues (cf.
        # `points_per_segment_for_n_steps`) — puis on ajoute un point « en
        # direct » animé en bout de courbe pour qu'elle respire entre deux pas
        # (sinon le graphe ne bougeait qu'au changement de pas).
        hist = self.market.history_of(tk, n)
        region = self._region_of(tk)
        dense = intraday.densify_step_series(self.market, tk, hist, pps,
                                             region=region, vol_mult=vol_mult)
        return intraday.append_live(self.market, self.app.sim_clock,
                                    self.app.gs.player.day, tk, dense,
                                    region=region, vol_mult=vol_mult,
                                    target=self.market.next_price_of(tk))

    # -------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        if self.error:
            widgets.draw_error_panel(surf, self.error,
                                     "Utilisez SEARCH <texte> depuis le terminal.")
            self.back_btn.draw(surf)
            return
        code = next((c for c, _, k, _ in TYPES if k == self.kind), "GP")
        label = next((l for c, l, k, _ in TYPES if k == self.kind), "")
        widgets.draw_text(surf, f"GRAPHE — {code}  {label}", (40, 18),
                          fonts.title(bold=True), config.COL_AMBER)
        # sous-titre : actifs + période
        per = next((p for p, s in PERIODS if s == self.period), "5A")
        assets = "—" if self.kind in _NO_ASSET else " · ".join(self.tickers) or "—"
        widgets.draw_text(surf, f"{assets}    ·    période {per}", (42, 62),
                          fonts.small(), config.COL_TEXT_DIM)

        self._draw_info_bar(surf)
        self._draw_type_tabs(surf)
        self._draw_controls(surf)

        canvas_top = self._controls_bottom + 10
        canvas_bottom = config.footer_y() - 10
        rsi_h = 110 if (self.kind == "line" and self.show_rsi) else 0
        main_h = canvas_bottom - canvas_top - (rsi_h + 12 if rsi_h else 0)
        canvas = pygame.Rect(40, canvas_top, config.SCREEN_WIDTH - 80, main_h)
        widgets.draw_panel(surf, canvas, None)
        inner = canvas.inflate(-24, -24)
        inner.height -= 14   # réserve une marge pour les libellés d'axe X
        drawer = getattr(self, f"_draw_{self.kind}", None)
        if drawer:
            drawer(surf, inner)

        if rsi_h:
            rsi_canvas = pygame.Rect(40, canvas.bottom + 12, config.SCREEN_WIDTH - 80, rsi_h)
            widgets.draw_panel(surf, rsi_canvas, None)
            self._draw_rsi_panel(surf, rsi_canvas.inflate(-24, -16))

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("PAGE PRÉC/SUIV", "défiler"), ("ESC", "retour")])
        self.back_btn.draw(surf)
        if self.kind == "spread":
            self.mode_btn.draw(surf)
        self._draw_suggestions(surf)   # overlay : au-dessus du graphe
        self.popups_draw(surf)

    def _draw_info_bar(self, surf):
        """Barre d'infos clés de l'actif principal sélectionné, affichée
        au-dessus du sélecteur de type de graphe (avec une marge suffisante
        sous le sous-titre noms/période pour ne jamais le chevaucher). Clic
        sur le nom -> Explorer pré-rempli ; clic droit -> fiche d'analyse
        flottante ; clic sur un badge (type/région/secteur) -> Explorer
        pré-filtré sur ce critère."""
        self._info_name_rect = None
        self._type_badge_rect = None
        self._region_badge_rect = None
        self._sector_badge_rect = None
        if self.kind in _NO_ASSET or not self.tickers:
            return
        info = self._info_for(self.tickers[0])
        if not info:
            return
        y = 90
        x = 40
        self._info_name_rect = pygame.Rect(x, y, 90, 18)
        widgets.draw_text(surf, self.tickers[0], (x, y), fonts.small(bold=True), config.COL_CYAN)
        x += 96
        self._type_badge_rect = widgets.draw_badge(surf, info["type"], (x, y - 2), config.COL_TEXT_DIM)
        x += 100
        if info["region"]:
            self._region_badge_rect = widgets.draw_badge(surf, info["region"], (x, y - 2), config.COL_AMBER)
            x += 110
        if info["sector"]:
            self._sector_badge_rect = widgets.draw_badge(surf, info["sector"], (x, y - 2), config.COL_WARN)
            x += 140
        vx = x + 10
        for label, val in info["values"]:
            widgets.draw_text(surf, f"{label} {val}", (vx, y), fonts.tiny(), config.COL_TEXT_DIM)
            vx += 130

    def _draw_type_tabs(self, surf):
        self._type_rects = {}
        x, y, h = 40, 120, 30
        w = (config.SCREEN_WIDTH - 80 - (len(TYPES) - 1) * 4) // len(TYPES)
        for code, _, kind, _ in TYPES:
            rect = pygame.Rect(x, y, w, h)
            self._type_rects[code] = rect
            sel = (kind == self.kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1)
            font = fonts.small(bold=sel)
            img = font.render(code, True, config.COL_AMBER if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            x += w + 4

    def _draw_controls(self, surf):
        # sélecteur de période (gauche)
        self._period_rects = {}
        choices = self._period_choices()
        btn_w = 44 if len(choices) > 4 else 56
        x, y = 40, 158
        for plabel, steps in choices:
            rect = pygame.Rect(x, y, btn_w, 26)
            self._period_rects[steps] = rect
            sel = (steps == self.period)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1)
            font = fonts.small(bold=sel)
            img = font.render(plabel, True, config.COL_CYAN if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            x += btn_w + 4
        # saisie d'actif (droite) + recherche intelligente par nom OU ticker
        if self.kind not in _NO_ASSET:
            hint = "+ NOM/TICKER" if self.kind in _MULTI else "NOM/TICKER"
            box = pygame.Rect(x + 16, y, 300, 26)
            self._input_box = box
            pygame.draw.rect(surf, config.COL_PANEL, box)
            pygame.draw.rect(surf, config.COL_CYAN if self.input else config.COL_BORDER, box, 1)
            widgets.draw_text(surf, f"{hint} ▸ {self.input}_", (box.x + 8, box.y + 5),
                              fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, "ou cliquez ci-dessous",
                              (box.right + 12, box.y + 5), fonts.tiny(), config.COL_TEXT_DIM)
        else:
            self._input_box = None
        y += 34
        if self.kind not in _NO_ASSET:
            y = self._draw_asset_picker(surf, y)
        if self.kind == "line":
            y = self._draw_indicator_toggles(surf, y)
        self._controls_bottom = y

    def _quick_candidates(self, limit=8):
        """Actifs cliquables proposés sans avoir à taper : watchlist puis
        portefeuille du joueur, complétés par les plus grosses capitalisations —
        pour faciliter le choix de 2+ actifs (comparaison, spread, corrélation)."""
        p = self.app.gs.player
        seen = set(self.tickers)
        out = []
        for tk in list(p.watchlist) + list(p.portfolio.keys()):
            if tk not in seen and _asset_exists(self.market, tk):
                seen.add(tk)
                out.append(tk)
        if len(out) < limit:
            for c in self.market.top_companies(n=limit):
                tk = c["ticker"]
                if tk not in seen:
                    seen.add(tk)
                    out.append(tk)
                if len(out) >= limit:
                    break
        return out[:limit]

    def _draw_asset_picker(self, surf, y):
        """Puces cliquables : actifs sélectionnés (retirables d'un clic) puis
        suggestions rapides (watchlist/portefeuille/plus grosses capis) — pour
        choisir sans taper, surtout utile dès qu'il faut 2+ actifs (COMP/HS/CORR)."""
        self._chip_rects = []
        self._quickadd_rects = []
        x = 40
        lbl_font = fonts.tiny()
        if self.tickers:
            img = lbl_font.render("Sélection :", True, config.COL_TEXT_DIM)
            surf.blit(img, (x, y + 5))
            x += img.get_width() + 8
            chip_zone_right = config.SCREEN_WIDTH - 200   # laisse de la place aux suggestions
            for n, tk in enumerate(self.tickers):
                label = f"{tk}  ✕"
                w = fonts.tiny(bold=True).size(label)[0] + 16
                remaining = len(self.tickers) - n
                if x + w > chip_zone_right and remaining > 1:
                    more = widgets.draw_badge(surf, f"+{remaining}", (x, y), config.COL_TEXT_DIM)
                    x = more.right + 6
                    break
                rect = pygame.Rect(x, y, w, 24)
                self._chip_rects.append((rect, tk))
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_AMBER, rect, 1, border_radius=4)
                widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=True),
                                  config.COL_AMBER, align="center")
                x += w + 6
            x += 14

        candidates = self._quick_candidates()
        if candidates:
            label = "Ajout rapide :" if self.kind in _MULTI else "Suggestions :"
            img = lbl_font.render(label, True, config.COL_TEXT_DIM)
            surf.blit(img, (x, y + 5))
            x += img.get_width() + 8
            for tk in candidates:
                w = fonts.tiny(bold=True).size(tk)[0] + 16
                if x + w > config.SCREEN_WIDTH - 40:
                    break
                rect = pygame.Rect(x, y, w, 24)
                self._quickadd_rects.append((rect, tk))
                pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_CYAN, rect, 1, border_radius=4)
                widgets.draw_text(surf, tk, rect.center, fonts.tiny(bold=True),
                                  config.COL_CYAN, align="center")
                x += w + 6
        return y + 32

    def _draw_indicator_toggles(self, surf, y):
        """Rangée de boutons toggle pour les indicateurs techniques superposables
        (SMA20, Bollinger, RSI) — purement analytique, aucun impact gameplay."""
        x = 40
        for attr, btn, accent in self._indicator_btns:
            btn.rect.topleft = (x, y)
            active = getattr(self, attr)
            btn.accent = accent if active else config.COL_TEXT_DIM
            btn.draw(surf)
            if active:
                pygame.draw.rect(surf, accent, btn.rect, 2, border_radius=6)
            x += btn.rect.w + 8
        return y + 34

    def _draw_suggestions(self, surf):
        """Menu déroulant de recherche intelligente (dessiné EN DERNIER, au-dessus
        du graphe) : nom déformé → ticker, cliquable."""
        self._suggest_rects = []
        box = getattr(self, "_input_box", None)
        if not box or not self.input.strip():
            return
        sy = box.bottom + 2
        for tk, nm in self.market.suggest(self.input, 8):
            rr = pygame.Rect(box.x, sy, box.w + 220, 22)
            self._suggest_rects.append((rr, tk))
            hov = rr.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, rr)
            pygame.draw.rect(surf, config.COL_CYAN if hov else config.COL_BORDER, rr, 1)
            widgets.draw_text(surf, tk, (rr.x + 8, rr.y + 3), fonts.small(bold=True),
                              config.COL_AMBER)
            widgets.draw_text(surf, widgets.fit_text(nm, fonts.tiny(), rr.w - 90),
                              (rr.x + 80, rr.y + 4), fonts.tiny(), config.COL_TEXT_DIM)
            sy += 22

