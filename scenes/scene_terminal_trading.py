"""
scene_terminal_trading.py — Commandes de trading du terminal (TerminalTradingMixin) :
actions/obligations/commodities/crypto (achat/vente/short/cover), marge, allocation,
hedge, rebalance, journal de trading. Extrait de scene_terminal_commands.py pour
limiter sa taille ; mixé dans TerminalScene avec les autres mixins de commandes.
"""

from core import config
from core import journal as journal_mod
from core import career as career_mod
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

    def _after_trade(self):
        p = self.app.gs.player
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
        journal_mod.log_trade(self.app.gs.player, self.market, asset_class="Action",
                              key=tk, label=tk, side="achat", qty=qty,
                              price=res["price"], fee=res.get("fee", 0.0))
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
