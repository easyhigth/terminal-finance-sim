"""
app_review.py — Application « Revue de performance » du bureau (NATIVE).

Migration de `scenes/scene_review.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — même principe que Décision/Portefeuille/Marché
avant elle. Toutes les positions sont relatives au `rect` de la fenêtre
plutôt qu'à `config.SCREEN_WIDTH`/`config.SCREEN_HEIGHT`. La scène plein
écran reste enregistrée (fallback/tests) ; l'ouverture EN FENÊTRE de "review"
est redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import config, i18n
from core import review as R
from ui import fonts, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


_CHOICES = [
    ("accept", ("Accepter le bonus standard", "Accept the standard bonus")),
    ("negotiate_up", ("Négocier à la hausse", "Negotiate upward")),
    ("ask_fixed", ("Demander une augmentation fixe", "Ask for a fixed raise")),
]


class ReviewApp(DesktopApp):
    title = "Revue de performance"
    icon_kind = "review"
    default_size = (860, 560)
    min_size = (540, 400)

    def on_open(self):
        p = self.app.gs.player
        self.offer = p.pending_review
        self.state = "decide"
        self.result = None
        self.option_rects = {}
        self.focus = 0
        self._continue_rect = None

    def _choose(self, i):
        p = self.app.gs.player
        choice_id = _CHOICES[i][0]
        self.result = R.negotiate(p, choice_id)
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
        if self.offer is None:
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
                n = len(_CHOICES)
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
        if self.offer is None:
            widgets.draw_text(surf, _L("Aucune revue de performance en attente.", "No pending performance review."),
                              (rect.x + 20, rect.y + 20), fonts.head(bold=True), config.COL_TEXT_DIM)
            return
        widgets.draw_text(surf, _L("REVUE DE PERFORMANCE", "PERFORMANCE REVIEW"), (rect.x + 20, rect.y + 12),
                          fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_badge(surf, _L("ANNUELLE", "ANNUAL"), (rect.right - 20, rect.y + 18), config.COL_CYAN, align="right")

        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        panel = pygame.Rect(rect.x + 20, rect.y + 50, rect.w - 40, 130)
        inner = widgets.draw_panel(surf, panel, _L("Bilan annuel", "Annual review"), config.COL_CYAN)
        o = self.offer
        lines = _L(
            f"Réputation actuelle : {o['reputation']}/100\n"
            f"Missions réalisées ce grade : {o['grade_missions']}\n"
            f"P&L réalisé récent : {widgets.format_money(o['realized_pnl'], cur)}\n"
            f"Bonus standard proposé : {widgets.format_money(o['standard_bonus'], cur)}",
            f"Current reputation: {o['reputation']}/100\n"
            f"Missions completed this grade: {o['grade_missions']}\n"
            f"Recent realized P&L: {widgets.format_money(o['realized_pnl'], cur)}\n"
            f"Standard bonus offered: {widgets.format_money(o['standard_bonus'], cur)}"
        )
        widgets.draw_text_wrapped(surf, lines, (inner.x, inner.y), fonts.small(),
                                  config.COL_TEXT, inner.w, line_gap=5)

        content_top = panel.bottom + 20
        if self.state == "decide":
            self._draw_options(surf, rect, cur, content_top)
        else:
            self._draw_outcome(surf, rect, cur, content_top)

    def _draw_options(self, surf, rect, cur, top):
        self.option_rects = {}
        widgets.draw_text(surf, _L("Votre réponse :", "Your response:"), (rect.x + 20, top), fonts.small(bold=True),
                          config.COL_TEXT_DIM)
        y = top + 26
        mp = pygame.mouse.get_pos()
        opt_h = 56
        for i, (_, labelpair) in enumerate(_CHOICES):
            label = _L(*labelpair)
            option_rect = pygame.Rect(rect.x + 20, y, rect.w - 40, opt_h)
            if option_rect.bottom > rect.bottom - 12:
                break
            self.option_rects[i] = option_rect
            hover = option_rect.collidepoint(mp)
            focused = (i == self.focus)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (hover or focused) else config.COL_PANEL, option_rect)
            pygame.draw.rect(surf, config.COL_CYAN if (hover or focused) else config.COL_AMBER, option_rect,
                             3 if focused else (2 if hover else 1))
            widgets.draw_text(surf, f"{chr(65+i)}. {label}", (option_rect.x + 14, option_rect.y + 16),
                              fonts.body(bold=True), config.COL_WHITE)
            y += opt_h + 10

    def _draw_outcome(self, surf, rect, cur, top):
        r = self.result
        panel_h = min(rect.bottom - top - 60, 220)
        panel = pygame.Rect(rect.x + 20, top, rect.w - 40, panel_h)
        inner = widgets.draw_panel(surf, panel, _L("Issue de la négociation", "Negotiation outcome"), config.COL_CYAN)
        widgets.draw_text_wrapped(surf, r.get("message", ""), (inner.x, inner.y),
                                  fonts.small(), config.COL_TEXT, inner.w, line_gap=5)
        eff = []
        bonus_paid = r.get("bonus_paid", 0.0)
        if bonus_paid:
            eff.append((f"bonus +{widgets.format_money(bonus_paid, cur)}", config.COL_UP))
        rep_delta = r.get("rep_delta", 0)
        if rep_delta:
            eff.append((_L(f"réputation {rep_delta:+d}", f"reputation {rep_delta:+d}"),
                        config.COL_UP if rep_delta >= 0 else config.COL_DOWN))
        x = inner.x
        for text, c in eff:
            rct = widgets.draw_text(surf, text, (x, inner.bottom - 30), fonts.small(bold=True), c)
            x = rct.right + 20
        self._continue_rect = pygame.Rect(rect.centerx - 110, rect.bottom - 46, 220, 36)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._continue_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._continue_rect, 2, border_radius=4)
        widgets.draw_text(surf, _L("CONTINUER", "CONTINUE"), self._continue_rect.center, fonts.small(bold=True),
                          config.COL_UP, align="center")
