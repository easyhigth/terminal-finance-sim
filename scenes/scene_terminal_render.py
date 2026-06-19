"""
scene_terminal_render.py — Rendu du terminal (TerminalRenderMixin).
Extrait de scene_terminal.py pour limiter sa taille ; mixé dans TerminalScene.
"""
import pygame

from core import career as career_mod
from core import config
from core import inbox as inbox_mod
from core import onboarding as onboarding_mod
from core import portfolio as pf_mod
from core import unlocks as unlocks_mod
from core.i18n import get_lang
from core.i18n import t as _t
from ui import fonts, widgets


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr


class TerminalRenderMixin:
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        info = config.CONTINENTS[p.continent]
        accent = info["color"]

        self._draw_topbar(surf, p, info, accent)
        self._draw_ticker(surf)

        M = config.MARGIN
        top = config.TOPBAR_H + config.TICKER_H + M
        onb_step = onboarding_mod.active_step(p)
        onb_h = 40 if onb_step else 0
        if onb_step:
            self._draw_onboarding_banner(
                surf, pygame.Rect(M, top, config.SCREEN_WIDTH - 2 * M, onb_h - M), p, onb_step)
            top += onb_h
        else:
            self._onboarding_skip_rect = None
        console_h = self._console_height()
        bottom = config.SCREEN_HEIGHT - console_h - M     # bas de la zone de contenu
        avail_h = bottom - top

        # --- rail latéral (commandes cliquables) ---
        self._draw_rail(surf, pygame.Rect(M, top, self.rail_w, avail_h), p)

        # --- 3 colonnes à droite du rail ---
        gx = M + self.rail_w + M
        col_l_w = 280
        col_r_w = 320
        cx = gx + col_l_w + M
        cw = config.SCREEN_WIDTH - M - col_r_w - M - cx
        rx = config.SCREEN_WIDTH - M - col_r_w

        gap = M
        half = (avail_h - gap) // 2

        # colonne gauche : indices / santé
        self._draw_indices(surf, pygame.Rect(gx, top, col_l_w, half))
        self._draw_health(surf, pygame.Rect(gx, top + half + gap, col_l_w, avail_h - half - gap), p, info)

        # centre : carte (haut) + flux (bas)
        map_h = int(avail_h * 0.62)
        self._map_rect = pygame.Rect(cx, top, cw, map_h)
        self.worldmap.draw(surf, self._map_rect, self.market)
        self._draw_feed(surf, pygame.Rect(cx, top + map_h + gap, cw, avail_h - map_h - gap), info)

        # colonne droite : top sociétés (haut) / priorités (bas)
        self._draw_top_companies(surf, pygame.Rect(rx, top, col_r_w, half), p)
        self._draw_career(surf, pygame.Rect(rx, top + half + gap, col_r_w, avail_h - half - gap), p)

        self._draw_console(surf)

        # overlay : fenêtres de données déplaçables
        for w in self.datawins:
            w.draw(surf)

        # overlay : panneau de triche (mode test uniquement)
        if self.cheat_panel is not None:
            self.cheat_panel.draw(surf)

        # overlay : panneau des raccourcis clavier
        if self.shortcuts_panel is not None:
            self.shortcuts_panel.draw(surf)

    def _draw_onboarding_banner(self, surf, rect, p, step):
        n = len(onboarding_mod.STEPS)
        idx = p.onboarding_step + 1
        pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, rect, 1, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, (rect.x, rect.y, 3, rect.h))
        skip = pygame.Rect(rect.right - 90, rect.y + (rect.h - 22) // 2, 80, 22)
        self._onboarding_skip_rect = skip
        title = f"PARCOURS — Étape {idx}/{n} : {step['title']}"
        widgets.draw_text(surf, title, (rect.x + 12, rect.y + 4), fonts.tiny(bold=True), config.COL_CYAN)
        widgets.draw_text(surf, widgets.fit_text(step["hint"], fonts.tiny(), rect.w - 220),
                          (rect.x + 12, rect.y + 20), fonts.tiny(), config.COL_TEXT_DIM)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, skip, border_radius=3)
        pygame.draw.rect(surf, config.COL_BORDER, skip, 1, border_radius=3)
        widgets.draw_text(surf, "✕ Passer", skip.center, fonts.tiny(bold=True),
                          config.COL_TEXT_DIM, align="center")

    def _draw_rail(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _t("term.commands"), config.COL_AMBER)
        self._rail_rects = {}
        gap = 4
        n_headers = sum(1 for label, _ in self.rail if label is None)
        n_buttons = max(1, len(self.rail) - n_headers)
        hh = 16  # hauteur d'un en-tête de section
        # pas adaptatif borné à la hauteur du panneau (jamais de débordement vers le bas)
        avail = inner.h - n_headers * (hh + gap) - gap * (n_buttons - 1)
        bh = max(13, min(24, avail // n_buttons))
        y = inner.y
        mp = pygame.mouse.get_pos()
        for label, cmd in self.rail:
            if label is None:
                widgets.draw_text(surf, cmd, (inner.x + 2, y + 2), fonts.tiny(bold=True),
                                  config.COL_TEXT_DIM)
                y += hh + gap
                continue
            br = pygame.Rect(inner.x, y, inner.w, bh)
            self._rail_rects[label] = br
            hover = br.collidepoint(mp)
            locked = not unlocks_mod.cmd_unlocked(p, cmd)
            # accent spécial pour quelques entrées
            acc = config.COL_AMBER
            if locked:
                acc = config.COL_BORDER
            elif cmd == "ADV":
                acc = config.COL_UP
            elif cmd == "INBOX" and inbox_mod.unread_count(p):
                acc = config.COL_CYAN
            elif cmd == "DECIDE" and p.pending_dilemmas:
                acc = config.COL_WARN
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (hover and not locked) else config.COL_PANEL,
                             br, border_radius=4)
            pygame.draw.rect(surf, acc, br, 1, border_radius=4)
            ty = br.y + (bh - fonts.small().get_height()) // 2
            if locked:
                g = unlocks_mod.required_grade(unlocks_mod.CMD_FEATURE[cmd])
                widgets.draw_text(surf, widgets.fit_text(f"⊘ {label}", fonts.small(), br.w - 36),
                                  (br.x + 8, ty),
                                  fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"G{g}", (br.right - 8, ty),
                                  fonts.tiny(), config.COL_TEXT_DIM, align="right")
            else:
                txt = _t("rail." + cmd)
                if cmd == "INBOX":
                    u = inbox_mod.unread_count(p)
                    if u:
                        txt = f"{txt} ({u})"
                elif cmd == "DECIDE" and p.pending_dilemmas:
                    txt = f"{txt} !"
                widgets.draw_text(surf, widgets.fit_text(txt, fonts.small(bold=hover), br.w - 16),
                                  (br.x + 10, ty),
                                  fonts.small(bold=hover), acc if hover else config.COL_TEXT)
            y += bh + gap

    def _draw_topbar(self, surf, p, info, accent):
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, (0, 0, config.SCREEN_WIDTH, config.TOPBAR_H))
        pygame.draw.line(surf, accent, (0, config.TOPBAR_H), (config.SCREEN_WIDTH, config.TOPBAR_H), 1)
        y = 12
        r = widgets.draw_text(surf, "TERMINAL", (12, 8), fonts.head(bold=True), config.COL_AMBER)
        x = r.right + 16
        # grade (tronqué si trop long pour ne jamais cacher les éléments suivants)
        max_grade_w = 200
        r = widgets.draw_text(surf, "GRADE  ", (x, y), fonts.small(), config.COL_TEXT_DIM)
        r = widgets.draw_text_fit(surf, p.grade, (r.right, y), fonts.small(bold=True),
                                  config.COL_WHITE, max_width=max_grade_w)
        x = r.right + 18
        # cash
        cash_col = config.COL_UP if p.cash >= 0 else config.COL_DOWN
        r = widgets.draw_text(surf, "CASH ", (x, y), fonts.small(), config.COL_TEXT_DIM)
        r = widgets.draw_text(surf, widgets.format_money(p.cash, info["currency"]),
                              (r.right, y), fonts.small(bold=True), cash_col)
        x = r.right + 18
        # reputation
        r = widgets.draw_text(surf, "REP  ", (x, y), fonts.small(), config.COL_TEXT_DIM)
        r = widgets.draw_text(surf, f"{p.reputation}/100", (r.right, y), fonts.small(bold=True),
                              config.COL_WHITE)
        x = r.right + 18
        # day
        widgets.draw_text(surf, "DAY  ", (x, y), fonts.small(), config.COL_TEXT_DIM)
        r = widgets.draw_text(surf, f"{p.day} (T{p.quarter})",
                              (x + fonts.small().size("DAY  ")[0], y), fonts.small(bold=True),
                              config.COL_WHITE)
        x = r.right + 18
        # levier / marge — toujours visible, pour anticiper un margin call
        st = pf_mod.margin_status(p, self.market)
        r = widgets.draw_text(surf, "LEV  ", (x, y), fonts.small(), config.COL_TEXT_DIM)
        lev = st["leverage"]
        lev_txt = f"{lev:.2f}x" if lev != float("inf") else "∞"
        lev_col = config.COL_DOWN if st["margin_call"] else (
            config.COL_WARN if lev >= 0.85 * st["max_leverage"] else config.COL_UP)
        r = widgets.draw_text(surf, lev_txt, (r.right, y), fonts.small(bold=True), lev_col)
        if st["margin_call"]:
            widgets.draw_badge(surf, "⚠ MARGIN CALL", (r.right + 10, y - 2), config.COL_DOWN)
        x = r.right + 18
        # devise
        r = widgets.draw_text(surf, f"{info['currency']}", (x, y), fonts.body(bold=True), accent)
        x = r.right + 14
        # badge messagerie (non-lus)
        unread = inbox_mod.unread_count(p)
        if unread:
            r = widgets.draw_badge(surf, f"@ {unread}", (x, y - 2), config.COL_CYAN)
            x = r.right + 14
        # bouton triche (mode test uniquement, jamais en jeu normal)
        self._cheat_btn_rect = None
        if getattr(self.app, "cheats", False):
            btn = pygame.Rect(x, 6, 96, 22)
            hover = btn.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL,
                             btn, border_radius=4)
            pygame.draw.rect(surf, config.COL_DOWN, btn, 1, border_radius=4)
            widgets.draw_text(surf, "🛠 CHEAT", btn.center, fonts.tiny(bold=True),
                              config.COL_DOWN, align="center")
            self._cheat_btn_rect = btn
        # bouton raccourcis clavier (toujours visible, coin haut-droit de la scène)
        sw, sh = 168, 26
        sbtn = pygame.Rect(config.SCREEN_WIDTH - 10 - sw, 4, sw, sh)
        hover = sbtn.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL,
                         sbtn, border_radius=5)
        pygame.draw.rect(surf, config.COL_CYAN, sbtn, 1, border_radius=5)
        widgets.draw_text(surf, "⌨ RACCOURCIS", sbtn.center, fonts.small(bold=True),
                          config.COL_CYAN, align="center")
        self._shortcuts_btn_rect = sbtn

    def _draw_ticker(self, surf):
        y = config.TOPBAR_H + 4
        pygame.draw.rect(surf, (12, 14, 20), (0, y, config.SCREEN_WIDTH, config.TICKER_H))
        parts = []
        for name, *_ in self.market.index_defs:
            v = self.market.index_value(name)
            chg = self.market.index_change_pct(name)
            sign = "+" if chg >= 0 else ""
            parts.append(f"{name} {v:,.0f} {sign}{chg:.2f}%")
        line = "    •    ".join(parts) + "    •    "
        offset = int(self.t * 50) % max(1, fonts.small().size(line)[0])
        widgets.draw_text(surf, line + line, (10 - offset, y + 3),
                          fonts.small(), config.COL_AMBER_DIM)

    def _draw_indices(self, surf, rect):
        inner = widgets.draw_panel(surf, rect,
                                   f'{_t("term.indices")} · {self.market.regime_label()}', config.COL_AMBER)
        self._indices_header_rect = pygame.Rect(rect.x, rect.y, rect.w, 26)
        self._indices_panel_rect = rect
        self._index_rects = {}
        defs = self.market.index_defs
        step = 50
        spark_h = max(8, step - 20)
        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(inner)
        y = inner.y - self._indices_scroll
        for name, *_ in defs:
            visible = (inner.top - step) < y < inner.bottom
            if visible:
                v = self.market.index_value(name)
                chg = self.market.index_change_pct(name)
                col = config.COL_UP if chg >= 0 else config.COL_DOWN
                row = pygame.Rect(inner.x - 4, y - 1, inner.w + 8, step - 2)
                self._index_rects[name] = row
                if row.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
                widgets.draw_text(surf, name, (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
                widgets.draw_text(surf, f"{v:,.0f}", (inner.x + 96, y), fonts.small(), config.COL_WHITE)
                widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}%", (inner.right, y),
                                  fonts.small(bold=True), col, align="right")
                widgets.draw_series(surf, pygame.Rect(inner.x, y + 16, inner.w, spark_h),
                                    self.market.index_history(name), col, baseline=False)
            y += step
        surf.set_clip(prev_clip)
        content_h = (y + self._indices_scroll) - inner.y
        self._indices_max_scroll = max(0, content_h - inner.h)
        self._indices_scroll = min(self._indices_scroll, self._indices_max_scroll)
        if self._indices_max_scroll > 0:
            track = pygame.Rect(rect.right - 6, inner.y, 4, inner.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=2)
            frac = inner.h / (content_h or 1)
            bar_h = max(16, int(inner.h * frac))
            bar_y = inner.y + int((inner.h - bar_h) * (self._indices_scroll / self._indices_max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 4, bar_h), border_radius=2)

    def _draw_health(self, surf, rect, p, info):
        self._health_rect = pygame.Rect(rect)     # cliquable → analyse détaillée (BOOK)
        title = _t("term.health") + (" ▸" if rect.collidepoint(pygame.mouse.get_pos()) else "")
        inner = widgets.draw_panel(surf, rect, title, config.COL_AMBER)
        cur = info["currency"]
        pos_val = pf_mod.positions_value(p, self.market)
        nw = pf_mod.net_worth(p, self.market)
        upnl = pf_mod.unrealized_pnl(p, self.market)
        nw_col = config.COL_UP if nw >= 0 else config.COL_DOWN
        widgets.draw_text(surf, _t("term.networth"), (inner.x, inner.y), fonts.small(bold=True), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.format_money(nw, cur), (inner.x, inner.y + 18),
                          fonts.head(bold=True), nw_col)
        # cash + positions + P&L latent sur une ligne
        widgets.draw_text(surf, f"Cash {widgets.format_money(p.cash, cur)}  ·  "
                                f"Titres {widgets.format_money(pos_val, cur)}",
                          (inner.x, inner.y + 46), fonts.tiny(), config.COL_TEXT)
        if p.portfolio:
            pcol = config.COL_UP if upnl >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"P&L latent {'+' if upnl>=0 else ''}{widgets.format_money(upnl, cur)}",
                              (inner.x, inner.y + 62), fonts.tiny(), pcol)
        self.networth_spark.draw(surf, pygame.Rect(inner.x, inner.y + 80, inner.w, 40))
        widgets.draw_text(surf, f"Réputation {p.reputation}/100", (inner.x, inner.y + 126),
                          fonts.small(), config.COL_TEXT_DIM)
        rep_col = config.COL_UP if p.reputation >= 50 else (config.COL_DOWN if p.reputation < 25 else config.COL_WARN)
        widgets.draw_progress(surf, (inner.x, inner.y + 146, inner.w, 9), p.reputation / 100.0, rep_col)
        hot = p.flags.get("hot_sector")
        if hot:
            widgets.draw_text(surf, f"Secteur du trimestre : {hot}", (inner.x, inner.y + 162),
                              fonts.tiny(bold=True), config.COL_PRESTIGE)
        else:
            widgets.draw_text(surf, "PORTFOLIO · BUY/SELL · RESEARCH",
                              (inner.x, inner.y + 162), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_feed(self, surf, rect, info):
        inner = widgets.draw_panel(surf, rect, _t("term.feed"), config.COL_CYAN)
        self._feed_header_rect = pygame.Rect(rect.x, rect.y, rect.w, 26)
        y = inner.y
        cur = info["currency"]
        for e in self.recent_events[:3]:
            col = {"good": config.COL_EVENT_GOOD, "bad": config.COL_EVENT_BAD,
                   "info": config.COL_EVENT_INFO}.get(e["kind"], config.COL_EVENT_INFO)
            tag = {"good": "↑", "bad": "↓", "info": "•"}.get(e["kind"], "•")
            widgets.draw_text(surf, tag, (inner.x, y), fonts.body(bold=True), col)
            label = e["title"] + (f"  {widgets.format_money(e['cash'], cur)}" if e.get("cash") else "")
            h = widgets.draw_text_wrapped(surf, label, (inner.x + 20, y), fonts.small(), col, inner.w - 24)
            y += h + 6
            if y > inner.bottom - 20:
                return
        for item in self.news[:max(0, 3 - len(self.recent_events))]:
            widgets.draw_text(surf, "▸", (inner.x, y), fonts.small(), config.COL_CYAN)
            h = widgets.draw_text_wrapped(surf, item, (inner.x + 20, y), fonts.small(), config.COL_TEXT, inner.w - 24)
            y += h + 6
            if y > inner.bottom - 20:
                return
        widgets.draw_text(surf, "clic titre → historique complet",
                          (inner.x, inner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_top_companies(self, surf, rect, p):
        watch = [tk for tk in p.watchlist if self.market.price_of(tk) is not None]
        title = f'{_t("term.topco")} ({len(watch)} suivies)' if watch else f'{_t("term.topco")} — {p.continent}'
        inner = widgets.draw_panel(surf, rect, title, config.COL_CYAN)
        self._topco_header_rect = pygame.Rect(rect.x, rect.y, rect.w, 26)
        self._topco_panel_rect = rect
        cur = config.CONTINENTS[p.continent]["currency"]
        self._topco_rects = {}
        mp = pygame.mouse.get_pos()
        list_area = pygame.Rect(inner.x, inner.y, inner.w, inner.h - 16)
        row_h = 28
        n = max(len(watch), 20) if watch else 20
        if watch:
            companies = []
            for tk in watch[:n]:
                mt = self.market.metrics(tk)
                if mt:
                    companies.append({"ticker": tk, "name": mt["name"], "mktcap": mt["mktcap"]})
        else:
            companies = self.market.top_companies(region=p.continent, n=n)
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y - self._topco_scroll
        for c in companies:
            visible = (list_area.top - row_h) < y < list_area.bottom
            if visible:
                row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 26)
                self._topco_rects[c["ticker"]] = row
                if row.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
                widgets.draw_text(surf, c["ticker"], (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, c["name"][:16], (inner.x + 58, y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, widgets.format_money(c["mktcap"] * 1e6, cur), (inner.right, y),
                                  fonts.tiny(bold=True), config.COL_WHITE, align="right")
            y += row_h
        surf.set_clip(prev_clip)
        content_h = (y + self._topco_scroll) - inner.y
        self._topco_max_scroll = max(0, content_h - list_area.h)
        self._topco_scroll = min(self._topco_scroll, self._topco_max_scroll)
        if self._topco_max_scroll > 0:
            track = pygame.Rect(rect.right - 6, list_area.y, 4, list_area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=2)
            frac = list_area.h / (content_h or 1)
            bar_h = max(16, int(list_area.h * frac))
            bar_y = list_area.y + int((list_area.h - bar_h) * (self._topco_scroll / self._topco_max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 4, bar_h), border_radius=2)
        widgets.draw_text(surf, "clic titre → explorateur · clic ligne → fiche",
                          (inner.x, inner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_career(self, surf, rect, p):
        """Panneau CARRIÈRE (ex-PRIORITÉS) : prochain objectif, promotion, risque,
        opportunité. Cliquable : ouvre la scène carrière."""
        # couleur de priorité du panneau selon le danger le plus pressant
        marge0 = p.cash - config.BANKRUPTCY_CASH
        prio = None
        if p.reputation < 20 or marge0 < 120000 or p.heat >= 55:
            prio = config.COL_PRIO_CRITICAL
        elif p.pending_dilemmas or any(d["days_left"] <= config.DAYS_PER_STEP * 2 for d in p.deals):
            prio = config.COL_PRIO_URGENT
        self._career_panel_rect = pygame.Rect(rect.x, rect.y, rect.w, 26)
        hover = self._career_panel_rect.collidepoint(pygame.mouse.get_pos())
        inner = widgets.draw_panel(surf, rect, _t("term.career"),
                                   config.COL_CYAN if hover else config.COL_AMBER, prio=prio)
        self._career_content_rect = inner
        prev_clip = surf.get_clip()
        surf.set_clip(inner)
        y = inner.y - self._career_scroll
        # 1) prochain objectif non atteint
        widgets.draw_text(surf, "OBJECTIF", (inner.x, y), fonts.tiny(bold=True), config.COL_CYAN)
        y += 18
        nxt = None
        for o in p.objectives:
            _, _, ok = career_mod.objective_progress(p, o)
            if not ok:
                nxt = o
                break
        if nxt:
            wrapped_h = widgets.draw_text_wrapped(surf, career_mod.objective_label(p, nxt), (inner.x, y),
                                                  fonts.small(), config.COL_TEXT, inner.w)
        else:
            widgets.draw_text(surf, "Tous les objectifs atteints ✓", (inner.x, y),
                              fonts.small(), config.COL_UP)
            wrapped_h = fonts.small().get_height()
        y += max(44, wrapped_h + 10)
        # 2) promotion
        widgets.draw_text(surf, "PROMOTION", (inner.x, y), fonts.tiny(bold=True), config.COL_CYAN)
        y += 18
        if p.can_promote():
            if career_mod.promotion_ready(p):
                widgets.draw_text(surf, "Prêt — tapez EVAL", (inner.x, y),
                                  fonts.small(bold=True), config.COL_UP)
            else:
                miss = career_mod.missing_criteria(p)
                widgets.draw_text(surf, "Manque : " + ", ".join(miss)[:34], (inner.x, y),
                                  fonts.tiny(), config.COL_WARN)
        else:
            widgets.draw_text(surf, "Grade maximal", (inner.x, y), fonts.small(), config.COL_TEXT_DIM)
        y += 34
        # 3) risque
        widgets.draw_text(surf, "RISQUE", (inner.x, y), fonts.tiny(bold=True), config.COL_CYAN)
        y += 18
        cur = config.CONTINENTS[p.continent]["currency"]
        marge = p.cash - config.BANKRUPTCY_CASH
        risk_col = config.COL_UP if (p.reputation >= 35 and marge > 300000) else config.COL_WARN
        if p.reputation < 20 or marge < 120000:
            risk_col = config.COL_DOWN
        widgets.draw_text(surf, f"Marge faillite {widgets.format_money(marge, cur)}",
                          (inner.x, y), fonts.tiny(), risk_col)
        scrut_col = config.COL_DOWN if p.heat >= 55 else (config.COL_WARN if p.heat >= 30 else config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"Scrutin réglementaire {p.heat}/100", (inner.x, y + 16),
                          fonts.tiny(), scrut_col)
        y += 40
        # 4) opportunité (deal le plus urgent)
        widgets.draw_text(surf, "OPPORTUNITÉ", (inner.x, y), fonts.tiny(bold=True), config.COL_CYAN)
        y += 18
        if p.deals:
            d = min(p.deals, key=lambda d: d["days_left"])
            acc = config.COL_DEAL_URGENT if d["days_left"] <= config.DAYS_PER_STEP * 2 else config.COL_DEAL
            widgets.draw_text(surf, f"#{d['id']} {d['title'][:22]}", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"échéance {d['days_left']}j · DEAL {d['id']}",
                              (inner.x, y + 16), fonts.tiny(), acc)
        else:
            widgets.draw_text(surf, "Aucun deal — ADV pour en générer.", (inner.x, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
        y += 36
        # prochain déblocage
        nxt = unlocks_mod.next_unlock(p)
        if nxt:
            widgets.draw_text(surf, "PROCHAIN DÉBLOCAGE", (inner.x, y),
                              fonts.tiny(bold=True), config.COL_CYAN)
            widgets.draw_text_wrapped(surf, f"{nxt[0]} — grade {config.GRADES[nxt[1]]}",
                                      (inner.x, y + 16), fonts.tiny(), config.COL_PRESTIGE, inner.w)
        y += 36
        surf.set_clip(prev_clip)
        content_h = (y + self._career_scroll) - inner.y
        self._career_max_scroll = max(0, content_h - inner.h)
        self._career_scroll = min(self._career_scroll, self._career_max_scroll)
        if self._career_max_scroll > 0:
            track = pygame.Rect(rect.right - 6, inner.y, 4, inner.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=2)
            frac = inner.h / (content_h or 1)
            bar_h = max(16, int(inner.h * frac))
            bar_y = inner.y + int((inner.h - bar_h) * (self._career_scroll / self._career_max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 4, bar_h), border_radius=2)

    CONSOLE_LINE_H = 16

    def _console_visible_lines(self):
        return 13 if self.console_expanded else 4

    def _console_height(self):
        # lignes visibles + bandeau (en-tête) + ligne de saisie
        return self._console_visible_lines() * self.CONSOLE_LINE_H + 40

    def _console_rect(self):
        h = self._console_height()
        return pygame.Rect(config.MARGIN, config.SCREEN_HEIGHT - h - config.MARGIN,
                           config.SCREEN_WIDTH - 2 * config.MARGIN, h)

    def _console_max_scroll(self):
        return max(0, len(self.cmd_history) - self._console_visible_lines())

    def _scroll_console(self, delta):
        self.console_scroll = max(0, min(self._console_max_scroll(),
                                         self.console_scroll + delta))

    def _draw_console(self, surf):
        rect = self._console_rect()
        pygame.draw.rect(surf, (6, 8, 12), rect)
        pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
        self._console_btns = {}

        # bandeau : titre + position de défilement + boutons (scroll / agrandir)
        head_y = rect.y + 4
        nvis = self._console_visible_lines()
        total = len(self.cmd_history)
        widgets.draw_text(surf, "CONSOLE", (rect.x + 10, head_y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        if self.console_scroll > 0:
            widgets.draw_text(surf, f"▲ historique +{self.console_scroll}",
                              (rect.x + 90, head_y), fonts.tiny(), config.COL_WARN)
        # boutons à droite : [▲][▼][AGRANDIR/RÉDUIRE]
        bx = rect.right - 10
        exp_label = "RÉDUIRE" if self.console_expanded else "AGRANDIR"
        ew = fonts.tiny(bold=True).size(exp_label)[0] + 16
        exp_rect = pygame.Rect(bx - ew, head_y - 2, ew, 16); bx = exp_rect.x - 6
        for key, rr, lab in (("expand", exp_rect, exp_label),):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, rr)
            pygame.draw.rect(surf, config.COL_AMBER, rr, 1)
            widgets.draw_text(surf, lab, rr.center, fonts.tiny(bold=True),
                              config.COL_AMBER, align="center")
            self._console_btns[key] = rr
        for key, sym in (("down", "▼"), ("up", "▲")):
            rr = pygame.Rect(bx - 18, head_y - 2, 16, 16); bx = rr.x - 4
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, rr)
            pygame.draw.rect(surf, config.COL_BORDER, rr, 1)
            widgets.draw_text(surf, sym, rr.center, fonts.tiny(bold=True),
                              config.COL_TEXT, align="center")
            self._console_btns[key] = rr

        # lignes : fenêtre [start:start+nvis] selon le défilement (0 = bas)
        start = max(0, total - nvis - self.console_scroll)
        window = self.cmd_history[start:start + nvis]
        y = rect.y + 22
        for line in window:
            col = config.COL_AMBER if line.startswith(">") else config.COL_AMBER_DIM
            widgets.draw_text(surf, widgets.fit_text(line, fonts.small(), rect.w - 24),
                              (rect.x + 10, y), fonts.small(), col)
            y += self.CONSOLE_LINE_H

        # ligne de saisie (toujours en bas)
        cursor = "_" if int(self.t * 2) % 2 == 0 else " "
        r = widgets.draw_text(surf, f"CMD> {self.cmd}", (rect.x + 10, rect.bottom - 20),
                              fonts.small(bold=True), config.COL_AMBER)
        ghost = self._ghost()
        gx = r.right
        if ghost:
            gr = widgets.draw_text(surf, ghost, (gx, rect.bottom - 20), fonts.small(bold=True),
                                   config.COL_TEXT_DIM)
            widgets.draw_text(surf, "  ⇥", (gr.right, rect.bottom - 20), fonts.tiny(),
                              config.COL_TEXT_DIM)
            gx = gr.right
        widgets.draw_text(surf, cursor, (r.right if not ghost else gx, rect.bottom - 20),
                          fonts.small(bold=True), config.COL_AMBER)
