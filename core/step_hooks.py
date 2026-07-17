"""
step_hooks.py — Registre ORDONNÉ des systèmes joués à chaque pas de marché.

Avant ce module, chaque instrument (dividendes, coupons, repo, CDS, TRS,
ordres conditionnels, limites VaR…) ajoutait son bloc à la main au milieu de
`GameState.advance_step`, dans un ordre implicite qui grossissait à chaque
lot. L'ordre d'exécution est pourtant un INVARIANT de gameplay (ex. : les
ordres conditionnels du joueur s'exécutent AVANT le contrôle de marge, pour
qu'un ordre voulu passe avant une liquidation forcée sur la position déjà
réduite). Il est désormais EXPLICITE dans `STEP_HOOKS` et verrouillé par
`tests/test_step_hooks.py`.

Contrat d'un hook : `hook(p, market, ctx)` — `p` est le PlayerState, `market`
le moteur (jamais None ici : `advance_step` n'appelle `run()` que si un
marché est fourni), `ctx` le dict-contexte du pas (cf. `new_context()`), que
le hook mute (cash crédité via `p.adjust_cash`, résultats déposés dans `ctx`
pour le résumé du terminal). Un hook ne retourne rien. Ajouter un instrument
= écrire son hook + l'insérer à la bonne place dans `STEP_HOOKS`, sans
toucher `game_state.py`.
"""
from core import config
from core.i18n import get_lang


def _L(fr, en):
    """Helper i18n court pour les messages générés dans ce module."""
    return fr if get_lang() == "fr" else en


def new_context():
    """Contexte vierge d'un pas : les clés reprises telles quelles dans le
    dict-résumé retourné par `advance_step` (mêmes défauts qu'avant le
    passage au registre)."""
    return {
        "dividends": 0.0,
        "financing": None,
        "margin_call": None,
        "structured_due": None,
        "securitised_due": None,
        "hedges_due": None,
        "options_due": None,
        "ipos_settled": None,
        "fx_due": None,
        "macro_resolved": None,
        "swaps_expired": [],
        "conditional_orders_executed": None,
        "nw": 0.0,
    }


def _passive_income(p, ctx, amount):
    """Crédite un revenu passif (catégorie « revenus » de l'attribution) et
    l'agrège dans le revenu passif affiché du pas."""
    if amount:
        p.adjust_cash(amount, category="revenus")
        ctx["dividends"] += amount


# ----- Revenus de portage ------------------------------------------------

def _hook_equity_dividends(p, market, ctx):
    """Dividendes des positions actions (longs touchent, shorts paient)."""
    from core import portfolio
    _passive_income(p, ctx, portfolio.dividends(p, market, config.DAYS_PER_STEP))


def _hook_bond_coupons(p, market, ctx):
    """Coupons obligataires (revenu de portage)."""
    if getattr(p, "bonds", None):
        from core import bonds as _bonds
        _passive_income(p, ctx, _bonds.coupons(p, market, config.DAYS_PER_STEP))


def _hook_commodity_roll(p, market, ctx):
    """Roulement des futures commodities (roll yield : coût en contango)."""
    if getattr(p, "commodities", None):
        from core import commodities as _cmdty
        _passive_income(p, ctx, _cmdty.roll_cost(p, market, config.DAYS_PER_STEP))


def _hook_cbdc_interest(p, market, ctx):
    """Intérêt de la CBDC (actif sûr rémunéré au taux directeur)."""
    if getattr(p, "crypto", None):
        from core import crypto as _crypto
        _passive_income(p, ctx, _crypto.interest(p, market, config.DAYS_PER_STEP))


def _hook_fx_carry(p, market, ctx):
    """Portage FX (carry) : différentiel de taux couru sur les positions spot
    ouvertes (core/fx_carry) — le carry trade devient un vrai revenu (ou un
    vrai coût)."""
    if getattr(p, "fx_positions", None):
        from core import fx_carry as _fxc
        _passive_income(p, ctx, _fxc.accrue(p, market, config.DAYS_PER_STEP))


