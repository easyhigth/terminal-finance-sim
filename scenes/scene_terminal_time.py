"""
scene_terminal_time.py — Moteur d'avance du temps du terminal (TerminalTimeMixin) :
un pas de marché complet (_advance_time) et l'avance jusqu'au trimestre suivant
(_advance_to_quarter). Extrait de scene_terminal_commands.py pour limiter sa
taille ; mixé dans TerminalScene avec les autres mixins de commandes.
"""

from core import config
from core import deals as deals_mod
from core import dilemmas as dilemmas_mod
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
from core import career as career_mod
from core.i18n import get_lang
from ui import widgets


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr


class TerminalTimeMixin:
    # ------------------------------------------------------- temps & deals
    def _advance_time(self):
        """Avance d'un pas de marché (config.DAYS_PER_STEP jours).
        Retourne un dict décrivant le tour, utilisé par _advance_to_quarter
        pour savoir si elle doit s'arrêter (évènement bloquant) ou continuer.
        Ne pas confondre avec le nombre de pas restants avant le trimestre :
        ce retour ne fait que rapporter ce qui s'est produit CE tour-ci.
        """
        import random
        gs = self.app.gs
        p = gs.player
        m = self.market
        # capturés pour le bilan du tour (boucle de jeu lisible : ce qu'on encaisse)
        cash_before = p.cash
        rep_before = p.reputation
        events_before = len(self.recent_events)
        mandate_offers_before = len(p.mandate_offers)
        # crise/boom éventuel AVANT le pas (le choc s'applique dès ce tour)
        scenario = scenarios_mod.maybe_trigger(m)
        if scenario and m.crises:
            m.crises[-1].start_nw = pf_mod.net_worth(p, m)
        # pas de marché (déterministe)
        market_news = m.step()
        p.market_step = m.step_count
        self.worldmap.push_news(market_news)
        # retombées visibles : postmortem des crises qui viennent de s'éteindre
        for cr in m.ended_crises:
            if cr.start_nw:
                growth = (pf_mod.net_worth(p, m) / cr.start_nw - 1) * 100
                sign = "+" if growth >= 0 else ""
                self._log(_L(
                    f"  ◇ Crise dissipée : {cr.name} — patrimoine net sur la période : {sign}{growth:.1f}%.",
                    f"  ◇ Crisis subsided: {cr.name} — net worth over the period: {sign}{growth:.1f}%."))
                career_mod.log(p, "crisis", _L(
                    f"Crise {cr.name} dissipée ({sign}{growth:.1f}% de patrimoine net)",
                    f"Crisis {cr.name} subsided ({sign}{growth:.1f}% net worth)"))
                self.app.notify(_L(f"Crise dissipée : {cr.name}", f"Crisis subsided: {cr.name}"),
                                 "good" if growth >= 0 else "warn")
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
            self._log(_L(
                f"  ⚠ APPEL DE MARGE : capitaux propres {widgets.format_money(mc['equity'], cur)} "
                f"< seuil de maintenance {widgets.format_money(mc['threshold'], cur)} "
                f"(levier {mc['leverage_before']:.2f}x). Liquidation forcée de "
                f"{widgets.format_money(mc['liquidated'], cur)} ({mc['reduce_frac']*100:.0f}% des positions) "
                f"→ levier ramené à {mc['leverage_after']:.2f}x (pénalité "
                f"{widgets.format_money(mc['penalty'], cur)}).",
                f"  ⚠ MARGIN CALL: equity {widgets.format_money(mc['equity'], cur)} "
                f"< maintenance threshold {widgets.format_money(mc['threshold'], cur)} "
                f"(leverage {mc['leverage_before']:.2f}x). Forced liquidation of "
                f"{widgets.format_money(mc['liquidated'], cur)} ({mc['reduce_frac']*100:.0f}% of positions) "
                f"→ leverage brought down to {mc['leverage_after']:.2f}x (penalty "
                f"{widgets.format_money(mc['penalty'], cur)})."))
            career_mod.log(p, "crisis", _L(
                f"Appel de marge : levier {mc['leverage_before']:.2f}x → {mc['leverage_after']:.2f}x "
                f"(liquidation {widgets.format_money(mc['liquidated'], cur)})",
                f"Margin call: leverage {mc['leverage_before']:.2f}x → {mc['leverage_after']:.2f}x "
                f"(liquidated {widgets.format_money(mc['liquidated'], cur)})"))
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
            profile_txt = f" ({mandates_mod.profile_label(offer['client_profile'])})" if offer.get("client_profile") else ""
            if offer.get("transformant"):
                self._log(_L(f"  ★★ MANDAT TRANSFORMANT : {offer['client']}{profile_txt} — "
                          f"{widgets.format_money(offer['capital'], cur)} (MANDATES pour voir).",
                          f"  ★★ TRANSFORMATIVE MANDATE: {offer['client']}{profile_txt} — "
                          f"{widgets.format_money(offer['capital'], cur)} (type MANDATES to view)."))
                self.app.notify(_L(f"Mandat transformant : {offer['client']}",
                                   f"Transformative mandate: {offer['client']}"), "prestige")
            else:
                self._log(_L(f"  ✶ OFFRE DE MANDAT : {offer['client']}{profile_txt} — {widgets.format_money(offer['capital'], cur)} "
                          f"(MANDATES pour voir).",
                          f"  ✶ MANDATE OFFER: {offer['client']}{profile_txt} — {widgets.format_money(offer['capital'], cur)} "
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
            self._log(_L(f"  ⚠ ENQUÊTE RÉGLEMENTAIRE : scrutin {inv['heat_before']:.0f}/100 "
                      f"(seuil 55) — vos décisions risquées récentes ont déclenché un contrôle. "
                      f"Amende {widgets.format_money(inv['fine'], cur)}, réputation -{inv['rep_loss']}.",
                      f"  ⚠ REGULATORY INVESTIGATION: scrutiny {inv['heat_before']:.0f}/100 "
                      f"(threshold 55) — your recent risky decisions triggered a probe. "
                      f"Fine {widgets.format_money(inv['fine'], cur)}, reputation -{inv['rep_loss']}."))
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
        # détail « pourquoi ma réputation a bougé » : une ligne par cause, pour que
        # le joueur comprenne IMMÉDIATEMENT l'origine de chaque variation (et ne
        # vive plus l'oscillation comme du bruit non expliqué).
        rep_log = getattr(p, "rep_log", None) or []
        if rep_log:
            for reason, delta in rep_log:
                sign = "+" if delta >= 0 else ""
                self._log(f"    {sign}{delta} rép. — {reason}")
                if abs(delta) >= 3:    # variation individuelle notable -> toast dédié
                    self.app.notify(
                        _L(f"Réputation {sign}{delta} — {reason}", f"Reputation {sign}{delta} — {reason}"),
                        "good" if delta >= 0 else "bad")
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
        game_over = bool(summary["game_over"] or p.check_game_over())
        new_mandate_offer = len(p.mandate_offers) > mandate_offers_before
        # motif d'arrêt prématuré pour ADV Q : tout évènement qui mérite l'attention
        # immédiate du joueur avant de poursuivre l'avance automatique (on ne saute
        # jamais par-dessus une décision, une crise ou une convocation).
        stop_reason = None
        if game_over:
            stop_reason = "game_over"
        elif dil:
            stop_reason = "dilemma"
        elif stress_test:
            stop_reason = "stress_test"
        elif summary.get("review_offer"):
            stop_reason = "review"
        elif inv:
            stop_reason = "investigation"
        elif new_mandate_offer:
            stop_reason = "mandate_offer"
        elif scenario:
            stop_reason = "scenario"
        elif mc:
            stop_reason = "margin_call"
        if game_over:
            self.app.scenes.go("gameover")
        elif dil:
            self.app.scenes.go("dilemma", return_to="terminal")
        return {
            "stop": stop_reason is not None,
            "reason": stop_reason,
            "quarter_changed": bool(summary.get("quarter_changed")),
            "game_over": game_over,
        }

    # libellés courts affichés quand ADV Q s'interrompt avant la fin du trimestre
    # (fonctions et non valeurs figées : la langue peut changer en cours de partie)
    _ADV_STOP_LABELS = {
        "game_over": lambda: _L("fin de partie", "game over"),
        "dilemma": lambda: _L("décision requise", "decision required"),
        "stress_test": lambda: _L("stress test réglementaire", "regulatory stress test"),
        "review": lambda: _L("revue de performance", "performance review"),
        "investigation": lambda: _L("enquête réglementaire", "regulatory investigation"),
        "mandate_offer": lambda: _L("nouvelle offre de mandat", "new mandate offer"),
        "scenario": lambda: _L("évènement de marché", "market event"),
        "margin_call": lambda: _L("appel de marge", "margin call"),
    }

    def _advance_to_quarter(self):
        """ADV Q : avance jusqu'au changement de trimestre, en répétant les pas
        de _advance_time(), MAIS s'arrête immédiatement dès qu'un évènement
        bloquant survient (dilemme, crise, mandat offert, appel de marge,
        convocation, game over...) — on ne saute jamais par-dessus un évènement,
        on évite juste au joueur de spammer ADV ~18 fois sans rien d'autre à faire.
        """
        p = self.app.gs.player
        start_quarter = p.quarter
        steps = 0
        # garde-fou anti-boucle infinie : largement au-dessus du nombre de pas
        # attendu pour un trimestre (config.DAYS_PER_QUARTER / DAYS_PER_STEP).
        max_steps = (config.DAYS_PER_QUARTER // config.DAYS_PER_STEP) + 4
        while steps < max_steps:
            result = self._advance_time()
            steps += 1
            if result.get("game_over"):
                return
            if result["stop"]:
                label_fn = self._ADV_STOP_LABELS.get(result["reason"])
                label = label_fn() if label_fn else result["reason"]
                self._log(_L(f"  ⏸ ADV Q interrompu après {steps} pas : {label}.",
                              f"  ⏸ ADV Q stopped after {steps} step(s): {label}."))
                return
            if p.quarter != start_quarter:
                self._log(_L(f"  ⏩ ADV Q : nouveau trimestre atteint en {steps} pas.",
                              f"  ⏩ ADV Q: reached next quarter in {steps} step(s)."))
                return
        self._log(_L(f"  ⏸ ADV Q interrompu après {steps} pas (limite de sécurité).",
                      f"  ⏸ ADV Q stopped after {steps} step(s) (safety limit)."))
