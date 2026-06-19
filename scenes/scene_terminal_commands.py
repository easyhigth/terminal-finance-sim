"""
scene_terminal_commands.py — Gestionnaires de commandes du terminal (TerminalCommandsMixin).
Extrait de scene_terminal.py pour limiter sa taille ; mixé dans TerminalScene.
"""

from core import badges as badges_mod
from core import career as career_mod
from core import config
from core import deals as deals_mod
from core import dilemmas as dilemmas_mod
from core import etfs as etfs_mod
from core import history as history_mod
from core import inbox as inbox_mod
from core import ipo as ipo_mod
from core import legacy as legacy_mod
from core import macrocal as macrocal_mod
from core import mandates as mandates_mod
from core import news as news_mod
from core import politics as politics_mod
from core import portfolio as pf_mod
from core import rivals as rivals_mod
from core import scenarios as scenarios_mod
from core import stresstest as stresstest_mod
from core import unlocks as unlocks_mod
from core.i18n import get_lang
from ui import widgets


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr


class TerminalCommandsMixin:
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
        p.flags["onboarding_seen_eval"] = True
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
        # comparaison d'ETF (panier vs panier) si les deux termes sont des ETF
        ea, eb = args[0].upper(), args[1].upper()
        if etfs_mod.exists(ea) and etfs_mod.exists(eb):
            qa, qb = etfs_mod.quote(self.market, ea), etfs_mod.quote(self.market, eb)
            rows = [
                ("NAV", f"{qa['price']:.2f}", f"{qb['price']:.2f}"),
                ("Catégorie", qa["category_label"], qb["category_label"]),
                ("Var 1 an", f"{qa['change_1y']:+.1f}%", f"{qb['change_1y']:+.1f}%"),
                ("Rendement", f"{qa['yield']*100:.1f}%", f"{qb['yield']*100:.1f}%"),
                ("Frais", f"{qa['expense']*100:.2f}%", f"{qb['expense']*100:.2f}%"),
                ("Bêta monde", f"{qa['beta']:+.2f}", f"{qb['beta']:+.2f}"),
                ("Risque", "●" * qa["risk"], "●" * qb["risk"]),
            ]
            self._open_window(f"COMPARER {ea} / {eb}",
                              [("Métrique", 110), (ea, 100), (eb, 100)], rows)
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
        self.app.scenes.go("mandates", return_to="terminal")

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

    def _cmd_legacy(self):
        """Affiche l'avancement des 5 objectifs de légende (ambitions de carrière)."""
        p = self.app.gs.player
        rows = []
        for g in legacy_mod.all_goals():
            done = g["id"] in p.legacy
            cur, target = g["progress"](p, self.market)
            status = "✓ ATTEINT" if done else f"{min(cur, target)}/{target}"
            col = config.COL_UP if done else config.COL_TEXT
            rows.append(((g["name"], config.COL_PRESTIGE), g["desc"], (status, col)))
        self._open_window(_L("OBJECTIFS DE LÉGENDE", "LEGACY GOALS"),
                          [("Objectif", 180), ("Description", 420), ("Avancement", 110)],
                          rows, accent=config.COL_PRESTIGE)

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
        self._check_legacy()

    def _check_legacy(self):
        """Attribue les objectifs de légende nouvellement atteints et notifie
        (toast renforcé + journal) : ce sont les ambitions de carrière, pas de
        simples jalons."""
        for g in legacy_mod.check_new(self.app.gs.player, self.market):
            self.app.notify(f"★ OBJECTIF DE LÉGENDE : {g['name']}", "prestige")
            career_mod.log(self.app.gs.player, "info", f"Objectif de légende atteint : {g['name']}")

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
        # capturés pour le bilan du tour (boucle de jeu lisible : ce qu'on encaisse)
        cash_before = p.cash
        rep_before = p.reputation
        events_before = len(self.recent_events)
        # crise/boom éventuel AVANT le pas (le choc s'applique dès ce tour)
        scenario = scenarios_mod.maybe_trigger(m)
        # pas de marché (déterministe)
        market_news = m.step()
        p.market_step = m.step_count
        self.worldmap.push_news(market_news)
        # fil d'actualités persistant du jour (carte + scène NEWS + historique 3 ans)
        today_news = [news_mod.make(news_mod.categorize_market(n), n.get("kind", "info"),
                                    n.get("text", ""), n.get("region"), "market")
                      for n in market_news]
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
        for res in (summary.get("options_due") or []):
            pos = res["position"]
            sign = "+" if res["pnl"] >= 0 else ""
            self._log(_L(f"  ■ Option échue : {pos['ticker']} {pos['option_type']} → "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)}).",
                      f"  ■ Option matured: {pos['ticker']} {pos['option_type']} → "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)})."))
            self.app.notify(_L("Option arrivée à échéance","Option matured"), "info")
        for res in (summary.get("ipos_settled") or []):
            pos = res["position"]
            sign = "+" if res["pnl"] >= 0 else ""
            self._log(_L(f"  ■ IPO cotée : {pos['ticker']} à {widgets.format_money(res['listing_price'], cur)} → "
                      f"{widgets.format_money(res['proceeds'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)}).",
                      f"  ■ IPO listed: {pos['ticker']} at {widgets.format_money(res['listing_price'], cur)} → "
                      f"{widgets.format_money(res['proceeds'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)})."))
            self.app.notify(_L(f"IPO cotée : {pos['ticker']}", f"IPO listed: {pos['ticker']}"), "good" if res["pnl"] >= 0 else "bad")
        for res in (summary.get("fx_due") or []):
            pos = res["position"]
            sign = "+" if res["pnl"] >= 0 else ""
            self._log(_L(f"  ■ Forward FX échu : {pos['pair']} → "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)}).",
                      f"  ■ FX forward matured: {pos['pair']} → "
                      f"{widgets.format_money(res['payoff'], cur)} "
                      f"(P&L {sign}{widgets.format_money(res['pnl'], cur)})."))
            self.app.notify(_L("Forward FX arrivé à échéance","FX forward matured"), "info")
        for res in (summary.get("macro_resolved") or []):
            ev = res["event"]
            won_bets = [b for b in res["bets_resolved"] if b["won"]]
            total_payout = sum(b["payout"] for b in res["bets_resolved"])
            self._log(_L(f"  ■ Évènement macro résolu : {ev['event_type']} → issue {res['actual_outcome']} "
                      f"({len(won_bets)}/{len(res['bets_resolved'])} pari(s) gagné(s), "
                      f"{widgets.format_money(total_payout, cur)}).",
                      f"  ■ Macro event resolved: {ev['event_type']} → outcome {res['actual_outcome']} "
                      f"({len(won_bets)}/{len(res['bets_resolved'])} bet(s) won, "
                      f"{widgets.format_money(total_payout, cur)})."))
            if res["bets_resolved"]:
                self.app.notify(_L(f"Évènement résolu : {ev['event_type']}", f"Event resolved: {ev['event_type']}"),
                                 "good" if won_bets else "bad")
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
            today_news.append(news_mod.make("event", scenario["kind"], scenario["name"], None, "scenario"))
            inbox_mod.on_crisis(p, scenario["name"], scenario["kind"])
            career_mod.log(p, "crisis", scenario["name"])
            self.app.notify(scenario["name"], scenario["kind"])
            if scenario["kind"] == "bad":
                p.flags["crises"] = p.flags.get("crises", 0) + 1
                if scenario.get("severity", 1.0) >= 1.35:
                    p.flags["major_crises"] = p.flags.get("major_crises", 0) + 1
        # événement HISTORIQUE scénarisé (campagne déterministe dans le temps)
        hist = history_mod.maybe_trigger(p, m)
        if hist:
            from core.i18n import get_lang
            hname, hstory = history_mod.localized(hist["event"], get_lang())
            self.worldmap.push_news([{"region": None, "kind": hist["kind"], "text": hname}])
            self.recent_events.insert(0, {"title": "✶ " + hname, "kind": hist["kind"],
                                          "cash": 0, "rep": 0})
            self._log(f"  ✶ {hname} — {hstory[:64]}…")
            today_news.append(news_mod.make("event", hist["kind"], hname, None, "history"))
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
            today_news.append(news_mod.make("political", pol["kind"], pname, pol["region"], "politics"))
            # une news de PAYS atterrit aussi dans l'inbox
            inbox_mod.push(p, "country", pol["country"],
                           _L(f"Actualité — {pol['country']}", f"Country brief — {pol['country_en']}"),
                           pstory)
            career_mod.log(p, "crisis", pname)
            self.app.notify(pname, pol["kind"])
            if pol["kind"] == "bad":
                p.flags["crises"] = p.flags.get("crises", 0) + 1
            # deal/mandat avec un gouvernement, si cohérent avec la situation
            gdeal = deals_mod.maybe_government_deal(p, pol, random)
            if gdeal:
                self._log(_L(f"  ✶ MANDAT SOUVERAIN : {gdeal['title']} — {pol['country']} "
                             f"({gdeal['days_left']}j, DEALS).",
                             f"  ✶ SOVEREIGN MANDATE: {gdeal['title']} — {pol['country_en']} "
                             f"({gdeal['days_left']}d, DEALS)."))
                today_news.append(news_mod.make("political", "info",
                                  _L(f"{pol['country']} mandate un conseil financier",
                                     f"{pol['country_en']} seeks a financial advisor"),
                                  pol["region"], "gov_deal"))
                inbox_mod.push(p, "country", pol["country"],
                               _L("Proposition de mandat souverain", "Sovereign mandate proposal"),
                               _L(f"{gdeal['desc']} Récompense {gdeal['reward_cash']:,.0f}. "
                                  "Ouvrez DEALS pour traiter ce mandat.",
                                  f"{gdeal['desc']} Reward {gdeal['reward_cash']:,.0f}. "
                                  "Open DEALS to handle this mandate."))
                self.app.notify(_L(f"Mandat souverain : {pol['country']}",
                                   f"Sovereign mandate: {pol['country_en']}"), "info")
        if summary.get("quarter_changed"):
            legacy_mod.on_quarter_close(p, m)
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
        offer = mandates_mod.maybe_offer(p, random, m)
        if offer:
            if offer.get("transformant"):
                self._log(_L(f"  ★★ MANDAT TRANSFORMANT : {offer['client']} — "
                          f"{widgets.format_money(offer['capital'], cur)} (MANDATES pour voir).",
                          f"  ★★ TRANSFORMATIVE MANDATE: {offer['client']} — "
                          f"{widgets.format_money(offer['capital'], cur)} (type MANDATES to view)."))
                self.app.notify(_L(f"Mandat transformant : {offer['client']}",
                                   f"Transformative mandate: {offer['client']}"), "prestige")
            else:
                self._log(_L(f"  ✶ OFFRE DE MANDAT : {offer['client']} — {widgets.format_money(offer['capital'], cur)} "
                          f"(MANDATES pour voir).",
                          f"  ✶ MANDATE OFFER: {offer['client']} — {widgets.format_money(offer['capital'], cur)} "
                          f"(type MANDATES to view)."))
                self.app.notify(_L(f"Offre de mandat : {offer['client']}", f"Mandate offer: {offer['client']}"), "info")
            inbox_mod.push(p, "client", offer["client"], "Proposition de mandat",
                           f"Nous souhaitons vous confier {widgets.format_money(offer['capital'], cur)} : "
                           f"objectif +{offer['target_pct']:.0f}% en {offer['horizon']} trimestres, "
                           f"bêta ≤ {offer['max_beta']:.2f}. Tapez MANDATES puis MANDATE ACCEPT {offer['id']}.")
        # nouvelle offre d'IPO éventuelle
        ipo_offer = ipo_mod.maybe_offer(p, random, m)
        if ipo_offer:
            self._log(_L(f"  ✶ NOUVELLE IPO : {ipo_offer['company_name']} ({ipo_offer['ticker']}) — "
                      f"{widgets.format_money(ipo_offer['price_min'], cur)}-"
                      f"{widgets.format_money(ipo_offer['price_max'], cur)} (IPO pour voir).",
                      f"  ✶ NEW IPO: {ipo_offer['company_name']} ({ipo_offer['ticker']}) — "
                      f"{widgets.format_money(ipo_offer['price_min'], cur)}-"
                      f"{widgets.format_money(ipo_offer['price_max'], cur)} (type IPO to view)."))
            self.app.notify(_L(f"Nouvelle IPO : {ipo_offer['ticker']}", f"New IPO: {ipo_offer['ticker']}"), "info")
        # nouvel évènement macro éventuel
        macro_event = macrocal_mod.maybe_schedule(p, random, m)
        if macro_event:
            self._log(_L(f"  ✶ AGENDA MACRO : {macro_event['event_type']} dans "
                      f"{macro_event['resolve_step'] - m.step_count} pas (AGENDA pour voir).",
                      f"  ✶ MACRO CALENDAR: {macro_event['event_type']} in "
                      f"{macro_event['resolve_step'] - m.step_count} steps (type AGENDA to view)."))
            self.app.notify(_L(f"Agenda macro : {macro_event['event_type']}", f"Macro calendar: {macro_event['event_type']}"), "info")
        # revue de performance éventuelle (déclenchée par advance_step)
        if summary.get("review_offer"):
            self._log(_L("  ★ REVUE DE PERFORMANCE : votre manager souhaite vous voir (tapez REVIEW).",
                      "  ★ PERFORMANCE REVIEW: your manager wants to see you (type REVIEW)."))
            self.app.notify(_L("Revue de performance annuelle","Annual performance review"), "info")
        # stress test réglementaire éventuel (semestriel)
        stress_test = stresstest_mod.maybe_trigger(p, summary.get("quarter_changed"), m)
        if stress_test:
            self._log(_L("  ★ STRESS TEST RÉGLEMENTAIRE : le superviseur vous convoque (tapez STRESS).",
                      "  ★ REGULATORY STRESS TEST: the supervisor wants to see you (type STRESS)."))
            self.app.notify(_L("Stress test réglementaire","Regulatory stress test"), "info")
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
            today_news.append(news_mod.make("regulatory", "bad",
                              _L("Enquête réglementaire ouverte à votre encontre",
                                 "Regulatory investigation opened against you"), p.continent, "regulator"))
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
        # enregistre le fil d'actualités du jour (persistant 3 ans) + marqueurs carte
        news_mod.record(p, today_news, p.day)
        self.worldmap.set_day_markers(today_news)
        # badges éventuels
        self._check_badges()
        unread = inbox_mod.unread_count(p)
        if unread:
            self._log(_L(f"  @ {unread} message(s) non lu(s) — tapez INBOX.", f"  @ {unread} unread message(s) — type INBOX."))
        # bilan du tour : encaisser la conséquence en un coup d'œil (cash + réputation
        # cumulés sur TOUT le tour — salaire, dividendes, frais, rivaux, sanctions…),
        # affiché en dernier pour rester visible juste avant le retour au terminal.
        cash_delta = p.cash - cash_before
        rep_delta = p.reputation - rep_before
        new_events = len(self.recent_events) - events_before
        cash_sign = "+" if cash_delta >= 0 else ""
        rep_sign = "+" if rep_delta >= 0 else ""
        bits = [f"{cash_sign}{widgets.format_money(cash_delta, cur)}"]
        if rep_delta:
            bits.append(f"{rep_sign}{rep_delta} rép.")
        if new_events > 0:
            bits.append(_L(f"{new_events} évènement(s)", f"{new_events} event(s)"))
        self._log(_L(f"  ════ BILAN DU TOUR — jour {p.day} : {' · '.join(bits)} ════",
                      f"  ════ TURN RECAP — day {p.day}: {' · '.join(bits)} ════"))
        self.app.notify(
            _L(f"Bilan du tour : {cash_sign}{widgets.format_money(cash_delta, cur)}"
               + (f" · {rep_sign}{rep_delta} rép." if rep_delta else ""),
               f"Turn recap: {cash_sign}{widgets.format_money(cash_delta, cur)}"
               + (f" · {rep_sign}{rep_delta} rep." if rep_delta else "")),
            "good" if cash_delta >= 0 else "warn")
        if not p.hardcore:
            gs.save(config.AUTOSAVE_SLOT)
        if summary["game_over"] or p.check_game_over():
            self.app.scenes.go("gameover")
        elif dil:
            self.app.scenes.go("dilemma", return_to="terminal")

    def _cmd_deals(self):
        self.app.scenes.go("deals", return_to="terminal")

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
