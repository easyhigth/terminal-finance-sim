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

from core import career as career_mod
from core import config
from core import news as news_mod
from core import rivals as rivals_mod
from core import unlocks as unlocks_mod
from core.i18n import get_lang
from core.scene_manager import Scene
from scenes.scene_terminal_commands import TerminalCommandsMixin
from scenes.scene_terminal_render import TerminalRenderMixin


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr
from ui import widgets
from ui.worldmap import WorldMap

# Noms de commandes pour l'autocomplétion (Tab) et la suggestion fantôme
CMD_NAMES = [
    "HELP", "COMMANDS", "ADV", "MISSION", "EVAL", "EXAMCERT", "TRACK", "CAREER", "INBOX",
    "RIVALS", "MANDATES", "MANDATE", "DECIDE", "MARKET", "MARKETHUB", "TOP", "MOVERS",
    "COMPANY", "FA", "SEARCH", "ACCESS", "EXPLORE", "SHOP", "WATCHLIST", "COMPARE", "SECTOR", "REGION", "SCREEN",
    "RANKING", "BENCHMARK", "CALENDAR", "RESEARCH", "ALERT", "ALERTS",
    "PORTFOLIO", "BOOK", "BUY", "SELL", "LONG", "SHORT", "COVER", "MARGIN",
    "BONDS", "BUYBOND", "SELLBOND", "GOV", "GOVERNMENTS", "PAYS",
    "CMDTY", "BUYCMDTY", "SELLCMDTY",
    "CRYPTO", "BUYCRYPTO", "SELLCRYPTO", "ETF", "ETFS", "BUYETF", "SELLETF",
    "STRUCT", "CREDIT", "ALM", "SWAP", "SWAPS",
    "ALLOCATE", "HEDGE", "PROTECT", "OPTIONS", "IPO", "FX", "AGENDA", "PRONOS", "REVIEW", "REBALANCE",
    "PITCH", "FRONTIER", "RISK", "QUANT", "MA", "SHEET", "GLOSSARY",
    "SAVE", "SAVES", "NEWS", "MORE", "REG", "STATUS", "MENU",
    "TEAM", "EQUIPE", "STRESS", "TIMELINE",
    "GP", "GPC", "GPO", "GPCH", "COMP", "HS", "HVOL", "BETA", "CORR",
    "GEG", "GC", "RV", "ECO", "DEFINE", "PA",
]

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


