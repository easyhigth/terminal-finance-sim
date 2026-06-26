"""
scene_rivals.py — Salle des rivaux (concurrence vivante).

Affiche le classement joueur + rivaux sous forme de cartes : rang, score, écart
au joueur, voie, et DERNIÈRE ACTION du rival (snipe, percée, débauchage…). Le
rival juste au-dessus du joueur est mis en avant comme « némésis ». Ouvert via
la commande RIVALS ou le rail latéral.
"""
import pygame

from core import config
from core import rivals as R
from core.scene_manager import Scene
from ui import fonts, widgets

_MOOD_COL = {"up": config.COL_UP, "down": config.COL_DOWN, "flat": config.COL_TEXT_DIM}
_TRACK_COL = {
    "M&A": config.COL_UP, "Risk": config.COL_DOWN, "Quant": config.COL_CYAN,
    "Portfolio": config.COL_AMBER, "Advisory": config.COL_PRESTIGE,
}


def _relative_date(player, entry):
    """Date relative lisible (« aujourd'hui », « il y a N j/sem. ») plutôt que
    le « T2 j14 » brut, dur à situer sans faire le calcul soi-même."""
    delta = player.day - entry.get("day", player.day)
    if delta <= 0:
        return "aujourd'hui"
    if delta == 1:
        return "hier"
    if delta < 14:
        return f"il y a {delta} j"
    return f"il y a {delta // 7} sem."


class RivalsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        board = R.leaderboard(p, self.market)
        rank, total = R.player_rank(p, self.market)
        nem = R.nemesis(p, self.market)
        pscore = R.player_score(p, self.market)

        widgets.draw_text(surf, "RIVAUX", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        sub = f"Rang {rank} / {total}"
        if nem:
            gap = nem["score"] - pscore
            sub += f"   ·   némésis : {nem['name']} (+{widgets.format_money(gap, cur)} devant)"
        else:
            sub += "   ·   vous dominez le classement"
        widgets.draw_text(surf, sub, (42, 72), fonts.small(), config.COL_TEXT_DIM)

        # cartes : une par acteur, triées par score (déjà fait par leaderboard)
        top = 110
        ch, gap = 92, 10
        log_h = 150  # réserve l'espace du journal d'activité en bas d'écran
        avail = config.footer_y() - 12 - top - log_h
        per_col = max(1, avail // (ch + gap))
        n_cols = max(1, -(-len(board) // per_col))  # ceil
        colw = (config.SCREEN_WIDTH - (n_cols + 1) * config.MARGIN) // n_cols
        for i, row in enumerate(board):
            col = i // per_col
            r_in_col = i % per_col
            x = config.MARGIN + col * (colw + config.MARGIN)
            y = top + r_in_col * (ch + gap)
            self._draw_card(surf, pygame.Rect(x, y, colw, ch), row, p, pscore, nem, cur)

        cards_bottom = top + min(per_col, len(board)) * (ch + gap)
        log_top = max(cards_bottom + 6, config.footer_y() - 12 - log_h)
        log_rect = pygame.Rect(config.MARGIN, log_top,
                               config.SCREEN_WIDTH - 2 * config.MARGIN,
                               config.footer_y() - 8 - log_top)
        self._draw_activity_log(surf, log_rect, p)

        self.back_btn.draw(surf)

    def _draw_activity_log(self, surf, rect, player):
        """Journal d'activité des rivaux : dernières actions visibles (percées,
        sniping de deals, débauchage de mandats, appropriation de cibles M&A)
        tirées du journal de carrière + du journal court `rival_events`."""
        col_left = pygame.Rect(rect.x, rect.y, int(rect.w * 0.62), rect.h)
        col_right = pygame.Rect(col_left.right + 10, rect.y, rect.right - col_left.right - 10, rect.h)

        inner = widgets.draw_panel(surf, col_left, "Journal d'activité des rivaux", config.COL_DOWN)
        log_events = R.recent_activity(player, limit=max(1, inner.h // 16))
        if not log_events:
            widgets.draw_text(surf, "Aucune activité rivale récente. Avancez le temps (ADV) pour en générer.",
                              (inner.x, inner.y + 2), fonts.tiny(), config.COL_TEXT_DIM)
        else:
            y = inner.y
            row_h = max(16, inner.h // len(log_events))
            for entry in log_events:
                kind = entry.get("kind", "info")
                ecol = config.COL_WARN if kind in ("deal", "crisis") else config.COL_TEXT_DIM
                label = f"{_relative_date(player, entry)} — {entry.get('text', '')}"
                widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), inner.w),
                                  (inner.x, y), fonts.tiny(), ecol)
                y += row_h

        inner2 = widgets.draw_panel(surf, col_right, "Coups récents", config.COL_AMBER)
        max_recent = max(1, inner2.h // 16)
        recent = list(reversed(getattr(player, "rival_events", None) or []))[:max_recent]
        if not recent:
            widgets.draw_text_wrapped(surf, "Rien à signaler pour l'instant. Les rivaux agissent "
                                      "en avançant le temps (ADV) : sniping de deals, débauchage "
                                      "de mandats, percées en cours.",
                              (inner2.x, inner2.y + 2), fonts.tiny(), config.COL_TEXT_DIM, inner2.w)
            return
        y = inner2.y
        row_h = max(16, inner2.h // len(recent))
        for entry in recent:
            kind = entry.get("kind", "info")
            ecol = config.COL_DOWN if kind == "bad" else config.COL_TEXT_DIM
            label = f"{_relative_date(player, entry)} — {entry.get('text', '')}"
            widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), inner2.w),
                              (inner2.x, y), fonts.tiny(), ecol)
            y += row_h

    def _draw_card(self, surf, rect, row, player, pscore, nem, cur):
        is_player = row["is_player"]
        is_nem = nem is not None and not is_player and row["name"] == nem["name"]
        # données du rival (action/humeur) si ce n'est pas le joueur
        rdata = None
        if not is_player:
            rdata = next((r for r in player.rivals if r["name"] == row["name"]), None)

        accent = config.COL_AMBER if is_player else (config.COL_DOWN if is_nem else config.COL_BORDER)
        bg = config.COL_PANEL_HEAD if (is_player or is_nem) else config.COL_PANEL
        pygame.draw.rect(surf, bg, rect, border_radius=6)
        pygame.draw.rect(surf, accent, rect, 2 if (is_player or is_nem) else 1, border_radius=6)
        pygame.draw.rect(surf, accent, (rect.x, rect.y, 4, rect.h),
                         border_top_left_radius=6, border_bottom_left_radius=6)

        # rang
        widgets.draw_text(surf, f"#{row['rank']}", (rect.x + 16, rect.y + 12),
                          fonts.head(bold=True), accent if not is_player else config.COL_AMBER)
        # nom + firme
        name = row["name"]
        widgets.draw_text(surf, widgets.fit_text(name, fonts.body(bold=True), rect.w - 230),
                          (rect.x + 70, rect.y + 10), fonts.body(bold=True),
                          config.COL_WHITE if not is_player else config.COL_AMBER)
        firm = row["firm"]
        widgets.draw_text(surf, widgets.fit_text(firm, fonts.tiny(), rect.w - 230),
                          (rect.x + 70, rect.y + 34), fonts.tiny(), config.COL_TEXT_DIM)

        # voie (badge) + dernière action
        if rdata:
            tcol = _TRACK_COL.get(rdata.get("track"), config.COL_TEXT_DIM)
            widgets.draw_badge(surf, rdata.get("track", "?"), (rect.x + 70, rect.y + 54), tcol)
            mood = _MOOD_COL.get(rdata.get("mood", "flat"), config.COL_TEXT_DIM)
            act = "▸ " + rdata.get("last", "—")
            widgets.draw_text(surf, widgets.fit_text(act, fonts.small(), rect.w - 240),
                              (rect.x + 160, rect.y + 56), fonts.small(), mood)
        else:
            widgets.draw_badge(surf, "VOUS", (rect.x + 70, rect.y + 54), config.COL_AMBER)

        # score + écart au joueur
        widgets.draw_text(surf, widgets.format_money(row["score"], cur),
                          (rect.right - 16, rect.y + 14), fonts.body(bold=True),
                          config.COL_WHITE, align="right")
        if not is_player:
            delta = row["score"] - pscore
            dcol = config.COL_DOWN if delta > 0 else config.COL_UP
            sign = "+" if delta > 0 else ""
            widgets.draw_text(surf, f"{sign}{widgets.format_money(delta, cur)} vs vous",
                              (rect.right - 16, rect.y + 40), fonts.tiny(), dcol, align="right")
            if is_nem:
                widgets.draw_text(surf, "NÉMÉSIS", (rect.right - 16, rect.y + 62),
                                  fonts.tiny(bold=True), config.COL_DOWN, align="right")