def _hook_funding_desk(p, market, ctx):
    """Desk de FINANCEMENT : intérêts repo/coupons du collatéral, frais
    d'emprunt des shorts / revenu de prêt, sweep monétaire, dépôts à terme
    échus et appel de marge repo (core/repo, seclending, money_market)."""
    from core import money_market as _mm
    from core import notify_queue as _nq
    from core import repo as _repo
    from core import seclending as _secl
    funding = 0.0
    if getattr(p, "repo_positions", None):
        funding += _repo.accrue(p, market, config.DAYS_PER_STEP)
    if p.portfolio:
        funding += _secl.accrue(p, market, config.DAYS_PER_STEP)
    funding += _mm.sweep_accrue(p, market, config.DAYS_PER_STEP)
    _passive_income(p, ctx, funding)
    for _dep in _mm.mature_due(p, market):
        _nq.push(p, _L("Depot a terme echu : ", "Term deposit matured: ")
                 + f"+{_dep['amount'] + _dep['interest']:,.0f} "
                 + _L("(interets ", "(interest ") + f"{_dep['interest']:,.0f})",
                 "good")
    if getattr(p, "repo_positions", None):
        for _ev in _repo.mark_and_call(p, market):
            _nq.push(p, _L("APPEL DE MARGE REPO - pension liquidee : ",
                           "REPO MARGIN CALL - position liquidated: ")
                     + f"{_ev['name']} ({_ev['equity']:+,.0f})", "warn")


def _hook_credit_rate_derivatives(p, market, ctx):
    """Dérivés de crédit/taux & convertibles : primes CDS courues, évènements
    de crédit, flux nets d'IRS, coupons de convertibles, TRS (jambe de
    financement + dividende courus, évènement de crédit / échéance au MTM)."""
    from core import notify_queue as _nq
    deriv = 0.0
    if getattr(p, "cds_positions", None):
        from core import cds as _cds
        deriv += _cds.accrue(p, market, config.DAYS_PER_STEP)
        for _ev in _cds.evaluate_due(p, market):
            if _ev["kind"] == "credit_event":
                _nq.push(p, _L("EVENEMENT DE CREDIT ", "CREDIT EVENT ")
                         + f"{_ev['ticker']} : protection payee "
                         + f"+{_ev['payoff']:,.0f}", "good")
            else:
                _nq.push(p, f"CDS {_ev['ticker']} "
                         + _L("expire sans evenement", "expired unexercised"),
                         "info")
    if getattr(p, "irs_positions", None):
        from core import irs as _irs
        deriv += _irs.accrue(p, market, config.DAYS_PER_STEP)
    if getattr(p, "convertibles", None):
        from core import convertibles as _conv
        deriv += _conv.accrue(p, market, config.DAYS_PER_STEP)
    if getattr(p, "trs_positions", None):
        from core import trs as _trs
        deriv += _trs.accrue(p, market, config.DAYS_PER_STEP)
        for _ev in _trs.evaluate_due(p, market):
            _side = _L("Receiver", "Receiver") if _ev["side"] == "receiver" \
                    else _L("Payer", "Payer")
            if _ev["kind"] == "credit_event":
                _nq.push(p, _L("EVENEMENT DE CREDIT ", "CREDIT EVENT ")
                         + f"{_ev['ticker']} ({_side}) : "
                         + f"{_ev['payoff']:+,.0f}", "good")
            else:
                _nq.push(p, f"TRS {_ev['ticker']} ({_side}) "
                         + _L("echu : MTM regle ",
                              "matured: MTM settled ")
                         + f"{_ev['payoff']:+,.0f}", "info")
    _passive_income(p, ctx, deriv)


def _hook_merger_arb(p, market, ctx):
    """Arbitrage de fusion : résolution des OPA arrivées à échéance
    (conclusion → paiement à l'offre, rupture → perte). Le cash est crédité
    dans evaluate_due ; ici on notifie le joueur."""
    if getattr(p, "arb_positions", None):
        from core import merger_arb as _marb
        from core import notify_queue as _nq
        for _ev in _marb.evaluate_due(p, market):
            if _ev["closed"]:
                _nq.push(p, _L("OPA CONCLUE ", "DEAL CLOSED ")
                         + f"{_ev['ticker']} ({_ev['acquirer']}) : "
                         + f"{_ev['pnl']:+,.0f}", "good")
            else:
                _nq.push(p, _L("OPA ROMPUE ", "DEAL BROKEN ")
                         + f"{_ev['ticker']} : {_ev['pnl']:+,.0f}", "warn")


# ----- Ordres automatiques & alertes --------------------------------------

