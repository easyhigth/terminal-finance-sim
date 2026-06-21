"""
scene_deal.py — Mini-jeu de résolution d'un deal.

Au lieu d'un tirage au sort, le joueur prend une vraie décision financière liée
à la voie du deal (cf. core/deal_game). La qualité du choix (good/ok/bad) donne
un succès plein, partiel ou un échec, et module la récompense.
"""
import random

import pygame

from core import career, config, deal_game
from core import deals as deals_mod
from core.scene_manager import Scene
from ui import fonts, widgets


class DealScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.deal_id = kwargs.get("deal_id")
        p = self.app.gs.player
        deal = deals_mod.find_deal(p, self.deal_id) if self.deal_id is not None else None
        self.challenge = deal_game.make_challenge(deal, random) if deal else None
        self.deal = deal
        self.state = "question"      # question -> result
        self.chosen = None
        self.result = None
        self._choice_rects = {}
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        fy = config.SCREEN_HEIGHT - 56
        self.continue_btn = widgets.Button((config.SCREEN_WIDTH // 2 - 130, fy, 260, 44),
                                           "RETOUR AU TERMINAL", config.COL_UP)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._leave()
        if self.state == "question" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in self._choice_rects.items():
                if rect.collidepoint(event.pos):
                    self._choose(i)
        if self.state == "result" and self.continue_btn.handle(event):
            self._leave()
        if self.back_btn.handle(event):
            self._leave()

    def _choose(self, i):
        ch = self.challenge["choices"][i]
        self.chosen = i
        self.result = deals_mod.apply_outcome(self.app.gs.player, self.deal_id, ch["quality"])
        self.state = "result"
        # traiter un deal prend du temps : le terminal avancera d'un tour au retour
        self.app.advance_on_return = 1
        if self.result:
            p = self.app.gs.player
            cur = config.CONTINENTS[p.continent]["currency"]
            cash_txt = widgets.format_money(abs(self.result["cash_delta"]), cur)
            rep = self.result["rep_delta"]
            outcome = self.result["outcome"]
            if outcome == "success":
                self.app.notify(f"Deal conclu : {self.deal['title']} "
                                 f"(+{cash_txt}, +{rep} rép.)", "good")
                career.log(p, "deal", f"Deal #{self.deal_id} conclu ({ch['text']}) : "
                                       f"+{cash_txt}, +{rep} réputation.")
            elif outcome == "partial":
                self.app.notify(f"Succès partiel : {self.deal['title']} "
                                 f"(+{cash_txt}, +{rep} rép.)", "warn")
                career.log(p, "deal", f"Deal #{self.deal_id} en demi-teinte ({ch['text']}) : "
                                       f"+{cash_txt}, +{rep} réputation (récompense réduite, "
                                       f"décision sous-optimale).")
            else:
                self.app.notify(f"Deal échoué : {self.deal['title']} "
                                 f"(-{cash_txt}, {rep} rép.)", "bad")
                career.log(p, "deal", f"Deal #{self.deal_id} échoué ({ch['text']}) : "
                                       f"-{cash_txt}, {rep} réputation.")
        if not self.app.gs.player.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    def _leave(self):
        if self.app.gs.player.check_game_over():
            self.app.scenes.go("gameover")
        else:
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.continue_btn.update(mp, dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "RÉSOLUTION DE DEAL", (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self.challenge:
            widgets.draw_text(surf, "Deal introuvable.", (42, 90), fonts.body(), config.COL_DOWN)
            self.back_btn.draw(surf)
            return
        d = self.deal
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        widgets.draw_text(surf, f"#{d['id']} {d['title']}  [{d['kind']}]  ·  "
                                f"gain {widgets.format_money(d['reward_cash'], cur)}",
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        panel = pygame.Rect(120, 120, config.SCREEN_WIDTH - 240, config.footer_y() - 150)
        inner = widgets.draw_panel(surf, panel, "Décision", config.COL_CYAN)
        widgets.draw_text_wrapped(surf, self.challenge["context"], (inner.x, inner.y),
                                  fonts.small(), config.COL_TEXT_DIM, inner.w)
        widgets.draw_text_wrapped(surf, self.challenge["prompt"], (inner.x, inner.y + 40),
                                  fonts.head(), config.COL_WHITE, inner.w)

        self._choice_rects = {}
        y = inner.y + 96
        for i, ch in enumerate(self.challenge["choices"]):
            rect = pygame.Rect(inner.x, y, inner.w, 46)
            self._choice_rects[i] = rect
            hover = rect.collidepoint(pygame.mouse.get_pos()) and self.state == "question"
            border = config.COL_CYAN if hover else config.COL_AMBER
            fill = config.COL_PANEL_HEAD if hover else config.COL_PANEL
            # en résultat : surligner le choix retenu (vert/orange/rouge)
            if self.state == "result" and i == self.chosen:
                q = ch["quality"]
                border = (config.COL_UP if q == "good" else
                          config.COL_WARN if q == "ok" else config.COL_DOWN)
            pygame.draw.rect(surf, fill, rect, border_radius=4)
            pygame.draw.rect(surf, border, rect, 2, border_radius=4)
            widgets.draw_text(surf, f"{chr(65+i)}. {ch['text']}", (rect.x + 14, rect.y + 13),
                              fonts.small(bold=True), config.COL_TEXT)
            # en résultat : ce que les options écartées auraient donné, pour comparer
            # avec le choix retenu plutôt que se demander "et si j'avais pris l'autre".
            if self.state == "result" and i != self.chosen:
                qlabel = {"good": "aurait donné : succès plein", "ok": "aurait donné : succès partiel",
                         "bad": "aurait donné : échec"}[ch["quality"]]
                qcol = {"good": config.COL_UP, "ok": config.COL_WARN, "bad": config.COL_DOWN}[ch["quality"]]
                widgets.draw_text(surf, qlabel, (rect.right - 12, rect.y + 13), fonts.tiny(),
                                  qcol, align="right")
            y += 56

        if self.state == "result" and self.result:
            oc = self.result["outcome"]
            ocol = (config.COL_UP if oc == "success" else
                    config.COL_WARN if oc == "partial" else config.COL_DOWN)
            label = {"success": "DEAL CONCLU (succès plein)",
                     "partial": "SUCCÈS PARTIEL",
                     "fail": "DEAL ÉCHOUÉ"}[oc]
            widgets.draw_text(surf, label, (inner.x, y + 6), fonts.head(bold=True), ocol)
            widgets.draw_text_wrapped(surf, self.challenge["expl"], (inner.x, y + 40),
                                      fonts.small(), config.COL_TEXT, inner.w)
            self.continue_btn.draw(surf)

        self.back_btn.draw(surf)
