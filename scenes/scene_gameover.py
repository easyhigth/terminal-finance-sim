"""
scene_gameover.py — Écran de fin de partie (faillite ou réputation anéantie).
Affiche le motif, un récapitulatif de carrière, le score composite de fin de
run (core/score.py), et renvoie au menu.
En mode hardcore, la sauvegarde automatique est effacée (run définitif).
"""
import math

import pygame

from core import badges as badges_mod
from core import config
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
            badges_mod.check_new(p, market)
        self.hof_top = hof_mod.top(5)
        # classement du défi du jour à part (marché différent des runs
        # classiques, comparer les scores mélangés serait trompeur)
        self.hof_daily_top = None
        self.hof_daily_rank = None
        if difficulty_mod.is_daily_challenge(p):
            self.hof_daily_top = hof_mod.top_for_daily(p.flags.get("daily_challenge"), n=5)
            self.hof_daily_rank = hof_mod.daily_rank(p)
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
        left_x = cx - (3 * col_w + 2 * gap) // 2

        # panneau gauche : rapport final + stats de run (défilable)
        left = pygame.Rect(left_x, top_y, col_w, row_h)
        self._draw_report_panel(surf, left, p, cur)

        # panneau central : journal de carrière, intégral (défilable)
        mid = pygame.Rect(left_x + col_w + gap, top_y, col_w, row_h)
        self._draw_journal_panel(surf, mid, p)

        # panneau droit : score composite de fin de run
        right = pygame.Rect(left_x + 2 * (col_w + gap), top_y, col_w, row_h)
        self._draw_score_panel(surf, right)

        # panneau bas : rétrospective graphique de la valeur nette
        bottom_h = 150
        bottom = pygame.Rect(left_x, top_y + row_h + gap, 3 * col_w + 2 * gap, bottom_h)
        binner = widgets.draw_panel(surf, bottom, "Rétrospective — valeur nette", config.COL_CYAN)
        self._draw_networth_retrospective(surf, binner, p, cur)

        if p.hardcore:
            widgets.draw_badge(surf, "HARDCORE — SAUVEGARDE EFFACÉE",
                               (cx, bottom.bottom + 10), config.COL_DOWN, align="center")

        self.menu_btn.draw(surf)

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
        # comparaison équitable uniquement entre joueurs du MÊME jour).
        if self.hof_daily_top:
            y += 10
            widgets.draw_text(surf, "CLASSEMENT DU DÉFI DU JOUR", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_CYAN)
            y += 18
            for i, run in enumerate(self.hof_daily_top, start=1):
                mine = (self.hof_daily_rank == i)
                col = config.COL_CYAN if mine else config.COL_TEXT
                txt = f"{i}. {run['name']} — {run['grade']} · score {run['score']:g}"
                widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.w),
                                  (inner.x, y), fonts.tiny(bold=mine), col)
                y += 16
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
        lo, hi = min(hist), max(hist)
        lo, hi, span = widgets.draw_chart_axes(
            surf, chart_rect, lo, hi,
            y_fmt=lambda v: widgets.format_money(v, cur), rows=2)
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
