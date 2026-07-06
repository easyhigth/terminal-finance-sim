"""
scene_terminal_commands.py — TerminalCommandsMixin : catalogue des commandes
(CMD_NAMES pour l'autocomplétion) et le dispatcher `_run_command`, qui route
chaque commande tapée vers une scène ou une méthode `_cmd_*` fournie par les
autres mixins (market/trading/career). Extrait de scene_terminal.py
(découpage en mixins, même principe que scene_terminal_market/_trading/
_career/_time/_render/_windows).
"""
from core import config
from core import unlocks as unlocks_mod
from core.i18n import get_lang
from ui import widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


# Noms de commandes pour l'autocomplétion (Tab) et la suggestion fantôme
CMD_NAMES = [
    "HELP", "COMMANDS", "MISSION", "EVAL", "EXAMCERT", "TRACK", "CAREER", "INBOX",
    "RIVALS", "RECLAIM", "RECONVERT", "MANDATES", "MANDATE", "DECIDE", "MARKET", "MARKETHUB", "WALL", "DESKTOP", "BUREAU", "HOURS", "TOP", "MOVERS",
    "COMPANY", "FA", "SEARCH", "ACCESS", "EXPLORE", "SHOP", "WATCHLIST", "COMPARE", "SECTOR", "REGION", "SCREEN",
    "RANKING", "BENCHMARK", "CALENDAR", "RESEARCH", "ALERT", "ALERTS", "LEGACY", "ARCHETYPE",
    "TENSION", "CRISIS",
    "PORTFOLIO", "BOOK", "BUY", "SELL", "LONG", "SHORT", "COVER", "TWAP", "PENDING", "MARGIN",
    "BONDS", "BUYBOND", "SELLBOND", "GOV", "GOVERNMENTS", "PAYS",
    "CMDTY", "BUYCMDTY", "SELLCMDTY",
    "CRYPTO", "BUYCRYPTO", "SELLCRYPTO", "ETF", "ETFS", "BUYETF", "SELLETF",
    "STRUCT", "CREDIT", "ALM", "SWAP", "SWAPS",
    "ALLOCATE", "HEDGE", "PROTECT", "OPTIONS", "IPO", "FX", "AGENDA", "PRONOS", "REVIEW", "REBALANCE",
    "PITCH", "FRONTIER", "RISK", "QUANT", "MA", "SHEET", "GLOSSARY",
    "SAVE", "SAVES", "NEWS", "MORE", "SHORTCUTS", "SETTINGS", "REGLAGES", "REG", "STATUS", "MENU",
    "TEAM", "EQUIPE", "STRESS", "TIMELINE",
    "GP", "GPC", "GPO", "GPCH", "COMP", "HS", "HVOL", "BETA", "CORR",
    "GEG", "GC", "RV", "ECO", "DEFINE", "PA", "ATTR",
    "TRADES", "NOTE", "IDEAS", "CRITERIA", "JSTATS", "ACHIEVEMENTS", "SUCCES", "BADGES",
    "STATS",
]


