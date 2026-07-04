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
from core import audio, config, order_confirm, unlocks
from core import conditional_orders as CO
from core import portfolio as PF
from core import portfolio_margin as PM
from ui import fonts, widgets

ROW_H = 24
QTY_PRESETS = [1, 5, 10, 25, 100]
AMOUNT_PRESETS = [500, 1000, 5000, 10000]
COND_ROW_H = 20
COND_LIST_MAX_H = 88   # zone réservée aux ordres en cours (0 si aucun)
FEED_MAX = 5           # derniers ordres exécutés affichés en bas de fenêtre
FEED_FLASH_MS = 900    # durée du flash de fond sur le dernier ordre


class TradingApp(DesktopApp):
    title = "Trading — Ordres"
    icon_kind = "trading"
    default_size = (840, 520)
    # largeur mini 640 (pas 560) : sous ~640 px, les colonnes COURS/POSSÉDÉ
    # passaient sous le bloc de boutons ORD/VENDRE/ACHETER des lignes détenues
    min_size = (640, 340)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.search = ""
        self.qty_text = "10"
        # "shares" (qty_text = nombre de titres) ou "amount" (qty_text = montant
        # en devise — le nombre de titres est calculé au moment de l'ordre,
        # cf. `_qty_for_ticker`) : évite au joueur de calculer lui-même combien
        # d'actions représente "je veux investir 5000€".
        self.qty_mode = "shares"
        self._qty_mode_rects = {}
        self.msg = ""
        # fil des derniers ordres EXÉCUTÉS de la session (achat/vente), avec
        # flash de confirmation sur le plus récent — le trade doit se SENTIR.
        self.order_feed = []
        self.scroll = 0
        self._max_scroll = 0
        self._buy_rects = {}
        self._sell_rects = {}
        self._preset_rects = {}
        self._qty_minus = self._qty_plus = None
        self._list_rect = None
        # ordres conditionnels (stop-loss / take-profit)
        self._order_rects = {}         # ticker -> Rect (bouton "⚑" par ligne détenue)
        self._order_prompt = None      # {"ticker": tk} en attente de saisie, ou None
        self._order_kind = "stop"
        self._order_price_str = ""
        self._order_focus = False
        self._order_kind_rects = {}
        self._order_price_rect = None
        self._order_confirm_rect = None
        self._order_cancel_rect = None
        self._cond_cancel_rects = {}   # order_id -> Rect (× dans la liste des ordres en cours)
        # confirmation des ordres à fort impact (>30% du patrimoine net) :
        # {"side","ticker","qty","notional","ratio"} en attente, ou None
        self._confirm_pending = None
        self._confirm_yes_rect = None
        self._confirm_no_rect = None
        self._flash = widgets.TickFlash()   # flash vert/rouge du cours en direct (COURS)

    def _live_price(self, tk):
        """Cours EN DIRECT (chemin de prix canonique, cf. core/intraday.py) —
        gelé automatiquement si la place de cotation de `tk` est fermée. La
        liste de valeurs affichait jusqu'ici le cours STATIQUE du pas
        (`market.price_of`), figé entre deux pas de marché (~80 s réelles à
        x1) : rien ne semblait bouger à l'écran tant qu'un nouveau pas
        n'arrivait pas. L'exécution reste sur `market.price_of` (fill_price)
        — seul l'AFFICHAGE devient vivant."""
        hist = self.market.history_of(tk, 1, sim_clock=self.app.sim_clock,
                                      day=self.app.gs.player.day)
        return hist[-1] if hist else self.market.price_of(tk)

    def focus_ticker(self, ticker):
        """Pré-filtre la liste sur `ticker` — appelé par le lien « Trader »
        de l'app Recherche (cf. DesktopScene.open_trading)."""
        self.search = str(ticker).upper()
        self.scroll = 0
        self.msg = f"Prêt à trader {self.search}."

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def _qty(self):
        try:
            return max(0.0, float(self.qty_text))
        except ValueError:
            return 0.0

    def _qty_for_ticker(self, tk):
        """Quantité RÉELLE en titres pour `tk` — convertit le montant saisi
        en nombre de titres si `qty_mode == "amount"` (arrondi au titre
        inférieur, comme un vrai ordre ne peut pas acheter une fraction
        d'action), sinon renvoie directement la quantité saisie."""
        raw = self._qty()
        if self.qty_mode != "amount":
            return raw
        price = self.market.price_of(tk)
        if not price or price <= 0:
            return 0.0
        return float(int(raw / price))

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
        qty = self._qty_for_ticker(tk)
        if qty <= 0:
            self.msg = "Quantité invalide."
            return
        if self._maybe_ask_confirmation("buy", tk, qty):
            return
        self._execute_buy(tk, qty)

    def _do_sell(self, tk):
        if not self._can_trade():
            return
        held = self._held(tk)
        if held <= 0:
            return
        qty = min(self._qty_for_ticker(tk), held)
        if qty <= 0:
            self.msg = "Quantité invalide."
            return
        if self._maybe_ask_confirmation("sell", tk, qty):
            return
        self._execute_sell(tk, qty)

    def _maybe_ask_confirmation(self, side, tk, qty):
        """Ordre au-delà du seuil d'impact (core/order_confirm.py, >30% du
        patrimoine net) : suspend l'exécution et ouvre une boîte de
        confirmation au lieu d'exécuter directement — retourne True si
        l'ordre est bien mis en attente (donc PAS encore exécuté)."""
        price = self.market.price_of(tk)
        notional = (price or 0.0) * qty
        p = self.app.gs.player
        if not order_confirm.needs_confirmation(p, self.market, notional):
            return False
        self._confirm_pending = {
            "side": side, "ticker": tk, "qty": qty, "notional": notional,
            "ratio": order_confirm.impact_ratio(p, self.market, notional),
        }
        return True

    def _execute_buy(self, tk, qty):
        r = PF.buy(self.app.gs.player, self.market, tk, qty)
        if r["ok"]:
            self.msg = ""
            self._push_feed(f"ACHAT {qty:g}×{tk} @ {r['price']:.2f}", "up")
        else:
            self.msg = f"Achat refusé ({r['reason']})."

    def _execute_sell(self, tk, qty):
        r = PF.sell(self.app.gs.player, self.market, tk, qty)
        if r["ok"]:
            self.msg = ""
            self._push_feed(f"VENTE {r['qty']:g}×{tk} @ {r['price']:.2f} "
                            f"(P&L {r['realized']:+,.0f})",
                            "up" if r["realized"] >= 0 else "down")
        else:
            self.msg = f"Vente refusée ({r['reason']})."

    def _confirm_pending_execute(self):
        c = self._confirm_pending
        self._confirm_pending = None
        if c is None:
            return
        if c["side"] == "buy":
            self._execute_buy(c["ticker"], c["qty"])
        else:
            self._execute_sell(c["ticker"], c["qty"])

    def _confirm_pending_cancel(self):
        self._confirm_pending = None

    def _push_feed(self, text, kind):
        """Empile un ordre exécuté dans le fil de confirmation (flash + son)
        et déclenche l'autosave — le trade doit se voir ET s'entendre."""
        self.order_feed.insert(0, {"text": text, "kind": kind,
                                   "ts": pygame.time.get_ticks()})
        del self.order_feed[FEED_MAX:]
        audio.play("order")
        self._autosave()

    def _autosave(self):
        p = self.app.gs.player
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    # ---------------------------------------------- ordres conditionnels
    def _open_order_prompt(self, tk):
        price = self.market.price_of(tk)
        self._order_prompt = {"ticker": tk}
        self._order_kind = "stop"
        self._order_price_str = f"{price:.2f}" if price is not None else ""
        self._order_focus = True

    def _confirm_order(self):
        tk = self._order_prompt["ticker"]
        try:
            trigger = float(self._order_price_str)
        except ValueError:
            self.msg = "Seuil invalide."
            return
        r = CO.place(self.app.gs.player, self.market, tk, self._order_kind, trigger)
        if r["ok"]:
            label = "Stop-loss" if self._order_kind == "stop" else "Take-profit"
            self.msg = f"{label} posé sur {tk} à {trigger:,.2f}."
            self._order_prompt = None
            self._order_focus = False
        else:
            self.msg = f"Ordre refusé ({r['reason']})."

    def _cancel_conditional(self, order_id):
        CO.cancel(self.app.gs.player, order_id)

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if self._confirm_pending is not None:
            return self._handle_confirm_event(event)
        if self._order_prompt is not None:
            return self._handle_order_prompt_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for mode, r in self._qty_mode_rects.items():
                if r.collidepoint(event.pos):
                    if mode != self.qty_mode:
                        self.qty_mode = mode
                        self.qty_text = "10" if mode == "shares" else "1000"
                    return True
            step = 1.0 if self.qty_mode == "shares" else 50.0
            if self._qty_minus and self._qty_minus.collidepoint(event.pos):
                self.qty_text = f"{max(0.0, self._qty() - step):g}"
                return True
            if self._qty_plus and self._qty_plus.collidepoint(event.pos):
                self.qty_text = f"{self._qty() + step:g}"
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
            for tk, r in self._order_rects.items():
                if r.collidepoint(event.pos):
                    self._open_order_prompt(tk)
                    return True
            for oid, r in self._cond_cancel_rects.items():
                if r.collidepoint(event.pos):
                    self._cancel_conditional(oid)
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

    def _handle_confirm_event(self, event):
        """Boîte « ordre à fort impact » : ÉCHAP/clic sur « Annuler » abandonne
        SANS exécuter l'ordre (comportement volontairement le plus sûr,
        cohérent avec ÉCHAP = annuler ailleurs dans le jeu) ; ENTRÉE/clic sur
        « Confirmer » exécute l'ordre resté en attente."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._confirm_pending_cancel()
            return True
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirm_pending_execute()
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._confirm_yes_rect and self._confirm_yes_rect.collidepoint(event.pos):
                self._confirm_pending_execute()
                return True
            if self._confirm_no_rect and self._confirm_no_rect.collidepoint(event.pos):
                self._confirm_pending_cancel()
                return True
            return True
        return False

    def _handle_order_prompt_event(self, event):
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
        # pouvoir d'achat — version compacte si la fenêtre est étroite (le
        # libellé complet passait SUR la barre de recherche à la taille mini)
        st = PM.margin_status(p, self.market)
        bp_full = (f"Pouvoir d'achat {widgets.format_money(st['buying_power'], cur)} · "
                   f"levier {st['leverage']:.2f}x")
        bp_short = f"PA {widgets.format_money(st['buying_power'], cur)}"
        bp_avail = rect.right - pad - (sr.right + 12)
        bp_font = fonts.small(bold=True)
        bp_txt = bp_full if bp_font.size(bp_full)[0] <= bp_avail else bp_short
        if bp_font.size(bp_txt)[0] <= bp_avail:
            widgets.draw_text(surf, bp_txt,
                              (rect.right - pad, rect.y + pad + 4), bp_font,
                              config.COL_DOWN if st["margin_call"] else config.COL_TEXT_DIM, align="right")
        # quantité — bascule "Titres" (nombre d'actions) / "€" (montant investi,
        # le jeu calcule la quantité correspondante au moment de l'ordre) :
        # évite au joueur de calculer lui-même "combien d'actions pour 5000€".
        qy = sr.bottom + 8
        widgets.draw_text(surf, "QUANTITÉ", (rect.x + pad, qy + 4), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        mx = rect.x + pad + 76
        self._qty_mode_rects = {}
        for mode, label in (("shares", "Titres"), ("amount", cur)):
            w = fonts.tiny(bold=True).size(label)[0] + 12
            r = pygame.Rect(mx, qy, w, 22)
            self._qty_mode_rects[mode] = r
            active = self.qty_mode == mode
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_BG, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            mx += w + 4
        qx = mx + 8
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
        presets = QTY_PRESETS if self.qty_mode == "shares" else AMOUNT_PRESETS
        for val in presets:
            plabel = f"x{val}" if self.qty_mode == "shares" else f"{val:g}"
            w = fonts.tiny(bold=True).size(plabel)[0] + 12
            r = pygame.Rect(px, qy, w, 22)
            self._preset_rects[val] = r
            pygame.draw.rect(surf, config.COL_BG, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, plabel, r.center, fonts.tiny(bold=True), config.COL_TEXT_DIM, align="center")
            px += w + 6

        # liste (rétrécie si des ordres conditionnels sont en cours, pour leur
        # réserver une bande visible sans qu'ils soient enterrés hors écran)
        orders = getattr(p, "conditional_orders", None) or []
        cond_h = min(COND_LIST_MAX_H, 18 + len(orders) * COND_ROW_H) if orders else 0
        list_top = qy + 30
        list_area = pygame.Rect(rect.x + pad, list_top, rect.w - 2 * pad,
                                rect.bottom - list_top - 30 - cond_h - (6 if cond_h else 0))
        self._list_rect = list_area
        pygame.draw.rect(surf, config.COL_BG, list_area)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)
        widgets.draw_text(surf, "VALEUR", (list_area.x + 8, list_area.y + 4), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "COURS", (list_area.x + int(list_area.w * 0.52), list_area.y + 4),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "POSSÉDÉ", (list_area.x + int(list_area.w * 0.66), list_area.y + 4),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        rows = self._rows()
        self._buy_rects, self._sell_rects, self._order_rects = {}, {}, {}
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

        # ordres conditionnels en cours (stop-loss/take-profit)
        self._cond_cancel_rects = {}
        if orders:
            cond_area = pygame.Rect(rect.x + pad, list_area.bottom + 6, rect.w - 2 * pad, cond_h)
            pygame.draw.rect(surf, config.COL_BG, cond_area)
            pygame.draw.rect(surf, config.COL_PRESTIGE, cond_area, 1)
            widgets.draw_text(surf, f"ORDRES CONDITIONNELS ({len(orders)})",
                              (cond_area.x + 6, cond_area.y + 2), fonts.tiny(bold=True), config.COL_PRESTIGE)
            oy = cond_area.y + 16
            for order in orders:
                if oy + COND_ROW_H > cond_area.bottom:
                    break
                label = "Stop-loss" if order["kind"] == "stop" else "Take-profit"
                qty_txt = "tout" if order["qty"] == "ALL" else f"{order['qty']:g}"
                widgets.draw_text(surf,
                                  f"{order['ticker']} · {label} @ {order['trigger']:,.2f} ({qty_txt})",
                                  (cond_area.x + 6, oy), fonts.tiny(), config.COL_TEXT)
                cx = pygame.Rect(cond_area.right - 20, oy, 14, 14)
                self._cond_cancel_rects[order["id"]] = cx
                hov = cx.collidepoint(pygame.mouse.get_pos())
                pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                                 (cx.x + 2, cx.y + 2), (cx.right - 2, cx.bottom - 2), 2)
                pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                                 (cx.x + 2, cx.bottom - 2), (cx.right - 2, cx.y + 2), 2)
                oy += COND_ROW_H
            msg_y = cond_area.bottom + 6
        else:
            msg_y = list_area.bottom + 6

        # message d'erreur/info, sinon fil des derniers ordres exécutés
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.small(), rect.w - 2 * pad),
                              (rect.x + pad, msg_y), fonts.small(), config.COL_WARN)
        else:
            self._draw_feed(surf, rect, msg_y, pad)

        if self._order_prompt is not None:
            self._draw_order_prompt(surf, rect)
        if self._confirm_pending is not None:
            self._draw_confirm_dialog(surf, rect)

    def _draw_confirm_dialog(self, surf, rect):
        """Boîte de confirmation modale pour un ordre à fort impact (>30% du
        patrimoine net, cf. core/order_confirm.py) — même style que la boîte
        d'ordre conditionnel, couleur ambre pour marquer l'avertissement."""
        c = self._confirm_pending
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, rect.topleft)
        box = pygame.Rect(0, 0, min(340, rect.w - 40), 150)
        box.center = rect.center
        pygame.draw.rect(surf, config.COL_PANEL, box)
        pygame.draw.rect(surf, config.COL_AMBER, box, 2)
        side_label = "ACHAT" if c["side"] == "buy" else "VENTE"
        widgets.draw_text(surf, f"⚠ ORDRE À FORT IMPACT — {side_label} {c['ticker']}",
                          (box.x + 12, box.y + 8), fonts.small(bold=True), config.COL_AMBER)
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        widgets.draw_text(surf, f"{c['qty']:g} titres — {widgets.format_money(c['notional'], cur)}",
                          (box.x + 12, box.y + 32), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"Soit {c['ratio']*100:.0f}% de votre patrimoine net en un seul ordre.",
                          (box.x + 12, box.y + 54), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "Confirmer ?", (box.x + 12, box.y + 76),
                          fonts.tiny(), config.COL_TEXT_DIM)
        self._confirm_yes_rect = pygame.Rect(box.x + 12, box.bottom - 32, box.w - 88, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._confirm_yes_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER, self._confirm_yes_rect, 1, border_radius=4)
        widgets.draw_text(surf, "CONFIRMER", self._confirm_yes_rect.center,
                          fonts.tiny(bold=True), config.COL_AMBER, align="center")
        self._confirm_no_rect = pygame.Rect(self._confirm_yes_rect.right + 6, box.bottom - 32, 60, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._confirm_no_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_TEXT_DIM, self._confirm_no_rect, 1, border_radius=4)
        widgets.draw_text(surf, "Annuler", self._confirm_no_rect.center,
                          fonts.tiny(), config.COL_TEXT_DIM, align="center")

    def _draw_feed(self, surf, rect, y, pad):
        """Fil des derniers ordres exécutés : le plus récent en couleur avec un
        flash de fond qui s'estompe (confirmation bien visible), les
        précédents en gris, sur la même ligne tant qu'il reste de la place."""
        if not self.order_feed:
            return
        colors = {"up": config.COL_UP, "down": config.COL_DOWN}
        x = rect.x + pad
        max_x = rect.right - pad
        now = pygame.time.get_ticks()
        for i, entry in enumerate(self.order_feed):
            font = fonts.small(bold=True) if i == 0 else fonts.tiny()
            col = colors.get(entry["kind"], config.COL_TEXT) if i == 0 else config.COL_TEXT_DIM
            text = entry["text"] if i == 0 else "· " + entry["text"]
            w = font.size(text)[0]
            if x + w > max_x:
                break
            if i == 0:
                age = now - entry["ts"]
                if age < FEED_FLASH_MS:
                    alpha = int(120 * (1 - age / FEED_FLASH_MS))
                    flash = pygame.Surface((w + 8, 18), pygame.SRCALPHA)
                    flash.fill((*colors.get(entry["kind"], config.COL_TEXT), alpha))
                    surf.blit(flash, (x - 4, y - 1))
            widgets.draw_text(surf, text, (x, y), font, col)
            x += w + 10

    def _draw_row(self, surf, tk, area, y, cur):
        m = self.market
        i = m.ticker_idx.get(tk)
        if i is None:
            return
        c = m.companies[i]
        price = self._live_price(tk)
        flash_col = self._flash.tick(tk, price, config.COL_UP, config.COL_DOWN, config.COL_WHITE)
        held = self._held(tk)
        r = pygame.Rect(area.x + 2, y, area.w - 4, ROW_H - 2)
        mp = pygame.mouse.get_pos()
        if r.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, r)
        widgets.draw_text(surf, tk, (r.x + 6, r.y + 4), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(c["name"], fonts.tiny(), int(area.w * 0.40)),
                          (r.x + 66, r.y + 5), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{price:,.2f}", (area.x + int(area.w * 0.52), r.y + 4),
                          fonts.small(), flash_col)
        held_x = area.x + int(area.w * 0.66)
        held_avail = max(20, (r.right - 174) - held_x)   # jamais sous les boutons ORD/VENDRE/ACHETER
        widgets.draw_text(surf, widgets.fit_text(f"{held:g}" if held else "—",
                                                 fonts.small(bold=held > 0), held_avail),
                          (held_x, r.y + 4), fonts.small(bold=held > 0),
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
                # ordre conditionnel (stop-loss/take-profit) sur cette position
                # (texte plain, pas de glyphe pictographique — non couvert par
                # la police embarquée, cf. CLAUDE.md/ui/desktop_icons.py)
                ore = pygame.Rect(sre.x - 34, r.y, 30, ROW_H - 4)
                self._order_rects[tk] = ore
                hov = ore.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD, ore, border_radius=3)
                pygame.draw.rect(surf, config.COL_PRESTIGE, ore, 1, border_radius=3)
                widgets.draw_text(surf, "ORD", ore.center, fonts.tiny(bold=True), config.COL_PRESTIGE, align="center")

    def _draw_order_prompt(self, surf, rect):
        """Boîte de dialogue modale (dans la fenêtre) pour poser un ordre
        conditionnel (stop-loss/take-profit) sur la position sélectionnée."""
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, rect.topleft)
        tk = self._order_prompt["ticker"]
        box = pygame.Rect(0, 0, min(320, rect.w - 40), 160)
        box.center = rect.center
        pygame.draw.rect(surf, config.COL_PANEL, box)
        pygame.draw.rect(surf, config.COL_PRESTIGE, box, 2)
        widgets.draw_text(surf, f"ORDRE CONDITIONNEL — {tk}", (box.x + 12, box.y + 8),
                          fonts.small(bold=True), config.COL_PRESTIGE)
        held = self._held(tk)
        price = self.market.price_of(tk)
        widgets.draw_text(surf, f"Détenu : {held:g} · cours {price:,.2f}" if price is not None else f"Détenu : {held:g}",
                          (box.x + 12, box.y + 28), fonts.tiny(), config.COL_TEXT_DIM)

        self._order_kind_rects = {}
        x = box.x + 12
        for kind, label in (("stop", "Stop-loss"), ("target", "Take-profit")):
            w = 130
            r = pygame.Rect(x, box.y + 48, w, 24)
            self._order_kind_rects[kind] = r
            active = (kind == self._order_kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_BG, r, border_radius=4)
            col = config.COL_DOWN if kind == "stop" else config.COL_UP
            pygame.draw.rect(surf, col if active else config.COL_BORDER, r, 2 if active else 1, border_radius=4)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True), col, align="center")
            x += w + 8

        widgets.draw_text(surf, "Seuil de déclenchement :", (box.x + 12, box.y + 82),
                          fonts.tiny(), config.COL_TEXT_DIM)
        self._order_price_rect = pygame.Rect(box.x + 12, box.y + 98, box.w - 24, 26)
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
