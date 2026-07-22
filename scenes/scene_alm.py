"""
scene_alm.py — Desk ALM : gestion actif-passif du banking book.

Le joueur règle les masses et durations de l'actif/passif, puis applique un choc
de taux pour voir l'impact sur la marge nette d'intérêt (NII) et sur la valeur
économique des fonds propres (ΔEVE). Outil d'analyse (sandbox). Ouvert via ALM.
"""
import pygame

from core import alm, config, unlocks
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


# (clé, (libellé fr, en), pas, format)
FIELDS = [
    ("assets", ("Actifs totaux (M)", "Total assets (M)"), 50.0, "{:.0f}"),
    ("liabilities", ("Passifs totaux (M)", "Total liabilities (M)"), 50.0, "{:.0f}"),
    ("rsa", ("Actifs sensibles 1 an (M)", "1Y rate-sensitive assets (M)"), 25.0, "{:.0f}"),
    ("rsl", ("Passifs sensibles 1 an (M)", "1Y rate-sensitive liabilities (M)"), 25.0, "{:.0f}"),
    ("dur_a", ("Duration actifs (ans)", "Asset duration (yrs)"), 0.5, "{:.1f}"),
    ("dur_l", ("Duration passifs (ans)", "Liability duration (yrs)"), 0.5, "{:.1f}"),
]
SHOCKS = [("-200 bps", -0.02), ("-100 bps", -0.01), ("+100 bps", 0.01), ("+200 bps", 0.02)]


class AlmScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.state = dict(alm.DEFAULT_STATE)
        self.dy = 0.01
        self._field_btns = {}
        self._shock_btns = {}
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       _L("TUTO", "GUIDE"), config.COL_CYAN)

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "alm")

    def _adj(self, key, delta):
        lo = 0.0
        self.state[key] = max(lo, round(self.state[key] + delta, 2))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="alm", return_to="alm")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, (minus, plus, step) in self._field_btns.items():
                if minus.collidepoint(event.pos):
                    self._adj(key, -step)
                elif plus.collidepoint(event.pos):
                    self._adj(key, +step)
            for dy, rect in self._shock_btns.items():
                if rect.collidepoint(event.pos):
                    self.dy = dy

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        self.tuto_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("DESK ALM — GESTION ACTIF-PASSIF", "ALM DESK — ASSET-LIABILITY MANAGEMENT"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L("Banking book : risque de taux & de liquidité. Réglez le bilan, "
                                "appliquez un choc de taux, lisez NII et ΔEVE.",
                                "Banking book: rate & liquidity risk. Adjust the balance sheet, "
                                "apply a rate shock, read NII and ΔEVE."),
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)
        self._field_btns = {}
        self._shock_btns = {}
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "alm")
            widgets.draw_text(surf, _L(f"⊘ Desk ALM débloqué au grade {config.GRADES[g]}.", f"⊘ ALM desk unlocked at {config.GRADES[g]} grade."),
                              (42, 110), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return
        ph = config.footer_y() - 8 - 100

        # ----- réglage du bilan (gauche) -----
        panel = pygame.Rect(40, 100, 560, ph)
        inner = widgets.draw_panel(surf, panel, _L("Bilan (M)", "Balance sheet (M)"), config.COL_CYAN)
        self._field_btns = {}
        y = inner.y
        for key, label_pair, step, fmt in FIELDS:
            widgets.draw_text(surf, _L(*label_pair), (inner.x, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, fmt.format(self.state[key]), (inner.x + 330, y),
                              fonts.small(bold=True), config.COL_WHITE)
            minus = pygame.Rect(inner.x + inner.w - 70, y - 2, 26, 22)
            plus = pygame.Rect(inner.x + inner.w - 38, y - 2, 26, 22)
            for rect, sym in ((minus, "-"), (plus, "+")):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
                pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
                img = fonts.body(bold=True).render(sym, True, config.COL_AMBER)
                surf.blit(img, img.get_rect(center=rect.center))
            self._field_btns[key] = (minus, plus, step)
            y += 46

        # choc de taux
        y += 4
        widgets.draw_text(surf, _L("Choc de taux :", "Rate shock:"), (inner.x, y), fonts.small(bold=True), config.COL_TEXT_DIM)
        self._shock_btns = {}
        x = inner.x
        for label, dy in SHOCKS:
            rect = pygame.Rect(x, y + 22, 120, 28)
            self._shock_btns[dy] = rect
            sel = abs(self.dy - dy) < 1e-9
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_WARN if sel else config.COL_BORDER, rect, 1)
            img = fonts.small(bold=sel).render(label, True,
                                               config.COL_WARN if sel else config.COL_TEXT)
            surf.blit(img, img.get_rect(center=rect.center))
            x += 128

        # ----- résultats (droite) -----
        s = alm.summary(self.state, self.dy)
        rp = pygame.Rect(620, 100, config.SCREEN_WIDTH - 660, ph)
        rinner = widgets.draw_panel(surf, rp, _L("Diagnostic ALM", "ALM diagnostics"), config.COL_AMBER)
        gcol = config.COL_UP if s["repricing_gap"] >= 0 else config.COL_DOWN
        rows = [
            (_L("Profil", "Profile"), _L("neutre", "neutral") if s["profile"] == "neutre" else s["profile"], config.COL_WHITE),
            (_L("Capitaux propres", "Equity"), f"{s['equity']:,.0f} M".replace(",", " "), config.COL_WHITE),
            (_L("Repricing gap (1 an)", "Repricing gap (1Y)"), f"{s['repricing_gap']:+,.0f} M".replace(",", " "), gcol),
            (_L("Duration gap", "Duration gap"), _L(f"{s['duration_gap']:+.2f} ans", f"{s['duration_gap']:+.2f} yrs"),
             config.COL_DOWN if s["duration_gap"] > 0 else config.COL_UP),
            ("", "", config.COL_TEXT),
            (_L(f"Δ NII (choc {self.dy*10000:+.0f} bps)", f"Δ NII (shock {self.dy*10000:+.0f} bps)"), f"{s['delta_nii']:+,.1f} M".replace(",", " "),
             config.COL_UP if s["delta_nii"] >= 0 else config.COL_DOWN),
            (_L(f"Δ EVE (choc {self.dy*10000:+.0f} bps)", f"Δ EVE (shock {self.dy*10000:+.0f} bps)"), f"{s['delta_eve']:+,.1f} M".replace(",", " "),
             config.COL_UP if s["delta_eve"] >= 0 else config.COL_DOWN),
            (_L("Δ EVE / fonds propres", "Δ EVE / equity"), f"{s['eve_pct_equity']:+.1f}%",
             config.COL_DOWN if abs(s["eve_pct_equity"]) > 15 else config.COL_TEXT),
        ]
        y = rinner.y
        for label, val, col in rows:
            if label:
                widgets.draw_text(surf, label, (rinner.x, y), fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, str(val), (rinner.right, y), fonts.body(bold=True),
                                  col, align="right")
            y += 34
        widgets.draw_text_wrapped(
            surf, _L("Lecture : gap > 0 -> la banque GAGNE quand les taux montent "
            "(asset-sensitive) ; un duration gap positif fait perdre de la valeur "
            "économique des fonds propres quand les taux montent.",
            "Reading: gap > 0 -> the bank GAINS when rates rise "
            "(asset-sensitive); a positive duration gap loses economic value "
            "of equity when rates rise."),
            (rinner.x, y + 6), fonts.tiny(), config.COL_TEXT_DIM, rinner.w)
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", _L("choc de taux", "rate shock"))])
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
