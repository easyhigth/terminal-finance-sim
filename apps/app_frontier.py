"""
app_frontier.py — Application « Frontière efficiente » du bureau (NATIVE,
INTERACTIVE) — remplace le laboratoire en lecture seule (scene_frontier_lab).

La différence fondamentale avec le labo : ici la courbe SE TRADE. Chaque
point de la frontière (core/quant_tools.frontier, qui garde les POIDS
optimaux de chaque point — finmath.efficient_frontier) est cliquable :

1. Cochez l'univers (positions détenues ✶ + candidates peu corrélées
   suggérées par core/analytics.diversification_candidates) ;
2. Cliquez un point de la courbe (ou MAX SHARPE / MIN VAR, ou ←/→ pour
   glisser le long de la frontière) — le panneau cible affiche rendement/
   vol/Sharpe attendus, les poids cibles vs actuels, et la LISTE D'ORDRES
   exacte (vendre n × X, acheter m × Y) qui y mène ;
3. APPLIQUER exécute réellement les ordres (core/portfolio, ventes d'abord
   puis achats, frais/slippage réels du jeu), après confirmation modale.

Le budget du rééquilibrage = valeur longue actuelle de l'univers (auto-
financé) ; si le joueur ne détient rien, 80 % du cash. Une « projection
1 an » (quantiles analytiques lognormaux, déterministes) montre la
fourchette de valeur attendue au point choisi. La courbe et le point
ACTUEL sont recalculés à chaque pas de marché — la frontière est vivante,
on la regarde bouger et on agit dessus.
"""
import pygame

from apps.base import DesktopApp
from core import analytics, config
from core import portfolio as pf
from core import quant_tools as QT
from ui import fonts, widgets

ROW_H = 20
SNAP_PX = 14                     # rayon de capture d'un clic sur la courbe


