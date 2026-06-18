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
from core.scene_manager import Scene
from ui import fonts, widgets

_KIND_COLORS = {
    "promo": config.COL_UP, "deal": config.COL_DEAL, "crisis": config.COL_DOWN,
    "objective": config.COL_CYAN, "info": config.COL_TEXT_DIM,
}


class CareerScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        career.ensure_objectives(self.app.gs.player)
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.rivals_btn = widgets.Button(
            (config.SCREEN_WIDTH - 40 - 160, 60, 160, 32), "RIVAUX →", config.COL_PRESTIGE)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.rivals_btn.handle(event):
            self.app.scenes.go("rivals", return_to="career")

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        self.rivals_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, "CARRIÈRE", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        sub = f"{p.name} · {p.grade} · {config.career_phase(p.grade_index)}"
        if p.track != "General":
            sub += f" · voie {p.track}"
        widgets.draw_text(surf, sub, (42, 72), fonts.small(), config.COL_TEXT_DIM)
        if p.titles:
            widgets.draw_text(surf, "Titres : " + " · ".join(p.titles),
                              (config.SCREEN_WIDTH - 40, 30), fonts.small(bold=True),
                              config.COL_WARN, align="right")

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

        self.back_btn.draw(surf)
        self.rivals_btn.draw(surf)

    def _draw_ladder(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, "Échelle des grades", config.COL_AMBER)
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
            for bid in p.badges:
                b = badges_mod.get(bid)
                if not b:
                    continue
                r = widgets.draw_badge(surf, b["name"], (x, y), config.COL_PRESTIGE)
                x = r.right + 6
                if x > inner.right - 90:
                    x = inner.x
                    y += r.height + 6

    def _draw_roadmap(self, surf, rect, p):
        ready = career.promotion_ready(p)
        accent = config.COL_UP if ready else config.COL_WARN
        inner = widgets.draw_panel(surf, rect, "Roadmap de promotion", accent)
        if not p.can_promote():
            widgets.draw_text(surf, "Grade maximal atteint.", (inner.x, inner.y),
                              fonts.body(bold=True), config.COL_UP)
            return
        y = inner.y
        for r in career.promotion_requirements(p):
            mark = "✓" if r["met"] else "○"
            col = config.COL_UP if r["met"] else config.COL_TEXT
            widgets.draw_text(surf, f"{mark} {r['label']}", (inner.x, y), fonts.small(), col)
            widgets.draw_text(surf, f"{int(r['current'])}/{int(r['target'])}",
                              (inner.right, y), fonts.small(bold=True),
                              col, align="right")
            y += 26
        y += 6
        if ready:
            widgets.draw_text(surf, "✓ Critères remplis — tapez EVAL pour l'examen.",
                              (inner.x, y), fonts.small(bold=True), config.COL_UP)
        else:
            widgets.draw_text(surf, "Manque : " + ", ".join(career.missing_criteria(p)),
                              (inner.x, y), fonts.tiny(), config.COL_WARN)

    def _draw_stats(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, "Statistiques de run", config.COL_CYAN)
        cur = config.CONTINENTS[p.continent]["currency"]
        rows = [
            ("Trésorerie", widgets.format_money(p.cash, cur)),
            ("Record trésorerie", widgets.format_money(max(p.best_cash, p.cash), cur)),
            ("Réputation", f"{p.reputation}/100"),
            ("Deals conclus", str(p.deals_won)),
            ("Missions réalisées", str(p.missions_done)),
            ("Scrutin réglementaire", f"{p.heat}/100"),
            ("Temps", f"jour {p.day} (T{p.quarter})"),
        ]
        # pas de ligne adaptatif : toutes les lignes tiennent dans le panneau
        step = max(18, min(25, inner.h // len(rows)))
        y = inner.y
        for label, val in rows:
            widgets.draw_text(surf, label, (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (inner.right, y), fonts.small(bold=True),
                              config.COL_WHITE, align="right")
            y += step

    def _draw_objectives(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, f"Objectifs — T{p.quarter}", config.COL_DEAL)
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
        widgets.draw_text(surf, "Récompense par objectif : +réputation & honoraire.",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "Trimestre parfait = bonus de prestige.",
                          (inner.x, y + 16), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_journal(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, "Journal de carrière", config.COL_AMBER)
        if not p.journal:
            widgets.draw_text(surf, "Votre histoire s'écrira ici : promotions, deals, crises…",
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
