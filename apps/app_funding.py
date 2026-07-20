"""
app_funding.py — Application « Desk Financement » du bureau (NATIVE).

La plomberie des marchés, trois onglets :

- REPO (core/repo.py) : acheter des obligations EN PENSION — on ne paie
  cash que le haircut, le reste est emprunté au taux repo contre le titre
  en garantie. Le devis affiche le CARRY DE L'EQUITY (le rendement du
  levier) ; les positions montrent l'equity vs la marge de maintenance —
  et l'appel de marge tombe tout seul en crise (advance_step).
- PRÊT-TITRES (core/seclending.py) : les shorts paient désormais leur taux
  d'emprunt (« hard to borrow » sur les petites capis, pire en crise) ;
  l'interrupteur PRÊTER MES TITRES active le revenu de prêt sur les longs.
- TRÉSORERIE (core/money_market.py) : dépôts à terme (bloqués, mieux
  payés) et sweep au jour le jour (liquide, moins payé) — l'arbitrage
  liquidité/rendement du cash oisif.
"""
import pygame

from apps.base import DesktopApp
from core import bonds as B
from core import config, i18n
from core import money_market as MM
from core import repo as REPO
from core import seclending as SL
from ui import fonts, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


TABS = [("repo", ("REPO (pension livrée)", "REPO (delivery)")),
        ("lending", ("PRÊT-TITRES", "SEC. LENDING")),
        ("cash", ("TRÉSORERIE", "CASH"))]
REPO_QTYS = [20, 50, 100]
DEPOSIT_AMOUNTS = [100_000.0, 250_000.0, 500_000.0]


