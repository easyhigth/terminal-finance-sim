"""
scene_gameover.py — Écran de fin de partie (faillite ou réputation anéantie).
Affiche le motif, un récapitulatif de carrière, le score composite de fin de
run (core/score.py), et renvoie au menu.
En mode hardcore, la sauvegarde automatique est effacée (run définitif).
"""
import math

import pygame

from core import audio, challenge_share, config
from core import badges as badges_mod
from core import difficulty as difficulty_mod
from core import hall_of_fame as hof_mod
from core import score as score_mod
from core.game_state import GameState
from core.scene_manager import Scene
from ui import fonts, widgets

# libellés FR courts pour les 7 dimensions du score (cf. core/score.py)
SCORE_DIMENSIONS = [
    ("performance", "Performance"),
    ("risque", "Risque"),
    ("drawdown", "Drawdown"),
    ("reputation", "Réputation"),
    ("conformite", "Conformité"),
    ("qualite_execution", "Exécution"),
    ("survie", "Survie"),
]


def _score_color(v):
    """Couleur du dégradé rouge→ambre→vert selon le score 0-100 (seuils
    alignés sur scenes/scene_ma.py et scenes/scene_ma_target.py : ≥60 vert,
    ≥40 ambre, sinon rouge)."""
    if v >= 60:
        return config.COL_UP
    if v >= 40:
        return config.COL_WARN
    return config.COL_DOWN


