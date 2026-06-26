"""
scene_examcert.py — Choix EXAMEN / CERTIFICATION.

Point d'entrée unique regroupant les deux voies d'évaluation : l'examen de
promotion (passer au grade suivant) et les certifications professionnelles
(CFA / FRM / CQF). Ouvert via EXAMCERT / le rail latéral « EXAM/CERTIF ».
"""
import pygame

from core import career as career_mod
from core import config
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets

CARD_KEYS = ["exam", "cert"]
_REQ_HINTS = {
    "Réputation": "Augmentez votre réputation via les missions, les deals et les certifications "
                  "(CFA/FRM/CQF réduisent aussi le seuil requis).",
    "Missions (ce grade)": "Terminez des missions (MISSIONS) — chaque mission complétée à ce grade compte.",
    "Deals conclus (ce grade)": "Concluez des deals via DEALS pour valider ce critère.",
    "Ancienneté (trimestres)": "Patientez : ce critère se remplit automatiquement avec le temps passé à ce grade.",
}


def _L(fr, en):
    return en if get_lang() == "en" else fr


class ExamCertScene(Scene):
    pageable = False

    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._card_rects = {}
        self.focus = 0   # index de la carte ayant le focus clavier

    def _activate(self, key):
        if key == "exam":
            self._go_exam()
        else:
            self.app.scenes.go("cert", return_to="terminal")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_LEFT):
                step = -1 if event.key == pygame.K_LEFT else 1
                self.focus = (self.focus + step) % len(CARD_KEYS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._activate(CARD_KEYS[self.focus])
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self._card_rects.items():
                if rect.collidepoint(event.pos):
                    self._activate(key)
                    return

    def _go_exam(self):
        p = self.app.gs.player
        if isinstance(p.eval_state, dict) and p.eval_state.get("mode") == "promotion" \
                and p.eval_state.get("items"):
            self.app.scenes.go("evaluation")
            return
        if not p.can_promote():
            self.msg = "Vous êtes au grade maximal : aucune promotion possible."
            return
        if not career_mod.promotion_ready(p):
            miss = ", ".join(career_mod.missing_criteria(p))
            self.msg = f"Critères de promotion non remplis : {miss}."
            return
        self.app.scenes.go("evaluation")

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, "EXAMEN / CERTIFICATION", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Passez l'examen pour évoluer en grade, ou une certification "
                                "pour booster votre carrière.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        self._card_rects = {}
        mp = pygame.mouse.get_pos()
        M = config.MARGIN
        top = config.content_top()
        colw = (config.SCREEN_WIDTH - 3 * M) // 2
        h = 280
        self._draw_exam_card(surf, pygame.Rect(M, top, colw, h), p, mp, self.focus == 0)
        self._draw_cert_card(surf, pygame.Rect(M * 2 + colw, top, colw, h), p, mp, self.focus == 1)

        if self.msg:
            widgets.draw_text(surf, self.msg, (40, top + h + 24), fonts.small(), config.COL_WARN)
        hints = [("TAB / ← →", _L("carte", "card")), (_L("ENTRÉE", "ENTER"), _L("ouvrir", "open"))]
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14), hints)
        self.back_btn.draw(surf)

    def _draw_exam_card(self, surf, rect, p, mp, focused):
        paused = isinstance(p.eval_state, dict) and p.eval_state.get("mode") == "promotion" \
            and p.eval_state.get("items")
        ready = p.can_promote() and career_mod.promotion_ready(p)
        accent = config.COL_CYAN if paused else (config.COL_UP if ready else config.COL_WARN)
        hover = rect.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL, rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_CYAN if focused else accent, rect, 3 if focused else 2,
                         border_radius=6)
        self._card_rects["exam"] = rect
        widgets.draw_text(surf, "EXAMEN DE PROMOTION", (rect.x + 20, rect.y + 18),
                          fonts.head(bold=True), config.COL_AMBER)
        if paused:
            idx = p.eval_state.get("idx", 0)
            total = len(p.eval_state.get("items", []))
            widgets.draw_text(surf, f"▮▮ Examen en pause — question {idx + 1}/{total}. Reprenez ci-dessous.",
                              (rect.x + 20, rect.y + 54), fonts.small(bold=True), config.COL_CYAN)
        else:
            widgets.draw_text(surf, "Réussir l'examen vous fait passer au grade suivant.",
                              (rect.x + 20, rect.y + 54), fonts.small(), config.COL_TEXT)
        if not p.can_promote():
            widgets.draw_text(surf, "Grade maximal atteint.", (rect.x + 20, rect.y + 84),
                              fonts.small(bold=True), config.COL_UP)
        else:
            y = rect.y + 84
            for r in career_mod.promotion_requirements(p):
                mark = "✓" if r["met"] else "○"
                col = config.COL_UP if r["met"] else config.COL_TEXT
                widgets.draw_text(surf, f"{mark} {r['label']}", (rect.x + 20, y), fonts.small(), col)
                widgets.draw_text(surf, f"{int(r['current'])}/{int(r['target'])}",
                                  (rect.right - 20, y), fonts.small(bold=True), col, align="right")
                hint = _REQ_HINTS.get(r["label"])
                if hint and pygame.Rect(rect.x + 20, y, rect.w - 40, 20).collidepoint(mp):
                    widgets.draw_tooltip(surf, hint, mp)
                y += 26
        label = "REPRENDRE L'EXAMEN" if paused else ("PASSER L'EXAMEN" if ready else "VOIR LA ROADMAP (CAREER)")
        widgets.draw_card_footer(surf, rect, label, accent, hover=hover)

    def _draw_cert_card(self, surf, rect, p, mp, focused):
        hover = rect.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL, rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_CYAN if focused else config.COL_PRESTIGE, rect,
                         3 if focused else 2, border_radius=6)
        self._card_rects["cert"] = rect
        widgets.draw_text(surf, "CERTIFICATIONS", (rect.x + 20, rect.y + 18),
                          fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "CFA / FRM / CQF — boostent réputation et promotions.",
                          (rect.x + 20, rect.y + 54), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"Voie actuelle : {p.track}", (rect.x + 20, rect.y + 84),
                          fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_card_footer(surf, rect, "VOIR LES CERTIFICATIONS", config.COL_PRESTIGE, hover=hover)