def _hook_conditional_orders(p, market, ctx):
    """Ordres conditionnels (stop-loss/take-profit) : exécutés AVANT le
    contrôle de marge, comme un vrai ordre du joueur (voulu) passerait avant
    une liquidation forcée (subie) sur la position réduite."""
    if not getattr(p, "conditional_orders", None):
        return
    from core import conditional_orders as _condord
    _condord.update_trailing_stops(p, market)
    executed = _condord.execute_due(p, market)
    ctx["conditional_orders_executed"] = executed
    if executed:
        from core import audio as _audio
        from core import notify_queue as _nq
        _audio.play("conditional")
        for _exec in executed[:3]:
            _o = _exec["order"]
            _side = _L("Stop-loss", "Stop-loss") if _o["kind"] == "stop" \
                else _L("Take-profit", "Take-profit")
            _txt = (f"{_side} {_o['ticker']} " + _L("exécuté", "executed")
                    + f" @ {_exec['result']['price']:.2f}")
            _nq.push(p, _txt, "info", action="trading",
                     action_kwargs={"ticker": _o["ticker"]})


def _hook_twap_orders(p, market, ctx):
    """Ordres TWAP/fractionnés : exécution par tranches à chaque pas."""
    if not getattr(p, "pending_orders", None):
        return
    from core import orders as _orders
    twap_executed = _orders.execute_due(p, market)
    if twap_executed:
        from core import audio as _audio
        from core import notify_queue as _nq
        _audio.play("order")
        for _exec in twap_executed[:3]:
            _side = _L("Achat", "Buy") if _exec["side"] == "buy" else _L("Vente", "Sell")
            _txt = f"TWAP {_exec['key']} : {_side} {_exec['chunk']:g} @ {_exec['price']:.2f}"
            _nq.push(p, _txt, "info", action="trading",
                     action_kwargs={"ticker": _exec["key"]})


def _hook_price_alerts(p, market, ctx):
    """Alertes de prix déclenchées (actions ET indices — un indice ne se
    trade pas, le clic ouvre le hub Marché)."""
    if not getattr(p, "alerts", None):
        return
    from core import alerts as _alerts
    from core import notify_queue as _nq
    for ev in _alerts.check(p, market)[:3]:
        kind = "warn" if not ev["above"] else "info"
        if ev.get("is_index"):
            _nq.push(p, _alerts.format_trigger(ev), kind, action="markethub")
        else:
            _nq.push(p, _alerts.format_trigger(ev), kind,
                     action="trading", action_kwargs={"ticker": ev["ticker"]})


def _hook_watchlist_earnings(p, market, ctx):
    """Résultats trimestriels d'une société SUIVIE (watchlist) : le moteur
    publie `market.last_earnings` à chaque pas (~1/4 des sociétés) — toast +
    message inbox pour chaque valeur suivie qui publie CE pas."""
    watchlist = getattr(p, "watchlist", None)
    if not (watchlist and getattr(market, "last_earnings", None)):
        return
    from core import inbox as _inbox
    from core import notify_queue as _nq
    watched = {t.upper() for t in watchlist}
    for rep in market.last_earnings:
        if rep["ticker"] not in watched:
            continue
        verb = _L("bat les attentes", "beats expectations") if rep["beat"] \
            else _L("déçoit", "misses expectations")
        pct = rep["surprise"] * 100.0
        txt = (f"{rep['ticker']} {verb} ({pct:+.1f}%)")
        _nq.push(p, txt, "good" if rep["beat"] else "warn",
                 action="scene", action_kwargs={"name": "company", "ticker": rep["ticker"]})
        _inbox.push(p, "desk",
                    _L("Bureau de recherche", "Research desk"),
                    _L(f"Résultats {rep['ticker']} : {verb}",
                       f"{rep['ticker']} earnings: {verb}"),
                    _L(f"{rep['name']} ({rep['ticker']}) publie une surprise de "
                       f"{pct:+.1f}% par rapport aux attentes. Guidance : "
                       f"{rep['guidance_label']}.",
                       f"{rep['name']} ({rep['ticker']}) reports a {pct:+.1f}% "
                       f"surprise vs expectations. Guidance: {rep['guidance_label']}."))


# ----- Marge, limites de risque, veille ------------------------------------

