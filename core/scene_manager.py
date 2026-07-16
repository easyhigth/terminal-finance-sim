"""
scene_manager.py — Machine à états des écrans (scènes).
Chaque scène gère ses événements, sa logique et son rendu.
Un fondu (fade-in) est joué automatiquement à chaque changement de scène.
Ctrl+K ouvre par-dessus la scène courante une palette de navigation globale
(recherche + accès direct à n'importe quelle page du jeu).
"""
import pygame

from core import config, crashlog, fuzzy, ui_state
from core.i18n import get_lang
from core.sim_clock import LIVE_SCENE_NAMES
from ui import fonts, widgets

PALETTE_W, PALETTE_H = 560, 360
PALETTE_ROW_H = 30

# Scènes de flux pré-partie (menu, création de run...) : jamais de fil
# d'Ariane pendant cette phase, et la pile est purgée pour repartir propre
# une fois "terminal" atteint. "desktop" : écran MAÎTRE du jeu (refonte UI) —
# toute la navigation qui s'y passe est interne (fenêtres), jamais un vrai
# SceneManager.go(), donc pas de fil d'Ariane à afficher par-dessus.
BREADCRUMB_SKIP = {"menu", "continent", "runsetup", "sandbox", "splash", "intro", "gameover",
                   "desktop"}
