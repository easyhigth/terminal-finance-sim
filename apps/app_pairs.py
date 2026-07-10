"""
app_pairs.py — Application « Pairs Trading » du bureau (NATIVE).

Première stratégie MARKET-NEUTRAL du jeu, la boucle complète de stat arb
(core/pairs.py) :

- **Scanner** : les paires les plus cointégrées des grosses capitalisations
  (test d'Engle-Granger), cliquables ;
- **Diagnostic** : β de cointégration, statistique ADF (verdict cointégré
  ou non), half-life du retour à la moyenne, corrélation ;
- **Spread** : le résidu u = ln(A) − α − β·ln(B) tracé dans le temps avec
  les bandes ±2σ (entrée) et 0 (sortie) — on VOIT l'élastique ;
- **Exécution** : LONG/SHORT réel (long une jambe, short l'autre
  dimensionnée par β en valeur), au signal affiché — soumis au déblocage
  « leverage », frais/slippage du jeu.
"""
import math

import pygame

from apps.base import DesktopApp
from core import config, unlocks
from core import pairs as PAIRS
from ui import fonts, widgets

NOTIONAL_CHOICES = [50_000.0, 100_000.0, 250_000.0]


class PairsApp(DesktopApp):
    title = "Pairs Trading"
    icon_kind = "trading"
    default_size = (1080, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.pair = None                  # (ticker_a, ticker_b)
        self.notional = NOTIONAL_CHOICES[1]
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self._scan_key = None
        self._scan = []
        self._eg_key = None
        self._eg = None
        self._pair_rects = {}
        self._notional_rects = {}
        self._exec_btn = None

    # ------------------------------------------------------------- calculs
    def _ensure_computed(self):
        if self._scan_key != self.market.step_count:
            self._scan_key = self.market.step_count
            self._scan = PAIRS.best_pairs(self.market)
            if self.pair is None and self._scan:
                self.pair = (self._scan[0][0], self._scan[0][1])
        key = (self.market.step_count, self.pair)
        if key != self._eg_key:
            self._eg_key = key
            self._eg = (PAIRS.engle_granger(self.market, *self.pair)
                        if self.pair else None)

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for pair, r in self._pair_rects.items():
            if r.collidepoint(pos):
                self.pair = pair
                self.msg = ""
                return True
        for v, r in self._notional_rects.items():
            if r.collidepoint(pos):
                self.notional = v
                return True
        if self._exec_btn and self._exec_btn.collidepoint(pos):
            self._execute()
            return True
        return False

    def _execute(self):
        p = self.app.gs.player
        if not unlocks.unlocked(p, "leverage"):
            g = unlocks.effective_required_grade(p, "leverage")
            self._say(f"Vente à découvert verrouillée (grade {config.GRADES[g]}).",
                      config.COL_DOWN)
            return
        if self._eg is None or self.pair is None:
            return
        sig = PAIRS.signal(self._eg["z_last"])
        if sig not in ("long_spread", "short_spread"):
            self._say("Pas de signal d'entrée (|z| < 2) — patience, c'est la "
                      "moitié du métier.", config.COL_AMBER)
            return
        r = PAIRS.execute_pair(p, self.market, self.pair[0], self.pair[1],
                               sig, self.notional)
        if r.get("ok"):
            legs = " · ".join(f"{leg['side'].upper()} {leg['qty']} {leg['ticker']}"
                              for leg in r["legs"])
            self._say(f"Paire exécutée ({legs}) — débouclez vers z ≈ 0.",
                      config.COL_UP)
        else:
            self._say(f"Refusé : {r.get('reason', '?')} "
                      f"({r.get('failed_leg', '')}).", config.COL_DOWN)

    def _say(self, text, col):
        self.msg, self.msg_col = text, col

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "PAIRS TRADING — ARBITRAGE STATISTIQUE",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        widgets.draw_text(surf, "Deux titres cointégrés = un élastique : on "
                          "vend l'écart quand il est tendu, on encaisse quand "
                          "il revient.", (rect.x + pad, rect.y + 30),
                          fonts.tiny(), config.COL_TEXT_DIM)
        body = pygame.Rect(rect.x + pad, rect.y + 52, rect.w - 2 * pad,
                           rect.bottom - pad - rect.y - 52)
        scan_w = 250
        scan = pygame.Rect(body.x, body.y, scan_w, body.h)
        rest = pygame.Rect(scan.right + 12, body.y, body.w - scan_w - 12, body.h)
        chart_h = int(rest.h * 0.55)
        chart = pygame.Rect(rest.x, rest.y, rest.w, chart_h)
        panel = pygame.Rect(rest.x, rest.y + chart_h + 8, rest.w,
                            rest.h - chart_h - 8)
        self._draw_scanner(surf, scan)
        self._draw_spread(surf, chart)
        self._draw_panel(surf, panel)

    def _draw_scanner(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Scanner (les + cointégrées)",
                                   config.COL_CYAN)
        self._pair_rects = {}
        y = inner.y + 2
        if not self._scan:
            widgets.draw_text(surf, "Historique insuffisant.", (inner.x, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
        for tka, tkb, adf, z in self._scan:
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 34)
            self._pair_rects[(tka, tkb)] = r
            sel = self.pair == (tka, tkb)
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, f"{tka} / {tkb}", (inner.x, y),
                              fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            zcol = (config.COL_UP if abs(z) >= PAIRS.ENTRY_Z
                    else config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"ADF {adf:.2f} · z {z:+.1f}",
                              (inner.x + 8, y + 16), fonts.tiny(), zcol)
            y += 36
        scan_hint = "ADF < −3 ⇒ spread stationnaire (cointégré)."
        scan_font = fonts.tiny()
        scan_lines = len(widgets.wrap_text_lines(scan_hint, scan_font, inner.w))
        scan_h = scan_lines * (scan_font.get_height() + 3)
        widgets.draw_text_wrapped(surf, scan_hint, (inner.x, inner.bottom - scan_h),
                                  scan_font, config.COL_TEXT_DIM, inner.w, line_gap=3)

    def _draw_spread(self, surf, rect):
        title = (f"Spread ln({self.pair[0]}) − β·ln({self.pair[1]})"
                 if self.pair else "Spread")
        inner = widgets.draw_panel(surf, rect, title, config.COL_UP)
        eg = self._eg
        if eg is None:
            widgets.draw_text(surf, "Sélectionnez une paire.", (inner.x, inner.y + 6),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        z = eg["z"]
        lo = min(float(z.min()), -2.6)
        hi = max(float(z.max()), 2.6)
        rng = (hi - lo) or 1.0
        plot = inner.inflate(-8, -16)

        def py(v):
            return plot.bottom - int((v - lo) / rng * plot.h)
        for lvl, col in ((PAIRS.ENTRY_Z, config.COL_DOWN),
                         (-PAIRS.ENTRY_Z, config.COL_DOWN),
                         (0.0, config.COL_BORDER)):
            yy = py(lvl)
            for x0 in range(plot.x, plot.right, 8):
                pygame.draw.line(surf, col, (x0, yy), (min(x0 + 4, plot.right), yy))
            if lvl:
                widgets.draw_text(surf, f"{lvl:+.0f}σ", (plot.right - 26, yy - 12),
                                  fonts.tiny(), col)
        pts = [(plot.x + int(i / max(1, len(z) - 1) * plot.w), py(float(v)))
               for i, v in enumerate(z)]
        pygame.draw.aalines(surf, config.COL_CYAN, False, pts)
        pygame.draw.circle(surf, config.COL_WHITE, pts[-1], 3)
        widgets.draw_text(surf, "±2σ = entrée · retour à 0 = sortie",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _draw_panel(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Diagnostic & exécution",
                                   config.COL_AMBER)
        eg = self._eg
        if eg is None:
            self._exec_btn = None
            return
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        y = inner.y + 2
        ccol = config.COL_UP if eg["cointegrated"] else config.COL_DOWN
        verdict = ("COINTÉGRÉE (spread stationnaire)" if eg["cointegrated"]
                   else "non cointégrée — l'élastique n'est pas prouvé")
        widgets.draw_text(surf, f"β = {eg['beta']:.2f} · ADF {eg['adf_t']:.2f} "
                          f"(seuil {PAIRS.ADF_CRITICAL}) · corr {eg['corr']:+.2f}",
                          (inner.x, y), fonts.small(), config.COL_TEXT)
        y += 20
        widgets.draw_text(surf, verdict, (inner.x, y), fonts.small(bold=True), ccol)
        y += 20
        hl = (f"{eg['half_life']:.0f} pas (≈ {eg['half_life'] * 5:.0f} j)"
              if math.isfinite(eg["half_life"]) else "∞ (pas de retour)")
        widgets.draw_text(surf, f"Half-life du retour à la moyenne : {hl}",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 22
        sig = PAIRS.signal(eg["z_last"])
        sig_txt = {
            "long_spread": f"z = {eg['z_last']:+.2f} → LONG SPREAD : acheter "
                           f"{self.pair[0]}, shorter {self.pair[1]}",
            "short_spread": f"z = {eg['z_last']:+.2f} → SHORT SPREAD : shorter "
                            f"{self.pair[0]}, acheter {self.pair[1]}",
            "exit": f"z = {eg['z_last']:+.2f} → zone de SORTIE (déboucler une "
                    "paire en cours)",
            "hold": f"z = {eg['z_last']:+.2f} → pas de signal (|z| < 2)",
        }[sig]
        scol = (config.COL_UP if sig in ("long_spread", "short_spread")
                else config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.fit_text(sig_txt, fonts.small(bold=True),
                                                 inner.w),
                          (inner.x, y), fonts.small(bold=True), scol)
        y += 26
        widgets.draw_text(surf, "Notionnel :", (inner.x, y + 3), fonts.tiny(),
                          config.COL_TEXT_DIM)
        x = inner.x + 70
        self._notional_rects = {}
        for v in NOTIONAL_CHOICES:
            lbl = widgets.format_money(v, cur)
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            self._notional_rects[v] = r
            sel = abs(v - self.notional) < 1e-9
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        self._exec_btn = pygame.Rect(x + 12, y - 2, 190, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._exec_btn, border_radius=4)
        pygame.draw.rect(surf, scol, self._exec_btn, 1, border_radius=4)
        widgets.draw_text(surf, "EXÉCUTER LA PAIRE", self._exec_btn.center,
                          fonts.small(bold=True), scol, align="center")
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(), inner.w),
                              (inner.x, inner.bottom - 14), fonts.tiny(),
                              self.msg_col)
