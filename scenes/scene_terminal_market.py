"""
scene_terminal_market.py — Commandes de lecture marché/recherche du terminal
(TerminalMarketMixin) : indices, sociétés, graphes, screener, alertes...
Extrait de scene_terminal_commands.py pour limiter sa taille ; mixé dans
TerminalScene avec les autres mixins de commandes.
"""

from core import alerts as alerts_mod
from core import audio, config
from core import etfs as etfs_mod
from core import inbox as inbox_mod
from core import market_hours as mh_mod
from core import opportunities as opportunities_mod
from core import screener as screener_mod
from core.i18n import get_lang
from ui import widgets


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr


class TerminalMarketMixin:
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

    def _cmd_hours(self):
        """HOURS : statut des 3 sessions (Asie/Europe/Amériques) au pas courant —
        2 ouvertes / 1 fermée en rotation (cf. core/market_hours.py)."""
        m = self.market
        step = m.step_count
        lang = get_lang()
        labels = mh_mod.session_labels(lang)
        rows = []
        for sess in ("ASIA", "EUROPE", "AMERICAS"):
            is_open = mh_mod.is_session_open(sess, step)
            status = _L("OUVERT", "OPEN") if is_open else _L("FERMÉ", "CLOSED")
            col = config.COL_UP if is_open else config.COL_DOWN
            when = _L("ce pas", "this step") if is_open else _L("rouvre au prochain pas", "reopens next step")
            rows.append(((labels[sess], config.COL_AMBER), when, (status, col)))
        self._open_window(_L("SESSIONS DE MARCHÉ", "MARKET SESSIONS"),
                          [(_L("Session", "Session"), 110),
                           (_L("Quand", "When"), 170),
                           (_L("Statut", "Status"), 90)], rows)
        self._log(_L("  Sessions par pas : 2 ouvertes / 1 fermée, en rotation à chaque pas.",
                     "  Sessions per step: 2 open / 1 closed, rotating each step."))

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
        rows.append(("Régime de marché",
                     f"{self.market.regime_label()} (depuis {self.market.regime_age()} sem.)",
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
        from core.i18n import get_lang
        from data import glossary_data
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
            self._log(_L("  Usage : COMPARE <t1> <t2> [...] [t6]  (actions OU ETF, jusqu'à 6)",
                          "  Usage: COMPARE <t1> <t2> [...] [t6]  (stocks OR ETFs, up to 6)"))
            return
        terms = [a.upper() for a in args[:6]]
        self._log(_L("  Comparateur ouvert.", "  Compare screen opened."))
        self.app.scenes.go("compare", tickers=terms, return_to="terminal")

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

    _SCREEN_NUM_KEYS = {"cap_min", "cap_max", "pe_max", "margin_min", "growth_min", "growth_max",
                        "beta_max", "momentum_min", "duration_min", "duration_max",
                        "dividend_min", "expense_max"}

    def _parse_screen_args(self, args):
        """Transforme une liste de tokens `clé=valeur` en kwargs pour
        `core.screener`, en convertissant les clés numériques connues."""
        kwargs = {}
        for tok in args:
            if "=" not in tok:
                continue
            key, val = tok.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            if key in self._SCREEN_NUM_KEYS:
                try:
                    kwargs[key] = float(val)
                except ValueError:
                    continue
            elif key == "region":
                kwargs[key] = self._match_region(val) if val else None
            elif key == "sector":
                for s in self.market.sectors:
                    if s.lower() == val.lower():
                        kwargs[key] = s
                        break
            elif key in ("category", "style", "theme", "rating_min"):
                kwargs[key] = val.upper() if key == "rating_min" else val.lower()
        return kwargs

    def _cmd_screen(self, args):
        if args and args[0].lower() in ("etf", "etfs"):
            kwargs = self._parse_screen_args(args[1:])
            quotes = screener_mod.screen_etfs(self.market, limit=18, **kwargs)
            rows = [((q["id"], config.COL_AMBER), q["name"][:18], q["category_label"],
                     f"{q['price']:.2f}", f"{q['change_1y']:+.1f}%", f"{q['expense']*100:.2f}%")
                    for q in quotes]
            if not rows:
                rows = [("—", "aucun fonds", "—", "—", "—", "—")]
            self._open_window(_L(f"SCREEN ETF ({len(quotes)})", f"SCREEN ETF ({len(quotes)})"),
                              [("Tk", 55), ("Nom", 150), ("Catégorie", 110),
                               ("NAV", 60), ("1AN", 60), ("Frais", 55)], rows)
            return
        kwargs = self._parse_screen_args(args)
        if not kwargs:
            # filtre par défaut : value (P/E bas) parmi les grandes capis
            kwargs = {"pe_max": 12.0, "cap_min": 50000.0}
        found = screener_mod.screen_stocks(self.market, limit=18, **kwargs)
        rows = [((c["ticker"], config.COL_AMBER), c["name"][:16], c["sector"],
                 f"{c['pe']:.1f}" if c["pe"] is not None else "n.m.", f"{c['change_pct']:+.1f}%")
                for c in found]
        if not rows:
            rows = [("—", "aucune valeur", "—", "—", "—")]
        self._open_window(_L(f"SCREEN ACTIONS ({len(found)})", f"SCREEN STOCKS ({len(found)})"),
                          [("Tk", 60), ("Nom", 140), ("Secteur", 90), ("P/E", 50), ("Var 1an", 60)], rows)

    # ---------------------------------------------------- idées/opportunités (core/opportunities.py)
    def _cmd_criteria(self, args):
        """CRITERIA ADD <stock|etf> clé=valeur...  ·  CRITERIA LIST  ·  CRITERIA REMOVE <id>."""
        p = self.app.gs.player
        if not args:
            self._log(_L("  Usage : CRITERIA ADD <stock|etf> [clé=valeur...] [label=...] · LIST · REMOVE <id>.",
                         "  Usage: CRITERIA ADD <stock|etf> [key=value...] [label=...] · LIST · REMOVE <id>."))
            return
        sub = args[0].upper()
        if sub == "LIST":
            screens = opportunities_mod.list_screens(p)
            rows = [((str(s["id"]), config.COL_AMBER), s["kind"], s["label"],
                     ", ".join(f"{k}={v}" for k, v in s["criteria"].items())[:40])
                    for s in screens]
            if not rows:
                rows = [("—", "—", "aucun critère sauvegardé", "—")]
            self._open_window("CRITÈRES SAUVEGARDÉS", [("Id", 30), ("Type", 50),
                              ("Label", 110), ("Critères", 180)], rows)
            return
        if sub == "REMOVE":
            if len(args) < 2 or not args[1].isdigit():
                self._log(_L("  Usage : CRITERIA REMOVE <id>.", "  Usage: CRITERIA REMOVE <id>."))
                return
            ok = opportunities_mod.remove_screen(p, int(args[1]))
            self._log(_L("  ✓ Critère supprimé." if ok else "  Identifiant inconnu.",
                         "  ✓ Criterion removed." if ok else "  Unknown id."))
            return
        if sub == "ADD":
            if len(args) < 2 or args[1].lower() not in ("stock", "etf"):
                self._log(_L("  Usage : CRITERIA ADD <stock|etf> [clé=valeur...].",
                             "  Usage: CRITERIA ADD <stock|etf> [key=value...]."))
                return
            kind = args[1].lower()
            rest = args[2:]
            label = ""
            tokens = []
            for tok in rest:
                if tok.lower().startswith("label="):
                    label = tok.split("=", 1)[1]
                else:
                    tokens.append(tok)
            criteria = self._parse_screen_args(tokens)
            try:
                e = opportunities_mod.add_screen(p, kind, criteria, label=label)
            except ValueError as exc:
                self._log(_L(f"  Refusé : {exc}.", f"  Rejected: {exc}."))
                return
            self._log(_L(f"  ✓ Critère #{e['id']} sauvegardé ({e['label']}).",
                         f"  ✓ Criterion #{e['id']} saved ({e['label']})."))
            return
        self._log(_L("  Sous-commande inconnue (ADD/LIST/REMOVE).", "  Unknown subcommand (ADD/LIST/REMOVE)."))

    def _cmd_ideas(self, args):
        """IDEAS [id] : exécute les critères sauvegardés et remonte les correspondances."""
        p = self.app.gs.player
        if not p.saved_screens:
            self._log(_L("  Aucun critère sauvegardé. Voir CRITERIA ADD.",
                         "  No saved criteria. See CRITERIA ADD."))
            return
        if args and args[0].isdigit():
            sid = int(args[0])
            screens = [s for s in p.saved_screens if s["id"] == sid]
            if not screens:
                self._log(_L("  Identifiant inconnu.", "  Unknown id."))
                return
            pairs = [(s, opportunities_mod.run_screen(self.market, s, limit=20)) for s in screens]
        else:
            pairs = opportunities_mod.run_all(p, self.market, limit=8)
        rows = []
        for s, results in pairs:
            if s["kind"] == "etf":
                for q in results:
                    rows.append(((q["id"], config.COL_AMBER), s["label"], q["name"][:18],
                                 f"{q['price']:.2f}"))
            else:
                for c in results:
                    rows.append(((c["ticker"], config.COL_AMBER), s["label"], c["name"][:18],
                                 f"{c['pe']:.1f}" if c["pe"] is not None else "n.m."))
        if not rows:
            rows = [("—", "—", "aucune correspondance", "—")]
        self._open_window(_L("IDÉES D'INVESTISSEMENT", "INVESTMENT IDEAS"),
                          [("Tk", 60), ("Critère", 90), ("Nom", 130), ("P/E ou NAV", 70)], rows)

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
            self._log(_L("  Usage : ALERT <ticker> <prix|%|trail%>",
                         "  Usage: ALERT <ticker> <price|%|trail%>"))
            self._log(_L("  Exemples : ALERT MVC 185  |  ALERT MVC +5%  |  ALERT MVC -3%  |  ALERT MVC trail 2%",
                         "  Examples: ALERT MVC 185 | ALERT MVC +5% | ALERT MVC -3% | ALERT MVC trail 2%"))
            return
        tk = self.market.resolve(args[0])
        if tk is None:
            self._log(_L(f"  Aucun résultat : {args[0]}.", f"  No match: {args[0]}."))
            return
        raw = args[1].replace(",", ".")
        kind = "level"
        if raw.lower().startswith("trail"):
            kind = "trailing"
            raw = raw[5:].strip()
        if raw.endswith("%"):
            kind = "trailing" if kind == "trailing" else "pct"
            raw = raw[:-1].strip()
        r = alerts_mod.place(p, self.market, tk, kind, raw)
        if not r["ok"]:
            self._log(_L(f"  Alerte refusée ({r['reason']}).", f"  Alert rejected ({r['reason']})."))
            return
        self.market.track_company(tk)
        a = r["alert"]
        if a["kind"] == "level":
            sens = "au-dessus de" if a["above"] else "en-dessous de"
            self._log(_L(f"  Alerte posée : {tk} {sens} {a['value']:.2f}.",
                         f"  Alert set: {tk} {sens} {a['value']:.2f}."))
        elif a["kind"] == "pct":
            sign = "hausse" if a["above"] else "baisse"
            self._log(_L(f"  Alerte posée : {tk} sur {sign} de {a['value']:.1f}%.",
                         f"  Alert set: {tk} {sign} {a['value']:.1f}%."))
        else:
            self._log(_L(f"  Stop suiveur posé sur {tk} à {a['value']:.1f}%.",
                         f"  Trailing stop set on {tk} at {a['value']:.1f}%."))

    def _cmd_alerts(self):
        p = self.app.gs.player
        summary = alerts_mod.summary(p)
        active = summary["active"]
        if not active:
            self._log(_L("  Aucune alerte active.","  No active alert."))
            return
        rows = []
        for a in active:
            kind = a.get("kind", "level")
            if kind == "level":
                desc = ("↑" if a["above"] else "↓") + f" {a['value']:.2f}"
            elif kind == "pct":
                desc = ("+" if a["above"] else "-") + f"{a['value']:.1f}%"
            else:
                desc = f"trail {a['value']:.1f}%"
            rows.append(((a["ticker"], config.COL_AMBER), desc,
                         f"{self.market.price_of(a['ticker']) or 0:.2f}"))
        self._open_window("ALERTES DE PRIX",
                          [("Tk", 60), ("Seuil", 90), ("Cours", 70)], rows)

    def _check_alerts(self):
        """Vérifie les alertes ; notifie au franchissement avec action vers Trading."""
        p = self.app.gs.player
        triggered = alerts_mod.check(p, self.market)
        for e in triggered:
            audio.play("alert")
            msg = alerts_mod.format_trigger(e)
            self._log(_L(f"  ⚠ ALERTE {msg}", f"  ⚠ ALERT {msg}"))
            self.app.notify(f"Alerte {e['ticker']} @ {e['price']:.2f}",
                            "warn", action="trading", action_kwargs={"ticker": e["ticker"]})
            inbox_mod.push(p, "desk", "Desk", f"Alerte cours : {e['ticker']}",
                           msg + " Cliquez la notification pour trader.")
