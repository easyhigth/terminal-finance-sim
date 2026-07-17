"""
app_clients.py — Application « Carnet clients » du bureau.

La mémoire RELATIONNELLE des mandats (core/clients.py) : chaque client
récurrent avec sa jauge de confiance, le capital qu'il est prêt à confier
(multiplicateur), son historique réussites/échecs, qui l'a référé, et les
clients PERDUS (grisés — deux échecs et ils ne reviennent jamais). S'ouvre
depuis l'icône Carrière ou les notifications de référencement/perte.
"""
import pygame

from apps.base import DesktopApp
from core import clients as clients_mod
from core import config
from core.i18n import get_lang
from ui import fonts, widgets

ROW_H = 58


def _L(fr, en):
    return en if get_lang() == "en" else fr


def _trust_color(trust):
    if trust >= 70:
        return config.COL_UP
    if trust >= 35:
        return config.COL_WARN
    return config.COL_DOWN


class ClientsApp(DesktopApp):
    title = "Carnet clients"
    icon_kind = "review"
    default_size = (560, 460)
    min_size = (420, 280)

    def on_open(self):
        self.scroll = 0
        self._list_rect = None

    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -ROW_H if event.button == 4 else ROW_H
            self.scroll = max(0, self.scroll + delta)
            return True
        return False

    def draw(self, surf, rect):
        pygame.draw.rect(surf, config.COL_BG, rect)
        p = self.app.gs.player
        clients_mod._ensure_field(p)
        inner = widgets.draw_panel(
            surf, rect.inflate(-16, -16),
            _L("Carnet clients", "Client book"), config.COL_CYAN)
        book = list(p.clients)
        if not book:
            widgets.draw_text_wrapped(
                surf,
                _L("Votre carnet est vide : il s'ouvrira avec votre premier "
                   "mandat client (grade Associate). Chaque mandat réussi fait "
                   "grandir la confiance — et la confiance amène capital et "
                   "recommandations.",
                   "Your book is empty: it opens with your first client mandate "
                   "(Associate grade). Every successful mandate grows trust — "
                   "and trust brings capital and referrals."),
                (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM, inner.w)
            return
        # actifs d'abord (confiance décroissante), perdus à la fin
        book.sort(key=lambda c: (c["lost"], -c["trust"]))
        list_area = pygame.Rect(inner.x - 4, inner.y, inner.w + 8, inner.h)
        self._list_rect = list_area
        max_scroll = max(0, len(book) * ROW_H - list_area.h)
        self.scroll = min(self.scroll, max_scroll)
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        for c in book:
            r = pygame.Rect(inner.x, y, inner.w, ROW_H - 8)
            if r.bottom >= list_area.top and r.top <= list_area.bottom:
                self._draw_client_row(surf, r, c)
            y += ROW_H
        surf.set_clip(prev_clip)
        self.scroll = widgets.draw_scrollbar(surf, rect, list_area, self.scroll,
                                             max_scroll, len(book) * ROW_H)

    def _draw_client_row(self, surf, r, c):
        from core.mandates import profile_label
        lost = c["lost"]
        pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=4)
        name_col = config.COL_TEXT_DIM if lost else config.COL_TEXT
        widgets.draw_text(surf, c["name"], (r.x + 10, r.y + 6),
                          fonts.small(bold=not lost), name_col)
        sub = profile_label(c["profile"])
        if c.get("referred_by"):
            sub += _L(f" · référé par {c['referred_by']}",
                      f" · referred by {c['referred_by']}")
        widgets.draw_text(surf, widgets.fit_text(sub, fonts.tiny(), r.w // 2),
                          (r.x + 10, r.y + 26), fonts.tiny(), config.COL_TEXT_DIM)
        stats = _L(f"{c['done']} réussi(s) · {c['failed']} échec(s) · "
                   f"capital ×{c['capital_mult']:.2f}",
                   f"{c['done']} won · {c['failed']} failed · "
                   f"capital ×{c['capital_mult']:.2f}")
        widgets.draw_text(surf, stats, (r.right - 10, r.y + 26), fonts.tiny(),
                          config.COL_TEXT_DIM, align="right")
        if lost:
            widgets.draw_text(surf, _L("CLIENT PERDU", "CLIENT LOST"),
                              (r.right - 10, r.y + 6), fonts.tiny(bold=True),
                              config.COL_DOWN, align="right")
            return
        # jauge de confiance
        bar = pygame.Rect(r.right - 150, r.y + 9, 110, 8)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar, border_radius=3)
        fill = bar.copy()
        fill.w = max(2, int(bar.w * c["trust"] / 100.0))
        pygame.draw.rect(surf, _trust_color(c["trust"]), fill, border_radius=3)
        widgets.draw_text(surf, f"{c['trust']}", (bar.right + 8, r.y + 4),
                          fonts.tiny(bold=True), _trust_color(c["trust"]))
