"""
order_prompt.py — Mixin réutilisable pour poser/lister des ORDRES
CONDITIONNELS (stop-loss / take-profit / trailing, core/conditional_orders.py)
depuis une app du bureau.

Factorisé depuis apps/app_trading.py (qui l'utilisait seul jusqu'ici) pour
que l'app Portefeuille (apps/app_book.py) offre le même geste : un joueur qui
gère son book depuis la fenêtre Portefeuille voit ses ordres en cours et peut
en poser sans devoir ouvrir Trading. L'app hôte doit fournir :
  - self.app (App globale), self.market (moteur de marché),
  - self.msg (str, ligne de message de l'app),
  - self._held(tk) -> nb de titres détenus (négatif = short).
Le mixin gère : boîte modale de saisie (_open_order_prompt/_draw_order_prompt/
_handle_order_prompt_event), bande récapitulative (_draw_cond_orders_band),
annulation individuelle (croix par ligne, _cond_cancel_rects).
"""
import pygame

from core import conditional_orders as CO
from core import config
from ui import fonts, style, widgets

COND_ROW_H = 20
COND_LIST_MAX_H = 88


class ConditionalOrderMixin:
    def init_order_prompt(self):
        self._order_prompt = None      # {"ticker": tk} en attente, ou None
        self._order_kind = "stop"
        self._order_price_str = ""
        self._order_focus = False
        self._order_kind_rects = {}
        self._order_price_rect = None
        self._order_confirm_rect = None
        self._order_cancel_rect = None
        self._cond_cancel_rects = {}   # order_id -> Rect (croix d'annulation)
        self._order_rects = {}         # ticker -> Rect (bouton ORD par ligne)

    # ------------------------------------------------------------- logique
    def _open_order_prompt(self, tk):
        price = self.market.price_of(tk)
        self._order_prompt = {"ticker": tk}
        self._order_kind = "stop"
        self._order_price_str = f"{price:.2f}" if price is not None else ""
        self._order_focus = True

    def _confirm_order(self):
        tk = self._order_prompt["ticker"]
        try:
            val = float(self._order_price_str)
        except ValueError:
            self.msg = "Valeur invalide."
            return
        if self._order_kind == "trailing":
            r = CO.place_trailing(self.app.gs.player, self.market, tk, val)
        else:
            r = CO.place(self.app.gs.player, self.market, tk, self._order_kind, val)
        if r["ok"]:
            labels = {"stop": "Stop-loss", "target": "Take-profit", "trailing": "Trailing stop"}
            label = labels.get(self._order_kind, "Ordre")
            if self._order_kind == "trailing":
                self.msg = f"{label} posé sur {tk} à {val:.1f}%."
            else:
                self.msg = f"{label} posé sur {tk} à {val:,.2f}."
            self._order_prompt = None
            self._order_focus = False
        else:
            self.msg = f"Ordre refusé ({r['reason']})."

    def _cancel_conditional(self, order_id):
        CO.cancel(self.app.gs.player, order_id)

    def _cond_orders(self):
        return getattr(self.app.gs.player, "conditional_orders", None) or []

    # -------------------------------------------------------------- events
    def _handle_order_prompt_event(self, event):
        """À appeler EN PREMIER par handle_event tant que _order_prompt est
        ouvert : la boîte est modale, elle absorbe tout."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._order_prompt = None
            self._order_focus = False
            return True
        if self._order_focus and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self._order_price_str = self._order_price_str[:-1]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_order()
                return True
            if event.unicode and (event.unicode.isdigit() or event.unicode == "."):
                self._order_price_str += event.unicode
                return True
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._order_price_rect and self._order_price_rect.collidepoint(event.pos):
                self._order_focus = True
                return True
            for kind, r in self._order_kind_rects.items():
                if r.collidepoint(event.pos):
                    self._order_kind = kind
                    return True
            if self._order_confirm_rect and self._order_confirm_rect.collidepoint(event.pos):
                self._confirm_order()
                return True
            if self._order_cancel_rect and self._order_cancel_rect.collidepoint(event.pos):
                self._order_prompt = None
                self._order_focus = False
                return True
            return True
        return False

    def _handle_cond_cancel_click(self, pos):
        """Clic sur une croix de la bande récapitulative : annule l'ordre.
        Retourne True si un ordre a été annulé."""
        for oid, r in self._cond_cancel_rects.items():
            if r.collidepoint(pos):
                self._cancel_conditional(oid)
                return True
        return False

    # ---------------------------------------------------------------- draw
    def cond_band_height(self, orders):
        """Hauteur de la bande récapitulative pour `orders` (0 si aucun)."""
        return min(COND_LIST_MAX_H, 18 + len(orders) * COND_ROW_H) if orders else 0

    def _draw_cond_orders_band(self, surf, cond_area, orders):
        """Bande « ORDRES CONDITIONNELS » : liste + croix d'annulation."""
        self._cond_cancel_rects = {}
        style.draw_card(surf, cond_area, bg=config.COL_BG, border=config.COL_PRESTIGE,
                        radius=style.RADIUS_MD)
        widgets.draw_text(surf, f"ORDRES CONDITIONNELS ({len(orders)})",
                          (cond_area.x + 6, cond_area.y + 2), fonts.tiny(bold=True),
                          config.COL_PRESTIGE)
        oy = cond_area.y + 16
        for order in orders:
            if oy + COND_ROW_H > cond_area.bottom:
                break
            labels = {"stop": "Stop-loss", "target": "Take-profit", "trailing": "Trailing"}
            label = labels.get(order["kind"], "Ordre")
            short_tag = " (short)" if order.get("is_short") else ""
            qty_txt = "tout" if order["qty"] == "ALL" else f"{order['qty']:g}"
            if order["kind"] == "trailing":
                trig_txt = f"{order.get('distance_pct', 0):.1f}%"
            else:
                trig_txt = f"{order['trigger']:,.2f}"
            widgets.draw_text(surf,
                              f"{order['ticker']}{short_tag} · {label} @ {trig_txt} ({qty_txt})",
                              (cond_area.x + 6, oy), fonts.tiny(), config.COL_TEXT)
            cx = pygame.Rect(cond_area.right - 20, oy, 14, 14)
            self._cond_cancel_rects[order["id"]] = cx
            hov = cx.collidepoint(pygame.mouse.get_pos())
            pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                             (cx.x + 2, cx.y + 2), (cx.right - 2, cx.bottom - 2), 2)
            pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                             (cx.x + 2, cx.bottom - 2), (cx.right - 2, cx.y + 2), 2)
            oy += COND_ROW_H

    def _draw_order_prompt(self, surf, rect):
        """Boîte de dialogue modale (dans la fenêtre) pour poser un ordre
        conditionnel (stop-loss/take-profit/trailing) sur la position choisie."""
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, rect.topleft)
        tk = self._order_prompt["ticker"]
        box = pygame.Rect(0, 0, min(320, rect.w - 40), 184)
        box.center = rect.center
        style.draw_card(surf, box, bg=config.COL_PANEL, border=config.COL_PRESTIGE,
                        radius=style.RADIUS_MD)
        widgets.draw_text(surf, f"ORDRE CONDITIONNEL — {tk}", (box.x + 12, box.y + 8),
                          fonts.small(bold=True), config.COL_PRESTIGE)
        held = self._held(tk)
        price = self.market.price_of(tk)
        side = "SHORT" if held < 0 else "LONG"
        pos_txt = f"Position {side} : {held:g}"
        widgets.draw_text(surf, f"{pos_txt} · cours {price:,.2f}" if price is not None else pos_txt,
                          (box.x + 12, box.y + 28), fonts.tiny(), config.COL_TEXT_DIM)

        self._order_kind_rects = {}
        x = box.x + 12
        kind_opts = [("stop", "Stop-loss", config.COL_DOWN),
                     ("target", "Take-profit", config.COL_UP),
                     ("trailing", "Trailing", config.COL_CYAN)]
        for kind, label, col in kind_opts:
            w = 96
            r = pygame.Rect(x, box.y + 48, w, 24)
            self._order_kind_rects[kind] = r
            active = (kind == self._order_kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_BG, r, border_radius=4)
            pygame.draw.rect(surf, col if active else config.COL_BORDER, r, 2 if active else 1, border_radius=4)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True), col, align="center")
            x += w + 6

        # sens de déclenchement selon le CÔTÉ de la position (sur un short,
        # stop = couvre si le cours monte, target = couvre s'il baisse)
        is_short = held < 0
        act = "Couvre" if is_short else "Vend"
        senses = {
            "stop":     f"{act} si le cours passe {'AU-DESSUS' if is_short else 'SOUS'} le seuil.",
            "target":   f"{act} si le cours passe {'SOUS' if is_short else 'AU-DESSUS'} le seuil.",
            "trailing": (f"{act} si le cours rebondit de X% depuis son plus bas."
                         if is_short else
                         f"{act} si le cours retombe de X% depuis son plus haut."),
        }
        widgets.draw_text(surf, senses[self._order_kind], (box.x + 12, box.y + 76),
                          fonts.tiny(), config.COL_TEXT)
        if self._order_kind == "trailing":
            hint = "Distance (% du cours) :"
        else:
            hint = "Seuil de déclenchement :"
        widgets.draw_text(surf, hint, (box.x + 12, box.y + 94),
                          fonts.tiny(), config.COL_TEXT_DIM)
        self._order_price_rect = pygame.Rect(box.x + 12, box.y + 110, box.w - 24, 26)
        pygame.draw.rect(surf, config.COL_BG, self._order_price_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self._order_focus else config.COL_BORDER,
                         self._order_price_rect, 1, border_radius=4)
        cur = "_" if self._order_focus and pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, (self._order_price_str or "0") + cur,
                          (self._order_price_rect.x + 8, self._order_price_rect.y + 5),
                          fonts.small(), config.COL_TEXT)

        self._order_confirm_rect = pygame.Rect(box.x + 12, box.bottom - 32, box.w - 88, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._order_confirm_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_PRESTIGE, self._order_confirm_rect, 1, border_radius=4)
        widgets.draw_text(surf, "POSER L'ORDRE", self._order_confirm_rect.center,
                          fonts.tiny(bold=True), config.COL_PRESTIGE, align="center")
        self._order_cancel_rect = pygame.Rect(self._order_confirm_rect.right + 6, box.bottom - 32, 60, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._order_cancel_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_TEXT_DIM, self._order_cancel_rect, 1, border_radius=4)
        widgets.draw_text(surf, "Annuler", self._order_cancel_rect.center,
                          fonts.tiny(), config.COL_TEXT_DIM, align="center")
