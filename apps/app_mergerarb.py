"""
app_mergerarb.py — Application « Arbitrage de fusion » du bureau (NATIVE).

Le desk event-driven : les OPA en cours sur le roster coté (core/merger_arb.py),
avec l'écart de deal à capturer, la probabilité de rupture et le rendement
annualisé implicite. Panneau gauche = opérations tradables (bouton PRENDRE) ;
panneau droit = positions ouvertes avec MTM et sortie anticipée.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import merger_arb as MA
from ui import fonts, widgets

DEFAULT_QTY = 100
QTY_CHOICES = [50, 100, 250, 500]


class MergerArbApp(DesktopApp):
    title = "Arbitrage de fusion"
    icon_kind = "deals"
    default_size = (1080, 620)
    min_size = (820, 480)

    def on_open(self):
        self.qty = DEFAULT_QTY
        self._enter_rects = {}
        self._exit_rects = {}
        self._qty_rects = {}
        self._msg = ""

    def _cur(self):
        try:
            return config.CONTINENTS[self.app.gs.player.continent]["currency"]
        except Exception:
            return "$"

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        market = self.app.ensure_market()
        p = self.app.gs.player
        for q, r in self._qty_rects.items():
            if r.collidepoint(pos):
                self.qty = q
                return True
        for sid, r in self._enter_rects.items():
            if r.collidepoint(pos):
                res = MA.enter(p, market, sid, self.qty)
                if res["ok"]:
                    self._msg = f"Position prise sur {res['position']['ticker']} " \
                                f"({self.qty} parts, {res['cost']:,.0f})."
                else:
                    self._msg = {"cash": "Trésorerie insuffisante.",
                                 "deja": "Position déjà ouverte sur cette opération.",
                                 "qty": "Quantité invalide.",
                                 "inconnue": "Opération introuvable."}.get(
                                     res["reason"], "Refusé.")
                return True
        for pid, r in self._exit_rects.items():
            if r.collidepoint(pos):
                res = MA.exit_position(p, market, pid)
                if res["ok"]:
                    self._msg = f"Sortie anticipée : {res['proceeds']:,.0f} " \
                                f"({res['pnl']:+,.0f})."
                return True
        return False

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        market = self.app.ensure_market()
        p = self.app.gs.player
        pad = 14
        widgets.draw_text(surf, "ARBITRAGE DE FUSION — trading événementiel",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        # sélecteur de quantité
        x = rect.x + pad
        y = rect.y + 32
        widgets.draw_text(surf, "Taille :", (x, y + 3), fonts.tiny(bold=True),
                          config.COL_TEXT_DIM)
        x += 56
        self._qty_rects = {}
        for q in QTY_CHOICES:
            w = fonts.tiny(bold=True).size(str(q))[0] + 16
            r = pygame.Rect(x, y, w, 20)
            self._qty_rects[q] = r
            sel = q == self.qty
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, str(q), r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        if self._msg:
            widgets.draw_text(surf, widgets.fit_text(self._msg, fonts.tiny(),
                              rect.right - x - pad), (x + 10, y + 3), fonts.tiny(),
                              config.COL_CYAN)

        col_w = (rect.w - 3 * pad) // 2
        left = pygame.Rect(rect.x + pad, y + 28, col_w, rect.bottom - (y + 28) - pad)
        right = pygame.Rect(left.right + pad, y + 28, col_w, left.h)
        self._draw_deals(surf, left, market, p)
        self._draw_positions(surf, right, market, p)

    def _draw_deals(self, surf, body, market, p):
        cur = self._cur()
        inner = widgets.draw_panel(surf, body, "Opérations en cours (OPA)", config.COL_CYAN)
        self._enter_rects = {}
        sits = MA.active_situations(market)
        if not sits:
            widgets.draw_text(surf, "Aucune opération annoncée pour le moment.",
                              (inner.x, inner.y + 6), fonts.small(), config.COL_TEXT_DIM)
            return
        held = {pos["deal_id"] for pos in (getattr(p, "arb_positions", None) or [])}
        yy = inner.y
        for s in sits:
            if yy > inner.bottom - 54:
                break
            row = pygame.Rect(inner.x, yy, inner.w, 50)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
            widgets.draw_text(surf, f"{s['acquirer']} → {s['name']} ({s['ticker']})",
                              (row.x + 8, row.y + 4), fonts.small(bold=True), config.COL_TEXT)
            spread_pct = (s["offer"] / s["implied"] - 1) * 100 if s["implied"] else 0
            widgets.draw_text(surf,
                              f"Offre {widgets.format_money(s['offer'], cur)} "
                              f"(+{s['premium'] * 100:.0f}%) · écart {spread_pct:.1f}% · "
                              f"{s['steps_left']} pas · rupture {s['break_prob'] * 100:.0f}%",
                              (row.x + 8, row.y + 24), fonts.tiny(), config.COL_TEXT_DIM)
            if s["id"] in held:
                widgets.draw_text(surf, "détenue", (row.right - 12, row.y + 6),
                                  fonts.tiny(bold=True), config.COL_UP, align="right")
            else:
                btn = pygame.Rect(row.right - 96, row.y + 12, 88, 24)
                self._enter_rects[s["id"]] = btn
                pygame.draw.rect(surf, config.COL_PANEL, btn, border_radius=4)
                pygame.draw.rect(surf, config.COL_CYAN, btn, 1, border_radius=4)
                widgets.draw_text(surf, "PRENDRE", btn.center, fonts.tiny(bold=True),
                                  config.COL_CYAN, align="center")
            yy += 56
        widgets.draw_text(surf, "Acheter sous l'offre : gain si l'opération conclut, "
                          "perte si elle rompt.", (inner.x, inner.bottom - 12),
                          fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_positions(self, surf, body, market, p):
        cur = self._cur()
        inner = widgets.draw_panel(surf, body, "Mes positions d'arbitrage", config.COL_AMBER)
        self._exit_rects = {}
        rows = MA.positions(p, market)
        if not rows:
            widgets.draw_text(surf, "Aucune position ouverte.", (inner.x, inner.y + 6),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        yy = inner.y
        for r in rows:
            if yy > inner.bottom - 54:
                break
            row = pygame.Rect(inner.x, yy, inner.w, 50)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=4)
            pcol = config.COL_UP if r["pnl"] >= 0 else config.COL_DOWN
            pygame.draw.rect(surf, pcol, row, 1, border_radius=4)
            widgets.draw_text(surf, f"{r['ticker']} — {r['acquirer']}",
                              (row.x + 8, row.y + 4), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf,
                              f"{r['qty']:.0f} × {widgets.format_money(r['price'], cur)} · "
                              f"P&L latent {r['pnl']:+,.0f} · {r['steps_left']} pas",
                              (row.x + 8, row.y + 24), fonts.tiny(), pcol)
            btn = pygame.Rect(row.right - 82, row.y + 12, 74, 24)
            self._exit_rects[r["id"]] = btn
            pygame.draw.rect(surf, config.COL_PANEL, btn, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER, btn, 1, border_radius=4)
            widgets.draw_text(surf, "SORTIR", btn.center, fonts.tiny(bold=True),
                              config.COL_AMBER, align="center")
            yy += 56
