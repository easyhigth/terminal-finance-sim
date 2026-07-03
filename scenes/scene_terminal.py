"""
scene_terminal.py — Le terminal principal (style Bloomberg).
Disposition :
  - Bandeau supérieur : identité, grade, cash, jour/trimestre, réputation, devise
  - Ticker défilant (indices réels du moteur de marché)
  - Colonne gauche : Indices mondiaux (sparklines) + Santé/Portefeuille
  - CENTRE : carte du monde (actus qui poppent par région) + flux d'actualités
  - Colonne droite : Top sociétés de la région + Carrière / deals
  - Ligne de commande en bas

Tout se pilote au clavier. COMMANDS affiche le catalogue complet.
"""
import pygame

from core import audio, config
from core import career as career_mod
from core import market_hours as mh_mod
from core import news as news_mod
from core import onboarding as onboarding_mod
from core import portfolio as pf_mod
from core import portfolio_views as pv_mod
from core import rivals as rivals_mod
from core import unlocks as unlocks_mod
from core.i18n import get_lang
from core.scene_manager import Scene
from scenes.scene_terminal_career import TerminalCareerMixin
from scenes.scene_terminal_commands import TerminalCommandsMixin
from scenes.scene_terminal_market import TerminalMarketMixin
from scenes.scene_terminal_render import TerminalRenderMixin
from scenes.scene_terminal_time import TerminalTimeMixin
from scenes.scene_terminal_trading import TerminalTradingMixin
from scenes.scene_terminal_windows import TerminalWindowsMixin


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr
from ui import keynav, widgets
from ui.worldmap import WorldMap

# Raccourcis directs Ctrl+<lettre> vers les accès rapides (ex-rail latéral,
# désormais icônes du bureau — mêmes mnémoniques que DESKTOP_SHORTCUTS de
# scenes/scene_desktop.py, garder synchronisé). Les
# lettres simples et Maj+lettre sont réservées à la saisie au clavier dans la
# ligne de commande (cf. handle_event, fallback unicode imprimable) — Ctrl
# est donc le seul modificateur disponible pour des déclencheurs instantanés
# sans ambiguïté. Mnémonique en priorité (M=Marché, P=Portefeuille…), avec un
# repli logique quand la lettre attendue est déjà prise par une autre entrée
# (ex. Mandats → A, M&A → F pour Fusions). Documenté dans
# data/shortcuts_data.py (cf. ShortcutsPanel) — garder synchronisé.
RAIL_SHORTCUTS = {
    pygame.K_m: "MARKETHUB",
    pygame.K_p: "PORTFOLIO",
    pygame.K_i: "INBOX",
    pygame.K_n: "NEWS",
    pygame.K_j: "MISSION",
    pygame.K_a: "MANDATES",
    pygame.K_d: "DEALS",
    pygame.K_f: "MA",
    pygame.K_e: "DECIDE",
    pygame.K_x: "EXAMCERT",
    pygame.K_b: "SHOP",
    pygame.K_t: "SHEET",
    pygame.K_l: "LEARN",
    pygame.K_g: "GLOSSARY",
    pygame.K_o: "MORE",
    pygame.K_s: "SAVE",
    pygame.K_h: "COMMANDS",
}

# Raccourcis Ctrl+Maj+<lettre> vers les pages qui ne sont QUE dans la scène
# PLUS (pas de rang dans le rail). Modificateur double pour ne jamais entrer
# en conflit ni avec RAIL_SHORTCUTS (Ctrl seul) ni avec la saisie de commandes
# en Maj (BUY, SELL...). Couvre les destinations les plus utiles ; le reste
# des pages PLUS reste à une commande tapée ou à Ctrl+O (MORE) + flèches.
# Documenté dans data/shortcuts_data.py — garder synchronisé.
MORE_SHORTCUTS = {
    pygame.K_e: "EXPLORE",
    pygame.K_c: "CAREER",
    pygame.K_b: "BOOK",
    pygame.K_h: "TIMELINE",
    pygame.K_t: "TEAM",
    pygame.K_r: "RISK",
    pygame.K_a: "AGENDA",
    pygame.K_v: "REVIEW",
    pygame.K_l: "RIVALS",
    pygame.K_s: "STRESS",
    pygame.K_w: "SAVES",
    pygame.K_o: "TRACK",
}

