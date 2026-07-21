"""
scene_history.py — Historique de carrière consultable à tout moment (pas
seulement en fin de partie). Reprend le style de scenes/scene_career.py
(panneaux, bouton retour) et la logique de graphique de
scenes/scene_gameover.py::_draw_networth_retrospective (sparkline de
cash_history) + une timeline du journal de carrière via
core/career_history.py::format_timeline.

Ouvert via HISTORY depuis le terminal (câblage central, hors périmètre ici).
"""
import pygame

from core import charts, config
from core.career_history import format_timeline
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


_KIND_COLORS = {
    "promo": config.COL_UP, "deal": config.COL_DEAL, "crisis": config.COL_DOWN,
    "objective": config.COL_CYAN, "info": config.COL_TEXT_DIM,
}

_ATTRIB_LABELS = {
    "salaire": (("Salaire", "Salary"), config.COL_CYAN),
    "revenus": (("Revenus passifs", "Passive income"), config.COL_UP),
    "deals": (("Deals", "Deals"), config.COL_DEAL),
    "mandats": (("Mandats", "Mandates"), config.COL_AMBER),
    "objectifs": (("Objectifs", "Objectives"), config.COL_PRESTIGE),
    "evenements": (("Événements", "Events"), config.COL_WARN),
    "marches": (("Marchés", "Markets"), config.COL_TEXT),
}


def _crisis_markers(market, hist):
    """Associe à chaque crise de market.crisis_log l'index de cash_history où
    elle est tombée (si encore dans la fenêtre visible), via la correspondance
    step_count <-> index : step_for_index(i) = step_count - (len(hist)-1-i)
    (cash_history est tronqué à 80 entrées, donc on ne retrouve que les
    crises encore couvertes par l'historique affiché)."""
    if not hist or market is None:
        return []
    n = len(hist)
    out = []
    for c in getattr(market, "crisis_log", []):
        idx = c["step"] - market.step_count + (n - 1)
        if 0 <= idx <= n - 1:
            out.append((idx, c))
    return out


def _drawdowns(hist):
    """Retourne (drawdown courant %, drawdown max %) depuis une série de valeurs
    nettes, calculés par rapport au sommet glissant (running peak)."""
    peak = hist[0]
    max_dd = 0.0
    for v in hist:
        peak = max(peak, v)
        if peak > 0:
            max_dd = max(max_dd, (peak - v) / peak * 100.0)
    cur_dd = (peak - hist[-1]) / peak * 100.0 if peak > 0 else 0.0
    return cur_dd, max_dd


class HistoryScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button(
            (config.back_button_rect(200)[0] + 220,
             config.back_button_rect(200)[1], 150, 42),
            "TUTO", config.COL_CYAN)
        self.scroll_timeline = 0
        self._timeline_max_scroll = 0
        self._timeline_list_rect = None
        self._crisis_tooltip = None  # (texte, pos souris) si survol d'un marqueur

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="history", return_to="history")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._timeline_list_rect and self._timeline_list_rect.collidepoint(event.pos):
                delta = -48 if event.button == 4 else 48
                self.scroll_timeline = max(0, min(self._timeline_max_scroll,
                                                  self.scroll_timeline + delta))

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, _L("HISTORIQUE DE CARRIÈRE", "CAREER HISTORY"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        sub = f"{p.name} · {p.grade} · jour {p.day} (T{p.quarter})"
        widgets.draw_text(surf, sub, (42, 72), fonts.small(), config.COL_TEXT_DIM)

        M = config.MARGIN
        top = config.content_top()
        bottom = config.footer_y() - 8
        total_h = bottom - top
        chart_h = int(total_h * 0.36)
        mid_h = int(total_h * 0.22)
        gap = 12
        journal_h = total_h - chart_h - mid_h - 2 * gap

        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        chart_rect = pygame.Rect(M, top, config.SCREEN_WIDTH - 2 * M, chart_h)
        self._draw_networth_chart(surf, chart_rect, p, cur)

        mid_y = top + chart_h + gap
        half_w = (config.SCREEN_WIDTH - 2 * M - gap) // 2
        perf_rect = pygame.Rect(M, mid_y, half_w, mid_h)
        attrib_rect = pygame.Rect(M + half_w + gap, mid_y, half_w, mid_h)
        self._draw_perf_vs_index(surf, perf_rect, p)
        self._draw_attribution(surf, attrib_rect, p, cur)

        journal_rect = pygame.Rect(M, mid_y + mid_h + gap,
                                   config.SCREEN_WIDTH - 2 * M, journal_h)
        self._draw_timeline(surf, journal_rect, p)

        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
        if self._crisis_tooltip:
            widgets.draw_tooltip(surf, *self._crisis_tooltip)

    def _draw_networth_chart(self, surf, rect, p, cur):
        inner = widgets.draw_panel(surf, rect, _L("Valeur nette — évolution", "Net worth — evolution"), config.COL_CYAN)
        hist = p.cash_history or []
        if len(hist) < 2:
            widgets.draw_text(surf, "Historique trop court pour un graphique.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return

        chart_rect = pygame.Rect(inner.x + 50, inner.y, inner.w - 60, inner.h - 38)
        lo, hi = min(hist), max(hist)
        lo, hi, span = widgets.draw_chart_axes(
            surf, chart_rect, lo, hi,
            y_fmt=lambda v: widgets.format_money(v, cur), rows=4)
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

        self._crisis_tooltip = None
        mp = pygame.mouse.get_pos()
        market = getattr(self.app, "market", None)
        for idx, c in _crisis_markers(market, hist):
            x, _ = pt(idx)
            col = config.COL_UP if c.get("kind") == "good" else config.COL_DOWN
            pygame.draw.line(surf, col, (x, chart_rect.y), (x, chart_rect.bottom), 1)
            pygame.draw.circle(surf, col, (x, chart_rect.bottom), 3)
            if abs(mp[0] - x) <= 4 and chart_rect.y <= mp[1] <= chart_rect.bottom + 6:
                self._crisis_tooltip = (_L(f"{c['name']} (sévérité {c['severity']:.1f}x)", f"{c['name']} (severity {c['severity']:.1f}x)"), mp)

        best = max(p.best_cash, hist[i_max])
        label_y = inner.y + inner.h - 14
        widgets.draw_text(surf, f"Record : {widgets.format_money(best, cur)}",
                          (inner.x, label_y), fonts.tiny(bold=True), config.COL_UP)
        widgets.draw_text(surf, f"Plus bas : {widgets.format_money(hist[i_min], cur)}",
                          (inner.x + 220, label_y), fonts.tiny(bold=True), config.COL_DOWN)

        cur_dd, max_dd = _drawdowns(hist)
        widgets.draw_text(surf, f"Drawdown actuel : -{cur_dd:.1f}%",
                          (inner.x + 440, label_y), fonts.tiny(bold=True),
                          config.COL_DOWN if cur_dd > 0 else config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"Drawdown max : -{max_dd:.1f}%",
                          (inner.x + 640, label_y), fonts.tiny(bold=True), config.COL_WARN)
        widgets.draw_text(
            surf, _L(f"({len(hist)} relevés récents)", f"({len(hist)} recent readings)"),
            (inner.right, inner.y), fonts.tiny(), config.COL_TEXT_DIM, align="right")

    def _draw_perf_vs_index(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L("Performance vs indice régional", "Performance vs regional index"), config.COL_AMBER)
        hist = p.cash_history or []
        market = getattr(self.app, "market", None)
        idx_name = None
        if market is not None:
            for name, region in getattr(market, "index_region", {}).items():
                if region == p.continent:
                    idx_name = name
                    break
        if len(hist) < 2 or idx_name is None:
            widgets.draw_text(surf, "Historique trop court pour comparer.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return
        idx_hist_full = market.index_hist.get(idx_name, [])
        idx_hist = idx_hist_full[-len(hist):]
        if len(idx_hist) < 2:
            widgets.draw_text(surf, "Historique trop court pour comparer.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return
        nw_pct = charts.normalize(hist)
        idx_pct = charts.normalize(idx_hist)
        chart_rect = pygame.Rect(inner.x + 50, inner.y, inner.w - 60, inner.h - 14)
        lo = min(min(nw_pct), min(idx_pct))
        hi = max(max(nw_pct), max(idx_pct))
        lo, hi, span = widgets.draw_chart_axes(
            surf, chart_rect, lo, hi, y_fmt=lambda v: f"{v:+.0f}%", rows=4)
        widgets.draw_series(surf, chart_rect, nw_pct, config.COL_CYAN, baseline=False,
                            show_extrema=False)
        widgets.draw_series(surf, chart_rect, idx_pct, config.COL_TEXT_DIM, baseline=False,
                            show_extrema=False)
        widgets.draw_chart_zero_line(surf, chart_rect, lo, span)
        widgets.draw_chart_legend(surf, rect, [
            ("Vous", config.COL_CYAN), (idx_name, config.COL_TEXT_DIM),
        ])

    def _draw_attribution(self, surf, rect, p, cur):
        inner = widgets.draw_panel(surf, rect, _L("Attribution du dernier trimestre", "Last quarter attribution"), config.COL_PRESTIGE)
        attrib = getattr(p, "last_quarter_attribution", None) or {}
        if not attrib:
            widgets.draw_text(surf, _L("Disponible après la clôture d'un trimestre.", "Available after a quarter closes."),
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return
        items = sorted(attrib.items(), key=lambda kv: -abs(kv[1]))
        max_abs = max((abs(v) for _, v in items), default=1.0) or 1.0
        line_h = 20
        bar_x = inner.x + 130
        bar_w = inner.w - 150
        for i, (cat, delta) in enumerate(items):
            y = inner.y + i * line_h
            if y + line_h > inner.bottom:
                break
            labelpair, col = _ATTRIB_LABELS.get(cat, ((cat, cat), config.COL_TEXT_DIM))
            label = _L(*labelpair)
            widgets.draw_text(surf, label, (inner.x, y + 2), fonts.tiny(), config.COL_TEXT)
            frac = abs(delta) / max_abs
            w = max(2, int(bar_w * 0.5 * frac))
            mid_x = bar_x + bar_w // 2
            bar_rect = (mid_x, y + 3, w, 12) if delta >= 0 else (mid_x - w, y + 3, w, 12)
            pygame.draw.rect(surf, col, bar_rect)
            sign = "+" if delta >= 0 else ""
            widgets.draw_text(surf, f"{sign}{widgets.format_money(delta, cur)}",
                              (bar_x + bar_w, y + 2), fonts.tiny(), col, align="right")

    def _draw_timeline(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _L("Timeline des évènements", "Events timeline"), config.COL_AMBER)
        entries = format_timeline(p.journal, limit=len(p.journal))
        if not entries:
            widgets.draw_text(surf, _L("Votre histoire s'écrira ici : promotions, deals, crises…", "Your story will be written here: promotions, deals, crises…"),
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            self._timeline_list_rect = None
            self._timeline_max_scroll = 0
            return

        # on retrouve le 'kind' d'origine (pour la couleur) en ré-associant par
        # position : format_timeline trie déjà du plus récent au plus ancien,
        # comme list(reversed(journal)).
        kinds = [e.get("kind", "info") for e in list(reversed(p.journal))[:len(entries)]]

        line_h = 22
        rows_per_col = max(1, inner.h // line_h)
        ncols = max(1, min(4, inner.w // 260))
        per_page = rows_per_col * ncols
        colw = inner.w // ncols - 10

        list_area = pygame.Rect(inner.x - 4, inner.y, inner.w + 8, inner.h)
        self._timeline_list_rect = list_area
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        page_off = (self.scroll_timeline // line_h) * ncols
        for i, (label, text) in enumerate(entries[page_off:]):
            idx = page_off + i
            if i >= per_page:
                break
            row = i // ncols
            col = i % ncols
            x = inner.x + col * (colw + 20)
            y = inner.y + row * line_h
            tag = _KIND_COLORS.get(kinds[idx] if idx < len(kinds) else "info", config.COL_TEXT_DIM)
            widgets.draw_text(surf, label, (x, y), fonts.tiny(bold=True), tag)
            font = fonts.tiny()
            widgets.draw_text(surf, widgets.fit_text(text, font, colw - 46),
                              (x + 46, y), font, config.COL_TEXT)
        surf.set_clip(prev_clip)

        n_pages_rows = -(-len(entries) // ncols)   # lignes nécessaires, ncols par ligne
        content_h = n_pages_rows * line_h
        self._timeline_max_scroll = max(0, content_h - inner.h)
        self.scroll_timeline = max(0, min(self._timeline_max_scroll, self.scroll_timeline))
        self.scroll_timeline = widgets.draw_scrollbar(surf, rect, list_area, self.scroll_timeline,
                               self._timeline_max_scroll, content_h)
