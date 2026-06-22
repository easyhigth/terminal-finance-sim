"""
scene_evaluation.py — Examen de promotion (quiz multi-types, niveau « entretien »).

Questions générées par core/exam.py : calculs chiffrés, QCM, lecture de graphe,
définitions à trous et formules à compléter — 20 à 30 selon le grade, jamais les
mêmes. Calculatrice intégrée, bouton SUIVANT, explication après chaque réponse.
Réussite (≥ seuil) → promotion.
"""
import pygame

from core import config, exam
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets

CHART_COLORS = {"A": config.COL_CYAN, "B": config.COL_AMBER}


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante."""
    return en if get_lang() == "en" else fr


class EvaluationScene(Scene):
    # examen en cours : pas de page dédiée, changement d'onglet bloqué (anti-triche)
    pageable = False

    def on_enter(self, **kwargs):
        self.t = 0.0
        p = self.app.gs.player
        self.cert_program = kwargs.get("program")
        self.cert_level = kwargs.get("level", 0)
        self.mode = kwargs.get("mode", "promotion")
        self.return_to = kwargs.get("return_to", "terminal")
        saved = p.eval_state if isinstance(p.eval_state, dict) else {}
        resume = bool(saved) and saved.get("mode") == self.mode and saved.get("items")
        if resume:
            # reprise d'un examen mis en pause : on retrouve EXACTEMENT où on était
            self.items = saved["items"]
            self.idx = saved.get("idx", 0)
            self.score = saved.get("score", 0)
            self.missed_lessons = list(saved.get("missed_lessons", []))
            self.pass_threshold = saved.get("pass_threshold", exam.PASS_THRESHOLD)
            self.target_grade = saved.get("target_grade", "")
            self.cert_program = saved.get("cert_program", self.cert_program)
            self.cert_level = saved.get("cert_level", self.cert_level)
            self.return_to = saved.get("return_to", self.return_to)
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
            self.missed_lessons = []    # ids de leçons des questions ratées (débrief)
            self.state = "intro"        # intro -> question -> feedback -> result
        self.chosen = None          # index mcq choisi
        self.input = ""             # saisie fill/text
        self.submitted_ok = None
        self.answer_rects = {}
        self.passed = False
        self.new_title = None
        self.calc = None
        fy = config.SCREEN_HEIGHT - 56
        self.continue_btn = widgets.Button((config.SCREEN_WIDTH//2-130, fy, 260, 44),
                                           (_L("REPRENDRE","RESUME") if resume else _L("COMMENCER","START")), config.COL_UP)
        self.back_btn = widgets.Button(config.back_button_rect(150), _L("← QUITTER","← QUIT"),
                                       config.COL_TEXT_DIM)
        self.calc_btn = widgets.Button((200, config.SCREEN_HEIGHT-50, 160, 42),
                                       _L("CALCULATRICE","CALCULATOR"), config.COL_CYAN)
        self.pause_btn = widgets.Button((372, config.SCREEN_HEIGHT-50, 150, 42),
                                        "PAUSE", config.COL_WARN)

    def _pause(self):
        """Sauvegarde la progression de l'examen pour reprendre plus tard."""
        p = self.app.gs.player
        p.eval_state = {
            "mode": self.mode, "items": self.items, "idx": self.idx,
            "score": self.score, "missed_lessons": list(self.missed_lessons),
            "pass_threshold": self.pass_threshold, "target_grade": self.target_grade,
            "cert_program": self.cert_program, "cert_level": self.cert_level,
            "return_to": self.return_to,
        }
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        self.app.notify(_L("Examen mis en pause — reprenez via EVAL","Exam paused — resume via EVAL"), "info")
        self.app.scenes.go(self.return_to)

    # ------------------------------------------------------------- helpers
    def _item(self):
        return self.items[self.idx] if 0 <= self.idx < len(self.items) else None

    def _is_mcq(self, it):
        return it["kind"] == "mcq" or (it["kind"] == "graph" and it.get("subkind") == "mcq")

    def _is_input(self, it):
        return it["kind"] in ("fill", "text") or \
            (it["kind"] == "graph" and it.get("subkind") == "fill")

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if self.calc is not None and self.calc.handle(event):
            if self.calc.closed:
                self.calc = None
            return
        if self.calc_btn.handle(event):
            if self.calc is None:
                from ui.calculator import Calculator
                self.calc = Calculator(pos=(config.SCREEN_WIDTH - 260, 110))
            else:
                self.calc = None
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.state in ("question", "feedback") and self.pause_btn.handle(event):
            self._pause()
            return

        it = self._item()
        if event.type == pygame.KEYDOWN:
            if self.state == "question" and it is not None and self._is_input(it):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._submit(it)
                elif event.key == pygame.K_BACKSPACE:
                    self.input = self.input[:-1]
                else:
                    self._type(it, event.unicode)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._advance_via_key()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "intro" and self.continue_btn.rect.collidepoint(event.pos):
                self.state = "question"
            elif self.state == "question" and it is not None and self._is_mcq(it):
                for i, rect in self.answer_rects.items():
                    if rect.collidepoint(event.pos):
                        self._answer_mcq(i, it)
            elif self.state == "feedback" and self.continue_btn.rect.collidepoint(event.pos):
                self._next()
            elif self.state == "result" and self.continue_btn.rect.collidepoint(event.pos):
                self.app.scenes.go(self.return_to)

    def _type(self, it, ch):
        if not ch:
            return
        if it["kind"] == "text":
            if ch.isalnum() or ch in " /.-'éèàçâêôûïü":
                self.input += ch
        else:  # fill numérique
            if ch.isdigit() or ch in ".,-":
                self.input += ("." if ch == "," else ch)

    def _advance_via_key(self):
        if self.state == "intro":
            self.state = "question"
        elif self.state == "feedback":
            self._next()
        elif self.state == "result":
            self.app.scenes.go(self.return_to)

    def _answer_mcq(self, i, it):
        self.chosen = i
        if i == it["answer"]:
            self.score += 1
        else:
            self._record_miss(it)
        self.state = "feedback"

    def _record_miss(self, it):
        """Mémorise la leçon liée à une question ratée (pour le débrief final)."""
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
        p.eval_state = {}                 # examen terminé : on efface l'état en pause
        self.app.advance_on_return = 1    # passer une éval fait avancer le temps d'un tic
        ratio = self.score / max(1, len(self.items))
        self.passed = ratio >= self.pass_threshold
        if self.mode == "cert":
            self._finish_cert(p)
            self.app.gs.save(config.AUTOSAVE_SLOT)
            self.state = "result"
            return
        if self.passed and p.can_promote():
            p.promote()
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
            from core import unlocks
            for feat, grade in unlocks.UNLOCKS.items():
                if grade == p.grade_index:
                    self.app.notify(_L(f"⊘→✓ Débloqué : {unlocks.feature_label(feat)}",
                                        f"⊘→✓ Unlocked: {unlocks.feature_label(feat)}"), "good")
                    tid = unlocks.FEATURE_TUTORIAL.get(feat)
                    if tid and not p.flags.get("pending_tutorial"):
                        p.flags["pending_tutorial"] = tid
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
        mp = pygame.mouse.get_pos()
        self.continue_btn.update(mp, dt)
        self.back_btn.update(mp, dt)
        self.calc_btn.update(mp, dt)
        self.pause_btn.update(mp, dt)

    # --------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        title = _L("EXAMEN DE CERTIFICATION","CERTIFICATION EXAM") if self.mode == "cert" else _L("ÉVALUATION DE PROMOTION","PROMOTION EXAM")
        widgets.draw_text(surf, title, (40, 22), fonts.title(bold=True), config.COL_AMBER)
        sub = (_L(f"{self.target_grade}    |    Voie : {p.track}", f"{self.target_grade}    |    Track: {p.track}") if self.mode == "cert"
               else _L(f"{p.grade}  →  {self.target_grade}    |    Voie : {p.track}", f"{p.grade}  →  {self.target_grade}    |    Track: {p.track}"))
        widgets.draw_text(surf, sub, (42, 72), fonts.small(), config.COL_TEXT_DIM)
        if self.state == "intro":
            self._draw_intro(surf)
        elif self.state in ("question", "feedback"):
            self._draw_item(surf)
        elif self.state == "result":
            self._draw_result(surf)
        self.back_btn.draw(surf)
        if self.state in ("question", "feedback"):
            self.calc_btn.draw(surf)
            self.pause_btn.draw(surf)
        if self.calc is not None:
            self.calc.draw(surf)

    def _draw_intro(self, surf):
        panel = pygame.Rect(120, 110, config.SCREEN_WIDTH-240, config.footer_y()-120)
        inner = widgets.draw_panel(surf, panel, "Brief", config.COL_CYAN)
        p = self.app.gs.player
        if self.mode == "cert":
            intro1 = _L(f"Examen de certification — {self.target_grade}.", f"Certification exam — {self.target_grade}.")
            bank_line = _L(f"{len(self.items)} questions exigeantes, banque dédiée.", f"{len(self.items)} demanding questions, dedicated bank.")
        else:
            intro1 = _L(f"Entretien technique pour le poste de {self.target_grade}.", f"Technical interview for the {self.target_grade} role.")
            bank_line = _L(f"{len(self.items)} questions tirées d'une banque d'environ {exam.bank_target(p.grade_index)} pour ce grade.", f"{len(self.items)} questions drawn from a bank of about {exam.bank_target(p.grade_index)} for this grade.")
        lines = [
            intro1,
            "",
            bank_line,
            _L("Types : calculs, QCM, lecture de graphe, définitions et formules à trous.", "Types: calculations, MCQ, chart reading, fill-in definitions and formulas."),
            _L(f"Seuil de réussite : {int(self.pass_threshold*100)}%.", f"Pass threshold: {int(self.pass_threshold*100)}%."),
            "",
            _L("Calcul : tapez votre nombre.  Définition/formule : tapez le ou les mots.", "Calculation: type your number.  Definition/formula: type the word(s)."),
            _L("QCM : cliquez la bonne réponse.  Une CALCULATRICE est disponible.", "MCQ: click the right answer.  A CALCULATOR is available."),
            "",
            _L("Réussite → promotion (+réputation).  Échec → −réputation, à retenter.", "Pass → promotion (+reputation).  Fail → −reputation, retry later."),
        ]
        y = inner.y
        for ln in lines:
            widgets.draw_text(surf, ln, (inner.x, y), fonts.body(), config.COL_TEXT)
            y += 30
        self.continue_btn.label = _L("COMMENCER","START")
        self.continue_btn.draw(surf)

    def _draw_item(self, surf):
        it = self._item()
        pw = config.SCREEN_WIDTH - 240
        n = len(self.items)
        widgets.draw_text(surf, f"Question {self.idx+1} / {n}", (120, 102),
                          fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_progress(surf, (120, 122, pw, 6), self.idx / n, config.COL_AMBER)

        has_chart = bool(it.get("charts"))
        prompt_w = pw if not has_chart else int(pw * 0.5)
        if has_chart:
            self._draw_charts(surf, it, pygame.Rect(120 + prompt_w + 20, 138,
                                                    pw - prompt_w - 20, 250))
        # énoncé
        ppanel = pygame.Rect(120, 138, prompt_w, 118)
        pinner = widgets.draw_panel(surf, ppanel, _L("Énoncé","Prompt"), config.COL_AMBER)
        widgets.draw_text_wrapped(surf, it["prompt"], (pinner.x, pinner.y),
                                  fonts.body(), config.COL_WHITE, pinner.w, line_gap=5)

        if self._is_mcq(it):
            self._draw_mcq(surf, it, prompt_w)
        else:
            self._draw_input(surf, it, prompt_w)

        if self.state == "feedback":
            self._draw_feedback(surf, it)

    def _draw_charts(self, surf, it, rect):
        inner = widgets.draw_panel(surf, rect, _L("Cours","Price"), config.COL_CYAN)
        names = ["A", "B"] if it.get("chart") == "AB" else [it.get("chart", "A")]
        series = [it["charts"][nm] for nm in names if it["charts"].get(nm)]
        y_margin = 38
        plot = pygame.Rect(inner.x + y_margin, inner.y + 8, inner.w - y_margin, inner.h - 36)
        if series:
            lo = min(min(s) for s in series)
            hi = max(max(s) for s in series)
            pad = (hi - lo) * 0.08 or 1.0
            lo, hi, span = widgets.draw_chart_axes(surf, plot, lo - pad, hi + pad,
                                                    y_fmt=lambda v: f"{v:.0f}")
            n = max(len(s) for s in series)
            widgets.draw_text(surf, _L("J0","D0"), (plot.x, plot.bottom + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, _L(f"J{n-1}", f"D{n-1}"), (plot.right - 28, plot.bottom + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        for nm in names:
            s = it["charts"].get(nm)
            if not s:
                continue
            col = CHART_COLORS.get(nm, config.COL_CYAN)
            widgets.draw_series(surf, plot, s, col, baseline=False)
            x0, x1 = plot.x, plot.right
            y0 = plot.bottom - int((s[0] - lo) / span * plot.h)
            y1 = plot.bottom - int((s[-1] - lo) / span * plot.h)
            widgets.draw_text(surf, f"{s[0]:.0f}", (x0 + 4, y0 - 16), fonts.tiny(bold=True), col)
            widgets.draw_text(surf, f"{s[-1]:.0f}", (x1 - 32, y1 - 16), fonts.tiny(bold=True), col)
        lx = inner.x
        for nm in names:
            widgets.draw_text(surf, _L(f"■ Titre {nm}", f"■ Stock {nm}"), (lx, inner.bottom-18),
                              fonts.small(bold=True), CHART_COLORS.get(nm, config.COL_CYAN))
            lx += 110

    def _draw_mcq(self, surf, it, width):
        self.answer_rects = {}
        y = 268
        for i, choice in enumerate(it["choices"]):
            rect = pygame.Rect(120, y, width, 46)
            self.answer_rects[i] = rect
            if self.state == "feedback":
                if i == it["answer"]:
                    bg, border, txt = (16, 40, 26), config.COL_UP, config.COL_UP
                elif i == self.chosen:
                    bg, border, txt = (40, 16, 18), config.COL_DOWN, config.COL_DOWN
                else:
                    bg, border, txt = config.COL_PANEL, config.COL_BORDER, config.COL_TEXT_DIM
            else:
                hover = rect.collidepoint(pygame.mouse.get_pos())
                bg = config.COL_PANEL_HEAD if hover else config.COL_PANEL
                border = config.COL_CYAN if hover else config.COL_AMBER
                txt = config.COL_WHITE if hover else config.COL_TEXT
            pygame.draw.rect(surf, bg, rect)
            pygame.draw.rect(surf, border, rect, 1)
            widgets.draw_text(surf, f"{chr(65+i)}.", (rect.x+12, rect.y+12),
                              fonts.body(bold=True), border)
            widgets.draw_text_wrapped(surf, choice, (rect.x+46, rect.y+6),
                                      fonts.small(), txt, rect.w-60)
            y += 52

    def _draw_input(self, surf, it, width):
        kind = _L("Réponse (texte)","Answer (text)") if it["kind"] == "text" else _L("Réponse (nombre)","Answer (number)")
        widgets.draw_text(surf, kind, (120, 266), fonts.small(bold=True), config.COL_TEXT_DIM)
        active = self.state == "question"
        box = pygame.Rect(120, 290, min(520, width), 50)
        pygame.draw.rect(surf, (6, 8, 12), box)
        pygame.draw.rect(surf, config.COL_CYAN if active else config.COL_BORDER, box, 2 if active else 1)
        cur = "_" if (active and int(self.t*2) % 2 == 0) else ""
        shown = (self.input or "") + cur
        widgets.draw_text(surf, shown or _L("tapez votre réponse…","type your answer…"), (box.x+12, box.y+14),
                          fonts.head(bold=True),
                          config.COL_WHITE if self.input else config.COL_TEXT_DIM)
        if it.get("unit"):
            widgets.draw_text(surf, it["unit"], (box.right+12, box.y+14), fonts.head(),
                              config.COL_TEXT_DIM)
        widgets.draw_text(surf, _L("Entrée pour valider.","Press Enter to submit."), (box.x, box.bottom+8),
                          fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_feedback(self, surf, it):
        if self._is_mcq(it):
            ok = (self.chosen == it["answer"])
        else:
            ok = bool(self.submitted_ok)
        y = config.footer_y() - 8
        exp = pygame.Rect(120, 360, config.SCREEN_WIDTH-240, y-360-8)
        inner = widgets.draw_panel(surf, exp, _L("Correction","Feedback"), config.COL_CYAN)
        widgets.draw_text(surf, _L("✓ Bonne réponse","✓ Correct") if ok else _L("✗ Mauvaise réponse","✗ Wrong"),
                          (inner.x, inner.y), fonts.small(bold=True),
                          config.COL_UP if ok else config.COL_DOWN)
        if not ok and self._is_input(it):
            exp_ans = (", ".join(it["answers"]) if it["kind"] == "text"
                       else f"{it['answer']:.2f} {it.get('unit','')}")
            widgets.draw_text(surf, _L("Attendu : ","Expected: ") + exp_ans, (inner.x+180, inner.y),
                              fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text_wrapped(surf, it["expl"], (inner.x, inner.y+24),
                                  fonts.small(), config.COL_TEXT, inner.w)
        self.continue_btn.label = _L("SUIVANT","NEXT") if self.idx < len(self.items)-1 else _L("VOIR RÉSULTAT","SEE RESULT")
        self.continue_btn.draw(surf)

    def _draw_result(self, surf):
        ratio = self.score / max(1, len(self.items))
        accent = config.COL_UP if self.passed else config.COL_DOWN
        p = self.app.gs.player
        if self.mode == "cert":
            verdict = _L("CERTIFICATION RÉUSSIE","CERTIFICATION PASSED") if self.passed else _L("EXAMEN ÉCHOUÉ","EXAM FAILED")
        else:
            verdict = _L("PROMOTION ACCORDÉE","PROMOTION GRANTED") if self.passed else _L("ÉVALUATION ÉCHOUÉE","EVALUATION FAILED")
        if self.mode == "cert":
            from core import certifications as C
            prog = C.PROGRAMS[self.cert_program]
            if self.passed:
                msg = [f"{prog['name']} — {C.status_label(p, self.cert_program)}.",
                       _L("Réputation accrue.","Reputation boosted.")]
                if self.new_title:
                    msg.append(_L(f"Titre : « {self.new_title} » !", f"Title: “{self.new_title}”!"))
            else:
                msg = [_L(f"Seuil non atteint ({int(self.pass_threshold*100)}% requis).", f"Threshold not met ({int(self.pass_threshold*100)}% required)."),
                       _L("Les frais d'inscription sont perdus.","The entry fee is forfeited."),
                       _L("Révisez (LEARN) et retentez plus tard.","Study (LEARN) and retry later.")]
        elif self.passed:
            msg = [_L(f"Félicitations. Nouveau grade : {p.grade}.", f"Congratulations. New grade: {p.grade}."), _L("+8 réputation.","+8 reputation.")]
            if self.new_title:
                msg.append(_L(f"Titre débloqué : « {self.new_title} » !", f"Title unlocked: “{self.new_title}”!"))
            if p.flags.get("can_choose_track"):
                msg.append(_L("Vous pouvez choisir une VOIE (TRACK).","You can choose a TRACK."))
        else:
            msg = [_L(f"Seuil non atteint ({int(self.pass_threshold*100)}% requis).", f"Threshold not met ({int(self.pass_threshold*100)}% required)."),
                   _L("−5 réputation. Révisez (LEARN) et retentez.","−5 reputation. Study (LEARN) and retry."),
                   _L("Astuce : utilisez la calculatrice et le glossaire (DEFINE).","Tip: use the calculator and the glossary (DEFINE).")]
        # leçons à revoir d'après les questions ratées
        from core.i18n import get_lang
        from data import lessons as lessons_data
        _lang = get_lang()
        titles = [lessons_data.title_for(lid, _lang) for lid in self.missed_lessons
                  if lessons_data.get(lid)]
        shown = titles[:8]
        # hauteur de panneau adaptée au contenu (anti-chevauchement du bouton)
        lessons_h = (32 + 22 * len(shown) + (20 if len(titles) > len(shown) else 0)
                     if titles else 0)
        panel_h = 150 + 32 * len(msg) + lessons_h + 70
        panel = pygame.Rect(280, max(70, (config.SCREEN_HEIGHT - panel_h) // 2),
                            config.SCREEN_WIDTH - 560, panel_h)
        inner = widgets.draw_panel(surf, panel, _L("Résultat","Result"), accent)
        cx = panel.centerx
        widgets.draw_text(surf, verdict, (cx, inner.y+10), fonts.title(bold=True), accent, align="center")
        widgets.draw_text(surf, _L(f"Score : {self.score} / {len(self.items)}  ({int(ratio*100)}%)", f"Score: {self.score} / {len(self.items)}  ({int(ratio*100)}%)"),
                          (cx, inner.y+62), fonts.head(), config.COL_WHITE, align="center")
        y = inner.y + 120
        for m in msg:
            widgets.draw_text(surf, m, (cx, y), fonts.body(), config.COL_TEXT, align="center")
            y += 32
        if shown:
            y += 6
            widgets.draw_text(surf, _L("À revoir (LEARN) :","Review (LEARN):"), (cx, y),
                              fonts.small(bold=True), config.COL_AMBER, align="center")
            y += 26
            for t in shown:
                widgets.draw_text(surf, "• " + t, (cx, y),
                                  fonts.small(), config.COL_TEXT_DIM, align="center")
                y += 22
            if len(titles) > len(shown):
                widgets.draw_text(surf, _L(f"… et {len(titles)-len(shown)} autre(s)", f"… and {len(titles)-len(shown)} more"),
                                  (cx, y), fonts.tiny(), config.COL_TEXT_DIM, align="center")
                y += 20
        self.continue_btn.rect.center = (cx, inner.bottom-30)
        self.continue_btn.label = _L(f"RETOUR : {self.return_to.upper()}", f"BACK: {self.return_to.upper()}")
        self.continue_btn.draw(surf)
