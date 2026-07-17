"""
app_fxdesk.py — Application « Desk FX (carry) » du bureau (NATIVE).

Le change avec sa dimension de TAUX (core/fx_carry.py) :

- table des paires triées par carry : taux des deux devises, portage
  annuel d'une position longue, forward THÉORIQUE 3 mois par parité des
  taux couverte et points de terme — la devise à haut taux cote forward
  DÉCOTÉ (le marché « rembourse » le carry : pas d'arbitrage sans risque,
  c'est le théorème) ;
- exécution LONG/SHORT réelle (core/fx.open_spot) — le portage couru est
  crédité à chaque pas par le moteur (fx_carry.accrue, câblé dans
  advance_step) : le carry devient un revenu quotidien… jusqu'au jour où
  la paire décroche (testez-le dans le Labo de crise) ;
- positions ouvertes avec P&L de prix ET carry couru estimé.
"""
import pygame

from apps.base import DesktopApp
from core import config, fx
from core import fx_carry as FXC
from ui import fonts, widgets

NOTIONALS = [50_000.0, 100_000.0, 250_000.0]


class FxDeskApp(DesktopApp):
    title = "Desk FX (carry)"
    icon_kind = "market"
    default_size = (1040, 620)
    min_size = (800, 480)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.pair = None
        self.notional = NOTIONALS[1]
        self.msg = ""
        self.msg_col = config.COL_TEXT_DIM
        self._cache_key = None
        self._table = []
        self._row_rects = {}
        self._notional_rects = {}
        self._long_btn = None
        self._short_btn = None
        self._close_rects = {}

    def _ensure_computed(self):
        key = self.market.step_count
        if key == self._cache_key:
            return
        self._cache_key = key
        self._table = FXC.carry_table(self.market)
        if self.pair is None and self._table:
            self.pair = self._table[0]["pair"]

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for pair, r in self._row_rects.items():
            if r.collidepoint(pos):
                self.pair = pair
                self.msg = ""
                return True
        for v, r in self._notional_rects.items():
            if r.collidepoint(pos):
                self.notional = v
                return True
        for direction, btn in (("long", self._long_btn),
                               ("short", self._short_btn)):
            if btn and btn.collidepoint(pos):
                self._open(direction)
                return True
        for pid, r in self._close_rects.items():
            if r.collidepoint(pos):
                res = fx.close_spot(self.app.gs.player, self.market, pid)
                if res.get("ok"):
                    self._say(f"Position fermée — P&L "
                              f"{res.get('pnl', 0.0):+,.0f}.", config.COL_TEXT)
                return True
        return False

    def _open(self, direction):
        p = self.app.gs.player
        r = fx.open_spot(p, self.market, self.pair, direction, self.notional)
        if r.get("ok"):
            carry = FXC.carry_annual(self.market, self.pair, direction)
            ccol = config.COL_UP if carry > 0 else config.COL_DOWN
            self._say(f"{direction.upper()} {self.pair} ouvert — portage "
                      f"{carry * 100:+.1f}%/an couru chaque pas.", ccol)
        else:
            self._say(f"Refusé : {r.get('reason', '?')}.", config.COL_DOWN)

    def _say(self, text, col):
        self.msg, self.msg_col = text, col

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        widgets.draw_text(surf, "DESK FX — CARRY & PARITÉ DES TAUX",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        widgets.draw_text(surf, "Long la paire = long la devise de BASE → on "
                          "touche (r_base − r_cotée). Le forward décote la "
                          "devise à haut taux : pas de repas gratuit couvert.",
                          (rect.x + pad, rect.y + 30), fonts.tiny(),
                          config.COL_TEXT_DIM)
        body = pygame.Rect(rect.x + pad, rect.y + 52, rect.w - 2 * pad,
                           rect.bottom - pad - rect.y - 52)
        col_w = int(body.w * 0.60)
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, body.w - col_w - 12, body.h)
        self._draw_table(surf, left)
        self._draw_panel(surf, right, cur)

    def _draw_table(self, surf, rect):
        inner = widgets.draw_panel(surf, rect,
                                   "Paires (triées par |carry|) · fwd 3 mois",
                                   config.COL_CYAN)
        self._row_rects = {}
        cols = [("PAIRE", 0), ("SPOT", int(inner.w * 0.20)),
                ("r base/cotée", int(inner.w * 0.36)),
                ("CARRY long", int(inner.w * 0.58)),
                ("PTS TERME", int(inner.w * 0.80))]
        y = inner.y
        for lbl, dx in cols:
            widgets.draw_text(surf, lbl, (inner.x + dx, y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        y += 16
        for row in self._table:
            if y > inner.bottom - 16:
                break
            r = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 19)
            self._row_rects[row["pair"]] = r
            sel = row["pair"] == self.pair
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, row["pair"], (inner.x, y),
                              fonts.small(bold=True),
                              config.COL_AMBER if sel else config.COL_TEXT)
            widgets.draw_text(surf, f"{row['spot']:,.3f}",
                              (inner.x + cols[1][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{row['r_base'] * 100:.1f}/{row['r_quote'] * 100:.1f}%",
                              (inner.x + cols[2][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            ccol = config.COL_UP if row["carry_long"] > 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{row['carry_long'] * 100:+.1f}%/an",
                              (inner.x + cols[3][1], y), fonts.small(bold=True), ccol)
            widgets.draw_text(surf, f"{row['points_pct']:+.2f}%",
                              (inner.x + cols[4][1], y), fonts.small(),
                              config.COL_TEXT)
            y += 20
        fwd_hint = ("Points de terme ≈ −carry × τ : la parité couverte rend "
                   "le carry non-arbitrable sans risque.")
        fwd_font = fonts.tiny()
        fwd_lines = len(widgets.wrap_text_lines(fwd_hint, fwd_font, inner.w))
        fwd_h = fwd_lines * (fwd_font.get_height() + 3)
        widgets.draw_text_wrapped(surf, fwd_hint, (inner.x, inner.bottom - fwd_h),
                                  fwd_font, config.COL_TEXT_DIM, inner.w, line_gap=3)

    def _draw_panel(self, surf, rect, cur):
        inner = widgets.draw_panel(surf, rect, "Exécution & positions",
                                   config.COL_AMBER)
        self._close_rects = {}
        y = inner.y + 2
        if self.pair:
            carry = FXC.carry_annual(self.market, self.pair, "long")
            vol = fx.pair_vol(self.pair)
            widgets.draw_text(surf, f"{self.pair} — carry long "
                              f"{carry * 100:+.1f}%/an · vol {vol * 100:.0f}%",
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            y += 18
            ratio = abs(carry) / vol if vol > 0 else 0.0
            ratio_txt = (f"Carry/vol = {ratio:.2f} — le portage paie-t-il le "
                        "risque de décrochage ?")
            ratio_font = fonts.tiny()
            y += widgets.draw_text_wrapped(surf, ratio_txt, (inner.x, y), ratio_font,
                                           config.COL_TEXT_DIM, inner.w) + 2
            # le carry traduit en devise PAR TOUR pour le notionnel choisi
            from core import impact_phrases as _ip
            phrase = _ip.fx_carry_impact(self.notional, carry)
            if phrase:
                y += widgets.draw_text_wrapped(surf, phrase, (inner.x, y), fonts.tiny(),
                                               config.COL_WARN, inner.w, line_gap=3) + 4
        self._notional_rects = {}
        x = inner.x
        for v in NOTIONALS:
            lbl = widgets.format_money(v, cur)
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, y, w, 20)
            self._notional_rects[v] = r
            sel = abs(v - self.notional) < 1e-9
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM,
                              align="center")
            x += w + 6
        y += 28
        self._long_btn = pygame.Rect(inner.x, y, 110, 24)
        self._short_btn = pygame.Rect(inner.x + 118, y, 110, 24)
        for r, lbl, col in ((self._long_btn, "LONG", config.COL_UP),
                            (self._short_btn, "SHORT", config.COL_DOWN)):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=4)
            pygame.draw.rect(surf, col, r, 1, border_radius=4)
            widgets.draw_text(surf, lbl, r.center, fonts.small(bold=True), col,
                              align="center")
        y += 34
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(), inner.w),
                              (inner.x, y), fonts.tiny(), self.msg_col)
            y += 18
        widgets.draw_text(surf, "POSITIONS OUVERTES :", (inner.x, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 16
        holdings = fx.holdings(self.app.gs.player, self.market)
        if not holdings:
            widgets.draw_text(surf, "Aucune.", (inner.x, y), fonts.tiny(),
                              config.COL_TEXT_DIM)
        for h in holdings:
            if y > inner.bottom - 18:
                break
            pnl = h.get("pnl", 0.0)
            pcol = config.COL_UP if pnl >= 0 else config.COL_DOWN
            carry = FXC.carry_annual(self.market, h["pair"],
                                     h.get("direction", "long"))
            widgets.draw_text(surf, f"{h.get('direction', '?').upper()} {h['pair']} "
                              f"{widgets.format_money(h['notional'], cur)}",
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"P&L {pnl:+,.0f} · carry {carry * 100:+.1f}%/an",
                              (inner.x + 8, y + 15), fonts.tiny(), pcol)
            xr = pygame.Rect(inner.right - 22, y, 18, 18)
            self._close_rects[h["id"]] = xr
            pygame.draw.rect(surf, config.COL_PANEL, xr, border_radius=3)
            widgets.draw_text(surf, "×", xr.center, fonts.small(bold=True),
                              config.COL_DOWN, align="center")
            y += 34