class FundingApp(DesktopApp):
    title = "Desk Financement"
    icon_kind = "book"
    default_size = (1080, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.tab = "repo"
        self.repo_bond = None
        self.repo_qty = REPO_QTYS[1]
        self.dep_amount = DEPOSIT_AMOUNTS[0]
        self.dep_term = MM.TERM_STEPS[1]
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self._tab_rects = {}
        self._bond_rects = {}
        self._qty_rects = {}
        self._open_btn = None
        self._close_rects = {}
        self._lend_toggle = None
        self._amount_rects = {}
        self._term_rects = {}
        self._dep_btn = None
        self._sweep_toggle = None

    def _say(self, text, col):
        self.msg, self.msg_col = text, col

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        p = self.app.gs.player
        for tab, r in self._tab_rects.items():
            if r.collidepoint(pos):
                self.tab = tab
                self.msg = ""
                return True
        for bid, r in self._bond_rects.items():
            if r.collidepoint(pos):
                self.repo_bond = bid
                return True
        for q, r in self._qty_rects.items():
            if r.collidepoint(pos):
                self.repo_qty = q
                return True
        if self._open_btn and self._open_btn.collidepoint(pos):
            r = REPO.open_repo(p, self.market, self.repo_bond, self.repo_qty)
            if r.get("ok"):
                dv = r["quote"]
                self._say(_L(f"Pension ouverte : marge "
                          f"{widgets.format_money(dv['margin'], self._cur())} "
                          f"pour {widgets.format_money(dv['value'], self._cur())} "
                          f"de collatéral (levier ×{dv['value'] / dv['margin']:.1f}).",
                          f"Repo opened: margin "
                          f"{widgets.format_money(dv['margin'], self._cur())} "
                          f"for {widgets.format_money(dv['value'], self._cur())} "
                          f"of collateral (leverage ×{dv['value'] / dv['margin']:.1f})."),
                          config.COL_UP)
            else:
                reason = {"cash": _L("marge > trésorerie", "margin > cash"),
                          "max_positions": _L("trop de pensions ouvertes", "too many open repos"),
                          "bond": _L("collatéral inconnu", "unknown collateral")}.get(r.get("reason"),
                                                            r.get("reason", "?"))
                self._say(_L(f"Refusé : {reason}.", f"Rejected: {reason}."), config.COL_DOWN)
            return True
        for pid, r in self._close_rects.items():
            if r.collidepoint(pos):
                res = REPO.close_repo(p, self.market, pid)
                if res.get("ok"):
                    self._say(_L(f"Pension dénouée — P&L {res['pnl']:+,.0f}.", f"Repo closed — P&L {res['pnl']:+,.0f}."),
                              config.COL_UP if res["pnl"] >= 0 else config.COL_DOWN)
                return True
        if self._lend_toggle and self._lend_toggle.collidepoint(pos):
            p.flags["sec_lending"] = not p.flags.get("sec_lending")
            return True
        for v, r in self._amount_rects.items():
            if r.collidepoint(pos):
                self.dep_amount = v
                return True
        for t, r in self._term_rects.items():
            if r.collidepoint(pos):
                self.dep_term = t
                return True
        if self._dep_btn and self._dep_btn.collidepoint(pos):
            r = MM.open_deposit(p, self.market, self.dep_amount, self.dep_term)
            if r.get("ok"):
                d = r["deposit"]
                self._say(_L(f"Dépôt ouvert à {d['rate'] * 100:.2f}%/an, "
                          f"bloqué {d['term_steps']} pas.",
                          f"Deposit opened at {d['rate'] * 100:.2f}%/yr, "
                          f"locked {d['term_steps']} steps."), config.COL_UP)
            else:
                self._say(_L(f"Refusé : {r.get('reason', '?')}.", f"Rejected: {r.get('reason', '?')}."), config.COL_DOWN)
            return True
        if self._sweep_toggle and self._sweep_toggle.collidepoint(pos):
            p.flags["mm_sweep"] = not p.flags.get("mm_sweep")
            return True
        return False

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, _L("DESK FINANCEMENT — REPO · PRÊT-TITRES · CASH", "FUNDING DESK — REPO · SEC. LENDING · CASH"),
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        x, y = rect.x + pad, rect.y + 32
        self._tab_rects = {}
        for tab, lblpair in TABS:
            lbl = _L(*lblpair)
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
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(),
                                                     rect.right - pad - x - 6),
                              (x + 6, y + 5), fonts.tiny(), self.msg_col)
        body = pygame.Rect(rect.x + pad, y + 28, rect.w - 2 * pad,
                           rect.bottom - pad - y - 28)
        if self.tab == "repo":
            self._draw_repo(surf, body)
        elif self.tab == "lending":
            self._draw_lending(surf, body)
        else:
            self._draw_cash(surf, body)

    def _chip_row(self, surf, items, current, x, y, accent, rects):
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

    # ------------------------------------------------------------------ repo
    def _draw_repo(self, surf, body):
        cur = self._cur()
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left, _L("Nouvelle pension (achat à levier)", "New repo (leveraged buy)"),
                                   config.COL_CYAN)
        quotes = sorted(B.sovereign_quotes(self.market), key=lambda q: q["years"])
        if self.repo_bond is None and quotes:
            self.repo_bond = quotes[-1]["id"]         # le plus long = plus de carry
        self._bond_rects = {}
        y = inner.y + 2
        widgets.draw_text(surf, _L("Collatéral (souverains) :", "Collateral (sovereigns):"), (inner.x, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 16
        for q in quotes[:6]:
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 19)
            self._bond_rects[q["id"]] = r
            sel = q["id"] == self.repo_bond
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(bold=True),
                                                     int(inner.w * 0.55)),
                              (inner.x, y), fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            widgets.draw_text(surf, _L(f"{q['years']:.0f}a · YTM {q['ytm'] * 100:.2f}%", f"{q['years']:.0f}y · YTM {q['ytm'] * 100:.2f}%"),
                              (inner.x + int(inner.w * 0.60), y), fonts.tiny(),
                              config.COL_TEXT_DIM)
            y += 20
        y += 6
        self._qty_rects = {}
        widgets.draw_text(surf, _L("Quantité :", "Quantity:"), (inner.x, y + 3), fonts.tiny(bold=True),
                          config.COL_TEXT_DIM)
        self._chip_row(surf, [(q, str(q)) for q in REPO_QTYS], self.repo_qty,
                       inner.x + 70, y, config.COL_CYAN, self._qty_rects)
        y += 28
        dv = (REPO.quote(self.market, self.repo_bond, self.repo_qty)
              if self.repo_bond else None)
        self._open_btn = None
        if dv:
            lines = [
                (_L(f"Valeur {widgets.format_money(dv['value'], cur)} · haircut "
                 f"{dv['haircut'] * 100:.1f}% → marge cash "
                 f"{widgets.format_money(dv['margin'], cur)}",
                 f"Value {widgets.format_money(dv['value'], cur)} · haircut "
                 f"{dv['haircut'] * 100:.1f}% → cash margin "
                 f"{widgets.format_money(dv['margin'], cur)}"), config.COL_TEXT),
                (_L(f"Emprunt {widgets.format_money(dv['borrowed'], cur)} au taux repo "
                 f"{dv['rate'] * 100:.2f}%/an (roulé chaque pas)",
                 f"Borrow {widgets.format_money(dv['borrowed'], cur)} at repo rate "
                 f"{dv['rate'] * 100:.2f}%/yr (rolled each step)"), config.COL_TEXT_DIM),
                (_L(f"CARRY DE L'EQUITY ≈ {dv['equity_carry'] * 100:+.1f}%/an "
                 f"(levier ×{dv['value'] / dv['margin']:.1f})",
                 f"EQUITY CARRY ≈ {dv['equity_carry'] * 100:+.1f}%/yr "
                 f"(leverage ×{dv['value'] / dv['margin']:.1f})"), config.COL_AMBER),
            ]
            for txt, col in lines:
                widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.w),
                                  (inner.x, y), fonts.tiny(), col)
                y += 16
            # la phrase concrète (core/impact_phrases) : ce que le repo
            # immobilise, libère, et coûte PAR TOUR
            from core import impact_phrases as _ip
            phrase = _ip.repo_impact(dv["value"], dv["borrowed"], dv["rate"])
            widgets.draw_text(surf, widgets.fit_text(phrase, fonts.tiny(), inner.w),
                              (inner.x, y), fonts.tiny(), config.COL_WARN)
            y += 20
            self._open_btn = pygame.Rect(inner.x, y, 200, 26)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._open_btn,
                             border_radius=4)
            pygame.draw.rect(surf, config.COL_UP, self._open_btn, 1, border_radius=4)
            widgets.draw_text(surf, _L("METTRE EN PENSION", "OPEN REPO"), self._open_btn.center,
                              fonts.small(bold=True), config.COL_UP, align="center")
        repo_hint = _L("En crise, haircut ET taux repo montent — l'appel de "
                    "marge liquide au pire moment (LTCM, 2008).",
                    "In a crisis, both haircut AND repo rate rise — the margin "
                    "call liquidates at the worst moment (LTCM, 2008).")
        repo_font = fonts.tiny()
        repo_lines = len(widgets.wrap_text_lines(repo_hint, repo_font, inner.w))
        repo_h = repo_lines * (repo_font.get_height() + 3)
        widgets.draw_text_wrapped(surf, repo_hint, (inner.x, inner.bottom - repo_h),
                                  repo_font, config.COL_TEXT_DIM, inner.w, line_gap=3)
        # positions en cours
        rinner = widgets.draw_panel(surf, right, _L("Pensions en cours", "Active repos"), config.COL_AMBER)
        self._close_rects = {}
        hh = REPO.holdings(self.app.gs.player, self.market)
        if not hh:
            widgets.draw_text(surf, _L("Aucune.", "None."), (rinner.x, rinner.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        y = rinner.y + 2
        for h in hh:
            if y > rinner.bottom - 40:
                break
            ecol = config.COL_DOWN if h["in_call"] else (
                config.COL_UP if h["pnl"] >= 0 else config.COL_AMBER)
            widgets.draw_text(surf, widgets.fit_text(
                f"{h['qty']} × {h['name']}", fonts.small(bold=True), rinner.w - 60),
                (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, _L(f"equity {widgets.format_money(h['equity'], cur)} "
                              f"(maint. {widgets.format_money(h['maintenance'], cur)}) "
                              f"· P&L {h['pnl']:+,.0f}",
                              f"equity {widgets.format_money(h['equity'], cur)} "
                              f"(maint. {widgets.format_money(h['maintenance'], cur)}) "
                              f"· P&L {h['pnl']:+,.0f}"),
                              (rinner.x + 8, y + 16), fonts.tiny(), ecol)
            xr = pygame.Rect(rinner.right - 22, y, 18, 18)
            self._close_rects[h["id"]] = xr
            pygame.draw.rect(surf, config.COL_PANEL, xr, border_radius=3)
            widgets.draw_text(surf, "×", xr.center, fonts.small(bold=True),
                              config.COL_DOWN, align="center")
            y += 36

    # --------------------------------------------------------------- lending
    def _draw_lending(self, surf, body):
        cur = self._cur()
        p = self.app.gs.player
        inner = widgets.draw_panel(surf, body,
                                   _L("Prêt-emprunt de titres (le short se paie)", "Securities lending (the short is paid for)"),
                                   config.COL_CYAN)
        on = bool(p.flags.get("sec_lending"))
        lend_label = ("[x] " if on else "[ ] ") + _L("PRÊTER MES TITRES ", "LEND MY SECURITIES ") \
            + _L(f"(part prêteur {SL.LENDER_SPLIT * 100:.0f}%)", f"(lender share {SL.LENDER_SPLIT * 100:.0f}%)")
        lend_font = fonts.tiny(bold=on)
        lend_w = lend_font.size(lend_label)[0] + 16
        self._lend_toggle = pygame.Rect(inner.x, inner.y, lend_w, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if on else config.COL_PANEL,
                         self._lend_toggle, border_radius=3)
        pygame.draw.rect(surf, config.COL_UP if on else config.COL_BORDER,
                         self._lend_toggle, 1, border_radius=3)
        widgets.draw_text(surf, lend_label,
                          (self._lend_toggle.x + 8, self._lend_toggle.y + 5),
                          lend_font, config.COL_UP if on else config.COL_TEXT_DIM)
        y = inner.y + 32
        rows = SL.table(p, self.market)
        if not rows:
            widgets.draw_text(surf, _L("Aucune position action — les frais d'emprunt "
                              "des shorts et le revenu de prêt vivent ici.",
                              "No equity positions — the borrow fees "
                              "of shorts and the lending income live here."),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        cols = [(_L("POSITION", "POSITION"), 0), (_L("VALEUR", "VALUE"), int(inner.w * 0.30)),
                (_L("TAUX", "RATE"), int(inner.w * 0.52)), (_L("FLUX ANNUEL", "ANNUAL FLOW"), int(inner.w * 0.72))]
        for lbl, dx in cols:
            widgets.draw_text(surf, lbl, (inner.x + dx, y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        y += 16
        total = 0.0
        for row in rows:
            if y > inner.bottom - 30:
                break
            total += row["annual"]
            side = "SHORT" if row["side"] == "short" else "long"
            scol = config.COL_DOWN if row["side"] == "short" else config.COL_TEXT
            widgets.draw_text(surf, f"{side} {row['ticker']}", (inner.x, y),
                              fonts.small(bold=True), scol)
            widgets.draw_text(surf, widgets.format_money(row["value"], cur),
                              (inner.x + cols[1][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            rcol = config.COL_UP if row["rate"] > 0 else (
                config.COL_DOWN if row["rate"] < 0 else config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{row['rate'] * 100:+.2f}%/an",
                              (inner.x + cols[2][1], y), fonts.small(), rcol)
            widgets.draw_text(surf, widgets.format_money(row["annual"], cur),
                              (inner.x + cols[3][1], y), fonts.small(bold=True), rcol)
            y += 19
        y += 8
        tcol = config.COL_UP if total >= 0 else config.COL_DOWN
        widgets.draw_text(surf, _L(f"FLUX NET ≈ {widgets.format_money(total, cur)}/an "
                          "(couru à chaque pas)",
                          f"NET FLOW ≈ {widgets.format_money(total, cur)}/yr "
                          "(accrued each step)"), (inner.x, y),
                          fonts.small(bold=True), tcol)
        htb_hint = _L("Petite capi = « hard to borrow » : rare au prêt, chère "
                   "à shorter — et tout s'élargit en crise.",
                   "Small cap = 'hard to borrow': scarce to lend, expensive "
                   "to short — and everything widens in a crisis.")
        htb_font = fonts.tiny()
        htb_lines = len(widgets.wrap_text_lines(htb_hint, htb_font, inner.w))
        htb_h = htb_lines * (htb_font.get_height() + 3)
        widgets.draw_text_wrapped(surf, htb_hint, (inner.x, inner.bottom - htb_h),
                                  htb_font, config.COL_TEXT_DIM, inner.w, line_gap=3)

    # ------------------------------------------------------------------ cash
    def _draw_cash(self, surf, body):
        cur = self._cur()
        p = self.app.gs.player
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        inner = widgets.draw_panel(surf, left, _L("Placer la trésorerie", "Invest the cash"),
                                   config.COL_CYAN)
        y = inner.y + 2
        on = bool(p.flags.get("mm_sweep"))
        sweep_label = ("[x] " if on else "[ ] ") + _L("SWEEP AU JOUR LE JOUR ", "OVERNIGHT SWEEP ") \
            + _L(f"({MM.sweep_rate(self.market) * 100:.2f}%/an, liquide)", f"({MM.sweep_rate(self.market) * 100:.2f}%/yr, liquid)")
        sweep_font = fonts.tiny(bold=on)
        sweep_w = sweep_font.size(sweep_label)[0] + 16
        self._sweep_toggle = pygame.Rect(inner.x, y, sweep_w, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if on else config.COL_PANEL,
                         self._sweep_toggle, border_radius=3)
        pygame.draw.rect(surf, config.COL_UP if on else config.COL_BORDER,
                         self._sweep_toggle, 1, border_radius=3)
        widgets.draw_text(surf, sweep_label,
                          (self._sweep_toggle.x + 8, self._sweep_toggle.y + 5),
                          sweep_font, config.COL_UP if on else config.COL_TEXT_DIM)
        y += 30
        widgets.draw_text(surf, _L(f"(cash balayé au-delà du coussin de "
                          f"{widgets.format_money(MM.SWEEP_BUFFER, cur)})",
                          f"(cash swept above the buffer of "
                          f"{widgets.format_money(MM.SWEEP_BUFFER, cur)})"),
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 24
        widgets.draw_text(surf, _L("Dépôt à terme (bloqué, mieux payé) :", "Term deposit (locked, better paid):"),
                          (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 18
        self._amount_rects = {}
        self._chip_row(surf, [(v, widgets.format_money(v, cur))
                              for v in DEPOSIT_AMOUNTS],
                       self.dep_amount, inner.x, y, config.COL_CYAN,
                       self._amount_rects)
        y += 26
        self._term_rects = {}
        self._chip_row(surf, [(t, _L(f"{t} pas — {MM.deposit_rate(self.market, t) * 100:.2f}%", f"{t} steps — {MM.deposit_rate(self.market, t) * 100:.2f}%"))
                              for t in MM.TERM_STEPS],
                       self.dep_term, inner.x, y, config.COL_AMBER, self._term_rects)
        y += 30
        self._dep_btn = pygame.Rect(inner.x, y, 200, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._dep_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._dep_btn, 1, border_radius=4)
        widgets.draw_text(surf, _L("OUVRIR LE DÉPÔT", "OPEN THE DEPOSIT"), self._dep_btn.center,
                          fonts.small(bold=True), config.COL_UP, align="center")
        liq_hint = _L("La liquidité a un prix : le terme paie plus que le jour "
                   "le jour — mais bloque.",
                   "Liquidity has a price: term pays more than overnight "
                   "— but locks up.")
        liq_font = fonts.tiny()
        liq_lines = len(widgets.wrap_text_lines(liq_hint, liq_font, inner.w))
        liq_h = liq_lines * (liq_font.get_height() + 3)
        widgets.draw_text_wrapped(surf, liq_hint, (inner.x, inner.bottom - liq_h),
                                  liq_font, config.COL_TEXT_DIM, inner.w, line_gap=3)
        rinner = widgets.draw_panel(surf, right, _L("Dépôts en cours", "Active deposits"), config.COL_AMBER)
        hh = MM.holdings(p, self.market)
        if not hh:
            widgets.draw_text(surf, _L("Aucun.", "None."), (rinner.x, rinner.y + 4), fonts.tiny(),
                              config.COL_TEXT_DIM)
        y = rinner.y + 2
        for d in hh:
            if y > rinner.bottom - 36:
                break
            widgets.draw_text(surf, f"{widgets.format_money(d['amount'], cur)} à "
                              f"{d['rate'] * 100:.2f}%",
                              (rinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, _L(f"échéance dans {d['steps_left']} pas · intérêts "
                              f"attendus {widgets.format_money(d['expected_interest'], cur)}",
                              f"maturity in {d['steps_left']} steps · expected "
                              f"interest {widgets.format_money(d['expected_interest'], cur)}"),
                              (rinner.x + 8, y + 16), fonts.tiny(),
                              config.COL_TEXT_DIM)
            y += 34
