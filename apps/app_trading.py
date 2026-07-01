"""
app_trading.py — Application « Trading » du bureau.

Passe des ordres sur les actions vues dans l'app Recherche : recherche,
quantité libre, ACHETER / VENDRE, pouvoir d'achat et levier en direct. Version
fenêtrée et resserrée de la boutique (`scenes/scene_shop.py`), réutilisant la
même logique d'exécution (`core/portfolio.buy/sell`, `core/portfolio_margin`)
et le même verrou de déblocage (`core/unlocks`). Étape 1 : actions au comptant
(les autres classes d'actifs restent accessibles via la boutique classique).
"""
import pygame

from apps.base import DesktopApp
from core import config, unlocks
from core import portfolio as PF
from core import portfolio_margin as PM
from ui import fonts, widgets

ROW_H = 24
QTY_PRESETS = [1, 5, 10, 25, 100]


class TradingApp(DesktopApp):
    title = "Trading — Ordres"
    icon = "💹"
    default_size = (840, 520)
    min_size = (560, 340)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.search = ""
        self.qty_text = "10"
        self.msg = ""
        self.scroll = 0
        self._max_scroll = 0
        self._row_rects = {}
        self._buy_rects = {}
        self._sell_rects = {}
        self._preset_rects = {}
        self._qty_minus = self._qty_plus = None
        self._list_rect = None

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def _qty(self):
        try:
            return max(0.0, float(self.qty_text))
        except ValueError:
            return 0.0

    def _rows(self):
        m = self.market
        q = self.search.strip()
        if q:
            return [tk for tk, _ in m.suggest(q, limit=60)]
        return [c["ticker"] for c in m.top_companies(n=40)]

    def _held(self, tk):
        pos = self.app.gs.player.portfolio.get(tk)
        return pos["shares"] if pos else 0.0

    # --------------------------------------------------------------- actions
    def _do_buy(self, tk):
        if not self._can_trade():
            self.msg = "Trading débloqué au grade Associate."
            return
        qty = self._qty()
        if qty <= 0:
            self.msg = "Quantité invalide."
            return
        r = PF.buy(self.app.gs.player, self.market, tk, qty)
        if r["ok"]:
            self.msg = f"Acheté {qty:g}×{tk} @ {r['price']:.2f}."
            self._autosave()
        else:
            self.msg = f"Achat refusé ({r['reason']})."

    def _do_sell(self, tk):
        if not self._can_trade():
            return
        held = self._held(tk)
        if held <= 0:
            return
        qty = min(self._qty(), held)
        if qty <= 0:
            self.msg = "Quantité invalide."
            return
        r = PF.sell(self.app.gs.player, self.market, tk, qty)
        if r["ok"]:
            self.msg = f"Vendu {r['qty']:g}×{tk} @ {r['price']:.2f} (P&L {r['realized']:+.0f})."
            self._autosave()
        else:
            self.msg = f"Vente refusée ({r['reason']})."

    def _autosave(self):
        p = self.app.gs.player
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._qty_minus and self._qty_minus.collidepoint(event.pos):
                self.qty_text = f"{max(0.0, self._qty() - 1):g}"
                return True
            if self._qty_plus and self._qty_plus.collidepoint(event.pos):
                self.qty_text = f"{self._qty() + 1:g}"
                return True
            for val, r in self._preset_rects.items():
                if r.collidepoint(event.pos):
                    self.qty_text = f"{val:g}"
                    return True
            for tk, r in self._buy_rects.items():
                if r.collidepoint(event.pos):
                    self._do_buy(tk)
                    return True
            for tk, r in self._sell_rects.items():
                if r.collidepoint(event.pos):
                    self._do_sell(tk)
                    return True
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self.scroll = 0
                return True
            if event.unicode and event.unicode.isprintable():
                self.search += event.unicode
                self.scroll = 0
                return True
        return False

    # --------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        pad = 10
        # recherche
        sr = pygame.Rect(rect.x + pad, rect.y + pad, min(280, rect.w - 2 * pad), 24)
        pygame.draw.rect(surf, config.COL_BG, sr, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, sr, 1, border_radius=4)
        curc = "_" if pygame.time.get_ticks() % 1000 < 500 else " "
        lbl = (self.search + curc) if self.search else "Rechercher une action…"
        widgets.draw_text(surf, widgets.fit_text(lbl, fonts.small(), sr.w - 16),
                          (sr.x + 8, sr.y + 4), fonts.small(),
                          config.COL_TEXT if self.search else config.COL_TEXT_DIM)
        # pouvoir d'achat
        st = PM.margin_status(p, self.market)
        widgets.draw_text(surf, f"Pouvoir d'achat {widgets.format_money(st['buying_power'], cur)} · "
                                f"levier {st['leverage']:.2f}x",
                          (rect.right - pad, rect.y + pad + 4), fonts.small(bold=True),
                          config.COL_DOWN if st["margin_call"] else config.COL_TEXT_DIM, align="right")
        # quantité
        qy = sr.bottom + 8
        widgets.draw_text(surf, "QUANTITÉ", (rect.x + pad, qy + 4), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        qx = rect.x + pad + 76
        self._qty_minus = pygame.Rect(qx, qy, 22, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._qty_minus, border_radius=3)
        widgets.draw_text(surf, "-", self._qty_minus.center, fonts.small(bold=True), config.COL_AMBER, align="center")
        qbox = pygame.Rect(qx + 26, qy, 64, 22)
        pygame.draw.rect(surf, config.COL_BG, qbox, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, qbox, 1, border_radius=4)
        widgets.draw_text(surf, self.qty_text or "0", (qbox.x + 8, qbox.y + 3), fonts.small(), config.COL_TEXT)
        self._qty_plus = pygame.Rect(qbox.right + 4, qy, 22, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._qty_plus, border_radius=3)
        widgets.draw_text(surf, "+", self._qty_plus.center, fonts.small(bold=True), config.COL_AMBER, align="center")
        px = self._qty_plus.right + 12
        self._preset_rects = {}
        for val in QTY_PRESETS:
            w = fonts.tiny(bold=True).size(f"x{val}")[0] + 12
            r = pygame.Rect(px, qy, w, 22)
            self._preset_rects[val] = r
            pygame.draw.rect(surf, config.COL_BG, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, f"x{val}", r.center, fonts.tiny(bold=True), config.COL_TEXT_DIM, align="center")
            px += w + 6

        # liste
        list_top = qy + 30
        list_area = pygame.Rect(rect.x + pad, list_top, rect.w - 2 * pad,
                                rect.bottom - list_top - 30)
        self._list_rect = list_area
        pygame.draw.rect(surf, config.COL_BG, list_area)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)
        widgets.draw_text(surf, "VALEUR", (list_area.x + 8, list_area.y + 4), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "COURS", (list_area.x + int(list_area.w * 0.52), list_area.y + 4),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "POSSÉDÉ", (list_area.x + int(list_area.w * 0.66), list_area.y + 4),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        rows = self._rows()
        self._row_rects, self._buy_rects, self._sell_rects = {}, {}, {}
        body = pygame.Rect(list_area.x, list_area.y + 22, list_area.w, list_area.h - 24)
        prev_clip = surf.get_clip()
        surf.set_clip(body)
        y = body.y - self.scroll
        for tk in rows:
            if body.top - ROW_H < y < body.bottom:
                self._draw_row(surf, tk, list_area, y, cur)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = len(rows) * ROW_H
        self._max_scroll = max(0, content_h - body.h)
        self.scroll = min(self.scroll, self._max_scroll)

        # message
        mcol = config.COL_UP if self.msg.startswith(("Acheté", "Vendu")) else config.COL_WARN
        widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.small(), rect.w - 2 * pad),
                          (rect.x + pad, list_area.bottom + 6), fonts.small(), mcol)

    def _draw_row(self, surf, tk, area, y, cur):
        m = self.market
        i = m.ticker_idx.get(tk)
        if i is None:
            return
        c = m.companies[i]
        price = m.price_of(tk)
        held = self._held(tk)
        r = pygame.Rect(area.x + 2, y, area.w - 4, ROW_H - 2)
        mp = pygame.mouse.get_pos()
        if r.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, r)
        widgets.draw_text(surf, tk, (r.x + 6, r.y + 4), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(c["name"], fonts.tiny(), int(area.w * 0.40)),
                          (r.x + 66, r.y + 5), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{price:,.2f}", (area.x + int(area.w * 0.52), r.y + 4),
                          fonts.small(), config.COL_WHITE)
        widgets.draw_text(surf, f"{held:g}" if held else "—",
                          (area.x + int(area.w * 0.66), r.y + 4), fonts.small(bold=held > 0),
                          config.COL_AMBER if held > 0 else config.COL_TEXT_DIM)
        if self._can_trade():
            br = pygame.Rect(r.right - 66, r.y, 64, ROW_H - 4)
            self._buy_rects[tk] = br
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, br, border_radius=3)
            widgets.draw_text(surf, "ACHETER", br.center, fonts.tiny(bold=True), config.COL_UP, align="center")
            if held > 0:
                sre = pygame.Rect(r.right - 134, r.y, 62, ROW_H - 4)
                self._sell_rects[tk] = sre
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, sre, border_radius=3)
                widgets.draw_text(surf, "VENDRE", sre.center, fonts.tiny(bold=True), config.COL_DOWN, align="center")
