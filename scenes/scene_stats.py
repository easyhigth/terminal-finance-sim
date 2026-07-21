"""
scene_stats.py — Écran de statistiques de session/carrière : synthèse en un
seul endroit de données déjà suivies mais éparpillées (journal de trades,
core/journal.py ; compteurs cumulés du joueur, core/game_state.py ; score
composite, core/score.py ; progression badges/arcs) — rien de tout ceci
n'avait jusqu'ici de vitrine dédiée (distinct de scene_career.py, qui montre
plutôt grade/objectifs/trésorerie que l'ANALYSE des décisions de trading).
"""
import time

import pygame

from core import badges as badges_mod
from core import config
from core import journal as journal_mod
from core import score as score_mod
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


def _fmt_duration(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, _s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}"
    return f"{m}min"


class StatsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")

        widgets.draw_text(surf, _L("STATISTIQUES DE CARRIÈRE", "CAREER STATISTICS"), (40, 20),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L("Vue d'ensemble de la session : trading, discipline, "
                          "progression et score composite actuel.",
                          "Session overview: trading, discipline, "
                          "progression and current composite score."),
                          (42, 64), fonts.small(), config.COL_TEXT_DIM)

        top = 100
        M = config.MARGIN
        bottom = config.footer_y() - 8
        h = bottom - top
        colw = (config.SCREEN_WIDTH - 3 * M) // 2
        x1, x2 = M, M + colw + M
        half_h = (h - M) // 2

        self._draw_session(surf, pygame.Rect(x1, top, colw, half_h), p, cur)
        self._draw_trading(surf, pygame.Rect(x1, top + half_h + M, colw, half_h), p, cur)
        self._draw_progression(surf, pygame.Rect(x2, top, colw, half_h), p)
        self._draw_score(surf, pygame.Rect(x2, top + half_h + M, colw, half_h), p)

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("ESC", _L("retour", "back"))])
        self.back_btn.draw(surf)

    def _draw_session(self, surf, rect, p, cur):
        inner = widgets.draw_panel(surf, rect, _L("Session", "Session"), config.COL_CYAN)
        created_at = getattr(self.app.gs, "created_at", None)
        playtime = time.time() - created_at if created_at else 0.0
        rows = [
            (_L("Temps de jeu (session)", "Playtime (session)"), _fmt_duration(playtime)),
            (_L("Jour / trimestre", "Day / quarter"), f"{_L('J', 'D')}{p.day} · {_L('T', 'Q')}{p.quarter}"),
            (_L("Meilleur patrimoine net", "Best net worth"), widgets.format_money(p.best_cash, cur)),
            (_L("Enquêtes réglementaires subies", "Regulatory investigations faced"), str(p.investigations_count)),
        ]
        self._draw_rows(surf, inner, rows)

    def _draw_trading(self, surf, rect, p, cur):
        inner = widgets.draw_panel(surf, rect, _L("Trading", "Trading"), config.COL_UP)
        journal = p.trade_journal
        closed = [e for e in journal if e["realized"] is not None]
        wins = sum(1 for e in closed if e["realized"] > 0)
        win_rate = (wins / len(closed) * 100.0) if closed else None
        disc = journal_mod.discipline_score(p)
        rows = [
            (_L("Ordres exécutés", "Orders executed"), str(len(journal))),
            (_L("Trades clôturés (gagnants/total)", "Closed trades (winners/total)"),
             f"{wins}/{len(closed)}" + (f" ({win_rate:.0f}%)" if win_rate is not None else "")
             if closed else "—"),
            (_L("P&L réalisé cumulé", "Cumulative realized P&L"), widgets.format_money(p.realized_pnl, cur)),
            (_L("Frais d'exécution payés", "Execution fees paid"), widgets.format_money(p.total_fees_paid, cur)),
            (_L("Pénalités d'appel de marge", "Margin call penalties"), widgets.format_money(p.total_margin_penalty, cur)),
            (_L("Score de discipline", "Discipline score"),
             f"{disc['score']:.0f}/100" if disc is not None else _L("— (aucun trade clôturé)", "— (no closed trade)")),
        ]
        self._draw_rows(surf, inner, rows)

    def _draw_progression(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L("Progression", "Progression"), config.COL_PRESTIGE)
        arcs_done, arcs_total = badges_mod._story_arcs_progress(p)
        rows = [
            (_L("Badges débloqués", "Badges unlocked"), f"{len(p.badges)}/{len(badges_mod.all_badges())}"),
            (_L("Badges à enjeu actifs", "Active stake badges"), str(len(p.streak_badges))),
            (_L("Arcs narratifs terminés", "Story arcs completed"), f"{arcs_done}/{arcs_total}"),
            (_L("Deals remportés", "Deals won"), str(p.deals_won)),
            (_L("Missions accomplies", "Missions completed"), str(p.missions_done)),
        ]
        self._draw_rows(surf, inner, rows)

    def _draw_score(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L("Score composite (si le run s'arrêtait maintenant)", "Composite score (if the run ended now)"),
                                   config.COL_WARN)
        fs = score_mod.compute_final_score(p, self.market)
        grade_col = config.COL_UP if fs.total >= 60 else (
            config.COL_WARN if fs.total >= 30 else config.COL_DOWN)
        widgets.draw_text(surf, f"{fs.grade} — {fs.total:.0f}/100", (inner.x, inner.y),
                          fonts.body(bold=True), grade_col)
        widgets.draw_text(surf, fs.rank_label, (inner.x, inner.y + 22),
                          fonts.small(), config.COL_TEXT_DIM)
        y = inner.y + 48
        for key, label in (
            ("performance", _L("Performance", "Performance")), ("risque", _L("Risque", "Risk")),
            ("drawdown", "Drawdown"), ("reputation", _L("Réputation", "Reputation")),
            ("conformite", _L("Conformité", "Compliance")), ("qualite_execution", _L("Qualité d'exécution", "Execution quality")),
            ("survie", _L("Survie", "Survival")),
        ):
            v = fs.breakdown[key]
            # libellé borné à sa colonne (« Qualité d'exécution » passait sous
            # la barre) ; barre raccourcie pour réserver une gouttière au
            # chiffre (un « 100 » plein débordait SUR la barre et semblait
            # tronqué en « 00 »).
            widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), 114),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            bx = inner.x + 120
            bw = inner.w - 120 - 34
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, (bx, y, bw, 10))
            col = config.COL_UP if v >= 60 else (config.COL_WARN if v >= 30 else config.COL_DOWN)
            pygame.draw.rect(surf, col, (bx, y, int(bw * v / 100.0), 10))
            widgets.draw_text(surf, f"{v:.0f}", (inner.right, y - 2),
                              fonts.tiny(bold=True), col, align="right")
            y += 18

    def _draw_rows(self, surf, inner, rows):
        y = inner.y
        row_h = max(20, (inner.h - 4) // max(1, len(rows)))
        for label, value in rows:
            widgets.draw_text(surf, label, (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, value, (inner.right, y), fonts.small(bold=True),
                              config.COL_TEXT, align="right")
            y += row_h
