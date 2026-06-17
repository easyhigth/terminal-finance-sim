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
import math
import pygame
from core import config
from core import deals as deals_mod
from core import missions as missions_mod
from core import career as career_mod
from core import portfolio as pf_mod
from core import inbox as inbox_mod
from core import rivals as rivals_mod
from core import scenarios as scenarios_mod
from core import politics as politics_mod
from core import dilemmas as dilemmas_mod
from core import badges as badges_mod
from core import mandates as mandates_mod
from core import unlocks as unlocks_mod
from core import history as history_mod
from core import etfs as etfs_mod
from core.i18n import t as _t, get_lang
from core.scene_manager import Scene


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr
from ui import fonts, widgets
from ui.worldmap import WorldMap

# Noms de commandes pour l'autocomplétion (Tab) et la suggestion fantôme
CMD_NAMES = [
    "HELP", "COMMANDS", "ADV", "MISSION", "EVAL", "EXAMCERT", "TRACK", "CAREER", "INBOX",
    "RIVALS", "MANDATES", "MANDATE", "DECIDE", "MARKET", "MARKETHUB", "TOP", "MOVERS",
    "COMPANY", "FA", "SEARCH", "ACCESS", "EXPLORE", "WATCHLIST", "COMPARE", "SECTOR", "REGION", "SCREEN",
    "RANKING", "BENCHMARK", "CALENDAR", "RESEARCH", "ALERT", "ALERTS",
    "PORTFOLIO", "BOOK", "BUY", "SELL", "LONG", "SHORT", "COVER", "MARGIN",
    "BONDS", "BUYBOND", "SELLBOND", "GOV", "GOVERNMENTS", "PAYS",
    "CMDTY", "BUYCMDTY", "SELLCMDTY",
    "CRYPTO", "BUYCRYPTO", "SELLCRYPTO", "ETF", "ETFS", "BUYETF", "SELLETF",
    "STRUCT", "CREDIT", "ALM",
    "ALLOCATE", "HEDGE", "REBALANCE",
    "PITCH", "FRONTIER", "RISK", "QUANT", "MA", "SHEET", "GLOSSARY",
    "SAVE", "SAVES", "NEWS", "REG", "STATUS", "MENU",
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


class TerminalScene(Scene):
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
        self.news = list(SAMPLE_NEWS.get(p.continent, SAMPLE_NEWS["USA"]))
        self.recent_events = []
        self.datawins = []        # fenêtres de données déplaçables (overlay)
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
        self.rail_w = 150         # largeur du rail latéral
        self._map_rect = None     # rect de la carte (pour le clic)
        # rail latéral : (libellé, commande), regroupé par usage
        self.rail = [
            ("ADV ▸", "ADV"),
            ("PORTEF.", "PORTFOLIO"), ("MARCHÉ", "MARKETHUB"), ("ETF", "ETF"),
            ("MISSION", "MISSION"), ("EXAM/CERTIF", "EXAMCERT"),
            ("MANDATS", "MANDATES"), ("DEALS", "DEALS"),
            ("INBOX", "INBOX"), ("DÉCIDE", "DECIDE"),
            ("TABLEUR", "SHEET"), ("ACADÉMIE", "LEARN"),
            ("GLOSSAIRE", "GLOSSARY"),
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

    # --------------------------------------------------------------- events
    def handle_event(self, event):
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
                    "  PORTFOLIO · BUY/SELL · ALLOCATE · HEDGE · REBALANCE",
                    "  RESEARCH <tk> · ALERT <tk> <px> · MANDATES · PITCH",
                    "  LEARN academy · CERT certifications · ECO macro",
                    "  RV <tk> · DEFINE <term>",
                    "  MISSION work · DEALS / DEAL <id>",
                    "  INBOX messages · RIVALS leaderboard",
                    "  DECIDE decisions · CAREER career",
                    "  EVAL promotion · TRACK specialisation",
                    "  PORTFOLIO·MA·RISK·QUANT·SHEET·GLOSSARY",
                    "  STATUS · SAVE · SAVES · REG · MENU",
                )
            else:
                self._log(
                    "  ADV avancer · COMMANDS catalogue complet",
                    "  MARKET indices · TOP [region] · MOVERS · EXPLORE explorer",
                    "  COMPANY <tk> · SEARCH · WATCHLIST · COMPARE",
                    "  GP/GPC/GPCH <tk> · COMP · HS · HVOL · BETA · CORR · GC graphes",
                    "  SECTOR · REGION · SCREEN · RANKING · CALENDAR",
                    "  PORTFOLIO · BUY/SELL · ALLOCATE · HEDGE · REBALANCE",
                    "  RESEARCH <tk> · ALERT <tk> <px> · MANDATES · PITCH",
                    "  LEARN académie · CERT certifications · ECO macro",
                    "  RV <tk> · DEFINE <terme>",
                    "  MISSION travailler · DEALS / DEAL <id>",
                    "  INBOX messagerie · RIVALS classement",
                    "  DECIDE décisions · CAREER carrière",
                    "  EVAL promotion · TRACK voie",
                    "  PORTFOLIO·MA·RISK·QUANT·SHEET·GLOSSARY",
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
        elif cmd == "NEWS":
            import random
            random.shuffle(self.news)
            self._log(_L("  Flux d'actualités rafraîchi.","  News feed refreshed."))
        elif cmd == "REG":
            info = config.CONTINENTS[p.continent]
            self._log(_L(f"  Régulateur : {info['regulator']}", f"  Regulator  : {info['regulator']}"),
                      _L(f"  Cadre      : {info['framework']}", f"  Framework  : {info['framework']}"))
        elif cmd == "MENU":
            self.app.scenes.go("menu")
        else:
            self._log(_L(f"  Commande inconnue : {raw}. Tapez COMMANDS.", f"  Unknown command: {raw}. Type COMMANDS."))

    # ------------------------------------------------------- commandes marché
    def _cmd_market(self):
        rows = []
        for name, *_ in self.market.index_defs:
            v = self.market.index_value(name)
            chg = self.market.index_change_pct(name)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            rows.append(((name, config.COL_AMBER), f"{v:,.0f}",
                         (f"{'+' if chg>=0 else ''}{chg:.2f}%", ccol)))
        self._open_window("INDICES MONDIAUX", [("Indice", 110), ("Valeur", 90),
                                               ("Var.", 80)], rows)
        self._log(_L("  Indices ouverts (fenêtre).","  Indices opened (window)."))

    def _match_region(self, name):
        if not name:
            return self.app.gs.player.continent
        for r in self.market.regions:
            if r.lower() == name.lower():
                return r
        return self.app.gs.player.continent

    def _cmd_top(self, region):
        region = self._match_region(region)
        cur = config.CONTINENTS[region]["currency"]
        rows = [((c["ticker"], config.COL_AMBER), c["name"][:18],
                 widgets.format_money(c["mktcap"] * 1e6, cur))
                for c in self.market.top_companies(region=region, n=15)]
        self._open_window(f"TOP — {region}", [("Tk", 60), ("Nom", 150),
                                              ("Capi", 90)], rows)

    def _cmd_movers(self):
        rows = []
        for c in self.market.top_companies(n=8, by="gain"):
            rows.append((("↑ " + c["ticker"], config.COL_UP), c["name"][:18], c["sector"]))
        for c in self.market.top_companies(n=8, by="loss"):
            rows.append((("↓ " + c["ticker"], config.COL_DOWN), c["name"][:18], c["sector"]))
        self._open_window("PLUS FORTS MOUVEMENTS", [("Tk", 70), ("Nom", 150),
                                                    ("Secteur", 90)], rows)

    def _cmd_company(self, ticker):
        if not ticker:
            self._log(_L("  Usage : COMPANY <nom ou ticker>  (ex: COMPANY MVC, ou COMPANY mavric).",
                         "  Usage: COMPANY <name or ticker>  (e.g. COMPANY MVC, or COMPANY mavric)."))
            return
        tk = self.market.resolve(ticker)
        if tk is None:
            self._log(_L(f"  Aucun résultat : {ticker}. Essayez SEARCH.",
                         f"  No match: {ticker}. Try SEARCH."))
            return
        self.app.scenes.go("company", ticker=tk, return_to="terminal")

    def _cmd_bond_trade(self, cmd, args):
        """BUYBOND/SELLBOND <id> <qté>."""
        import core.bonds as bonds_mod
        if not unlocks_mod.unlocked(self.app.gs.player, "trade"):
            self._log(_L("  ⊘ Trading débloqué au grade Associate.","  ⊘ Trading unlocked at Associate grade."))
            return
        if len(args) < 1:
            self._log(_L(f"  Usage : {cmd} <id> <qté>  (voir BONDS).", f"  Usage: {cmd} <id> <qty>  (see BONDS)."))
            return
        bid = args[0].upper()
        qty = "ALL"
        if len(args) > 1 and args[1].upper() != "ALL":
            if not args[1].isdigit():
                self._log(_L("  Quantité invalide.","  Invalid quantity."))
                return
            qty = int(args[1])
        p, m = self.app.gs.player, self.market
        if cmd == "BUYBOND":
            if qty == "ALL":
                self._log(_L("  Précisez une quantité pour l'achat.","  Specify a quantity to buy."))
                return
            r = bonds_mod.buy_bond(p, m, bid, qty)
            if r["ok"]:
                self._log(_L(f"  ✓ Achat {qty} × {bid} @ {r['price']:.2f} = "
                          f"{widgets.format_money(r['total'], self._cur())}.",
                          f"  ✓ Bought {qty} × {bid} @ {r['price']:.2f} = "
                          f"{widgets.format_money(r['total'], self._cur())}."))
            else:
                self._log(_L(f"  Achat refusé ({r['reason']}).", f"  Buy rejected ({r['reason']})."))
        else:
            r = bonds_mod.sell_bond(p, m, bid, qty)
            if r["ok"]:
                self._log(_L(f"  ✓ Vente {int(r['qty'])} × {bid} (P&L réalisé "
                          f"{r['realized']:+.0f}).",
                          f"  ✓ Sold {int(r['qty'])} × {bid} (realised P&L "
                          f"{r['realized']:+.0f})."))
            else:
                self._log(_L(f"  Vente refusée ({r['reason']}).", f"  Sell rejected ({r['reason']})."))
        self._after_trade()

    def _cmd_alt_trade(self, asset, cmd, args):
        """Trading générique commodities/crypto : BUY/SELL <id> <qté>."""
        import importlib
        mod = importlib.import_module(f"core.{asset}")
        if not unlocks_mod.unlocked(self.app.gs.player, "trade"):
            self._log(_L("  ⊘ Trading débloqué au grade Associate.","  ⊘ Trading unlocked at Associate grade."))
            return
        if len(args) < 1:
            self._log(_L(f"  Usage : {cmd} <id> <qté>.", f"  Usage: {cmd} <id> <qty>."))
            return
        cid = args[0].upper()
        qty = "ALL"
        if len(args) > 1 and args[1].upper() != "ALL":
            if not args[1].isdigit():
                self._log(_L("  Quantité invalide.","  Invalid quantity."))
                return
            qty = int(args[1])
        p, m = self.app.gs.player, self.market
        if cmd.startswith("BUY"):
            if qty == "ALL":
                self._log(_L("  Précisez une quantité pour l'achat.","  Specify a quantity to buy."))
                return
            r = mod.buy(p, m, cid, qty)
            self._log(_L(f"  ✓ Achat {qty} {cid} @ {r['price']:.2f}.", f"  ✓ Bought {qty} {cid} @ {r['price']:.2f}.") if r["ok"]
                      else _L(f"  Achat refusé ({r['reason']}).", f"  Buy rejected ({r['reason']})."))
        else:
            r = mod.sell(p, m, cid, qty)
            self._log(_L(f"  ✓ Vente {cid} (P&L réalisé {r['realized']:+.0f}).", f"  ✓ Sold {cid} (realised P&L {r['realized']:+.0f}).") if r["ok"]
                      else _L(f"  Vente refusée ({r['reason']}).", f"  Sell rejected ({r['reason']})."))
        self._after_trade()

    def _cmd_financials(self, ticker):
        """FA <ticker> : états financiers complets (bilan + compte de résultat)."""
        if not ticker:
            self._log(_L("  Usage : FA <nom ou ticker>  (états financiers ; ex: FA MVC).",
                         "  Usage: FA <name or ticker>  (financial statements; e.g. FA MVC)."))
            return
        tk = self.market.resolve(ticker)
        if tk is None:
            self._log(_L(f"  Aucun résultat : {ticker}. Essayez SEARCH.",
                         f"  No match: {ticker}. Try SEARCH."))
            return
        self.app.scenes.go("financials", ticker=tk, return_to="terminal")

    def _cmd_search(self, terms):
        q = " ".join(terms) if terms else ""
        if not q:
            self._open_quick_access()
            return
        res = self.market.search(q)
        if not res:
            self._log(_L(f"  Aucune société pour « {q} ».", f"  No company for “{q}”."))
        else:
            self._log(_L(f"  Résultats : {', '.join(res)}", f"  Results: {', '.join(res)}"))

    def _cmd_graph(self, kind, args):
        """Ouvre l'atelier de graphes analytiques (5 ans d'historique disponibles
        dès le jour 1). `kind` choisit le type ; `args` les tickers éventuels."""
        # recherche intelligente : résout chaque argument (nom OU ticker partiel)
        tickers = []
        if kind not in ("macro", "curve"):
            for a in args:
                tk = self.market.resolve(a)
                if not tk and etfs_mod.exists(a.upper()):   # ETF graphable aussi
                    tk = a.upper()
                if tk:
                    tickers.append(tk)
                else:
                    self._log(_L(f"  Aucun résultat : {a}.", f"  No match: {a}."))
        self.app.scenes.go("graph", kind=kind, tickers=tickers, return_to="terminal")

    def _cmd_rv(self, ticker):
        """RV — valeur relative : multiples de la société vs médianes du secteur."""
        if not ticker:
            self._log(_L("  Usage : RV <ticker>  (valeur relative vs pairs).","  Usage: RV <ticker>  (relative value vs peers)."))
            return
        tk = self.market.resolve(ticker)
        mt = self.market.metrics(tk) if tk else None
        if not mt:
            self._log(_L(f"  Aucun résultat : {ticker}.", f"  No match: {ticker}."))
            return
        med = self.market.sector_medians(mt["sector"])

        def fmt(v):
            return f"{v:.1f}x" if v else "n.m."

        def verdict(val, ref):
            if not val or not ref:
                return ("—", config.COL_TEXT_DIM)
            if val < ref * 0.9:
                return ("décoté", config.COL_UP)
            if val > ref * 1.1:
                return ("cher", config.COL_DOWN)
            return ("en ligne", config.COL_TEXT)
        rows = []
        for label, key in [("P/E", "pe"), ("EV/EBITDA", "ev_ebitda"), ("P/S", "ps")]:
            v, r = mt[key], med[key]
            txt, col = verdict(v, r)
            rows.append((label, fmt(v), fmt(r), (txt, col)))
        self._open_window(f"RV {mt['ticker']} — secteur {mt['sector']} ({med['n']} pairs)",
                          [("Multiple", 90), (mt["ticker"], 70), ("Médiane", 70),
                           ("Verdict", 80)], rows)

    def _cmd_eco(self):
        """ECO — indicateurs macro et leur tendance."""
        m = self.market.macro
        notes = {
            "rate": "coût de l'argent ; ↑ pèse sur actions/immo",
            "inflation": "hausse des prix ; guide la banque centrale",
            "growth": "PIB ; ↑ soutient les bénéfices",
            "unemployment": "↑ = ralentissement",
            "confidence": "moral des marchés",
        }
        rows = []
        reg_good = self.market.regime in ("Expansion", "Calme")
        rows.append(("Régime de marché", self.market.regime_label(),
                     ("", config.COL_UP if reg_good else config.COL_DOWN),
                     "toile de fond : module dérive & volatilité"))
        for key in ["rate", "inflation", "growth", "unemployment", "confidence"]:
            d = m[key]
            ch = self.market.macro_change(key)
            ccol = config.COL_UP if ch >= 0 else config.COL_DOWN
            rows.append((d["label"], f"{d['v']:.2f}{d['unit']}",
                         (f"{'+' if ch>=0 else ''}{ch:.2f}", ccol), notes[key]))
        self._open_window("ECO — macro-économie",
                          [("Indicateur", 120), ("Niveau", 70), ("1 an", 60),
                           ("Lecture", 200)], rows)

    def _cmd_define(self, terms):
        """DEFINE — définition d'un terme du glossaire."""
        q = " ".join(terms).strip()
        if not q:
            self._log(_L("  Usage : DEFINE <terme>  (ex: DEFINE WACC). Voir aussi GLOSSARY.","  Usage: DEFINE <term>  (e.g. DEFINE WACC). See also GLOSSARY."))
            return
        from data import glossary_data
        from core.i18n import get_lang
        GLOSSARY, _ = glossary_data.localized(get_lang())
        ql = q.lower()
        hit = None
        for term, (cat, definition) in GLOSSARY.items():
            if term.lower() == ql:
                hit = (term, cat, definition)
                break
        if not hit:
            for term, (cat, definition) in GLOSSARY.items():
                if ql in term.lower():
                    hit = (term, cat, definition)
                    break
        if not hit:
            self._log(_L(f"  « {q} » introuvable au glossaire. Tapez GLOSSARY pour parcourir.", f"  “{q}” not found in the glossary. Type GLOSSARY to browse."))
            return
        term, cat, definition = hit
        self._log(f"  [{cat}] {term} :")
        # découpe la définition sur ~2 lignes
        words = definition.split()
        line = "   "
        for w in words:
            if len(line) + len(w) > 64:
                self._log(line)
                line = "   "
            line += w + " "
        self._log(line)

    def _cmd_cheat(self, cmd, args):
        """Commandes de TEST (mode triche, via main_cheat.py)."""
        p = self.app.gs.player
        if cmd in ("CHEAT", "CHEATS"):
            self._log(_L("  ⊕ TRICHE : GRADE <0-11> · CASH <montant> · REP <0-100> · MAXUNLOCK","  ⊕ CHEAT: GRADE <0-11> · CASH <amount> · REP <0-100> · MAXUNLOCK"))
            self._log(_L("  Grades : ","  Grades: ") + " ".join(f"{i}={g}" for i, g in enumerate(config.GRADES)))
            return
        if cmd == "GRADE":
            if not args or not args[0].lstrip("-").isdigit():
                self._log(_L("  Usage : GRADE <0-11>  (voir CHEAT pour la liste).","  Usage: GRADE <0-11>  (see CHEAT for the list)."))
                return
            gi = max(0, min(len(config.GRADES) - 1, int(args[0])))
            p.grade_index = gi
            p.grade_deals = 0
            p.grade_missions = 0
            p.grade_start_quarter = p.quarter
            if gi >= 2 and p.track == "General":
                p.flags["can_choose_track"] = True
            self._log(_L(f"  ⊕ Grade réglé sur {gi} = {config.GRADES[gi]}.", f"  ⊕ Grade set to {gi} = {config.GRADES[gi]}."))
            self._check_badges()
        elif cmd == "CASH":
            if not args or not args[0].lstrip("-").replace(".", "").isdigit():
                self._log(_L("  Usage : CASH <montant>.","  Usage: CASH <amount>."))
                return
            p.cash = float(args[0])
            self._log(_L(f"  ⊕ Trésorerie réglée sur {widgets.format_money(p.cash, self._cur())}.", f"  ⊕ Cash set to {widgets.format_money(p.cash, self._cur())}."))
        elif cmd in ("REP", "REPUTATION"):
            if not args or not args[0].lstrip("-").isdigit():
                self._log(_L("  Usage : REP <0-100>.","  Usage: REP <0-100>."))
                return
            p.reputation = max(0, min(100, int(args[0])))
            self._log(_L(f"  ⊕ Réputation réglée sur {p.reputation}/100.", f"  ⊕ Reputation set to {p.reputation}/100."))
        elif cmd == "MAXUNLOCK":
            p.grade_index = len(config.GRADES) - 1
            p.reputation = max(p.reputation, 80)
            if p.track == "General":
                p.flags["can_choose_track"] = True
            self._log(_L(f"  ⊕ Grade max ({config.GRADES[-1]}) : toutes les actions débloquées.", f"  ⊕ Top grade ({config.GRADES[-1]}): all actions unlocked."))
            self._check_badges()

    def _cmd_eval(self):
        """Ouvre l'examen si TOUS les critères de promotion sont remplis."""
        p = self.app.gs.player
        # un examen mis en pause se reprend directement (peu importe les critères)
        if isinstance(p.eval_state, dict) and p.eval_state.get("mode") == "promotion" \
                and p.eval_state.get("items"):
            self._log(_L("  Reprise de l'examen en pause…","  Resuming the paused exam…"))
            self.app.scenes.go("evaluation")
            return
        if not p.can_promote():
            self._log(_L("  Vous êtes au grade maximal : aucune promotion possible.","  You are at the top grade: no promotion possible."))
            return
        if not career_mod.promotion_ready(p):
            self._log(_L("  Critères de promotion non remplis :","  Promotion criteria not met:"))
            for r in career_mod.promotion_requirements(p):
                if not r["met"]:
                    self._log(_L(f"   ○ {r['label']} : {int(r['current'])}/{int(r['target'])}", f"   ○ {r['label']}: {int(r['current'])}/{int(r['target'])}"))
            self._log(_L("  Voir CAREER pour la roadmap complète.","  See CAREER for the full roadmap."))
            return
        self.app.scenes.go("evaluation")

    # ---------------------------------------------------- commandes lecture
    def _cmd_watchlist(self, args):
        p = self.app.gs.player
        if not args:
            self._open_quick_access()
            return
        op = args[0].upper()
        tk = args[1].upper() if len(args) > 1 else None
        if op in ("ADD", "+") and tk:
            if self.market.price_of(tk) is None:
                self._log(_L(f"  Ticker inconnu : {tk}.", f"  Unknown ticker: {tk}."))
            elif tk in p.watchlist:
                self._log(_L(f"  {tk} est déjà dans la watchlist.", f"  {tk} is already in the watchlist."))
            elif len(p.watchlist) >= 10:
                self._log(_L("  Limite de 10 favoris atteinte. Retirez-en un avant d'en ajouter un autre.",
                             "  Limit of 10 favorites reached. Remove one before adding another."))
            else:
                p.watchlist.append(tk)
                self.market.track_company(tk)
                self._log(_L(f"  {tk} ajouté à la watchlist.", f"  {tk} added to the watchlist."))
        elif op in ("REMOVE", "RM", "-") and tk:
            if tk in p.watchlist:
                p.watchlist.remove(tk)
                self._log(_L(f"  {tk} retiré de la watchlist.", f"  {tk} removed from the watchlist."))
            else:
                self._log(_L(f"  {tk} n'est pas dans la watchlist.", f"  {tk} is not in the watchlist."))
        else:
            self._log(_L("  Usage : WATCHLIST [ADD|REMOVE <ticker>]","  Usage: WATCHLIST [ADD|REMOVE <ticker>]"))

    def _cmd_compare(self, args):
        if len(args) < 2:
            self._log(_L("  Usage : COMPARE <ticker1> <ticker2>","  Usage: COMPARE <ticker1> <ticker2>"))
            return
        a, b = self.market.resolve(args[0]), self.market.resolve(args[1])
        ma = self.market.metrics(a) if a else None
        mb = self.market.metrics(b) if b else None
        if not ma or not mb:
            self._log(_L("  Un des termes est introuvable.","  One of the terms has no match."))
            return
        def fmt(m, key, f):
            v = m[key]
            return f(v) if v is not None else "n.m."
        rows = [
            ("Prix", fmt(ma, "price", lambda v: f"{v:.2f}"), fmt(mb, "price", lambda v: f"{v:.2f}")),
            ("Capi(M)", fmt(ma, "mktcap", lambda v: f"{v:,.0f}"), fmt(mb, "mktcap", lambda v: f"{v:,.0f}")),
            ("P/E", fmt(ma, "pe", lambda v: f"{v:.1f}"), fmt(mb, "pe", lambda v: f"{v:.1f}")),
            ("EV/EBITDA", fmt(ma, "ev_ebitda", lambda v: f"{v:.1f}"), fmt(mb, "ev_ebitda", lambda v: f"{v:.1f}")),
            ("Marge nette", fmt(ma, "net_margin", lambda v: f"{v*100:.0f}%"), fmt(mb, "net_margin", lambda v: f"{v*100:.0f}%")),
            ("Bêta", fmt(ma, "beta", lambda v: f"{v:.2f}"), fmt(mb, "beta", lambda v: f"{v:.2f}")),
        ]
        self._open_window(f"COMPARER {a} / {b}",
                          [("Métrique", 110), (a, 90), (b, 90)], rows)

    def _cmd_sector(self, name):
        if not name:
            secs = ", ".join(self.market.sectors)
            self._log(_L("  Secteurs : ","  Sectors: ") + secs[:60], "  " + secs[60:])
            return
        key = None
        for s in self.market.sectors:
            if s.lower().startswith(name.lower()):
                key = s
                break
        if not key:
            self._log(_L(f"  Secteur inconnu : {name}.", f"  Unknown sector: {name}."))
            return
        members = [c for c in self.market.companies if c["sector"] == key]
        members.sort(key=lambda c: self.market.price_of(c["ticker"]) * c["shares"], reverse=True)
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        rows = [((c["ticker"], config.COL_AMBER), c["name"][:18], c["region"],
                 widgets.format_money(self.market.price_of(c["ticker"]) * c["shares"] * 1e6, cur))
                for c in members[:18]]
        self._open_window(f"SECTEUR — {key}", [("Tk", 60), ("Nom", 150),
                                               ("Région", 70), ("Capi", 80)], rows)

    def _cmd_region(self, name):
        region = self._match_region(name)
        idxs = [n for n, r, *_ in self.market.index_defs if r == region]
        self._log(_L(f"  Région {region} — indices : {', '.join(idxs)}", f"  Region {region} — indices: {', '.join(idxs)}"))
        for n in idxs:
            self._log(f"   {n:9s} {self.market.index_value(n):>12,.0f}  {self.market.index_change_pct(n):+.2f}%")

    def _cmd_screen(self):
        # filtre simple : value (P/E bas) parmi les grandes capis
        found = []
        for c in self.market.companies:
            mt = self.market.metrics(c["ticker"])
            if mt and mt["pe"] and 0 < mt["pe"] < 12 and mt["mktcap"] > 50000:
                found.append((mt["pe"], c["ticker"], c["name"], c["sector"]))
        found.sort()
        rows = [((tk, config.COL_AMBER), f"{pe:.1f}", nm[:16], sec)
                for pe, tk, nm, sec in found[:16]]
        if not rows:
            rows = [("—", "—", "aucune valeur", "—")]
        self._open_window("SCREEN — value (P/E < 12, grandes capis)",
                          [("Tk", 60), ("P/E", 50), ("Nom", 140), ("Secteur", 90)], rows)

    def _cmd_benchmark(self):
        p = self.app.gs.player
        idx = {n: r for n, r, *_ in self.market.index_defs}
        ref = next((n for n, r in idx.items() if r == p.continent), "C&D 500")
        hist = self.market.index_history(ref)
        perf = ((hist[-1] / hist[0] - 1) * 100) if len(hist) > 1 and hist[0] else 0.0
        self._log(_L(f"  Benchmark régional {ref} : {perf:+.1f}% depuis le suivi.", f"  Regional benchmark {ref}: {perf:+.1f}% since tracking."))
        self._log(_L(f"  Votre trésorerie : {widgets.format_money(p.cash, config.CONTINENTS[p.continent]['currency'])} "
                  f"(record {widgets.format_money(max(p.best_cash, p.cash), config.CONTINENTS[p.continent]['currency'])}).",
                  f"  Your cash: {widgets.format_money(p.cash, config.CONTINENTS[p.continent]['currency'])} "
                  f"(high {widgets.format_money(max(p.best_cash, p.cash), config.CONTINENTS[p.continent]['currency'])})."))

    def _cmd_calendar(self):
        p = self.app.gs.player
        days_in_q = (p.day - 1) % config.DAYS_PER_QUARTER
        to_end = config.DAYS_PER_QUARTER - days_in_q
        rows = [("Fin de trimestre", f"~{to_end}j", f"T{p.quarter}")]
        for d in sorted(p.deals, key=lambda d: d["days_left"]):
            urgent = d["days_left"] <= config.DAYS_PER_STEP * 2
            rows.append(((f"#{d['id']} {d['title'][:20]}",
                          config.COL_DOWN if urgent else config.COL_TEXT),
                         f"{d['days_left']}j", d["kind"]))
        self._open_window(f"CALENDRIER — Jour {p.day}",
                          [("Échéance", 200), ("Délai", 60), ("Type", 80)], rows)

    # ------------------------------------------------------------- mandats
    def _cmd_mandates(self):
        p = self.app.gs.player
        cur = self._cur()
        rows = []
        for m in p.mandates:
            g, beta = mandates_mod.progress(p, self.market, m)
            gcol = config.COL_UP if g >= m["target_pct"] else config.COL_WARN
            rows.append(((f"#{m['id']} {m['client'][:16]}", config.COL_AMBER),
                         f"{g:+.1f}/{m['target_pct']:.0f}%",
                         (f"β{beta:.2f}/{m['max_beta']:.2f}",
                          config.COL_DOWN if beta > m["max_beta"] else config.COL_TEXT),
                         f"T{m['deadline_q']}"))
        for o in p.mandate_offers:
            rows.append(((f"#{o['id']} {o['client'][:16]}", config.COL_CYAN),
                         f"obj {o['target_pct']:.0f}%", f"β≤{o['max_beta']:.2f}",
                         (f"OFFRE {o['horizon']}T", config.COL_CYAN)))
        if not rows:
            if p.grade_index < mandates_mod.MIN_GRADE:
                rows = [("Mandats dès le grade Associate.", "", "", "")]
            else:
                rows = [("Aucun mandat. ADV pour en recevoir.", "", "", "")]
        self._open_window("MANDATS CLIENTS",
                          [("Mandat", 170), ("Perf/Obj", 90), ("Risque", 90),
                           ("Échéance", 80)], rows, accent=config.COL_PRESTIGE)
        self._log(_L("  MANDATE ACCEPT <id> / MANDATE DECLINE <id> pour gérer.","  MANDATE ACCEPT <id> / MANDATE DECLINE <id> to manage."))

    def _cmd_mandate(self, args):
        p = self.app.gs.player
        if len(args) < 2 or not args[1].isdigit():
            self._log(_L("  Usage : MANDATE ACCEPT|DECLINE <id>","  Usage: MANDATE ACCEPT|DECLINE <id>"))
            return
        op, mid = args[0].upper(), int(args[1])
        if op in ("ACCEPT", "ACCEPTER"):
            res = mandates_mod.accept(p, mid, self.market)
            if res == "full":
                self._log(_L(f"  Déjà {mandates_mod.MAX_ACTIVE} mandats en cours.", f"  Already {mandates_mod.MAX_ACTIVE} active mandates."))
            elif res:
                self._log(_L(f"  ✓ Mandat #{mid} accepté : {res['client']} — objectif "
                          f"+{res['target_pct']:.0f}% en {res['horizon']}T, bêta ≤ {res['max_beta']:.2f}.",
                          f"  ✓ Mandate #{mid} accepted: {res['client']} — target "
                          f"+{res['target_pct']:.0f}% in {res['horizon']}Q, beta ≤ {res['max_beta']:.2f}."))
                career_mod.log(p, "deal", f"Mandat accepté : {res['client']}")
            else:
                self._log(_L(f"  Offre #{mid} introuvable.", f"  Offer #{mid} not found."))
        elif op in ("DECLINE", "REFUSER"):
            self._log(_L("  Offre déclinée.","  Offer declined.") if mandates_mod.decline(p, mid)
                      else _L(f"  Offre #{mid} introuvable.", f"  Offer #{mid} not found."))
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    # ------------------------------------------------------------- recherche
    def _cmd_research(self, ticker):
        p = self.app.gs.player
        if not ticker:
            self._log(_L("  Usage : RESEARCH <ticker>","  Usage: RESEARCH <ticker>"))
            return
        tk = self.market.resolve(ticker)
        mt = self.market.metrics(tk) if tk else None
        if not mt:
            self._log(_L(f"  Aucun résultat : {ticker}.", f"  No match: {ticker}."))
            return
        # valeur intrinsèque simplifiée : BPA capitalisé à un P/E « juste » sectoriel
        fair_pe = {"Tech": 24, "Semicon": 22, "Luxe": 22, "Sante": 19, "Conso": 18,
                   "Finance": 11, "Energie": 10, "Industrie": 15, "Agro": 13,
                   "Telecom": 12, "Utilities": 14, "Materiaux": 12,
                   "Immobilier": 15, "Auto": 9}.get(mt["sector"], 15)
        fair = max(0.5, mt["eps"] * fair_pe)
        upside = (fair / mt["price"] - 1) * 100
        rating = ("ACHAT" if upside > 12 else "VENTE" if upside < -12 else "NEUTRE")
        p.research[tk] = {"fair": round(fair, 2), "rating": rating,
                          "upside": round(upside, 1), "day": p.day}
        rcol = (config.COL_UP if rating == "ACHAT" else
                config.COL_DOWN if rating == "VENTE" else config.COL_WARN)
        self._log(_L(f"  Recherche {tk} : valeur intrinsèque {fair:.2f} "
                  f"(potentiel {upside:+.0f}%) → {rating}.",
                  f"  Research {tk}: intrinsic value {fair:.2f} "
                  f"(upside {upside:+.0f}%) → {rating}."))
        self.app.notify(f"{tk} : {rating} ({upside:+.0f}%)",
                        "good" if rating == "ACHAT" else "bad" if rating == "VENTE" else "info")

    # ------------------------------------------------------------- alertes
    def _cmd_alert(self, args):
        p = self.app.gs.player
        if len(args) < 2:
            self._log(_L("  Usage : ALERT <ticker> <prix>","  Usage: ALERT <ticker> <price>"))
            return
        tk = self.market.resolve(args[0])
        try:
            price = float(args[1].replace(",", "."))
        except ValueError:
            self._log(_L("  Prix invalide.","  Invalid price."))
            return
        cur_price = self.market.price_of(tk) if tk else None
        if cur_price is None:
            self._log(_L(f"  Aucun résultat : {args[0]}.", f"  No match: {args[0]}."))
            return
        self.market.track_company(tk)
        p.alerts.append({"ticker": tk, "price": price, "above": price > cur_price})
        sens = "au-dessus de" if price > cur_price else "en-dessous de"
        self._log(_L(f"  Alerte posée : {tk} {sens} {price:.2f} (cours {cur_price:.2f}).", f"  Alert set: {tk} {sens} {price:.2f} (price {cur_price:.2f})."))

    def _cmd_alerts(self):
        p = self.app.gs.player
        if not p.alerts:
            self._log(_L("  Aucune alerte active.","  No active alert."))
            return
        rows = [((a["ticker"], config.COL_AMBER), f"{a['price']:.2f}",
                 "↑" if a["above"] else "↓",
                 f"{self.market.price_of(a['ticker']) or 0:.2f}") for a in p.alerts]
        self._open_window("ALERTES DE PRIX",
                          [("Tk", 60), ("Seuil", 70), ("Sens", 50), ("Cours", 70)], rows)

    def _check_alerts(self):
        """Vérifie les alertes ; notifie au franchissement et les retire."""
        p = self.app.gs.player
        still = []
        for a in p.alerts:
            price = self.market.price_of(a["ticker"])
            if price is None:
                continue
            crossed = (price >= a["price"]) if a["above"] else (price <= a["price"])
            if crossed:
                self._log(_L(f"  ⚠ ALERTE {a['ticker']} : cours {price:.2f} a franchi {a['price']:.2f}.", f"  ⚠ ALERT {a['ticker']}: price {price:.2f} crossed {a['price']:.2f}."))
                self.app.notify(f"Alerte {a['ticker']} @ {price:.2f}", "warn")
                inbox_mod.push(p, "desk", "Desk", f"Alerte cours : {a['ticker']}",
                               f"{a['ticker']} a franchi votre seuil de {a['price']:.2f} "
                               f"(cours {price:.2f}).")
            else:
                still.append(a)
        p.alerts = still

    # ---------------------------------------------------- trading & portefeuille
    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _after_trade(self):
        p = self.app.gs.player
        self._check_badges()
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        nw = pf_mod.net_worth(p, self.market)
        if p.check_game_over(net_worth=nw):
            self.app.scenes.go("gameover")

    def _check_badges(self):
        """Attribue les nouveaux badges et notifie (toast + journal)."""
        for b in badges_mod.check_new(self.app.gs.player, self.market):
            self.app.notify(f"✶ Badge : {b['name']}", "prestige")
            career_mod.log(self.app.gs.player, "info", f"Badge débloqué : {b['name']}")

    def _cmd_buy(self, args):
        if len(args) < 2 or not args[1].lstrip("-").isdigit():
            self._log(_L("  Usage : BUY <ticker> <quantité>","  Usage: BUY <ticker> <quantity>"))
            return
        tk, qty = args[0].upper(), int(args[1])
        res = pf_mod.buy(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            reason = {"ticker": "ticker inconnu", "qty": "quantité invalide",
                      "isshort": f"position courte ouverte sur {tk} — utilisez COVER",
                      "leverage": f"levier max atteint ({res.get('max_leverage',0):.1f}x)"
                      }.get(res["reason"], res["reason"])
            self._log(_L(f"  Achat refusé : {reason}.", f"  Buy rejected: {reason}."))
            return
        self._log(_L(f"  ✓ Achat {qty} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['total'], self._cur())} (frais inclus).",
                     f"  ✓ Bought {qty} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['total'], self._cur())} (fees incl.)."))
        if res["total"] > 60000:
            career_mod.log(self.app.gs.player, "deal", f"Achat {qty} {tk}")
        self._after_trade()

    def _cmd_sell(self, args):
        if not args:
            self._log(_L("  Usage : SELL <ticker> <quantité|ALL>","  Usage: SELL <ticker> <quantity|ALL>"))
            return
        tk = args[0].upper()
        qty = "ALL"
        if len(args) > 1 and args[1].upper() != "ALL":
            if not args[1].isdigit():
                self._log(_L("  Quantité invalide.","  Invalid quantity."))
                return
            qty = int(args[1])
        res = pf_mod.sell(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            self._log(_L(f"  Vente refusée : {'aucune position' if res['reason']=='noposition' else res['reason']}.", f"  Sell rejected: {'no position' if res['reason']=='noposition' else res['reason']}."))
            return
        sign = "+" if res["realized"] >= 0 else ""
        self._log(_L(f"  ✓ Vente {int(res['qty'])} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['net'], self._cur())}  "
                     f"(P&L réalisé {sign}{widgets.format_money(res['realized'], self._cur())}).",
                     f"  ✓ Sold {int(res['qty'])} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['net'], self._cur())}  "
                     f"(realised P&L {sign}{widgets.format_money(res['realized'], self._cur())})."))
        self._after_trade()

    def _cmd_short(self, args):
        """SHORT <ticker> <quantité> : vente à découvert (pari à la baisse)."""
        if len(args) < 2 or not args[1].isdigit():
            self._log(_L("  Usage : SHORT <ticker> <quantité>  (parier à la baisse)","  Usage: SHORT <ticker> <quantity>  (bet on a fall)"))
            return
        tk, qty = args[0].upper(), int(args[1])
        res = pf_mod.short(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            reason = {"ticker": "ticker inconnu", "qty": "quantité invalide",
                      "islong": f"position longue ouverte sur {tk} — vendez-la d'abord",
                      "leverage": f"levier max atteint ({res.get('max_leverage',0):.1f}x)"
                      }.get(res["reason"], res["reason"])
            self._log(_L(f"  Short refusé : {reason}.", f"  Short rejected: {reason}."))
            return
        self._log(_L(f"  ✓ Short {qty} {tk} @ {res['price']:.2f} = "
                     f"+{widgets.format_money(res['net'], self._cur())} en cash "
                     "(à racheter via COVER).",
                     f"  ✓ Shorted {qty} {tk} @ {res['price']:.2f} = "
                     f"+{widgets.format_money(res['net'], self._cur())} cash "
                     "(buy back via COVER)."))
        self._after_trade()

    def _cmd_cover(self, args):
        """COVER <ticker> <quantité|ALL> : rachète une position courte."""
        if not args:
            self._log(_L("  Usage : COVER <ticker> <quantité|ALL>","  Usage: COVER <ticker> <quantity|ALL>"))
            return
        tk = args[0].upper()
        qty = "ALL"
        if len(args) > 1 and args[1].upper() != "ALL":
            if not args[1].isdigit():
                self._log(_L("  Quantité invalide.","  Invalid quantity."))
                return
            qty = int(args[1])
        res = pf_mod.cover(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            self._log(_L(f"  Rachat refusé : {'aucune position courte' if res['reason']=='noshort' else res['reason']}.", f"  Cover rejected: {'no short position' if res['reason']=='noshort' else res['reason']}."))
            return
        sign = "+" if res["realized"] >= 0 else ""
        self._log(_L(f"  ✓ Cover {int(res['qty'])} {tk} @ {res['price']:.2f} "
                     f"(P&L réalisé {sign}{widgets.format_money(res['realized'], self._cur())}).",
                     f"  ✓ Covered {int(res['qty'])} {tk} @ {res['price']:.2f} "
                     f"(realised P&L {sign}{widgets.format_money(res['realized'], self._cur())})."))
        self._after_trade()

    def _cmd_margin(self):
        """MARGIN : état de la marge (equity, exposition, levier, pouvoir d'achat)."""
        st = pf_mod.margin_status(self.app.gs.player, self.market)
        cur = self._cur()
        lev = "∞" if st["leverage"] == float("inf") else f"{st['leverage']:.2f}x"
        self._log(_L(f"  Marge — equity {widgets.format_money(st['equity'], cur)} · "
                     f"exposition {widgets.format_money(st['gross'], cur)} · levier {lev} "
                     f"(max {st['max_leverage']:.1f}x)",
                     f"  Margin — equity {widgets.format_money(st['equity'], cur)} · "
                     f"exposure {widgets.format_money(st['gross'], cur)} · leverage {lev} "
                     f"(max {st['max_leverage']:.1f}x)"))
        self._log(_L(f"  Pouvoir d'achat {widgets.format_money(st['buying_power'], cur)} · "
                     f"capital emprunté {widgets.format_money(st['borrowed'], cur)}"
                     + ("  ⚠ APPEL DE MARGE IMMINENT" if st["margin_call"] else ""),
                     f"  Buying power {widgets.format_money(st['buying_power'], cur)} · "
                     f"borrowed {widgets.format_money(st['borrowed'], cur)}"
                     + ("  ⚠ MARGIN CALL IMMINENT" if st["margin_call"] else "")))

    def _cmd_allocate(self, args):
        """ALLOCATE <ticker> <pct> : ajuste la position à pct% de la valeur nette."""
        if len(args) < 2 or not args[1].replace(".", "").isdigit():
            self._log(_L("  Usage : ALLOCATE <ticker> <pourcentage>","  Usage: ALLOCATE <ticker> <percentage>"))
            return
        p = self.app.gs.player
        tk = args[0].upper()
        pct = float(args[1])
        price = self.market.price_of(tk)
        if price is None:
            self._log(_L(f"  Ticker inconnu : {tk}.", f"  Unknown ticker: {tk}."))
            return
        nw = pf_mod.net_worth(p, self.market)
        target_val = nw * pct / 100.0
        cur_shares = p.portfolio.get(tk, {}).get("shares", 0)
        cur_val = cur_shares * price
        diff = target_val - cur_val
        if abs(diff) < price:
            self._log(_L("  Position déjà proche de la cible.","  Position already close to target."))
            return
        if diff > 0:
            qty = int(diff // price)
            if qty > 0:
                self._cmd_buy([tk, str(qty)])
        else:
            qty = min(int(cur_shares), int((-diff) // price) + 1)
            if qty > 0:
                self._cmd_sell([tk, str(qty)])

    def _cmd_hedge(self, arg):
        """HEDGE <pct> : lève du cash en vendant pct% de chaque position."""
        p = self.app.gs.player
        if not p.portfolio:
            self._log(_L("  Aucune position à couvrir.","  No position to hedge."))
            return
        beta = pf_mod.portfolio_beta(p, self.market)
        if arg is None or not arg.replace(".", "").isdigit():
            self._log(_L(f"  Bêta du portefeuille : {beta:.2f}. "
                         "HEDGE <pct> pour réduire l'exposition (vendre une part vers le cash).",
                         f"  Portfolio beta: {beta:.2f}. "
                         "HEDGE <pct> to cut exposure (sell part into cash)."))
            return
        pct = max(0.0, min(100.0, float(arg)))
        for tk, pos in list(p.portfolio.items()):
            qty = int(abs(pos["shares"]) * pct / 100.0)
            if qty <= 0:
                continue
            if pos["shares"] > 0:           # long -> on allège
                pf_mod.sell(p, self.market, tk, qty)
            else:                           # short -> on rachète
                pf_mod.cover(p, self.market, tk, qty)
        self._log(_L(f"  Couverture : exposition réduite de {pct:.0f}%. "
                  f"Nouveau bêta {pf_mod.portfolio_beta(p, self.market):.2f}.",
                  f"  Hedge: exposure cut by {pct:.0f}%. "
                  f"New beta {pf_mod.portfolio_beta(p, self.market):.2f}."))
        self._after_trade()

    def _cmd_rebalance(self):
        """REBALANCE : ramène les positions à poids égaux."""
        p = self.app.gs.player
        if len(p.portfolio) < 2:
            self._log(_L("  Rééquilibrage : au moins 2 positions nécessaires.","  Rebalance: at least 2 positions required."))
            return
        pos_val = pf_mod.positions_value(p, self.market)
        target = pos_val / len(p.portfolio)
        for tk in list(p.portfolio.keys()):
            price = self.market.price_of(tk)
            if not price:
                continue
            cur = p.portfolio[tk]["shares"] * price
            diff = target - cur
            qty = int(abs(diff) // price)
            if qty <= 0:
                continue
            if diff > 0:
                pf_mod.buy(p, self.market, tk, qty)
            else:
                pf_mod.sell(p, self.market, tk, qty)
        self._log(_L(f"  Portefeuille rééquilibré à poids égaux ({len(p.portfolio)} lignes).", f"  Portfolio rebalanced to equal weights ({len(p.portfolio)} lines)."))
        self._after_trade()

    def _cmd_pitch(self):
        """PITCH : démarche un client pour décrocher un mandat (selon réputation)."""
        import random
        p = self.app.gs.player
        prob = 0.3 + 0.5 * (p.reputation / 100.0)
        if random.random() < prob:
            d = deals_mod.maybe_generate(p)
            if d:
                self._log(_L(f"  ✓ Pitch réussi : nouveau mandat #{d[0]['id']} — {d[0]['title']}.", f"  ✓ Pitch won: new mandate #{d[0]['id']} — {d[0]['title']}."))
            else:
                self._log(_L("  ✓ Pitch réussi, mais votre pipeline de deals est déjà plein.","  ✓ Pitch won, but your deal pipeline is already full."))
        else:
            p.adjust_reputation(-1)
            self._log(_L("  ✗ Pitch infructueux. Le client passe son tour (-1 réputation).","  ✗ Pitch failed. The client passes (-1 reputation)."))
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    # ------------------------------------------------------- temps & deals
    def _advance_time(self):
        import random
        gs = self.app.gs
        p = gs.player
        m = self.market
        # crise/boom éventuel AVANT le pas (le choc s'applique dès ce tour)
        scenario = scenarios_mod.maybe_trigger(m)
        # pas de marché (déterministe)
        market_news = m.step()
        p.market_step = m.step_count
        self.worldmap.push_news(market_news)
        # logique carrière existante (salaire/coûts, deals, événements) +
        # valorisation du portefeuille via le marché
        summary = gs.advance_step(m)
        info = config.CONTINENTS[p.continent]
        cur = info["currency"]
        self.networth_spark.push(pf_mod.net_worth(p, m))
        # concurrents : progression + sniping des deals expirés + actions actives
        for r in p.rivals:
            r["mood"] = "flat"          # réinitialise l'humeur du tour
        rivals_mod.step(p, m)
        for d in summary["expired"]:
            rival = rivals_mod.snipe(p, d, random)
            inbox_mod.on_deal_sniped(p, d, rival)
            career_mod.log(p, "deal", f"{rival} rafle « {d['title']} »")
        # rivaux ACTIFS : percées, snipe de deals en retard, débauchage de mandats
        for ev in rivals_mod.act(p, m, random):
            self.recent_events.insert(0, {"title": ev["text"][:70], "kind": ev["kind"]})
            self.worldmap.push_news([{"region": p.continent, "kind": ev["kind"],
                                      "text": ev["rival"]}])
            career_mod.log(p, "deal" if ev["type"] in ("snipe", "poach") else "info",
                           ev["text"])
            self.app.notify(ev["text"][:60], ev["kind"])
            if ev["type"] == "snipe":
                inbox_mod.on_deal_sniped(p, ev["deal"], ev["rival"])
            elif ev["type"] == "poach":
                inbox_mod.push(p, "client", f"Mandat — {ev['client']}", "Mandat perdu",
                               f"{ev['rival']} a décroché le mandat de {ev['client']} "
                               "pendant que vous hésitiez. Soyez plus décidé.")
        self.recent_events = self.recent_events[:8]
        self._log(_L(f"  +{config.DAYS_PER_STEP}j → jour {p.day} (T{p.quarter}). "
                  f"Solde du tour : {widgets.format_money(summary['net'], cur)}",
                  f"  +{config.DAYS_PER_STEP}d → day {p.day} (Q{p.quarter}). "
                  f"Turn balance: {widgets.format_money(summary['net'], cur)}"))
        if summary.get("dividends", 0) > 0:
            self._log(_L(f"  ◆ Dividendes encaissés : +{widgets.format_money(summary['dividends'], cur)}",
                          f"  ◆ Income received: +{widgets.format_money(summary['dividends'], cur)}"))
        # débrief « pourquoi mon portefeuille a bougé » : attribution par facteur
        if p.portfolio:
            holdings = {t: pos["shares"] for t, pos in p.portfolio.items()}
            attr = m.factor_attribution(holdings)
            if abs(attr["total"]) > 1.0:
                fm_ = lambda v: widgets.format_money(v, cur)
                own = attr["specific"] + attr["drift"]   # part propre + dérive de base
                self._log(_L(f"  ≡ Positions {fm_(attr['total'])} = marché {fm_(attr['world'])}"
                          f" · secteur {fm_(attr['sector'])} · région {fm_(attr['region'])}"
                          f" · propre {fm_(own)}",
                          f"  ≡ Positions {fm_(attr['total'])} = market {fm_(attr['world'])}"
                          f" · sector {fm_(attr['sector'])} · region {fm_(attr['region'])}"
                          f" · idiosyncratic {fm_(own)}"))
        # financement (intérêts sur marge + frais de short) et appel de marge
        fin = summary.get("financing")
        if fin and fin["total"] > 1.0:
            self._log(_L(f"  ◆ Frais de financement : -{widgets.format_money(fin['total'], cur)} "
                      f"(intérêts marge + emprunt de titres).",
                      f"  ◆ Financing cost: -{widgets.format_money(fin['total'], cur)} "
                      f"(margin interest + stock borrow)."))
        for res in (summary.get("structured_due") or []):
            pr = res["product"]
            sign = "+" if res["pnl"] >= 0 else ""
            self._log(_L(f"  ■ Produit structuré échu : {pr['name']} → "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)}).",
                      f"  ■ Structured product matured: {pr['name']} → "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)})."))
            self.app.notify(_L("Produit structuré arrivé à échéance","Structured product matured"), "info")
        for res in (summary.get("securitised_due") or []):
            pos = res["position"]
            sign = "+" if res["pnl"] >= 0 else ""
            self._log(_L(f"  ■ Tranche {pos['name']} échue : perte pool {res['pool_loss']*100:.1f}% → "
                      f"votre tranche -{res['loss_frac']*100:.0f}% capital · "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)}).",
                      f"  ■ Tranche {pos['name']} matured: pool loss {res['pool_loss']*100:.1f}% → "
                      f"your tranche -{res['loss_frac']*100:.0f}% capital · "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)})."))
            self.app.notify(_L("Tranche de titrisation dénouée","Securitisation tranche settled"), "info")
        mc = summary.get("margin_call")
        if mc:
            self._log(_L(f"  ⚠ APPEL DE MARGE : liquidation forcée de "
                      f"{widgets.format_money(mc['liquidated'], cur)} "
                      f"(pénalité {widgets.format_money(mc['penalty'], cur)}).",
                      f"  ⚠ MARGIN CALL: forced liquidation of "
                      f"{widgets.format_money(mc['liquidated'], cur)} "
                      f"(penalty {widgets.format_money(mc['penalty'], cur)})."))
            self.app.notify(_L("Appel de marge : liquidation forcée","Margin call: forced liquidation"), "bad")
        # news marché en tête du flux
        self.recent_events = [{"title": n["text"], "kind": n["kind"], "cash": 0, "rep": 0}
                              for n in market_news] + summary["events"] + self.recent_events
        self.recent_events = self.recent_events[:6]
        for e in summary["events"]:
            tag = {"good": "↑", "bad": "↓", "info": "•"}.get(e["kind"], "•")
            extra = (f" {widgets.format_money(e['cash'], cur)}" if e["cash"] else "")
            extra += (f" rep{e['rep']:+d}" if e["rep"] else "")
            self._log(f"  {tag} {e['title']}{extra}")
        for d in summary["expired"]:
            self._log(_L(f"  ✕ Deal expiré : {d['title']} (raflé par un rival)", f"  ✕ Deal expired: {d['title']} (snatched by a rival)"))
        # crise/boom : narration (carte + flux + journal + inbox)
        if scenario:
            self.worldmap.push_news([{"region": None, "kind": scenario["kind"],
                                      "text": scenario["name"]}])
            self.recent_events.insert(0, {"title": "⚠ " + scenario["name"],
                                          "kind": scenario["kind"], "cash": 0, "rep": 0})
            self._log(_L(f"  ⚠ ÉVÉNEMENT : {scenario['name']} — {scenario['story'][:50]}…", f"  ⚠ EVENT: {scenario['name']} — {scenario['story'][:50]}…"))
            inbox_mod.on_crisis(p, scenario["name"], scenario["kind"])
            career_mod.log(p, "crisis", scenario["name"])
            self.app.notify(scenario["name"], scenario["kind"])
            if scenario["kind"] == "bad":
                p.flags["crises"] = p.flags.get("crises", 0) + 1
        # événement HISTORIQUE scénarisé (campagne déterministe dans le temps)
        hist = history_mod.maybe_trigger(p, m)
        if hist:
            from core.i18n import get_lang
            hname, hstory = history_mod.localized(hist["event"], get_lang())
            self.worldmap.push_news([{"region": None, "kind": hist["kind"], "text": hname}])
            self.recent_events.insert(0, {"title": "✶ " + hname, "kind": hist["kind"],
                                          "cash": 0, "rep": 0})
            self._log(f"  ✶ {hname} — {hstory[:64]}…")
            inbox_mod.on_crisis(p, hname, hist["kind"])
            career_mod.log(p, "crisis", hname)
            self.app.notify(hname, hist["kind"])
            if hist["kind"] == "bad":
                p.flags["crises"] = p.flags.get("crises", 0) + 1
        # événement POLITIQUE régional (impacte actions ET spreads obligataires de la zone)
        pol = politics_mod.maybe_trigger(p, m, random)
        if pol:
            from core.i18n import get_lang
            en = get_lang() == "en"
            pname = pol["name_en"] if en else pol["name"]
            pstory = pol["story_en"] if en else pol["story"]
            self.worldmap.push_news([{"region": pol["region"], "kind": pol["kind"],
                                      "text": pname}])
            tag = {"good": "▲", "bad": "▼", "info": "◆"}.get(pol["kind"], "◆")
            self.recent_events.insert(0, {"title": f"{tag} {pname}", "kind": pol["kind"],
                                          "cash": 0, "rep": 0})
            self._log(_L(f"  ⚑ POLITIQUE — {pname} : {pstory[:64]}…",
                         f"  ⚑ POLITICS — {pname}: {pstory[:64]}…"))
            inbox_mod.on_crisis(p, pname, pol["kind"])
            career_mod.log(p, "crisis", pname)
            self.app.notify(pname, pol["kind"])
            if pol["kind"] == "bad":
                p.flags["crises"] = p.flags.get("crises", 0) + 1
        if summary.get("quarter_changed"):
            self._log(_L(f"  ── Nouveau trimestre : T{p.quarter} ──", f"  ── New quarter: Q{p.quarter} ──"))
            qr = summary.get("quarter_report")
            if qr and qr["total"]:
                self._log(_L(f"  Bilan T{p.quarter-1} : {qr['done']}/{qr['total']} objectifs, "
                          f"+{qr['rep']} rép, +{widgets.format_money(qr['cash'], cur)}",
                          f"  Q{p.quarter-1} review: {qr['done']}/{qr['total']} objectives, "
                          f"+{qr['rep']} rep, +{widgets.format_money(qr['cash'], cur)}"))
            inbox_mod.on_quarter(p, summary.get("quarter_report"))
            hot = p.flags.get("hot_sector")
            if hot:
                self._log(_L(f"  ✶ Secteur à surveiller ce trimestre : {hot}.", f"  ✶ Sector to watch this quarter: {hot}."))
                self.app.notify(_L(f"Secteur du trimestre : {hot}", f"Sector of the quarter: {hot}"), "info")
            # mandats arrivés à échéance
            for res in mandates_mod.evaluate_due(p, m):
                mm = res["mandate"]
                if res["ok"]:
                    self._log(_L(f"  ✓ MANDAT réussi : {mm['client']} (+{res['growth']:.1f}%) "
                              f"→ +{widgets.format_money(mm['reward_cash'], cur)}, rép +{mm['reward_rep']}.",
                              f"  ✓ MANDATE won: {mm['client']} (+{res['growth']:.1f}%) "
                              f"→ +{widgets.format_money(mm['reward_cash'], cur)}, rep +{mm['reward_rep']}."))
                    self.app.notify(_L(f"Mandat réussi : {mm['client']}", f"Mandate won: {mm['client']}"), "good")
                    inbox_mod.push(p, "client", mm["client"], "Mandat rempli avec succès",
                                   f"Performance de {res['growth']:.1f}% conforme à nos attentes. "
                                   "Commission versée. Au plaisir de retravailler ensemble.")
                else:
                    self._log(_L(f"  ✗ MANDAT échoué : {mm['client']} (rép -{mm['penalty_rep']}).", f"  ✗ MANDATE failed: {mm['client']} (rep -{mm['penalty_rep']})."))
                    self.app.notify(_L(f"Mandat échoué : {mm['client']}", f"Mandate failed: {mm['client']}"), "bad")
                    inbox_mod.push(p, "client", mm["client"], "Mandat non rempli",
                                   "Les objectifs n'ont pas été atteints. Nous confions "
                                   "désormais notre capital ailleurs.")
        # nouvelle offre de mandat éventuelle
        offer = mandates_mod.maybe_offer(p, random)
        if offer:
            self._log(_L(f"  ✶ OFFRE DE MANDAT : {offer['client']} — {widgets.format_money(offer['capital'], cur)} "
                      f"(MANDATES pour voir).",
                      f"  ✶ MANDATE OFFER: {offer['client']} — {widgets.format_money(offer['capital'], cur)} "
                      f"(type MANDATES to view)."))
            self.app.notify(_L(f"Offre de mandat : {offer['client']}", f"Mandate offer: {offer['client']}"), "info")
            inbox_mod.push(p, "client", offer["client"], "Proposition de mandat",
                           f"Nous souhaitons vous confier {widgets.format_money(offer['capital'], cur)} : "
                           f"objectif +{offer['target_pct']:.0f}% en {offer['horizon']} trimestres, "
                           f"bêta ≤ {offer['max_beta']:.2f}. Tapez MANDATES puis MANDATE ACCEPT {offer['id']}.")
        # alertes de prix
        self._check_alerts()
        for d in summary["new_deals"]:
            self._log(_L(f"  ✶ Nouveau deal #{d['id']} : {d['title']} ({d['days_left']}j)", f"  ✶ New deal #{d['id']}: {d['title']} ({d['days_left']}d)"))
        # messages d'ambiance / conformité
        inbox_mod.on_step(p, m, summary, random)
        # scrutin réglementaire : décroissance + risque d'enquête
        inv = dilemmas_mod.maybe_investigate(p, random)
        if inv:
            self._log(_L(f"  ⚠ ENQUÊTE RÉGLEMENTAIRE : amende "
                      f"{widgets.format_money(inv['fine'], cur)}, réputation -{inv['rep_loss']}.",
                      f"  ⚠ REGULATORY INVESTIGATION: fine "
                      f"{widgets.format_money(inv['fine'], cur)}, reputation -{inv['rep_loss']}."))
            self.app.notify(_L("Enquête réglementaire : sanction","Regulatory investigation: penalty"), "bad")
        # dilemme éventuel à trancher
        dil = dilemmas_mod.maybe_trigger(p, random)
        if dil:
            self._log(_L(f"  § DÉCISION REQUISE : {dil['title']} — tapez DECIDE.", f"  § DECISION REQUIRED: {dil['title']} — type DECIDE."))
            self.app.notify(_L(f"Décision requise : {dil['title']}", f"Decision required: {dil['title']}"), "warn")
        # bilan de trimestre / quarter en toast
        if summary.get("quarter_changed") and summary.get("quarter_report") \
                and summary["quarter_report"]["total"]:
            qr = summary["quarter_report"]
            self.app.notify(_L(f"Bilan T{p.quarter-1} : {qr['done']}/{qr['total']} objectifs", f"Q{p.quarter-1} review: {qr['done']}/{qr['total']} objectives"), "info")
        # badges éventuels
        self._check_badges()
        unread = inbox_mod.unread_count(p)
        if unread:
            self._log(_L(f"  @ {unread} message(s) non lu(s) — tapez INBOX.", f"  @ {unread} unread message(s) — type INBOX."))
        if not p.hardcore:
            gs.save(config.AUTOSAVE_SLOT)
        if summary["game_over"] or p.check_game_over():
            self.app.scenes.go("gameover")
        elif dil:
            self.app.scenes.go("dilemma", return_to="terminal")

    def _cmd_deals(self):
        p = self.app.gs.player
        if not p.deals:
            self._log(_L("  Aucun deal en cours. Avancez le temps (ADV) pour en générer.","  No active deals. Advance time (ADV) to generate some."))
            return
        cur = config.CONTINENTS[p.continent]["currency"]
        self._log(_L("  Deals en cours :","  Active deals:"))
        for d in p.deals:
            prob = deals_mod.success_probability(p, d)
            self._log(f"   #{d['id']} {d['title']} [{d['kind']}] {d['days_left']}j  "
                      f"gain {widgets.format_money(d['reward_cash'], cur)} p={int(prob*100)}%")

    def _cmd_deal(self, arg):
        p = self.app.gs.player
        if arg is None or not arg.isdigit():
            self._log(_L("  Usage : DEAL <id>  (voir DEALS).","  Usage: DEAL <id>  (see DEALS)."))
            return
        if deals_mod.find_deal(p, int(arg)) is None:
            self._log(_L(f"  Deal #{arg} introuvable.", f"  Deal #{arg} not found."))
            return
        # mini-jeu : vraie décision financière (au lieu d'une résolution au dé)
        self.app.scenes.go("deal", deal_id=int(arg), return_to="terminal")

    # --------------------------------------------------------------- update
    def update(self, dt):
        self.t += dt
        self.worldmap.update(dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        info = config.CONTINENTS[p.continent]
        accent = info["color"]

        self._draw_topbar(surf, p, info, accent)
        self._draw_ticker(surf)

        M = config.MARGIN
        top = config.TOPBAR_H + config.TICKER_H + M
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

    def _draw_rail(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, _t("term.commands"), config.COL_AMBER)
        self._rail_rects = {}
        gap = 4
        n = max(1, len(self.rail))
        bh = max(18, min(26, (inner.h - gap * (n - 1)) // n))   # pas adaptatif
        y = inner.y
        mp = pygame.mouse.get_pos()
        for label, cmd in self.rail:
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
        # badge messagerie (non-lus) — aligné à droite
        unread = inbox_mod.unread_count(p)
        if unread:
            widgets.draw_badge(surf, f"@ {unread}", (config.SCREEN_WIDTH - 70, 9),
                               config.COL_CYAN, align="right")
        widgets.draw_text(surf, f"{info['currency']}", (config.SCREEN_WIDTH - 90, 10),
                          fonts.body(bold=True), accent, align="right")

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
        inner = widgets.draw_panel(surf, rect, _t("term.health"), config.COL_AMBER)
        cur = info["currency"]
        pos_val = pf_mod.positions_value(p, self.market)
        nw = p.cash + pos_val
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
        y = inner.y
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
            widgets.draw_text_wrapped(surf, career_mod.objective_label(p, nxt), (inner.x, y),
                                      fonts.small(), config.COL_TEXT, inner.w)
        else:
            widgets.draw_text(surf, "Tous les objectifs atteints ✓", (inner.x, y),
                              fonts.small(), config.COL_UP)
        y += 44
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
