"""
scene_mission.py — Mission du grade courant (jouable au clavier/souris).

Selon le grade : compte-rendu (texte à trous + QCM), lecture de graphes,
décision d'investissement, ou portefeuille/hedging. Le score rapporte de la
réputation (et un honoraire), nécessaires pour débloquer l'EVAL.

États : intro → item → feedback → result.
"""
import pygame

from core import config
from core import missions as M
from core.scene_manager import Scene
from ui import fonts, widgets

# couleurs des deux courbes des missions graphiques
CHART_COLORS = {"A": config.COL_CYAN, "B": config.COL_AMBER}


class MissionScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.t = 0.0
        p = self.app.gs.player
        market = self.app.ensure_market()
        self.mission = M.generate(p.grade_index, market, region=p.continent, track=p.track)
        self.idx = 0
        self.score = 0
        self.state = "intro"
        self.chosen = None
        self.input = ""        # saisie pour les items "fill"
        self.input_ok = None   # résultat de la dernière validation fill
        self.answer_rects = {}
        self.mcq_focus = 0     # index focusé au clavier parmi les choix MCQ
        self.continue_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 130, config.SCREEN_HEIGHT - 56, 260, 44),
            "COMMENCER", config.COL_UP)
        self.back_btn = widgets.Button(
            config.back_button_rect(150), "← QUITTER", config.COL_TEXT_DIM)
        self.calc_btn = widgets.Button(
            (200, config.SCREEN_HEIGHT - 50, 160, 42), "CALCULATRICE", config.COL_CYAN)
        self.calc = None        # calculatrice déplaçable (overlay)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        # la calculatrice (overlay) capte d'abord les clics
        if self.calc is not None:
            if self.calc.handle(event):
                if self.calc.closed:
                    self.calc = None
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.calc_btn.handle(event):
            if self.calc is None:
                from ui.calculator import Calculator
                self.calc = Calculator(pos=(config.SCREEN_WIDTH - 260, 110))
            else:
                self.calc = None
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return

        item = self._item()

        if event.type == pygame.KEYDOWN:
            if self.state == "question" and item and item["kind"] == "fill":
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._submit_fill()
                elif event.key == pygame.K_BACKSPACE:
                    self.input = self.input[:-1]
                else:
                    ch = event.unicode
                    if ch and (ch.isdigit() or ch in ".,-"):
                        self.input += ("." if ch == "," else ch)
            elif self.state == "question" and item and item["kind"] == "mcq":
                n = len(item["choices"])
                if event.key in (pygame.K_DOWN, pygame.K_TAB):
                    self.mcq_focus = (self.mcq_focus + 1) % n
                elif event.key == pygame.K_UP:
                    self.mcq_focus = (self.mcq_focus - 1) % n
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._answer_mcq(self.mcq_focus)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._advance_state_via_key()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "intro" and self.continue_btn.rect.collidepoint(event.pos):
                self.state = "question"
            elif self.state == "question" and item and item["kind"] == "mcq":
                for i, rect in self.answer_rects.items():
                    if rect.collidepoint(event.pos):
                        self._answer_mcq(i)
            elif self.state == "feedback" and self.continue_btn.rect.collidepoint(event.pos):
                self._next_item()
            elif self.state == "result" and self.continue_btn.rect.collidepoint(event.pos):
                self.app.scenes.go(self.return_to)

    def _advance_state_via_key(self):
        if self.state == "intro":
            self.state = "question"
        elif self.state == "feedback":
            self._next_item()
        elif self.state == "result":
            self.app.scenes.go(self.return_to)

    def _item(self):
        if 0 <= self.idx < len(self.mission["items"]):
            return self.mission["items"][self.idx]
        return None

    def _answer_mcq(self, i):
        self.chosen = i
        if i == self._item()["answer"]:
            self.score += 1
        self.state = "feedback"

    def _submit_fill(self):
        item = self._item()
        try:
            val = float(self.input.replace(",", "."))
        except ValueError:
            self.input_ok = None
            return
        self.input_ok = M.check_fill(item, val)
        if self.input_ok:
            self.score += 1
        self.chosen = val
        self.state = "feedback"

    def _next_item(self):
        self.idx += 1
        self.chosen = None
        self.input = ""
        self.input_ok = None
        self.mcq_focus = 0
        if self.idx >= len(self.mission["items"]):
            self._finish()
        else:
            self.state = "question"

    def _finish(self):
        from core import career
        p = self.app.gs.player
        total = len(self.mission["items"])
        self.rep_gain, self.cash_gain = M.compute_rewards(self.mission, self.score, total)
        p.adjust_reputation(self.rep_gain, reason=f"Mission : {self.mission.get('title', '')}")
        p.adjust_cash(self.cash_gain)
        p.missions_done += 1
        p.grade_missions += 1
        if self.score == total:
            career.log(p, "info", f"Mission '{self.mission['title']}' réussie ({self.score}/{total}).")
        self.app.notify(f"Mission : +{self.rep_gain} réputation", "good")
        # une mission prend du temps : le terminal avancera d'un tour au retour
        self.app.advance_on_return = 1
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        self.state = "result"

    # ------------------------------------------------------------- update
    def update(self, dt):
        self.t += dt
        mp = pygame.mouse.get_pos()
        self.continue_btn.update(mp, dt)
        self.back_btn.update(mp, dt)
        self.calc_btn.update(mp, dt)

    # --------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text_scaled(surf, "MISSION — " + self.mission["title"], (40, 24),
                                 fonts.title(bold=True), config.COL_AMBER,
                                 config.SCREEN_WIDTH - 80)
        widgets.draw_text(surf, f"{p.grade}  ·  {M.grade_focus(p.grade_index)}",
                          (42, 76), fonts.small(), config.COL_TEXT_DIM)

        if self.state == "intro":
            self._draw_intro(surf)
        elif self.state in ("question", "feedback"):
            self._draw_item(surf)
        elif self.state == "result":
            self._draw_result(surf)
        self.back_btn.draw(surf)
        self.calc_btn.draw(surf)
        if self.calc is not None:
            self.calc.draw(surf)

    def _draw_intro(self, surf):
        panel = pygame.Rect(120, 150, config.SCREEN_WIDTH - 240, 420)
        inner = widgets.draw_panel(surf, panel, "Brief", config.COL_CYAN)
        widgets.draw_text_wrapped(surf, self.mission["brief"], (inner.x, inner.y),
                                  fonts.body(), config.COL_TEXT, inner.w, line_gap=6)
        lines = [
            "",
            f"{len(self.mission['items'])} questions.",
            "Texte à trous : tapez votre réponse chiffrée puis Entrée.",
            "QCM / décisions : cliquez la bonne réponse.",
            "",
            f"Récompense (au prorata du score) : jusqu'à +{self.mission['reward_rep']} réputation",
            "et un honoraire de conseil.",
            "",
            f"Seuil de réputation pour l'examen (EVAL) : "
            f"{M.reputation_threshold(self.app.gs.player.grade_index)}/100.",
        ]
        y = inner.y + 70
        for ln in lines:
            widgets.draw_text(surf, ln, (inner.x, y), fonts.small(), config.COL_TEXT)
            y += 26
        self.continue_btn.label = "COMMENCER"
        self.continue_btn.draw(surf)

    def _draw_item(self, surf):
        item = self._item()
        total = len(self.mission["items"])
        # progression
        widgets.draw_text(surf, f"Question {self.idx + 1} / {total}", (40, 104),
                          fonts.small(), config.COL_TEXT_DIM)
        pw = config.SCREEN_WIDTH - 80
        widgets.draw_progress(surf, (40, 126, pw, 6), self.idx / total, config.COL_AMBER)

        has_chart = bool(self.mission["charts"]) and item.get("chart")
        prompt_w = (config.SCREEN_WIDTH - 80) if not has_chart else (config.SCREEN_WIDTH // 2 - 60)

        # éventuel graphe
        if has_chart:
            self._draw_charts(surf, item, pygame.Rect(config.SCREEN_WIDTH // 2 + 20, 150,
                                                      config.SCREEN_WIDTH // 2 - 60, 300))

        # énoncé
        ppanel = pygame.Rect(40, 150, prompt_w, 150)
        pinner = widgets.draw_panel(surf, ppanel, "Énoncé", config.COL_AMBER)
        widgets.draw_text_wrapped(surf, item["prompt"], (pinner.x, pinner.y),
                                  fonts.body(), config.COL_WHITE, pinner.w, line_gap=6)

        if item["kind"] == "mcq":
            self._draw_mcq(surf, item, prompt_w)
        else:
            self._draw_fill(surf, item, prompt_w)

        if self.state == "feedback":
            self._draw_feedback(surf, item)

    def _draw_charts(self, surf, item, rect):
        inner = widgets.draw_panel(surf, rect, "Cours", config.COL_CYAN)
        which = item.get("chart", "")
        names = ["A", "B"] if which == "AB" else [which]
        for name in names:
            series = self.mission["charts"].get(name)
            if series:
                widgets.draw_series(surf, pygame.Rect(inner.x, inner.y + 10, inner.w, inner.h - 40),
                                    series, CHART_COLORS.get(name, config.COL_CYAN), baseline=False,
                                    mouse_pos=pygame.mouse.get_pos(), y_fmt=lambda v: f"{v:.0f}",
                                    show_pct=True)
        # légende
        lx = inner.x
        for name in names:
            widgets.draw_text(surf, f"■ Titre {name}", (lx, inner.bottom - 18),
                              fonts.small(bold=True), CHART_COLORS.get(name, config.COL_CYAN))
            lx += 110

    def _draw_mcq(self, surf, item, width):
        self.answer_rects = {}
        y = 320
        for i, choice in enumerate(item["choices"]):
            rect = pygame.Rect(40, y, width, 50)
            self.answer_rects[i] = rect
            if self.state == "feedback":
                if i == item["answer"]:
                    bg, border, txt = (16, 40, 26), config.COL_UP, config.COL_UP
                elif i == self.chosen:
                    bg, border, txt = (40, 16, 18), config.COL_DOWN, config.COL_DOWN
                else:
                    bg, border, txt = config.COL_PANEL, config.COL_BORDER, config.COL_TEXT_DIM
            else:
                hover = rect.collidepoint(pygame.mouse.get_pos())
                focused = (i == self.mcq_focus)
                bg = config.COL_PANEL_HEAD if (hover or focused) else config.COL_PANEL
                border = config.COL_CYAN if (hover or focused) else config.COL_AMBER
                txt = config.COL_WHITE if (hover or focused) else config.COL_TEXT
            pygame.draw.rect(surf, bg, rect)
            pygame.draw.rect(surf, border, rect, 3 if (self.state == "question" and i == self.mcq_focus) else 1)
            widgets.draw_text(surf, f"{chr(65 + i)}.", (rect.x + 12, rect.y + 15),
                              fonts.body(bold=True), border)
            widgets.draw_text(surf, choice, (rect.x + 48, rect.y + 15), fonts.small(), txt)
            y += 58

    def _draw_fill(self, surf, item, width):
        # zone de saisie
        box = pygame.Rect(40, 320, min(420, width), 56)
        active = self.state == "question"
        border = config.COL_CYAN if active else config.COL_BORDER
        pygame.draw.rect(surf, (6, 8, 12), box)
        pygame.draw.rect(surf, border, box, 2 if active else 1)
        cursor = "_" if (active and int(self.t * 2) % 2 == 0) else ""
        shown = (self.input or "") + cursor
        widgets.draw_text(surf, shown or "tapez un nombre…", (box.x + 12, box.y + 16),
                          fonts.head(bold=True),
                          config.COL_WHITE if self.input else config.COL_TEXT_DIM)
        if item.get("unit"):
            widgets.draw_text(surf, item["unit"], (box.right + 12, box.y + 16),
                              fonts.head(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "Entrée pour valider.", (box.x, box.bottom + 8),
                          fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_feedback(self, surf, item):
        ok = (self.chosen == item["answer"]) if item["kind"] == "mcq" else bool(self.input_ok)
        accent = config.COL_UP if ok else config.COL_DOWN
        verdict = "Correct" if ok else "Incorrect"
        y = 320 + (len(item["choices"]) * 58 if item["kind"] == "mcq" else 90)
        y = min(y, config.SCREEN_HEIGHT - 230)
        widgets.draw_text(surf, verdict, (40, y), fonts.head(bold=True), accent)
        if item["kind"] == "fill" and not ok:
            widgets.draw_text(surf, f"Réponse attendue ≈ {item['answer']:.2f} {item['unit']}",
                              (180, y + 4), fonts.small(), config.COL_TEXT_DIM)
        exp = pygame.Rect(40, y + 34, config.SCREEN_WIDTH - 80, 90)
        einner = widgets.draw_panel(surf, exp, "Explication", config.COL_CYAN)
        widgets.draw_text_wrapped(surf, item["expl"], (einner.x, einner.y),
                                  fonts.small(), config.COL_TEXT, einner.w)
        self.continue_btn.label = ("SUIVANT" if self.idx < len(self.mission["items"]) - 1
                                   else "VOIR RÉSULTAT")
        self.continue_btn.draw(surf)

    def _draw_result(self, surf):
        total = len(self.mission["items"])
        ratio = self.score / max(1, total)
        accent = config.COL_UP if ratio >= 0.5 else config.COL_WARN
        panel = pygame.Rect(240, 170, config.SCREEN_WIDTH - 480, 360)
        inner = widgets.draw_panel(surf, panel, "Mission terminée", accent)
        cx = panel.centerx
        widgets.draw_text(surf, f"Score : {self.score} / {total}", (cx, inner.y + 10),
                          fonts.title(bold=True), accent, align="center")
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        msg = [
            f"Réputation : +{self.rep_gain}  (désormais {p.reputation}/100)",
            f"Honoraire  : +{widgets.format_money(self.cash_gain, cur)}",
        ]
        if self.score < total:
            best_rep, best_cash = M.compute_rewards(self.mission, total, total)
            miss_rep, miss_cash = best_rep - self.rep_gain, best_cash - self.cash_gain
            if miss_rep > 0 or miss_cash > 0:
                msg.append(f"Avec un score parfait : +{miss_rep} réputation et "
                           f"+{widgets.format_money(miss_cash, cur)} de plus.")
        msg.append("")
        thr = M.reputation_threshold(p.grade_index)
        if p.reputation >= thr and p.can_promote():
            msg.append(f"Réputation ≥ {thr} : vous pouvez tenter l'examen (EVAL).")
        elif p.can_promote():
            msg.append(f"Encore {thr - p.reputation} de réputation avant l'examen (EVAL).")
        else:
            msg.append("Grade maximal atteint.")
        y = inner.y + 70
        for m in msg:
            widgets.draw_text(surf, m, (cx, y), fonts.body(), config.COL_TEXT, align="center")
            y += 32
        self.continue_btn.rect.center = (cx, inner.bottom - 36)
        self.continue_btn.label = f"RETOUR : {self.return_to.upper()}"
        self.continue_btn.draw(surf)