class TerminalScene(TerminalCommandsMixin, TerminalRenderMixin, Scene):
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
        self.datawins = []        # fenêtres de données déplaçables (overlay)
        self.cheat_panel = None   # panneau de triche (overlay, mode test uniquement)
        self._cheat_btn_rect = None
        self._rail_rects = {}     # boutons du rail latéral (label -> Rect)
        self._topco_rects = {}    # sociétés cliquables (panneau top sociétés)
        self._topco_header_rect = None   # titre du panneau (clic → explorateur)
        self._topco_panel_rect = None    # zone défilable (molette)
        self._topco_scroll = 0
        self._topco_max_scroll = 0
        self._index_rects = {}    # indices cliquables (panneau indices → graphe)
        self._indices_header_rect = None  # titre du panneau (clic → MARKETHUB)
        self._indices_panel_rect = None   # zone défilable (molette)
        self._indices_scroll = 0
        self._indices_max_scroll = 0
        self._career_panel_rect = None   # panneau CARRIÈRE (ex-priorités) → scène carrière
        self._feed_header_rect = None    # panneau FLUX & ÉVÉNEMENTS → scène historique
        self.rail_w = 150         # largeur du rail latéral
        self._map_rect = None     # rect de la carte (pour le clic)
        # rail latéral : (libellé, commande), regroupé par usage
        self.rail = [
            ("ADV ▸", "ADV"),
            ("PORTEF.", "PORTFOLIO"), ("MARCHÉ", "MARKETHUB"), ("SHOP", "SHOP"),
            ("MISSION", "MISSION"), ("EXAM/CERTIF", "EXAMCERT"),
            ("MANDATS", "MANDATES"), ("DEALS", "DEALS"), ("M&A", "MA"),
            ("INBOX", "INBOX"), ("NEWS", "NEWS"), ("DÉCIDE", "DECIDE"),
            ("TABLEUR", "SHEET"), ("ACADÉMIE", "LEARN"),
            ("GLOSSAIRE", "GLOSSARY"), ("PLUS", "MORE"),
            ("SAUVER", "SAVE"), ("AIDE", "COMMANDS"),
        ]
        self.networth_spark = widgets.Sparkline(80)
        for v in p.cash_history[-80:]:
            self.networth_spark.push(v)
        if not p.cash_history:
            self.networth_spark.push(p.cash)
        # une tâche longue (mission / deal / éval) fait passer le temps comme un ADV
        if getattr(self.app, "advance_on_return", 0) and not p.game_over:
            self.app.advance_on_return = 0
            self._log(_L("  ⏱ Le temps avance pendant que vous travaillez…","  ⏱ Time advances while you work…"))
            self._advance_time()
        # tutoriel auto-déclenché à l'unlock d'une fonctionnalité (cf. scene_evaluation._finish)
        tid = p.flags.pop("pending_tutorial", None)
        if tid:
            self.app.scenes.go("tutorials", tid=tid, return_to="terminal")

    # --------------------------------------------------------------- events
    def handle_event(self, event):
        # 0) panneau de triche (mode test uniquement) : priorité sur tout le reste
        if self.cheat_panel is not None:
            if self.cheat_panel.handle(event):
                if self.cheat_panel.closed:
                    self.cheat_panel = None
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
        # 2) souris : boutons console + rail latéral + carte
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (getattr(self.app, "cheats", False) and self._cheat_btn_rect
                    and self._cheat_btn_rect.collidepoint(event.pos)):
                if self.cheat_panel is None:
                    from ui.cheatpanel import CheatPanel
                    self.cheat_panel = CheatPanel(self.app)
                else:
                    self.cheat_panel = None
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
            for label, rect in self._rail_rects.items():
                if rect.collidepoint(event.pos):
                    self._run_command(dict(self.rail)[label])
                    return
            if self._topco_header_rect and self._topco_header_rect.collidepoint(event.pos):
                self.app.scenes.go("explorer", return_to="terminal")
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
                    from ui.datawindow import DataWindow
                    self.datawins.append(DataWindow(
                        f"{name} — historique", [], [],
                        pos=(self.rail_w + 40, 100),
                        accent=config.COL_AMBER,
                        chart=list(self.market.index_history(name))))
                    if len(self.datawins) > 5:
                        self.datawins.pop(0)
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
        # 3) clavier : ligne de commande
        if event.type == pygame.KEYDOWN:
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
                    self.app.scenes.go("menu")
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
            else:
                if event.unicode and event.unicode.isprintable():
                    self.cmd += event.unicode
                    self.hist_pos = None

    def _datawin_row_click(self, w, idx):
        """Si la 1ʳᵉ cellule de la ligne est un ticker connu, ouvre sa fiche."""
        if idx >= len(w.rows):
            return
        cell = w.rows[idx][0]
        text = cell[0] if isinstance(cell, tuple) else cell
        ticker = str(text).replace("↑", "").replace("↓", "").strip().split()[0:1]
        if ticker and self.market.price_of(ticker[0].upper()) is not None:
            self._open_company_popup(ticker[0].upper())

    def _open_window(self, title, columns, rows, accent=config.COL_CYAN):
        """Ouvre une fenêtre de données déplaçable (en cascade)."""
        from ui.datawindow import DataWindow
        offset = 16 * (len(self.datawins) % 6)
        pos = (self.rail_w + 30 + offset, 90 + offset)
        self.datawins.append(DataWindow(title, columns, rows, pos=pos, accent=accent))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _open_news_window(self, region):
        """Détaille les news du jour à un emplacement de la carte (clic marqueur)."""
        p = self.app.gs.player
        items = [e for e in news_mod.for_day(p, p.day) if e["region"] == region]
        kcol = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_CYAN}
        rows = []
        for e in items:
            cat = news_mod.CATEGORY_LABEL.get(e["cat"], e["cat"])
            rows.append(((cat, kcol.get(e["kind"], config.COL_TEXT)), e["text"]))
        if not rows:
            rows = [("—", _L("Aucune actualité détaillée.", "No detailed news."))]
        loc = region or _L("Mondial", "Global")
        self._open_window(_L(f"NEWS — {loc} (jour {p.day})", f"NEWS — {loc} (day {p.day})"),
                          [(_L("Type", "Type"), 110), (_L("Actualité", "Headline"), 360)],
                          rows, accent=config.COL_PRESTIGE)

    def _open_company_popup(self, ticker):
        """Ouvre la fiche flottante d'une société (en cascade), sans changer de scène."""
        from ui.popups import CompanyPopup
        if not ticker or not self.market or self.market.metrics(ticker.upper()) is None:
            return
        offset = 16 * (len(self.datawins) % 6)
        pos = (self.rail_w + 30 + offset, 90 + offset)
        self.datawins.append(CompanyPopup(ticker, self.market, pos=pos))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _open_quick_access(self):
        """Ouvre le gestionnaire « accès rapide » des favoris (watchlist)."""
        from ui.popups import QuickAccessWindow
        offset = 16 * (len(self.datawins) % 6)
        pos = (self.rail_w + 30 + offset, 90 + offset)
        p = self.app.gs.player
        self.datawins.append(QuickAccessWindow(p, self.market, self._open_company_popup, pos=pos))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _open_chart_popup(self, ticker, kind="line"):
        """Ouvre un graphe flottant agrandi (en cascade) pour un ticker donné."""
        from ui.popups import ChartPopup
        offset = 16 * (len(self.datawins) % 6)
        pos = (self.rail_w + 30 + offset, 90 + offset)
        self.datawins.append(ChartPopup(f"GRAPHE — {ticker.upper()}", market=self.market,
                                        ticker=ticker, kind=kind, pos=pos))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

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

    def _ghost(self):
        """Retourne la complétion suggérée pour la saisie en cours (ou '')."""
        c = self.cmd.strip()
        if not c or " " in c:
            return ""
        up = c.upper()
        for name in CMD_NAMES:
            if name.startswith(up) and name != up:
                return name[len(up):]
        return ""

    def _autocomplete(self):
        c = self.cmd.strip()
        if not c or " " in c:
            return
        up = c.upper()
        for name in CMD_NAMES:
            if name.startswith(up) and name != up:
                self.cmd = name + " "
                self.hist_pos = None
                break

    def _run_command(self, raw):
        if not raw:
            return
        parts = raw.split()
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else None
        self.cmd_history.append(f"> {raw}")
        self.console_scroll = 0          # toute saisie ramène la vue au bas
        if not self.entered or self.entered[-1] != raw:
            self.entered.append(raw)
            self.entered = self.entered[-30:]
        p = self.app.gs.player

        # verrou par grade : certaines actions se débloquent en progressant
        feat = unlocks_mod.CMD_FEATURE.get(cmd)
        if feat and not unlocks_mod.unlocked(p, feat):
            g = unlocks_mod.required_grade(feat)
            self._log(_L(f"  ⊘ {unlocks_mod.feature_label(feat)}", f"  ⊘ {unlocks_mod.feature_label(feat)}"),
                      _L(f"     débloqué au grade {config.GRADES[g]} (vous : {p.grade}).",
                         f"     unlocked at grade {config.GRADES[g]} (you: {p.grade})."))
            return

        if cmd == "HELP":
            if get_lang() == "en":
                self._log(
                    "  ADV advance · COMMANDS full catalogue",
                    "  MARKET indices · TOP [region] · MOVERS · EXPLORE explorer",
                    "  COMPANY <tk> · SEARCH · WATCHLIST · COMPARE",
                    "  GP/GPC/GPCH <tk> · COMP · HS · HVOL · BETA · CORR · GC charts",
                    "  SECTOR · REGION · SCREEN · RANKING · CALENDAR",
                    "  PORTFOLIO · BUY/SELL · ALLOCATE · HEDGE · REBALANCE · PROTECT · OPTIONS · IPO · FX · AGENDA",
                    "  RESEARCH <tk> · ALERT <tk> <px> · MANDATES · PITCH",
                    "  LEARN academy · CERT certifications · ECO macro",
                    "  RV <tk> · DEFINE <term>",
                    "  MISSION work · DEALS / DEAL <id>",
                    "  INBOX messages · RIVALS leaderboard",
                    "  DECIDE decisions · CAREER career",
                    "  EVAL promotion · TRACK specialisation · REVIEW manager · STRESS regulator",
                    "  PORTFOLIO·MA·RISK·QUANT·SHEET·GLOSSARY · TEAM analysts · TIMELINE career",
                    "  STATUS · SAVE · SAVES · REG · MENU",
                )
            else:
                self._log(
                    "  ADV avancer · COMMANDS catalogue complet",
                    "  MARKET indices · TOP [region] · MOVERS · EXPLORE explorer",
                    "  COMPANY <tk> · SEARCH · WATCHLIST · COMPARE",
                    "  GP/GPC/GPCH <tk> · COMP · HS · HVOL · BETA · CORR · GC graphes",
                    "  SECTOR · REGION · SCREEN · RANKING · CALENDAR",
                    "  PORTFOLIO · BUY/SELL · ALLOCATE · HEDGE · REBALANCE · PROTECT · OPTIONS · IPO · FX · AGENDA",
                    "  RESEARCH <tk> · ALERT <tk> <px> · MANDATES · PITCH",
                    "  LEARN académie · CERT certifications · ECO macro",
                    "  RV <tk> · DEFINE <terme>",
                    "  MISSION travailler · DEALS / DEAL <id>",
                    "  INBOX messagerie · RIVALS classement",
                    "  DECIDE décisions · CAREER carrière",
                    "  EVAL promotion · TRACK voie · REVIEW manager · STRESS régulateur",
                    "  PORTFOLIO·MA·RISK·QUANT·SHEET·GLOSSARY · TEAM analystes · TIMELINE carrière",
                    "  STATUS · SAVE · SAVES · REG · MENU",
                )
        elif cmd in ("COMMANDS", "?", "CMD"):
            self.app.scenes.go("commands", return_to="terminal")
        elif cmd in ("ADV", "NEXT", "ADVANCE", "T"):
            self._advance_time()
        elif cmd in ("MARKET", "INDEX", "INDICES", "WEI"):
            self._cmd_market()
        elif cmd == "MARKETHUB":
            self.app.scenes.go("markethub", return_to="terminal")
        elif cmd == "TOP":
            self._cmd_top(arg)
        elif cmd in ("EXPLORE", "EXPLORER", "EXPLO"):
            self.app.scenes.go("explorer", return_to="terminal")
        elif cmd == "SHOP":
            self.app.scenes.go("shop", return_to="terminal")
        elif cmd in ("MOVERS", "MOVER"):
            self._cmd_movers()
        elif cmd in ("COMPANY", "CO", "TICKER", "DES"):
            self._cmd_company(arg)
        elif cmd in ("FA", "FIN", "STATEMENTS", "ETATS"):
            self._cmd_financials(arg)
        elif cmd in ("BONDS", "BOND", "OBLIGATIONS", "FI"):
            self.app.scenes.go("bonds", return_to="terminal")
        elif cmd in ("BUYBOND", "SELLBOND"):
            self._cmd_bond_trade(cmd, parts[1:])
        elif cmd in ("CMDTY", "COMMODITIES", "COMMO", "MATIERES"):
            self.app.scenes.go("commodities", return_to="terminal")
        elif cmd in ("BUYCMDTY", "SELLCMDTY"):
            self._cmd_alt_trade("commodities", cmd, parts[1:])
        elif cmd in ("CRYPTO", "COIN"):
            self.app.scenes.go("crypto", return_to="terminal")
        elif cmd in ("ETF", "ETFS", "FUNDS", "FONDS"):
            self.app.scenes.go("etfs", return_to="terminal")
        elif cmd in ("BUYETF", "SELLETF"):
            self._cmd_alt_trade("etfs", cmd, parts[1:])
        elif cmd in ("STRUCT", "STRUCTURED", "STRUCTURES"):
            self.app.scenes.go("structured", return_to="terminal")
        elif cmd in ("SWAP", "SWAPS"):
            self.app.scenes.go("swaps", return_to="terminal")
        elif cmd == "PROTECT":
            self.app.scenes.go("hedge", return_to="terminal")
        elif cmd in ("OPTIONS", "OPTION"):
            self.app.scenes.go("options", return_to="terminal")
        elif cmd in ("IPO", "IPOS"):
            self.app.scenes.go("ipo", return_to="terminal")
        elif cmd == "FX":
            self.app.scenes.go("fx", return_to="terminal")
        elif cmd in ("AGENDA", "PRONOS"):
            self.app.scenes.go("calendar", return_to="terminal")
        elif cmd == "REVIEW":
            self.app.scenes.go("review", return_to="terminal")
        elif cmd in ("TEAM", "EQUIPE"):
            self.app.scenes.go("team", return_to="terminal")
        elif cmd == "STRESS":
            self.app.scenes.go("stresstest", return_to="terminal")
        elif cmd == "TIMELINE":
            self.app.scenes.go("history", return_to="terminal")
        elif cmd in ("CREDIT", "TITRISATION", "ABS", "CLO"):
            self.app.scenes.go("credit", return_to="terminal")
        elif cmd in ("ALM", "BANKING"):
            self.app.scenes.go("alm", return_to="terminal")
        elif cmd in ("BUYCRYPTO", "SELLCRYPTO"):
            self._cmd_alt_trade("crypto", cmd, parts[1:])
        elif cmd in ("GP", "CHART", "GRAPH"):
            self._cmd_graph("line", parts[1:])
        elif cmd in ("GPC", "CANDLE", "CANDLES"):
            self._cmd_graph("candles", parts[1:])
        elif cmd in ("GPO", "BARS"):
            self._cmd_graph("bars", parts[1:])
        elif cmd in ("GPCH", "CHANGE", "PERF"):
            self._cmd_graph("change", parts[1:])
        elif cmd in ("COMP", "COMPGRAPH"):
            self._cmd_graph("compare", parts[1:])
        elif cmd in ("HS", "SPREAD", "RATIO"):
            self._cmd_graph("spread", parts[1:])
        elif cmd in ("HVOL", "VOL", "VOLATILITY"):
            self._cmd_graph("vol", parts[1:])
        elif cmd in ("BETA", "REG"):
            self._cmd_graph("beta", parts[1:])
        elif cmd in ("CORR", "CORRELATION", "MATRIX"):
            self._cmd_graph("corr", parts[1:])
        elif cmd in ("GEG", "MACROGRAPH"):
            self._cmd_graph("macro", parts[1:])
        elif cmd in ("GC", "CURVE", "YIELDCURVE", "YCRV"):
            self._cmd_graph("curve", parts[1:])
        elif cmd in ("RV", "PEERS", "COMPS"):
            self._cmd_rv(arg)
        elif cmd in ("ECO", "MACRO", "ECONOMY"):
            self._cmd_eco()
        elif cmd in ("LEARN", "ACADEMY", "ACADEMIE", "APPRENDRE"):
            self.app.scenes.go("academy", return_to="terminal")
        elif cmd in ("TUTO", "TUTORIAL", "TUTORIELS", "HOWTO", "GUIDE"):
            self.app.scenes.go("tutorials", return_to="terminal")
        elif cmd in ("GOV", "GOVERNMENTS", "GOVT", "PAYS", "SOUVERAINS", "POLITICS", "POLITIQUE"):
            self.app.scenes.go("governments", return_to="terminal",
                               focus=(arg.upper() if arg else None))
        elif cmd in ("CERT", "CERTS", "CERTIFICATIONS", "CFA", "FRM"):
            self.app.scenes.go("cert", return_to="terminal")
        elif cmd in ("DEFINE", "DEF", "GLO"):
            self._cmd_define(parts[1:])
        elif cmd in ("SEARCH", "FIND"):
            self._cmd_search(parts[1:])
        elif cmd in ("ACCESS", "FAVORIS", "FAVORITES", "QUICKACCESS"):
            self._open_quick_access()
        elif cmd == "DEALS":
            self._cmd_deals()
        elif cmd == "DEAL":
            self._cmd_deal(arg)
        elif cmd in ("EVAL", "EVALUATION"):
            self._cmd_eval()
        elif cmd == "EXAMCERT":
            self.app.scenes.go("examcert", return_to="terminal")
        elif cmd in ("GLOSSARY", "GLOSSAIRE"):
            self.app.scenes.go("glossary", return_to="terminal")
        elif cmd in ("PORTFOLIO", "PORTEFEUILLE", "BOOK", "POSITIONS", "PRT"):
            self.app.scenes.go("book", return_to="terminal")
        elif cmd in ("PA", "ANALYSE", "ANALYTICS", "DETAIL", "PORT"):
            self.app.scenes.go("analytics", return_to="terminal")
        elif cmd in ("FRONTIER", "MARKOWITZ", "FRONTIERE"):
            self.app.scenes.go("portfolio")
        elif cmd in ("BUY", "ACHETER", "LONG"):
            self._cmd_buy(parts[1:])
        elif cmd in ("SELL", "VENDRE"):
            self._cmd_sell(parts[1:])
        elif cmd in ("SHORT", "VAD"):
            self._cmd_short(parts[1:])
        elif cmd in ("COVER", "RACHETER"):
            self._cmd_cover(parts[1:])
        elif cmd in ("MARGIN", "MARGE"):
            self._cmd_margin()
        elif cmd in ("ALLOCATE", "ALLOC"):
            self._cmd_allocate(parts[1:])
        elif cmd == "HEDGE":
            self._cmd_hedge(arg)
        elif cmd in ("REBALANCE", "REBAL"):
            self._cmd_rebalance()
        elif cmd == "PITCH":
            self._cmd_pitch()
        elif cmd in ("MA", "M&A"):
            self.app.scenes.go("ma")
        elif cmd == "RISK":
            self.app.scenes.go("risk")
        elif cmd == "QUANT":
            self.app.scenes.go("quant")
        elif cmd in ("SHEET", "EXCEL", "TABLEUR"):
            self.app.scenes.go("spreadsheet")
        elif cmd in ("SAVES", "LOAD"):
            self.app.scenes.go("saves", return_to="terminal")
        elif cmd in ("CAREER", "CARRIERE", "ROADMAP", "OBJECTIVES", "OBJ", "HISTORY", "JOURNAL"):
            self.app.scenes.go("career", return_to="terminal")
        elif cmd in ("INBOX", "MAIL", "MESSAGES"):
            self.app.scenes.go("inbox", return_to="terminal")
        elif cmd in ("DECIDE", "DECISION", "DILEMMA"):
            if p.pending_dilemmas:
                self.app.scenes.go("dilemma", return_to="terminal")
            else:
                self._log(_L("  Aucune décision en attente.","  No pending decision."))
        elif cmd in ("RIVALS", "RIVAUX", "LEADERBOARD"):
            self.app.scenes.go("rivals", return_to="terminal")
        elif cmd in ("MANDATES", "MANDATS"):
            self._cmd_mandates()
        elif cmd in ("MANDATE", "MANDAT"):
            self._cmd_mandate(parts[1:])
        elif cmd in ("RESEARCH", "RECHERCHE"):
            self._cmd_research(arg)
        elif cmd in ("ALERT", "ALERTE"):
            self._cmd_alert(parts[1:])
        elif cmd in ("ALERTS", "ALERTES"):
            self._cmd_alerts()
        elif cmd in ("WATCHLIST", "WATCH", "WL"):
            self._cmd_watchlist(parts[1:])
        elif cmd in ("COMPARE", "CMP"):
            self._cmd_compare(parts[1:])
        elif cmd in ("SECTOR", "SECTEUR"):
            self._cmd_sector(arg)
        elif cmd in ("REGION", "REGIONS"):
            self._cmd_region(arg)
        elif cmd in ("SCREEN", "SCREENER", "EQS"):
            self._cmd_screen()
        elif cmd in ("RANKING", "RANK"):
            self._cmd_top(arg)
        elif cmd in ("BENCHMARK", "BENCH"):
            self._cmd_benchmark()
        elif cmd in ("CALENDAR", "CAL"):
            self._cmd_calendar()
        elif cmd in ("MISSION", "MISSIONS", "WORK", "JOB"):
            self.app.scenes.go("mission")
        elif cmd in ("TRACK", "VOIE"):
            if p.flags.get("can_choose_track") or p.grade_index >= 2:
                self.app.scenes.go("track")
            else:
                self._log(_L("  Voies disponibles à partir du grade Analyst.","  Tracks available from Analyst grade."))
        elif cmd == "STATUS":
            info = config.CONTINENTS[p.continent]
            if get_lang() == "en":
                self._log(
                    f"  Name       : {p.name}",
                    f"  Grade      : {p.grade}  |  Track: {p.track}",
                    f"  Cash       : {widgets.format_money(p.cash, info['currency'])}",
                    f"  Reputation : {p.reputation}/100",
                    f"  Time       : day {p.day} (Q{p.quarter})",
                )
            else:
                self._log(
                    f"  Nom        : {p.name}",
                    f"  Grade      : {p.grade}  |  Voie : {p.track}",
                    f"  Trésorerie : {widgets.format_money(p.cash, info['currency'])}",
                    f"  Réputation : {p.reputation}/100",
                    f"  Temps      : jour {p.day} (T{p.quarter})",
                )
        elif cmd == "SAVE":
            if p.hardcore:
                self._log(_L("  [HARDCORE] Sauvegarde manuelle désactivée.","  [HARDCORE] Manual save disabled."))
            else:
                self.app.gs.save(config.SAVE_SLOTS[0])
                self._log(_L(f"  Partie sauvegardée (slot: {config.SAVE_SLOTS[0]}).", f"  Game saved (slot: {config.SAVE_SLOTS[0]})."))
        elif getattr(self.app, "cheats", False) and cmd in (
                "GRADE", "CASH", "REP", "REPUTATION", "CHEAT", "CHEATS", "MAXUNLOCK"):
            self._cmd_cheat(cmd, parts[1:])
        elif cmd in ("NEWS", "ACTUS", "ACTUALITES", "EVENTS"):
            self.app.scenes.go("news", return_to="terminal")
        elif cmd in ("MORE", "PLUS", "RACCOURCIS", "SHORTCUTS", "PAGES"):
            self.app.scenes.go("more", return_to="terminal")
        elif cmd == "REG":
            info = config.CONTINENTS[p.continent]
            self._log(_L(f"  Régulateur : {info['regulator']}", f"  Regulator  : {info['regulator']}"),
                      _L(f"  Cadre      : {info['framework']}", f"  Framework  : {info['framework']}"))
        elif cmd == "MENU":
            self.app.scenes.go("menu")
        else:
            self._log(_L(f"  Commande inconnue : {raw}. Tapez COMMANDS.", f"  Unknown command: {raw}. Type COMMANDS."))

    # ------------------------------------------------------- commandes marché
    def update(self, dt):
        self.t += dt
        self.worldmap.update(dt)

    # ----------------------------------------------------------------- draw
