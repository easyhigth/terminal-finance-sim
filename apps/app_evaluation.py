"""
app_evaluation.py — Application « Évaluation » du bureau (NATIVE).

Migration de `scenes/scene_evaluation.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — même principe que Mission avant elle (l'écran à
plus fort enjeu du jeu : examen de promotion ET de certification). Toutes
les positions sont relatives au `rect` de la fenêtre plutôt qu'à
`config.SCREEN_WIDTH`/`footer_y()`. La logique (génération des questions,
notation, promotion, certifications) est réutilisée telle quelle depuis
`core/exam.py`/`core/certifications.py`/`core/career.py`. La scène plein
écran reste enregistrée (fallback/tests) ; l'ouverture EN FENÊTRE de
"evaluation" est redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import audio, config, exam
from core.i18n import get_lang
from ui import fonts, widgets

CHART_COLORS = {"A": config.COL_CYAN, "B": config.COL_AMBER}


def _L(fr, en):
    return en if get_lang() == "en" else fr


class EvaluationApp(DesktopApp):
    title = "Évaluation"
    icon_kind = "examcert"
    default_size = (1040, 660)
    min_size = (680, 460)

    def on_open(self):
        """Appelé sans argument par WindowManager.open() à la création de la
        fenêtre — mode promotion par défaut (accès direct via l'icône/menu
        Démarrer). Un mode "cert" avec programme précis est fourni ensuite
        via `configure(**kwargs)`, appelé explicitement par le redirecteur
        du bureau (cf. DesktopScene._open_scene_window)."""
        self.configure()

    def reenter(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        self.t = 0.0
        p = self.app.gs.player
        self.cert_program = kwargs.get("program")
        self.cert_level = kwargs.get("level", 0)
        self.mode = kwargs.get("mode", "promotion")
        saved = p.eval_state if isinstance(p.eval_state, dict) else {}
        resume = bool(saved) and saved.get("mode") == self.mode and saved.get("items")
        if resume:
            self.items = saved["items"]
            self.idx = saved.get("idx", 0)
            self.score = saved.get("score", 0)
            self.missed_lessons = list(saved.get("missed_lessons", []))
            self.pass_threshold = saved.get("pass_threshold", exam.PASS_THRESHOLD)
            self.target_grade = saved.get("target_grade", "")
            self.cert_program = saved.get("cert_program", self.cert_program)
            self.cert_level = saved.get("cert_level", self.cert_level)
            self.state = "question"
        else:
            if self.mode == "cert":
                from core import certifications as C
                prog = C.PROGRAMS[self.cert_program]
                tier = kwargs.get("tier", prog["tier"])
                self.items = exam.generate(p.grade_index, difficulty=tier, n=C.EXAM_N)
                self.pass_threshold = C.PASS_THRESHOLD
                self.target_grade = f"{prog['name']} niveau {self.cert_level + 1}"
            else:
                target = min(p.grade_index + 1, len(config.GRADES) - 1)
                self.target_grade = config.GRADES[target]
                self.items = exam.generate(p.grade_index)
                self.pass_threshold = exam.PASS_THRESHOLD
            self.idx = 0
            self.score = 0
            self.missed_lessons = []
            self.state = "intro"
        self.chosen = None
        self.input = ""
        self.submitted_ok = None
        self.answer_rects = {}
        self.passed = False
        self.new_title = None
        self.calc = None
        self._continue_rect = None
        self._calc_rect = None
        self._pause_rect = None
        self._resume_label = resume

    def _leave(self):
        if self.desktop is not None:
            w = next((w for w in self.desktop.wm.windows if w.app_obj is self), None)
            if w is not None:
                self.desktop.wm.close(w)

    def _pause(self):
        """Sauvegarde la progression de l'examen pour reprendre plus tard —
        fermer la fenêtre pendant un examen n'abandonne jamais silencieusement
        (bouton explicite, contrairement à une simple minimisation)."""
        p = self.app.gs.player
        p.eval_state = {
            "mode": self.mode, "items": self.items, "idx": self.idx,
            "score": self.score, "missed_lessons": list(self.missed_lessons),
            "pass_threshold": self.pass_threshold, "target_grade": self.target_grade,
            "cert_program": self.cert_program, "cert_level": self.cert_level,
        }
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        self.app.notify(_L("Examen mis en pause — reprenez via EVAL", "Exam paused — resume via EVAL"), "info")
        self._leave()

    # ------------------------------------------------------------- helpers
    def _item(self):
        return self.items[self.idx] if 0 <= self.idx < len(self.items) else None

    def _is_mcq(self, it):
        return it["kind"] == "mcq" or (it["kind"] == "graph" and it.get("subkind") == "mcq")

    def _is_input(self, it):
        return it["kind"] in ("fill", "text") or \
            (it["kind"] == "graph" and it.get("subkind") == "fill")

    # ------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if self.calc is not None and self.calc.handle(event):
            if self.calc.closed:
                self.calc = None
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._calc_rect and self._calc_rect.collidepoint(event.pos):
                if self.calc is None:
                    from ui.calculator import Calculator
                    self.calc = Calculator(pos=(max(rect.x + 20, rect.right - 260), rect.y + 60))
                else:
                    self.calc = None
                return True
            if self.state in ("question", "feedback") and self._pause_rect \
                    and self._pause_rect.collidepoint(event.pos):
                self._pause()
                return True

        it = self._item()
        if event.type == pygame.KEYDOWN:
            if self.state == "question" and it is not None and self._is_input(it):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._submit(it)
                elif event.key == pygame.K_BACKSPACE:
                    self.input = self.input[:-1]
                else:
                    self._type(it, event.unicode)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._advance_via_key()
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "intro" and self._continue_rect \
                    and self._continue_rect.collidepoint(event.pos):
                self.state = "question"
                return True
            if self.state == "question" and it is not None and self._is_mcq(it):
                for i, r in self.answer_rects.items():
                    if r.collidepoint(event.pos):
                        self._answer_mcq(i, it)
                        return True
            if self.state == "feedback" and self._continue_rect \
                    and self._continue_rect.collidepoint(event.pos):
                self._next()
                return True
            if self.state == "result" and self._continue_rect \
                    and self._continue_rect.collidepoint(event.pos):
                self._leave()
                return True
        return False

    def _type(self, it, ch):
        if not ch:
            return
        if it["kind"] == "text":
            if ch.isalnum() or ch in " /.-'éèàçâêôûïü":
                self.input += ch
        else:
            if ch.isdigit() or ch in ".,-":
                self.input += ("." if ch == "," else ch)

    def _advance_via_key(self):
        if self.state == "intro":
            self.state = "question"
        elif self.state == "feedback":
            self._next()
        elif self.state == "result":
            self._leave()

    def _answer_mcq(self, i, it):
        self.chosen = i
        if i == it["answer"]:
            self.score += 1
        else:
            self._record_miss(it)
        self.state = "feedback"

    def _record_miss(self, it):
        lid = exam.lesson_for_item(it)
        if lid and lid not in self.missed_lessons:
            self.missed_lessons.append(lid)

    def _submit(self, it):
        if it["kind"] == "text":
            ok = exam.check_text(it, self.input)
        else:
            try:
                ok = exam.check_fill(it, float(self.input.replace(",", ".")))
            except ValueError:
                ok = False
        self.submitted_ok = ok
        if ok:
            self.score += 1
        else:
            self._record_miss(it)
        self.state = "feedback"

    def _next(self):
        self.idx += 1
        self.chosen = None
        self.input = ""
        self.submitted_ok = None
        if self.idx >= len(self.items):
            self._finish()
        else:
            self.state = "question"

    def _finish(self):
        from core import career
        p = self.app.gs.player
        p.eval_state = {}
        self.app.pending_market_steps += 1
        ratio = self.score / max(1, len(self.items))
        self.passed = ratio >= self.pass_threshold
        if self.mode == "cert":
            self._finish_cert(p)
            self.app.gs.save(config.AUTOSAVE_SLOT)
            self.state = "result"
            return
        if self.passed and p.can_promote():
            old_grade_index = p.grade_index
            p.promote()
            audio.play("promotion")
            from core import profile
            profile.record_grade_reached(p.grade_index)
            p.reputation = min(100, p.reputation + 8)
            if p.grade_index >= 2 and p.track == "General":
                p.flags["can_choose_track"] = True
            self.new_title = career.award_promotion(p)
            career.log(p, "promo", f"Promotion : {p.grade}"
                       + (f" — titre « {self.new_title} »" if self.new_title else ""))
            from core import inbox
            inbox.on_promotion(p)
            self.app.notify(_L(f"Promotion : {p.grade}", f"Promotion: {p.grade}"), "good")
            if self.new_title:
                self.app.notify(_L(f"Titre : {self.new_title}", f"Title: {self.new_title}"), "prestige")
            from core import unlock_briefs, unlocks
            new_feats = unlock_briefs.newly_unlocked(p, old_grade_index)
            if new_feats:
                p.flags["pending_unlock_briefs"] = {"grade": p.grade,
                                                    "features": list(new_feats)}
            for feat in new_feats:
                self.app.notify(_L(f"⊘→✓ Débloqué : {unlocks.feature_label(feat)}",
                                    f"⊘→✓ Unlocked: {unlocks.feature_label(feat)}"), "good")
                tid = unlocks.FEATURE_TUTORIAL.get(feat)
                if tid and not p.flags.get("pending_tutorial"):
                    p.flags["pending_tutorial"] = tid
                label = unlocks.feature_label(feat)
                body = (f"Votre promotion au grade {p.grade} ouvre un nouveau "
                        f"périmètre : {label}. Prenez le temps de vous y faire "
                        "la main avant d'engager du capital.")
                if tid:
                    body += (" Un tutoriel dédié vous attend (écran TUTORIELS, "
                             "ou l'icône Aide du bureau).")
                inbox.push(p, "manager", "Votre manager",
                           f"Nouveau périmètre : {label}", body)
        else:
            p.reputation = max(0, p.reputation - 5)
            pct = int(ratio * 100)
            req = int(self.pass_threshold * 100)
            self.app.notify(_L(f"Évaluation échouée : {pct}% < {req}% requis (−5 réputation)",
                                f"Evaluation failed: {pct}% < {req}% required (−5 reputation)"), "bad")
            career.log(p, "promo", _L(
                f"Évaluation de promotion échouée ({pct}% < seuil {req}%, −5 réputation)",
                f"Promotion evaluation failed ({pct}% < threshold {req}%, −5 reputation)"))
        self.app.gs.save(config.AUTOSAVE_SLOT)
        self.state = "result"

    def _finish_cert(self, p):
        from core import badges, career
        from core import certifications as C
        self.new_title = None
        name = C.PROGRAMS[self.cert_program]["name"]
        if self.passed:
            res = C.pass_stage(p, self.cert_program)
            self.new_title = res.get("title") if res else None
            self.app.notify(_L(f"{name} : niveau réussi", f"{name}: level passed"), "prestige")
            for b in badges.check_new(p, self.app.market):
                bname = badges.badge_name(b)
                self.app.notify(_L(f"✶ Badge : {bname}", f"✶ Badge: {bname}"), "prestige")
        else:
            ratio = self.score / max(1, len(self.items))
            pct = int(ratio * 100)
            req = int(self.pass_threshold * 100)
            self.app.notify(_L(f"{name} échouée : {pct}% < {req}% requis",
                                f"{name} failed: {pct}% < {req}% required"), "bad")
            career.log(p, "promo", _L(
                f"Certification {name} échouée ({pct}% < seuil {req}%)",
                f"Certification {name} failed ({pct}% < threshold {req}%)"))

    def update(self, dt):
        self.t += dt

    # --------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        p = self.app.gs.player
        title = _L("EXAMEN DE CERTIFICATION", "CERTIFICATION EXAM") if self.mode == "cert" \
            else _L("ÉVALUATION DE PROMOTION", "PROMOTION EXAM")
        widgets.draw_text(surf, title, (rect.x + 16, rect.y + 10), fonts.head(bold=True), config.COL_AMBER)
        sub = (_L(f"{self.target_grade} | Voie : {p.track}", f"{self.target_grade} | Track: {p.track}")
               if self.mode == "cert" else
               _L(f"{p.grade} → {self.target_grade} | Voie : {p.track}",
                  f"{p.grade} → {self.target_grade} | Track: {p.track}"))
        widgets.draw_text(surf, widgets.fit_text(sub, fonts.tiny(), rect.w - 32),
                          (rect.x + 16, rect.y + 34), fonts.tiny(), config.COL_TEXT_DIM)

        if self.state in ("question", "feedback"):
            self._calc_rect = pygame.Rect(rect.right - 224, rect.y + 10, 104, 22)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._calc_rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN, self._calc_rect, 1, border_radius=3)
            widgets.draw_text(surf, _L("CALCULATRICE", "CALCULATOR"), self._calc_rect.center,
                              fonts.tiny(bold=True), config.COL_CYAN, align="center")
            self._pause_rect = pygame.Rect(rect.right - 112, rect.y + 10, 96, 22)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._pause_rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_WARN, self._pause_rect, 1, border_radius=3)
            widgets.draw_text(surf, "PAUSE", self._pause_rect.center, fonts.tiny(bold=True),
                              config.COL_WARN, align="center")

        if self.state == "intro":
            self._draw_intro(surf, rect)
        elif self.state in ("question", "feedback"):
            self._draw_item(surf, rect)
        elif self.state == "result":
            self._draw_result(surf, rect)
        if self.calc is not None:
            self.calc.draw(surf)

    def _draw_continue(self, surf, rect, label):
        self._continue_rect = pygame.Rect(rect.centerx - 120, rect.bottom - 44, 240, 34)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._continue_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._continue_rect, 2, border_radius=4)
        widgets.draw_text(surf, label, self._continue_rect.center, fonts.small(bold=True),
                          config.COL_UP, align="center")

    def _draw_intro(self, surf, rect):
        panel = pygame.Rect(rect.x + 20, rect.y + 60, rect.w - 40, rect.h - 60 - 56)
        inner = widgets.draw_panel(surf, panel, "Brief", config.COL_CYAN)
        p = self.app.gs.player
        if self.mode == "cert":
            intro1 = _L(f"Examen de certification — {self.target_grade}.", f"Certification exam — {self.target_grade}.")
            bank_line = _L(f"{len(self.items)} questions exigeantes, banque dédiée.", f"{len(self.items)} demanding questions, dedicated bank.")
        else:
            intro1 = _L(f"Entretien technique pour le poste de {self.target_grade}.", f"Technical interview for the {self.target_grade} role.")
            bank_line = _L(f"{len(self.items)} questions tirées d'une banque d'environ {exam.bank_target(p.grade_index)} pour ce grade.",
                          f"{len(self.items)} questions drawn from a bank of about {exam.bank_target(p.grade_index)} for this grade.")
        lines = [
            intro1, "", bank_line,
            _L("Types : calculs, QCM, lecture de graphe, définitions et formules à trous.",
               "Types: calculations, MCQ, chart reading, fill-in definitions and formulas."),
            _L(f"Seuil de réussite : {int(self.pass_threshold*100)}%.", f"Pass threshold: {int(self.pass_threshold*100)}%."),
            "",
            _L("Calcul : tapez votre nombre.  Définition/formule : tapez le ou les mots.",
               "Calculation: type your number.  Definition/formula: type the word(s)."),
            _L("QCM : cliquez la bonne réponse.  Une CALCULATRICE est disponible.",
               "MCQ: click the right answer.  A CALCULATOR is available."),
            "",
            _L("Réussite → promotion (+réputation).  Échec → −réputation, à retenter.",
               "Pass → promotion (+reputation).  Fail → −reputation, retry later."),
        ]
        y = inner.y
        for ln in lines:
            if y > inner.bottom - 24:
                break
            widgets.draw_text_wrapped(surf, ln, (inner.x, y), fonts.small(), config.COL_TEXT, inner.w, line_gap=4)
            y += 22
        self._draw_continue(surf, rect, _L("REPRENDRE", "RESUME") if self._resume_label else _L("COMMENCER", "START"))

    def _draw_item(self, surf, rect):
        it = self._item()
        n = len(self.items)
        top = rect.y + 56
        widgets.draw_text(surf, f"Question {self.idx+1} / {n}", (rect.x + 20, top),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_progress(surf, (rect.x + 20, top + 16, rect.w - 40, 5), self.idx / n, config.COL_AMBER)

        has_chart = bool(it.get("charts")) and rect.w >= 780
        pw = rect.w - 40
        prompt_w = pw if not has_chart else int(pw * 0.5)
        content_top = top + 32
        if has_chart:
            self._draw_charts(surf, it, pygame.Rect(rect.x + 20 + prompt_w + 16, content_top,
                                                     pw - prompt_w - 16, min(220, rect.h - content_top - 160)))
        ppanel = pygame.Rect(rect.x + 20, content_top, prompt_w, 96)
        pinner = widgets.draw_panel(surf, ppanel, _L("Énoncé", "Prompt"), config.COL_AMBER)
        widgets.draw_text_wrapped(surf, it["prompt"], (pinner.x, pinner.y),
                                  fonts.small(), config.COL_WHITE, pinner.w, line_gap=4)

        options_top = ppanel.bottom + 16
        if self._is_mcq(it):
            self._draw_mcq(surf, rect, it, prompt_w, options_top)
        else:
            self._draw_input(surf, rect, it, prompt_w, options_top)

        if self.state == "feedback":
            self._draw_feedback(surf, rect, it)

    def _draw_charts(self, surf, it, rect):
        inner = widgets.draw_panel(surf, rect, _L("Cours", "Price"), config.COL_CYAN)
        names = ["A", "B"] if it.get("chart") == "AB" else [it.get("chart", "A")]
        series = [it["charts"][nm] for nm in names if it["charts"].get(nm)]
        y_margin = 38
        plot = pygame.Rect(inner.x + y_margin, inner.y + 8, inner.w - y_margin, max(30, inner.h - 36))
        lo = hi = span = 0
        if series:
            lo = min(min(s) for s in series)
            hi = max(max(s) for s in series)
            pad = (hi - lo) * 0.08 or 1.0
            lo, hi, span = widgets.draw_chart_axes(surf, plot, lo - pad, hi + pad, y_fmt=lambda v: f"{v:.0f}")
        for nm in names:
            s = it["charts"].get(nm)
            if not s:
                continue
            col = CHART_COLORS.get(nm, config.COL_CYAN)
            widgets.draw_series(surf, plot, s, col, baseline=False,
                                mouse_pos=pygame.mouse.get_pos(), y_fmt=lambda v: f"{v:.0f}", show_pct=True)
        lx = inner.x
        for nm in names:
            widgets.draw_text(surf, _L(f"■ Titre {nm}", f"■ Stock {nm}"), (lx, inner.bottom - 16),
                              fonts.tiny(bold=True), CHART_COLORS.get(nm, config.COL_CYAN))
            lx += 100

    def _draw_mcq(self, surf, rect, it, width, top):
        self.answer_rects = {}
        y = top
        row_h = 40
        for i, choice in enumerate(it["choices"]):
            r = pygame.Rect(rect.x + 20, y, width, row_h)
            if r.bottom > rect.bottom - 8:
                break
            self.answer_rects[i] = r
            if self.state == "feedback":
                if i == it["answer"]:
                    bg, border, txt = (16, 40, 26), config.COL_UP, config.COL_UP
                elif i == self.chosen:
                    bg, border, txt = (40, 16, 18), config.COL_DOWN, config.COL_DOWN
                else:
                    bg, border, txt = config.COL_PANEL, config.COL_BORDER, config.COL_TEXT_DIM
            else:
                hover = r.collidepoint(pygame.mouse.get_pos())
                bg = config.COL_PANEL_HEAD if hover else config.COL_PANEL
                border = config.COL_CYAN if hover else config.COL_AMBER
                txt = config.COL_WHITE if hover else config.COL_TEXT
            pygame.draw.rect(surf, bg, r)
            pygame.draw.rect(surf, border, r, 1)
            widgets.draw_text(surf, f"{chr(65+i)}.", (r.x + 10, r.y + 10), fonts.small(bold=True), border)
            widgets.draw_text(surf, widgets.fit_text(choice, fonts.tiny(), r.w - 44),
                              (r.x + 38, r.y + 12), fonts.tiny(), txt)
            y += row_h + 6

    def _draw_input(self, surf, rect, it, width, top):
        kind = _L("Réponse (texte)", "Answer (text)") if it["kind"] == "text" else _L("Réponse (nombre)", "Answer (number)")
        widgets.draw_text(surf, kind, (rect.x + 20, top), fonts.small(bold=True), config.COL_TEXT_DIM)
        active = self.state == "question"
        box = pygame.Rect(rect.x + 20, top + 22, min(420, width), 44)
        pygame.draw.rect(surf, (6, 8, 12), box)
        pygame.draw.rect(surf, config.COL_CYAN if active else config.COL_BORDER, box, 2 if active else 1)
        cur = "_" if (active and int(self.t * 2) % 2 == 0) else ""
        shown = (self.input or "") + cur
        widgets.draw_text(surf, shown or _L("tapez votre réponse…", "type your answer…"), (box.x + 10, box.y + 12),
                          fonts.body(bold=True), config.COL_WHITE if self.input else config.COL_TEXT_DIM)
        if it.get("unit"):
            widgets.draw_text(surf, it["unit"], (box.right + 10, box.y + 12), fonts.body(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, _L("Entrée pour valider.", "Press Enter to submit."), (box.x, box.bottom + 6),
                          fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_feedback(self, surf, rect, it):
        ok = (self.chosen == it["answer"]) if self._is_mcq(it) else bool(self.submitted_ok)
        exp_top = rect.bottom - 190
        exp = pygame.Rect(rect.x + 20, exp_top, rect.w - 40, 190 - 56)
        inner = widgets.draw_panel(surf, exp, _L("Correction", "Feedback"), config.COL_CYAN)
        widgets.draw_text(surf, _L("✓ Bonne réponse", "✓ Correct") if ok else _L("✗ Mauvaise réponse", "✗ Wrong"),
                          (inner.x, inner.y), fonts.small(bold=True), config.COL_UP if ok else config.COL_DOWN)
        if not ok and self._is_input(it):
            exp_ans = (", ".join(it["answers"]) if it["kind"] == "text"
                       else f"{it['answer']:.2f} {it.get('unit','')}")
            widgets.draw_text(surf, widgets.fit_text(_L("Attendu : ", "Expected: ") + exp_ans, fonts.tiny(), inner.w - 170),
                              (inner.x + 170, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text_wrapped(surf, it["expl"], (inner.x, inner.y + 22),
                                  fonts.tiny(), config.COL_TEXT, inner.w, line_gap=3)
        label = _L("SUIVANT", "NEXT") if self.idx < len(self.items) - 1 else _L("VOIR RÉSULTAT", "SEE RESULT")
        self._draw_continue(surf, rect, label)

    def _draw_result(self, surf, rect):
        ratio = self.score / max(1, len(self.items))
        accent = config.COL_UP if self.passed else config.COL_DOWN
        p = self.app.gs.player
        if self.mode == "cert":
            verdict = _L("CERTIFICATION RÉUSSIE", "CERTIFICATION PASSED") if self.passed else _L("EXAMEN ÉCHOUÉ", "EXAM FAILED")
        else:
            verdict = _L("PROMOTION ACCORDÉE", "PROMOTION GRANTED") if self.passed else _L("ÉVALUATION ÉCHOUÉE", "EVALUATION FAILED")
        if self.mode == "cert":
            from core import certifications as C
            prog = C.PROGRAMS[self.cert_program]
            if self.passed:
                msg = [f"{prog['name']} — {C.status_label(p, self.cert_program)}.",
                       _L("Réputation accrue.", "Reputation boosted.")]
                if self.new_title:
                    msg.append(_L(f"Titre : « {self.new_title} » !", f"Title: “{self.new_title}”!"))
            else:
                msg = [_L(f"Seuil non atteint ({int(self.pass_threshold*100)}% requis).", f"Threshold not met ({int(self.pass_threshold*100)}% required)."),
                       _L("Les frais d'inscription sont perdus.", "The entry fee is forfeited."),
                       _L("Révisez (LEARN) et retentez plus tard.", "Study (LEARN) and retry later.")]
        elif self.passed:
            msg = [_L(f"Félicitations. Nouveau grade : {p.grade}.", f"Congratulations. New grade: {p.grade}."),
                   _L("+8 réputation.", "+8 reputation.")]
            if self.new_title:
                msg.append(_L(f"Titre débloqué : « {self.new_title} » !", f"Title unlocked: “{self.new_title}”!"))
            if p.flags.get("can_choose_track"):
                msg.append(_L("Vous pouvez choisir une VOIE (TRACK).", "You can choose a TRACK."))
        else:
            msg = [_L(f"Seuil non atteint ({int(self.pass_threshold*100)}% requis).", f"Threshold not met ({int(self.pass_threshold*100)}% required)."),
                   _L("−5 réputation. Révisez (LEARN) et retentez.", "−5 reputation. Study (LEARN) and retry."),
                   _L("Astuce : utilisez la calculatrice et le glossaire (DEFINE).", "Tip: use the calculator and the glossary (DEFINE).")]
        from core.i18n import get_lang as _get_lang
        from data import lessons as lessons_data
        _lang = _get_lang()
        titles = [lessons_data.title_for(lid, _lang) for lid in self.missed_lessons if lessons_data.get(lid)]
        shown = titles[:6]

        panel = pygame.Rect(rect.x + max(20, rect.w // 8), rect.y + 56,
                            rect.w - 2 * max(20, rect.w // 8), rect.h - 56 - 54)
        inner = widgets.draw_panel(surf, panel, _L("Résultat", "Result"), accent)
        cx = panel.centerx
        widgets.draw_text(surf, verdict, (cx, inner.y + 6), fonts.body(bold=True), accent, align="center")
        widgets.draw_text(surf, _L(f"Score : {self.score} / {len(self.items)}  ({int(ratio*100)}%)",
                                   f"Score: {self.score} / {len(self.items)}  ({int(ratio*100)}%)"),
                          (cx, inner.y + 34), fonts.small(bold=True), config.COL_WHITE, align="center")
        y = inner.y + 66
        for m in msg:
            if y > inner.bottom - 24:
                break
            widgets.draw_text(surf, widgets.fit_text(m, fonts.tiny(), inner.w), (cx, y),
                              fonts.tiny(), config.COL_TEXT, align="center")
            y += 20
        if shown and y < inner.bottom - 40:
            y += 6
            widgets.draw_text(surf, _L("À revoir (LEARN) :", "Review (LEARN):"), (cx, y),
                              fonts.tiny(bold=True), config.COL_AMBER, align="center")
            y += 18
            for t in shown:
                if y > inner.bottom - 4:
                    break
                widgets.draw_text(surf, "• " + t, (cx, y), fonts.tiny(), config.COL_TEXT_DIM, align="center")
                y += 16
        self._draw_continue(surf, rect, _L("TERMINER", "FINISH"))
