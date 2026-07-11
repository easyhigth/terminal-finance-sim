"""
app_pitchbook.py — Application « Pitch Book » du bureau (NATIVE, EXCLUSIVE
voie Advisory, cf. core/unlocks.TRACK_AFFINITY["pitchbook"] et
scene_desktop_common.TRACK_APP).

Démarchage ACTIF de mandats (core/pitch_book.py) : choisir un profil client,
régler l'ambition du pitch (capital/objectif visés), lire la probabilité de
succès calculée AVANT de se lancer, puis pitcher — remplace le tirage
purement passif de core/mandates.py::maybe_offer par un vrai outil du
banquier-conseil.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import mandates as M
from core import pitch_book as PB
from ui import fonts, widgets

AMBITION_STEP = 0.1


class PitchBookApp(DesktopApp):
    title = "Pitch Book"
    icon_kind = "advisory"
    default_size = (980, 620)
    min_size = (760, 480)

    def on_open(self):
        self.profile_key = M.CLIENT_PROFILES[0]["key"]
        self.ambition = 1.0
        self._log = []
        self._chip_rects = {}
        self._adj_rects = {}
        self._pitch_btn = None

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for key, r in self._chip_rects.items():
            if r.collidepoint(pos):
                self.profile_key = key
                return True
        for key, r in self._adj_rects.items():
            if r.collidepoint(pos):
                if key == "amb-":
                    self.ambition = max(PB.MIN_AMBITION, round(self.ambition - AMBITION_STEP, 2))
                elif key == "amb+":
                    self.ambition = min(PB.MAX_AMBITION, round(self.ambition + AMBITION_STEP, 2))
                return True
        if self._pitch_btn and self._pitch_btn.collidepoint(pos):
            self._do_pitch()
            return True
        return False

    def _do_pitch(self):
        p = self.app.gs.player
        market = self.app.ensure_market()
        result = PB.pitch(p, self.profile_key, self.ambition, market=market)
        self._log.insert(0, result)
        self._log = self._log[:8]

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        pad = 14
        p = self.app.gs.player
        widgets.draw_text(surf, "PITCH BOOK — démarchage actif de mandats",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        if p.grade_index < M.MIN_GRADE:
            widgets.draw_text(surf, f"Réservé aux grades {config.GRADES[M.MIN_GRADE]} "
                              "et au-delà.", (rect.x + pad, rect.y + 40),
                              fonts.small(), config.COL_TEXT_DIM)
            return

        col_w = (rect.w - 3 * pad) // 2
        left = pygame.Rect(rect.x + pad, rect.y + 34, col_w, rect.h - 34 - pad)
        right = pygame.Rect(left.right + pad, rect.y + 34, col_w, left.h)
        self._draw_profiles(surf, left, p)
        self._draw_pitch_panel(surf, right, p)

    def _draw_profiles(self, surf, body, p):
        inner = widgets.draw_panel(surf, body, "Profils clients", config.COL_CYAN)
        self._chip_rects = {}
        y = inner.y
        for prof in M.CLIENT_PROFILES:
            key = prof["key"]
            sel = key == self.profile_key
            allowed, until = PB.can_pitch(p, key)
            row = pygame.Rect(inner.x, y, inner.w, 58)
            self._chip_rects[key] = row
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             row, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             row, 1, border_radius=4)
            label = M.profile_label(key)
            col = config.COL_TEXT if allowed else config.COL_TEXT_DIM
            widgets.draw_text(surf, label, (row.x + 8, row.y + 6),
                              fonts.small(bold=True), col)
            if not allowed:
                widgets.draw_text(surf, f"indisponible jusqu'au trimestre {until}",
                                  (row.x + 8, row.y + 24), fonts.tiny(), config.COL_DOWN)
            else:
                fit = PB.fit_score(p, key)
                widgets.draw_text(surf, f"affinité {fit * 100:.0f}%",
                                  (row.x + 8, row.y + 24), fonts.tiny(), config.COL_TEXT_DIM)
            desc = widgets.fit_text(M.profile_desc(key), fonts.tiny(), row.w - 16)
            widgets.draw_text(surf, desc, (row.x + 8, row.y + 40), fonts.tiny(),
                              config.COL_TEXT_DIM)
            y += 64
            if y > inner.bottom - 58:
                break

    def _draw_pitch_panel(self, surf, body, p):
        inner = widgets.draw_panel(surf, body, "Préparer le pitch", config.COL_AMBER)
        self._adj_rects = {}
        y = inner.y
        widgets.draw_text(surf, f"Client : {M.profile_label(self.profile_key)}",
                          (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
        y += 24
        widgets.draw_text(surf, f"Ambition : {self.ambition:.1f}× "
                          "(capital et objectif visés)", (inner.x, y),
                          fonts.tiny(bold=True), config.COL_CYAN)
        bx = inner.x + fonts.tiny(bold=True).size(
            f"Ambition : {self.ambition:.1f}× (capital et objectif visés)")[0] + 8
        r1 = pygame.Rect(bx, y - 2, 18, 18)
        self._adj_rects["amb-"] = r1
        pygame.draw.rect(surf, config.COL_PANEL, r1, border_radius=3)
        pygame.draw.rect(surf, config.COL_BORDER, r1, 1, border_radius=3)
        widgets.draw_text(surf, "−", r1.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        r2 = pygame.Rect(bx + 22, y - 2, 18, 18)
        self._adj_rects["amb+"] = r2
        pygame.draw.rect(surf, config.COL_PANEL, r2, border_radius=3)
        pygame.draw.rect(surf, config.COL_BORDER, r2, 1, border_radius=3)
        widgets.draw_text(surf, "+", r2.center, fonts.small(bold=True),
                          config.COL_TEXT, align="center")
        y += 30
        prob = PB.win_probability(p, self.profile_key, self.ambition)
        allowed, until = PB.can_pitch(p, self.profile_key)
        pcol = config.COL_UP if prob >= 0.5 else (
            config.COL_AMBER if prob >= 0.3 else config.COL_DOWN)
        widgets.draw_text(surf, "Probabilité de succès estimée",
                          (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
        y += 20
        widgets.draw_text(surf, f"{prob * 100:.0f}%",
                          (inner.x, y), fonts.title(bold=True), pcol)
        y += 44
        can_afford_slot = len(p.mandates) + len(p.mandate_offers) < M.MAX_ACTIVE + 1
        self._pitch_btn = pygame.Rect(inner.x, y, 160, 28)
        active = allowed and can_afford_slot
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL,
                         self._pitch_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP if active else config.COL_BORDER,
                         self._pitch_btn, 1, border_radius=4)
        widgets.draw_text(surf, "PITCHER", self._pitch_btn.center,
                          fonts.small(bold=True),
                          config.COL_UP if active else config.COL_TEXT_DIM, align="center")
        if not can_afford_slot:
            widgets.draw_text(surf, "Trop de mandats/offres en cours.",
                              (self._pitch_btn.right + 10, y + 6), fonts.tiny(),
                              config.COL_DOWN)
        y += 40
        widgets.draw_text(surf, "Journal des pitchs", (inner.x, y),
                          fonts.small(bold=True), config.COL_TEXT)
        y += 20
        for res in self._log:
            if y > inner.bottom - 16:
                break
            if not res.get("ok"):
                txt = f"— {res.get('reason', 'échec')}"
                col = config.COL_TEXT_DIM
            elif res.get("won"):
                offer = res.get("offer") or {}
                txt = (f"GAGNÉ — {offer.get('client', '?')} "
                       f"({offer.get('capital', 0):,.0f}, {offer.get('target_pct', 0):+.1f}%)")
                col = config.COL_UP
            else:
                txt = f"PERDU — {res.get('reason', '')} ({res['probability'] * 100:.0f}% de chance)"
                col = config.COL_DOWN
            widgets.draw_text(surf, widgets.fit_text(txt, fonts.tiny(), inner.w),
                              (inner.x, y), fonts.tiny(), col)
            y += 16