BREADCRUMB_Y = 4


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (chrome UI)."""
    return en if get_lang() == "en" else fr


class Scene:
    """Classe de base. À hériter pour chaque écran."""

    # Si False, la scène ne peut pas être ouverte dans une page dédiée
    # (onglet) et bloque le changement d'onglet tant qu'elle est active.
    # Utilisé pour les scènes d'examen/certification (anti-triche).
    pageable = True

    def __init__(self, app):
        self.app = app          # référence à l'application (accès global)

    def on_enter(self, **kwargs):
        """Appelé quand la scène devient active."""
        pass

    def refresh_data(self):
        """Appelé quand la page contenant cette scène redevient active
        (changement d'onglet), pour rafraîchir les données mises en cache
        à l'on_enter (ex: catalogue boutique) sans réinitialiser l'état
        d'interface (scroll, recherche, filtres...). No-op par défaut :
        la plupart des scènes recalculent déjà tout en direct dans draw()."""
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


class SceneManager:
    """Gère la pile de scènes et les transitions (fondu au changement)."""

    FADE_TIME = 0.28   # durée du fondu d'entrée (secondes)

    def __init__(self, app):
        self.app = app
        self.scenes = {}
        self.current = None
        self.current_name = None
        self._fade = 0.0          # 1.0 = écran noir, 0.0 = pleinement visible
        self._overlay = None      # surface noire réutilisée pour le fondu
        self.palette_open = False
        self.palette_query = ""
        self.palette_sel = 0
        self.palette_recent = []   # [(label, scene, kw)] derniers choix (session courante)
        self.nav_stack = []        # [(scene, kwargs)] fil d'Ariane depuis "terminal"
        self._breadcrumb_rects = []  # [(Rect, scene, kwargs)] segments cliquables (hors dernier)

    def register(self, name, scene):
        self.scenes[name] = scene

    def back(self, name, **kwargs):
        """« Retour » (bouton précédent/continuer) : distinct de `go()` pour
        les scènes HÉBERGÉES en fenêtre (cf. apps/scene_host.py::_Router.back,
        qui ferme la fenêtre appelante plutôt que d'en ouvrir une autre — sinon
        cliquer « retour » vers ex. "terminal" ouvrait la fenêtre du terminal
        SANS fermer la fenêtre courante, un bug visible). Sur le vrai
        SceneManager (flux plein écran hors bureau, ou tests directs), il n'y
        a pas de fenêtre à fermer : `back()` se comporte donc comme `go()`,
        son comportement historique."""
        self.go(name, **kwargs)

    def go(self, name, **kwargs):
        if name not in self.scenes:
            raise KeyError(f"Scène inconnue : {name}")
        self._update_breadcrumb(name, kwargs)
        self.current = self.scenes[name]
        self.current_name = name
        self.current.on_enter(**kwargs)
        self._fade = 1.0          # déclenche le fondu d'entrée
        self.palette_open = False
        # pause automatique de l'horloge de jeu dès qu'on quitte la scène
        # principale (mission, examen, deal, dilemme...) ; reprise exacte au
        # retour, sans rattrapage — aucune minute de jeu n'est comptée
        # pendant l'absence (cf. core/sim_clock.py).
        clock = getattr(self.app, "sim_clock", None)
        if clock is not None:
            clock.set_auto_paused(name not in LIVE_SCENE_NAMES)

    # --- fil d'Ariane (breadcrumb) -----------------------------------------
    def _update_breadcrumb(self, name, kwargs):
        if name in BREADCRUMB_SKIP:
            self.nav_stack = []
            return
        if name == "terminal":
            self.nav_stack = [("terminal", {})]
            return
        for i, (n, _kw) in enumerate(self.nav_stack):
            if n == name:
                # on revient sur une scène déjà visitée (clic sur un segment,
                # ou navigation en boucle) : on tronque plutôt que d'empiler.
                self.nav_stack = self.nav_stack[:i + 1]
                return
        if not self.nav_stack:
            self.nav_stack = [("terminal", {})]
        self.nav_stack.append((name, dict(kwargs)))

    def _scene_label(self, name):
        if name == "terminal":
            return "Terminal"
        from core.app_catalog import SECTIONS
        for _title, items in SECTIONS:
            for label, scene_name, _kw, _desc in items:
                if scene_name == name:
                    return label
        return name.capitalize()

    def _draw_breadcrumb(self, surf):
        self._breadcrumb_rects = []
        if len(self.nav_stack) < 2:
            return
        font = fonts.tiny()
        x, y = 12, BREADCRUMB_Y
        n = len(self.nav_stack)
        for i, (name, kw) in enumerate(self.nav_stack):
            label = self._scene_label(name)
            is_last = (i == n - 1)
            col = config.COL_TEXT_DIM if is_last else config.COL_CYAN
            rect = widgets.draw_text(surf, label, (x, y), font, col)
            if not is_last:
                self._breadcrumb_rects.append((rect, name, kw))
            x = rect.right
            if not is_last:
                sep = widgets.draw_text(surf, " › ", (x, y), font, config.COL_TEXT_DIM)
                x = sep.right

    def _handle_breadcrumb_click(self, pos):
        for rect, name, kw in self._breadcrumb_rects:
            if rect.collidepoint(pos):
                self.go(name, **kw)
                return True
        return False

    # --- palette de navigation globale (Ctrl+K) ---------------------------
    def _palette_entries(self):
        from core import experience_mode
        from core.app_catalog import SECTIONS
        gs = getattr(self.app, "gs", None)
        player = getattr(gs, "player", None) if gs else None
        return [(label, scene, kw) for _, items in SECTIONS for (label, scene, kw, _desc) in items
                if player is None or not experience_mode.scene_hidden(scene, player)]

    def _palette_ticker_matches(self, query, limit=6):
        """Suggestions d'actifs (ticker/nom) correspondant à la saisie, pour
        sauter directement à la fiche d'analyse d'une société sans connaître
        son ticker — la palette devient aussi une recherche globale d'actifs."""
        market = getattr(self.app, "market", None)
        if market is None or not query.strip():
            return []
        hits = market.suggest(query, limit)
        return [(f"↗ {tk} — {name}", "company", {"ticker": tk}) for tk, name in hits]

    def _palette_glossary_matches(self, query, limit=4):
        """Suggestions de termes du glossaire correspondant à la saisie, pour
        ouvrir directement la définition sans passer par la scène glossaire."""
        from core.i18n import get_lang
        from data import glossary_data
        lang = get_lang()
        gloss, _cats = glossary_data.localized(lang)
        hits = fuzzy.filter_sorted(query, list(gloss.keys()), key=lambda t: t)[:limit]
        return [(f"[GLOS] {glossary_data.display_name(t, lang)}", "glossary", {"term": t}) for t in hits]

    def _palette_lesson_matches(self, query, limit=4):
        """Suggestions de leçons de l'Académie correspondant à la saisie."""
        from data import lessons as L
        hits = fuzzy.filter_sorted(query, L.LESSONS, key=lambda l: l["title"])[:limit]
        return [(f"[COURS] {l['title']}", "academy", {"lesson_id": l["id"]}) for l in hits]

    def _palette_action_matches(self, query, limit=6):
        """Actions rapides exécutables DIRECTEMENT depuis la palette, sans
        ouvrir de fenêtre — "vendre tout TICKER" pour chaque position tenue,
        cherchable par ticker OU par le mot "vendre"/"sell". Le libellé
        "→ Action" (préfixe ⚡) distingue visuellement une exécution
        immédiate d'une simple navigation. Un ordre à fort impact
        (`core.order_confirm`) retombe sur l'ouverture de Trading plutôt que
        de vendre en silence — même garde-fou que l'app Trading."""
        gs = getattr(self.app, "gs", None)
        player = getattr(gs, "player", None) if gs else None
        if player is None or not player.portfolio:
            return []
        tickers = list(player.portfolio.keys())
        haystack = [f"vendre {tk} sell {tk}" for tk in tickers]
        idx = fuzzy.filter_sorted(query, list(range(len(haystack))), key=lambda i: haystack[i])
        out = []
        for i in idx[:limit]:
            tk = tickers[i]
            qty = player.portfolio[tk]["shares"]
            out.append((f"⚡ Vendre tout : {tk} ({qty:g} titres)", "__sell_all__", {"ticker": tk}))
        return out

    def _palette_remember(self, label, scene, kw):
        """Mémorise un choix de palette (favoris récents, session courante) :
        plus récent en tête, sans doublon, plafonné à 5."""
        entry = (label, scene, kw)
        self.palette_recent = [e for e in self.palette_recent if e[:2] != (label, scene)]
        self.palette_recent.insert(0, entry)
        self.palette_recent = self.palette_recent[:5]

    def _palette_filtered(self):
        entries = self._palette_entries()
        q = self.palette_query.strip()
        if not q:
            return self.palette_recent + entries if self.palette_recent else entries
        scene_hits = fuzzy.filter_sorted(q, entries, key=lambda e: e[0])
        ticker_hits = self._palette_ticker_matches(q)
        gloss_hits = self._palette_glossary_matches(q)
        lesson_hits = self._palette_lesson_matches(q)
        action_hits = self._palette_action_matches(q)
        return action_hits + ticker_hits + gloss_hits + lesson_hits + scene_hits

    def open_palette(self):
        self.palette_open = True
        self.palette_query = ""
        self.palette_sel = 0

    def close_palette(self):
        self.palette_open = False

    def _palette_navigate(self, scene, kw):
        """Ouvre une entrée de palette : sur le BUREAU, en FENÊTRE (via
        App.route_scene, cohérent avec « tout se passe sur le bureau ») ;
        ailleurs, bascule plein écran classique. `scene == "__sell_all__"`
        est une ACTION exécutée directement (cf. `_palette_action_matches`),
        pas une navigation — jamais un simple `go()`."""
        if scene == "__sell_all__":
            self._palette_execute_sell_all(kw.get("ticker"))
            return
        if self.current_name == "desktop" and hasattr(self.app, "route_scene"):
            self.app.route_scene(scene, **kw)
        else:
            self.go(scene, return_to=self.current_name or "terminal", **kw)

    def _palette_execute_sell_all(self, ticker):
        """Vend l'intégralité d'une position depuis la palette — même
        garde-fou « ordre à fort impact » que l'app Trading
        (core.order_confirm) : au-delà du seuil, on ouvre Trading sur ce
        titre (pré-filtré) pour confirmation explicite plutôt que de vendre
        en silence."""
        from core import order_confirm
        from core import portfolio as pf_mod
        gs = getattr(self.app, "gs", None)
        market = getattr(self.app, "market", None)
        player = getattr(gs, "player", None) if gs else None
        if player is None or market is None or ticker not in player.portfolio:
            return
        pos = player.portfolio[ticker]
        price = market.price_of(ticker)
        notional = (price or 0) * pos["shares"]
        if order_confirm.needs_confirmation(player, market, notional):
            opener = getattr(self.current, "open_trading", None) if self.current_name == "desktop" else None
            if opener:
                opener(ticker)
            if hasattr(self.app, "notify"):
                self.app.notify(_L("Ordre important : confirmez dans Trading",
                                   "High-impact order: confirm in Trading"), "warn")
            return
        res = pf_mod.sell(player, market, ticker, "ALL")
        if hasattr(self.app, "notify"):
            if res.get("ok"):
                self.app.notify(_L(f"Vendu : {ticker} ({res['qty']:g} titres)",
                                   f"Sold: {ticker} ({res['qty']:g} shares)"), "good")
            else:
                self.app.notify(_L(f"Échec de la vente : {ticker}",
                                   f"Sell failed: {ticker}"), "bad")

    def _handle_palette_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            filtered = self._palette_filtered()
            box = pygame.Rect((config.SCREEN_WIDTH-PALETTE_W)//2,
                              (config.SCREEN_HEIGHT-PALETTE_H)//2, PALETTE_W, PALETTE_H)
            if not box.collidepoint(event.pos):
                self.close_palette()
                return
            list_y = box.y + 64
            for i, (label, scene, kw) in enumerate(filtered):
                row = pygame.Rect(box.x+10, list_y + i*PALETTE_ROW_H, box.w-20, PALETTE_ROW_H)
                if row.collidepoint(event.pos):
                    self._palette_remember(label, scene, kw)
                    self.close_palette()
                    self._palette_navigate(scene, kw)
                    return
            return
        if event.type != pygame.KEYDOWN:
            return
        filtered = self._palette_filtered()
        if event.key == pygame.K_ESCAPE:
            self.close_palette()
        elif event.key == pygame.K_BACKSPACE:
            self.palette_query = self.palette_query[:-1]
            self.palette_sel = 0
        elif event.key == pygame.K_DOWN:
            if filtered:
                self.palette_sel = (self.palette_sel + 1) % len(filtered)
        elif event.key == pygame.K_UP:
            if filtered:
                self.palette_sel = (self.palette_sel - 1) % len(filtered)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if filtered:
                label, scene, kw = filtered[self.palette_sel % len(filtered)]
                self._palette_remember(label, scene, kw)
                self.close_palette()
                self._palette_navigate(scene, kw)
        elif event.unicode and event.unicode.isprintable():
            self.palette_query += event.unicode
            self.palette_sel = 0

    def _draw_palette(self, surf):
        filtered = self._palette_filtered()
        self.palette_sel = min(self.palette_sel, max(0, len(filtered)-1))
        box = pygame.Rect((config.SCREEN_WIDTH-PALETTE_W)//2,
                          (config.SCREEN_HEIGHT-PALETTE_H)//2, PALETTE_W, PALETTE_H)
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surf.blit(shade, (0, 0))
        pygame.draw.rect(surf, config.COL_PANEL, box)
        pygame.draw.rect(surf, config.COL_CYAN, box, 2)
        widgets.draw_text(surf, "NAVIGATION (Ctrl+K)", (box.x+14, box.y+12),
                          fonts.small(bold=True), config.COL_CYAN)
        search_box = pygame.Rect(box.x+14, box.y+38, box.w-28, 26)
        pygame.draw.rect(surf, (6, 8, 12), search_box)
        pygame.draw.rect(surf, config.COL_BORDER, search_box, 1)
        widgets.draw_text(surf, self.palette_query or "tapez pour filtrer…", (search_box.x+8, search_box.y+5),
                          fonts.small(), config.COL_WHITE if self.palette_query else config.COL_TEXT_DIM)
        list_y = box.y + 64
        max_rows = (box.bottom - 10 - list_y) // PALETTE_ROW_H
        if not filtered:
            widgets.draw_text(surf, "Aucun résultat.", (box.x+14, list_y+6),
                              fonts.small(), config.COL_TEXT_DIM)
        for i, (label, scene, kw) in enumerate(filtered[:max_rows]):
            row = pygame.Rect(box.x+10, list_y + i*PALETTE_ROW_H, box.w-20, PALETTE_ROW_H)
            if i == self.palette_sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
                pygame.draw.rect(surf, config.COL_CYAN, row, 1)
            widgets.draw_text(surf, label, (row.x+8, row.y+6), fonts.small(), config.COL_TEXT)
        if len(filtered) > max_rows:
            widgets.draw_text(surf, f"… et {len(filtered)-max_rows} autre(s)",
                              (box.x+14, box.bottom-22), fonts.tiny(), config.COL_TEXT_DIM)

    # touches 1/2/3 -> SAVE_SLOTS[0..2] (CTRL+chiffre = sauvegarder,
    # CTRL+SHIFT+chiffre = charger), accessibles depuis n'importe quel écran
    # pageable (mêmes raccourcis que SAVE/scene_saves, juste plus rapides).
    QUICKSLOT_KEYS = {
        pygame.K_1: 0, pygame.K_KP1: 0,
        pygame.K_2: 1, pygame.K_KP2: 1,
        pygame.K_3: 2, pygame.K_KP3: 2,
    }

    def _handle_quickslot(self, event):
        idx = self.QUICKSLOT_KEYS.get(event.key)
        if idx is None or not (event.mod & pygame.KMOD_CTRL):
            return False
        cur = self.current
        if cur is not None and not getattr(cur, "pageable", True):
            return False
        slot = config.SAVE_SLOTS[idx]
        if event.mod & pygame.KMOD_SHIFT:
            self._quickslot_load(slot)
        else:
            self._quickslot_save(slot)
        return True

    def _quickslot_save(self, slot):
        p = self.app.gs.player
        if p.hardcore:
            self.app.notify(_L("Mode hardcore : sauvegarde manuelle désactivée.",
                               "Hardcore mode: manual save disabled."), "warn")
            return
        self.app.gs.save(slot)
        self.app.notify(_L(f"Sauvegardé sur {slot.upper()}.", f"Saved to {slot.upper()}."), "good")

    def _dispatch_notification_action(self, action, action_kwargs):
        """Construit un callback qui exécute l'action d'une notification.
        Retourne None si l'action n'est pas reconnaissable."""
        if not action:
            return None
        kwargs = dict(action_kwargs or {})

        def cb():
            try:
                if action == "trading":
                    self.app.route_scene("trading", ticker=kwargs.get("ticker"))
                elif action == "book":
                    self.app.route_scene("book")
                elif action == "sheet":
                    self.app.route_scene("spreadsheet")
                elif action == "scene":
                    name = kwargs.get("name")
                    if name:
                        self.app.route_scene(name, **{k: v for k, v in kwargs.items()
                                                       if k != "name"})
                else:
                    self.app.route_scene(action, **kwargs)
            except Exception:
                crashlog.swallowed("core.scene_manager")

        return cb

    def _quickslot_load(self, slot):
        from core.game_state import GameState
        gs = GameState.load(slot)
        if not gs:
            self.app.notify(_L(f"Aucune sauvegarde sur {slot.upper()}.",
                               f"No save on {slot.upper()}."), "warn")
            return
        self.app.gs = gs
        gs.attach_app(self.app)
        ui_state.load(slot, self.app)
        self.app.ensure_market()
        self.close_palette()
        self.go("gameover" if gs.player.game_over else "desktop")
        self.app.notify(_L(f"Chargé depuis {slot.upper()}.", f"Loaded from {slot.upper()}."), "good")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in self.QUICKSLOT_KEYS:
            if self._handle_quickslot(event):
                return
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_k
                and (event.mod & pygame.KMOD_CTRL)):
            if self.palette_open:
                self.close_palette()
            else:
                self.open_palette()
            return
        if self.palette_open:
            self._handle_palette_event(event)
            return
        # notifications/toasts cliquables (sous la palette, au-dessus de la scène)
        notes = getattr(self.app, "notes", None)
        if notes and notes.handle_event(event):
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self._handle_breadcrumb_click(event.pos)):
            return
        # on ignore les entrées pendant le tout début du fondu pour éviter
        # les clics fantômes hérités de la scène précédente
        if self.current and self._fade < 0.6:
            self.current.handle_event(event)

    def update(self, dt):
        if self._fade > 0.0:
            self._fade = max(0.0, self._fade - dt / self.FADE_TIME)
        if self.current:
            self.current.update(dt)
        # toasts différés émis par la logique pure (advance_step, mandats...)
        player = getattr(getattr(self.app, "gs", None), "player", None)
        if player is not None:
            from core import notify_queue
            for toast in notify_queue.drain(player):
                on_click = self._dispatch_notification_action(
                    toast.get("action"), toast.get("action_kwargs"))
                self.app.notify(toast["text"], toast["kind"],
                                action=toast.get("action"),
                                action_kwargs=toast.get("action_kwargs"),
                                on_click=on_click)
        notes = getattr(self.app, "notes", None)
        if notes:
            notes.update(dt)

    def draw(self, surf):
        if not self.current:
            return
        self.current.draw(surf)
        self._draw_breadcrumb(surf)
        # overlay : notifications (toasts) au-dessus de la scène, sous le fondu
        notes = getattr(self.app, "notes", None)
        if notes:
            notes.draw(surf)
        if self.palette_open:
            self._draw_palette(surf)
        if self._fade > 0.0:
            if self._overlay is None or self._overlay.get_size() != surf.get_size():
                self._overlay = pygame.Surface(surf.get_size())
                self._overlay.fill(config.COL_BG)
            self._overlay.set_alpha(int(255 * self._fade))
            surf.blit(self._overlay, (0, 0))
