"""
scene_ma.py — Module M&A : analyse d'une opération.
Deux outils en un :
  1. LBO : ajuster levier / multiple de sortie / croissance EBITDA -> MOIC & IRR
  2. Accretion / Dilution : impact d'une acquisition payée en actions sur le BPA
Basé sur core.finmath (lbo_returns, accretion_dilution).
"""
import pygame
from core import config
from core.scene_manager import Scene
from core import finmath as fm
from ui import fonts, widgets


class MAScene(Scene):
    def on_enter(self, **kwargs):
        # paramètres LBO
        self.entry_ev = 1000.0      # M€
        self.entry_ebitda = 100.0
        self.debt_pct = 0.6
        self.exit_multiple = 11.0
        self.years = 5
        self.ebitda_cagr = 0.08
        # paramètres accretion/dilution
        self.acq_eps = 5.0
        self.acq_shares = 100.0      # M
        self.target_ni = 200.0       # M€
        self.new_shares = 30.0       # M
        self.synergies = 50.0        # M€

        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT-66, 160, 44), "← TERMINAL", config.COL_TEXT_DIM)
        self._sliders = {}

    def _adj(self, key, delta):
        bounds = {
            "debt_pct": (0.0, 0.85, 0.05),
            "exit_multiple": (5.0, 18.0, 0.5),
            "years": (3, 8, 1),
            "ebitda_cagr": (0.0, 0.20, 0.01),
            "synergies": (0.0, 200.0, 10.0),
            "new_shares": (0.0, 100.0, 5.0),
        }
        lo, hi, _ = bounds[key]
        val = getattr(self, key) + delta
        setattr(self, key, max(lo, min(hi, val)))

    def handle_event(self, event):
        if self.back_btn.handle(event):
            self.app.scenes.go("terminal")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, (minus, plus, step) in self._sliders.items():
                if minus.collidepoint(event.pos):
                    self._adj(key, -step)
                elif plus.collidepoint(event.pos):
                    self._adj(key, +step)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos())

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MODULE M&A — ANALYSE D'OPÉRATION",
                          (40, 24), fonts.title(bold=True), config.COL_AMBER)
        self._sliders = {}
        self._draw_lbo(surf)
        self._draw_accretion(surf)
        self.back_btn.draw(surf)

    # ---- LBO -------------------------------------------------------------
    def _slider(self, surf, x, y, label, value, key, step, fmt="{:.0f}"):
        widgets.draw_text(surf, label, (x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, fmt.format(value), (x+250, y),
                          fonts.small(bold=True), config.COL_WHITE)
        minus = pygame.Rect(x+320, y-2, 24, 22)
        plus = pygame.Rect(x+348, y-2, 24, 22)
        for rect, sym in ((minus, "-"), (plus, "+")):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
            img = fonts.body(bold=True).render(sym, True, config.COL_AMBER)
            surf.blit(img, img.get_rect(center=rect.center))
        self._sliders[key] = (minus, plus, step)

    def _draw_lbo(self, surf):
        panel = pygame.Rect(40, 110, 600, 560)
        inner = widgets.draw_panel(surf, panel, "Leveraged Buyout (LBO)", config.COL_UP)
        x, y = inner.x, inner.y
        widgets.draw_text(surf, f"EV d'entrée : {self.entry_ev:.0f} M  |  "
                                f"EBITDA : {self.entry_ebitda:.0f} M  |  "
                                f"Multiple entrée : {self.entry_ev/self.entry_ebitda:.1f}x",
                          (x, y), fonts.small(), config.COL_TEXT_DIM)
        y += 36
        self._slider(surf, x, y, "Levier (dette / EV)", self.debt_pct, "debt_pct", 0.05, "{:.0%}"); y += 38
        self._slider(surf, x, y, "Multiple de sortie", self.exit_multiple, "exit_multiple", 0.5, "{:.1f}x"); y += 38
        self._slider(surf, x, y, "Horizon (années)", self.years, "years", 1, "{:.0f}"); y += 38
        self._slider(surf, x, y, "Croissance EBITDA (CAGR)", self.ebitda_cagr, "ebitda_cagr", 0.01, "{:.0%}"); y += 50

        moic, irr_v, exit_eq = fm.lbo_returns(
            self.entry_ev, self.entry_ebitda, self.debt_pct,
            self.exit_multiple, int(self.years), self.ebitda_cagr)

        res_panel = pygame.Rect(x-4, y, inner.w-8, 230)
        pygame.draw.rect(surf, (10, 22, 14), res_panel)
        pygame.draw.rect(surf, config.COL_UP, res_panel, 1)
        ry = y+14
        equity_in = self.entry_ev * (1 - self.debt_pct)
        exit_ebitda = self.entry_ebitda * ((1+self.ebitda_cagr)**int(self.years))
        rows = [
            ("Equity investi (entrée)", f"{equity_in:.0f} M", config.COL_TEXT),
            ("EBITDA de sortie", f"{exit_ebitda:.0f} M", config.COL_TEXT),
            ("EV de sortie", f"{exit_ebitda*self.exit_multiple:.0f} M", config.COL_TEXT),
            ("Equity de sortie", f"{exit_eq:.0f} M", config.COL_WHITE),
            ("", "", config.COL_TEXT),
            ("MOIC (multiple)", f"{moic:.2f}x",
             config.COL_UP if moic >= 2 else config.COL_WARN),
            ("IRR (fonds propres)", f"{irr_v*100:.1f}%",
             config.COL_UP if irr_v >= 0.20 else config.COL_WARN if irr_v >= 0.10 else config.COL_DOWN),
        ]
        for label, val, col in rows:
            if label:
                widgets.draw_text(surf, label, (res_panel.x+14, ry),
                                  fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, val, (res_panel.x+330, ry),
                                  fonts.body(bold=True), col)
            ry += 30
        # verdict
        verdict = ("Deal attractif (IRR > 20%)" if irr_v >= 0.20
                   else "Deal limite" if irr_v >= 0.10
                   else "Deal à éviter (IRR faible)")
        vcol = (config.COL_UP if irr_v >= 0.20
                else config.COL_WARN if irr_v >= 0.10 else config.COL_DOWN)
        widgets.draw_text(surf, verdict, (res_panel.x+14, res_panel.bottom-26),
                          fonts.small(bold=True), vcol)

    # ---- Accretion / Dilution -------------------------------------------
    def _draw_accretion(self, surf):
        panel = pygame.Rect(660, 110, config.SCREEN_WIDTH-700, 560)
        inner = widgets.draw_panel(surf, panel, "Accretion / Dilution (paiement en actions)",
                                   config.COL_CYAN)
        x, y = inner.x, inner.y
        widgets.draw_text(surf, "Acquéreur", (x, y), fonts.small(bold=True), config.COL_AMBER)
        y += 26
        widgets.draw_text(surf, f"BPA actuel : {self.acq_eps:.2f}   "
                                f"Actions : {self.acq_shares:.0f} M",
                          (x, y), fonts.small(), config.COL_TEXT); y += 26
        widgets.draw_text(surf, f"Résultat net : {self.acq_eps*self.acq_shares:.0f} M",
                          (x, y), fonts.small(), config.COL_TEXT_DIM); y += 40

        widgets.draw_text(surf, "Cible & financement", (x, y),
                          fonts.small(bold=True), config.COL_AMBER); y += 28
        widgets.draw_text(surf, f"Résultat net cible : {self.target_ni:.0f} M",
                          (x, y), fonts.small(), config.COL_TEXT); y += 34
        self._slider(surf, x, y, "Actions émises (M)", self.new_shares, "new_shares", 5.0, "{:.0f}"); y += 38
        self._slider(surf, x, y, "Synergies (M)", self.synergies, "synergies", 10.0, "{:.0f}"); y += 50

        pf_eps, delta = fm.accretion_dilution(
            self.acq_eps, self.acq_shares*1e6, self.target_ni*1e6,
            self.new_shares*1e6, self.synergies*1e6)

        res = pygame.Rect(x-4, y, inner.w-8, 200)
        accretive = delta >= 0
        bg = (10, 22, 14) if accretive else (24, 12, 14)
        border = config.COL_UP if accretive else config.COL_DOWN
        pygame.draw.rect(surf, bg, res)
        pygame.draw.rect(surf, border, res, 1)
        ry = y+16
        widgets.draw_text(surf, "BPA pro-forma", (res.x+14, ry),
                          fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{pf_eps:.3f}", (res.x+260, ry),
                          fonts.body(bold=True), config.COL_WHITE); ry += 36
        widgets.draw_text(surf, "Variation du BPA", (res.x+14, ry),
                          fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{'+' if delta>=0 else ''}{delta:.2f}%",
                          (res.x+260, ry), fonts.head(bold=True), border); ry += 44
        verdict = "RELUTIF (accretive) ✓" if accretive else "DILUTIF (dilutive) ✗"
        widgets.draw_text(surf, verdict, (res.x+14, ry),
                          fonts.body(bold=True), border); ry += 34
        note = ("Le BPA combiné dépasse celui de l'acquéreur : crée de la valeur par action."
                if accretive else
                "Le BPA combiné baisse : à justifier par des synergies futures ou stratégie.")
        widgets.draw_text_wrapped(surf, note, (res.x+14, ry),
                                  fonts.small(), config.COL_TEXT, res.w-28)
