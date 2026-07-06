"""
scene_terminal_trading.py — Commandes de trading du terminal (TerminalTradingMixin) :
actions/obligations/commodities/crypto (achat/vente/short/cover), marge, allocation,
hedge, rebalance, journal de trading. Extrait de scene_terminal_commands.py pour
limiter sa taille ; mixé dans TerminalScene avec les autres mixins de commandes.
"""

from core import audio, config
from core import career as career_mod
from core import firms as firms_mod
from core import journal as journal_mod
from core import liquidity as liq_mod
from core import market_hours as mh_mod
from core import portfolio as pf_mod
from core import unlocks as unlocks_mod
from core.i18n import get_lang
from ui import widgets


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr


# Config par classe d'actif des commandes BUYxxx/SELLxxx génériques (cf.
# _cmd_trade) : nom du module core.*, noms des fonctions buy/sell (le module
# obligations s'appelle buy_bond/sell_bond plutôt que buy/sell) et le libellé
# de classe d'actif attendu par core.journal.log_trade.
ASSET_TRADE_CONFIG = {
    "bonds": {"module": "core.bonds", "buy_fn": "buy_bond", "sell_fn": "sell_bond",
              "asset_class": "Obligation"},
    "commodities": {"module": "core.commodities", "buy_fn": "buy", "sell_fn": "sell",
                     "asset_class": "Commodity"},
    "crypto": {"module": "core.crypto", "buy_fn": "buy", "sell_fn": "sell",
               "asset_class": "Crypto"},
    "etfs": {"module": "core.etfs", "buy_fn": "buy", "sell_fn": "sell",
             "asset_class": "ETF"},
}


