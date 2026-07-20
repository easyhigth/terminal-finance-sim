"""
app_creditdesk.py — Application « Desk Crédit » du bureau (NATIVE).

Deux onglets de crédit « qui s'étudient » :

- MERTON (core/credit_risk.py) : la dette comme OPTION — les actions sont
  un call sur les actifs de l'entreprise (strike = la dette). Pour chaque
  société : distance au défaut, probabilité de défaut, spread implicite,
  et la courbe PD vs cours de l'action (le lien actions ↔ crédit rendu
  visible : une action qui chute rapproche la société du défaut). Scanner
  des sociétés les plus risquées du roster.

- WATERFALL (core/securitisation, tranches réelles du jeu) : la CASCADE
  des pertes d'un pool titrisé, interactive — un curseur règle la perte du
  pool (◀ ▶ ou clic sur la jauge) et on VOIT l'equity absorber d'abord,
  la mezzanine ensuite, le senior en dernier. Comprendre 2008 en le
  regardant. La perte ATTENDUE courante du pool (macro du jeu) est
  marquée sur la jauge.
"""
import pygame

from apps.base import DesktopApp
from core import config, i18n
from core import credit_risk as CR
from core import securitisation as SEC
from ui import fonts, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


TABS = [("merton", "MERTON"), ("cdsdesk", "CDS"),
        ("trs", "TRS"), ("convert", "CONVERTIBLES"), ("waterfall", "WATERFALL")]
CDS_NOTIONALS = [100_000.0, 250_000.0, 500_000.0]
CONV_QTYS = [10, 25, 50]
TRS_SIDES = [("receiver", "RECEIVER"), ("payer", "PAYER")]


