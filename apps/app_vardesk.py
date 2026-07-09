"""
app_vardesk.py — Application « Risque (VaR) » du bureau (NATIVE).

La feuille de risque d'un desk, sur le book RÉEL du joueur et le PROPRE
modèle à facteurs du marché (core/risk.simulate — cohérence totale avec le
moteur) :

- tuiles VaR / CVaR (95 % et 99 %, 1 pas de marché) + histogramme de la
  distribution simulée de P&L avec les seuils marqués — la différence
  VaR/CVaR (queue au-delà du seuil) se VOIT ;
- **VaR par position (allocation d'Euler)** — core/risk_advanced.py :
  quelle ligne PORTE le risque (les contributions somment à la VaR
  totale ; une contribution négative = une couverture) ;
- **Backtest de Kupiec** : la VaR paramétrique rejouée sur l'historique
  du panier, exceptions comptées, statistique LR et verdict — un modèle
  de risque, ça se VALIDE ;
- lien vers le Stress test (scénarios nommés, écran existant).
"""
import pygame

from apps.base import DesktopApp
from core import config, risk
from core import risk_advanced as RA
from ui import fonts, widgets


class VarDeskApp(DesktopApp):
    title = "Risque (VaR)"
    icon_kind = "risk"
    default_size = (1060, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.confidence = 0.95
        self._cache_key = None
        self._sim = None
        self._comp = None
        self._bt = None
        self._conf_rects = {}
        self._stress_btn = None

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        p = self.app.gs.player
        key = (self.market.step_count, self.confidence, len(p.portfolio),
               len(getattr(p, "bonds", {}) or {}))
        if key == self._cache_key:
            return
        self._cache_key = key
        if p.portfolio or getattr(p, "bonds", None):
            self._sim = risk.simulate(p, self.market, confidence=self.confidence,
                                      n=8000)
            self._comp = RA.component_var(p, self.market,
                                          confidence=self.confidence, n=8000)
            self._bt = RA.var_backtest(p, self.market,
                                       confidence=self.confidence)
        else:
            self._sim = self._comp = self._bt = None

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        for conf, r in self._conf_rects.items():
            if r.collidepoint(event.pos):
                self.confidence = conf
                return True
        if self._stress_btn and self._stress_btn.collidepoint(event.pos):
            if self.desktop is not None:
                self.desktop._open_scene_window("stresstest")
            return True
        return False

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "RISQUE — VaR · CVaR · CONTRIBUTIONS · BACKTEST",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        x, y = rect.x + pad, rect.y + 32
        self._conf_rects = {}
        for conf in (0.95, 0.99):
            lbl = f"{conf * 100:.0f} %"
            w = fonts.tiny(bold=True).size(lbl)[0] + 16
            r = pygame.Rect(x, y, w, 20)
            self._conf_rects[conf] = r
            sel = abs(conf - self.confidence) < 1e-9
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        sw = fonts.tiny(bold=True).size("STRESS TEST →")[0] + 16
        self._stress_btn = pygame.Rect(rect.right - pad - sw, y, sw, 20)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._stress_btn,
                         border_radius=3)
        pygame.draw.rect(surf, config.COL_DOWN, self._stress_btn, 1, border_radius=3)
        widgets.draw_text(surf, "STRESS TEST →", self._stress_btn.center,
                          fonts.tiny(bold=True), config.COL_DOWN, align="center")
        top = y + 28
        if self._sim is None:
            widgets.draw_text(surf, "Book vide — la VaR mesure le risque de VOS "
                              "positions (actions, obligations).",
                              (rect.x + pad, top + 8), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        # tuiles
        s = self._sim
        tiles = [
            (f"VaR {self.confidence * 100:.0f}% (1 pas)", f"{s['var']:.2f} M",
             config.COL_DOWN),
            (f"CVaR {self.confidence * 100:.0f}%", f"{s['cvar']:.2f} M",
             config.COL_DOWN),
            ("VaR PARAM.", f"{s['param_var']:.2f} M", config.COL_AMBER),
            ("σ P&L", f"{s['sigma']:.2f} M", config.COL_TEXT),
        ]
        tx = rect.x + pad
        for lbl, val, col in tiles:
            tw = max(150, fonts.head(bold=True).size(val)[0] + 24)
            tr = pygame.Rect(tx, top, tw, 50)
            pygame.draw.rect(surf, config.COL_PANEL, tr, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, tr, 1, border_radius=4)
            widgets.draw_text(surf, lbl, (tr.x + 8, tr.y + 5), fonts.tiny(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (tr.x + 8, tr.y + 20),
                              fonts.head(bold=True), col)
            tx += tw + 8
        body_top = top + 60
        col_w = (rect.w - 2 * pad - 12) // 2
        left = pygame.Rect(rect.x + pad, body_top, col_w,
                           rect.bottom - pad - body_top)
        right = pygame.Rect(left.right + 12, body_top, col_w, left.h)
        h_half = (left.h - 10) // 2
        self._draw_hist(surf, pygame.Rect(left.x, left.y, left.w, h_half), s)
        self._draw_backtest(surf, pygame.Rect(left.x, left.y + h_half + 10,
                                              left.w, h_half))
        self._draw_components(surf, right)

    def _draw_hist(self, surf, rect, s):
        inner = widgets.draw_panel(surf, rect,
                                   "Distribution simulée du P&L (1 pas, en M)",
                                   config.COL_CYAN)
        import numpy as np
        pnl = s["pnl"]
        counts, edges = np.histogram(pnl, bins=40)
        cmax = counts.max() or 1
        plot = inner.inflate(-8, -18)
        bw = plot.w / len(counts)
        lo, hi = edges[0], edges[-1]
        for i, c in enumerate(counts):
            h = int(c / cmax * plot.h)
            x0 = plot.x + int(i * bw)
            mid = 0.5 * (edges[i] + edges[i + 1])
            col = config.COL_DOWN if mid <= -s["var"] else config.COL_PANEL_HEAD
            pygame.draw.rect(surf, col, pygame.Rect(x0, plot.bottom - h,
                                                    max(1, int(bw) - 1), h))
        for val, col, lbl in ((-s["var"], config.COL_AMBER, "VaR"),
                              (-s["cvar"], config.COL_DOWN, "CVaR")):
            if hi > lo:
                x0 = plot.x + int((val - lo) / (hi - lo) * plot.w)
                pygame.draw.line(surf, col, (x0, plot.y), (x0, plot.bottom), 1)
                widgets.draw_text(surf, lbl, (x0 + 3, plot.y), fonts.tiny(), col)
        widgets.draw_text(surf, "Barres rouges : la QUEUE au-delà de la VaR — "
                          "leur moyenne est la CVaR.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _draw_backtest(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Backtest de Kupiec (VaR param.)",
                                   config.COL_UP)
        bt = self._bt
        if bt is None:
            widgets.draw_text(surf, "Historique insuffisant (il faut ≥ 20 pas de "
                              "panier actions).", (inner.x, inner.y + 6),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        y = inner.y + 2
        widgets.draw_text(surf, f"{bt['n']} pas rejoués · seuil VaR "
                          f"{bt['var_step_pct']:.2f} %/pas",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 18
        col = config.COL_DOWN if bt["reject"] else config.COL_UP
        widgets.draw_text(surf, f"Exceptions : {bt['exceptions']} "
                          f"(attendu ≈ {bt['expected']:.1f})",
                          (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
        y += 20
        widgets.draw_text(surf, f"LR de Kupiec = {bt['lr']:.2f} "
                          f"(seuil χ² 95 % = {RA.KUPIEC_CHI2_95})",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT)
        y += 18
        verdict = ("MODÈLE REJETÉ — trop d'écarts avec l'observé"
                   if bt["reject"] else "Modèle NON rejeté — calibrage cohérent")
        widgets.draw_text(surf, verdict, (inner.x, y), fonts.small(bold=True), col)
        # frise des rendements avec exceptions marquées
        y += 22
        strip = pygame.Rect(inner.x, y, inner.w, max(18, inner.bottom - y - 14))
        if strip.h >= 18 and bt["n"] > 1:
            import numpy as np
            rets = bt["returns"]
            lo, hi = float(np.min(rets)), float(np.max(rets))
            rng = (hi - lo) or 1.0
            exc = set(bt["exception_idx"])
            for i, r in enumerate(rets):
                x0 = strip.x + int(i / (bt["n"] - 1) * (strip.w - 2))
                y0 = strip.bottom - int((r - lo) / rng * strip.h)
                col = config.COL_DOWN if i in exc else config.COL_TEXT_DIM
                pygame.draw.circle(surf, col, (x0, y0), 2 if i in exc else 1)

    def _draw_components(self, surf, rect):
        inner = widgets.draw_panel(surf, rect,
                                   "VaR par position (allocation d'Euler)",
                                   config.COL_AMBER)
        comp = self._comp
        if comp is None or not comp["lines"]:
            widgets.draw_text(surf, "Aucune ligne.", (inner.x, inner.y + 6),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        widgets.draw_text(surf, "Les contributions SOMMENT à la VaR totale — une "
                          "contribution négative est une couverture.",
                          (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        y = inner.y + 20
        cmax = max(abs(x["contrib"]) for x in comp["lines"]) or 1.0
        bar_w = inner.w - 210
        for line in comp["lines"]:
            if y > inner.bottom - 16:
                widgets.draw_text(surf, "…", (inner.x, y), fonts.tiny(),
                                  config.COL_TEXT_DIM)
                break
            widgets.draw_text(surf, widgets.fit_text(line["label"],
                                                     fonts.small(bold=True), 90),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            bx = inner.x + 96
            frac = line["contrib"] / cmax
            col = config.COL_DOWN if frac >= 0 else config.COL_UP
            w = int(abs(frac) * bar_w * 0.5)
            mid = bx + bar_w // 2
            pygame.draw.line(surf, config.COL_BORDER, (mid, y), (mid, y + 12))
            r0 = pygame.Rect(mid if frac >= 0 else mid - w, y + 2, w, 10)
            pygame.draw.rect(surf, col, r0, border_radius=2)
            widgets.draw_text(surf, f"{line['contrib']:+.2f} M ({line['pct']:+.0f}%)",
                              (bx + bar_w + 8, y), fonts.tiny(), col)
            y += 18
        total = sum(x["contrib"] for x in comp["lines"])
        widgets.draw_text(surf, f"Σ contributions = {total:.2f} M ≈ VaR "
                          f"{comp['var']:.2f} M (propriété d'Euler)",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
