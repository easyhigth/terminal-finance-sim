"""
scene_performance.py — Module Performance : attribution de la performance du
book réel sur le dernier pas de marché.
Quatre axes, tous calculés par core/attribution.py (logique pure) :
  - secteur / région : P&L de prix ventilé par secteur/région des positions actions
  - style : Croissance vs Valeur (proxy rendement du dividende)
  - sélection de titres vs timing : réutilise le modèle à facteurs du marché
    (composante spécifique = stock-picking, monde + dérive = timing)
"""
import pygame

from core import attribution, config
from core.scene_manager import Scene
from ui import fonts, widgets

_BAR_COLORS = [config.COL_CYAN, config.COL_AMBER, config.COL_PRESTIGE, config.COL_WARN,
               config.COL_UP, config.COL_DOWN, config.COL_TEXT]


def _fm_signed(v, cur):
    return ("+" if v >= 0 else "") + widgets.format_money(v, cur)


class PerformanceScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        m = self.market
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")

        widgets.draw_text(surf, "ANALYSE DE PERFORMANCE — ATTRIBUTION",
                          (40, 20), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "P&L de prix du dernier pas, ventilé par secteur, région, "
                          "style, sélection de titres et timing.",
                          (42, 64), fonts.small(), config.COL_TEXT_DIM)

        if not p.portfolio:
            widgets.draw_text(surf, "Aucune position actions. Achetez des titres (BUY) "
                              "pour voir l'attribution de performance.",
                              (40, 120), fonts.body(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        top = 100
        M = config.MARGIN
        bottom = config.footer_y() - 8
        h = bottom - top
        colw = (config.SCREEN_WIDTH - 3 * M) // 2
        x1 = M
        x2 = M + colw + M
        half_h = (h - M) // 2

        self._draw_bucket(surf, pygame.Rect(x1, top, colw, half_h), cur,
                          "Par secteur", attribution.sector_attribution(p, m))
        self._draw_bucket(surf, pygame.Rect(x1, top + half_h + M, colw, half_h), cur,
                          "Par région", attribution.region_attribution(p, m))
        self._draw_bucket(surf, pygame.Rect(x2, top, colw, half_h), cur,
                          "Par style (Croissance / Valeur)", attribution.style_attribution(p, m))
        self._draw_selection_timing(surf, pygame.Rect(x2, top + half_h + M, colw, half_h), cur, p, m)
        self.back_btn.draw(surf)

    def _draw_bucket(self, surf, rect, cur, title, data):
        inner = widgets.draw_panel(surf, rect, title, config.COL_CYAN)
        if not data:
            widgets.draw_text(surf, "Aucune donnée (premier pas du marché).",
                              (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
            return
        items = sorted(data.items(), key=lambda kv: -abs(kv[1]))
        max_abs = max(abs(v) for _, v in items) or 1.0
        y = inner.y
        row_h = min(28, max(16, (inner.h - 10) // max(1, len(items))))
        bar_x = inner.x + 140
        bar_w = inner.w - 140 - 110
        for i, (k, v) in enumerate(items):
            col = config.COL_UP if v >= 0 else config.COL_DOWN
            widgets.draw_text(surf, widgets.fit_text(str(k), fonts.tiny(), 132),
                              (inner.x, y + 4), fonts.tiny(), config.COL_TEXT)
            mid = bar_x + bar_w // 2
            frac = abs(v) / max_abs
            w = int(bar_w / 2 * frac)
            if v >= 0:
                pygame.draw.rect(surf, col, (mid, y + 6, w, row_h - 12))
            else:
                pygame.draw.rect(surf, col, (mid - w, y + 6, w, row_h - 12))
            pygame.draw.line(surf, config.COL_BORDER, (mid, y), (mid, y + row_h - 4), 1)
            widgets.draw_text(surf, _fm_signed(v, cur),
                              (inner.right, y + 4), fonts.tiny(bold=True), col, align="right")
            y += row_h

    def _draw_selection_timing(self, surf, rect, cur, p, m):
        inner = widgets.draw_panel(surf, rect, "Sélection de titres vs. timing", config.COL_WARN)
        st = attribution.selection_timing_attribution(p, m)
        if st["total"] == 0.0 and not p.portfolio:
            widgets.draw_text(surf, "Aucune donnée.", (inner.x, inner.y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        rows = [
            ("Sélection de titres (spécifique)", st["selection"]),
            ("Timing (monde + dérive)", st["timing"]),
            ("Effet secteur (facteur)", st["sector_factor"]),
            ("Effet région (facteur)", st["region_factor"]),
        ]
        y = inner.y
        max_abs = max(abs(v) for _, v in rows) or 1.0
        for label, v in rows:
            col = config.COL_UP if v >= 0 else config.COL_DOWN
            widgets.draw_text(surf, label, (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 14
            bw = inner.w - 20
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, (inner.x, y, bw, 10))
            w = int(bw * min(1.0, abs(v) / max_abs))
            pygame.draw.rect(surf, col, (inner.x, y, w, 10))
            widgets.draw_text(surf, _fm_signed(v, cur),
                              (inner.right, y - 14), fonts.tiny(bold=True), col, align="right")
            y += 22
        y += 6
        pygame.draw.line(surf, config.COL_BORDER, (inner.x, y), (inner.right, y), 1)
        y += 8
        tcol = config.COL_UP if st["total"] >= 0 else config.COL_DOWN
        widgets.draw_text(surf, "P&L total (dernier pas)", (inner.x, y),
                          fonts.small(bold=True), config.COL_WHITE)
        widgets.draw_text(surf, _fm_signed(st["total"], cur),
                          (inner.right, y), fonts.small(bold=True), tcol, align="right")