class TerminalCommandsMixin:

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
            g = unlocks_mod.effective_required_grade(p, feat)
            lines = [_L(f"  ⊘ {unlocks_mod.feature_label(feat)}", f"  ⊘ {unlocks_mod.feature_label(feat)}"),
                     _L(f"     débloqué au grade {config.GRADES[g]} (vous : {p.grade}).",
                        f"     unlocked at grade {config.GRADES[g]} (you: {p.grade}).")]
            track_note = unlocks_mod.track_lock_note(p, feat)
            if track_note:
                lines.append(track_note)
            tid = unlocks_mod.FEATURE_TUTORIAL.get(feat)
            if tid:
                lines.append(_L(f"     en attendant, tapez TUTO {tid} pour voir comment ça marche.",
                                 f"     in the meantime, type TUTO {tid} to see how it works."))
            self._log(*lines)
            return

        if cmd == "HELP":
            # asymétrie novice/expert : un stagiaire (grade < 2, non vétéran) voit
            # un HELP court, focalisé sur l'essentiel — pas la cinquantaine de
            # commandes du catalogue complet, dont la plupart sont encore verrouillées.
            novice = p.grade_index < 2 and not p.flags.get("veteran")
            if novice:
                if get_lang() == "en":
                    self._log(
                        "  COMMANDS full catalogue · the clock runs live (||/▶/▶▶/▶▶▶ top-right)",
                        "  MARKET indices · COMPANY <tk> · SEARCH · WATCHLIST",
                        "  MISSION work · CAREER career · EVAL promotion",
                        "  LEARN academy · GLOSSARY · DEFINE <term>",
                        "  INBOX messages · STATUS · SAVE · MENU",
                        "  → more commands (trading, derivatives, M&A...) unlock as you "
                        "are promoted. Type COMMANDS to see everything.",
                        "  ✶ TIP: press Ctrl+K anywhere to jump to a page or asset by name.",
                    )
                else:
                    self._log(
                        "  COMMANDS catalogue complet · le temps avance en direct (||/▶/▶▶/▶▶▶ en haut à droite)",
                        "  MARKET indices · COMPANY <tk> · SEARCH · WATCHLIST",
                        "  MISSION travailler · CAREER carrière · EVAL promotion",
                        "  LEARN académie · GLOSSARY · DEFINE <terme>",
                        "  INBOX messagerie · STATUS · SAVE · MENU",
                        "  → d'autres commandes (trading, dérivés, M&A...) se débloquent "
                        "en progressant. Tapez COMMANDS pour tout voir.",
                        "  ✶ ASTUCE : Ctrl+K ouvre n'importe où une recherche rapide (page, actif…).",
                    )
                return
            if get_lang() == "en":
                self._log(
                    "  COMMANDS full catalogue · the clock runs live (||/▶/▶▶/▶▶▶ top-right)",
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
                    "  COMMANDS catalogue complet · le temps avance en direct (||/▶/▶▶/▶▶▶ en haut à droite)",
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
        elif cmd in ("MARKET", "INDEX", "INDICES", "WEI"):
            self._cmd_market()
        elif cmd == "HOURS":
            self._cmd_hours()
        elif cmd == "MARKETHUB":
            self.app.scenes.go("markethub", return_to="terminal")
        elif cmd == "WALL":
            self.app.scenes.go("wall", return_to="terminal")
        elif cmd in ("DESKTOP", "BUREAU", "PC"):
            self.app.scenes.go("desktop")
        elif cmd in ("SETTINGS", "REGLAGES", "RÉGLAGES"):
            self.app.scenes.go("settings", return_to="terminal")
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
            self._cmd_trade("bonds", cmd, parts[1:])
        elif cmd in ("CMDTY", "COMMODITIES", "COMMO", "MATIERES"):
            self.app.scenes.go("commodities", return_to="terminal")
        elif cmd in ("BUYCMDTY", "SELLCMDTY"):
            self._cmd_trade("commodities", cmd, parts[1:])
        elif cmd in ("CRYPTO", "COIN"):
            self.app.scenes.go("crypto", return_to="terminal")
        elif cmd in ("ETF", "ETFS", "FUNDS", "FONDS"):
            self.app.scenes.go("etfs", return_to="terminal")
        elif cmd in ("BUYETF", "SELLETF"):
            self._cmd_trade("etfs", cmd, parts[1:])
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
            self._cmd_trade("crypto", cmd, parts[1:])
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
            from data import tutorials as tutorials_mod
            tids = {t["id"] for t in tutorials_mod.TUTORIALS}
            kw = {"tid": arg.lower()} if arg and arg.lower() in tids else {}
            self.app.scenes.go("tutorials", return_to="terminal", **kw)
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
        elif cmd in ("ATTR", "ATTRIBUTION", "PERFATTR"):
            self.app.scenes.go("performance", return_to="terminal")
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
        elif cmd in ("TWAP", "FRAC"):
            self._cmd_twap(parts[1:])
        elif cmd in ("PENDING", "ORDERS"):
            self._cmd_pending()
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
        elif cmd in ("ACHIEVEMENTS", "SUCCES", "SUCCESS", "BADGES"):
            self.app.scenes.go("achievements", return_to="terminal")
        elif cmd == "STATS":
            self.app.scenes.go("stats", return_to="terminal")
        elif cmd in ("INBOX", "MAIL", "MESSAGES"):
            self.app.scenes.go("inbox", return_to="terminal")
        elif cmd in ("DECIDE", "DECISION", "DILEMMA"):
            if p.pending_dilemmas:
                self.app.scenes.go("dilemma", return_to="terminal")
            else:
                self._log(_L("  Aucune décision en attente.","  No pending decision."))
        elif cmd in ("RIVALS", "RIVAUX", "LEADERBOARD"):
            self.app.scenes.go("rivals", return_to="terminal")
        elif cmd in ("RECLAIM", "CONTEST"):
            self._cmd_reclaim(parts[1:])
        elif cmd == "RECONVERT":
            self._cmd_reconvert(parts[1:])
        elif cmd in ("MANDATES", "MANDATS"):
            self._cmd_mandates()
        elif cmd in ("MANDATE", "MANDAT"):
            self._cmd_mandate(parts[1:])
        elif cmd in ("RESEARCH", "RECHERCHE"):
            self._cmd_research(arg)
        elif cmd in ("ALERT", "ALERTE"):
            if len(parts) >= 3:
                self._cmd_alert(parts[1:])
            else:
                self.app.scenes.go("alerts", return_to="terminal")
        elif cmd in ("ALERTS", "ALERTES"):
            self.app.scenes.go("alerts", return_to="terminal")
        elif cmd == "LEGACY":
            self._cmd_legacy()
        elif cmd == "ARCHETYPE":
            self._cmd_archetype()
        elif cmd == "TENSION":
            self._cmd_tension()
        elif cmd == "CRISIS":
            self._cmd_crisis(parts[1:])
        elif cmd in ("WATCHLIST", "WATCH", "WL"):
            self._cmd_watchlist(parts[1:])
        elif cmd in ("COMPARE", "CMP"):
            self._cmd_compare(parts[1:])
        elif cmd in ("SECTOR", "SECTEUR"):
            self._cmd_sector(arg)
        elif cmd in ("REGION", "REGIONS"):
            self._cmd_region(arg)
        elif cmd in ("SCREEN", "SCREENER", "EQS"):
            self._cmd_screen(parts[1:])
        elif cmd in ("CRITERIA", "CRITERES"):
            self._cmd_criteria(parts[1:])
        elif cmd in ("IDEAS", "IDEES", "OPPORTUNITIES"):
            self._cmd_ideas(parts[1:])
        elif cmd in ("TRADES", "TRADELOG", "TJOURNAL"):
            self.app.scenes.go("tradejournal", return_to="terminal")
        elif cmd == "NOTE":
            self._cmd_note(parts[1:])
        elif cmd in ("JSTATS", "BILAN"):
            self._cmd_jstats(parts[1:])
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
        elif cmd in ("MORE", "PLUS", "PAGES"):
            # ouvre le menu Démarrer du bureau (toutes les pages, cf.
            # core/app_catalog.py) — plus d'écran PLUS séparé à ouvrir en
            # fenêtre, le menu Démarrer couvrait déjà exactement le même
            # besoin. `.scenes.scenes` (dict des instances enregistrées, cf.
            # core/scene_manager.SceneManager) donne accès direct à
            # l'instance persistante du bureau, hébergé ou non.
            desktop = self.app.scenes.scenes.get("desktop")
            if desktop is not None:
                desktop._open_start_menu()
        elif cmd in ("SHORTCUTS", "RACCOURCIS", "KEYS", "TOUCHES"):
            self._toggle_shortcuts_panel()
        elif cmd == "REG":
            info = config.CONTINENTS[p.continent]
            self._log(_L(f"  Régulateur : {info['regulator']}", f"  Regulator  : {info['regulator']}"),
                      _L(f"  Cadre      : {info['framework']}", f"  Framework  : {info['framework']}"))
        elif cmd == "MENU":
            self.app.scenes.go("menu")
        else:
            from core import fuzzy
            from scenes.scene_commands import all_command_tokens
            guess = fuzzy.suggest(cmd, all_command_tokens())
            if guess:
                self._log(_L(f"  Commande inconnue : {raw}. Vouliez-vous dire {guess} ? Tapez COMMANDS pour la liste.",
                              f"  Unknown command: {raw}. Did you mean {guess}? Type COMMANDS for the list."))
            else:
                self._log(_L(f"  Commande inconnue : {raw}. Tapez COMMANDS.", f"  Unknown command: {raw}. Type COMMANDS."))
