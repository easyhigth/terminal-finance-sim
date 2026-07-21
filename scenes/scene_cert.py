"""
scene_cert.py — Certifications professionnelles (CFA / FRM / CQF).
Liste les programmes, leur statut, et permet de s'inscrire à l'examen suivant
(frais débités, puis examen en mode certification). Une certification complète
liée à votre voie booste la réputation et accélère les promotions.
"""
import pygame

from core import certifications as C
from core import config
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, keynav, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


class CertScene(Scene):
    pageable = False

    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.btn_rects = {}
        self.cursor = 0  # curseur clavier dans la liste des programmes
        self._pid_list = list(C.PROGRAMS.keys())
        self.back_btn = widgets.Button(config.back_button_rect(200),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.back(self.return_to)
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.cursor, activate = widgets.list_key_nav(
                    event, self.cursor, len(self._pid_list))
                if activate and self._pid_list:
                    self._attempt(self._pid_list[self.cursor])
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for pid, rect in self.btn_rects.items():
                if rect.collidepoint(event.pos):
                    self._attempt(pid)
                    if pid in self._pid_list:
                        self.cursor = self._pid_list.index(pid)

    def _attempt(self, pid):
        p = self.app.gs.player
        code, fee, tier = C.can_attempt(p, pid)
        if code == "done":
            self.msg = _L(f"{C.PROGRAMS[pid]['name']} déjà entièrement obtenu.", f"{C.PROGRAMS[pid]['name']} already fully obtained.")
            return
        if code == "grade":
            self.msg = _L(f"{C.PROGRAMS[pid]['name']} : grade insuffisant (min. {config.GRADES[fee]}).", f"{C.PROGRAMS[pid]['name']}: insufficient grade (min. {config.GRADES[fee]}).")
            return
        if code == "cash":
            self.msg = _L(f"Frais d'inscription {widgets.format_money(fee, self._cur())} : trésorerie insuffisante.", f"Registration fee {widgets.format_money(fee, self._cur())}: insufficient cash.")
            return
        started = C.pay_and_start(p, pid)
        if started:
            tier, level = started
            self.app.scenes.go("evaluation", mode="cert", program=pid,
                               tier=tier, level=level, return_to="cert")

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cur = self._cur()
        widgets.draw_text(surf, _L("CERTIFICATIONS", "CERTIFICATIONS"), (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L("Une certification liée à votre voie booste la réputation "
                                "et accélère l'accès aux hauts postes.",
                                "A certification tied to your track boosts reputation "
                                "and speeds access to senior roles."),
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        self.btn_rects = {}
        self._pid_list = list(C.PROGRAMS.keys())
        self.cursor = min(self.cursor, len(self._pid_list) - 1) if self._pid_list else 0
        mp = pygame.mouse.get_pos()
        y = 116
        cw = config.SCREEN_WIDTH - 80
        for pos, (pid, prog) in enumerate(C.PROGRAMS.items()):
            rect = pygame.Rect(40, y, cw, 120)
            relevant = (prog["track"] == p.track)
            accent = config.COL_PRESTIGE if relevant else config.COL_BORDER
            pygame.draw.rect(surf, config.COL_PANEL, rect)
            pygame.draw.rect(surf, accent, rect, 2 if relevant else 1)
            keynav.draw_focus_ring(surf, rect, pos == self.cursor)
            if relevant:
                pygame.draw.rect(surf, config.COL_PRESTIGE, (rect.x, rect.y, 3, rect.h))
            widgets.draw_text(surf, f"{prog['name']} — {prog['full']}", (rect.x+16, rect.y+12),
                              fonts.head(bold=True), config.COL_AMBER)
            if relevant:
                widgets.draw_badge(surf, _L("VOIE ", "TRACK ") + p.track, (rect.x+16, rect.y+44),
                                   config.COL_PRESTIGE)
            widgets.draw_text(surf, C.desc_for(pid), (rect.x+16, rect.y+72),
                              fonts.small(), config.COL_TEXT)
            lvl = C.level(p, pid)
            status_line = _L(f"Statut : {C.status_label(p, pid)}  ·  "
                          f"niveaux {prog['levels']}  ·  voie {prog['track']}",
                          f"Status: {C.status_label(p, pid)}  ·  "
                          f"levels {prog['levels']}  ·  track {prog['track']}")
            if lvl < len(prog["fee"]):
                remaining = sum(prog["fee"][lvl:])
                status_line += _L(f"  ·  frais restants : {widgets.format_money(remaining, cur)} "
                                f"({prog['levels'] - lvl} niveau(x), débités un par un à "
                                f"l'inscription)",
                                f"  ·  remaining fees: {widgets.format_money(remaining, cur)} "
                                f"({prog['levels'] - lvl} level(s), charged one by one at "
                                f"registration)")
            widgets.draw_text(surf, status_line,
                              (rect.x+16, rect.y+94), fonts.small(), config.COL_TEXT_DIM)
            # bouton d'inscription, ancré en bas-droite de la carte (largeur fixe)
            code, fee, _ = C.can_attempt(p, pid)
            if code == "done":
                label, bcol = _L("OBTENU ✓", "OBTAINED ✓"), config.COL_UP
            elif code == "grade":
                label, bcol = _L(f"Grade min. {prog['min_grade']+1}*", f"Min. grade {prog['min_grade']+1}*"), config.COL_TEXT_DIM
            else:
                label, bcol = _L(f"PASSER NIV. {lvl+1} — {widgets.format_money(prog['fee'][lvl], cur)}", f"TAKE LVL. {lvl+1} — {widgets.format_money(prog['fee'][lvl], cur)}"), config.COL_UP
            footer_rect = pygame.Rect(rect.right - 260, rect.y, 244, rect.h)
            hover = pygame.Rect(rect.right - 260, rect.bottom - 16 - 36,
                                244, 36).collidepoint(mp)
            br = widgets.draw_card_footer(surf, footer_rect, label, bcol, hover=hover)
            self.btn_rects[pid] = br
            y += 132

        if self.msg:
            widgets.draw_text(surf, self.msg, (40, y+4), fonts.small(), config.COL_WARN)
        self.back_btn.draw(surf)
