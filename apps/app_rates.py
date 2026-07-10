"""
app_rates.py — Application « Desk Taux » du bureau (NATIVE).

Fixed income de salle des marchés, sur l'univers obligataire RÉEL du jeu
(core/bonds.py) via core/rates_analytics.py :

- **Courbe des taux** souveraine (YTM par maturité) — celle que déforment
  le taux directeur et la prime de terme du moteur macro ;
- **Book obligataire** du joueur : duration modifiée, convexité et DV01
  par ligne + agrégats pondérés — le DV01 (P&L d'1 point de base) est
  l'unité de compte d'un desk de taux ;
- **Chocs de courbe** : P&L du book au 2e ordre (duration + convexité)
  sous des scénarios parallèles ET non parallèles (pentification /
  aplatissement) — deux books de même duration n'y réagissent pas pareil.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import rates_analytics as RT
from ui import fonts, widgets


class RatesApp(DesktopApp):
    title = "Desk Taux"
    icon_kind = "rates"
    default_size = (1060, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.tab = "rates"                    # "rates" | "futures" | "immun"
        self.liability = 500_000.0
        self.horizon = 5
        self._liab_rects = {}
        self._horizon_rects = {}
        self._immun_btn = None
        self._hedge_swap_btn = None
        self._swap_close_rects = {}
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self._cache_key = None
        self._curve = None
        self._forwards = []
        self._table = None
        self._bonds_btn = None
        self._tab_rects = {}
        self._shorten_btn = None
        self._lengthen_btn = None

    def _ensure_computed(self):
        p = self.app.gs.player
        key = (self.market.step_count, len(getattr(p, "bonds", {}) or {}))
        if key == self._cache_key:
            return
        self._cache_key = key
        self._curve = RT.yield_curve(self.market)
        self._forwards = RT.forward_rates(self._curve)
        self._table = RT.scenario_table(p, self.market)

    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for tab, r in self._tab_rects.items():
            if r.collidepoint(pos):
                self.tab = tab
                return True
        if self._bonds_btn and self._bonds_btn.collidepoint(pos):
            if self.desktop is not None:
                self.desktop._open_scene_window("bonds")
            return True
        for direction, btn in (("shorten", self._shorten_btn),
                               ("lengthen", self._lengthen_btn)):
            if btn and btn.collidepoint(pos):
                self._rotate(direction)
                return True
        for v, r in self._liab_rects.items():
            if r.collidepoint(pos):
                self.liability = v
                return True
        for h, r in self._horizon_rects.items():
            if r.collidepoint(pos):
                self.horizon = h
                return True
        if self._hedge_swap_btn and self._hedge_swap_btn.collidepoint(pos):
            from core import irs as IRS
            p = self.app.gs.player
            dv01 = IRS.portfolio_dv01(p, self.market)
            if dv01 <= 1e-9:
                self.msg, self.msg_col = ("DV01 net déjà nul ou négatif — rien "
                                          "à couvrir.", config.COL_TEXT_DIM)
            else:
                notional = IRS.hedge_notional(dv01, years=5.0)
                r = IRS.enter_swap(p, self.market, "payer", notional, 5.0)
                if r.get("ok"):
                    self.msg = (f"Swap payeur 5 ans, notionnel "
                                f"{notional:,.0f} — le DV01 du book est "
                                "neutralisé sans vendre une obligation.")
                    self.msg_col = config.COL_UP
                    self._cache_key = None
                else:
                    self.msg, self.msg_col = (f"Refusé : {r.get('reason', '?')}.",
                                              config.COL_DOWN)
            return True
        for pid, r in self._swap_close_rects.items():
            if r.collidepoint(pos):
                from core import irs as IRS
                res = IRS.close(self.app.gs.player, self.market, pid)
                if res.get("ok"):
                    self.msg = f"Swap dénoué — MTM {res['mtm']:+,.0f}."
                    self.msg_col = (config.COL_UP if res["mtm"] >= 0
                                    else config.COL_DOWN)
                return True
        if self._immun_btn and self._immun_btn.collidepoint(pos):
            plan = RT.immunize_plan(self.app.gs.player, self.market,
                                    self.liability, self.horizon)
            if plan is None:
                self.msg, self.msg_col = ("Univers insuffisant pour encadrer "
                                          "cet horizon.", config.COL_DOWN)
            else:
                r = RT.execute_immunization(self.app.gs.player, self.market, plan)
                if r.get("ok"):
                    self.msg = (f"Barbell immunisant acheté : "
                                f"{plan['short']['qty']} × {plan['short']['name']} + "
                                f"{plan['long']['qty']} × {plan['long']['name']}")
                    self.msg_col = config.COL_UP
                    self._cache_key = None
                else:
                    self.msg, self.msg_col = (f"Refusé : {r.get('reason', '?')}.",
                                              config.COL_DOWN)
            return True
        return False

    def _rotate(self, direction):
        p = self.app.gs.player
        plan = RT.dv01_rotation_plan(p, self.market, direction)
        if plan is None:
            self.msg, self.msg_col = ("Rien à tourner (book vide ou déjà à "
                                      "l'extrême).", config.COL_TEXT_DIM)
            return
        r = RT.execute_rotation(p, self.market, plan)
        if r.get("ok"):
            self.msg = (f"Rotation : vendu {plan['sell']['qty']} × "
                        f"{plan['sell']['name']} → acheté {plan['buy']['qty']} × "
                        f"{plan['buy']['name']} (DV01 apparié)")
            self.msg_col = config.COL_UP
            self._cache_key = None
        else:
            self.msg, self.msg_col = (f"Refusé : {r.get('reason', '?')} "
                                      f"(jambe {r.get('leg', '?')}).",
                                      config.COL_DOWN)

    def draw(self, surf, rect):
        self._ensure_computed()
        self._shorten_btn = self._lengthen_btn = None
        surf.fill(config.COL_BG, rect)
        pad = 14
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        widgets.draw_text(surf, "DESK TAUX — COURBE · DURATION · DV01 · CHOCS",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        bw = fonts.tiny(bold=True).size("MARCHÉ OBLIGATAIRE →")[0] + 16
        self._bonds_btn = pygame.Rect(rect.right - pad - bw, rect.y + 10, bw, 20)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._bonds_btn, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, self._bonds_btn, 1, border_radius=3)
        widgets.draw_text(surf, "MARCHÉ OBLIGATAIRE →", self._bonds_btn.center,
                          fonts.tiny(bold=True), config.COL_CYAN, align="center")
        # onglets TAUX / FUTURES
        x, ty = rect.x + pad, rect.y + 36
        self._tab_rects = {}
        for tab, lbl in (("rates", "TAUX"), ("futures", "FUTURES (commodities)"),
                         ("immun", "IMMUNISATION"), ("swaps", "SWAPS (IRS)")):
            w = fonts.tiny(bold=True).size(lbl)[0] + 18
            r = pygame.Rect(x, ty, w, 20)
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
                              (x + 6, ty + 4), fonts.tiny(), self.msg_col)
        body = pygame.Rect(rect.x + pad, ty + 26, rect.w - 2 * pad,
                           rect.bottom - pad - ty - 26)
        if self.tab == "futures":
            self._draw_futures(surf, body, cur)
            return
        if self.tab == "immun":
            self._draw_immunization(surf, body, cur)
            return
        if self.tab == "swaps":
            self._draw_swaps(surf, body, cur)
            return
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        h_half = (left.h - 10) // 2
        self._draw_curve(surf, pygame.Rect(left.x, left.y, left.w, h_half))
        self._draw_scenarios(surf, pygame.Rect(left.x, left.y + h_half + 10,
                                               left.w, h_half), cur)
        self._draw_book(surf, right, cur)

    def _draw_curve(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Courbe des taux (souverains, YTM)",
                                   config.COL_CYAN)
        pts = self._curve or []
        if len(pts) < 2:
            widgets.draw_text(surf, "Pas assez de points de courbe.",
                              (inner.x, inner.y + 6), fonts.tiny(),
                              config.COL_TEXT_DIM)
            return
        years = [y for y, _ in pts]
        ytms = [v * 100 for _, v in pts]
        lo, hi = min(ytms), max(ytms)
        rng = (hi - lo) or 1.0
        plot = inner.inflate(-30, -26)
        plot.move_ip(10, 2)
        plot.height -= 16  # réserve la place sous l'axe X pour l'étiquette + le résumé
        pygame.draw.line(surf, config.COL_BORDER, plot.bottomleft, plot.bottomright)
        pygame.draw.line(surf, config.COL_BORDER, plot.topleft, plot.bottomleft)
        xmax = max(years)
        px_pts = []
        for yy, v in zip(years, ytms):
            x0 = plot.x + int(yy / xmax * plot.w)
            y0 = plot.bottom - int((v - lo) / rng * plot.h)
            px_pts.append((x0, y0))
        if len(px_pts) >= 2:
            pygame.draw.aalines(surf, config.COL_CYAN, False, px_pts)
        for (x0, y0), yy, v in zip(px_pts, years, ytms):
            pygame.draw.circle(surf, config.COL_WHITE, (x0, y0), 3)
            widgets.draw_text(surf, f"{yy:.0f}a", (x0 - 6, plot.bottom + 3),
                              fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{hi:.1f}%", (plot.x - 34, plot.y - 4),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{lo:.1f}%", (plot.x - 34, plot.bottom - 10),
                          fonts.tiny(), config.COL_TEXT_DIM)
        shape = "pentue" if ytms[-1] > ytms[0] + 0.15 else \
                ("INVERSÉE (signal récession)" if ytms[-1] < ytms[0] - 0.15
                 else "plate")
        fwd_txt = " · ".join(f"{t1:.0f}→{t2:.0f}a {f * 100:.1f}%"
                             for t1, t2, f in self._forwards[:3])
        widgets.draw_text(surf, widgets.fit_text(
            f"Courbe {shape} · forwards implicites : {fwd_txt}", fonts.tiny(), inner.w),
            (inner.x, plot.bottom + 16), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_scenarios(self, surf, rect, cur):
        inner = widgets.draw_panel(surf, rect,
                                   "Chocs de courbe (duration + convexité)",
                                   config.COL_DOWN)
        t = self._table
        if not t or not t["lines"]:
            widgets.draw_text(surf, "Book obligataire vide.", (inner.x, inner.y + 6),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        y = inner.y + 2
        pmax = max(abs(s["pnl"]) for s in t["scenarios"]) or 1.0
        bar_w = inner.w - 260
        for s in t["scenarios"]:
            if y > inner.bottom - 16:
                break
            widgets.draw_text(surf, widgets.fit_text(s["name"], fonts.tiny(bold=True),
                                                     150),
                              (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT)
            bx = inner.x + 155
            mid = bx + bar_w // 2
            frac = s["pnl"] / pmax
            w = int(abs(frac) * bar_w * 0.5)
            col = config.COL_UP if s["pnl"] >= 0 else config.COL_DOWN
            pygame.draw.line(surf, config.COL_BORDER, (mid, y), (mid, y + 12))
            pygame.draw.rect(surf, col,
                             pygame.Rect(mid if frac >= 0 else mid - w, y + 2, w, 10),
                             border_radius=2)
            widgets.draw_text(surf, f"{widgets.format_money(s['pnl'], cur)} "
                              f"({s['pnl_pct']:+.1f}%)",
                              (bx + bar_w + 6, y), fonts.tiny(), col)
            y += 19
        widgets.draw_text(surf, "ΔP ≈ V·(−D·Δy + ½·C·Δy²) — la convexité adoucit "
                          "les hausses de taux.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _draw_book(self, surf, rect, cur):
        inner = widgets.draw_panel(surf, rect, "Book obligataire", config.COL_AMBER)
        t = self._table
        if not t or not t["lines"]:
            widgets.draw_text(surf, "Aucune obligation détenue — le desk Taux "
                              "s'anime avec un book (bouton MARCHÉ OBLIGATAIRE).",
                              (inner.x, inner.y + 6), fonts.tiny(),
                              config.COL_TEXT_DIM)
            return
        tot = t["totals"]
        tiles = [
            ("VALEUR", widgets.format_money(tot["value"], cur)),
            ("DURATION MOD.", f"{tot['duration']:.2f}"),
            ("CONVEXITÉ", f"{tot['convexity']:.1f}"),
            ("DV01", widgets.format_money(tot["dv01"], cur)),
        ]
        tx = inner.x
        for lbl, val in tiles:
            tw = max(120, fonts.small(bold=True).size(val)[0] + 18)
            if tx + tw > inner.right:
                break
            tr = pygame.Rect(tx, inner.y, tw, 42)
            pygame.draw.rect(surf, config.COL_PANEL, tr, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, tr, 1, border_radius=4)
            widgets.draw_text(surf, lbl, (tr.x + 7, tr.y + 4), fonts.tiny(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (tr.x + 7, tr.y + 19),
                              fonts.small(bold=True), config.COL_TEXT)
            tx += tw + 8
        y = inner.y + 52
        cols = [("OBLIGATION", 0), ("MAT.", int(inner.w * 0.42)),
                ("YTM", int(inner.w * 0.52)), ("DUR.", int(inner.w * 0.64)),
                ("CONV.", int(inner.w * 0.75)), ("DV01", int(inner.w * 0.87))]
        for lbl, dx in cols:
            widgets.draw_text(surf, lbl, (inner.x + dx, y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        y += 16
        for x in t["lines"]:
            if y > inner.bottom - 28:
                widgets.draw_text(surf, "…", (inner.x, y), fonts.tiny(),
                                  config.COL_TEXT_DIM)
                break
            widgets.draw_text(surf, widgets.fit_text(x["name"], fonts.small(bold=True),
                                                     int(inner.w * 0.40)),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{x['years']:.0f}a",
                              (inner.x + cols[1][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{x['ytm'] * 100:.2f}%",
                              (inner.x + cols[2][1], y), fonts.small(),
                              config.COL_CYAN)
            widgets.draw_text(surf, f"{x['duration']:.2f}",
                              (inner.x + cols[3][1], y), fonts.small(),
                              config.COL_TEXT)
            widgets.draw_text(surf, f"{x['convexity']:.0f}",
                              (inner.x + cols[4][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, widgets.format_money(x["dv01"], cur),
                              (inner.x + cols[5][1], y), fonts.small(),
                              config.COL_AMBER)
            y += 18
        # rotation de courbe DV01-neutre (le jeu ne shorte pas d'obligation :
        # on fait TOURNER le book, risque de taux déplacé identique des deux
        # côtés — cf. rates_analytics.dv01_rotation_plan)
        dv01_hint = ("DV01 = P&L d'une hausse d'1 point de base — rotation "
                    "court↔long à DV01 apparié.")
        dv01_font = fonts.tiny()
        dv01_lines = len(widgets.wrap_text_lines(dv01_hint, dv01_font, inner.w))
        dv01_h = dv01_lines * (dv01_font.get_height() + 3)
        by = inner.bottom - dv01_h - 30
        self._shorten_btn = pygame.Rect(inner.x, by, 150, 24)
        self._lengthen_btn = pygame.Rect(inner.x + 158, by, 150, 24)
        for r, lbl in ((self._shorten_btn, "↤ RACCOURCIR"),
                       (self._lengthen_btn, "ALLONGER ↦")):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER, r, 1, border_radius=4)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER, align="center")
        widgets.draw_text_wrapped(surf, dv01_hint, (inner.x, inner.bottom - dv01_h),
                                  dv01_font, config.COL_TEXT_DIM, inner.w, line_gap=3)

    def _draw_immunization(self, surf, body, cur):
        """Immunisation classique : financer un passif futur avec un barbell
        obligataire dont la DURATION égale l'horizon — au 1er ordre, le choc
        de taux ne perce pas la couverture (rates_analytics.immunize_plan)."""
        inner = widgets.draw_panel(surf, body,
                                   "Immuniser un passif (duration matching)",
                                   config.COL_CYAN)
        y = inner.y + 2
        widgets.draw_text(surf, "Passif à financer :", (inner.x, y + 3),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        x = inner.x + 120
        self._liab_rects = {}
        for v in (250_000.0, 500_000.0, 1_000_000.0):
            lbl = widgets.format_money(v, cur)
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            self._liab_rects[v] = r
            sel = abs(v - self.liability) < 1e-9
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        x += 14
        widgets.draw_text(surf, "Horizon :", (x, y + 3), fonts.tiny(bold=True),
                          config.COL_TEXT_DIM)
        x += 62
        self._horizon_rects = {}
        for h in (3, 5, 7):
            lbl = f"{h} ans"
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            self._horizon_rects[h] = r
            sel = h == self.horizon
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        y += 32
        plan = RT.immunize_plan(self.app.gs.player, self.market,
                                self.liability, self.horizon)
        if plan is None:
            widgets.draw_text(surf, "L'univers souverain n'encadre pas cet horizon.",
                              (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
            self._immun_btn = None
            return
        widgets.draw_text(surf, f"Valeur actuelle du passif : "
                          f"{widgets.format_money(plan['pv'], cur)} "
                          f"(actualisé à {plan['y_h'] * 100:.2f}%)",
                          (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
        y += 22
        for leg, lbl in ((plan["short"], "Jambe courte"),
                         (plan["long"], "Jambe longue")):
            widgets.draw_text(surf, f"{lbl} : {leg['qty']} × {leg['name']} "
                              f"(poids {leg['weight'] * 100:.0f}%, duration "
                              f"{leg['dur']:.2f})",
                              (inner.x, y), fonts.small(), config.COL_TEXT)
            y += 19
        y += 4
        widgets.draw_text(surf, f"Duration du barbell = {plan['dur_target']:.1f} "
                          "= l'horizon — c'est l'immunisation.",
                          (inner.x, y), fonts.tiny(bold=True), config.COL_AMBER)
        y += 20
        chk = RT.immunization_check(plan, dy=0.01)
        widgets.draw_text(surf, f"Vérif +100 bp : actifs "
                          f"{widgets.format_money(chk['d_assets'], cur)} vs passif "
                          f"{widgets.format_money(chk['d_liability'], cur)} → écart "
                          f"{widgets.format_money(chk['mismatch'], cur)}",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 26
        self._immun_btn = pygame.Rect(inner.x, y, 220, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._immun_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._immun_btn, 1, border_radius=4)
        widgets.draw_text(surf, "ACHETER LE BARBELL", self._immun_btn.center,
                          fonts.small(bold=True), config.COL_UP, align="center")
        widgets.draw_text(surf, "Le prix perd ce que le réinvestissement gagne "
                          "(et réciproquement) — le passif reste financé.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _draw_swaps(self, surf, body, cur):
        """Swaps de taux (core/irs.py) : le payeur de fixe a un DV01 négatif
        — LA couverture du book obligataire sans le vendre. Flux net réglé
        chaque pas, MTM à la sortie."""
        from core import irs as IRS
        p = self.app.gs.player
        inner = widgets.draw_panel(surf, body,
                                   "Swaps de taux — couvrir le DV01 sans vendre",
                                   config.COL_CYAN)
        y = inner.y + 2
        book_dv01 = RT.book_totals(RT.book_lines(p, self.market))["dv01"]
        net = IRS.portfolio_dv01(p, self.market)
        ncol = (config.COL_UP if abs(net) < abs(book_dv01) * 0.2 + 1e-9
                else config.COL_AMBER)
        widgets.draw_text(surf, f"DV01 du book obligataire : "
                          f"{widgets.format_money(book_dv01, cur)} · DV01 NET "
                          f"(book + swaps) : {widgets.format_money(net, cur)}",
                          (inner.x, y), fonts.small(bold=True), ncol)
        y += 22
        widgets.draw_text(surf, f"Taux fixe 5 ans « à la monnaie » : "
                          f"{IRS.par_rate(self.market, 5.0) * 100:.2f}% — le "
                          "payeur gagne si les taux montent.",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 22
        self._hedge_swap_btn = pygame.Rect(inner.x, y, 260, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._hedge_swap_btn,
                         border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._hedge_swap_btn, 1,
                         border_radius=4)
        widgets.draw_text(surf, "COUVRIR LE DV01 (swap payeur 5a)",
                          self._hedge_swap_btn.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
        y += 36
        widgets.draw_text(surf, "SWAPS EN COURS :", (inner.x, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 16
        self._swap_close_rects = {}
        hh = IRS.holdings(p, self.market)
        if not hh:
            widgets.draw_text(surf, "Aucun.", (inner.x, y), fonts.tiny(),
                              config.COL_TEXT_DIM)
        for h in hh:
            if y > inner.bottom - 36:
                break
            mcol = config.COL_UP if h["mtm"] >= 0 else config.COL_DOWN
            lbl = "PAYEUR" if h["direction"] == "payer" else "RECEVEUR"
            widgets.draw_text(surf, f"{lbl} fixe {h['fixed_rate'] * 100:.2f}% · "
                              f"notionnel {h['notional']:,.0f} · "
                              f"{h['steps_left']} pas",
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"MTM {h['mtm']:+,.0f} · DV01 "
                              f"{widgets.format_money(h['dv01'], cur)}",
                              (inner.x + 8, y + 16), fonts.tiny(), mcol)
            xr = pygame.Rect(inner.right - 22, y, 18, 18)
            self._swap_close_rects[h["id"]] = xr
            pygame.draw.rect(surf, config.COL_PANEL, xr, border_radius=3)
            widgets.draw_text(surf, "×", xr.center, fonts.small(bold=True),
                              config.COL_DOWN, align="center")
            y += 36
        widgets.draw_text(surf, "Aucun cash à l'entrée : le flux net "
                          "(variable − fixe) est réglé à chaque pas.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _draw_futures(self, surf, body, cur):
        """Courbes de futures des commodities : contango / backwardation et
        roll yield — pourquoi détenir un future pétrole PERD de l'argent en
        contango même si le spot ne bouge pas (le roll)."""
        from core import commodities as C
        inner = widgets.draw_panel(surf, body,
                                   "Structures par terme (contango / backwardation)",
                                   config.COL_WARN)
        widgets.draw_text(surf, "Courbe MONTANTE (contango) : rouler le future "
                          "coûte à chaque échéance (roll yield négatif) ; courbe "
                          "DESCENDANTE (backwardation) : le roll rapporte.",
                          (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        quotes = C.all_quotes(self.market)
        if not quotes:
            return
        cols = 3
        cell_w = (inner.w - (cols - 1) * 10) // cols
        cell_h = 96
        x0, y0 = inner.x, inner.y + 22
        for i, q in enumerate(quotes[:9]):
            cx = x0 + (i % cols) * (cell_w + 10)
            cy = y0 + (i // cols) * (cell_h + 8)
            if cy + cell_h > inner.bottom:
                break
            cell = pygame.Rect(cx, cy, cell_w, cell_h)
            pygame.draw.rect(surf, config.COL_PANEL, cell, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, cell, 1, border_radius=4)
            pts_curve = C.curve(self.market, q["id"])
            ry = q["roll_yield"]
            rcol = config.COL_DOWN if ry < 0 else config.COL_UP
            widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.tiny(bold=True),
                                                     cell_w - 16),
                              (cell.x + 8, cell.y + 5), fonts.tiny(bold=True),
                              config.COL_TEXT)
            widgets.draw_text(surf, f"{q['structure']} · roll {ry * 100:+.1f}%/an",
                              (cell.x + 8, cell.y + 19), fonts.tiny(), rcol)
            if len(pts_curve) >= 2:
                vals = [v for _m, v in pts_curve]
                lo, hi = min(vals), max(vals)
                rng = (hi - lo) or 1.0
                plot = pygame.Rect(cell.x + 8, cell.y + 36, cell_w - 16,
                                   cell_h - 46)
                pts = []
                for j, (_mn, v) in enumerate(pts_curve):
                    px = plot.x + int(j / (len(pts_curve) - 1) * plot.w)
                    py = plot.bottom - int((v - lo) / rng * plot.h)
                    pts.append((px, py))
                pygame.draw.aalines(surf, rcol, False, pts)
                for pt in pts:
                    pygame.draw.circle(surf, config.COL_WHITE, pt, 2)
