"""
app_mission.py — Application « Mission » du bureau (NATIVE).

Migration de `scenes/scene_mission.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — c'est l'écran de carrière le plus consulté du jeu,
même principe que Décision/Revue/Portefeuille/Marché avant lui. Toutes les
positions sont relatives au `rect` de la fenêtre. Les récompenses et l'état
de progression (intro → question → feedback → result) reprennent tels quels
la logique de la scène ; la scène plein écran reste enregistrée
(fallback/tests), l'ouverture EN FENÊTRE de "mission" est redirigée ici
(cf. DesktopScene._open_scene_window). La calculatrice reste l'overlay
déplaçable de ui/calculator.py (coordonnées absolues, compatibles fenêtre).
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import missions as M
from ui import fonts, widgets

CHART_COLORS = {"A": config.COL_CYAN, "B": config.COL_AMBER}


class MissionApp(DesktopApp):
    title = "Mission"
    icon_kind = "mission"
    default_size = (1000, 640)
    min_size = (640, 460)

    def on_open(self):
        self.t = 0.0
        p = self.app.gs.player
        market = self.app.ensure_market()
        self.mission = M.generate(p.grade_index, market, region=p.continent, track=p.track,
                                  player=p)
        self.idx = 0
        self.score = 0
        self.state = "intro"
        self.chosen = None
        self.input = ""
        self.input_ok = None
        self.answer_rects = {}
        self.mcq_focus = 0
        self.rep_gain = 0
        self.cash_gain = 0.0
        self._continue_rect = None
        self._calc_rect = None
        self.calc = None

    def _leave(self):
        if self.desktop is not None:
            w = next((w for w in self.desktop.wm.windows if w.app_obj is self), None)
            if w is not None:
                self.desktop.wm.close(w)

    # ------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if self.calc is not None:
            if self.calc.handle(event):
                if self.calc.closed:
                    self.calc = None
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                and self._calc_rect and self._calc_rect.collidepoint(event.pos):
            if self.calc is None:
                from ui.calculator import Calculator
                self.calc = Calculator(pos=(max(rect.x + 20, rect.right - 260), rect.y + 60))
            else:
                self.calc = None
            return True

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
                return True
            if self.state == "question" and item and item["kind"] == "mcq":
                n = len(item["choices"])
                if event.key in (pygame.K_DOWN, pygame.K_TAB):
                    self.mcq_focus = (self.mcq_focus + 1) % n
                    return True
                if event.key == pygame.K_UP:
                    self.mcq_focus = (self.mcq_focus - 1) % n
                    return True
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._answer_mcq(self.mcq_focus)
                    return True
                return False
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._advance_state_via_key()
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "intro" and self._continue_rect \
                    and self._continue_rect.collidepoint(event.pos):
                self.state = "question"
                return True
            if self.state == "question" and item and item["kind"] == "mcq":
                for i, r in self.answer_rects.items():
                    if r.collidepoint(event.pos):
                        self._answer_mcq(i)
                        return True
            if self.state == "feedback" and self._continue_rect \
                    and self._continue_rect.collidepoint(event.pos):
                self._next_item()
                return True
            if self.state == "result" and self._continue_rect \
                    and self._continue_rect.collidepoint(event.pos):
                self._leave()
                return True
        return False

    def _advance_state_via_key(self):
        if self.state == "intro":
            self.state = "question"
        elif self.state == "feedback":
            self._next_item()
        elif self.state == "result":
            self._leave()

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
        # logique partagée avec la scène plein écran : core/mission_flow.
        from core import mission_flow
        res = mission_flow.apply_result(self.app, self.mission, self.score)
        self.rep_gain, self.cash_gain = res["rep_gain"], res["cash_gain"]
        for text, kind in res["toasts"]:
            self.app.notify(text, kind)
        self.state = "result"

    # ------------------------------------------------------------- update
    def update(self, dt):
        self.t += dt

    # --------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        p = self.app.gs.player
        widgets.draw_text_scaled(surf, "MISSION — " + self.mission["title"],
                                 (rect.x + 16, rect.y + 10),
                                 fonts.head(bold=True), config.COL_AMBER, rect.w - 160)
        widgets.draw_text(surf, f"{p.grade}  ·  {M.grade_focus(p.grade_index)}",
                          (rect.x + 16, rect.y + 38), fonts.tiny(), config.COL_TEXT_DIM)
        # bouton calculatrice (coin haut-droit)
        self._calc_rect = pygame.Rect(rect.right - 120, rect.y + 10, 104, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._calc_rect, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, self._calc_rect, 1, border_radius=3)
        widgets.draw_text(surf, "CALCULATRICE", self._calc_rect.center,
                          fonts.tiny(bold=True), config.COL_CYAN, align="center")

        if self.state == "intro":
            self._draw_intro(surf, rect)
        elif self.state in ("question", "feedback"):
            self._draw_item(surf, rect)
        elif self.state == "result":
            self._draw_result(surf, rect)
        if self.calc is not None:
            self.calc.draw(surf)

    def _draw_continue(self, surf, rect, label):
        self._continue_rect = pygame.Rect(rect.centerx - 110, rect.bottom - 44, 220, 34)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._continue_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._continue_rect, 2, border_radius=4)
        widgets.draw_text(surf, label, self._continue_rect.center, fonts.small(bold=True),
                          config.COL_UP, align="center")

    def _draw_intro(self, surf, rect):
        panel = pygame.Rect(rect.x + 20, rect.y + 62, rect.w - 40,
                            rect.h - 62 - 56)
        inner = widgets.draw_panel(surf, panel, "Brief", config.COL_CYAN)
        widgets.draw_text_wrapped(surf, self.mission["brief"], (inner.x, inner.y),
                                  fonts.small(), config.COL_TEXT, inner.w, line_gap=5)
        lines = [
            f"{len(self.mission['items'])} questions.",
            "Texte à trous : tapez votre réponse chiffrée puis Entrée.",
            "QCM / décisions : cliquez la bonne réponse.",
            "",
            f"Récompense (au prorata du score) : jusqu'à +{self.mission['reward_rep']} réputation",
            "et un honoraire de conseil.",
        ]
        y = inner.y + 66
        for ln in lines:
            if y > inner.bottom - 60:
                break
            widgets.draw_text(surf, ln, (inner.x, y), fonts.tiny(), config.COL_TEXT)
            y += 20
        p = self.app.gs.player
        thr = M.reputation_threshold(p.grade_index)
        if y <= inner.bottom - 40:
            widgets.draw_text(surf, f"Seuil de réputation pour l'examen (EVAL) : {p.reputation}/{thr}",
                              (inner.x, y), fonts.tiny(), config.COL_TEXT)
            widgets.draw_progress(surf, pygame.Rect(inner.x, y + 18, min(260, inner.w), 8),
                                  min(1.0, p.reputation / thr) if thr else 1.0,
                                  config.COL_UP if p.reputation >= thr else config.COL_AMBER)
        self._draw_continue(surf, rect, "COMMENCER")

    def _draw_item(self, surf, rect):
        item = self._item()
        total = len(self.mission["items"])
        widgets.draw_text(surf, f"Question {self.idx + 1} / {total}",
                          (rect.x + 20, rect.y + 58), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_progress(surf, (rect.x + 20, rect.y + 74, rect.w - 40, 5),
                              self.idx / total, config.COL_AMBER)

        has_chart = bool(self.mission["charts"]) and item.get("chart") and rect.w >= 760
        prompt_w = (rect.w - 40) if not has_chart else (rect.w // 2 - 30)

        if has_chart:
            self._draw_charts(surf, item,
                              pygame.Rect(rect.x + rect.w // 2 + 10, rect.y + 88,
                                          rect.w // 2 - 30, min(260, rect.h - 200)))

        ppanel = pygame.Rect(rect.x + 20, rect.y + 88, prompt_w, 120)
        pinner = widgets.draw_panel(surf, ppanel, "Énoncé", config.COL_AMBER)
        widgets.draw_text_wrapped(surf, item["prompt"], (pinner.x, pinner.y),
                                  fonts.small(), config.COL_WHITE, pinner.w, line_gap=5)

        if item["kind"] == "mcq":
            self._draw_mcq(surf, rect, item, prompt_w)
        else:
            self._draw_fill(surf, rect, item, prompt_w)

        if self.state == "feedback":
            self._draw_feedback(surf, rect, item)

    def _draw_charts(self, surf, item, chart_rect):
        inner = widgets.draw_panel(surf, chart_rect, "Cours", config.COL_CYAN)
        which = item.get("chart", "")
        names = ["A", "B"] if which == "AB" else [which]
        for name in names:
            series = self.mission["charts"].get(name)
            if series:
                widgets.draw_series(surf, pygame.Rect(inner.x, inner.y + 8, inner.w, inner.h - 36),
                                    series, CHART_COLORS.get(name, config.COL_CYAN), baseline=False,
                                    mouse_pos=pygame.mouse.get_pos(), y_fmt=lambda v: f"{v:.0f}",
                                    show_pct=True)
        lx = inner.x
        for name in names:
            widgets.draw_text(surf, f"■ Titre {name}", (lx, inner.bottom - 16),
                              fonts.tiny(bold=True), CHART_COLORS.get(name, config.COL_CYAN))
            lx += 100

    def _draw_mcq(self, surf, rect, item, width):
        self.answer_rects = {}
        y = rect.y + 220
        row_h = 44
        for i, choice in enumerate(item["choices"]):
            r = pygame.Rect(rect.x + 20, y, width, row_h)
            if r.bottom > rect.bottom - 8:
                break
            self.answer_rects[i] = r
            if self.state == "feedback":
                if i == item["answer"]:
                    bg, border, txt = (16, 40, 26), config.COL_UP, config.COL_UP
                elif i == self.chosen:
                    bg, border, txt = (40, 16, 18), config.COL_DOWN, config.COL_DOWN
                else:
                    bg, border, txt = config.COL_PANEL, config.COL_BORDER, config.COL_TEXT_DIM
            else:
                hover = r.collidepoint(pygame.mouse.get_pos())
                focused = (i == self.mcq_focus)
                bg = config.COL_PANEL_HEAD if (hover or focused) else config.COL_PANEL
                border = config.COL_CYAN if (hover or focused) else config.COL_AMBER
                txt = config.COL_WHITE if (hover or focused) else config.COL_TEXT
            pygame.draw.rect(surf, bg, r)
            pygame.draw.rect(surf, border, r,
                             3 if (self.state == "question" and i == self.mcq_focus) else 1)
            widgets.draw_text(surf, f"{chr(65 + i)}.", (r.x + 10, r.y + 12),
                              fonts.small(bold=True), border)
            widgets.draw_text(surf, widgets.fit_text(choice, fonts.tiny(), r.w - 52),
                              (r.x + 40, r.y + 13), fonts.tiny(), txt)
            y += row_h + 8

    def _draw_fill(self, surf, rect, item, width):
        box = pygame.Rect(rect.x + 20, rect.y + 220, min(360, width), 46)
        active = self.state == "question"
        border = config.COL_CYAN if active else config.COL_BORDER
        pygame.draw.rect(surf, (6, 8, 12), box)
        pygame.draw.rect(surf, border, box, 2 if active else 1)
        cursor = "_" if (active and int(self.t * 2) % 2 == 0) else ""
        shown = (self.input or "") + cursor
        widgets.draw_text(surf, shown or "tapez un nombre…", (box.x + 10, box.y + 12),
                          fonts.body(bold=True),
                          config.COL_WHITE if self.input else config.COL_TEXT_DIM)
        if item.get("unit"):
            widgets.draw_text(surf, item["unit"], (box.right + 10, box.y + 12),
                              fonts.body(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "Entrée pour valider.", (box.x, box.bottom + 6),
                          fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_feedback(self, surf, rect, item):
        ok = (self.chosen == item["answer"]) if item["kind"] == "mcq" else bool(self.input_ok)
        accent = config.COL_UP if ok else config.COL_DOWN
        verdict = "Correct" if ok else "Incorrect"
        y = rect.y + 220 + (len(item["choices"]) * 52 if item["kind"] == "mcq" else 80)
        y = min(y, rect.bottom - 170)
        widgets.draw_text(surf, verdict, (rect.x + 20, y), fonts.body(bold=True), accent)
        if item["kind"] == "fill" and not ok:
            widgets.draw_text(surf, f"Réponse attendue ≈ {item['answer']:.2f} {item['unit']}",
                              (rect.x + 140, y + 2), fonts.tiny(), config.COL_TEXT_DIM)
        exp = pygame.Rect(rect.x + 20, y + 26, rect.w - 40,
                          max(60, rect.bottom - (y + 26) - 52))
        einner = widgets.draw_panel(surf, exp, "Explication", config.COL_CYAN)
        widgets.draw_text_wrapped(surf, item["expl"], (einner.x, einner.y),
                                  fonts.tiny(), config.COL_TEXT, einner.w)
        self._draw_continue(surf, rect,
                            "SUIVANT" if self.idx < len(self.mission["items"]) - 1
                            else "VOIR RÉSULTAT")

    def _objective_impact_lines(self, p):
        from core import career
        lines = []
        for o in p.objectives:
            if o["kind"] not in ("missions", "reputation"):
                continue
            cur, target, ok = career.objective_progress(p, o)
            mark = "✓" if ok else "→"
            lines.append(f"{mark} {career.objective_label(p, o)}")
        return lines

    def _draw_result(self, surf, rect):
        total = len(self.mission["items"])
        ratio = self.score / max(1, total)
        accent = config.COL_UP if ratio >= 0.5 else config.COL_WARN
        panel = pygame.Rect(rect.x + max(20, rect.w // 6), rect.y + 70,
                            rect.w - 2 * max(20, rect.w // 6), rect.h - 70 - 60)
        inner = widgets.draw_panel(surf, panel, "Mission terminée", accent)
        cx = panel.centerx
        widgets.draw_text(surf, f"Score : {self.score} / {total}", (cx, inner.y + 6),
                          fonts.head(bold=True), accent, align="center")
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
        msg.extend(self._objective_impact_lines(p))
        thr = M.reputation_threshold(p.grade_index)
        if p.reputation >= thr and p.can_promote():
            msg.append(f"Réputation ≥ {thr} : vous pouvez tenter l'examen (EVAL).")
        elif p.can_promote():
            msg.append(f"Encore {thr - p.reputation} de réputation avant l'examen (EVAL).")
        else:
            msg.append("Grade maximal atteint.")
        y = inner.y + 44
        for m in msg:
            if y > inner.bottom - 20:
                break
            widgets.draw_text(surf, widgets.fit_text(m, fonts.small(), inner.w),
                              (cx, y), fonts.small(), config.COL_TEXT, align="center")
            y += 26
        self._draw_continue(surf, rect, "TERMINER")
