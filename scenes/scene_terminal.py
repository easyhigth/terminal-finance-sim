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
from core import dilemmas as dilemmas_mod
from core import badges as badges_mod
from core import mandates as mandates_mod
from core import unlocks as unlocks_mod
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.worldmap import WorldMap

# Noms de commandes pour l'autocomplétion (Tab) et la suggestion fantôme
CMD_NAMES = [
    "HELP", "COMMANDS", "ADV", "MISSION", "EVAL", "TRACK", "CAREER", "INBOX",
    "RIVALS", "MANDATES", "MANDATE", "DECIDE", "MARKET", "TOP", "MOVERS",
    "COMPANY", "FA", "SEARCH", "WATCHLIST", "COMPARE", "SECTOR", "REGION", "SCREEN",
    "RANKING", "BENCHMARK", "CALENDAR", "RESEARCH", "ALERT", "ALERTS",
    "PORTFOLIO", "BOOK", "BUY", "SELL", "SHORT", "COVER", "MARGIN",
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
        self.cmd_history = ["> Bienvenue. Tapez HELP, ou COMMANDS pour tout voir."]
        p = self.app.gs.player
        if p.cash == 0 and p.day == 1 and not p.cash_history:
            p.cash = config.START_CASH
            p.cash_history = [p.cash]
        # marché déterministe (créé/synchronisé)
        self.market = self.app.ensure_market()
        career_mod.ensure_objectives(p)   # objectifs du trimestre courant
        rivals_mod.ensure(p)              # concurrents
        self._check_badges()              # badges éventuellement franchis ailleurs
        self.worldmap = WorldMap()
        self.news = list(SAMPLE_NEWS.get(p.continent, SAMPLE_NEWS["USA"]))
        self.recent_events = []
        self.datawins = []        # fenêtres de données déplaçables (overlay)
        self._rail_rects = {}     # boutons du rail latéral (label -> Rect)
        self._topco_rects = {}    # sociétés cliquables (panneau top sociétés)
        self._index_rects = {}    # indices cliquables (panneau indices → graphe)
        self.rail_w = 150         # largeur du rail latéral
        self._map_rect = None     # rect de la carte (pour le clic)
        # rail latéral : (libellé, commande)
        self.rail = [
            ("ADV ▸", "ADV"), ("MISSION", "MISSION"), ("EVAL", "EVAL"),
            ("DEALS", "DEALS"), ("MARCHÉ", "MARKET"), ("TOP", "TOP"),
            ("MOVERS", "MOVERS"), ("PORTEF.", "PORTFOLIO"), ("MANDATS", "MANDATES"),
            ("TABLEUR", "SHEET"), ("ÉCO", "ECO"), ("ACADÉMIE", "LEARN"),
            ("CERTIF.", "CERT"), ("INBOX", "INBOX"), ("DÉCIDE", "DECIDE"),
            ("CARRIÈRE", "CAREER"), ("RIVAUX", "RIVALS"), ("AIDE", "COMMANDS"),
        ]
        self.networth_spark = widgets.Sparkline(80)
        for v in p.cash_history[-80:]:
            self.networth_spark.push(v)
        if not p.cash_history:
            self.networth_spark.push(p.cash)

    # --------------------------------------------------------------- events
    def handle_event(self, event):
        # 1) fenêtres de données déplaçables (la plus au-dessus d'abord)
        for w in reversed(self.datawins):
            if w.handle(event):
                if w.clicked_row is not None:
                    self._datawin_row_click(w, w.clicked_row)
                    w.clicked_row = None
                self.datawins = [x for x in self.datawins if not x.closed]
                return
        # 2) souris : rail latéral + carte
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for label, rect in self._rail_rects.items():
                if rect.collidepoint(event.pos):
                    self._run_command(dict(self.rail)[label])
                    return
            for tk, rect in self._topco_rects.items():
                if rect.collidepoint(event.pos):
                    self.app.scenes.go("company", ticker=tk, return_to="terminal")
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
                    self.app.scenes.go("company", ticker=action[1], return_to="terminal")
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
            self.app.scenes.go("company", ticker=ticker[0].upper(), return_to="terminal")

    def _open_window(self, title, columns, rows, accent=config.COL_CYAN):
        """Ouvre une fenêtre de données déplaçable (en cascade)."""
        from ui.datawindow import DataWindow
        offset = 16 * (len(self.datawins) % 6)
        pos = (self.rail_w + 30 + offset, 90 + offset)
        self.datawins.append(DataWindow(title, columns, rows, pos=pos, accent=accent))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _log(self, *lines):
        self.cmd_history += list(lines)
        self.cmd_history = self.cmd_history[-9:]

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
        if not self.entered or self.entered[-1] != raw:
            self.entered.append(raw)
            self.entered = self.entered[-30:]
        p = self.app.gs.player

        # verrou par grade : certaines actions se débloquent en progressant
        feat = unlocks_mod.CMD_FEATURE.get(cmd)
        if feat and not unlocks_mod.unlocked(p, feat):
            g = unlocks_mod.required_grade(feat)
            self._log(f"  🔒 {unlocks_mod.feature_label(feat)}",
                      f"     débloqué au grade {config.GRADES[g]} (vous : {p.grade}).")
            return

        if cmd == "HELP":
            self._log(
                "  ADV avancer · COMMANDS catalogue complet",
                "  MARKET indices · TOP [region] · MOVERS",
                "  COMPANY <tk> · SEARCH · WATCHLIST · COMPARE",
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
        elif cmd == "TOP":
            self._cmd_top(arg)
        elif cmd in ("MOVERS", "MOVER"):
            self._cmd_movers()
        elif cmd in ("COMPANY", "CO", "TICKER", "DES"):
            self._cmd_company(arg)
        elif cmd in ("FA", "FIN", "STATEMENTS", "ETATS"):
            self._cmd_financials(arg)
        elif cmd in ("GP", "CHART", "GRAPH"):
            self._cmd_chart(arg)
        elif cmd in ("RV", "PEERS", "COMPS"):
            self._cmd_rv(arg)
        elif cmd in ("ECO", "MACRO", "ECONOMY"):
            self._cmd_eco()
        elif cmd in ("LEARN", "ACADEMY", "ACADEMIE", "APPRENDRE"):
            self.app.scenes.go("academy", return_to="terminal")
        elif cmd in ("CERT", "CERTS", "CERTIFICATIONS", "CFA", "FRM"):
            self.app.scenes.go("cert", return_to="terminal")
        elif cmd in ("DEFINE", "DEF", "GLO"):
            self._cmd_define(parts[1:])
        elif cmd in ("SEARCH", "FIND"):
            self._cmd_search(parts[1:])
        elif cmd == "DEALS":
            self._cmd_deals()
        elif cmd == "DEAL":
            self._cmd_deal(arg)
        elif cmd in ("EVAL", "EVALUATION"):
            self._cmd_eval()
        elif cmd in ("GLOSSARY", "GLOSSAIRE"):
            self.app.scenes.go("glossary", return_to="terminal")
        elif cmd in ("PORTFOLIO", "PORTEFEUILLE", "BOOK", "POSITIONS", "PRT"):
            self.app.scenes.go("book", return_to="terminal")
        elif cmd in ("FRONTIER", "MARKOWITZ", "FRONTIERE"):
            self.app.scenes.go("portfolio")
        elif cmd in ("BUY", "ACHETER"):
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
                self._log("  Aucune décision en attente.")
        elif cmd in ("RIVALS", "RIVAUX", "LEADERBOARD"):
            self._cmd_rivals()
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
                self._log("  Voies disponibles à partir du grade Analyst.")
        elif cmd == "STATUS":
            info = config.CONTINENTS[p.continent]
            self._log(
                f"  Nom        : {p.name}",
                f"  Grade      : {p.grade}  |  Voie : {p.track}",
                f"  Trésorerie : {widgets.format_money(p.cash, info['currency'])}",
                f"  Réputation : {p.reputation}/100",
                f"  Temps      : jour {p.day} (T{p.quarter})",
            )
        elif cmd == "SAVE":
            if p.hardcore:
                self._log("  [HARDCORE] Sauvegarde manuelle désactivée.")
            else:
                self.app.gs.save(config.SAVE_SLOTS[0])
                self._log(f"  Partie sauvegardée (slot: {config.SAVE_SLOTS[0]}).")
        elif cmd == "NEWS":
            import random
            random.shuffle(self.news)
            self._log("  Flux d'actualités rafraîchi.")
        elif cmd == "REG":
            info = config.CONTINENTS[p.continent]
            self._log(f"  Régulateur : {info['regulator']}",
                      f"  Cadre      : {info['framework']}")
        elif cmd == "MENU":
            self.app.scenes.go("menu")
        else:
            self._log(f"  Commande inconnue : {raw}. Tapez COMMANDS.")

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
        self._log("  Indices ouverts (fenêtre).")

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
            self._log("  Usage : COMPANY <ticker>  (ex: COMPANY MVC).")
            return
        if self.market.price_of(ticker.upper()) is None:
            self._log(f"  Ticker inconnu : {ticker.upper()}. Essayez SEARCH.")
            return
        self.app.scenes.go("company", ticker=ticker.upper(), return_to="terminal")

    def _cmd_financials(self, ticker):
        """FA <ticker> : états financiers complets (bilan + compte de résultat)."""
        if not ticker:
            self._log("  Usage : FA <ticker>  (états financiers ; ex: FA MVC).")
            return
        if self.market.price_of(ticker.upper()) is None:
            self._log(f"  Ticker inconnu : {ticker.upper()}. Essayez SEARCH.")
            return
        self.app.scenes.go("financials", ticker=ticker.upper(), return_to="terminal")

    def _cmd_search(self, terms):
        q = " ".join(terms) if terms else ""
        if not q:
            self._log("  Usage : SEARCH <nom ou ticker>.")
            return
        res = self.market.search(q)
        if not res:
            self._log(f"  Aucune société pour « {q} ».")
        else:
            self._log(f"  Résultats : {', '.join(res)}")

    def _cmd_chart(self, ticker):
        """GP — graphe de prix d'une société (fenêtre déplaçable)."""
        if not ticker:
            self._log("  Usage : GP <ticker>  (graphe de prix).")
            return
        tk = ticker.upper()
        if self.market.price_of(tk) is None:
            self._log(f"  Ticker inconnu : {tk}.")
            return
        from ui.datawindow import DataWindow
        hist = self.market.track_company(tk)
        self.datawins.append(DataWindow(f"{tk} — cours", [], [],
                                        pos=(self.rail_w + 60, 110),
                                        accent=config.COL_AMBER, chart=list(hist)))
        self.datawins = self.datawins[-5:]
        if len(hist) < 2:
            self._log(f"  {tk} : historique en constitution (ADV pour le remplir).")

    def _cmd_rv(self, ticker):
        """RV — valeur relative : multiples de la société vs médianes du secteur."""
        if not ticker:
            self._log("  Usage : RV <ticker>  (valeur relative vs pairs).")
            return
        mt = self.market.metrics(ticker.upper())
        if not mt:
            self._log(f"  Ticker inconnu : {ticker.upper()}.")
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
            self._log("  Usage : DEFINE <terme>  (ex: DEFINE WACC). Voir aussi GLOSSARY.")
            return
        from data.glossary_data import GLOSSARY
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
            self._log(f"  « {q} » introuvable au glossaire. Tapez GLOSSARY pour parcourir.")
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

    def _cmd_eval(self):
        """Ouvre l'examen si TOUS les critères de promotion sont remplis."""
        p = self.app.gs.player
        if not p.can_promote():
            self._log("  Vous êtes au grade maximal : aucune promotion possible.")
            return
        if not career_mod.promotion_ready(p):
            self._log("  Critères de promotion non remplis :")
            for r in career_mod.promotion_requirements(p):
                if not r["met"]:
                    self._log(f"   ○ {r['label']} : {int(r['current'])}/{int(r['target'])}")
            self._log("  Voir CAREER pour la roadmap complète.")
            return
        self.app.scenes.go("evaluation")

    # ---------------------------------------------------- commandes lecture
    def _cmd_watchlist(self, args):
        p = self.app.gs.player
        if not args:
            if not p.watchlist:
                self._log("  Watchlist vide. WATCHLIST ADD <ticker> pour suivre une valeur.")
                return
            rows = []
            for tk in p.watchlist:
                mt = self.market.metrics(tk)
                if mt:
                    ccol = config.COL_UP if mt["change_pct"] >= 0 else config.COL_DOWN
                    rows.append(((tk, config.COL_AMBER), f"{mt['price']:.2f}",
                                 (f"{mt['change_pct']:+.1f}%", ccol), mt["sector"]))
            self._open_window("WATCHLIST", [("Tk", 60), ("Cours", 70),
                                            ("Var.", 70), ("Secteur", 90)], rows)
            return
        op = args[0].upper()
        tk = args[1].upper() if len(args) > 1 else None
        if op in ("ADD", "+") and tk:
            if self.market.price_of(tk) is None:
                self._log(f"  Ticker inconnu : {tk}.")
            elif tk in p.watchlist:
                self._log(f"  {tk} est déjà dans la watchlist.")
            else:
                p.watchlist.append(tk)
                self.market.track_company(tk)
                self._log(f"  {tk} ajouté à la watchlist.")
        elif op in ("REMOVE", "RM", "-") and tk:
            if tk in p.watchlist:
                p.watchlist.remove(tk)
                self._log(f"  {tk} retiré de la watchlist.")
            else:
                self._log(f"  {tk} n'est pas dans la watchlist.")
        else:
            self._log("  Usage : WATCHLIST [ADD|REMOVE <ticker>]")

    def _cmd_compare(self, args):
        if len(args) < 2:
            self._log("  Usage : COMPARE <ticker1> <ticker2>")
            return
        a, b = args[0].upper(), args[1].upper()
        ma, mb = self.market.metrics(a), self.market.metrics(b)
        if not ma or not mb:
            self._log("  Un des tickers est inconnu.")
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
            self._log("  Secteurs : " + secs[:60], "  " + secs[60:])
            return
        key = None
        for s in self.market.sectors:
            if s.lower().startswith(name.lower()):
                key = s
                break
        if not key:
            self._log(f"  Secteur inconnu : {name}.")
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
        self._log(f"  Région {region} — indices : {', '.join(idxs)}")
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
        self._log(f"  Benchmark régional {ref} : {perf:+.1f}% depuis le suivi.")
        self._log(f"  Votre trésorerie : {widgets.format_money(p.cash, config.CONTINENTS[p.continent]['currency'])} "
                  f"(record {widgets.format_money(max(p.best_cash, p.cash), config.CONTINENTS[p.continent]['currency'])}).")

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

    def _cmd_rivals(self):
        p = self.app.gs.player
        cur = self._cur()
        board = rivals_mod.leaderboard(p, self.market)
        rows = []
        for row in board:
            col = config.COL_AMBER if row["is_player"] else config.COL_TEXT
            rows.append((f"{row['rank']}", (row["name"][:20], col),
                         widgets.format_money(row["score"], cur)))
        self._open_window("CLASSEMENT — rivaux",
                          [("#", 30), ("Banquier", 160), ("Score", 90)],
                          rows, accent=config.COL_PRESTIGE)

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
        self._log("  MANDATE ACCEPT <id> / MANDATE DECLINE <id> pour gérer.")

    def _cmd_mandate(self, args):
        p = self.app.gs.player
        if len(args) < 2 or not args[1].isdigit():
            self._log("  Usage : MANDATE ACCEPT|DECLINE <id>")
            return
        op, mid = args[0].upper(), int(args[1])
        if op in ("ACCEPT", "ACCEPTER"):
            res = mandates_mod.accept(p, mid, self.market)
            if res == "full":
                self._log(f"  Déjà {mandates_mod.MAX_ACTIVE} mandats en cours.")
            elif res:
                self._log(f"  ✓ Mandat #{mid} accepté : {res['client']} — objectif "
                          f"+{res['target_pct']:.0f}% en {res['horizon']}T, bêta ≤ {res['max_beta']:.2f}.")
                career_mod.log(p, "deal", f"Mandat accepté : {res['client']}")
            else:
                self._log(f"  Offre #{mid} introuvable.")
        elif op in ("DECLINE", "REFUSER"):
            self._log("  Offre déclinée." if mandates_mod.decline(p, mid)
                      else f"  Offre #{mid} introuvable.")
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    # ------------------------------------------------------------- recherche
    def _cmd_research(self, ticker):
        p = self.app.gs.player
        if not ticker:
            self._log("  Usage : RESEARCH <ticker>")
            return
        tk = ticker.upper()
        mt = self.market.metrics(tk)
        if not mt:
            self._log(f"  Ticker inconnu : {tk}.")
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
        self._log(f"  Recherche {tk} : valeur intrinsèque {fair:.2f} "
                  f"(potentiel {upside:+.0f}%) → {rating}.")
        self.app.notify(f"{tk} : {rating} ({upside:+.0f}%)",
                        "good" if rating == "ACHAT" else "bad" if rating == "VENTE" else "info")

    # ------------------------------------------------------------- alertes
    def _cmd_alert(self, args):
        p = self.app.gs.player
        if len(args) < 2:
            self._log("  Usage : ALERT <ticker> <prix>")
            return
        tk = args[0].upper()
        try:
            price = float(args[1].replace(",", "."))
        except ValueError:
            self._log("  Prix invalide.")
            return
        cur_price = self.market.price_of(tk)
        if cur_price is None:
            self._log(f"  Ticker inconnu : {tk}.")
            return
        self.market.track_company(tk)
        p.alerts.append({"ticker": tk, "price": price, "above": price > cur_price})
        sens = "au-dessus de" if price > cur_price else "en-dessous de"
        self._log(f"  Alerte posée : {tk} {sens} {price:.2f} (cours {cur_price:.2f}).")

    def _cmd_alerts(self):
        p = self.app.gs.player
        if not p.alerts:
            self._log("  Aucune alerte active.")
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
                self._log(f"  🔔 ALERTE {a['ticker']} : cours {price:.2f} a franchi {a['price']:.2f}.")
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
            self.app.notify(f"🏅 Badge : {b['name']}", "prestige")
            career_mod.log(self.app.gs.player, "info", f"Badge débloqué : {b['name']}")

    def _cmd_buy(self, args):
        if len(args) < 2 or not args[1].lstrip("-").isdigit():
            self._log("  Usage : BUY <ticker> <quantité>")
            return
        tk, qty = args[0].upper(), int(args[1])
        res = pf_mod.buy(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            reason = {"ticker": "ticker inconnu", "qty": "quantité invalide",
                      "isshort": f"position courte ouverte sur {tk} — utilisez COVER",
                      "leverage": f"levier max atteint ({res.get('max_leverage',0):.1f}x)"
                      }.get(res["reason"], res["reason"])
            self._log(f"  Achat refusé : {reason}.")
            return
        self._log(f"  ✓ Achat {qty} {tk} @ {res['price']:.2f} = "
                  f"{widgets.format_money(res['total'], self._cur())} (frais inclus).")
        if res["total"] > 60000:
            career_mod.log(self.app.gs.player, "deal", f"Achat {qty} {tk}")
        self._after_trade()

    def _cmd_sell(self, args):
        if not args:
            self._log("  Usage : SELL <ticker> <quantité|ALL>")
            return
        tk = args[0].upper()
        qty = "ALL"
        if len(args) > 1 and args[1].upper() != "ALL":
            if not args[1].isdigit():
                self._log("  Quantité invalide.")
                return
            qty = int(args[1])
        res = pf_mod.sell(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            self._log(f"  Vente refusée : {'aucune position' if res['reason']=='noposition' else res['reason']}.")
            return
        sign = "+" if res["realized"] >= 0 else ""
        self._log(f"  ✓ Vente {int(res['qty'])} {tk} @ {res['price']:.2f} = "
                  f"{widgets.format_money(res['net'], self._cur())}  "
                  f"(P&L réalisé {sign}{widgets.format_money(res['realized'], self._cur())}).")
        self._after_trade()

    def _cmd_short(self, args):
        """SHORT <ticker> <quantité> : vente à découvert (pari à la baisse)."""
        if len(args) < 2 or not args[1].isdigit():
            self._log("  Usage : SHORT <ticker> <quantité>  (parier à la baisse)")
            return
        tk, qty = args[0].upper(), int(args[1])
        res = pf_mod.short(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            reason = {"ticker": "ticker inconnu", "qty": "quantité invalide",
                      "islong": f"position longue ouverte sur {tk} — vendez-la d'abord",
                      "leverage": f"levier max atteint ({res.get('max_leverage',0):.1f}x)"
                      }.get(res["reason"], res["reason"])
            self._log(f"  Short refusé : {reason}.")
            return
        self._log(f"  ✓ Short {qty} {tk} @ {res['price']:.2f} = "
                  f"+{widgets.format_money(res['net'], self._cur())} en cash "
                  "(à racheter via COVER).")
        self._after_trade()

    def _cmd_cover(self, args):
        """COVER <ticker> <quantité|ALL> : rachète une position courte."""
        if not args:
            self._log("  Usage : COVER <ticker> <quantité|ALL>")
            return
        tk = args[0].upper()
        qty = "ALL"
        if len(args) > 1 and args[1].upper() != "ALL":
            if not args[1].isdigit():
                self._log("  Quantité invalide.")
                return
            qty = int(args[1])
        res = pf_mod.cover(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            self._log(f"  Rachat refusé : {'aucune position courte' if res['reason']=='noshort' else res['reason']}.")
            return
        sign = "+" if res["realized"] >= 0 else ""
        self._log(f"  ✓ Cover {int(res['qty'])} {tk} @ {res['price']:.2f} "
                  f"(P&L réalisé {sign}{widgets.format_money(res['realized'], self._cur())}).")
        self._after_trade()

    def _cmd_margin(self):
        """MARGIN : état de la marge (equity, exposition, levier, pouvoir d'achat)."""
        st = pf_mod.margin_status(self.app.gs.player, self.market)
        cur = self._cur()
        lev = "∞" if st["leverage"] == float("inf") else f"{st['leverage']:.2f}x"
        self._log(f"  Marge — equity {widgets.format_money(st['equity'], cur)} · "
                  f"exposition {widgets.format_money(st['gross'], cur)} · levier {lev} "
                  f"(max {st['max_leverage']:.1f}x)")
        self._log(f"  Pouvoir d'achat {widgets.format_money(st['buying_power'], cur)} · "
                  f"capital emprunté {widgets.format_money(st['borrowed'], cur)}"
                  + ("  ⚠ APPEL DE MARGE IMMINENT" if st["margin_call"] else ""))

    def _cmd_allocate(self, args):
        """ALLOCATE <ticker> <pct> : ajuste la position à pct% de la valeur nette."""
        if len(args) < 2 or not args[1].replace(".", "").isdigit():
            self._log("  Usage : ALLOCATE <ticker> <pourcentage>")
            return
        p = self.app.gs.player
        tk = args[0].upper()
        pct = float(args[1])
        price = self.market.price_of(tk)
        if price is None:
            self._log(f"  Ticker inconnu : {tk}.")
            return
        nw = pf_mod.net_worth(p, self.market)
        target_val = nw * pct / 100.0
        cur_shares = p.portfolio.get(tk, {}).get("shares", 0)
        cur_val = cur_shares * price
        diff = target_val - cur_val
        if abs(diff) < price:
            self._log("  Position déjà proche de la cible.")
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
            self._log("  Aucune position à couvrir.")
            return
        beta = pf_mod.portfolio_beta(p, self.market)
        if arg is None or not arg.replace(".", "").isdigit():
            self._log(f"  Bêta du portefeuille : {beta:.2f}. "
                      "HEDGE <pct> pour réduire l'exposition (vendre une part vers le cash).")
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
        self._log(f"  Couverture : exposition réduite de {pct:.0f}%. "
                  f"Nouveau bêta {pf_mod.portfolio_beta(p, self.market):.2f}.")
        self._after_trade()

    def _cmd_rebalance(self):
        """REBALANCE : ramène les positions à poids égaux."""
        p = self.app.gs.player
        if len(p.portfolio) < 2:
            self._log("  Rééquilibrage : au moins 2 positions nécessaires.")
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
        self._log(f"  Portefeuille rééquilibré à poids égaux ({len(p.portfolio)} lignes).")
        self._after_trade()

    def _cmd_pitch(self):
        """PITCH : démarche un client pour décrocher un mandat (selon réputation)."""
        import random
        p = self.app.gs.player
        prob = 0.3 + 0.5 * (p.reputation / 100.0)
        if random.random() < prob:
            d = deals_mod.maybe_generate(p)
            if d:
                self._log(f"  ✓ Pitch réussi : nouveau mandat #{d[0]['id']} — {d[0]['title']}.")
            else:
                self._log("  ✓ Pitch réussi, mais votre pipeline de deals est déjà plein.")
        else:
            p.adjust_reputation(-1)
            self._log("  ✗ Pitch infructueux. Le client passe son tour (-1 réputation).")
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
        # concurrents : progression + sniping des deals expirés
        rivals_mod.step(p, m)
        for d in summary["expired"]:
            rival = rivals_mod.snipe(p, d, random)
            inbox_mod.on_deal_sniped(p, d, rival)
            career_mod.log(p, "deal", f"{rival} rafle « {d['title']} »")
        self._log(f"  +{config.DAYS_PER_STEP}j → jour {p.day} (T{p.quarter}). "
                  f"Solde du tour : {widgets.format_money(summary['net'], cur)}")
        if summary.get("dividends", 0) > 0:
            self._log(f"  💰 Dividendes encaissés : +{widgets.format_money(summary['dividends'], cur)}")
        # débrief « pourquoi mon portefeuille a bougé » : attribution par facteur
        if p.portfolio:
            holdings = {t: pos["shares"] for t, pos in p.portfolio.items()}
            attr = m.factor_attribution(holdings)
            if abs(attr["total"]) > 1.0:
                fm_ = lambda v: widgets.format_money(v, cur)
                own = attr["specific"] + attr["drift"]   # part propre + dérive de base
                self._log(f"  📊 Positions {fm_(attr['total'])} = marché {fm_(attr['world'])}"
                          f" · secteur {fm_(attr['sector'])} · région {fm_(attr['region'])}"
                          f" · propre {fm_(own)}")
        # financement (intérêts sur marge + frais de short) et appel de marge
        fin = summary.get("financing")
        if fin and fin["total"] > 1.0:
            self._log(f"  💸 Frais de financement : -{widgets.format_money(fin['total'], cur)} "
                      f"(intérêts marge + emprunt de titres).")
        mc = summary.get("margin_call")
        if mc:
            self._log(f"  ⚠ APPEL DE MARGE : liquidation forcée de "
                      f"{widgets.format_money(mc['liquidated'], cur)} "
                      f"(pénalité {widgets.format_money(mc['penalty'], cur)}).")
            self.app.notify("Appel de marge : liquidation forcée", "bad")
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
            self._log(f"  ✕ Deal expiré : {d['title']} (raflé par un rival)")
        # crise/boom : narration (carte + flux + journal + inbox)
        if scenario:
            self.worldmap.push_news([{"region": None, "kind": scenario["kind"],
                                      "text": scenario["name"]}])
            self.recent_events.insert(0, {"title": "⚠ " + scenario["name"],
                                          "kind": scenario["kind"], "cash": 0, "rep": 0})
            self._log(f"  ⚠ ÉVÉNEMENT : {scenario['name']} — {scenario['story'][:50]}…")
            inbox_mod.on_crisis(p, scenario["name"], scenario["kind"])
            career_mod.log(p, "crisis", scenario["name"])
            self.app.notify(scenario["name"], scenario["kind"])
            if scenario["kind"] == "bad":
                p.flags["crises"] = p.flags.get("crises", 0) + 1
        if summary.get("quarter_changed"):
            self._log(f"  ── Nouveau trimestre : T{p.quarter} ──")
            qr = summary.get("quarter_report")
            if qr and qr["total"]:
                self._log(f"  Bilan T{p.quarter-1} : {qr['done']}/{qr['total']} objectifs, "
                          f"+{qr['rep']} rép, +{widgets.format_money(qr['cash'], cur)}")
            inbox_mod.on_quarter(p, summary.get("quarter_report"))
            hot = p.flags.get("hot_sector")
            if hot:
                self._log(f"  ★ Secteur à surveiller ce trimestre : {hot}.")
                self.app.notify(f"Secteur du trimestre : {hot}", "info")
            # mandats arrivés à échéance
            for res in mandates_mod.evaluate_due(p, m):
                mm = res["mandate"]
                if res["ok"]:
                    self._log(f"  ✓ MANDAT réussi : {mm['client']} (+{res['growth']:.1f}%) "
                              f"→ +{widgets.format_money(mm['reward_cash'], cur)}, rép +{mm['reward_rep']}.")
                    self.app.notify(f"Mandat réussi : {mm['client']}", "good")
                    inbox_mod.push(p, "client", mm["client"], "Mandat rempli avec succès",
                                   f"Performance de {res['growth']:.1f}% conforme à nos attentes. "
                                   "Commission versée. Au plaisir de retravailler ensemble.")
                else:
                    self._log(f"  ✗ MANDAT échoué : {mm['client']} (rép -{mm['penalty_rep']}).")
                    self.app.notify(f"Mandat échoué : {mm['client']}", "bad")
                    inbox_mod.push(p, "client", mm["client"], "Mandat non rempli",
                                   "Les objectifs n'ont pas été atteints. Nous confions "
                                   "désormais notre capital ailleurs.")
        # nouvelle offre de mandat éventuelle
        offer = mandates_mod.maybe_offer(p, random)
        if offer:
            self._log(f"  ★ OFFRE DE MANDAT : {offer['client']} — {widgets.format_money(offer['capital'], cur)} "
                      f"(MANDATES pour voir).")
            self.app.notify(f"Offre de mandat : {offer['client']}", "info")
            inbox_mod.push(p, "client", offer["client"], "Proposition de mandat",
                           f"Nous souhaitons vous confier {widgets.format_money(offer['capital'], cur)} : "
                           f"objectif +{offer['target_pct']:.0f}% en {offer['horizon']} trimestres, "
                           f"bêta ≤ {offer['max_beta']:.2f}. Tapez MANDATES puis MANDATE ACCEPT {offer['id']}.")
        # alertes de prix
        self._check_alerts()
        for d in summary["new_deals"]:
            self._log(f"  ★ Nouveau deal #{d['id']} : {d['title']} ({d['days_left']}j)")
        # messages d'ambiance / conformité
        inbox_mod.on_step(p, m, summary, random)
        # scrutin réglementaire : décroissance + risque d'enquête
        inv = dilemmas_mod.maybe_investigate(p, random)
        if inv:
            self._log(f"  ⚠ ENQUÊTE RÉGLEMENTAIRE : amende "
                      f"{widgets.format_money(inv['fine'], cur)}, réputation -{inv['rep_loss']}.")
            self.app.notify("Enquête réglementaire : sanction", "bad")
        # dilemme éventuel à trancher
        dil = dilemmas_mod.maybe_trigger(p, random)
        if dil:
            self._log(f"  ⚖ DÉCISION REQUISE : {dil['title']} — tapez DECIDE.")
            self.app.notify(f"Décision requise : {dil['title']}", "warn")
        # bilan de trimestre / quarter en toast
        if summary.get("quarter_changed") and summary.get("quarter_report") \
                and summary["quarter_report"]["total"]:
            qr = summary["quarter_report"]
            self.app.notify(f"Bilan T{p.quarter-1} : {qr['done']}/{qr['total']} objectifs", "info")
        # badges éventuels
        self._check_badges()
        unread = inbox_mod.unread_count(p)
        if unread:
            self._log(f"  ✉ {unread} message(s) non lu(s) — tapez INBOX.")
        if not p.hardcore:
            gs.save(config.AUTOSAVE_SLOT)
        if summary["game_over"] or p.check_game_over():
            self.app.scenes.go("gameover")
        elif dil:
            self.app.scenes.go("dilemma", return_to="terminal")

    def _cmd_deals(self):
        p = self.app.gs.player
        if not p.deals:
            self._log("  Aucun deal en cours. Avancez le temps (ADV) pour en générer.")
            return
        cur = config.CONTINENTS[p.continent]["currency"]
        self._log("  Deals en cours :")
        for d in p.deals:
            prob = deals_mod.success_probability(p, d)
            self._log(f"   #{d['id']} {d['title']} [{d['kind']}] {d['days_left']}j  "
                      f"gain {widgets.format_money(d['reward_cash'], cur)} p={int(prob*100)}%")

    def _cmd_deal(self, arg):
        p = self.app.gs.player
        if arg is None or not arg.isdigit():
            self._log("  Usage : DEAL <id>  (voir DEALS).")
            return
        if deals_mod.find_deal(p, int(arg)) is None:
            self._log(f"  Deal #{arg} introuvable.")
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
        console_h = 74
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

        self._draw_console(surf, console_h)

        # overlay : fenêtres de données déplaçables
        for w in self.datawins:
            w.draw(surf)

    def _draw_rail(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, "Commandes", config.COL_AMBER)
        self._rail_rects = {}
        bh = 26
        gap = 4
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
            if locked:
                g = unlocks_mod.required_grade(unlocks_mod.CMD_FEATURE[cmd])
                widgets.draw_text(surf, f"🔒 {label}", (br.x + 8, br.y + 7),
                                  fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"G{g}", (br.right - 8, br.y + 7),
                                  fonts.tiny(), config.COL_TEXT_DIM, align="right")
            else:
                txt = label
                if cmd == "INBOX":
                    u = inbox_mod.unread_count(p)
                    if u:
                        txt = f"{label} ({u})"
                elif cmd == "DECIDE" and p.pending_dilemmas:
                    txt = f"{label} !"
                widgets.draw_text(surf, txt, (br.x + 10, br.y + 7),
                                  fonts.small(bold=hover), acc if hover else config.COL_TEXT)
            y += bh + gap

    def _draw_topbar(self, surf, p, info, accent):
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, (0, 0, config.SCREEN_WIDTH, config.TOPBAR_H))
        pygame.draw.line(surf, accent, (0, config.TOPBAR_H), (config.SCREEN_WIDTH, config.TOPBAR_H), 1)
        widgets.draw_text(surf, "TERMINAL", (12, 8), fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_ticker_value(surf, "GRADE", p.grade, (190, 12))
        cash_col = config.COL_UP if p.cash >= 0 else config.COL_DOWN
        widgets.draw_text(surf, "CASH ", (400, 12), fonts.small(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.format_money(p.cash, info["currency"]),
                          (448, 12), fonts.small(bold=True), cash_col)
        widgets.draw_ticker_value(surf, "REP", f"{p.reputation}/100", (640, 12))
        widgets.draw_ticker_value(surf, "DAY", f"{p.day} (T{p.quarter})", (800, 12))
        # badge messagerie (non-lus)
        unread = inbox_mod.unread_count(p)
        if unread:
            widgets.draw_badge(surf, f"✉ {unread}", (config.SCREEN_WIDTH - 70, 9),
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
                                   f"Indices · {self.market.regime_label()}", config.COL_AMBER)
        self._index_rects = {}
        defs = self.market.index_defs
        n = max(1, len(defs))
        step = max(26, min(50, inner.h // n))
        spark_h = max(8, step - 20)
        mp = pygame.mouse.get_pos()
        y = inner.y
        for name, *_ in defs:
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

    def _draw_health(self, surf, rect, p, info):
        inner = widgets.draw_panel(surf, rect, "Santé financière", config.COL_AMBER)
        cur = info["currency"]
        pos_val = pf_mod.positions_value(p, self.market)
        nw = p.cash + pos_val
        upnl = pf_mod.unrealized_pnl(p, self.market)
        nw_col = config.COL_UP if nw >= 0 else config.COL_DOWN
        widgets.draw_text(surf, "Valeur nette", (inner.x, inner.y), fonts.small(bold=True), config.COL_TEXT_DIM)
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
        inner = widgets.draw_panel(surf, rect, "Flux & événements", config.COL_CYAN)
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
        inner = widgets.draw_panel(surf, rect, f"Top sociétés — {p.continent}", config.COL_CYAN)
        cur = config.CONTINENTS[p.continent]["currency"]
        self._topco_rects = {}
        mp = pygame.mouse.get_pos()
        y = inner.y
        n = max(6, (inner.h - 20) // 28)
        for c in self.market.top_companies(region=p.continent, n=n):
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 26)
            self._topco_rects[c["ticker"]] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            widgets.draw_text(surf, c["ticker"], (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, c["name"][:16], (inner.x + 58, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, widgets.format_money(c["mktcap"] * 1e6, cur), (inner.right, y),
                              fonts.tiny(bold=True), config.COL_WHITE, align="right")
            y += 28
        widgets.draw_text(surf, "clic → fiche · COMPANY <tk>", (inner.x, inner.bottom - 14),
                          fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_career(self, surf, rect, p):
        """Panneau PRIORITÉS : prochain objectif, promotion, risque, opportunité."""
        # couleur de priorité du panneau selon le danger le plus pressant
        marge0 = p.cash - config.BANKRUPTCY_CASH
        prio = None
        if p.reputation < 20 or marge0 < 120000 or p.heat >= 55:
            prio = config.COL_PRIO_CRITICAL
        elif p.pending_dilemmas or any(d["days_left"] <= config.DAYS_PER_STEP * 2 for d in p.deals):
            prio = config.COL_PRIO_URGENT
        inner = widgets.draw_panel(surf, rect, "Priorités", config.COL_AMBER, prio=prio)
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

    def _draw_console(self, surf, height=74):
        rect = pygame.Rect(config.MARGIN, config.SCREEN_HEIGHT - height - config.MARGIN,
                           config.SCREEN_WIDTH - 2 * config.MARGIN, height)
        pygame.draw.rect(surf, (6, 8, 12), rect)
        pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
        y = rect.y + 5
        for line in self.cmd_history[-3:]:
            widgets.draw_text(surf, line, (rect.x + 10, y), fonts.small(), config.COL_AMBER_DIM)
            y += 15
        cursor = "_" if int(self.t * 2) % 2 == 0 else " "
        r = widgets.draw_text(surf, f"CMD> {self.cmd}", (rect.x + 10, rect.bottom - 20),
                              fonts.small(bold=True), config.COL_AMBER)
        # suggestion fantôme (Tab pour compléter)
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
