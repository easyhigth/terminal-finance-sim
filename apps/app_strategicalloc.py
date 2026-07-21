"""
app_strategicalloc.py — Application « Allocation stratégique » du bureau
(NATIVE, EXCLUSIVE voie Portfolio, cf.
core/unlocks.TRACK_AFFINITY["strategicalloc"] et scene_desktop_common.TRACK_APP).

Allocation multi-classes d'actifs (core/strategic_allocation.py) : donut de
répartition actuelle vs cible (profil prédéfini ou personnalisé), buckets
hors bande de tolérance signalés, bouton REÉQUILIBRER qui redimensionne les
positions actions existantes vers la cible (les autres classes restent
manuelles — cf. docstring du module core).
"""
import math

import pygame

from apps.base import DesktopApp
from core import config, i18n
from core import strategic_allocation as SA
from ui import fonts, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr

BUCKET_COLOR = {
    "cash": (120, 130, 140), "equity": config.COL_UP, "bonds": config.COL_CYAN,
    "commodities": config.COL_AMBER, "crypto": (168, 85, 247),
}
CUSTOM_STEP = 0.05


class StrategicAllocApp(DesktopApp):
    title = "Allocation stratégique"
    icon_kind = "portfolio"
    default_size = (1040, 640)
    min_size = (800, 500)

    def on_open(self):
        self.profile_key = "equilibre"
        self.custom_targets = dict(SA.PROFILES["equilibre"]["targets"])
        self._cache_key = None
        self._alloc = None
        self._plan = None
        self._profile_rects = {}
        self._adj_rects = {}
        self._rebal_btn = None
        self._msg = ""

    def _targets(self):
        if self.profile_key == "custom":
            return self.custom_targets
        return SA.PROFILES[self.profile_key]["targets"]

    def _ensure_computed(self):
        market = self.app.ensure_market()
        p = self.app.gs.player
        key = (market.step_count, self.profile_key, tuple(sorted(self.custom_targets.items())))
        if key == self._cache_key:
            return
        self._cache_key = key
        self._alloc = SA.current_allocation(p, market)
        self._plan = SA.rebalance_plan(p, market, self._targets())

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for key, r in self._profile_rects.items():
            if r.collidepoint(pos):
                self.profile_key = key
                self._cache_key = None
                return True
        for key, r in self._adj_rects.items():
            if r.collidepoint(pos):
                bucket, sign = key.split(":")
                step = CUSTOM_STEP if sign == "+" else -CUSTOM_STEP
                self.custom_targets[bucket] = max(0.0, min(1.0,
                    round(self.custom_targets.get(bucket, 0.0) + step, 2)))
                self.profile_key = "custom"
                self._cache_key = None
                return True
        if self._rebal_btn and self._rebal_btn.collidepoint(pos):
            self._do_rebalance()
            return True
        return False

    def _do_rebalance(self):
        market = self.app.ensure_market()
        p = self.app.gs.player
        plan = SA.rebalance_plan(p, market, self._targets())
        results = SA.apply_plan(p, market, plan)
        ok = sum(1 for r in results if r.get("ok"))
        self._msg = _L(f"{ok}/{len(results)} ordre(s) exécuté(s).", f"{ok}/{len(results)} order(s) executed.") if results else \
            _L("Rien à rééquilibrer côté actions.", "Nothing to rebalance on the equity side.")
        self._cache_key = None

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, _L("ALLOCATION STRATÉGIQUE — multi-actifs", "STRATEGIC ALLOCATION — multi-asset"),
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        col_w = (rect.w - 3 * pad) // 2
        left = pygame.Rect(rect.x + pad, rect.y + 34, col_w, rect.h - 34 - pad)
        right = pygame.Rect(left.right + pad, rect.y + 34, col_w, left.h)
        self._draw_donut(surf, left)
        self._draw_targets(surf, right)

    def _draw_donut(self, surf, body):
        inner = widgets.draw_panel(surf, body, _L("Répartition actuelle", "Current allocation"), config.COL_CYAN)
        alloc = self._alloc
        if not alloc or alloc["total"] <= 0:
            widgets.draw_text(surf, _L("Patrimoine nul.", "Zero net worth."), (inner.x, inner.y + 8),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        cx, cy, radius = inner.x + 110, inner.y + 120, 90
        start = -90.0
        for b in SA.BUCKETS:
            pct = alloc["pct"].get(b, 0.0)
            if pct <= 0.0005:
                continue
            sweep = pct * 360.0
            col = BUCKET_COLOR[b]
            pts = [(cx, cy)]
            steps = max(2, int(sweep / 4) + 1)
            for i in range(steps + 1):
                a = math.radians(start + sweep * i / steps)
                pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
            if len(pts) >= 3:
                pygame.draw.polygon(surf, col, pts)
            start += sweep
        pygame.draw.circle(surf, config.COL_BG, (cx, cy), int(radius * 0.55))
        widgets.draw_text(surf, widgets.format_money(alloc["total"], ""),
                          (cx, cy), fonts.small(bold=True), config.COL_TEXT, align="center")
        ly = inner.y
        lx = cx + radius + 30
        targets = self._targets()
        d = SA.drift(alloc, targets)
        for b in SA.BUCKETS:
            col = BUCKET_COLOR[b]
            pygame.draw.rect(surf, col, pygame.Rect(lx, ly + 2, 10, 10))
            pct = alloc["pct"].get(b, 0.0) * 100
            dv = d.get(b, 0.0) * 100
            flag = " ⚠" if abs(d.get(b, 0.0)) > SA.DRIFT_BAND else ""
            txt = _L(f"{SA.BUCKET_LABEL[b]} {pct:.0f}% "
                   f"(cible {targets.get(b, 0) * 100:.0f}%, {dv:+.0f}pp){flag}",
                   f"{SA.BUCKET_LABEL[b]} {pct:.0f}% "
                   f"(target {targets.get(b, 0) * 100:.0f}%, {dv:+.0f}pp){flag}")
            widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.right - lx - 16),
                              (lx + 16, ly), fonts.tiny(bold=bool(flag)),
                              config.COL_AMBER if flag else config.COL_TEXT)
            ly += 20
        if self._msg:
            widgets.draw_text(surf, self._msg, (inner.x, inner.bottom - 16),
                              fonts.tiny(), config.COL_UP)

    def _draw_targets(self, surf, body):
        inner = widgets.draw_panel(surf, body, _L("Cible d'allocation", "Allocation target"), config.COL_AMBER)
        self._profile_rects = {}
        x, y = inner.x, inner.y
        for key in list(SA.PROFILES) + ["custom"]:
            label = SA.PROFILES[key]["label"] if key != "custom" else _L("Personnalisé", "Custom")
            w = fonts.tiny(bold=True).size(label)[0] + 16
            if x + w > inner.right:
                x = inner.x
                y += 24
            r = pygame.Rect(x, y, w, 20)
            self._profile_rects[key] = r
            sel = key == self.profile_key
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        y += 32
        self._adj_rects = {}
        targets = self._targets()
        for b in SA.BUCKETS:
            widgets.draw_text(surf, _L(f"{SA.BUCKET_LABEL[b]} : {targets.get(b, 0) * 100:.0f}%", f"{SA.BUCKET_LABEL[b]}: {targets.get(b, 0) * 100:.0f}%"),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            if self.profile_key == "custom":
                bx = inner.x + 200
                r1 = pygame.Rect(bx, y - 2, 18, 18)
                self._adj_rects[f"{b}:-"] = r1
                pygame.draw.rect(surf, config.COL_PANEL, r1, border_radius=3)
                pygame.draw.rect(surf, config.COL_BORDER, r1, 1, border_radius=3)
                widgets.draw_text(surf, "−", r1.center, fonts.small(bold=True),
                                  config.COL_TEXT, align="center")
                r2 = pygame.Rect(bx + 22, y - 2, 18, 18)
                self._adj_rects[f"{b}:+"] = r2
                pygame.draw.rect(surf, config.COL_PANEL, r2, border_radius=3)
                pygame.draw.rect(surf, config.COL_BORDER, r2, 1, border_radius=3)
                widgets.draw_text(surf, "+", r2.center, fonts.small(bold=True),
                                  config.COL_TEXT, align="center")
            y += 26
        tsum = sum(targets.values())
        if abs(tsum - 1.0) > 0.02:
            widgets.draw_text(surf, _L(f"Somme des cibles : {tsum * 100:.0f}% "
                              "(idéalement 100%)",
                              f"Sum of targets: {tsum * 100:.0f}% "
                              "(ideally 100%)"), (inner.x, y), fonts.tiny(),
                              config.COL_DOWN)
            y += 18
        y += 8
        plan = self._plan or {"trades": [], "notes": []}
        widgets.draw_text(surf, _L(f"{len(plan['trades'])} ordre(s) action(s) prêt(s)", f"{len(plan['trades'])} equity order(s) ready"),
                          (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
        y += 20
        for note in plan.get("notes", [])[:5]:
            widgets.draw_text(surf, widgets.fit_text(note, fonts.tiny(), inner.w),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 15
        _rebal_lbl = _L("RÉÉQUILIBRER (actions)", "REBALANCE (equities)")
        btn_w = fonts.small(bold=True).size(_rebal_lbl)[0] + 20
        self._rebal_btn = pygame.Rect(inner.x, inner.bottom - 32, btn_w, 26)
        active = bool(plan.get("trades"))
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL,
                         self._rebal_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP if active else config.COL_BORDER,
                         self._rebal_btn, 1, border_radius=4)
        widgets.draw_text(surf, _rebal_lbl, self._rebal_btn.center,
                          fonts.small(bold=True),
                          config.COL_UP if active else config.COL_TEXT_DIM, align="center")