class FrontierApp(DesktopApp):
    title = "Frontière efficiente"
    icon_kind = "frontier"
    default_size = (1140, 660)
    min_size = (860, 520)

    def on_open(self):
        self.market = self.app.ensure_market()
        p = self.app.gs.player
        held = [h["ticker"] for h in pf.holdings(p, self.market) if not h["short"]]
        cands = analytics.diversification_candidates(p, self.market, n=15)
        if not held and not cands:
            cands = [c["ticker"] for c in self.market.top_companies(n=10)]
        self.universe = list(dict.fromkeys(held + cands))
        self.selected = set(held) if len(held) >= 2 else set(self.universe[:5])
        self.target_idx = None
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self.scroll = 0
        self._max_scroll = 0
        self._cache_key = None
        self._fr = None
        self._trades = None
        self._confirm = False
        self._row_rects = {}
        self._universe_rect = None
        self._curve_px = []
        self._chart_plot = None
        self._maxsharpe_btn = None
        self._minvar_btn = None
        self._apply_btn = None
        self._yes_btn = None
        self._no_btn = None

    def refresh_data(self):
        self._cache_key = None

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        key = (self.market.step_count, frozenset(self.selected),
               len(self.app.gs.player.portfolio))
        if key == self._cache_key:
            return
        self._cache_key = key
        sel = [tk for tk in self.universe if tk in self.selected]
        self._fr = QT.frontier(self.market, sel, n_points=30)
        if self._fr and self.target_idx is not None:
            self.target_idx = min(self.target_idx, len(self._fr["vols"]) - 1)
        self._refresh_trades()

    def _refresh_trades(self):
        self._trades = None
        if self._fr is None or self.target_idx is None:
            return
        fr = self._fr
        w = fr["weights"][self.target_idx]
        self._trades = QT.target_trades(self.app.gs.player, self.market,
                                        fr["tickers"], w)

    def _set_target(self, idx):
        if self._fr is None:
            return
        self.target_idx = max(0, min(idx, len(self._fr["vols"]) - 1))
        self._refresh_trades()

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if self._confirm:
            return self._handle_confirm(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT and self.target_idx is not None:
                self._set_target(self.target_idx - 1)
                return True
            if event.key == pygame.K_RIGHT and self.target_idx is not None:
                self._set_target(self.target_idx + 1)
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._universe_rect and self._universe_rect.collidepoint(event.pos):
                delta = -ROW_H * 2 if event.button == 4 else ROW_H * 2
                self.scroll = max(0, min(self._max_scroll, self.scroll + delta))
                return True
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for tk, r in self._row_rects.items():
            if r.collidepoint(pos):
                if tk in self.selected:
                    if len(self.selected) > 2:
                        self.selected.discard(tk)
                else:
                    self.selected.add(tk)
                self.target_idx = None
                self._cache_key = None
                self.msg = ""
                return True
        if self._maxsharpe_btn and self._maxsharpe_btn.collidepoint(pos):
            if self._fr:
                self._set_target(self._fr["i_max_sharpe"])
            return True
        if self._minvar_btn and self._minvar_btn.collidepoint(pos):
            if self._fr:
                self._set_target(self._fr["i_min_var"])
            return True
        if self._apply_btn and self._apply_btn.collidepoint(pos):
            if self._trades and self._trades["trades"]:
                self._confirm = True
            return True
        # clic sur la courbe : point le plus proche dans le rayon de capture
        if self._chart_plot and self._chart_plot.collidepoint(pos) and self._curve_px:
            best, best_d2 = None, SNAP_PX ** 2
            for i, (px, py) in enumerate(self._curve_px):
                d2 = (px - pos[0]) ** 2 + (py - pos[1]) ** 2
                if d2 <= best_d2:
                    best, best_d2 = i, d2
            if best is not None:
                self._set_target(best)
                return True
        return False

    def _handle_confirm(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._confirm = False
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True
        if self._yes_btn and self._yes_btn.collidepoint(event.pos):
            self._confirm = False
            self._apply()
            return True
        if self._no_btn and self._no_btn.collidepoint(event.pos):
            self._confirm = False
            return True
        return True

    def _apply(self):
        trades = (self._trades or {}).get("trades", [])
        if not trades:
            return
        res = QT.apply_trades(self.app.gs.player, self.market, trades)
        if res["failed"]:
            details = ", ".join(f"{tk} ({reason})" for tk, reason in res["failed"][:3])
            self.msg = (f"{res['done']} ordre(s) exécuté(s), "
                        f"{len(res['failed'])} refusé(s) : {details}")
            self.msg_col = config.COL_AMBER
        else:
            self.msg = (f"{res['done']} ordre(s) exécuté(s) — le portefeuille "
                        "rejoint le point choisi de la frontière.")
            self.msg_col = config.COL_UP
        self._cache_key = None     # recalcul : le point ACTUEL a bougé

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 12
        widgets.draw_text(surf, "FRONTIÈRE EFFICIENTE — OPTIMISER PUIS EXÉCUTER",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(
            "Cochez l'univers · cliquez un point de la courbe (ou ←/→) · "
            "APPLIQUER passe les ordres réels.", fonts.tiny(), rect.w - 2 * pad),
            (rect.x + pad, rect.y + 30), fonts.tiny(), config.COL_TEXT_DIM)
        body = pygame.Rect(rect.x + pad, rect.y + 50, rect.w - 2 * pad,
                           rect.bottom - pad - rect.y - 50)
        uni_w = 210
        uni = pygame.Rect(body.x, body.y, uni_w, body.h)
        rest = pygame.Rect(uni.right + 10, body.y, body.w - uni_w - 10, body.h)
        chart_h = int(rest.h * 0.56)
        chart = pygame.Rect(rest.x, rest.y, rest.w, chart_h)
        target = pygame.Rect(rest.x, rest.y + chart_h + 8, rest.w,
                             rest.h - chart_h - 8)
        self._draw_universe(surf, uni)
        self._draw_chart(surf, chart)
        self._draw_target(surf, target)
        if self._confirm:
            self._draw_confirm(surf, rect)

    def _draw_universe(self, surf, rect):
        inner = widgets.draw_panel(surf, rect,
                                   f"Univers ({len(self.selected)} sél.)",
                                   config.COL_CYAN)
        self._row_rects = {}
        self._universe_rect = inner
        held = {h["ticker"] for h in pf.holdings(self.app.gs.player, self.market)
                if not h["short"]}
        # réserve la place du conseil « ✶ = détenue... » en bas AVANT de
        # calculer la zone de défilement des lignes (sinon la dernière ligne
        # visible peut se dessiner par-dessus ce texte, cf. capture tutoriel).
        univ_hint = "✶ = détenue · clic = inclure/exclure"
        univ_font = fonts.tiny()
        univ_lines = len(widgets.wrap_text_lines(univ_hint, univ_font, inner.w))
        univ_h = univ_lines * (univ_font.get_height() + 3)
        rows_area = pygame.Rect(inner.x, inner.y, inner.w, inner.h - univ_h - 4)
        prev_clip = surf.get_clip()
        surf.set_clip(rows_area)
        y = rows_area.y - self.scroll
        for tk in self.universe:
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H - 2)
            self._row_rects[tk] = row
            checked = tk in self.selected
            box_col = config.COL_UP if checked else config.COL_TEXT_DIM
            widgets.draw_text(surf, "[x]" if checked else "[ ]", (inner.x, y),
                              fonts.small(bold=True), box_col)
            label = tk + (" ✶" if tk in held else "")
            widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), inner.w - 34),
                              (inner.x + 26, y), fonts.small(),
                              config.COL_WHITE if checked else config.COL_TEXT_DIM)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - rows_area.y
        self._max_scroll = max(0, content_h - rows_area.h)
        self.scroll = max(0, min(self._max_scroll, self.scroll))
        self.scroll = widgets.draw_scrollbar(surf, rect, rows_area, self.scroll,
                                             self._max_scroll, content_h)
        widgets.draw_text_wrapped(surf, univ_hint, (inner.x, inner.bottom - univ_h),
                                  univ_font, config.COL_TEXT_DIM, inner.w, line_gap=3)

    def _draw_chart(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Rendement attendu vs risque (annualisés)",
                                   config.COL_UP)
        self._curve_px = []
        self._chart_plot = None
        # boutons rapides
        bx = inner.right
        self._maxsharpe_btn = self._quick_btn(surf, "MAX SHARPE", bx, inner.y - 2,
                                              config.COL_UP, right=True)
        self._minvar_btn = self._quick_btn(surf, "MIN VAR",
                                           self._maxsharpe_btn.x - 6, inner.y - 2,
                                           config.COL_CYAN, right=True)
        if self._fr is None:
            widgets.draw_text(surf, "Cochez au moins 2 valeurs avec assez d'historique.",
                              (inner.x, inner.y + 20), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        fr = self._fr
        vols = fr["vols"] * 100
        rets = fr["rets"] * 100
        cur_w, cur_val = QT.current_weights(self.app.gs.player, self.market,
                                            fr["tickers"])
        cur_pt = None
        if cur_val > 0:
            ret, vol, _sh = QT.point_stats(cur_w, fr["mean"], fr["cov"])
            cur_pt = (vol * 100, ret * 100)
        xs = list(vols) + ([cur_pt[0]] if cur_pt else [])
        ys = list(rets) + ([cur_pt[1]] if cur_pt else [])
        lo_x, hi_x = min(xs), max(xs)
        lo_y, hi_y = min(ys), max(ys)
        sx = (hi_x - lo_x) or 1.0
        sy = (hi_y - lo_y) or 1.0
        plot = inner.inflate(-46, -34)
        plot.move_ip(16, 2)
        plot.height -= 16  # réserve la place sous l'axe X pour l'étiquette + le conseil
        self._chart_plot = plot.inflate(SNAP_PX * 2, SNAP_PX * 2)

        def px(v, r):
            return (plot.x + int((v - lo_x) / sx * plot.w),
                    plot.bottom - int((r - lo_y) / sy * plot.h))
        # axes étiquetés
        pygame.draw.line(surf, config.COL_BORDER, plot.bottomleft, plot.bottomright)
        pygame.draw.line(surf, config.COL_BORDER, plot.topleft, plot.bottomleft)
        widgets.draw_text(surf, f"{lo_x:.0f}%", (plot.x - 4, plot.bottom + 4),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{hi_x:.0f}%  vol", (plot.right - 40, plot.bottom + 4),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{hi_y:.0f}%", (plot.x - 40, plot.y - 4),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{lo_y:.0f}%", (plot.x - 40, plot.bottom - 10),
                          fonts.tiny(), config.COL_TEXT_DIM)
        pts = [px(v, r) for v, r in zip(vols, rets)]
        self._curve_px = pts
        if len(pts) >= 2:
            pygame.draw.aalines(surf, config.COL_CYAN, False, pts)
        # marqueurs min-var / max-sharpe
        mv = pts[fr["i_min_var"]]
        ms = pts[fr["i_max_sharpe"]]
        pygame.draw.circle(surf, config.COL_CYAN, mv, 4)
        widgets.draw_text(surf, "min var", (mv[0] + 6, mv[1] + 2), fonts.tiny(),
                          config.COL_CYAN)
        pygame.draw.circle(surf, config.COL_UP, ms, 4)
        widgets.draw_text(surf, "max Sharpe", (ms[0] + 6, ms[1] - 12), fonts.tiny(),
                          config.COL_UP)
        if cur_pt:
            hp = px(*cur_pt)
            pygame.draw.circle(surf, config.COL_TEXT_DIM, hp, 5, 1)
            widgets.draw_text(surf, "ACTUEL", (hp[0] + 7, hp[1] + 4), fonts.tiny(),
                              config.COL_TEXT_DIM)
        if self.target_idx is not None and self.target_idx < len(pts):
            tp = pts[self.target_idx]
            pulse = 5
            pygame.draw.circle(surf, config.COL_AMBER, tp, pulse + 3, 2)
            pygame.draw.circle(surf, config.COL_AMBER, tp, 3)
            widgets.draw_text(surf, "CIBLE", (tp[0] + 8, tp[1] - 14),
                              fonts.tiny(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Cliquez la courbe pour poser la CIBLE.",
                          (inner.x, plot.bottom + 18), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _quick_btn(self, surf, label, x, y, col, right=False):
        w = fonts.tiny(bold=True).size(label)[0] + 14
        r = pygame.Rect(x - w if right else x, y, w, 18)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
        pygame.draw.rect(surf, col, r, 1, border_radius=3)
        widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True), col,
                          align="center")
        return r

    def _draw_target(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Point cible → ordres", config.COL_AMBER)
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        if self._fr is None or self.target_idx is None:
            widgets.draw_text(surf, "Aucune cible : cliquez un point de la frontière, "
                              "ou MAX SHARPE / MIN VAR.",
                              (inner.x, inner.y + 6), fonts.small(), config.COL_TEXT_DIM)
            if self.msg:
                widgets.draw_text(surf, self.msg, (inner.x, inner.y + 30),
                                  fonts.small(), self.msg_col)
            self._apply_btn = None
            return
        fr = self._fr
        w = fr["weights"][self.target_idx]
        ret, vol, sh = QT.point_stats(w, fr["mean"], fr["cov"])
        col_w = (inner.w - 16) // 2
        # colonne gauche : stats + poids
        x0, y = inner.x, inner.y + 2
        widgets.draw_text(surf, f"Rendement attendu {ret * 100:+.1f}% · "
                          f"vol {vol * 100:.1f}% · Sharpe {sh:+.2f}",
                          (x0, y), fonts.small(bold=True), config.COL_AMBER)
        y += 20
        budget = (self._trades or {}).get("budget", 0.0)
        proj = QT.projection(budget, ret, vol, years=1.0)
        widgets.draw_text(surf, f"Budget {widgets.format_money(budget, cur)} → dans 1 an : "
                          f"{widgets.format_money(proj['p5'], cur)} / "
                          f"{widgets.format_money(proj['p50'], cur)} / "
                          f"{widgets.format_money(proj['p95'], cur)} (p5/p50/p95)",
                          (x0, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 20
        cur_w, _tot = QT.current_weights(self.app.gs.player, self.market, fr["tickers"])
        rows = sorted(zip(fr["tickers"], w, cur_w), key=lambda t: t[1], reverse=True)
        bar_w = col_w - 130
        for tk, wi, ci in rows:
            if y > inner.bottom - 16:
                break
            if wi < 0.005 and ci < 0.005:
                continue
            widgets.draw_text(surf, tk, (x0, y), fonts.tiny(bold=True), config.COL_TEXT)
            bx = x0 + 52
            pygame.draw.rect(surf, config.COL_PANEL,
                             pygame.Rect(bx, y + 2, bar_w, 8), border_radius=2)
            pygame.draw.rect(surf, config.COL_TEXT_DIM,
                             pygame.Rect(bx, y + 2, int(bar_w * min(1.0, ci)), 8),
                             border_radius=2)
            pygame.draw.rect(surf, config.COL_AMBER,
                             pygame.Rect(bx, y + 6, int(bar_w * min(1.0, wi)), 4),
                             border_radius=2)
            widgets.draw_text(surf, f"{ci * 100:.0f}→{wi * 100:.0f}%",
                              (bx + bar_w + 6, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 15
        # colonne droite : liste d'ordres + APPLIQUER
        x1 = inner.x + col_w + 16
        y = inner.y + 2
        trades = (self._trades or {}).get("trades", [])
        if not trades:
            widgets.draw_text(surf, "Déjà sur la cible (ou écarts trop petits).",
                              (x1, y), fonts.small(), config.COL_UP)
            self._apply_btn = None
        else:
            widgets.draw_text(surf, f"ORDRES ({len(trades)}) :", (x1, y),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM)
            y += 16
            for t in trades:
                if y > inner.bottom - 40:
                    widgets.draw_text(surf, "…", (x1, y), fonts.tiny(),
                                      config.COL_TEXT_DIM)
                    y += 12
                    break
                side = "VENDRE" if t["side"] == "sell" else "ACHETER"
                col = config.COL_DOWN if t["side"] == "sell" else config.COL_UP
                widgets.draw_text(surf, f"{side} {t['qty']} × {t['ticker']}",
                                  (x1, y), fonts.small(bold=True), col)
                widgets.draw_text(surf, f"≈ {widgets.format_money(t['value'], cur)}",
                                  (x1 + 160, y), fonts.small(), config.COL_TEXT_DIM)
                y += 17
            y += 4
            self._apply_btn = pygame.Rect(x1, min(y, inner.bottom - 28), 220, 24)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._apply_btn,
                             border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER, self._apply_btn, 1,
                             border_radius=4)
            widgets.draw_text(surf, f"APPLIQUER ({len(trades)} ordres)",
                              self._apply_btn.center, fonts.small(bold=True),
                              config.COL_AMBER, align="center")
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(),
                                                     inner.w - (x1 - inner.x)),
                              (x1, inner.bottom - 14), fonts.tiny(), self.msg_col)

    def _draw_confirm(self, surf, rect):
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 170))
        surf.blit(shade, rect.topleft)
        trades = (self._trades or {}).get("trades", [])
        n_sell = sum(1 for t in trades if t["side"] == "sell")
        n_buy = len(trades) - n_sell
        box = pygame.Rect(0, 0, 360, 130)
        box.center = rect.center
        pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=6)
        pygame.draw.rect(surf, config.COL_AMBER, box, 1, border_radius=6)
        widgets.draw_text(surf, "Exécuter le rééquilibrage ?", (box.centerx, box.y + 16),
                          fonts.small(bold=True), config.COL_AMBER, align="center")
        widgets.draw_text(surf, f"{n_sell} vente(s) puis {n_buy} achat(s) — "
                          "frais et slippage réels.", (box.centerx, box.y + 42),
                          fonts.tiny(), config.COL_TEXT, align="center")
        self._yes_btn = pygame.Rect(box.x + 40, box.bottom - 44, 120, 26)
        self._no_btn = pygame.Rect(box.right - 160, box.bottom - 44, 120, 26)
        for r, lbl, col in ((self._yes_btn, "EXÉCUTER", config.COL_UP),
                            (self._no_btn, "ANNULER", config.COL_TEXT_DIM)):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=4)
            pygame.draw.rect(surf, col, r, 1, border_radius=4)
            widgets.draw_text(surf, lbl, r.center, fonts.small(bold=True), col,
                              align="center")