# ordre de parcours Tab des blocs du terminal (sens horaire approximatif) ;
# la navigation aux flèches utilise la position réelle des blocs
# (cf. ui/keynav.nearest_in_direction), Tab suit cet ordre fixe.
ZONE_ORDER = ["console", "indices", "health", "topco", "career", "feed"]

SAMPLE_NEWS = {
    "Europe": ["BCE : statu quo, marché partagé sur le calendrier des baisses.",
               "MiFID II : reporting renforcé pour les buy-side.",
               "Spread OAT-Bund stable après adjudication."],
    "USA": ["Fed : ton jugé prudent par les analystes.",
            "Saison des résultats : la tech surprend à la hausse.",
            "SEC : vigilance accrue sur le short-selling."],
    "Asia": ["HKMA défend le peg du HKD.",
             "BoJ surveille la devise ; intervention possible.",
             "Flux transfrontaliers sous contrôle renforcé."],
}


class TerminalScene(TerminalMarketMixin, TerminalTradingMixin, TerminalCareerMixin,
                     TerminalTimeMixin, TerminalRenderMixin, TerminalCommandsMixin,
                     TerminalWindowsMixin, Scene):
    def on_enter(self, **kwargs):
        self.t = 0.0
        self.cmd = ""
        self.entered = []          # historique des commandes saisies (↑/↓)
        self.hist_pos = None
        # journal de la console : conservé entre les allers-retours (scrollback),
        # réinitialisé seulement sur une nouvelle partie.
        p0 = self.app.gs.player
        fresh = (p0.day == 1 and not p0.cash_history)
        if not hasattr(self, "cmd_history") or fresh:
            self.cmd_history = ["> Bienvenue. Tapez HELP, ou COMMANDS pour tout voir."]
        self.console_expanded = getattr(self, "console_expanded", False)
        self.console_scroll = 0    # 0 = bas (dernier message) ; >0 = remonte
        self._console_rect_cache = None
        self._console_btns = {}
        # commande pré-remplie depuis le catalogue (clic « copier »)
        pending = getattr(self.app, "pending_input", None)
        if pending:
            self.cmd = pending
            self.app.pending_input = None
        p = self.app.gs.player
        if p.cash == 0 and p.day == 1 and not p.cash_history:
            p.cash = config.START_CASH
            p.cash_history = [p.cash]
        # marché déterministe (créé/synchronisé)
        self.market = self.app.ensure_market()
        # scénario « krach de départ » : on injecte un choc une seule fois
        if p.flags.get("start_crisis") and not p.flags.get("start_crisis_done"):
            from core.market import Crisis
            self.market.add_crisis(Crisis("Krach de départ", steps=6,
                                          world=-0.05, vol_mult=2.2))
            p.flags["start_crisis_done"] = True
        career_mod.ensure_objectives(p)   # objectifs du trimestre courant
        rivals_mod.ensure(p)              # concurrents
        self._check_badges()              # badges éventuellement franchis ailleurs
        self.worldmap = WorldMap()
        # restaure les marqueurs persistants des news du jour courant (reprise de save)
        self.worldmap.set_day_markers(news_mod.for_day(p, p.day))
        self.news = list(SAMPLE_NEWS.get(p.continent, SAMPLE_NEWS["USA"]))
        self.recent_events = []
        if not hasattr(self, "datawins"):
            self.datawins = []        # fenêtres de données déplaçables (overlay)
            self._restore_workspace()
        self.shortcuts_panel = None   # panneau des raccourcis clavier (overlay)
        # navigation hiérarchique au clavier : pile de focus bloc → contenu
        # interne (cf. ui/keynav.ZoneStack). Par défaut le focus reste « dans »
        # la console comme avant (saisie immédiate), Échap permet de remonter
        # au niveau bloc pour naviguer le reste du terminal aux flèches/Tab.
        # Préservé entre deux passages par le terminal (ex. on quitte le bloc
        # RAIL pour ouvrir une page puis on revient : le focus clavier reste là
        # où le joueur l'avait laissé, sauf au tout premier on_enter).
        if not hasattr(self, "zones"):
            self.zones = keynav.ZoneStack(ZONE_ORDER)
            self.zones.inside = True
        self._zone_rects = {}     # rects des blocs (zone -> Rect), pour les flèches
        self._topco_rects = {}    # sociétés cliquables (panneau top sociétés)
        self._topco_header_rect = None   # titre du panneau (clic → explorateur)
        self._topco_panel_rect = None    # zone défilable (molette)
        self._topco_scroll = 0
        self._topco_max_scroll = 0
        self._topco_sort_rects = {}    # en-têtes de colonne triables (panneau top sociétés)
        if not hasattr(self, "_topco_sort_key"):
            self._topco_sort_key = "mktcap"   # préservé entre deux passages par le terminal
            self._topco_sort_rev = True
        self._index_rects = {}    # indices cliquables (panneau indices → graphe)
        self._indices_header_rect = None  # titre du panneau (clic → MARKETHUB)
        self._indices_panel_rect = None   # zone défilable (molette)
        self._indices_scroll = 0
        self._indices_max_scroll = 0
        if not hasattr(self, "_index_flash"):
            self._index_flash = widgets.TickFlash()   # flash vert/rouge du tick en direct
        if not hasattr(self, "_pnl_sign"):
            self._pnl_sign = {}   # signe du P&L latent par ticker, pour notifier un franchissement
        if not hasattr(self, "_session_open"):
            self._session_open = None   # état d'ouverture des sessions régionales (cloche)
        if not hasattr(self, "_session_day"):
            self._session_day = None    # jour de jeu courant (résumé de séance)
            self._day_start_nw = 0.0
        self._career_panel_rect = None   # panneau CARRIÈRE (ex-priorités) → scène carrière
        self._career_content_rect = None  # zone défilable (molette)
        self._career_scroll = 0
        self._career_max_scroll = 0
        self._feed_header_rect = None    # panneau FLUX & ÉVÉNEMENTS → scène historique
        self._onboarding_skip_rect = None  # bouton « passer » du bandeau d'intégration
        self._map_rect = None     # rect de la carte (pour le clic)
        # le rail latéral de commandes rapides a été retiré (refonte UI « Jeu
        # PC ») : ces accès sont désormais des ICÔNES DU BUREAU, ouvertes en
        # fenêtre au même titre que les autres apps (cf.
        # scenes/scene_desktop.py::QUICK_APP). Les raccourcis Ctrl+<lettre>
        # (RAIL_SHORTCUTS, ci-dessus) restent fonctionnels : ils appellent
        # directement _run_command(), indépendamment de tout bouton visuel.
        self.networth_spark = widgets.Sparkline(80)
        for v in p.cash_history[-80:]:
            self.networth_spark.push(v)
        if not p.cash_history:
            self.networth_spark.push(p.cash)
        # une tâche longue (mission / deal / éval) fait passer le temps : les pas
        # bancarisés par l'horloge pendant l'absence (cf. core/sim_clock.py) sont
        # joués ici, au retour sur le terminal.
        if getattr(self.app, "pending_market_steps", 0) and not p.game_over:
            self._log(_L("  ⏱ Le temps a avancé pendant que vous travailliez…",
                          "  ⏱ Time advanced while you were working…"))
            self._drain_pending_steps()
        # tutoriel auto-déclenché à l'unlock d'une fonctionnalité (cf. scene_evaluation._finish)
        tid = p.flags.pop("pending_tutorial", None)
        if tid:
            self.app.scenes.go("tutorials", tid=tid, return_to="terminal")

    # --------------------------------------------------------------- events
    def handle_event(self, event):
        # 0) panneau des raccourcis clavier : priorité sur tout le reste
        if self.shortcuts_panel is not None:
            if self.shortcuts_panel.handle(event):
                if self.shortcuts_panel.closed:
                    self.shortcuts_panel = None
                return
        # 1) fenêtres de données déplaçables (la plus au-dessus d'abord)
        for w in reversed(self.datawins):
            if w.handle(event):
                if w.clicked_row is not None:
                    self._datawin_row_click(w, w.clicked_row)
                    w.clicked_row = None
                if getattr(w, "expand_requested", False):
                    w.expand_requested = False
                    self._open_chart_popup(w.ticker, kind=w.kind)
                tk = getattr(w, "open_ticker", None)
                if tk:
                    w.open_ticker = None
                    self._open_company_popup(tk)
                nav = getattr(w, "nav_request", None)
                if nav:
                    w.nav_request = None
                    nav = dict(nav)
                    target = nav.pop("to")
                    nav["return_to"] = "terminal"
                    self.app.scenes.go(target, **nav)
                    return
                self.datawins = [x for x in self.datawins if not x.closed]
                return
        # 1bis) molette : console, panneau indices, panneau top sociétés
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            mp = pygame.mouse.get_pos()
            if self._console_rect().collidepoint(mp):
                self._scroll_console(3 if event.button == 4 else -3)
                return
            if self._indices_panel_rect and self._indices_panel_rect.collidepoint(mp):
                self._indices_scroll = max(0, min(self._indices_max_scroll,
                    self._indices_scroll + (-32 if event.button == 4 else 32)))
                return
            if self._topco_panel_rect and self._topco_panel_rect.collidepoint(mp):
                self._topco_scroll = max(0, min(self._topco_max_scroll,
                    self._topco_scroll + (-28 if event.button == 4 else 28)))
                return
            if self._career_content_rect and self._career_content_rect.collidepoint(mp):
                self._career_scroll = max(0, min(self._career_max_scroll,
                    self._career_scroll + (-28 if event.button == 4 else 28)))
                return
        # 2) souris : boutons console + carte
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._onboarding_skip_rect and self._onboarding_skip_rect.collidepoint(event.pos):
                onboarding_mod.skip(self.app.gs.player)
                return
            for key, rect in self._console_btns.items():
                if rect.collidepoint(event.pos):
                    if key == "expand":
                        self.console_expanded = not self.console_expanded
                        self.console_scroll = min(self.console_scroll, self._console_max_scroll())
                    elif key == "up":
                        self._scroll_console(3)
                    elif key == "down":
                        self._scroll_console(-3)
                    return
            if self._topco_header_rect and self._topco_header_rect.collidepoint(event.pos):
                self.app.scenes.go("explorer", return_to="terminal")
                return
            for key, rect in self._topco_sort_rects.items():
                if rect.collidepoint(event.pos):
                    if self._topco_sort_key == key:
                        self._topco_sort_rev = not self._topco_sort_rev
                    else:
                        self._topco_sort_key = key
                        self._topco_sort_rev = key != "ticker"
                    return
            if self._indices_header_rect and self._indices_header_rect.collidepoint(event.pos):
                self.app.scenes.go("markethub", return_to="terminal")
                return
            if self._career_panel_rect and self._career_panel_rect.collidepoint(event.pos):
                self.app.scenes.go("career", return_to="terminal")
                return
            if getattr(self, "_feed_header_rect", None) and self._feed_header_rect.collidepoint(event.pos):
                self.app.scenes.go("history", return_to="terminal")
                return
            if getattr(self, "_health_rect", None) and self._health_rect.collidepoint(event.pos):
                self.app.scenes.go("book", return_to="terminal")
                return
            for tk, rect in self._topco_rects.items():
                if rect.collidepoint(event.pos):
                    self._open_company_popup(tk)
                    return
            for name, rect in self._index_rects.items():
                if rect.collidepoint(event.pos):
                    self._open_index_chart(name)
                    return
            if getattr(self, "_map_rect", None):
                action = self.worldmap.handle_click(event.pos, self._map_rect, self.market)
                if action and action[0] == "company":
                    self._open_company_popup(action[1])
                    return
                if action and action[0] == "news":
                    self._open_news_window(action[1])
                    return
                if action:
                    return
        # 3) clavier : raccourcis globaux, navigation de blocs, ligne de commande
        if event.type == pygame.KEYDOWN:
            ctrl = bool(event.mod & pygame.KMOD_CTRL)
            shift = bool(event.mod & pygame.KMOD_SHIFT)
            # Ctrl+Shift+<lettre> : raccourcis vers les pages de la scène PLUS
            # (Ctrl seul est réservé au rail, cf. RAIL_SHORTCUTS plus bas).
            if ctrl and shift and event.key in MORE_SHORTCUTS:
                self._run_command(MORE_SHORTCUTS[event.key])
                return
            # Ctrl+<lettre> : raccourcis directs vers les accès rapides
            if ctrl and not shift and event.key in RAIL_SHORTCUTS:
                cmd = RAIL_SHORTCUTS[event.key]
                if unlocks_mod.cmd_unlocked(self.app.gs.player, cmd):
                    self._run_command(cmd)
                return

            # navigation hiérarchique des blocs (panneaux) : tant que le
            # focus est « dans » la ligne de commande, elle capte la saisie
            # comme avant (comportement historique, zéro régression) ; Échap
            # remonte au niveau bloc d'où l'on peut naviguer aux flèches.
            if self.zones.zone == "console" and self.zones.inside:
                if event.key == pygame.K_RETURN:
                    self._run_command(self.cmd.strip())
                    self.cmd = ""
                    self.hist_pos = None
                elif event.key == pygame.K_BACKSPACE:
                    self.cmd = self.cmd[:-1]
                elif event.key == pygame.K_ESCAPE:
                    if self.datawins:
                        self.datawins.pop()
                    else:
                        self.zones.escape()
                elif event.key == pygame.K_UP:
                    self._recall(-1)
                elif event.key == pygame.K_DOWN:
                    self._recall(1)
                elif event.key == pygame.K_PAGEUP:
                    self._scroll_console(self._console_visible_lines() - 1)
                elif event.key == pygame.K_PAGEDOWN:
                    self._scroll_console(-(self._console_visible_lines() - 1))
                elif event.key == pygame.K_TAB:
                    self._autocomplete()
                elif event.key == pygame.K_SPACE and not self.cmd:
                    # barre d'espace, ligne de commande vide → pause/reprise du
                    # jeu (raccourci naturel ; n'interfère jamais avec la saisie
                    # de commandes à espaces type « BUY AAPL 100 », non vides).
                    self.app.sim_clock.toggle_pause()
                else:
                    if event.unicode and event.unicode.isprintable():
                        self.cmd += event.unicode
                        self.hist_pos = None
                return

            # niveau « blocs » : Échap remonte / sort, Tab change de zone,
            # les flèches déplacent le focus selon la position visuelle réelle
            # des blocs, Entrée descend dans le bloc puis active son item.
            if event.key == pygame.K_ESCAPE:
                if self.datawins:
                    self.datawins.pop()
                elif not self.zones.escape():
                    self.app.scenes.go("menu")
                return
            if event.key == pygame.K_TAB:
                self.zones.cycle_zone(-1 if shift else 1)
                return
            if event.key in keynav.DIRECTIONS:
                direction = keynav.DIRECTIONS[event.key]
                if not self.zones.inside:
                    self.zones.move_zone(self._zone_rects, direction)
                else:
                    items = self._zone_items(self.zones.zone)
                    if items:
                        self.zones.item = keynav.nearest_in_direction(
                            items, self.zones.item, direction)
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._activate_zone()
                return

    def _zone_items(self, zone):
        """Items navigables aux flèches à l'intérieur d'un bloc (id -> Rect)."""
        if zone == "indices":
            return dict(self._index_rects)
        if zone == "topco":
            return dict(self._topco_rects)
        return {}

    def _focus_hints(self):
        """Raccourcis pertinents pour le focus clavier courant, affichés en
        bandeau discret au-dessus de la ligne de commande (cf.
        ui/widgets.draw_hint_bar). Vide en mode saisie console : la console
        est déjà auto-explicative (CMD> + curseur clignotant)."""
        z = self.zones.zone
        if z == "console" and self.zones.inside:
            return []
        enter_key = _L("ENTRÉE", "ENTER")
        esc_key = _L("ÉCHAP", "ESC")
        if not self.zones.inside:
            return [("↑↓←→", _L("blocs", "blocks")), (enter_key, _L("entrer", "enter")),
                    ("TAB", _L("suivant", "next")), (esc_key, _L("menu", "menu"))]
        if z in ("indices", "topco"):
            return [("↑↓←→", _L("items", "items")), (enter_key, _L("activer", "activate")),
                    (esc_key, _L("bloc", "block"))]
        return []

    def _activate_zone(self):
        """Entrée au clavier : descend dans le bloc focalisé (1ʳᵉ pression),
        puis active l'item interne focalisé (2ᵉ pression) — navigation
        hiérarchique bloc → contenu interne."""
        z = self.zones.zone
        if not self.zones.inside:
            if z in ("indices", "topco"):
                items = self._zone_items(z)
                if items:
                    self.zones.enter()
                    self.zones.item = next(iter(items))
            elif z == "console":
                self.zones.enter()
            elif z == "health":
                self.app.scenes.go("book", return_to="terminal")
            elif z == "career":
                self.app.scenes.go("career", return_to="terminal")
            elif z == "feed":
                self.app.scenes.go("history", return_to="terminal")
            return
        if z == "indices" and self.zones.item is not None:
            self._open_index_chart(self.zones.item)
        elif z == "topco" and self.zones.item is not None:
            self._open_company_popup(self.zones.item)

    def _toggle_shortcuts_panel(self):
        """Ouvre/ferme le panneau listant tous les raccourcis clavier."""
        if self.shortcuts_panel is None:
            from ui.shortcutspanel import ShortcutsPanel
            self.shortcuts_panel = ShortcutsPanel()
        else:
            self.shortcuts_panel = None

    def _log(self, *lines):
        self.cmd_history += list(lines)
        self.cmd_history = self.cmd_history[-400:]   # backlog défilable
        self.console_scroll = 0                       # revient au bas (dernier message)

    def _recall(self, direction):
        """Navigue dans l'historique des commandes saisies (↑ = -1, ↓ = +1)."""
        if not self.entered:
            return
        if self.hist_pos is None:
            self.hist_pos = len(self.entered)
        self.hist_pos = max(0, min(len(self.entered), self.hist_pos + direction))
        self.cmd = self.entered[self.hist_pos] if self.hist_pos < len(self.entered) else ""

    def update(self, dt):
        self.t += dt
        self.worldmap.update(dt)
        onboarding_mod.progress(self.app.gs.player, self.app)
        self._sync_workspace()
        self._drain_pending_steps()
        self._check_pnl_threshold()
        self._check_market_clock()

    def _check_pnl_threshold(self):
        """Notifie un toast quand le P&L latent d'une position franchit le
        seuil de signe (passe en perte ou en gain) pendant qu'on regarde le
        marché en direct — purement informatif, n'affecte aucun ordre."""
        m = self.app.market
        if not m:
            return
        for h in pv_mod.holdings(self.app.gs.player, m):
            tk, pnl = h["ticker"], h["pnl"]
            sign = 1 if pnl > 0 else (-1 if pnl < 0 else 0)
            prev = self._pnl_sign.get(tk)
            if prev is not None and sign != 0 and prev != sign and prev != 0:
                if sign > 0:
                    self.app.notify(f"{tk} : position repassée en gain latent ({pnl:+,.0f})", "good")
                else:
                    self.app.notify(f"{tk} : position repassée en perte latente ({pnl:+,.0f})", "warn")
            self._pnl_sign[tk] = sign
        for tk in list(self._pnl_sign):
            if tk not in self.app.gs.player.portfolio:
                del self._pnl_sign[tk]

    def _check_market_clock(self):
        """Cloche d'ouverture/fermeture des sessions régionales (toast + son)
        et résumé de séance au changement de jour de jeu — purement
        informatif, ne touche ni au marché ni aux ordres."""
        m = self.app.market
        if not m:
            return
        p = self.app.gs.player
        labels = mh_mod.session_labels(get_lang())
        # sessions par pas : 2 ouvertes / 1 fermée, en rotation. On signale la
        # bascule (une place ferme, une autre rouvre) à chaque changement de pas.
        cur = {s: mh_mod.is_session_open(s, m.step_count) for s in mh_mod.SESSIONS}
        if self._session_open is not None:
            for s, is_open in cur.items():
                was = self._session_open.get(s, True)
                if is_open and not was:
                    audio.play("bell")
                    self.app.notify(_L(f"🔔 Ouverture {labels[s]}", f"🔔 {labels[s]} open"), "good")
                elif was and not is_open:
                    self.app.notify(_L(f"🔔 Clôture {labels[s]}", f"🔔 {labels[s]} close"), "info")
        self._session_open = cur
        # résumé de séance : émis une fois par changement de jour de jeu
        day = self.app.sim_clock.current_time(p.day)[0]
        if self._session_day is None:
            self._session_day, self._day_start_nw = day, pf_mod.net_worth(p, m)
        elif day != self._session_day:
            self._emit_day_summary()
            self._session_day, self._day_start_nw = day, pf_mod.net_worth(p, m)

    def _emit_day_summary(self):
        """Toast de fin de séance : variation de valeur nette + meilleure/pire
        position latente du jour (réutilise portfolio_views.holdings)."""
        m, p = self.app.market, self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        delta = pf_mod.net_worth(p, m) - getattr(self, "_day_start_nw", 0.0)
        sign = "+" if delta >= 0 else ""
        msg = _L(f"Séance close · valeur nette {sign}{widgets.format_money(delta, cur)}",
                 f"Session close · net worth {sign}{widgets.format_money(delta, cur)}")
        hs = [h for h in pv_mod.holdings(p, m) if h.get("pnl_pct") is not None]
        if hs:
            best = max(hs, key=lambda h: h["pnl_pct"])
            worst = min(hs, key=lambda h: h["pnl_pct"])
            msg += (f" · {best['ticker']} {best['pnl_pct']:+.1f}%"
                    f" · {worst['ticker']} {worst['pnl_pct']:+.1f}%")
        self.app.notify(msg, "good" if delta >= 0 else "warn")

    # ----------------------------------------------------------------- draw
