"""
scene_dilemma.py — Écran de décision (dilemmes signature / éthiques / réglementaires).
Présente un scénario et des options aux conséquences chiffrées et visibles
(trésorerie, réputation, scrutin réglementaire), puis l'issue du choix.
"""
import pygame

from core import config
from core import dilemmas as D
from core.scene_manager import Scene
from ui import fonts, widgets

_CAT = {
    "ethique": ("ÉTHIQUE", config.COL_DOWN),
    "reglementaire": ("RÉGLEMENTAIRE", config.COL_WARN),
    "strategie": ("STRATÉGIE", config.COL_CYAN),
    "signature": ("DÉCISION SIGNATURE", config.COL_AMBER),
}


class DilemmaScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        p = self.app.gs.player
        self.dilemma = p.pending_dilemmas[0] if p.pending_dilemmas else None
        self.state = "decide"
        self.chosen = None
        self.option_rects = {}
        self.focus = 0   # index de l'option ayant le focus clavier
        self.continue_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 130, config.SCREEN_HEIGHT - 78, 260, 48),
            "RETOUR AU TERMINAL", config.COL_UP)

    def handle_event(self, event):
        if self.dilemma is None:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.app.scenes.go(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "decide":
                for i, rect in self.option_rects.items():
                    if rect.collidepoint(event.pos):
                        self._choose(i)
            elif self.state == "outcome" and self.continue_btn.rect.collidepoint(event.pos):
                self._leave()
        if event.type == pygame.KEYDOWN:
            if self.state == "outcome" and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self._leave()
            elif self.state == "decide":
                n = len(self.dilemma["options"])
                if event.key in (pygame.K_DOWN, pygame.K_TAB):
                    self.focus = (self.focus + 1) % n
                elif event.key == pygame.K_UP:
                    self.focus = (self.focus - 1) % n
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._choose(self.focus)
                elif event.key == pygame.K_ESCAPE:
                    self.app.scenes.go(self.return_to)

    def _choose(self, i):
        p = self.app.gs.player
        self.chosen = i
        self.applied = D.apply_choice(p, self.dilemma, i)
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        self.state = "outcome"

    def _leave(self):
        p = self.app.gs.player
        # une décision peut faire basculer en faillite
        if p.check_game_over():
            self.app.scenes.go("gameover")
        else:
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        self.continue_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        if self.dilemma is None:
            widgets.draw_text(surf, "Aucune décision en attente.", (40, 40),
                              fonts.head(bold=True), config.COL_TEXT_DIM)
            widgets.draw_text(surf, "ESC pour revenir.", (40, 90), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        d = self.dilemma
        label, col = _CAT.get(d["category"], ("DÉCISION", config.COL_AMBER))
        widgets.draw_text(surf, "DÉCISION", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_badge(surf, label, (config.SCREEN_WIDTH - 40, 30), col, align="right")

        # scénario
        panel = pygame.Rect(120, 100, config.SCREEN_WIDTH - 240, 150)
        inner = widgets.draw_panel(surf, panel, d["title"], col)
        widgets.draw_text_wrapped(surf, d["scenario"], (inner.x, inner.y),
                                  fonts.body(), config.COL_TEXT, inner.w, line_gap=6)

        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        if self.state == "decide":
            self._draw_options(surf, d, cur)
        else:
            self._draw_outcome(surf, d, cur)

    def _draw_options(self, surf, d, cur):
        self.option_rects = {}
        widgets.draw_text(surf, "Votre décision :", (120, 270), fonts.small(bold=True),
                          config.COL_TEXT_DIM)
        y = 300
        mp = pygame.mouse.get_pos()
        for i, o in enumerate(d["options"]):
            rect = pygame.Rect(120, y, config.SCREEN_WIDTH - 240, 72)
            self.option_rects[i] = rect
            hover = rect.collidepoint(mp)
            focused = (i == self.focus)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (hover or focused) else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_CYAN if (hover or focused) else config.COL_BORDER, rect,
                             3 if focused else (2 if hover else 1))
            widgets.draw_text(surf, f"{chr(65+i)}. {o['label']}", (rect.x + 16, rect.y + 12),
                              fonts.body(bold=True), config.COL_WHITE)
            # effets visibles
            parts = []
            if o["cash"]:
                parts.append(("cash " + ("+" if o["cash"] >= 0 else "") +
                              widgets.format_money(o["cash"], cur),
                              config.COL_UP if o["cash"] >= 0 else config.COL_DOWN))
            if o["rep"]:
                parts.append((f"réputation {o['rep']:+d}",
                              config.COL_UP if o["rep"] >= 0 else config.COL_DOWN))
            if o["heat"]:
                parts.append((f"scrutin {o['heat']:+d}",
                              config.COL_DOWN if o["heat"] > 0 else config.COL_UP))
            if not parts:
                parts.append(("aucun effet immédiat", config.COL_TEXT_DIM))
            x = rect.x + 16
            for text, c in parts:
                r = widgets.draw_text(surf, text, (x, rect.y + 44), fonts.small(bold=True), c)
                x = r.right + 20
            y += 82

    def _effect_parts(self, o, cur):
        parts = []
        if o.get("cash"):
            parts.append(("cash " + ("+" if o["cash"] >= 0 else "") + widgets.format_money(o["cash"], cur),
                          config.COL_UP if o["cash"] >= 0 else config.COL_DOWN))
        if o.get("rep"):
            parts.append((f"réputation {o['rep']:+d}", config.COL_UP if o["rep"] >= 0 else config.COL_DOWN))
        if o.get("heat"):
            parts.append((f"scrutin {o['heat']:+d}", config.COL_DOWN if o["heat"] > 0 else config.COL_UP))
        return parts

    def _draw_outcome(self, surf, d, cur):
        o = self.applied
        p = self.app.gs.player
        others = [opt for i, opt in enumerate(d["options"]) if i != self.chosen]
        panel = pygame.Rect(120, 290, config.SCREEN_WIDTH - 240, 230 + 22 * len(others))
        inner = widgets.draw_panel(surf, panel, "Conséquence", config.COL_CYAN)
        widgets.draw_text(surf, o["label"], (inner.x, inner.y), fonts.head(bold=True), config.COL_WHITE)
        widgets.draw_text_wrapped(surf, o["outcome"], (inner.x, inner.y + 36),
                                  fonts.body(), config.COL_TEXT, inner.w, line_gap=6)
        # récap des effets appliqués
        eff = self._effect_parts(o, cur)
        y = inner.y + 96
        x = inner.x
        for text, c in eff:
            r = widgets.draw_text(surf, text, (x, y), fonts.small(bold=True), c)
            x = r.right + 18
        y += 28
        # ce que vous avez écarté : comparaison avec les options non choisies, pour
        # que la décision raconte une mini-histoire ("j'ai préféré X plutôt que Y").
        if others:
            widgets.draw_text(surf, "Vous avez écarté :", (inner.x, y), fonts.small(bold=True),
                              config.COL_TEXT_DIM)
            y += 20
            for opt in others:
                x = inner.x
                r = widgets.draw_text(surf, f"· {opt['label']}", (x, y), fonts.small(), config.COL_TEXT_DIM)
                x = r.right + 14
                parts = self._effect_parts(opt, cur)
                if not parts:
                    widgets.draw_text(surf, "(aucun effet immédiat)", (x, y), fonts.tiny(), config.COL_TEXT_DIM)
                else:
                    for text, c in parts:
                        r = widgets.draw_text(surf, text, (x, y), fonts.tiny(), c)
                        x = r.right + 14
                y += 20
        widgets.draw_text(surf, f"Scrutin réglementaire actuel : {p.heat}/100",
                          (inner.x, inner.bottom - 28), fonts.small(),
                          config.COL_DOWN if p.heat >= 55 else config.COL_TEXT_DIM)
        self.continue_btn.draw(surf)
