"""
app_pnlexplain.py — Application « P&L Explain » du bureau (NATIVE).

Le rituel n°1 d'un desk réel : chaque matin, expliquer d'où vient CHAQUE
euro d'hier. À chaque pas de marché, advance_step dépose un instantané
(player.flags['pnl_explain']) ; l'app le décompose :

    Δ patrimoine = effet PRIX (les positions ont bougé — ventilé par
                   secteur via core/attribution, le module du dernier pas)
                 + REVENUS PASSIFS (dividendes, coupons, carry FX, repo,
                   prêt-titres, sweep, flux de dérivés — tout ce que le
                   moteur a couru pendant le pas)
                 + RESTE (salaire, frais, opérations du joueur)

S'y ajoute la jauge de la LIMITE DE VaR DE LA FIRME (core/risklimits) :
la VaR du book vs le budget de risque du grade — l'avertissement, la
sanction, puis la coupe forcée tombent au-delà (advance_step).
"""
import pygame

from apps.base import DesktopApp
from core import attribution as ATTR
from core import config, risklimits
from ui import fonts, widgets


class PnlExplainApp(DesktopApp):
    title = "P&L Explain"
    icon_kind = "graph"
    default_size = (940, 580)
    min_size = (720, 440)

    def on_open(self):
        self.market = self.app.ensure_market()
        self._cache_key = None
        self._sector = {}
        self._firm = None

    def _ensure_computed(self):
        p = self.app.gs.player
        key = (self.market.step_count, len(p.portfolio))
        if key == self._cache_key:
            return
        self._cache_key = key
        try:
            self._sector = ATTR.sector_attribution(p, self.market)
        except Exception:
            self._sector = {}
        self._firm = risklimits.firm_var_check(p, self.market, n=3000)

    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "P&L EXPLAIN — D'OÙ VIENT CHAQUE EURO ?",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        snap = p.flags.get("pnl_explain")
        y = rect.y + 36
        if not snap:
            widgets.draw_text(surf, "Aucun pas de marché encore joué — le "
                              "premier instantané tombera au prochain pas.",
                              (rect.x + pad, y), fonts.small(), config.COL_TEXT_DIM)
            self._draw_firm_gauge(surf, pygame.Rect(rect.x + pad, y + 40,
                                                    rect.w - 2 * pad, 70), cur)
            return
        delta = snap["nw"] - snap["nw_prev"]
        passive = snap.get("passive", 0.0)
        price_and_rest = delta - passive
        dcol = config.COL_UP if delta >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"Dernier pas (jour {snap['day']}) : "
                          f"Δ patrimoine {widgets.format_money(delta, cur)}",
                          (rect.x + pad, y), fonts.title(bold=True), dcol)
        y += 34
        rows = [
            ("REVENUS PASSIFS (dividendes, coupons, carry, repo, prêt-titres, "
             "sweep, dérivés)", passive, config.COL_UP if passive >= 0
             else config.COL_DOWN),
            ("PRIX & RESTE (positions qui bougent, salaire, frais, vos ordres)",
             price_and_rest, config.COL_UP if price_and_rest >= 0
             else config.COL_DOWN),
        ]
        vmax = max(abs(v) for _l, v, _c in rows) or 1.0
        bar_w = rect.w - 2 * pad - 420
        for label, v, col in rows:
            widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(bold=True),
                                                     360),
                              (rect.x + pad, y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
            bx = rect.x + pad + 370
            w = int(abs(v) / vmax * bar_w * 0.9)
            pygame.draw.rect(surf, col, pygame.Rect(bx, y + 2, max(2, w), 11),
                             border_radius=2)
            widgets.draw_text(surf, widgets.format_money(v, cur),
                              (bx + w + 8, y), fonts.small(bold=True), col)
            y += 22
        y += 8
        # ventilation PRIX par secteur (attribution du dernier pas)
        body = pygame.Rect(rect.x + pad, y, rect.w - 2 * pad,
                           rect.bottom - pad - y - 84)
        inner = widgets.draw_panel(surf, body,
                                   "Effet prix du pas, par secteur "
                                   "(core/attribution)", config.COL_CYAN)
        if not self._sector:
            widgets.draw_text(surf, "Aucune position action.",
                              (inner.x, inner.y + 4), fonts.tiny(),
                              config.COL_TEXT_DIM)
        else:
            entries = sorted(self._sector.items(), key=lambda kv: abs(kv[1]),
                             reverse=True)[:10]
            smax = max((abs(v) for _s, v in entries), default=1.0) or 1.0
            yy = inner.y + 2
            sbar = inner.w - 320
            for sector, v in entries:
                if yy > inner.bottom - 16:
                    break
                col = config.COL_UP if v >= 0 else config.COL_DOWN
                widgets.draw_text(surf, widgets.fit_text(str(sector),
                                                         fonts.small(bold=True), 170),
                                  (inner.x, yy), fonts.small(bold=True),
                                  config.COL_TEXT)
                bx = inner.x + 180
                mid = bx + sbar // 2
                w = int(abs(v) / smax * sbar * 0.5)
                pygame.draw.line(surf, config.COL_BORDER, (mid, yy), (mid, yy + 12))
                pygame.draw.rect(surf, col,
                                 pygame.Rect(mid if v >= 0 else mid - w, yy + 2,
                                             w, 9), border_radius=2)
                widgets.draw_text(surf, widgets.format_money(v, cur),
                                  (bx + sbar + 8, yy), fonts.tiny(bold=True), col)
                yy += 18
        self._draw_firm_gauge(surf, pygame.Rect(rect.x + pad, rect.bottom - pad - 74,
                                                rect.w - 2 * pad, 70), cur)

    def _draw_firm_gauge(self, surf, rect, cur):
        """Jauge de la limite de VaR de la firme : votre budget de risque de
        grade, et où vous en êtes — dépasser déclenche l'escalade."""
        inner = widgets.draw_panel(surf, rect, "Budget de risque de la firme",
                                   config.COL_DOWN)
        f = self._firm
        if f is None:
            return
        ratio = min(1.5, f["ratio"])
        gauge = pygame.Rect(inner.x, inner.y + 4, inner.w - 240, 12)
        pygame.draw.rect(surf, config.COL_PANEL, gauge, border_radius=4)
        col = (config.COL_DOWN if f["breach"]
               else config.COL_AMBER if ratio > 0.75 else config.COL_UP)
        pygame.draw.rect(surf, col,
                         pygame.Rect(gauge.x, gauge.y,
                                     int(gauge.w * min(1.0, ratio / 1.5)), 12),
                         border_radius=4)
        lim_x = gauge.x + int(gauge.w / 1.5)
        pygame.draw.line(surf, config.COL_WHITE, (lim_x, gauge.y - 3),
                         (lim_x, gauge.bottom + 3), 2)
        widgets.draw_text(surf, f"VaR {f['var']:.2f} M / limite du grade "
                          f"{f['limit']:.2f} M",
                          (gauge.right + 12, gauge.y - 1), fonts.small(bold=True),
                          col)
        widgets.draw_text(surf, "Au-delà : avertissement → réputation → la firme "
                          "COUPE votre plus grosse ligne (5 pas de dépassement).",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