def _hook_financing_and_margin(p, market, ctx):
    """Intérêts de financement (marge + emprunt de titres) puis CONTRÔLE DE
    MARGE — toujours APRÈS l'exécution des ordres conditionnels du joueur.
    Une liquidation forcée peut avoir fermé des positions portant des ordres
    conditionnels : on les purge tout de suite, sinon un ordre périmé
    survivrait un pas et pourrait s'appliquer à une position rouverte."""
    from core import portfolio
    ctx["financing"] = portfolio.accrue_financing(p, market, config.DAYS_PER_STEP)
    margin_call = portfolio.check_margin_call(p, market)
    ctx["margin_call"] = margin_call
    if margin_call:
        from core import audio
        from core import notify_queue as _nq
        audio.play("margin_call")
        _nq.push(p, _L("Appel de marge : positions liquidées.",
                       "Margin call : positions liquidated."), "bad",
                 action="book")
        if getattr(p, "conditional_orders", None):
            from core import conditional_orders as _condord
            _condord.prune_orphans(p)


def _hook_leverage_sample(p, market, ctx):
    """Échantillonnage du levier (style de jeu, indépendant de la progression
    de grade) : utilisé par career.risk_profile() pour moduler les mandats."""
    from core import portfolio
    if portfolio.leverage(p, market) >= 2.5:
        p.flags["high_leverage_steps"] = p.flags.get("high_leverage_steps", 0) + 1


def _hook_firm_var_limit(p, market, ctx):
    """Limite de VaR IMPOSÉE PAR LA FIRME (par grade) : avertissement, puis
    réputation, puis RÉDUCTION FORCÉE (cf. risklimits.firm_var_*)."""
    from core import notify_queue as _nq
    from core import risklimits as _rl
    _firm_ev = _rl.firm_var_enforce(p, market)
    if _firm_ev is None:
        return
    if _firm_ev["level"] == "cut":
        _nq.push(p, _L("RISQUE : la firme a COUPÉ ",
                       "RISK: the firm CUT ")
                 + f"{_firm_ev['cut_qty']} × {_firm_ev['cut_ticker']}"
                 + _L(" (VaR au-dessus de la limite du grade)",
                      " (VaR above grade limit)"), "warn")
    elif _firm_ev["level"] == "rep":
        _nq.push(p, _L("RISQUE : dépassement persistant de la limite "
                       "de VaR de la firme (réputation −3)",
                       "RISK: persistent firm VaR limit breach "
                       "(reputation −3)"), "warn")
    else:
        _nq.push(p, _L("Avertissement risque : VaR ",
                       "Risk warning: VaR ")
                 + f"{_firm_ev['var']:.2f} M > "
                 + _L("limite ", "limit ")
                 + f"{_firm_ev['limit']:.2f} M", "warn")


def _hook_risk_breach_streak(p, market, ctx):
    """Dépassement persistant des limites de risque du PROFIL (cf.
    core/risklimits.py, scenes/scene_risk.py) : un dépassement isolé ne coûte
    rien, mais le laisser filer pénalise la réputation tant qu'il n'est pas
    corrigé."""
    from core import risklimits as _risklimits
    if _risklimits.check_limits(p, market)["breaches"]:
        p.flags["risk_breach_streak"] = p.flags.get("risk_breach_streak", 0) + 1
        if p.flags["risk_breach_streak"] >= 3:
            reason = ("Persistent risk limit breach" if get_lang() == "en"
                      else "Dépassement persistant des limites de risque")
            p.adjust_reputation(-2, reason=reason)
    else:
        p.flags["risk_breach_streak"] = 0


def _hook_saved_screens(p, market, ctx):
    """Veille marché : critères sauvegardés (core/opportunities.py) →
    notification inbox dès qu'un nouveau titre matche (une seule fois par
    titre/critère)."""
    if getattr(p, "saved_screens", None):
        from core import opportunities as _opportunities
        _opportunities.check_alerts(p, market)


# ----- Échéances d'instruments ---------------------------------------------

def _hook_structured_due(p, market, ctx):
    """Produits structurés arrivés à échéance."""
    if getattr(p, "structured", None):
        from core import structured as _struct
        ctx["structured_due"] = _struct.evaluate_due(p, market)


