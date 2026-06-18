"""
scene_alm.py — Desk ALM : gestion actif-passif du banking book.

Le joueur règle les masses et durations de l'actif/passif, puis applique un choc
de taux pour voir l'impact sur la marge nette d'intérêt (NII) et sur la valeur
économique des fonds propres (ΔEVE). Outil d'analyse (sandbox). Ouvert via ALM.
"""
import pygame

from core import alm, config
from core.scene_manager import Scene
from ui import fonts, widgets

# (clé, libellé, pas, format)
FIELDS = [
    ("assets", "Actifs totaux (M)", 50.0, "{:.0f}"),
    ("liabilities", "Passifs totaux (M)", 50.0, "{:.0f}"),
    ("rsa", "Actifs sensibles 1 an (M)", 25.0, "{:.0f}"),
    ("rsl", "Passifs sensibles 1 an (M)", 25.0, "{:.0f}"),
    ("dur_a", "Duration actifs (ans)", 0.5, "{:.1f}"),
    ("dur_l", "Duration passifs (ans)", 0.5, "{:.1f}"),
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
                                       "📘 TUTO", config.COL_CYAN)

    def _adj(self, key, delta):
        lo = 0.0
        self.state[key] = max(lo, round(self.state[key] + delta, 2))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
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
        widgets.draw_text(surf, "DESK ALM — GESTION ACTIF-PASSIF", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Banking book : risque de taux & de liquidité. Réglez le bilan, "
                                "appliquez un choc de taux, lisez NII et ΔEVE.",
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)
        ph = config.footer_y() - 8 - 100

        # ----- réglage du bilan (gauche) -----
        panel = pygame.Rect(40, 100, 560, ph)
        inner = widgets.draw_panel(surf, panel, "Bilan (M)", config.COL_CYAN)
        self._field_btns = {}
        y = inner.y
        for key, label, step, fmt in FIELDS:
            widgets.draw_text(surf, label, (inner.x, y), fonts.small(), config.COL_TEXT)
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
        widgets.draw_text(surf, "Choc de taux :", (inner.x, y), fonts.small(bold=True), config.COL_TEXT_DIM)
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
        rinner = widgets.draw_panel(surf, rp, "Diagnostic ALM", config.COL_AMBER)
        gcol = config.COL_UP if s["repricing_gap"] >= 0 else config.COL_DOWN
        rows = [
            ("Profil", s["profile"], config.COL_WHITE),
            ("Capitaux propres", f"{s['equity']:,.0f} M".replace(",", " "), config.COL_WHITE),
            ("Repricing gap (1 an)", f"{s['repricing_gap']:+,.0f} M".replace(",", " "), gcol),
            ("Duration gap", f"{s['duration_gap']:+.2f} ans",
             config.COL_DOWN if s["duration_gap"] > 0 else config.COL_UP),
            ("", "", config.COL_TEXT),
            (f"Δ NII (choc {self.dy*10000:+.0f} bps)", f"{s['delta_nii']:+,.1f} M".replace(",", " "),
             config.COL_UP if s["delta_nii"] >= 0 else config.COL_DOWN),
            (f"Δ EVE (choc {self.dy*10000:+.0f} bps)", f"{s['delta_eve']:+,.1f} M".replace(",", " "),
             config.COL_UP if s["delta_eve"] >= 0 else config.COL_DOWN),
            ("Δ EVE / fonds propres", f"{s['eve_pct_equity']:+.1f}%",
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
            surf, "Lecture : gap > 0 -> la banque GAGNE quand les taux montent "
            "(asset-sensitive) ; un duration gap positif fait perdre de la valeur "
            "économique des fonds propres quand les taux montent.",
            (rinner.x, y + 6), fonts.tiny(), config.COL_TEXT_DIM, rinner.w)
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
