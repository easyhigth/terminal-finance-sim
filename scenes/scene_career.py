"""
scene_career.py — Tableau de bord de carrière.

Regroupe en un écran : l'échelle des 12 grades (progression), la roadmap de
promotion (critères combinés), les objectifs du trimestre (avec barres de
progression), les statistiques de run et le journal de carrière.

Ouvert via CAREER / ROADMAP / OBJECTIVES / HISTORY depuis le terminal.
"""
import pygame

from core import badges as badges_mod
from core import career, config
from core import difficulty as difficulty_mod
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr

_KIND_COLORS = {
    "promo": config.COL_UP, "deal": config.COL_DEAL, "crisis": config.COL_DOWN,
    "objective": config.COL_CYAN, "info": config.COL_TEXT_DIM,
}


class CareerScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.app.gs.player.flags["onboarding_seen_career"] = True
        career.ensure_objectives(self.app.gs.player)
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.rivals_btn = widgets.Button(
            (config.SCREEN_WIDTH - 40 - 160, 60, 160, 32), _L("RIVAUX →", "RIVALS →"), config.COL_PRESTIGE)
        self.achievements_btn = widgets.Button(
            (config.SCREEN_WIDTH - 40 - 340, 60, 170, 32), _L("SUCCÈS →", "ACHIEVEMENTS →"), config.COL_PRESTIGE)
        self.unlocks_btn = widgets.Button(
            (config.SCREEN_WIDTH - 40 - 560, 60, 210, 32), _L("DÉBLOCAGES →", "UNLOCKS →"), config.COL_PRESTIGE)
        # fondation de firme (endgame, grade max) — cf. core/founding.py
        self.found_prompt = False
        self.found_buf = ""
        self._found_btn_rect = None
        self._found_box_rect = None

    def handle_event(self, event):
        from core import founding
        p = self.app.gs.player
        # boîte modale « nom de votre firme » : capture tout en premier
        if self.found_prompt:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.found_prompt = False
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    res = founding.found(p, self.found_buf)
                    if res["ok"]:
                        self.found_prompt = False
                        self.app.notify(_L(f"{p.firm_name} est née. À vous de jouer, fondateur.", f"{p.firm_name} is born. Your move, founder."), "good")
                    else:
                        self.app.notify(_L("Il faut un nom.", "A name is required."), "warn")
                elif event.key == pygame.K_BACKSPACE:
                    self.found_buf = self.found_buf[:-1]
                elif event.unicode and event.unicode.isprintable() and len(self.found_buf) < 24:
                    self.found_buf += event.unicode
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._found_btn_rect and self._found_btn_rect.collidepoint(event.pos):
                ok, reason = founding.can_found(p)
                if ok:
                    self.found_prompt = True
                    self.found_buf = ""
                elif reason == "cash":
                    self.app.notify(_L(f"Fonder sa firme coûte {widgets.format_money(founding.FOUNDING_COST, '$')} — ",
                                       f"Founding your firm costs {widgets.format_money(founding.FOUNDING_COST, '$')} — ") +
                                    _L("capital insuffisant.", "insufficient capital."), "warn")
                return
            from core import focus as focus_mod
            for key, r in getattr(self, "_focus_rects", {}).items():
                if r.collidepoint(event.pos):
                    p = self.app.gs.player
                    res = focus_mod.set_focus(p, None if focus_mod.current(p) == key else key)
                    if not res["ok"] and res["reason"] == "quarter":
                        self.app.notify(_L("Focus déjà changé ce trimestre — patience.", "Focus already changed this quarter — be patient."), "warn")
                    return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if self.rivals_btn.handle(event):
            self.app.scenes.go("rivals", return_to="career")
        if self.achievements_btn.handle(event):
            self.app.scenes.go("achievements", return_to="career")
        if self.unlocks_btn.handle(event):
            self.app.scenes.go("unlockhistory", return_to="career")

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        self.rivals_btn.update(pygame.mouse.get_pos(), dt)
        self.achievements_btn.update(pygame.mouse.get_pos(), dt)
        self.unlocks_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, _L("CARRIÈRE", "CAREER"), (40, 22), fonts.title(bold=True), config.COL_AMBER)
        sub = f"{p.name} · {p.grade} · {config.career_phase(p.grade_index)}"
        if p.track != "General":
            sub += _L(f" · voie {p.track}", f" · {p.track} track")
        widgets.draw_text(surf, sub, (42, 72), fonts.small(), config.COL_TEXT_DIM)
        if p.titles:
            widgets.draw_text(surf, _L("Titres : ", "Titles: ") + " · ".join(p.titles),
                              (config.SCREEN_WIDTH - 40, 30), fonts.small(bold=True),
                              config.COL_WARN, align="right")
        status = difficulty_mod.status_label(p)
        if status:
            widgets.draw_badge(surf, status.upper(), (config.SCREEN_WIDTH - 40, 96),
                               config.COL_PRESTIGE, align="right")

        M = config.MARGIN
        top = 100
        bottom = config.footer_y() - 8
        colw = (config.SCREEN_WIDTH - 4 * M) // 3
        x1, x2, x3 = M, M * 2 + colw, M * 3 + colw * 2
        # journal en bas pleine largeur ; panneaux du haut au-dessus
        journal_h = 140
        gap = 12
        row_h = bottom - top - journal_h - gap
        road_h = int(row_h * 0.54)
        stats_h = row_h - road_h - gap
        self._draw_ladder(surf, pygame.Rect(x1, top, colw, row_h), p)
        self._draw_roadmap(surf, pygame.Rect(x2, top, colw, road_h), p)
        self._draw_stats(surf, pygame.Rect(x2, top + road_h + gap, colw, stats_h), p)
        self._draw_objectives(surf, pygame.Rect(x3, top, colw, row_h), p)
        self._draw_journal(surf, pygame.Rect(x1, top + row_h + gap,
                                             config.SCREEN_WIDTH - 2 * M, journal_h), p)
        self._draw_focus_bar(surf, p)
        self._draw_founding(surf, p)

        self.back_btn.draw(surf)
        self.rivals_btn.draw(surf)
        self.achievements_btn.draw(surf)
        self.unlocks_btn.draw(surf)

    def _draw_founding(self, surf, p):
        """Bouton « FONDER MA FIRME » (grade max, cf. core/founding.py) puis
        boîte modale de nom. Une firme déjà fondée s'affiche en en-tête."""
        from core import founding
        self._found_btn_rect = None
        if founding.founded(p):
            widgets.draw_badge(surf, p.firm_name.upper(),
                               (config.SCREEN_WIDTH - 40, 130),
                               config.COL_PRESTIGE, align="right")
            return
        ok, reason = founding.can_found(p)
        if reason == "grade":
            return   # pas encore Partner : le bouton n'existe pas
        r = pygame.Rect(config.SCREEN_WIDTH - 40 - 220, 122, 220, 30)
        self._found_btn_rect = r
        hov = r.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL,
                         r, border_radius=4)
        pygame.draw.rect(surf, config.COL_PRESTIGE, r, 2, border_radius=4)
        widgets.draw_text(surf, _L("FONDER MA FIRME", "FOUND MY FIRM"), r.center,
                          fonts.small(bold=True), config.COL_PRESTIGE, align="center")
        if self.found_prompt:
            box = pygame.Rect(config.SCREEN_WIDTH // 2 - 240,
                              config.SCREEN_HEIGHT // 2 - 60, 480, 120)
            self._found_box_rect = box
            pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=6)
            pygame.draw.rect(surf, config.COL_PRESTIGE, box, 2, border_radius=6)
            widgets.draw_text(surf, _L("LE NOM DE VOTRE FIRME", "YOUR FIRM'S NAME"),
                              (box.centerx, box.y + 18), fonts.small(bold=True),
                              config.COL_PRESTIGE, align="center")
            import time as _time
            cursor = "_" if int(_time.time() * 2) % 2 == 0 else ""
            widgets.draw_text(surf, (self.found_buf or "") + cursor,
                              (box.centerx, box.y + 52), fonts.head(bold=True),
                              config.COL_TEXT, align="center")
            widgets.draw_text(surf,
                              _L(f"Coût : {widgets.format_money(4_000_000, '$')} · ENTRÉE valider · ÉCHAP annuler",
                                 f"Cost: {widgets.format_money(4_000_000, '$')} · ENTER confirm · ESC cancel"),
                              (box.centerx, box.y + 92), fonts.tiny(),
                              config.COL_TEXT_DIM, align="center")

    def _draw_focus_bar(self, surf, p):
        """FOCUS DU TRIMESTRE (core/focus.py) : où passez-vous vos journées ?
        Un clic choisit l'axe (re-clic = aucun) ; un seul changement par
        trimestre. Rangée compacte dans l'en-tête, à côté du sous-titre."""
        from core import focus as focus_mod
        self._focus_rects = {}
        x = 420
        y = 68
        widgets.draw_text(surf, _L("FOCUS DU TRIMESTRE", "QUARTER FOCUS"), (x, y - 14),
                          fonts.tiny(bold=True), config.COL_CYAN)
        current = focus_mod.current(p)
        mp = pygame.mouse.get_pos()
        hovered = None
        for key in focus_mod.FOCUS:
            lbl = focus_mod.label(key)
            w = fonts.tiny(bold=True).size(lbl)[0] + 16
            r = pygame.Rect(x, y, w, 20)
            sel = key == current
            hov = r.collidepoint(mp)
            if hov:
                hovered = key
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (sel or hov) else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 2 if sel else 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM, align="center")
            self._focus_rects[key] = r
            x += w + 6
        if not focus_mod.can_change(p):
            widgets.draw_text(surf, _L("changé ce trimestre", "changed this quarter"), (x + 6, y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
        if hovered:
            widgets.draw_tooltip(surf, focus_mod.desc(hovered), mp)

    def _draw_ladder(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L("Échelle des grades", "Grade ladder"), config.COL_AMBER)
        y = inner.y
        for i, g in enumerate(config.GRADES):
            cur = (i == p.grade_index)
            done = (i < p.grade_index)
            if cur:
                col, marker = config.COL_AMBER, "▶"
            elif done:
                col, marker = config.COL_UP, "✓"
            else:
                col, marker = config.COL_TEXT_DIM, "·"
            widgets.draw_text(surf, f"{marker} {g}", (inner.x, y),
                              fonts.small(bold=cur), col)
            y += 21
        # galerie de badges sous l'échelle
        y += 8
        widgets.draw_text(surf, f"BADGES ({len(p.badges)}/{len(badges_mod.all_badges())})",
                          (inner.x, y), fonts.small(bold=True), config.COL_PRESTIGE)
        y += 22
        if not p.badges:
            widgets.draw_text(surf, "Aucun pour l'instant.", (inner.x, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
        else:
            x = inner.x
            mp = pygame.mouse.get_pos()
            self._badge_hover_desc = None
            for bid in p.badges:
                b = badges_mod.get(bid)
                if not b:
                    continue
                r = widgets.draw_badge(surf, badges_mod.badge_name(b), (x, y), config.COL_PRESTIGE)
                if r.collidepoint(mp):
                    self._badge_hover_desc = badges_mod.badge_desc(b)
                x = r.right + 6
                if x > inner.right - 90:
                    x = inner.x
                    y += r.height + 6
            if self._badge_hover_desc:
                widgets.draw_tooltip(surf, self._badge_hover_desc, mp)

    def _draw_roadmap(self, surf, rect, p):
        ready = career.promotion_ready(p)
        accent = config.COL_UP if ready else config.COL_WARN
        inner = widgets.draw_panel(surf, rect, _L("Roadmap de promotion", "Promotion roadmap"), accent)
        if not p.can_promote():
            widgets.draw_text(surf, _L("Grade maximal atteint.", "Top grade reached."), (inner.x, inner.y),
                              fonts.body(bold=True), config.COL_UP)
            return
        y = inner.y
        for r in career.promotion_requirements(p):
            mark = "✓" if r["met"] else "○"
            col = config.COL_UP if r["met"] else config.COL_TEXT
            label = r["label"]
            if not r["met"] and r["label"].startswith("Ancienneté") :
                next_q = p.grade_start_quarter + int(r["target"])
                days_left = max(0, (next_q - 1) * config.DAYS_PER_QUARTER + 1 - p.day)
                label += f" (encore {days_left} j)"
            # libellé borné : les intitulés longs (« Voie de spécialisation
            # choisie (TRACK) », ancienneté avec compte à rebours…) passaient
            # SOUS la valeur x/y et débordaient même du panneau (le rendu
            # n'est pas clippé au rect du panneau).
            widgets.draw_text(surf, widgets.fit_text(f"{mark} {label}", fonts.small(), inner.w - 56),
                              (inner.x, y), fonts.small(), col)
            widgets.draw_text(surf, f"{int(r['current'])}/{int(r['target'])}",
                              (inner.right, y), fonts.small(bold=True),
                              col, align="right")
            y += 20
            ratio = 1.0 if r["met"] else (max(0.0, r["current"]) / r["target"] if r["target"] else 1.0)
            widgets.draw_progress(surf, (inner.x, y, inner.w, 6), ratio,
                                  config.COL_UP if r["met"] else config.COL_WARN)
            y += 18
        y += 6
        if ready:
            widgets.draw_text(surf, _L("✓ Critères remplis — tapez EVAL pour l'examen.", "✓ Criteria met — type EVAL for the exam."),
                              (inner.x, y), fonts.small(bold=True), config.COL_UP)
        else:
            widgets.draw_text(surf, widgets.fit_text(_L("Manque : ", "Missing: ") + ", ".join(career.missing_criteria(p)),
                                                     fonts.tiny(), inner.w),
                              (inner.x, y), fonts.tiny(), config.COL_WARN)

    def _draw_stats(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L("Statistiques de run", "Run statistics"), config.COL_CYAN)
        cur = config.CONTINENTS[p.continent]["currency"]
        profile = career.risk_profile(p)
        profile_col = {"Risque élevé": config.COL_DOWN, "Modéré": config.COL_WARN,  # noqa: keys from career.risk_profile
                       "Prudent": config.COL_UP}.get(profile, config.COL_TEXT)
        rows = [
            (_L("Trésorerie", "Cash"), widgets.format_money(p.cash, cur), config.COL_WHITE),
            (_L("Record trésorerie", "Peak cash"), widgets.format_money(max(p.best_cash, p.cash), cur), config.COL_WHITE),
            (_L("Réputation", "Reputation"), f"{p.reputation}/100", config.COL_WHITE),
            (_L("Profil de risque", "Risk profile"), profile, profile_col),
            (_L("Deals conclus", "Deals won"), str(p.deals_won), config.COL_WHITE),
            (_L("Missions réalisées", "Missions done"), str(p.missions_done), config.COL_WHITE),
            (_L("Scrutin réglementaire", "Regulatory scrutiny"), f"{p.heat}/100", config.COL_WHITE),
            (_L("Temps", "Time"), _L(f"jour {p.day} (T{p.quarter})", f"day {p.day} (Q{p.quarter})"), config.COL_WHITE),
        ]
        # réputation SEGMENTÉE par métier + momentum de carrière : n'apparaissent
        # qu'une fois pertinents (voie choisie / série en cours), pour garder la
        # vue épurée en début de partie (cf. core/track_rep, core/momentum).
        from core import momentum as _momentum
        from core import track_rep as _trep
        dom_track, dom_pts = _trep.dominant(p)
        if dom_track:
            is_spec = _trep.specialist_track(p) == dom_track
            val = f"{dom_track} {dom_pts}" + (_L(" — spécialiste", " — specialist") if is_spec else "")
            rows.append((_L("Réputation-métier", "Track reputation"), val,
                         config.COL_PRESTIGE if is_spec else config.COL_WHITE))
        mom_label = _momentum.label(p)
        if mom_label:
            mcol = config.COL_UP if _momentum.status(p) == "hot" else config.COL_DOWN
            rows.append((_L("Momentum", "Momentum"), mom_label, mcol))
        # pas de ligne adaptatif : toutes les lignes tiennent dans le panneau
        # (plancher abaissé à 15 px — à 18, la dernière ligne « Temps » était
        # coupée par le bord bas du panneau)
        step = max(15, min(25, inner.h // len(rows)))
        y = inner.y
        for label, val, col in rows:
            widgets.draw_text(surf, label, (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (inner.right, y), fonts.small(bold=True),
                              col, align="right")
            y += step

    def _draw_objectives(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L(f"Objectifs — T{p.quarter}", f"Objectives — Q{p.quarter}"), config.COL_DEAL)
        if not p.objectives:
            widgets.draw_text(surf, "Aucun objectif (avancez le temps).", (inner.x, inner.y),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        y = inner.y
        for o in p.objectives:
            cur, target, ok = career.objective_progress(p, o)
            col = config.COL_UP if ok else config.COL_TEXT
            widgets.draw_text(surf, ("✓ " if ok else "○ ") + career.objective_label(p, o),
                              (inner.x, y), fonts.small(), col)
            # barre de progression (bornée)
            ratio = 1.0 if ok else (max(0.0, cur) / target if target else 0.0)
            widgets.draw_progress(surf, (inner.x, y + 20, inner.w, 6), ratio,
                                  config.COL_UP if ok else config.COL_DEAL)
            y += 40
        y += 6
        widgets.draw_text(surf, _L("Récompense par objectif : +réputation & honoraire.", "Reward per objective: +reputation & fee."),
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "Trimestre parfait = bonus de prestige.",
                          (inner.x, y + 16), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_journal(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L("Journal de carrière", "Career journal"), config.COL_AMBER)
        if not p.journal:
            widgets.draw_text(surf, _L("Votre histoire s'écrira ici : promotions, deals, crises…", "Your story will unfold here: promotions, deals, crises…"),
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return
        # deux colonnes d'entrées récentes (les plus récentes en haut) ; le nombre
        # de lignes par colonne s'adapte à la hauteur du panneau (anti-débordement)
        line_h = 22
        rows_per_col = max(1, inner.h // line_h)
        entries = list(reversed(p.journal))[:rows_per_col * 2]
        colw = inner.w // 2 - 10
        for i, e in enumerate(entries):
            col = i // rows_per_col
            row = i % rows_per_col
            x = inner.x + col * (colw + 20)
            y = inner.y + row * line_h
            tag = _KIND_COLORS.get(e["kind"], config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"J{e['day']}", (x, y), fonts.tiny(bold=True), tag)
            font = fonts.tiny()
            widgets.draw_text(surf, widgets.fit_text(e["text"], font, colw - 46),
                              (x + 46, y), font, config.COL_TEXT)