def _hook_securitised_due(p, market, ctx):
    """Tranches de titrisation arrivées à échéance."""
    if getattr(p, "securitised", None):
        from core import securitisation as _sec
        ctx["securitised_due"] = _sec.evaluate_due(p, market)


def _hook_hedges_due(p, market, ctx):
    """Puts protecteurs (couverture) arrivés à échéance."""
    if getattr(p, "hedges", None):
        from core import hedging as _hedging
        hedges_due = _hedging.evaluate_due(p, market)
        ctx["hedges_due"] = hedges_due
        if hedges_due:
            from core import notify_queue as _nq
            _total = sum(h["pnl"] for h in hedges_due)
            _kind = "good" if _total >= 0 else "bad"
            _nq.push(p, _L(f"Couverture échue : P&L {_total:+.0f}.",
                           f"Hedge expired : P&L {_total:+.0f}."), _kind)


def _hook_options_due(p, market, ctx):
    """Options sur actions arrivées à échéance."""
    if getattr(p, "options", None):
        from core import options as _options
        options_due = _options.evaluate_due(p, market)
        ctx["options_due"] = options_due
        if options_due:
            from core import notify_queue as _nq
            for _opt in options_due[:3]:
                _kind = "good" if _opt["pnl"] >= 0 else "bad"
                _nq.push(p, _L(f"Option {_opt['position']['ticker']} échue : P&L {_opt['pnl']:+.0f}.",
                               f"Option {_opt['position']['ticker']} expired : P&L {_opt['pnl']:+.0f}."), _kind)


def _hook_ipo_listings(p, market, ctx):
    """IPO souscrites qui arrivent en cotation."""
    if getattr(p, "ipos", None):
        from core import ipo as _ipo
        ipos_settled = _ipo.evaluate_listings(p, market)
        ctx["ipos_settled"] = ipos_settled
        if ipos_settled:
            from core import notify_queue as _nq
            for _ipo_res in ipos_settled[:3]:
                _nq.push(p, _L(f"IPO {_ipo_res['ticker']} cotée : {_ipo_res['shares']:.0f} actions reçues.",
                               f"IPO {_ipo_res['ticker']} listed : {_ipo_res['shares']:.0f} shares received."), "good")


def _hook_fx_forwards_due(p, market, ctx):
    """Forwards FX arrivés à échéance (règlement)."""
    if getattr(p, "fx_forwards", None):
        from core import fx as _fx
        fx_due = _fx.evaluate_due(p, market)
        ctx["fx_due"] = fx_due
        if fx_due:
            from core import notify_queue as _nq
            for _fxr in fx_due[:3]:
                _kind = "good" if _fxr.get("pnl", 0) >= 0 else "bad"
                _nq.push(p, _L(f"Forward FX échu : P&L {_fxr.get('pnl', 0):+.0f}.",
                               f"FX forward expired : P&L {_fxr.get('pnl', 0):+.0f}."), _kind)


def _hook_macro_bets(p, market, ctx):
    """Paris macro résolus (calendrier macro, core/macrocal.py)."""
    if getattr(p, "macro_events", None):
        from core import macrocal as _macrocal
        macro_resolved = _macrocal.resolve_due_events(p, market)
        ctx["macro_resolved"] = macro_resolved
        if macro_resolved:
            from core import notify_queue as _nq
            for _mr in macro_resolved[:3]:
                _kind = "good" if _mr.get("pnl", 0) >= 0 else "bad"
                _nq.push(p, _L(f"Pari macro résolu : P&L {_mr.get('pnl', 0):+.0f}.",
                               f"Macro bet resolved : P&L {_mr.get('pnl', 0):+.0f}."), _kind)


def _hook_currency_swaps(p, market, ctx):
    """Swaps de devises : flux couru + expirations."""
    if getattr(p, "currency_swaps", None):
        from core import swaps as _swaps
        swap_flow, swaps_expired = _swaps.accrue(p, market, config.DAYS_PER_STEP)
        ctx["swaps_expired"] = swaps_expired
        _passive_income(p, ctx, swap_flow)
        if swaps_expired:
            from core import notify_queue as _nq
            for _sw in swaps_expired[:3]:
                _nq.push(p, _L(f"Swap de devises {_sw['foreign_region']} échu.",
                               f"Currency swap {_sw['foreign_region']} expired."), "info")


# ----- Clôture du pas -------------------------------------------------------

