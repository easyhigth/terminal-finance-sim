"""
scene_governments.py — Écran PAYS / GOUVERNEMENTS.

Liste des pays à gauche (groupés par région), fiche détaillée à droite : note
souveraine, dette/PIB, stabilité politique, régime, devise, HISTORIQUE sur ~5 ans
(inspiré du réel) et OBLIGATIONS souveraines du pays (rendement/prix en direct,
réagissant aux événements politiques). Ouvert via la commande GOV.

Objectif pédagogique : montrer que le risque souverain (rating + dette +
stabilité) pilote le rendement exigé des obligations, et que les événements
politiques régionaux font bouger ces spreads.
"""
import pygame

from core import bonds as B
from core import config
from core import governments as G
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets

# ordre d'affichage des régions
_REGION_ORDER = ["USA", "Am.Nord", "Europe", "Am.Sud", "Afrique", "Asia", "Océanie"]


class GovernmentsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        focus = kwargs.get("focus")
        codes = G.all_codes()
        self.sel = focus if (focus in codes) else codes[0]
        self.row_rects = {}
        self._code_order = []
        self._row_offsets = {}
        self.list_scroll = 0
        self._list_max = 0
        self.detail_scroll = 0
        self._detail_max = 0
        self._detail_rect = None
        self._list_rect = None
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.bonds_btn = widgets.Button(
            (260, config.SCREEN_HEIGHT - 50, 200, 42), "MARCHÉ OBLIGATAIRE", config.COL_CYAN)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN) and self._code_order:
            idx = self._code_order.index(self.sel) if self.sel in self._code_order else 0
            idx = (idx + (1 if event.key == pygame.K_DOWN else -1)) % len(self._code_order)
            self.sel = self._code_order[idx]
            self.detail_scroll = 0
            off = self._row_offsets.get(self.sel)
            if off is not None and self._list_rect:
                if off < self.list_scroll:
                    self.list_scroll = off
                elif off + 24 > self.list_scroll + self._list_rect.h:
                    self.list_scroll = off + 24 - self._list_rect.h
                self.list_scroll = max(0, min(self._list_max, self.list_scroll))
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if self.bonds_btn.handle(event):
            self.app.scenes.go("bonds", return_to="governments")
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for code, rect in self.row_rects.items():
                    if rect.collidepoint(event.pos):
                        self.sel = code
                        self.detail_scroll = 0
            elif event.button in (4, 5):
                d = -36 if event.button == 4 else 36
                mp = event.pos
                if self._detail_rect and self._detail_rect.collidepoint(mp):
                    self.detail_scroll = max(0, min(self._detail_max, self.detail_scroll + d))
                elif self._list_rect and self._list_rect.collidepoint(mp):
                    self.list_scroll = max(0, min(self._list_max, self.list_scroll + d))

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.bonds_btn.update(mp, dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        lang = get_lang()
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "GOUVERNEMENTS & RISQUE SOUVERAIN", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Note, dette/PIB et stabilité pilotent le rendement exigé "
                                "des obligations · les événements politiques font bouger les spreads.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)
        ph = config.footer_y() - 8 - 100
        self._draw_list(surf, pygame.Rect(40, 100, 320, ph), lang)
        self._draw_detail(surf, pygame.Rect(380, 100, config.SCREEN_WIDTH - 420, ph), lang)
        hints = [("↑↓", "country")] if lang == "en" else [("↑↓", "pays")]
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14), hints)
        self.back_btn.draw(surf)
        self.bonds_btn.draw(surf)

    def _draw_list(self, surf, panel, lang):
        inner = widgets.draw_panel(surf, panel, "Pays", config.COL_CYAN)
        self._list_rect = inner
        self.row_rects = {}
        self._code_order = []
        self._row_offsets = {}
        prev_clip = surf.get_clip()
        surf.set_clip(inner)
        y = inner.y - self.list_scroll
        for region in _REGION_ORDER:
            govs = G.by_region(region)
            if not govs:
                continue
            widgets.draw_text(surf, region.upper(), (inner.x, y),
                              fonts.tiny(bold=True), config.COL_AMBER_DIM)
            y += 18
            for g in govs:
                rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 24)
                self.row_rects[g["code"]] = rect
                self._code_order.append(g["code"])
                self._row_offsets[g["code"]] = y - inner.y + self.list_scroll
                sel = (g["code"] == self.sel)
                if sel:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
                    pygame.draw.rect(surf, config.COL_AMBER, (inner.x - 4, y - 2, 3, 24))
                name = G.localized_name(g, lang)
                widgets.draw_text(surf, widgets.fit_text(name, fonts.small(bold=sel), inner.w - 50),
                                  (inner.x + 6, y + 3), fonts.small(bold=sel),
                                  config.COL_WHITE if sel else config.COL_TEXT)
                widgets.draw_text(surf, g["rating"], (inner.right - 6, y + 3),
                                  fonts.tiny(bold=True), widgets.rating_color(g["rating"]), align="right")
                y += 26
            y += 6
        surf.set_clip(prev_clip)
        content_h = (y + self.list_scroll) - inner.y
        self._list_max = max(0, content_h - inner.h)
        self.list_scroll = min(self.list_scroll, self._list_max)

    def _draw_detail(self, surf, panel, lang):
        inner = widgets.draw_panel(surf, panel, "Fiche pays", config.COL_AMBER)
        self._detail_rect = panel
        g = G.get(self.sel)
        if not g:
            return
        market = getattr(self.app, "market", None)
        prev_clip = surf.get_clip()
        surf.set_clip(inner)
        oy = -self.detail_scroll
        y = inner.y + oy
        x = inner.x

        # en-tête : nom + région + devise
        widgets.draw_text(surf, G.localized_name(g, lang), (x, y), fonts.head(bold=True),
                          config.COL_WHITE)
        y += 30
        widgets.draw_text(surf, f"{g['region']} · {g['currency']} · {g['regime']}",
                          (x, y), fonts.small(), config.COL_TEXT_DIM)
        y += 26

        # tuiles : rating, dette/PIB, stabilité
        tile_w = (inner.w - 2 * 12) // 3
        widgets.draw_tile(surf, (x, y, tile_w, 46), "Note souveraine", g["rating"],
                          widgets.rating_color(g["rating"]), widgets.rating_color(g["rating"]))
        widgets.draw_tile(surf, (x + tile_w + 12, y, tile_w, 46), "Dette / PIB",
                          f"{g['debt_gdp']}%", config.COL_AMBER,
                          config.COL_DOWN if g["debt_gdp"] >= 100 else config.COL_TEXT)
        stab = g["stability"]
        scol = (config.COL_UP if stab >= 0.7 else config.COL_WARN if stab >= 0.52 else config.COL_DOWN)
        widgets.draw_tile(surf, (x + 2 * (tile_w + 12), y, tile_w, 46), "Stabilité",
                          G.stability_label(stab), scol, scol)
        y += 54
        # jauge de stabilité
        widgets.draw_progress(surf, (x, y, inner.w, 8), stab, scol)
        y += 18
        prime = G.country_premium(g) * 100
        widgets.draw_text(surf, f"Prime de risque pays ≈ +{prime:.2f}% sur le rendement souverain.",
                          (x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 24

        # historique 5 ans
        widgets.draw_text(surf, "HISTORIQUE (≈5 ANS)", (x, y), fonts.tiny(bold=True), config.COL_CYAN)
        pygame.draw.line(surf, config.COL_BORDER, (x, y + 17), (inner.right, y + 17), 1)
        y += 24
        kindcol = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_TEXT_DIM}
        for h in g["history"]:
            col = kindcol.get(h["kind"], config.COL_TEXT_DIM)
            widgets.draw_text(surf, str(h["y"]), (x, y), fonts.small(bold=True), config.COL_AMBER)
            txt = h["en"] if lang == "en" else h["fr"]
            dh = widgets.draw_text_wrapped(surf, txt, (x + 48, y), fonts.small(), col, inner.w - 48)
            y += max(dh, 18) + 6

        # obligations du pays
        y += 6
        widgets.draw_text(surf, "OBLIGATIONS SOUVERAINES", (x, y), fonts.tiny(bold=True), config.COL_CYAN)
        pygame.draw.line(surf, config.COL_BORDER, (x, y + 17), (inner.right, y + 17), 1)
        y += 22
        cols = [("OBLIGATION", x), ("RATING", x + 220), ("COUPON", x + 300),
                ("MAT.", x + 380), ("YTM", x + 450), ("PRIX", x + 540), ("DUR.", x + 640)]
        for label, cx in cols:
            widgets.draw_text(surf, label, (cx, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 20
        govbonds = [q for q in B.sovereign_quotes(market) if q["gov"] == g["code"]]
        if not govbonds:
            widgets.draw_text(surf, "Aucune obligation cotée pour ce pays.", (x, y),
                              fonts.small(), config.COL_TEXT_DIM)
            y += 22
        for q in sorted(govbonds, key=lambda b: b["years"]):
            widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(), 210),
                              (cols[0][1], y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, q["rating"], (cols[1][1], y), fonts.small(bold=True),
                              widgets.rating_color(q["rating"]))
            widgets.draw_text(surf, f"{q['coupon']*100:.1f}%", (cols[2][1], y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['years']}a", (cols[3][1], y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['ytm']*100:.2f}%", (cols[4][1], y), fonts.small(), config.COL_CYAN)
            widgets.draw_text(surf, f"{q['price']:.1f}", (cols[5][1], y), fonts.small(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, f"{q['mod_duration']:.1f}", (cols[6][1], y), fonts.small(), config.COL_TEXT_DIM)
            y += 24

        # bump de crédit régional courant (réaction politique en direct)
        bump = getattr(market, "region_credit_bump", {}).get(g["region"], 0.0) if market else 0.0
        if abs(bump) > 1e-5:
            sign = "+" if bump > 0 else ""
            bcol = config.COL_DOWN if bump > 0 else config.COL_UP
            y += 4
            widgets.draw_text(surf, f"» Tension politique régionale : spread {sign}{bump*10000:.0f} bps "
                              "(les prix obligataires de la zone réagissent).",
                              (x, y), fonts.tiny(bold=True), bcol)
            y += 20

        surf.set_clip(prev_clip)
        content_h = y - (inner.y + oy)
        self._detail_max = max(0, content_h - inner.h)
        self.detail_scroll = min(self.detail_scroll, self._detail_max)
        # barre de défilement
        if self._detail_max > 0:
            track = pygame.Rect(panel.right - 8, inner.y, 6, inner.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = inner.h / (content_h or 1)
            bar_h = max(24, int(inner.h * frac))
            bar_y = inner.y + int((inner.h - bar_h) * (self.detail_scroll / self._detail_max))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)