class TerminalTradingMixin:
    def _cmd_trade(self, asset, cmd, args):
        """Trading générique BUY<X>/SELL<X> <id> <qté> pour bonds/commodities/
        crypto/etfs (cf. ASSET_TRADE_CONFIG) : même validation, mêmes messages
        et même journalisation pour les 4 classes d'actifs, qui ne diffèrent
        que par le module core.* et le nom de leurs fonctions buy/sell."""
        conf = ASSET_TRADE_CONFIG[asset]
        import importlib
        mod = importlib.import_module(conf["module"])
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
        asset_class = conf["asset_class"]
        if cmd.startswith("BUY"):
            if qty == "ALL":
                self._log(_L("  Précisez une quantité pour l'achat.","  Specify a quantity to buy."))
                return
            r = getattr(mod, conf["buy_fn"])(p, m, cid, qty)
            if r["ok"]:
                self._log(_L(f"  ✓ Achat {qty} × {cid} @ {r['price']:.2f} = "
                          f"{widgets.format_money(r['total'], self._cur())}.",
                          f"  ✓ Bought {qty} × {cid} @ {r['price']:.2f} = "
                          f"{widgets.format_money(r['total'], self._cur())}."))
                journal_mod.log_trade(p, m, asset_class=asset_class, key=cid, label=cid,
                                      side="achat", qty=r["qty"], price=r["price"],
                                      fee=r.get("fee", 0.0))
            else:
                self._log(_L(f"  Achat refusé ({r['reason']}).", f"  Buy rejected ({r['reason']})."))
        else:
            r = getattr(mod, conf["sell_fn"])(p, m, cid, qty)
            if r["ok"]:
                self._log(_L(f"  ✓ Vente {int(r['qty'])} × {cid} (P&L réalisé "
                          f"{r['realized']:+.0f}).",
                          f"  ✓ Sold {int(r['qty'])} × {cid} (realised P&L "
                          f"{r['realized']:+.0f})."))
                journal_mod.log_trade(p, m, asset_class=asset_class, key=cid, label=cid,
                                      side="vente", qty=r["qty"], price=r["price"],
                                      fee=r.get("fee", 0.0), realized=r["realized"])
            else:
                self._log(_L(f"  Vente refusée ({r['reason']}).", f"  Sell rejected ({r['reason']})."))
        self._after_trade()

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def _market_closed_msg(self, tk):
        """Renvoie un message de refus si la place régionale de `tk` est fermée
        au pas de marché courant (cf. core/market_hours.py : sessions par pas,
        2 ouvertes / 1 fermée en rotation), sinon None. Ticker inconnu : on
        laisse pf_mod.buy/sell/short renvoyer l'erreur normale plutôt que de la
        masquer derrière un faux « marché fermé »."""
        idx = self.market.ticker_idx.get(tk)
        if idx is None:
            return None
        region = self.market.companies[idx]["region"]
        if mh_mod.is_region_open(region, self.market.step_count):
            return None
        return _L(
            f"  ⊘ Marché {region} fermé ce pas — réouvre au prochain pas.",
            f"  ⊘ {region} market closed this step — reopens next step.")

    def _after_trade(self):
        p = self.app.gs.player
        audio.play("order")        # retour sonore d'exécution d'ordre
        self._check_badges()
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        nw = pf_mod.net_worth(p, self.market)
        if p.check_game_over(net_worth=nw):
            self.app.scenes.go("gameover")

    def _cmd_buy(self, args):
        if len(args) < 2 or not args[1].lstrip("-").isdigit():
            self._log(_L("  Usage : BUY <ticker> <quantité>","  Usage: BUY <ticker> <quantity>"))
            return
        tk, qty = args[0].upper(), int(args[1])
        closed = self._market_closed_msg(tk)
        if closed:
            self._log(closed)
            return
        res = pf_mod.buy(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            if res["reason"] == "sector_excluded":
                firm = firms_mod.get(self.app.gs.player.firm)
                fname = firm["name"] if firm else "votre firme"
                reason = _L(
                    f"secteur {res.get('sector', '?')} exclu par l'ADN « {fname} » "
                    "(contrainte ESG/mandat de la firme, pas de contournement possible)",
                    f"{res.get('sector', '?')} sector excluded by « {fname} »'s DNA "
                    "(firm ESG/mandate constraint, no workaround)")
            else:
                reason = {"ticker": "ticker inconnu", "qty": "quantité invalide",
                          "isshort": f"position courte ouverte sur {tk} — utilisez COVER",
                          "leverage": f"levier max atteint ({res.get('max_leverage',0):.1f}x) — tapez MARGIN pour le détail"
                          }.get(res["reason"], res["reason"])
            self._log(_L(f"  Achat refusé : {reason}.", f"  Buy rejected: {reason}."))
            return
        slip_pct = self._slippage_pct(res)
        tier = liq_mod.equity_tier(self.market, tk)
        self._log(_L(f"  ✓ Achat {qty} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['total'], self._cur())} (frais inclus)"
                     f" · glissement {slip_pct:+.2f}% · liquidité {tier}.",
                     f"  ✓ Bought {qty} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['total'], self._cur())} (fees incl.)"
                     f" · slippage {slip_pct:+.2f}% · liquidity {tier}."))
        self._warn_if_leveraged()
        self._warn_leverage_cost_first_time()
        if res["total"] > 60000:
            career_mod.log(self.app.gs.player, "deal", f"Achat {qty} {tk}")
        journal_mod.log_trade(self.app.gs.player, self.market, asset_class="Action",
                              key=tk, label=tk, side="achat", qty=qty,
                              price=res["price"], fee=res.get("fee", 0.0))
        self._after_trade()

    def _slippage_pct(self, res):
        """Glissement (spread + impact de marché) en % du prix mi-coté,
        à partir de la clé `slippage` (écart fill - mid) renvoyée par
        core.portfolio.buy/sell."""
        slip = res.get("slippage", 0.0)
        mid = res["price"] - slip
        return (slip / mid * 100.0) if mid else 0.0

    def _warn_leverage_cost_first_time(self):
        """À la première utilisation de la marge (cash emprunté) ou d'un short,
        explique une fois le coût annualisé (taux directeur + surcoût marge /
        frais d'emprunt de titres) — invisible sinon avant le premier relevé
        de financement en fin de tour."""
        p = self.app.gs.player
        if p.flags.get("onboarding_seen_leverage_cost"):
            return
        st = pf_mod.margin_status(p, self.market)
        has_short = any(pos["shares"] < 0 for pos in p.portfolio.values())
        if st["borrowed"] <= 0 and not has_short:
            return
        p.flags["onboarding_seen_leverage_cost"] = True
        rate = self.market.macro["rate"]["v"] if hasattr(self.market, "macro") else 3.0
        from core import portfolio_margin as pm_mod
        self._log(_L(
            f"  » Coût annualisé du levier : intérêts sur capital emprunté ≈ taux "
            f"directeur ({rate:.1f}%) + {pm_mod.MARGIN_SPREAD*100:.0f}% de surcoût · "
            f"short = + {pm_mod.SHORT_FEE_ANNUAL*100:.0f}%/an d'emprunt de titres "
            "(prélevé chaque tour, tapez MARGIN).",
            f"  » Annualized leverage cost: interest on borrowed cash ≈ policy "
            f"rate ({rate:.1f}%) + {pm_mod.MARGIN_SPREAD*100:.0f}% spread · "
            f"short = + {pm_mod.SHORT_FEE_ANNUAL*100:.0f}%/yr stock borrow fee "
            "(charged every turn, type MARGIN)."))

    def _warn_if_leveraged(self):
        """Aperçu immédiat du risque pris : si le trade qui vient de s'exécuter
        approche le levier maximal autorisé, le signaler tout de suite plutôt
        que d'attendre un appel de marge surprise au prochain pas de marché."""
        st = pf_mod.margin_status(self.app.gs.player, self.market)
        if st["max_leverage"] <= 0 or st["leverage"] == float("inf"):
            return
        ratio = st["leverage"] / st["max_leverage"]
        if ratio >= 0.75:
            self._log(_L(
                f"  ⚠ Levier {st['leverage']:.2f}x / {st['max_leverage']:.1f}x max — "
                "marge de sécurité réduite, tapez MARGIN pour le détail.",
                f"  ⚠ Leverage {st['leverage']:.2f}x / {st['max_leverage']:.1f}x max — "
                "safety margin reduced, type MARGIN for detail."))

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
        closed = self._market_closed_msg(tk)
        if closed:
            self._log(closed)
            return
        res = pf_mod.sell(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            self._log(_L(f"  Vente refusée : {'aucune position' if res['reason']=='noposition' else res['reason']}.", f"  Sell rejected: {'no position' if res['reason']=='noposition' else res['reason']}."))
            return
        sign = "+" if res["realized"] >= 0 else ""
        slip_pct = self._slippage_pct(res)
        self._log(_L(f"  ✓ Vente {int(res['qty'])} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['net'], self._cur())}  "
                     f"(P&L réalisé {sign}{widgets.format_money(res['realized'], self._cur())}) "
                     f"· glissement {slip_pct:+.2f}%.",
                     f"  ✓ Sold {int(res['qty'])} {tk} @ {res['price']:.2f} = "
                     f"{widgets.format_money(res['net'], self._cur())}  "
                     f"(realised P&L {sign}{widgets.format_money(res['realized'], self._cur())}) "
                     f"· slippage {slip_pct:+.2f}%."))
        journal_mod.log_trade(self.app.gs.player, self.market, asset_class="Action",
                              key=tk, label=tk, side="vente", qty=res["qty"],
                              price=res["price"], fee=res.get("fee", 0.0),
                              realized=res["realized"])
        self._after_trade()

    def _cmd_short(self, args):
        """SHORT <ticker> <quantité> : vente à découvert (pari à la baisse)."""
        if len(args) < 2 or not args[1].isdigit():
            self._log(_L("  Usage : SHORT <ticker> <quantité>  (parier à la baisse)","  Usage: SHORT <ticker> <quantity>  (bet on a fall)"))
            return
        tk, qty = args[0].upper(), int(args[1])
        closed = self._market_closed_msg(tk)
        if closed:
            self._log(closed)
            return
        res = pf_mod.short(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            reason = {"ticker": "ticker inconnu", "qty": "quantité invalide",
                      "islong": f"position longue ouverte sur {tk} — vendez-la d'abord",
                      "leverage": f"levier max atteint ({res.get('max_leverage',0):.1f}x) — tapez MARGIN pour le détail"
                      }.get(res["reason"], res["reason"])
            self._log(_L(f"  Short refusé : {reason}.", f"  Short rejected: {reason}."))
            return
        tier = liq_mod.equity_tier(self.market, tk)
        self._log(_L(f"  ✓ Short {qty} {tk} @ {res['price']:.2f} = "
                     f"+{widgets.format_money(res['net'], self._cur())} en cash "
                     f"(à racheter via COVER) · liquidité {tier}.",
                     f"  ✓ Shorted {qty} {tk} @ {res['price']:.2f} = "
                     f"+{widgets.format_money(res['net'], self._cur())} cash "
                     f"(buy back via COVER) · liquidity {tier}."))
        self._warn_if_leveraged()
        self._warn_leverage_cost_first_time()
        journal_mod.log_trade(self.app.gs.player, self.market, asset_class="Action",
                              key=tk, label=tk, side="short", qty=qty,
                              price=res["price"], fee=res.get("fee", 0.0))
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
        closed = self._market_closed_msg(tk)
        if closed:
            self._log(closed)
            return
        res = pf_mod.cover(self.app.gs.player, self.market, tk, qty)
        if not res["ok"]:
            self._log(_L(f"  Rachat refusé : {'aucune position courte' if res['reason']=='noshort' else res['reason']}.", f"  Cover rejected: {'no short position' if res['reason']=='noshort' else res['reason']}."))
            return
        sign = "+" if res["realized"] >= 0 else ""
        self._log(_L(f"  ✓ Cover {int(res['qty'])} {tk} @ {res['price']:.2f} "
                     f"(P&L réalisé {sign}{widgets.format_money(res['realized'], self._cur())}).",
                     f"  ✓ Covered {int(res['qty'])} {tk} @ {res['price']:.2f} "
                     f"(realised P&L {sign}{widgets.format_money(res['realized'], self._cur())})."))
        journal_mod.log_trade(self.app.gs.player, self.market, asset_class="Action",
                              key=tk, label=tk, side="couverture", qty=res["qty"],
                              price=res["price"], fee=res.get("fee", 0.0),
                              realized=res["realized"])
        self._after_trade()

    def _cmd_margin(self):
        """MARGIN : état de la marge (equity, exposition, levier, pouvoir d'achat,
        coût de financement cumulé, répartition par classe d'actifs)."""
        p = self.app.gs.player
        st = pf_mod.margin_status(p, self.market)
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
        total_fin = getattr(p, "total_financing_paid", 0.0)
        if total_fin:
            self._log(_L(f"  Financement cumulé payé (intérêts marge + emprunt de titres) : "
                         f"{widgets.format_money(total_fin, cur)}.",
                         f"  Cumulative financing paid (margin interest + stock borrow fees): "
                         f"{widgets.format_money(total_fin, cur)}."))
        from core import analytics as analytics_mod
        by_class = analytics_mod.holdings_table(p, self.market)
        if by_class:
            agg = {}
            for r in by_class:
                agg[r["cls"]] = agg.get(r["cls"], 0.0) + abs(r["value"])
            tot = sum(agg.values()) or 1.0
            parts = " · ".join(f"{c} {v/tot*100:.0f}%" for c, v in
                              sorted(agg.items(), key=lambda kv: -kv[1]))
            self._log(_L(f"  Répartition par classe : {parts}.",
                         f"  Allocation by asset class: {parts}."))

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

    def _cmd_trades(self, args):
        """TRADES [classe] : affiche les dernières entrées du journal de trading."""
        p = self.app.gs.player
        asset_class = args[0].capitalize() if args else None
        entries = journal_mod.list_entries(p, asset_class=asset_class, limit=30)
        rows = []
        for e in entries:
            res = f"{e['realized']:+.0f}" if e["realized"] is not None else "—"
            rows.append(((str(e["id"]), config.COL_AMBER), f"j{e['day']}", e["asset_class"],
                         e["side"], e["key"], f"{e['notional']:,.0f}", res, e["regime"],
                         (e["reason"] or "—")[:16]))
        if not rows:
            rows = [("—", "—", "—", "—", "—", "—", "—", "—", "aucune entrée")]
        self._open_window(_L("JOURNAL DE TRADING", "TRADING JOURNAL"),
                          [("Id", 30), ("Jour", 45), ("Classe", 70), ("Sens", 60),
                           ("Actif", 60), ("Taille", 80), ("P&L", 60), ("Régime", 70),
                           ("Raison", 120)], rows)

    def _cmd_note(self, args):
        """NOTE <id> <commentaire...> : annote une entrée existante du journal."""
        p = self.app.gs.player
        if len(args) < 2 or not args[0].isdigit():
            self._log(_L("  Usage : NOTE <id> <commentaire>.", "  Usage: NOTE <id> <comment>."))
            return
        entry_id = int(args[0])
        comment = " ".join(args[1:])
        e = journal_mod.annotate(p, entry_id, comment=comment)
        if e is None:
            self._log(_L("  Identifiant de journal inconnu.", "  Unknown journal id."))
            return
        self._log(_L(f"  ✓ Note ajoutée à l'entrée #{entry_id}.", f"  ✓ Note added to entry #{entry_id}."))

    def _cmd_jstats(self, args):
        """JSTATS [regime|reason] : bilan du journal de trading, P&L réalisé
        agrégé par régime de marché (défaut) ou par raison de trade."""
        p = self.app.gs.player
        group_by = args[0].lower() if args and args[0].lower() in ("regime", "reason") else "regime"
        stats = journal_mod.performance_stats(p, group_by=group_by)
        if not stats:
            self._log(_L("  Aucun trade clôturé avec P&L réalisé pour le moment.",
                         "  No closed trade with realized P&L yet."))
            return
        disc = journal_mod.discipline_score(p)
        if disc is not None:
            self._log(_L(
                f"  Discipline : {disc['score']:.0f}/100  "
                f"(trades documentés : {disc['reasoned_share']:.0f}%).",
                f"  Discipline: {disc['score']:.0f}/100  "
                f"(documented trades: {disc['reasoned_share']:.0f}%)."))
        rows = [(g["label"], str(g["count"]), f"{g['win_rate']:.0f}%",
                 f"{g['avg_pnl']:+.0f}", f"{g['total_pnl']:+.0f}") for g in stats]
        title = (_L("BILAN PAR RÉGIME", "STATS BY REGIME") if group_by == "regime"
                 else _L("BILAN PAR RAISON", "STATS BY REASON"))
        self._open_window(title, [(_L("Régime", "Regime") if group_by == "regime"
                                    else _L("Raison", "Reason"), 140),
                                   ("Trades", 60), ("Win %", 60),
                                   ("P&L moy.", 90), ("P&L total", 90)], rows)

    def _cmd_twap(self, args):
        """TWAP <BUY|SELL> <ticker> <qté> <steps> : exécute l'ordre réparti
        sur <steps> pas de marché (actions uniquement)."""
        p = self.app.gs.player
        if len(args) < 4:
            self._log(_L("  Usage : TWAP <BUY|SELL> <ticker> <qté> <steps>  (actions).",
                         "  Usage: TWAP <BUY|SELL> <ticker> <qty> <steps>  (stocks)."))
            return
        side_raw = args[0].upper()
        if side_raw in ("BUY", "ACHETER", "LONG"):
            side = "buy"
        elif side_raw in ("SELL", "VENDRE"):
            side = "sell"
        else:
            self._log(_L("  Sens invalide : BUY ou SELL.", "  Invalid side: BUY or SELL."))
            return
        tk = self.market.resolve(args[1])
        if tk is None:
            self._log(_L(f"  Ticker inconnu : {args[1]}.", f"  Unknown ticker: {args[1]}."))
            return
        if not args[2].isdigit() or not args[3].isdigit():
            self._log(_L("  Quantité et steps doivent être des entiers.",
                         "  Quantity and steps must be integers."))
            return
        qty, steps = int(args[2]), int(args[3])
        if qty <= 0 or steps <= 0:
            self._log(_L("  Quantité et steps doivent être positifs.",
                         "  Quantity and steps must be positive."))
            return
        from core import orders as orders_mod
        r = orders_mod.place_twap(p, self.market, "Action", tk, side, qty, steps, label=tk)
        if not r["ok"]:
            self._log(_L(f"  TWAP refusé ({r['reason']}).", f"  TWAP rejected ({r['reason']})."))
            return
        o = r["order"]
        side_label = _L("Achat", "Buy") if side == "buy" else _L("Vente", "Sell")
        self._log(_L(f"  TWAP posé : {side_label} {o['total_qty']:g} {tk} sur {o['steps_total']} pas.",
                     f"  TWAP set: {side_label} {o['total_qty']:g} {tk} over {o['steps_total']} steps."))

    def _cmd_pending(self):
        """PENDING : liste les ordres TWAP/fractionnés en attente."""
        p = self.app.gs.player
        from core import orders as orders_mod
        orders = orders_mod.list_orders(p)
        if not orders:
            self._log(_L("  Aucun ordre fractionné en attente.", "  No pending fractional order."))
            return
        rows = []
        for o in orders:
            side = _L("Achat", "Buy") if o["side"] == "buy" else _L("Vente", "Sell")
            rows.append(((f"#{o['id']}", config.COL_AMBER), o["key"], side,
                         f"{o['remaining']:g}/{o['total_qty']:g}",
                         f"{o['steps_left']}/{o['steps_total']}"))
        self._open_window(_L("ORDRES TWAP", "TWAP ORDERS"),
                          [("Id", 40), ("Actif", 70), ("Sens", 70),
                           ("Reste", 90), ("Pas", 70)], rows)
