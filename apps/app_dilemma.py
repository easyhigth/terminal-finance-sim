"""
app_dilemma.py — Application « Décision » du bureau (NATIVE).

Migration de `scenes/scene_dilemma.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — même principe que Portefeuille/Marché avant elle.
Toutes les positions sont désormais relatives au `rect` de la fenêtre plutôt
qu'à `config.SCREEN_WIDTH`/`config.SCREEN_HEIGHT`. La scène plein écran reste
enregistrée (fallback/tests) ; l'ouverture EN FENÊTRE de "dilemma" est
redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import dilemmas as D
from ui import fonts, widgets

_CAT = {
    "ethique": ("ÉTHIQUE", config.COL_DOWN),
    "reglementaire": ("RÉGLEMENTAIRE", config.COL_WARN),
    "strategie": ("STRATÉGIE", config.COL_CYAN),
    "signature": ("DÉCISION SIGNATURE", config.COL_AMBER),
}


class DilemmaApp(DesktopApp):
    title = "Décision"
    icon_kind = "decide"
    default_size = (900, 620)
    min_size = (560, 420)

    def on_open(self):
        p = self.app.gs.player
        self.dilemma = p.pending_dilemmas[0] if p.pending_dilemmas else None
        self.state = "decide"
        self.chosen = None
        self.applied = None
        self.option_rects = {}
        self.focus = 0
        self._continue_rect = None

    def _choose(self, i):
        p = self.app.gs.player
        self.chosen = i
        self.applied = D.apply_choice(p, self.dilemma, i)
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        self.state = "outcome"

    def _leave(self):
        p = self.app.gs.player
        if p.check_game_over():
            self.app.scenes.go("gameover")
            return
        if self.desktop is not None:
            w = next((w for w in self.desktop.wm.windows if w.app_obj is self), None)
            if w is not None:
                self.desktop.wm.close(w)

    def handle_event(self, event, rect):
        if self.dilemma is None:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "decide":
                for i, r in self.option_rects.items():
                    if r.collidepoint(event.pos):
                        self._choose(i)
                        return True
            elif self.state == "outcome" and self._continue_rect \
                    and self._continue_rect.collidepoint(event.pos):
                self._leave()
                return True
        if event.type == pygame.KEYDOWN:
            if self.state == "outcome" and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self._leave()
                return True
            if self.state == "decide":
                n = len(self.dilemma["options"])
                if event.key in (pygame.K_DOWN, pygame.K_TAB):
                    self.focus = (self.focus + 1) % n
                    return True
                if event.key == pygame.K_UP:
                    self.focus = (self.focus - 1) % n
                    return True
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._choose(self.focus)
                    return True
        return False

    def update(self, dt):
        pass

    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        if self.dilemma is None:
            widgets.draw_text(surf, "Aucune décision en attente.", (rect.x + 20, rect.y + 20),
                              fonts.head(bold=True), config.COL_TEXT_DIM)
            return
        d = self.dilemma
        label, col = _CAT.get(d["category"], ("DÉCISION", config.COL_AMBER))
        widgets.draw_text(surf, "DÉCISION", (rect.x + 20, rect.y + 12), fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_badge(surf, label, (rect.right - 20, rect.y + 18), col, align="right")

        panel = pygame.Rect(rect.x + 20, rect.y + 50, rect.w - 40, 140)
        inner = widgets.draw_panel(surf, panel, d["title"], col)
        widgets.draw_text_wrapped(surf, d["scenario"], (inner.x, inner.y),
                                  fonts.body(), config.COL_TEXT, inner.w, line_gap=6)

        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        content_top = panel.bottom + 20
        if self.state == "decide":
            self._draw_options(surf, rect, d, cur, content_top)
        else:
            self._draw_outcome(surf, rect, d, cur, content_top)

    def _draw_options(self, surf, rect, d, cur, top):
        self.option_rects = {}
        widgets.draw_text(surf, "Votre décision :", (rect.x + 20, top), fonts.small(bold=True),
                          config.COL_TEXT_DIM)
        y = top + 26
        mp = pygame.mouse.get_pos()
        opt_h = 68
        for i, o in enumerate(d["options"]):
            option_rect = pygame.Rect(rect.x + 20, y, rect.w - 40, opt_h)
            if option_rect.bottom > rect.bottom - 12:
                break
            self.option_rects[i] = option_rect
            hover = option_rect.collidepoint(mp)
            focused = (i == self.focus)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (hover or focused) else config.COL_PANEL, option_rect)
            pygame.draw.rect(surf, config.COL_CYAN if (hover or focused) else config.COL_AMBER, option_rect,
                             3 if focused else (2 if hover else 1))
            widgets.draw_text(surf, f"{chr(65+i)}. {o['label']}", (option_rect.x + 14, option_rect.y + 10),
                              fonts.body(bold=True), config.COL_WHITE)
            parts = self._effect_parts(o, cur)
            x = option_rect.x + 14
            for text, c in parts:
                r = widgets.draw_text(surf, text, (x, option_rect.y + 40), fonts.tiny(bold=True), c)
                x = r.right + 16
            y += opt_h + 10

    def _effect_parts(self, o, cur):
        parts = []
        if o.get("cash"):
            parts.append(("cash " + ("+" if o["cash"] >= 0 else "") + widgets.format_money(o["cash"], cur),
                          config.COL_UP if o["cash"] >= 0 else config.COL_DOWN))
        if o.get("rep"):
            parts.append((f"réputation {o['rep']:+d}", config.COL_UP if o["rep"] >= 0 else config.COL_DOWN))
        if o.get("heat"):
            parts.append((f"scrutin {o['heat']:+d}", config.COL_DOWN if o["heat"] > 0 else config.COL_UP))
        if not parts:
            parts.append(("aucun effet immédiat", config.COL_TEXT_DIM))
        return parts

    def _objective_impact_lines(self, p):
        from core import career
        lines = []
        for o in p.objectives:
            if o["kind"] not in ("cash", "reputation"):
                continue
            cur_v, target, ok = career.objective_progress(p, o)
            mark = "✓" if ok else "→"
            lines.append(f"{mark} {career.objective_label(p, o)}")
        return lines

    def _draw_outcome(self, surf, rect, d, cur, top):
        o = self.applied
        p = self.app.gs.player
        others = [opt for i, opt in enumerate(d["options"]) if i != self.chosen]
        impact = self._objective_impact_lines(p)
        panel_h = min(rect.bottom - top - 60, 320)
        panel = pygame.Rect(rect.x + 20, top, rect.w - 40, panel_h)
        inner = widgets.draw_panel(surf, panel, "Conséquence", config.COL_CYAN)
        widgets.draw_text(surf, o["label"], (inner.x, inner.y), fonts.body(bold=True), config.COL_WHITE)
        widgets.draw_text_wrapped(surf, o["outcome"], (inner.x, inner.y + 30),
                                  fonts.small(), config.COL_TEXT, inner.w, line_gap=4)
        eff = self._effect_parts(o, cur)
        y = inner.y + 80
        x = inner.x
        for text, c in eff:
            r = widgets.draw_text(surf, text, (x, y), fonts.small(bold=True), c)
            x = r.right + 16
        y += 24
        if impact:
            for line in impact:
                if y > inner.bottom - 20:
                    break
                widgets.draw_text(surf, line, (inner.x, y), fonts.tiny(), config.COL_CYAN)
                y += 16
            y += 4
        if others and y < inner.bottom - 20:
            widgets.draw_text(surf, "Vous avez écarté :", (inner.x, y), fonts.small(bold=True),
                              config.COL_TEXT_DIM)
            y += 18
            for opt in others:
                if y > inner.bottom - 4:
                    break
                x = inner.x
                r = widgets.draw_text(surf, f"· {opt['label']}", (x, y), fonts.tiny(), config.COL_TEXT_DIM)
                x = r.right + 12
                parts = self._effect_parts(opt, cur)
                for text, c in parts:
                    r = widgets.draw_text(surf, text, (x, y), fonts.tiny(), c)
                    x = r.right + 12
                y += 17
        widgets.draw_text(surf, f"Scrutin réglementaire actuel : {p.heat}/100",
                          (rect.x + 20, panel.bottom + 8), fonts.small(),
                          config.COL_DOWN if p.heat >= 55 else config.COL_TEXT_DIM)
        self._continue_rect = pygame.Rect(rect.centerx - 110, rect.bottom - 46, 220, 36)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._continue_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._continue_rect, 2, border_radius=4)
        widgets.draw_text(surf, "CONTINUER", self._continue_rect.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
