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
from ui import fonts, keynav, widgets

_TOPIC_COL = {
    "Valorisation": config.COL_AMBER, "Risque": config.COL_DOWN,
    "Dérivés": config.COL_WARN, "Macro": config.COL_CYAN,
    "M&A": config.COL_UP, "Bloomberg": config.COL_PRESTIGE,
    "Taux": config.COL_CYAN, "Crédit": config.COL_DOWN, "Marché": config.COL_AMBER,
    "Performance": config.COL_UP, "Comportement": config.COL_WARN,
    "ESG": config.COL_UP, "Banque": config.COL_CYAN,
    # thèmes EN
    "Valuation": config.COL_AMBER, "Risk": config.COL_DOWN, "Derivatives": config.COL_WARN,
    "Rates": config.COL_CYAN, "Credit": config.COL_DOWN, "Market": config.COL_AMBER,
    "Banking": config.COL_CYAN,
}


class AcademyScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.sel = L.LESSONS[0]["id"]
        self._mark_read(self.sel)
        self.row_rects = {}
        self.scroll = 0          # défilement de la liste de leçons (px)
        self._max_scroll = 0
        self.cursor = 0          # curseur clavier dans la liste visible de leçons
        self._lesson_id_list = []  # ordre des leçons affichées (pour la nav clavier)
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button(
            (260, config.SCREEN_HEIGHT - 50, 180, 42), "TUTORIELS", config.COL_CYAN)

    def _mark_read(self, lesson_id):
        p = self.app.gs.player
        if lesson_id not in p.learned:
            p.learned.append(lesson_id)
            p.adjust_reputation(1, reason="Leçon apprise (Académie)")
            self.app.notify("Leçon apprise (+1 réputation)", "good")
            if len(p.learned) >= len(L.LESSONS):
                from core import badges
                for b in badges.check_new(p, self.app.market):
                    self.app.notify(f"✶ Badge : {badges.badge_name(b)}", "prestige")

    def _scroll_to_cursor(self):
        """Ajuste le scroll pour garder la leçon sélectionnée au clavier visible."""
        rect = self.row_rects.get(self._lesson_id_list[self.cursor]) if self._lesson_id_list else None
        if not rect:
            return
        if rect.top < 100:
            self.scroll = max(0, self.scroll - (100 - rect.top))
        elif rect.bottom > config.footer_y() - 8:
            self.scroll = min(self._max_scroll, self.scroll + (rect.bottom - (config.footer_y() - 8)))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.go(self.return_to)
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.cursor, activate = widgets.list_key_nav(
                    event, self.cursor, len(self._lesson_id_list))
                if self._lesson_id_list:
                    self._scroll_to_cursor()
                if activate and self._lesson_id_list:
                    lid = self._lesson_id_list[self.cursor]
                    self.sel = lid
                    self._mark_read(lid)
                return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", return_to="academy")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            self.scroll = max(0, self.scroll - 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            self.scroll = min(self._max_scroll, self.scroll + 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for lid, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    self.sel = lid
                    self._mark_read(lid)
                    if lid in self._lesson_id_list:
                        self.cursor = self._lesson_id_list.index(lid)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        from core.i18n import get_lang, t
        lang = get_lang()
        lessons_loc, topics_loc = L.localized(lang)
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, t("academy.title"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, t("academy.progress", n=len(p.learned), m=len(L.LESSONS)),
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        # liste à gauche, groupée par thème
        ph = config.footer_y() - 8 - 100
        listp = pygame.Rect(40, 100, 360, ph)
        linner = widgets.draw_panel(surf, listp, t("academy.program"), config.COL_CYAN)
        self.row_rects = {}
        self._lesson_id_list = []
        # liste défilante : on clippe au panneau et on décale de self.scroll
        prev_clip = surf.get_clip()
        surf.set_clip(linner)
        y = linner.y - self.scroll
        for topic in topics_loc:
            lessons_t = [x for x in lessons_loc if x["topic"] == topic]
            if not lessons_t:
                continue
            widgets.draw_text(surf, topic.upper(), (linner.x, y),
                              fonts.tiny(bold=True), _TOPIC_COL.get(topic, config.COL_TEXT))
            y += 18
            for lesson in lessons_t:
                rect = pygame.Rect(linner.x - 4, y - 2, linner.w + 8, 22)
                self.row_rects[lesson["id"]] = rect
                pos = len(self._lesson_id_list)
                self._lesson_id_list.append(lesson["id"])
                sel = (lesson["id"] == self.sel)
                read = lesson["id"] in p.learned
                if sel:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
                keynav.draw_focus_ring(surf, rect, pos == self.cursor)
                mark = "✓" if read else "•"
                col = config.COL_UP if read else config.COL_TEXT
                font = fonts.small(bold=sel)
                label = widgets.fit_text(f"{mark} {lesson['title']}", font, linner.w - 8)
                widgets.draw_text(surf, label, (linner.x + 6, y),
                                  font, col if not sel else config.COL_WHITE)
                y += 22
            y += 6
        surf.set_clip(prev_clip)
        self.cursor = min(self.cursor, len(self._lesson_id_list) - 1) if self._lesson_id_list else 0
        # hauteur totale du contenu -> borne de défilement
        content_h = (y + self.scroll) - linner.y
        self._max_scroll = max(0, content_h - linner.h)
        self.scroll = min(self.scroll, self._max_scroll)
        widgets.draw_scrollbar(surf, listp, linner, self.scroll, self._max_scroll, content_h)

        # lecture à droite
        readp = pygame.Rect(420, 100, config.SCREEN_WIDTH - 460, ph)
        rinner = widgets.draw_panel(surf, readp, t("academy.lesson"), config.COL_AMBER)
        lesson = L.get_localized(self.sel, lang)
        if lesson:
            tcol = _TOPIC_COL.get(lesson["topic"], config.COL_AMBER)
            widgets.draw_badge(surf, lesson["topic"], (rinner.x, rinner.y), tcol)
            widgets.draw_text(surf, lesson["title"], (rinner.x, rinner.y + 28),
                              fonts.head(bold=True), config.COL_WHITE)
            y = rinner.y + 64
            y += widgets.draw_text_wrapped(surf, lesson["body"], (rinner.x, y),
                                           fonts.body(), config.COL_TEXT, rinner.w, line_gap=5) + 14
            for label, key, col in [(t("academy.formula"), "formula", config.COL_CYAN),
                                    (t("academy.example"), "example", config.COL_TEXT),
                                    (t("academy.takeaway"), "takeaway", config.COL_UP)]:
                widgets.draw_text(surf, label, (rinner.x, y), fonts.tiny(bold=True), col)
                y += 18
                y += widgets.draw_text_wrapped(surf, lesson[key], (rinner.x, y),
                                               fonts.small(), config.COL_TEXT, rinner.w, line_gap=4) + 12

        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
