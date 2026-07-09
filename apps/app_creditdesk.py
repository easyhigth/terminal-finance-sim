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
from core import config
from core import credit_risk as CR
from core import securitisation as SEC
from ui import fonts, widgets

TABS = [("merton", "MERTON (la dette comme option)"),
        ("waterfall", "WATERFALL (titrisation)")]


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
        return False

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
        widgets.draw_text(surf, "DESK CRÉDIT — DÉFAUT, SPREADS, TITRISATION",
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
        if self.tab == "merton":
            self._draw_merton(surf, body)
        else:
            self._draw_waterfall(surf, body)

    # -------------------------------------------------------------- Merton
    def _draw_merton(self, surf, body):
        scan_w = 260
        scan = pygame.Rect(body.x, body.y, scan_w, body.h)
        rest = pygame.Rect(scan.right + 12, body.y, body.w - scan_w - 12, body.h)
        inner = widgets.draw_panel(surf, scan, "Scanner (PD décroissante)",
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
            surf, rest, f"{self.ticker or '—'} — la dette comme option",
            config.COL_CYAN)
        if f is None:
            return
        y = rinner.y + 2
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        lines = [
            (f"Actifs V = actions {widgets.format_money(f['equity'], cur)} + "
             f"dette {widgets.format_money(f['debt'], cur)}", config.COL_TEXT),
            (f"Levier D/E = {f['leverage']:.2f} · vol actions "
             f"{f['sigma_e'] * 100:.0f}% → vol actifs {f['sigma_v'] * 100:.0f}% "
             "(dé-leviérée)", config.COL_TEXT_DIM),
        ]
        for txt, col in lines:
            widgets.draw_text(surf, widgets.fit_text(txt, fonts.small(), rinner.w),
                              (rinner.x, y), fonts.small(), col)
            y += 20
        y += 6
        dd_txt = "∞" if f["dd"] == float("inf") else f"{f['dd']:.2f}"
        pcol = (config.COL_DOWN if f["pd"] > 0.05
                else config.COL_AMBER if f["pd"] > 0.01 else config.COL_UP)
        widgets.draw_text(surf, f"Distance au défaut : {dd_txt} σ", (rinner.x, y),
                          fonts.head(bold=True), pcol)
        y += 26
        widgets.draw_text(surf, f"PD 1 an : {f['pd'] * 100:.2f}% · spread "
                          f"implicite ≈ {f['spread_bps']:.0f} bp (LGD 60 %)",
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
            widgets.draw_text(surf, "PD si le COURS de l'action bouge de… — le lien "
                              "actions ↔ spreads.", (plot.x + 6, plot.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)

    # ----------------------------------------------------------- Waterfall
    def _draw_waterfall(self, surf, body):
        inner = widgets.draw_panel(surf, body,
                                   "Cascade des pertes d'un pool titrisé",
                                   config.COL_AMBER)
        widgets.draw_text(surf, "Glissez le curseur : la perte du pool remonte la "
                          "structure — l'equity absorbe d'abord, le senior en dernier.",
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
        widgets.draw_text(surf, f"Perte du pool : {self.pool_loss * 100:.0f}%",
                          (sr.right + 12, y), fonts.small(bold=True),
                          config.COL_DOWN)
        # perte attendue courante (macro du jeu) marquée sur la jauge
        el = SEC.expected_pool_loss(self.market)
        ex = sr.x + int(sr.w * min(1.0, el))
        pygame.draw.line(surf, config.COL_AMBER, (ex, sr.y - 6), (ex, sr.bottom + 6), 2)
        widgets.draw_text(surf, f"attendue {el * 100:.0f}%", (ex - 26, sr.bottom + 8),
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
            status = ("INDEMNE" if loss == 0.0
                      else "ANÉANTIE" if loss >= 1.0 else f"−{loss * 100:.0f}%")
            scol = (config.COL_UP if loss == 0.0
                    else config.COL_DOWN if loss >= 1.0 else config.COL_AMBER)
            widgets.draw_text(surf, status, (r.right - 90, r.y + 6),
                              fonts.small(bold=True), scol)
            widgets.draw_text(surf, "le coupon paie le RISQUE de rang : plus on "
                              "est bas dans la cascade, plus il est gros",
                              (r.x + 10, r.y + bar_h - 16), fonts.tiny(),
                              config.COL_TEXT_DIM)
            y += bar_h + 12