class GameOverScene(Scene):
    def on_enter(self, **kwargs):
        self.t = 0.0
        p = self.app.gs.player
        # fin de partie : on ferme tous les autres onglets pour repartir
        # d'un état d'onglets totalement vierge à la prochaine partie.
        self.app.pages.close_other_pages()
        # run définitif en hardcore : on efface l'autosave
        if p.hardcore:
            GameState.delete(config.AUTOSAVE_SLOT)
            # la rotation d'autosaves ne doit pas permettre de ressusciter
            # un run hardcore terminé : on purge aussi les générations.
            for slot in config.AUTOSAVE_HISTORY_SLOTS:
                GameState.delete(slot)
        market = getattr(self.app, "market", None)
        self.score = score_mod.compute_final_score(p, market)
        # panthéon local : le run terminé entre au classement (une seule fois
        # par run — flag joueur — et seulement sur un VRAI game over, pas une
        # simple visite de la scène).
        self.hof_rank = None
        if p.game_over and not p.flags.get("hof_recorded"):
            p.flags["hof_recorded"] = True
            self.hof_rank = hof_mod.record(p, self.score.total)
            if self.hof_rank is not None and self.hof_rank <= 3:
                p.flags["hof_top3"] = True
            # badges dépendant de l'issue de la partie (panthéon...) : plus
            # aucun pas de marché ne sera joué après cet écran, donc c'est
            # ici — pas dans la boucle de jeu — qu'il faut les attribuer.
            if badges_mod.check_new(p, market):
                audio.play("badge")
        self.hof_top = hof_mod.top(5)
        # classement du défi du jour à part (marché différent des runs
        # classiques, comparer les scores mélangés serait trompeur) — FUSIONNE
        # les runs joués localement et les scores d'amis importés (codes
        # texte, cf. core/challenge_share.py) en un seul classement trié ;
        # "mine" se détermine par ID (pas par rang positionnel, qui change au
        # fil des imports) plutôt que via hof_daily_rank.
        self.hof_daily_top = None
        self.hof_daily_rank = None
        self._my_hof_entry_id = p.flags.get("hof_entry_id")
        self._daily_date = p.flags.get("daily_challenge")
        if difficulty_mod.is_daily_challenge(p):
            self.hof_daily_top = hof_mod.combined_daily_ranking(self._daily_date, n=8)
            self.hof_daily_rank = hof_mod.daily_rank(p)
        # code d'export du score de CE run (généré paresseusement au clic sur
        # « Exporter », pas à chaque entrée sur l'écran)
        self._export_code = None
        self._export_rect = None
        self._import_rect = None
        # boîte de saisie du code d'un ami à importer (même pattern que
        # scene_saves.py::path_prompt)
        self.code_prompt = False
        self.code_buf = ""
        self._code_box_rect = None
        self._code_confirm_rect = None
        self._code_cancel_rect = None
        self.menu_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 150, 660, 300, 26),
            "RETOUR AU MENU", config.COL_AMBER)
        # défilement (molette) des blocs "Rapport final" et "Journal de carrière"
        self.scroll_report = 0
        self.scroll_journal = 0
        self._report_max_scroll = 0
        self._journal_max_scroll = 0
        self._report_list_rect = None
        self._journal_list_rect = None

    def handle_event(self, event):
        # boîte de saisie du code d'un ami : MODALE, capture tout en premier
        # (même pattern que scene_saves.py::path_prompt) — sinon RETURN/ÉCHAP
        # ci-dessous renverraient au menu au milieu de la frappe.
        if self.code_prompt:
            self._handle_code_prompt_event(event)
            return
        if self.menu_btn.handle(event):
            self.app.scenes.go("menu")
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.app.scenes.go("menu")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -32 if event.button == 4 else 32
            if self._report_list_rect and self._report_list_rect.collidepoint(event.pos):
                self.scroll_report = max(0, min(self._report_max_scroll, self.scroll_report + delta))
                return
            if self._journal_list_rect and self._journal_list_rect.collidepoint(event.pos):
                self.scroll_journal = max(0, min(self._journal_max_scroll, self.scroll_journal + delta))
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._export_rect and self._export_rect.collidepoint(event.pos):
                self._export_score()
                return
            if self._import_rect and self._import_rect.collidepoint(event.pos):
                self.code_prompt = True
                self.code_buf = ""
                return

    def _export_score(self):
        """Génère (paresseusement, au 1er clic) le code de partage du score
        de CE run et le copie dans le presse-papiers système (best-effort,
        cf. scenes/scene_commands.py::_try_clipboard — jamais bloquant)."""
        if self._export_code is None:
            p = self.app.gs.player
            entry = hof_mod.make_entry(p, self.score.total)
            self._export_code = challenge_share.encode_entry(entry)
        from scenes.scene_commands import _try_clipboard
        _try_clipboard(self._export_code)
        self.app.notify("Code copié — collez-le à un ami (Discord, SMS…).", "good")

    def _handle_code_prompt_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.code_prompt = False
                return
            if event.key == pygame.K_BACKSPACE:
                self.code_buf = self.code_buf[:-1]
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_code_prompt()
                return
            from core import clipboard
            if clipboard.is_paste_shortcut(event):
                self.code_buf += clipboard.paste()
                return
            if event.unicode and event.unicode.isprintable():
                self.code_buf += event.unicode
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._code_confirm_rect and self._code_confirm_rect.collidepoint(event.pos):
                self._confirm_code_prompt()
                return
            if self._code_cancel_rect and self._code_cancel_rect.collidepoint(event.pos):
                self.code_prompt = False
                return
            if not (self._code_box_rect and self._code_box_rect.collidepoint(event.pos)):
                self.code_prompt = False

    def _confirm_code_prompt(self):
        ok, result = hof_mod.import_friend_code(self.code_buf)
        self.code_prompt = False
        if ok:
            msg = f"Score de {result['name']} ajouté au classement du défi."
            kind = "good"
            # retour social : si CE run est un défi du jour (seul cas où le
            # classement s'affiche, cf. test_non_daily_run_shows_no_export_
            # import_buttons), on compare tout de suite mon score à celui de
            # l'ami importé — sinon "ajouté au classement" laisse le joueur
            # deviner s'il est devant ou derrière sans regarder le tableau.
            if self._daily_date and result.get("daily_date") == self._daily_date:
                mine, theirs = self.score.total, result.get("score", 0.0)
                diff = abs(round(mine - theirs, 1))
                if mine > theirs:
                    msg += f" Vous le devancez de {diff:g} points !"
                elif mine < theirs:
                    msg += f" {result['name']} vous devance de {diff:g} points."
                    kind = "warn"
                else:
                    msg += " Vous êtes à égalité !"
            self.app.notify(msg, kind)
            if self._daily_date:
                self.hof_daily_top = hof_mod.combined_daily_ranking(self._daily_date, n=8)
        elif result == "duplicate":
            self.app.notify("Ce code a déjà été importé.", "warn")
        else:
            self.app.notify("Code invalide — vérifiez le copier-coller.", "bad")

    def update(self, dt):
        self.t += dt
        self.menu_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cx = config.SCREEN_WIDTH // 2

        # titre pulsé en rouge (compact pour laisser de la place au score)
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.5)
        col = widgets._lerp_col(config.COL_DOWN, (120, 20, 24), pulse)
        widgets.draw_text(surf, "GAME OVER", (cx, 50),
                          fonts.title(bold=True), col, align="center")
        subtitle = "FIN DE CARRIÈRE"
        if self.hof_rank:
            subtitle += f" — PANTHÉON LOCAL : n°{self.hof_rank}"
        widgets.draw_text(surf, subtitle, (cx, 84), fonts.small(),
                          config.COL_PRESTIGE if self.hof_rank else config.COL_TEXT_DIM,
                          align="center")

        info = config.CONTINENTS.get(p.continent, {})
        cur = info.get("currency", "$")

        top_y = 106
        col_w = 250
        gap = 8
        row_h = 360
        left_x = cx - (4 * col_w + 3 * gap) // 2

        # panneau gauche : rapport final + stats de run (défilable)
        left = pygame.Rect(left_x, top_y, col_w, row_h)
        self._draw_report_panel(surf, left, p, cur)

        # panneau centre-gauche : journal de carrière, intégral (défilable)
        mid = pygame.Rect(left_x + col_w + gap, top_y, col_w, row_h)
        self._draw_journal_panel(surf, mid, p)

        # panneau centre-droit : décisions marquantes + badges du run
        decisions = pygame.Rect(left_x + 2 * (col_w + gap), top_y, col_w, row_h)
        self._draw_decisions_panel(surf, decisions, p)

        # panneau droit : score composite de fin de run
        right = pygame.Rect(left_x + 3 * (col_w + gap), top_y, col_w, row_h)
        self._draw_score_panel(surf, right)

        # panneau bas : rétrospective graphique de la valeur nette
        bottom_h = 150
        bottom = pygame.Rect(left_x, top_y + row_h + gap, 4 * col_w + 3 * gap, bottom_h)
        binner = widgets.draw_panel(surf, bottom, "Rétrospective — valeur nette", config.COL_CYAN)
        self._draw_networth_retrospective(surf, binner, p, cur)

        if p.hardcore:
            widgets.draw_badge(surf, "HARDCORE — SAUVEGARDE EFFACÉE",
                               (cx, bottom.bottom + 10), config.COL_DOWN, align="center")

        self.menu_btn.draw(surf)
        if self.code_prompt:
            self._draw_code_prompt(surf)

    def _draw_code_prompt(self, surf):
        """Boîte modale pour coller le code de score d'un ami (cf.
        core/challenge_share.py) — même style que scene_saves.py::path_prompt."""
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        box = pygame.Rect(0, 0, 520, 160)
        box.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        widgets.draw_panel(surf, box, "IMPORTER UN CODE D'AMI", config.COL_AMBER)
        widgets.draw_text(surf, "Collez le code de score reçu (Discord, SMS…) :",
                          (box.x + 20, box.y + 46), fonts.small(), config.COL_TEXT_DIM)

        self._code_box_rect = pygame.Rect(box.x + 20, box.y + 70, box.w - 40, 30)
        pygame.draw.rect(surf, config.COL_BG, self._code_box_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, self._code_box_rect, 1, border_radius=4)
        cur = "_" if pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, widgets.fit_text(self.code_buf + cur, fonts.small(), self._code_box_rect.w - 16),
                          (self._code_box_rect.x + 8, self._code_box_rect.y + 6), fonts.small(), config.COL_TEXT)

        self._code_confirm_rect = pygame.Rect(box.x + 20, box.bottom - 34, 120, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._code_confirm_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, self._code_confirm_rect, 1, border_radius=4)
        widgets.draw_text(surf, "IMPORTER", self._code_confirm_rect.center,
                          fonts.tiny(bold=True), config.COL_AMBER, align="center")
        self._code_cancel_rect = pygame.Rect(self._code_confirm_rect.right + 10, box.bottom - 34, 90, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._code_cancel_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_TEXT_DIM, self._code_cancel_rect, 1, border_radius=4)
        widgets.draw_text(surf, "Annuler", self._code_cancel_rect.center,
                          fonts.tiny(), config.COL_TEXT_DIM, align="center")

    def _draw_report_panel(self, surf, rect, p, cur):
        """Rapport final + stats de run — défilable à la molette pour
        toujours pouvoir tout lire, même un motif de fin de partie long."""
        inner = widgets.draw_panel(surf, rect, "Rapport final", config.COL_DOWN)
        list_area = pygame.Rect(inner.x - 4, inner.y, inner.w + 8, inner.h)
        self._report_list_rect = list_area
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y - self.scroll_report
        h = widgets.draw_text_wrapped(surf, p.game_over_reason or "Partie terminée.",
                                      (inner.x, y), fonts.tiny(),
                                      config.COL_TEXT, inner.w, line_gap=4)
        y += h + 8
        lines = [
            f"Nom    : {p.name}",
            f"Grade  : {p.grade}",
            f"Voie   : {p.track}",
            f"Région : {p.continent}",
            f"Durée  : {p.quarter} trim. ({p.day} j)",
            f"Cash   : {widgets.format_money(p.cash, cur)}",
            f"Record : {widgets.format_money(max(p.best_cash, p.cash), cur)}",
            f"Rép.   : {p.reputation}/100",
            f"Deals {p.deals_won}  Miss. {p.missions_done}",
            "",
            "— P&L DU RUN —",
            f"Réalisé : {widgets.format_money(p.realized_pnl, cur)}",
            f"Frais   : {widgets.format_money(-p.total_fees_paid, cur)}",
            f"Financ. : {widgets.format_money(-p.total_financing_paid, cur)}",
            f"Marge   : {widgets.format_money(-p.total_margin_penalty, cur)}",
        ]
        for ln in lines:
            widgets.draw_text(surf, ln, (inner.x, y), fonts.tiny(), config.COL_TEXT)
            y += 18
        if p.titles:
            y += 4
            y += widgets.draw_text_wrapped(surf, "Titres : " + " · ".join(p.titles),
                                           (inner.x, y), fonts.tiny(), config.COL_WARN, inner.w)
        # panthéon local : les meilleurs runs de ce poste, toutes parties
        # confondues (core/hall_of_fame.py) — un point de comparaison qui
        # donne envie de relancer.
        if self.hof_top:
            y += 10
            widgets.draw_text(surf, "PANTHÉON LOCAL", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_PRESTIGE)
            y += 18
            for i, run in enumerate(self.hof_top, start=1):
                mine = (self.hof_rank == i)
                col = config.COL_PRESTIGE if mine else config.COL_TEXT
                # marqué pour signaler un run de défi du jour (marché
                # différent — le score n'est pas rigoureusement comparable
                # aux runs classiques du dessus/dessous).
                tag = " [défi]" if run.get("daily_date") else ""
                txt = (f"{i}. {run['name']} — {run['grade']} · "
                       f"{run['quarters']} trim. · score {run['score']:g}{tag}")
                widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.w),
                                  (inner.x, y), fonts.tiny(bold=mine), col)
                y += 16
        # classement du défi du jour à part (marché déterministe partagé,
        # comparaison équitable uniquement entre joueurs du MÊME jour) —
        # FUSIONNE runs joués localement et scores d'amis importés (codes
        # texte, cf. core/challenge_share.py) ; "mine" par ID, pas par rang
        # positionnel (qui change au fil des imports).
        self._export_rect = None
        self._import_rect = None
        if self.hof_daily_top:
            y += 10
            widgets.draw_text(surf, "CLASSEMENT DU DÉFI DU JOUR", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_CYAN)
            y += 18
            for run in self.hof_daily_top:
                mine = (self._my_hof_entry_id is not None and run.get("id") == self._my_hof_entry_id)
                col = config.COL_CYAN if mine else config.COL_TEXT
                tag = " (ami)" if run.get("friend") else ""
                txt = f"{run['name']} — {run['grade']} · score {run['score']:g}{tag}"
                widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.w),
                                  (inner.x, y), fonts.tiny(bold=mine), col)
                y += 16
            y += 6
            self._export_rect = pygame.Rect(inner.x, y, inner.w // 2 - 4, 22)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._export_rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN, self._export_rect, 1, border_radius=4)
            widgets.draw_text(surf, "EXPORTER MON SCORE", self._export_rect.center,
                              fonts.tiny(bold=True), config.COL_CYAN, align="center")
            self._import_rect = pygame.Rect(self._export_rect.right + 8, y, inner.w // 2 - 4, 22)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._import_rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER, self._import_rect, 1, border_radius=4)
            widgets.draw_text(surf, "IMPORTER UN CODE", self._import_rect.center,
                              fonts.tiny(bold=True), config.COL_AMBER, align="center")
            y += 26
            if self._export_code:
                y += widgets.draw_text_wrapped(
                    surf, "Code copié : " + self._export_code, (inner.x, y),
                    fonts.tiny(), config.COL_TEXT_DIM, inner.w, line_gap=2)
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll_report) - inner.y
        self._report_max_scroll = max(0, content_h - list_area.h)
        self.scroll_report = max(0, min(self._report_max_scroll, self.scroll_report))
        self.scroll_report = widgets.draw_scrollbar(surf, rect, list_area, self.scroll_report,
                               self._report_max_scroll, content_h)

    def _draw_journal_panel(self, surf, rect, p):
        """Journal de carrière intégral (plus de limite à 9 entrées) —
        défilable à la molette."""
        inner = widgets.draw_panel(surf, rect, "Journal de carrière", config.COL_AMBER)
        list_area = pygame.Rect(inner.x - 4, inner.y, inner.w + 8, inner.h)
        self._journal_list_rect = list_area
        if not p.journal:
            widgets.draw_text_wrapped(surf, "Carrière trop courte pour laisser une trace.",
                              (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM, inner.w)
            self._journal_max_scroll = 0
            return
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        row_h = 22
        yy = inner.y - self.scroll_journal
        for e in reversed(p.journal):
            if list_area.top - row_h < yy < list_area.bottom:
                widgets.draw_text(surf, f"J{e['day']}", (inner.x, yy),
                                  fonts.tiny(bold=True), config.COL_CYAN)
                widgets.draw_text(surf, widgets.fit_text(e["text"], fonts.tiny(), inner.w - 40),
                                  (inner.x + 40, yy), fonts.tiny(), config.COL_TEXT)
            yy += row_h
        surf.set_clip(prev_clip)
        content_h = (yy + self.scroll_journal) - inner.y
        self._journal_max_scroll = max(0, content_h - list_area.h)
        self.scroll_journal = max(0, min(self._journal_max_scroll, self.scroll_journal))
        self.scroll_journal = widgets.draw_scrollbar(surf, rect, list_area, self.scroll_journal,
                               self._journal_max_scroll, content_h)

    def _draw_decisions_panel(self, surf, rect, p):
        """Décisions marquantes (dilemmes tranchés, core/dilemmas.py) et
        badges décrochés pendant le run — la mémoire NARRATIVE de la partie,
        complémentaire du journal (événements) et du score (chiffres)."""
        from core import badges as badges_mod
        inner = widgets.draw_panel(surf, rect, "Décisions & badges", config.COL_PRESTIGE)
        y = inner.y
        decisions = getattr(p, "decisions_log", None) or []
        if decisions:
            widgets.draw_text(surf, "DÉCISIONS MARQUANTES", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_CYAN)
            y += 18
            for d in decisions[-6:][::-1]:
                widgets.draw_text(surf, f"J{d.get('day', '?')}", (inner.x, y),
                                  fonts.tiny(bold=True), config.COL_CYAN)
                widgets.draw_text(surf,
                                  widgets.fit_text(str(d.get("title", "")), fonts.tiny(),
                                                   inner.w - 40),
                                  (inner.x + 40, y), fonts.tiny(), config.COL_TEXT)
                y += 15
                widgets.draw_text(surf,
                                  widgets.fit_text("→ " + str(d.get("choice", "")),
                                                   fonts.tiny(), inner.w - 40),
                                  (inner.x + 40, y), fonts.tiny(), config.COL_TEXT_DIM)
                y += 19
        else:
            y += widgets.draw_text_wrapped(
                surf, "Aucun dilemme tranché pendant ce run.",
                (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM, inner.w) + 6
        badge_ids = getattr(p, "badges", None) or []
        if badge_ids:
            y += 8
            widgets.draw_text(surf, f"BADGES ({len(badge_ids)})", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_PRESTIGE)
            y += 18
            shown = 0
            for b in badges_mod.BADGES:
                if b["id"] not in badge_ids:
                    continue
                if y > inner.bottom - 14:
                    remaining = len(badge_ids) - shown
                    if remaining > 0:
                        widgets.draw_text(surf, f"… +{remaining} autres", (inner.x, y - 2),
                                          fonts.tiny(), config.COL_TEXT_DIM)
                    break
                widgets.draw_text(surf,
                                  widgets.fit_text("· " + badges_mod.badge_name(b),
                                                   fonts.tiny(), inner.w),
                                  (inner.x, y), fonts.tiny(), config.COL_WARN)
                y += 16
                shown += 1
        if getattr(p, "investigations_count", 0):
            y += 8
            widgets.draw_text(surf, f"Enquêtes subies : {p.investigations_count}",
                              (inner.x, y), fonts.tiny(), config.COL_DOWN)

    def _draw_score_panel(self, surf, rect):
        """Affiche le score composite de fin de run (core/score.py) : note
        lettre + total, puis une jauge par dimension (0-100)."""
        sc = self.score
        accent = _score_color(sc.total)
        inner = widgets.draw_panel(surf, rect, "Score de carrière", accent)

        widgets.draw_text(surf, f"{sc.grade}", (inner.x, inner.y),
                          fonts.title(bold=True), accent)
        widgets.draw_text(surf, f"{sc.total:.0f}/100", (inner.x + 50, inner.y + 6),
                          fonts.small(bold=True), config.COL_TEXT)
        widgets.draw_text_wrapped(surf, sc.rank_label, (inner.x, inner.y + 30),
                                  fonts.tiny(), config.COL_TEXT_DIM, inner.w)

        bar_y = inner.y + 64
        bar_h = 16
        gap = 12
        for key, label in SCORE_DIMENSIONS:
            val = getattr(sc, key)
            widgets.draw_text(surf, label, (inner.x, bar_y), fonts.tiny(), config.COL_TEXT)
            bar_rect = pygame.Rect(inner.x + 78, bar_y + 1, inner.w - 78 - 46, bar_h - 2)
            widgets.draw_progress(surf, bar_rect, val / 100.0, _score_color(val))
            widgets.draw_text(surf, f"{val:.0f}/100", (inner.right, bar_y),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            bar_y += bar_h + gap

    def _draw_networth_retrospective(self, surf, inner, p, cur):
        """Sparkline de `cash_history` avec annotation du meilleur et du pire
        moment de la carrière. Reste discret si l'historique est trop court."""
        hist = p.cash_history or []
        if len(hist) < 2:
            widgets.draw_text(surf, "Historique trop court pour un graphique.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return

        chart_rect = pygame.Rect(inner.x + 50, inner.y, inner.w - 60, inner.h - 38)
        # RUNS FANTÔMES : la trajectoire des amis sur le même défi du jour
        # (core/ghost.py), projetée sur l'échelle locale, sous votre courbe.
        from core import ghost as ghost_mod
        ghosts = [(g["name"], ghost_mod.project(g["curve"], hist[0], len(hist)))
                  for g in ghost_mod.ghosts_for(p)]
        ghosts = [(n, v) for n, v in ghosts if v]
        lo, hi = min(hist), max(hist)
        for _n, gvals in ghosts:
            lo, hi = min(lo, min(gvals)), max(hi, max(gvals))
        lo, hi, span = widgets.draw_chart_axes(
            surf, chart_rect, lo, hi,
            y_fmt=lambda v: widgets.format_money(v, cur), rows=2)
        for gname, gvals in ghosts:
            widgets.draw_series(surf, chart_rect, gvals, config.COL_TEXT_DIM,
                                baseline=False, show_extrema=False, y_fmt=None)
            gx = chart_rect.right - 6
            gy = chart_rect.bottom - int((gvals[-1] - lo) / (span or 1) * chart_rect.h)
            widgets.draw_text(surf, gname, (gx, gy - 10), fonts.tiny(),
                              config.COL_TEXT_DIM, align="right")
        widgets.draw_series(surf, chart_rect, hist, config.COL_CYAN, baseline=False,
                            mouse_pos=pygame.mouse.get_pos(),
                            y_fmt=lambda v: widgets.format_money(v, cur),
                            show_pct=True, show_extrema=False)
        n_hist = len(hist)
        d = config.DAYS_PER_STEP
        widgets.draw_chart_x_labels(surf, chart_rect, [
            (0.0, f"-{(n_hist - 1) * d}j"),
            (0.5, f"-{(n_hist - 1) // 2 * d}j"),
            (1.0, "aujourd'hui"),
        ])

        # repère du meilleur et du pire point de la série
        i_max = max(range(len(hist)), key=lambda i: hist[i])
        i_min = min(range(len(hist)), key=lambda i: hist[i])
        n = len(hist)

        def pt(i):
            x = chart_rect.x + int(i / (n - 1) * chart_rect.w)
            y = chart_rect.bottom - int((hist[i] - lo) / span * chart_rect.h)
            return x, y

        x_max, y_max = pt(i_max)
        x_min, y_min = pt(i_min)
        pygame.draw.circle(surf, config.COL_UP, (x_max, y_max), 4)
        pygame.draw.circle(surf, config.COL_DOWN, (x_min, y_min), 4)

        best = max(p.best_cash, hist[i_max])
        label_y = inner.y + inner.h - 14
        widgets.draw_text(surf, f"Record : {widgets.format_money(best, cur)}",
                          (inner.x, label_y), fonts.tiny(bold=True), config.COL_UP)
        widgets.draw_text(surf, f"Plus bas : {widgets.format_money(hist[i_min], cur)}",
                          (inner.x + 220, label_y), fonts.tiny(bold=True), config.COL_DOWN)
