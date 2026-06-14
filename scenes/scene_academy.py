"""
scene_academy.py — Académie : apprendre la finance.
Liste des leçons par thème à gauche, lecture détaillée à droite (explication,
formule, exemple chiffré, à retenir). Lire une leçon la marque comme apprise
(+1 réputation la 1ʳᵉ fois) ; tout lire débloque un badge. Ouvert via LEARN.
"""
import pygame
from core import config
from core.scene_manager import Scene
from data import lessons as L
from ui import fonts, widgets

_TOPIC_COL = {
    "Valorisation": config.COL_AMBER, "Risque": config.COL_DOWN,
    "Dérivés": config.COL_WARN, "Macro": config.COL_CYAN,
    "M&A": config.COL_UP, "Bloomberg": config.COL_PRESTIGE,
    "Taux": config.COL_CYAN, "Crédit": config.COL_DOWN, "Marché": config.COL_AMBER,
    "Performance": config.COL_UP, "Comportement": config.COL_WARN,
    "ESG": config.COL_UP, "Banque": config.COL_CYAN,
}


class AcademyScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.sel = L.LESSONS[0]["id"]
        self._mark_read(self.sel)
        self.row_rects = {}
        self.scroll = 0          # défilement de la liste de leçons (px)
        self._max_scroll = 0
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _mark_read(self, lesson_id):
        p = self.app.gs.player
        if lesson_id not in p.learned:
            p.learned.append(lesson_id)
            p.adjust_reputation(1)
            self.app.notify("Leçon apprise (+1 réputation)", "good")
            if len(p.learned) >= len(L.LESSONS):
                from core import badges
                for b in badges.check_new(p, self.app.market):
                    self.app.notify(f"🏅 Badge : {b['name']}", "prestige")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            self.scroll = max(0, self.scroll - 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            self.scroll = min(self._max_scroll, self.scroll + 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for lid, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    self.sel = lid
                    self._mark_read(lid)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, "ACADÉMIE DE FINANCE", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{len(p.learned)}/{len(L.LESSONS)} leçons lues · "
                                "cliquez une leçon pour l'étudier",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        # liste à gauche, groupée par thème
        ph = config.footer_y() - 8 - 100
        listp = pygame.Rect(40, 100, 360, ph)
        linner = widgets.draw_panel(surf, listp, "Programme", config.COL_CYAN)
        self.row_rects = {}
        # liste défilante : on clippe au panneau et on décale de self.scroll
        prev_clip = surf.get_clip()
        surf.set_clip(linner)
        y = linner.y - self.scroll
        for topic in L.TOPICS:
            lessons_t = [x for x in L.LESSONS if x["topic"] == topic]
            if not lessons_t:
                continue
            widgets.draw_text(surf, topic.upper(), (linner.x, y),
                              fonts.tiny(bold=True), _TOPIC_COL.get(topic, config.COL_TEXT))
            y += 18
            for lesson in lessons_t:
                rect = pygame.Rect(linner.x - 4, y - 2, linner.w + 8, 22)
                self.row_rects[lesson["id"]] = rect
                sel = (lesson["id"] == self.sel)
                read = lesson["id"] in p.learned
                if sel:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
                mark = "✓" if read else "•"
                col = config.COL_UP if read else config.COL_TEXT
                widgets.draw_text(surf, f"{mark} {lesson['title']}", (linner.x + 6, y),
                                  fonts.small(bold=sel), col if not sel else config.COL_WHITE)
                y += 22
            y += 6
        surf.set_clip(prev_clip)
        # hauteur totale du contenu -> borne de défilement
        content_h = (y + self.scroll) - linner.y
        self._max_scroll = max(0, content_h - linner.h)
        self.scroll = min(self.scroll, self._max_scroll)

        # lecture à droite
        readp = pygame.Rect(420, 100, config.SCREEN_WIDTH - 460, ph)
        rinner = widgets.draw_panel(surf, readp, "Leçon", config.COL_AMBER)
        lesson = L.get(self.sel)
        if lesson:
            tcol = _TOPIC_COL.get(lesson["topic"], config.COL_AMBER)
            widgets.draw_badge(surf, lesson["topic"], (rinner.x, rinner.y), tcol)
            widgets.draw_text(surf, lesson["title"], (rinner.x, rinner.y + 28),
                              fonts.head(bold=True), config.COL_WHITE)
            y = rinner.y + 64
            y += widgets.draw_text_wrapped(surf, lesson["body"], (rinner.x, y),
                                           fonts.body(), config.COL_TEXT, rinner.w, line_gap=5) + 14
            for label, key, col in [("FORMULE", "formula", config.COL_CYAN),
                                    ("EXEMPLE", "example", config.COL_TEXT),
                                    ("À RETENIR", "takeaway", config.COL_UP)]:
                widgets.draw_text(surf, label, (rinner.x, y), fonts.tiny(bold=True), col)
                y += 18
                y += widgets.draw_text_wrapped(surf, lesson[key], (rinner.x, y),
                                               fonts.small(), config.COL_TEXT, rinner.w, line_gap=4) + 12

        self.back_btn.draw(surf)
