"""
portfolio_news.py — News feed contextualisé au portefeuille (logique pure).

A chaque pas de marché, génère des messages inbox quand :
  - une société détenue publie des résultats (beat/miss + guidance),
  - une société détenue subit un événement d'entreprise,
  - une position détenue bouge de plus de X % sur le pas,
  - une crise active touche fortement un secteur ou une région où le joueur
    est exposé.

Le module est appelé depuis GameState.advance_step() ; il lit le marché
DÉJÀ avancé (market.step() a été joué juste avant) et pousse des messages
inbox via core.inbox.push. On limite le spam avec un cooldown par type/ticker.
"""
from core import config, inbox

# Seuils
PRICE_MOVE_PCT = 8.0        # position bouge de +/- X% sur le pas -> message
SECTOR_CRISIS_PCT = 12.0    # exposition sectorielle impactée de +/- X% -> message
COOLDOWN_STEPS = 8          # pas minimum entre deux messages sur le même ticker/type


def _cooldown_key(kind, key):
    return f"_pn_{kind}_{key}"


def _on_cooldown(player, kind, key, step, cooldown=COOLDOWN_STEPS):
    cd = player.flags.setdefault("_portfolio_news_cooldown", {})
    last = cd.get(_cooldown_key(kind, key), -cooldown - 1)
    if step - last < cooldown:
        return True
    cd[_cooldown_key(kind, key)] = step
    return False


def _fmt_pct(v):
    return f"{v:+.1f}%"


def _fmt_money(v, cur):
    if v >= 1e9:
        return f"{v/1e9:.2f} G{cur}"
    if v >= 1e6:
        return f"{v/1e6:.2f} M{cur}"
    if v >= 1e3:
        return f"{v/1e3:.2f} k{cur}"
    return f"{v:.0f} {cur}"


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
def _push_earnings(player, market, tk, rep, cur):
    name = rep.get("name", tk)
    surprise = rep.get("surprise", 0.0)
    beat = rep.get("beat", surprise >= 0)
    guidance = rep.get("guidance_label", "")
    growth = rep.get("growth", 0.0) * 100.0
    if beat:
        subject = f"{tk} — Résultats supérieurs aux attentes"
        body = (f"{name} a publié des résultats en hausse de {_fmt_pct(growth)} "
                f"et dépasse le consensus de {_fmt_pct(surprise*100)}. "
                f"Guidance : {guidance}.")
        kind = "desk"
    else:
        subject = f"{tk} — Résultats décevants"
        body = (f"{name} a publié des résultats en baisse de {_fmt_pct(growth)} "
                f"avec un manque de {_fmt_pct(-surprise*100)} au consensus. "
                f"Guidance : {guidance}.")
        kind = "desk"
    inbox.push(player, kind, "Research Desk", subject, body)


def _push_company_event(player, market, tk, ev, cur):
    subject = f"{tk} — {ev.get('title', 'Événement')}"[:80]
    body = ev.get("desc", "")
    inbox.push(player, "desk", "News Desk", subject, body)


def _push_price_move(player, market, tk, move_pct, pnl, cur):
    direction = "envolée" if move_pct > 0 else "chute"
    subject = f"{tk} — {direction} de {_fmt_pct(move_pct)} ce pas"
    body = (f"Votre position sur {tk} bouge de {_fmt_pct(move_pct)}. "
            f"Impact P&L latent : {_fmt_money(pnl, cur)}.")
    inbox.push(player, "desk", "Trading Desk", subject, body)


def _push_crisis_sector(player, market, sector, move_pct, exposure, cur):
    direction = "sous tension" if move_pct < 0 else "en forte hausse"
    subject = f"Secteur {sector} {direction}"
    body = (f"Le secteur {sector} bouge de {_fmt_pct(move_pct)} ce pas. "
            f"Votre exposition sectorielle nette y est de {_fmt_money(exposure, cur)}.")
    inbox.push(player, "desk", "Risk Desk", subject, body)


# ---------------------------------------------------------------------------
# Analyse du portefeuille
# ---------------------------------------------------------------------------
def _sector_exposure(player, market, sector):
    """Valeur nette signée dans un secteur (actions uniquement)."""
    from core import portfolio_views
    total = 0.0
    for h in portfolio_views.holdings(player, market):
        c = market.companies[market.ticker_idx[h["ticker"]]]
        if c["sector"] == sector:
            total += h["value"]
    return total


def generate(player, market):
    """Génère les messages inbox liés au portefeuille pour CE pas de marché.
    À appeler depuis GameState.advance_step() après que market.step() ait été
    joué."""
    if market is None:
        return
    cur = config.CONTINENTS.get(player.continent, {}).get("currency", "$")
    step = market.step_count

    # 1) earnings des sociétés détenues
    for tk, pos in player.portfolio.items():
        rep = market.earnings_log.get(tk)
        if rep and rep.get("step") == step:
            if not _on_cooldown(player, "earnings", tk, step):
                _push_earnings(player, market, tk, rep, cur)

    # 2) événements d'entreprise des sociétés détenues
    for tk, pos in player.portfolio.items():
        events = market.company_events_log.get(tk, [])
        for ev in reversed(events):
            if ev.get("step") == step:
                if not _on_cooldown(player, "event", tk, step):
                    _push_company_event(player, market, tk, ev, cur)
                break

    # 3) gros mouvement de prix d'une position détenue
    if market.prev_price is not None and market.last_ret is not None:
        for tk, pos in player.portfolio.items():
            i = market.ticker_idx.get(tk)
            if i is None:
                continue
            prev = float(market.prev_price[i])
            cur_price = float(market.price[i])
            if prev <= 0:
                continue
            move_pct = (cur_price / prev - 1.0) * 100.0
            if abs(move_pct) >= PRICE_MOVE_PCT:
                # on veut le P&L DU PAS, pas le P&L latent total
                pnl_step = (cur_price - prev) * pos["shares"]
                if not _on_cooldown(player, "move", tk, step):
                    _push_price_move(player, market, tk, move_pct, pnl_step, cur)

    # 4) crise sectorielle impactant une exposition significative
    for cr in market.crises:
        if not cr.sectors:
            continue
        for sector, shock in cr.sectors.items():
            exp = _sector_exposure(player, market, sector)
            if exp == 0:
                continue
            # approximation du mouvement sectoriel sur ce pas
            move_pct = shock * 100.0
            if abs(move_pct) >= SECTOR_CRISIS_PCT:
                if not _on_cooldown(player, "crisis_sector", sector, step):
                    _push_crisis_sector(player, market, sector, move_pct, exp, cur)