class CreditDeskApp(DesktopApp):
    title = "Desk Crédit"
    icon_kind = "quant"
    default_size = (1080, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.tab = "merton"
        self.ticker = None
        self.pool_loss = 0.15                # curseur du waterfall
        self._cache_key = None
        self._scan = []
        self._fiche = None
        self._curve = []
        self._tab_rects = {}
        self._scan_rects = {}
        self._slider_rect = None
        self._dragging = False
        self.cds_tenor = 3.0
        self.cds_notional = CDS_NOTIONALS[1]
        self.conv_qty = CONV_QTYS[1]
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self._cds_tenor_rects = {}
        self._cds_notional_rects = {}
        self._cds_buy_btn = None
        self._cds_close_rects = {}
        self._conv_qty_rects = {}
        self._conv_buy_btn = None
        self._conv_sell_rects = {}
        self._conv_arb_rects = {}
        self.trs_side = "receiver"
        self.trs_tenor = 3.0
        self.trs_notional = CDS_NOTIONALS[1]
        self._trs_side_rects = {}
        self._trs_tenor_rects = {}
        self._trs_notional_rects = {}
        self._trs_open_btn = None
        self._trs_close_rects = {}

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        key = (self.market.step_count, self.ticker)
        if key == self._cache_key:
            return
        self._cache_key = key
        self._scan = CR.market_scan(self.market, n=12)
        if self.ticker is None and self._scan:
            self.ticker = self._scan[0]["ticker"]
        self._fiche = (CR.merton_credit(self.market, self.ticker)
                       if self.ticker else None)
        self._curve = (CR.pd_vs_equity_curve(self.market, self.ticker)
                       if self.ticker else [])

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
            return False
        if event.type == pygame.MOUSEMOTION and self._dragging:
            self._set_loss_from_x(event.pos[0])
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for tab, r in self._tab_rects.items():
            if r.collidepoint(pos):
                self.tab = tab
                return True
        for tk, r in self._scan_rects.items():
            if r.collidepoint(pos):
                self.ticker = tk
                return True
        if self._slider_rect and self._slider_rect.inflate(0, 10).collidepoint(pos):
            self._dragging = True
            self._set_loss_from_x(pos[0])
            return True
        for t, r in self._cds_tenor_rects.items():
            if r.collidepoint(pos):
                self.cds_tenor = t
                return True
        for v, r in self._cds_notional_rects.items():
            if r.collidepoint(pos):
                self.cds_notional = v
                return True
        if self._cds_buy_btn and self._cds_buy_btn.collidepoint(pos):
            from core import cds as CDS
            r = CDS.buy_protection(self.app.gs.player, self.market, self.ticker,
                                   self.cds_notional, self.cds_tenor)
            if r.get("ok"):
                self.msg = _L(f"Protection achetée : {r['quote']['spread_bps']:.0f} bp/an "
                            "courus chaque pas — la peur du défaut se trade en MTM.",
                            f"Protection bought: {r['quote']['spread_bps']:.0f} bp/yr "
                            "accruing each step — default fear trades in MTM.")
                self.msg_col = config.COL_UP
            else:
                self.msg, self.msg_col = _L(f"Refusé : {r.get('reason', '?')}.", f"Rejected: {r.get('reason', '?')}."), config.COL_DOWN
            return True
        for pid, r in self._cds_close_rects.items():
            if r.collidepoint(pos):
                from core import cds as CDS
                res = CDS.close(self.app.gs.player, self.market, pid)
                if res.get("ok"):
                    self.msg = _L(f"Protection dénouée — MTM {res['mtm']:+,.0f}.", f"Protection closed — MTM {res['mtm']:+,.0f}.")
                    self.msg_col = (config.COL_UP if res["mtm"] >= 0
                                    else config.COL_DOWN)
                return True
        for q, r in self._conv_qty_rects.items():
            if r.collidepoint(pos):
                self.conv_qty = q
                return True
        if self._conv_buy_btn and self._conv_buy_btn.collidepoint(pos):
            from core import convertibles as CONV
            r = CONV.buy(self.app.gs.player, self.market, self.ticker, self.conv_qty)
            if r.get("ok"):
                q = r["quote"]
                self.msg = _L(f"Convertible achetée : plancher {q['bond_floor']:,.0f} "
                            f"+ option {q['option_value']:,.0f} = {q['price']:,.0f}/titre.",
                            f"Convertible bought: floor {q['bond_floor']:,.0f} "
                            f"+ option {q['option_value']:,.0f} = {q['price']:,.0f}/unit.")
                self.msg_col = config.COL_UP
            else:
                self.msg, self.msg_col = _L(f"Refusé : {r.get('reason', '?')}.", f"Rejected: {r.get('reason', '?')}."), config.COL_DOWN
            return True
        for pid, r in self._conv_sell_rects.items():
            if r.collidepoint(pos):
                from core import convertibles as CONV
                res = CONV.sell(self.app.gs.player, self.market, pid)
                if res.get("ok"):
                    self.msg = _L(f"Convertible revendue — P&L {res['pnl']:+,.0f}.", f"Convertible sold — P&L {res['pnl']:+,.0f}.")
                    self.msg_col = (config.COL_UP if res["pnl"] >= 0
                                    else config.COL_DOWN)
                return True
        for pid, r in self._conv_arb_rects.items():
            if r.collidepoint(pos):
                self._conv_arb(pid)
                return True
        for s, r in self._trs_side_rects.items():
            if r.collidepoint(pos):
                self.trs_side = s
                return True
        for t, r in self._trs_tenor_rects.items():
            if r.collidepoint(pos):
                self.trs_tenor = t
                return True
        for v, r in self._trs_notional_rects.items():
            if r.collidepoint(pos):
                self.trs_notional = v
                return True
        if self._trs_open_btn and self._trs_open_btn.collidepoint(pos):
            from core import trs as TRS
            r = TRS.open_trs(self.app.gs.player, self.market, self.ticker,
                             self.trs_notional, self.trs_tenor, self.trs_side)
            if r.get("ok"):
                q = r["quote"]
                _lab = ("Receiver" if self.trs_side == "receiver" else "Payer")
                self.msg = _L(f"TRS {_lab} ouvert : financement "
                            f"{q['ref_rate']*100:.1f}% + {q['funding_bps']:.0f} bp/an "
                            "— le rendement total se règle au MTM.",
                            f"TRS {_lab} opened: funding "
                            f"{q['ref_rate']*100:.1f}% + {q['funding_bps']:.0f} bp/yr "
                            "— total return settles in MTM.")
                self.msg_col = config.COL_UP
            else:
                self.msg, self.msg_col = _L(f"Refusé : {r.get('reason', '?')}.", f"Rejected: {r.get('reason', '?')}."), config.COL_DOWN
            return True
        for pid, r in self._trs_close_rects.items():
            if r.collidepoint(pos):
                from core import trs as TRS
                res = TRS.close(self.app.gs.player, self.market, pid)
                if res.get("ok"):
                    self.msg = _L(f"TRS dénoué — MTM {res['mtm']:+,.0f}.", f"TRS closed — MTM {res['mtm']:+,.0f}.")
                    self.msg_col = (config.COL_UP if res["mtm"] >= 0
                                    else config.COL_DOWN)
                return True
        return False

    def _conv_arb(self, pos_id):
        """Arbitrage convertible : short delta actions (core/portfolio.short,
        soumis au déblocage leverage comme tout short)."""
        from core import convertibles as CONV
        from core import portfolio as pf
        from core import unlocks
        p = self.app.gs.player
        pos = next((c for c in getattr(p, "convertibles", []) or []
                    if c["id"] == pos_id), None)
        if pos is None:
            return
        if not unlocks.unlocked(p, "leverage"):
            g = unlocks.effective_required_grade(p, "leverage")
            self.msg = _L(f"Short verrouillé (grade {config.GRADES[g]}).", f"Short locked (grade {config.GRADES[g]}).")
            self.msg_col = config.COL_DOWN
            return
        plan = CONV.arb_plan(self.market, pos)
        if plan is None:
            self.msg, self.msg_col = _L("Delta trop petit pour l'arbitrage.", "Delta too small for arbitrage."), config.COL_TEXT_DIM
            return
        r = pf.short(p, self.market, plan["ticker"], plan["shares"])
        if r.get("ok"):
            self.msg = _L(f"Arb posé : short {plan['shares']} × {plan['ticker']} — "
                        "direction neutralisée, on porte le coupon.",
                        f"Arb set: short {plan['shares']} × {plan['ticker']} — "
                        "direction neutralized, carrying the coupon.")
            self.msg_col = config.COL_UP
        else:
            self.msg, self.msg_col = _L(f"Short refusé : {r.get('reason', '?')}.", f"Short rejected: {r.get('reason', '?')}."), config.COL_DOWN

    def _set_loss_from_x(self, x):
        r = self._slider_rect
        if r is None or r.w <= 0:
            return
        self.pool_loss = max(0.0, min(1.0, (x - r.x) / r.w))

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, _L("DESK CRÉDIT — DÉFAUT, SPREADS, TITRISATION", "CREDIT DESK — DEFAULT, SPREADS, SECURITIZATION"),
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        x, y = rect.x + pad, rect.y + 32
        self._tab_rects = {}
        for tab, lbl in TABS:
            w = fonts.tiny(bold=True).size(lbl)[0] + 18
            r = pygame.Rect(x, y, w, 22)
            self._tab_rects[tab] = r
            sel = tab == self.tab
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 8
        body = pygame.Rect(rect.x + pad, y + 30, rect.w - 2 * pad,
                           rect.bottom - pad - y - 30)
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(),
                                                     rect.w - 2 * pad),
                              (rect.x + pad, body.y - 6), fonts.tiny(),
                              self.msg_col)
        if self.tab == "merton":
            self._draw_merton(surf, body)
        elif self.tab == "cdsdesk":
            self._draw_cds(surf, body)
        elif self.tab == "trs":
            self._draw_trs(surf, body)
        elif self.tab == "convert":
            self._draw_convertibles(surf, body)
        else:
            self._draw_waterfall(surf, body)

    def _chips(self, surf, items, current, x, y, accent, rects):
        for key, lbl in items:
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            rects[key] = r
            sel = key == current
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              accent if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        return x

    # ----------------------------------------------------------------- CDS
    def _draw_cds(self, surf, body):
        from core import cds as CDS
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left,
                                   _L(f"Protection sur {self.ticker or '—'}", f"Protection on {self.ticker or '—'}"),
                                   config.COL_CYAN)
        # scanner réutilisé (sélection de la société, PD décroissante)
        self._scan_rects = {}
        y = inner.y + 2
        for row in self._scan[:6]:
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 19)
            self._scan_rects[row["ticker"]] = r
            sel = row["ticker"] == self.ticker
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, f"{row['ticker']} — PD {row['pd'] * 100:.1f}%",
                              (inner.x, y), fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            y += 20
        y += 6
        self._cds_tenor_rects = {}
        self._chips(surf, [(t, _L(f"{t:.0f} an{'s' if t > 1 else ''}", f"{t:.0f}y"))
                           for t in CDS.TENORS],
                    self.cds_tenor, inner.x, y, config.COL_CYAN,
                    self._cds_tenor_rects)
        y += 26
        self._cds_notional_rects = {}
        self._chips(surf, [(v, widgets.format_money(v, cur))
                           for v in CDS_NOTIONALS],
                    self.cds_notional, inner.x, y, config.COL_AMBER,
                    self._cds_notional_rects)
        y += 28
        q = (CDS.quote(self.market, self.ticker, self.cds_tenor)
             if self.ticker else None)
        self._cds_buy_btn = None
        if q:
            widgets.draw_text(surf, _L(f"Prime : {q['spread_bps']:.0f} bp/an "
                              f"(Merton + {CDS.MARKET_SPREAD_BPS:.0f} bp de marge) "
                              f"≈ {widgets.format_money(q['spread_bps'] / 1e4 * self.cds_notional, cur)}/an",
                              f"Premium: {q['spread_bps']:.0f} bp/yr "
                              f"(Merton + {CDS.MARKET_SPREAD_BPS:.0f} bp margin) "
                              f"≈ {widgets.format_money(q['spread_bps'] / 1e4 * self.cds_notional, cur)}/yr"),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            y += 22
            # les bps traduits en concret (core/impact_phrases)
            from core import impact_phrases as _ip
            widgets.draw_text(surf, widgets.fit_text(
                _ip.cds_impact(self.market, self.ticker, self.cds_notional,
                               self.cds_tenor), fonts.tiny(), inner.w),
                (inner.x, y), fonts.tiny(), config.COL_WARN)
            y += 20
            self._cds_buy_btn = pygame.Rect(inner.x, y, 220, 26)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._cds_buy_btn,
                             border_radius=4)
            pygame.draw.rect(surf, config.COL_UP, self._cds_buy_btn, 1,
                             border_radius=4)
            widgets.draw_text(surf, _L("ACHETER LA PROTECTION", "BUY THE PROTECTION"),
                              self._cds_buy_btn.center, fonts.small(bold=True),
                              config.COL_UP, align="center")
        widgets.draw_text(surf, _L("Évènement de crédit du jeu : action sous "
                          f"{CDS.TRIGGER_FRAC * 100:.0f}% du niveau d'entrée → "
                          f"paie {(1 - CDS.RECOVERY) * 100:.0f}% du notionnel.",
                          "Game credit event: stock below "
                          f"{CDS.TRIGGER_FRAC * 100:.0f}% of entry level → "
                          f"pays {(1 - CDS.RECOVERY) * 100:.0f}% of notional."),
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
        rinner = widgets.draw_panel(surf, right, _L("Protections en cours (MTM)", "Active protections (MTM)"),
                                    config.COL_AMBER)
        self._cds_close_rects = {}
        hh = CDS.holdings(self.app.gs.player, self.market)
        if not hh:
            widgets.draw_text(surf, _L("Aucune.", "None."), (rinner.x, rinner.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        y = rinner.y + 2
        for h in hh:
            if y > rinner.bottom - 36:
                break
            mcol = config.COL_UP if h["mtm"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{h['ticker']} · "
                              f"{widgets.format_money(h['notional'], cur)} · "
                              f"payé {h['entry_spread_bps']:.0f} bp",
                              (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            cur_s = (f"{h['cur_spread_bps']:.0f}" if h["cur_spread_bps"]
                     else "—")
            widgets.draw_text(surf, _L(f"spread {cur_s} bp · MTM {h['mtm']:+,.0f} · "
                              f"{h['steps_left']} pas",
                              f"spread {cur_s} bp · MTM {h['mtm']:+,.0f} · "
                              f"{h['steps_left']} steps"),
                              (rinner.x + 8, y + 16), fonts.tiny(), mcol)
            xr = pygame.Rect(rinner.right - 22, y, 18, 18)
            self._cds_close_rects[h["id"]] = xr
            pygame.draw.rect(surf, config.COL_PANEL, xr, border_radius=3)
            widgets.draw_text(surf, "×", xr.center, fonts.small(bold=True),
                              config.COL_DOWN, align="center")
            y += 36

    # --------------------------------------------------------------- TRS
    def _draw_trs(self, surf, body):
        from core import trs as TRS
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left,
                                   _L(f"TRS sur {self.ticker or '—'}", f"TRS on {self.ticker or '—'}"),
                                   config.COL_CYAN)
        # scanner réutilisé (sélection de la société, PD décroissante)
        self._scan_rects = {}
        y = inner.y + 2
        for row in self._scan[:6]:
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 19)
            self._scan_rects[row["ticker"]] = r
            sel = row["ticker"] == self.ticker
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, f"{row['ticker']} — PD {row['pd'] * 100:.1f}%",
                              (inner.x, y), fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            y += 20
        y += 6
        # sens : RECEIVER (long synth. à levier) / PAYER (short synth.)
        self._trs_side_rects = {}
        self._chips(surf, TRS_SIDES, self.trs_side, inner.x, y,
                    config.COL_CYAN, self._trs_side_rects)
        y += 26
        self._trs_tenor_rects = {}
        self._chips(surf, [(t, _L(f"{t:.0f} an{'s' if t > 1 else ''}", f"{t:.0f}y"))
                           for t in TRS.TENORS],
                    self.trs_tenor, inner.x, y, config.COL_CYAN,
                    self._trs_tenor_rects)
        y += 26
        self._trs_notional_rects = {}
        self._chips(surf, [(v, widgets.format_money(v, cur))
                           for v in CDS_NOTIONALS],
                    self.trs_notional, inner.x, y, config.COL_AMBER,
                    self._trs_notional_rects)
        y += 28
        q = (TRS.quote(self.market, self.ticker, self.trs_tenor)
             if self.ticker else None)
        self._trs_open_btn = None
        if q:
            cost = q["ref_rate"] * 1e2 + q["funding_bps"] / 1e2
            widgets.draw_text(surf, _L(f"Financement : {q['ref_rate']*100:.1f}% réf. "
                              f"+ {q['funding_bps']:.0f} bp = {cost:.2f}%/an "
                              f"≈ {widgets.format_money(cost/100 * self.trs_notional, cur)}/an",
                              f"Funding: {q['ref_rate']*100:.1f}% ref. "
                              f"+ {q['funding_bps']:.0f} bp = {cost:.2f}%/yr "
                              f"≈ {widgets.format_money(cost/100 * self.trs_notional, cur)}/yr"),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            y += 22
            from core import impact_phrases as _ip
            _lab = _ip.trs_impact(self.trs_notional,
                                  q["ref_rate"] + q["funding_bps"] / 1e4,
                                  side=self.trs_side)
            y += widgets.draw_text_wrapped(surf, _lab, (inner.x, y), fonts.tiny(),
                                           config.COL_WARN, inner.w, line_gap=3) + 4
            self._trs_open_btn = pygame.Rect(inner.x, y, 200, 26)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._trs_open_btn,
                             border_radius=4)
            pygame.draw.rect(surf, config.COL_UP, self._trs_open_btn, 1,
                             border_radius=4)
            widgets.draw_text(surf, _L("OUVRIR LE TRS", "OPEN THE TRS"),
                              self._trs_open_btn.center, fonts.small(bold=True),
                              config.COL_UP, align="center")
        widgets.draw_text(surf, _L("Évènement de crédit du jeu : action sous "
                          f"{TRS.TRIGGER_FRAC * 100:.0f}% de l'entrée → le receiver "
                          f"absorbe {(1 - TRS.RECOVERY) * 100:.0f}% du notionnel "
                          f"(le payer gagne symétriquement).",
                          "Game credit event: stock below "
                          f"{TRS.TRIGGER_FRAC * 100:.0f}% of entry → the receiver "
                          f"absorbs {(1 - TRS.RECOVERY) * 100:.0f}% of notional "
                          "(the payer gains symmetrically)."),
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
        rinner = widgets.draw_panel(surf, right, _L("TRS en cours (MTM vivant)", "Active TRS (live MTM)"),
                                    config.COL_AMBER)
        self._trs_close_rects = {}
        hh = TRS.holdings(self.app.gs.player, self.market)
        if not hh:
            widgets.draw_text(surf, _L("Aucun.", "None."), (rinner.x, rinner.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        y = rinner.y + 2
        for h in hh:
            if y > rinner.bottom - 36:
                break
            mcol = config.COL_UP if h["mtm"] >= 0 else config.COL_DOWN
            _tag = "REC" if h["side"] == "receiver" else "PAY"
            widgets.draw_text(surf, f"{_tag} {h['ticker']} · "
                              f"{widgets.format_money(h['notional'], cur)} · "
                              f"{h['funding_bps']:.0f} bp",
                              (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            px = (f"{h['price']:.2f}" if h["price"] else "—")
            widgets.draw_text(surf, _L(f"cours {px} · MTM {h['mtm']:+,.0f} · "
                              f"{h['steps_left']} pas",
                              f"price {px} · MTM {h['mtm']:+,.0f} · "
                              f"{h['steps_left']} steps"),
                              (rinner.x + 8, y + 16), fonts.tiny(), mcol)
            xr = pygame.Rect(rinner.right - 22, y, 18, 18)
            self._trs_close_rects[h["id"]] = xr
            pygame.draw.rect(surf, config.COL_PANEL, xr, border_radius=3)
            widgets.draw_text(surf, "×", xr.center, fonts.small(bold=True),
                              config.COL_DOWN, align="center")
            y += 36

    # -------------------------------------------------------- convertibles
    def _draw_convertibles(self, surf, body):
        from core import convertibles as CONV
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left,
                                   _L(f"Convertible sur {self.ticker or '—'} "
                                   "(émise au spot)",
                                   f"Convertible on {self.ticker or '—'} "
                                   "(issued at spot)"), config.COL_CYAN)
        self._scan_rects = {}
        y = inner.y + 2
        for c in self.market.top_companies(n=6):
            tk = c["ticker"]
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 19)
            self._scan_rects[tk] = r
            sel = tk == self.ticker
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, tk, (inner.x, y), fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            y += 20
        y += 6
        self._conv_qty_rects = {}
        self._chips(surf, [(q, str(q)) for q in CONV_QTYS], self.conv_qty,
                    inner.x, y, config.COL_AMBER, self._conv_qty_rects)
        y += 28
        q = CONV.quote(self.market, self.ticker) if self.ticker else None
        self._conv_buy_btn = None
        if q:
            lines = [
                (_L(f"Plancher obligataire {q['bond_floor']:,.0f} + option "
                 f"{q['option_value']:,.0f} = {q['price']:,.0f}",
                 f"Bond floor {q['bond_floor']:,.0f} + option "
                 f"{q['option_value']:,.0f} = {q['price']:,.0f}"), config.COL_TEXT),
                (_L(f"Coupon {q['coupon'] * 100:.2f}% (réduit : le droit de "
                 f"conversion se paie) · strike {q['strike']:,.1f}",
                 f"Coupon {q['coupon'] * 100:.2f}% (reduced: the conversion "
                 f"right is paid for) · strike {q['strike']:,.1f}"),
                 config.COL_TEXT_DIM),
                (_L(f"Delta {q['delta']:.2f} action/titre · prime sur parité "
                 f"{q['premium_over_parity'] * 100:+.0f}%",
                 f"Delta {q['delta']:.2f} share/unit · premium over parity "
                 f"{q['premium_over_parity'] * 100:+.0f}%"), config.COL_AMBER),
            ]
            for txt, col in lines:
                widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.w),
                                  (inner.x, y), fonts.tiny(), col)
                y += 16
            y += 8
            self._conv_buy_btn = pygame.Rect(inner.x, y, 220, 26)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._conv_buy_btn,
                             border_radius=4)
            pygame.draw.rect(surf, config.COL_UP, self._conv_buy_btn, 1,
                             border_radius=4)
            widgets.draw_text(surf, _L(f"ACHETER ({widgets.format_money(q['price'] * self.conv_qty, cur)})", f"BUY ({widgets.format_money(q['price'] * self.conv_qty, cur)})"),
                              self._conv_buy_btn.center, fonts.small(bold=True),
                              config.COL_UP, align="center")
        widgets.draw_text(surf, _L("Δ ≈ 0 : c'est une obligation · Δ ≈ ratio : "
                          "c'est une action — le plancher + le kicker.",
                          "Δ ≈ 0: it's a bond · Δ ≈ ratio: "
                          "it's a stock — the floor + the kicker."),
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
        rinner = widgets.draw_panel(surf, right, _L("Convertibles détenues", "Convertibles held"),
                                    config.COL_AMBER)
        self._conv_sell_rects = {}
        self._conv_arb_rects = {}
        hh = CONV.holdings(self.app.gs.player, self.market)
        if not hh:
            widgets.draw_text(surf, _L("Aucune.", "None."), (rinner.x, rinner.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        y = rinner.y + 2
        for h in hh:
            if y > rinner.bottom - 40:
                break
            pcol = config.COL_UP if h["pnl"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{h['qty']} × {h['ticker']} — "
                              f"{widgets.format_money(h['value'], cur)}",
                              (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"P&L {h['pnl']:+,.0f} · Δ {h['quote']['delta']:.2f}",
                              (rinner.x + 8, y + 16), fonts.tiny(), pcol)
            ar = pygame.Rect(rinner.right - 84, y, 56, 18)
            self._conv_arb_rects[h["id"]] = ar
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, ar, border_radius=3)
            pygame.draw.rect(surf, config.COL_PRESTIGE, ar, 1, border_radius=3)
            widgets.draw_text(surf, "ARB Δ", ar.center, fonts.tiny(bold=True),
                              config.COL_PRESTIGE, align="center")
            xr = pygame.Rect(rinner.right - 22, y, 18, 18)
            self._conv_sell_rects[h["id"]] = xr
            pygame.draw.rect(surf, config.COL_PANEL, xr, border_radius=3)
            widgets.draw_text(surf, "×", xr.center, fonts.small(bold=True),
                              config.COL_DOWN, align="center")
            y += 38

    # -------------------------------------------------------------- Merton
    def _draw_merton(self, surf, body):
        scan_w = 260
        scan = pygame.Rect(body.x, body.y, scan_w, body.h)
        rest = pygame.Rect(scan.right + 12, body.y, body.w - scan_w - 12, body.h)
        inner = widgets.draw_panel(surf, scan, _L("Scanner (PD décroissante)", "Scanner (decreasing PD)"),
                                   config.COL_DOWN)
        self._scan_rects = {}
        y = inner.y + 2
        for row in self._scan:
            if y > inner.bottom - 20:
                break
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 20)
            self._scan_rects[row["ticker"]] = r
            sel = row["ticker"] == self.ticker
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, row["ticker"], (inner.x, y),
                              fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            pcol = (config.COL_DOWN if row["pd"] > 0.05
                    else config.COL_AMBER if row["pd"] > 0.01 else config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"PD {row['pd'] * 100:.1f}% · "
                              f"{row['spread_bps']:.0f} bp",
                              (inner.x + 70, y), fonts.tiny(), pcol)
            y += 21
        f = self._fiche
        rinner = widgets.draw_panel(
            surf, rest, _L(f"{self.ticker or '—'} — la dette comme option", f"{self.ticker or '—'} — debt as an option"),
            config.COL_CYAN)
        if f is None:
            return
        y = rinner.y + 2
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        lines = [
            (_L(f"Actifs V = actions {widgets.format_money(f['equity'], cur)} + "
             f"dette {widgets.format_money(f['debt'], cur)}",
             f"Assets V = equity {widgets.format_money(f['equity'], cur)} + "
             f"debt {widgets.format_money(f['debt'], cur)}"), config.COL_TEXT),
            (_L(f"Levier D/E = {f['leverage']:.2f} · vol actions "
             f"{f['sigma_e'] * 100:.0f}% → vol actifs {f['sigma_v'] * 100:.0f}% "
             "(dé-leviérée)",
             f"Leverage D/E = {f['leverage']:.2f} · equity vol "
             f"{f['sigma_e'] * 100:.0f}% → asset vol {f['sigma_v'] * 100:.0f}% "
             "(unlevered)"), config.COL_TEXT_DIM),
        ]
        for txt, col in lines:
            widgets.draw_text(surf, widgets.fit_text(txt, fonts.small(), rinner.w),
                              (rinner.x, y), fonts.small(), col)
            y += 20
        y += 6
        dd_txt = "∞" if f["dd"] == float("inf") else f"{f['dd']:.2f}"
        pcol = (config.COL_DOWN if f["pd"] > 0.05
                else config.COL_AMBER if f["pd"] > 0.01 else config.COL_UP)
        widgets.draw_text(surf, _L(f"Distance au défaut : {dd_txt} σ", f"Distance to default: {dd_txt} σ"), (rinner.x, y),
                          fonts.head(bold=True), pcol)
        y += 26
        widgets.draw_text(surf, _L(f"PD 1 an : {f['pd'] * 100:.2f}% · spread "
                          f"implicite ≈ {f['spread_bps']:.0f} bp (LGD 60 %)",
                          f"1y PD: {f['pd'] * 100:.2f}% · implied "
                          f"spread ≈ {f['spread_bps']:.0f} bp (LGD 60%)"),
                          (rinner.x, y), fonts.small(bold=True), pcol)
        y += 28
        # courbe PD vs choc action
        if self._curve:
            plot = pygame.Rect(rinner.x, y, rinner.w - 8,
                               max(60, rinner.bottom - y - 34))
            pygame.draw.rect(surf, config.COL_PANEL, plot, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, plot, 1, border_radius=4)
            pds = [pd for _s, pd in self._curve]
            pmax = max(max(pds), 0.02)
            pts = []
            for i, (shock, pd) in enumerate(self._curve):
                x0 = plot.x + 14 + int(i / (len(self._curve) - 1) * (plot.w - 28))
                y0 = plot.bottom - 16 - int(pd / pmax * (plot.h - 34))
                pts.append((x0, y0))
                widgets.draw_text(surf, f"{shock * 100:+.0f}%", (x0 - 12, plot.bottom - 14),
                                  fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"{pd * 100:.1f}%", (x0 - 12, y0 - 14),
                                  fonts.tiny(), config.COL_DOWN)
            if len(pts) >= 2:
                pygame.draw.aalines(surf, config.COL_DOWN, False, pts)
            widgets.draw_text(surf, _L("PD si le COURS de l'action bouge de… — le lien "
                              "actions ↔ spreads.",
                              "PD if the stock PRICE moves by… — the "
                              "equity ↔ spreads link."), (plot.x + 6, plot.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)

    # ----------------------------------------------------------- Waterfall
    def _draw_waterfall(self, surf, body):
        inner = widgets.draw_panel(surf, body,
                                   _L("Cascade des pertes d'un pool titrisé", "Loss waterfall of a securitized pool"),
                                   config.COL_AMBER)
        widgets.draw_text(surf, _L("Glissez le curseur : la perte du pool remonte la "
                          "structure — l'equity absorbe d'abord, le senior en dernier.",
                          "Drag the slider: the pool loss climbs the "
                          "structure — equity absorbs first, senior last."),
                          (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        # curseur de perte de pool
        y = inner.y + 26
        self._slider_rect = pygame.Rect(inner.x, y + 6, inner.w - 160, 8)
        sr = self._slider_rect
        pygame.draw.rect(surf, config.COL_PANEL, sr, border_radius=4)
        fill = int(sr.w * self.pool_loss)
        pygame.draw.rect(surf, config.COL_DOWN,
                         pygame.Rect(sr.x, sr.y, fill, sr.h), border_radius=4)
        knob = pygame.Rect(0, 0, 10, 18)
        knob.center = (sr.x + fill, sr.centery)
        pygame.draw.rect(surf, config.COL_WHITE, knob, border_radius=3)
        widgets.draw_text(surf, _L(f"Perte du pool : {self.pool_loss * 100:.0f}%", f"Pool loss: {self.pool_loss * 100:.0f}%"),
                          (sr.right + 12, y), fonts.small(bold=True),
                          config.COL_DOWN)
        # perte attendue courante (macro du jeu) marquée sur la jauge
        el = SEC.expected_pool_loss(self.market)
        ex = sr.x + int(sr.w * min(1.0, el))
        pygame.draw.line(surf, config.COL_AMBER, (ex, sr.y - 6), (ex, sr.bottom + 6), 2)
        widgets.draw_text(surf, _L(f"attendue {el * 100:.0f}%", f"expected {el * 100:.0f}%"), (ex - 26, sr.bottom + 8),
                          fonts.tiny(), config.COL_AMBER)
        # tranches
        y += 46
        bar_h = max(36, (inner.bottom - y - 20) // len(SEC.TRANCHES) - 12)
        for tid, name, attach, detach, coupon, rating in SEC.TRANCHES:
            loss = SEC.tranche_loss_fraction(self.pool_loss, attach, detach)
            r = pygame.Rect(inner.x, y, inner.w - 8, bar_h)
            pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=4)
            dmg = int(r.w * loss)
            if dmg:
                pygame.draw.rect(surf, config.COL_DOWN,
                                 pygame.Rect(r.x, r.y, dmg, r.h), border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=4)
            widgets.draw_text(surf, f"{name} [{attach * 100:.0f}–{detach * 100:.0f}%] "
                              f"· coupon {coupon * 100:.1f}% · {rating}",
                              (r.x + 10, r.y + 6), fonts.small(bold=True),
                              config.COL_WHITE)
            status = (_L("INDEMNE", "UNSCATHED") if loss == 0.0
                      else _L("ANÉANTIE", "WIPED OUT") if loss >= 1.0 else f"−{loss * 100:.0f}%")
            scol = (config.COL_UP if loss == 0.0
                    else config.COL_DOWN if loss >= 1.0 else config.COL_AMBER)
            widgets.draw_text(surf, status, (r.right - 90, r.y + 6),
                              fonts.small(bold=True), scol)
            widgets.draw_text(surf, _L("le coupon paie le RISQUE de rang : plus on "
                              "est bas dans la cascade, plus il est gros",
                              "the coupon pays for RANK risk: the lower "
                              "you are in the waterfall, the bigger it is"),
                              (r.x + 10, r.y + bar_h - 16), fonts.tiny(),
                              config.COL_TEXT_DIM)
            y += bar_h + 12