def _hook_net_worth(p, market, ctx):
    """Valeur nette du pas (cash + toutes classes d'actifs) — TOUJOURS après
    tous les règlements du pas, pour que l'historique/le contrôle de faillite
    voient l'état final."""
    from core import portfolio
    ctx["nw"] = portfolio.net_worth(p, market)


def _hook_hist_scenario(p, market, ctx):
    """Scénario HISTORIQUE du run (core/histscenarios.py) : déclenche la
    crise scriptée au pas prévu et rend le verdict au pas de fin. APRÈS
    "net_worth" (il consomme la valeur nette du pas pour l'ancre et le
    ratio final)."""
    if not p.flags.get("hist_scenario"):
        return
    from core import histscenarios as _hist
    from core import notify_queue as _nq
    ev = _hist.step(p, market, ctx["nw"])
    if not ev:
        return
    if ev["kind"] == "crisis":
        _nq.push(p, _L("DÉFI HISTORIQUE — la crise frappe : ",
                       "HISTORICAL CHALLENGE — the crisis hits: ")
                 + _hist.label(ev["scenario"]), "warn", action="markethub")
    else:
        if ev["success"]:
            _nq.push(p, _L("DÉFI HISTORIQUE RÉUSSI : ",
                           "HISTORICAL CHALLENGE PASSED: ")
                     + f"{ev['ratio']:.0%} " + _L("du patrimoine préservé",
                                                  "of net worth preserved"), "good")
        else:
            _nq.push(p, _L("Défi historique échoué : ",
                           "Historical challenge failed: ")
                     + f"{ev['ratio']:.0%} " + _L("du patrimoine préservé",
                                                  "of net worth preserved"), "warn")


def _hook_portfolio_news(p, market, ctx):
    """News feed contextualisé au portefeuille (résultats, événements, gros
    mouvements, crises sectorielles) — après que le marché a step et que les
    valorisations sont à jour."""
    from core import portfolio_news as _portfolio_news
    _portfolio_news.generate(p, market)


# L'ORDRE EST UN INVARIANT DE GAMEPLAY — ne pas trier, ne pas réordonner sans
# comprendre les dépendances (commentées sur les hooks concernés). Points durs :
#  - "conditional_orders" AVANT "financing_and_margin" (ordre voulu du joueur
#    avant liquidation forcée) ;
#  - "net_worth" APRÈS tous les règlements/échéances du pas ;
#  - les revenus de portage en tête (le cash crédité compte dans la marge).
STEP_HOOKS = [
    ("equity_dividends", _hook_equity_dividends),
    ("bond_coupons", _hook_bond_coupons),
    ("commodity_roll", _hook_commodity_roll),
    ("cbdc_interest", _hook_cbdc_interest),
    ("fx_carry", _hook_fx_carry),
    ("funding_desk", _hook_funding_desk),
    ("credit_rate_derivatives", _hook_credit_rate_derivatives),
    ("merger_arb", _hook_merger_arb),
    ("conditional_orders", _hook_conditional_orders),
    ("twap_orders", _hook_twap_orders),
    ("price_alerts", _hook_price_alerts),
    ("watchlist_earnings", _hook_watchlist_earnings),
    ("financing_and_margin", _hook_financing_and_margin),
    ("leverage_sample", _hook_leverage_sample),
    ("firm_var_limit", _hook_firm_var_limit),
    ("risk_breach_streak", _hook_risk_breach_streak),
    ("saved_screens", _hook_saved_screens),
    ("structured_due", _hook_structured_due),
    ("securitised_due", _hook_securitised_due),
    ("hedges_due", _hook_hedges_due),
    ("options_due", _hook_options_due),
    ("ipo_listings", _hook_ipo_listings),
    ("fx_forwards_due", _hook_fx_forwards_due),
    ("macro_bets", _hook_macro_bets),
    ("currency_swaps", _hook_currency_swaps),
    ("net_worth", _hook_net_worth),
    ("hist_scenario", _hook_hist_scenario),
    ("portfolio_news", _hook_portfolio_news),
]


def run(p, market):
    """Joue tous les hooks du pas dans l'ordre et retourne le contexte
    rempli. Appelé par `GameState.advance_step` quand un marché est fourni."""
    ctx = new_context()
    for _name, hook in STEP_HOOKS:
        hook(p, market, ctx)
    return ctx
