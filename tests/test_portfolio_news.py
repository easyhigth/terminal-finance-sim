"""Tests pour core/portfolio_news.py — génération contextualisée d'inbox."""
import pytest

from core import config, game_state
from core.market import Market
from core import portfolio as pf, portfolio_news


def _make_player_and_market(seed=42, steps=10, cash=1_000_000):
    gs = game_state.GameState()
    p = gs.player
    p.continent = "Europe"
    p.cash = cash
    m = Market(seed=seed)
    for _ in range(steps):
        m.step()
    p.day = m.step_count * config.DAYS_PER_STEP
    return p, m


def test_earnings_news_for_held_stock():
    """Un résultat publié ce pas par une société détenue génère un inbox."""
    p, m = _make_player_and_market(steps=10)
    # avancer jusqu'à un pas où il y a des earnings
    # EARN_PERIOD est typiquement 8 pas ; on force un pas supplémentaire avec achat
    tk = "MVC"
    pf.buy(p, m, tk, 100)
    # le market.step() suivant est celui où les earnings peuvent tomber
    # on avance un pas
    m.step()
    p.day = m.step_count * config.DAYS_PER_STEP
    prev_count = len(p.inbox)
    portfolio_news.generate(p, m)
    # soit on a un message earnings, soit rien si pas d'earnings ce pas
    if m.earnings_log.get(tk, {}).get("step") == m.step_count:
        assert len(p.inbox) > prev_count
        assert any(tk in msg["subject"] for msg in p.inbox[prev_count:])


def test_big_price_move_generates_news():
    """Un mouvement de prix extrême génère un message inbox."""
    p, m = _make_player_and_market(steps=10)
    tk = "MVC"
    pf.buy(p, m, tk, 100)
    # forcer un gros mouvement artificiel
    i = m.ticker_idx[tk]
    m.prev_price = m.price.copy()
    m.price[i] *= 1.20
    m.last_ret = [0.0] * m.n
    m.last_ret[i] = 0.18
    prev_count = len(p.inbox)
    portfolio_news.generate(p, m)
    assert len(p.inbox) > prev_count
    assert any("envolée" in msg["subject"] for msg in p.inbox[prev_count:])


def test_no_news_when_no_positions():
    """Sans positions, le module ne génère pas de messages."""
    p, m = _make_player_and_market(steps=10)
    portfolio_news.generate(p, m)
    assert len(p.inbox) == 0


def test_cooldown_limits_spam():
    """Deux appels consécutifs avec le même événement ne spamment pas."""
    p, m = _make_player_and_market(steps=10)
    tk = "MVC"
    pf.buy(p, m, tk, 100)
    i = m.ticker_idx[tk]
    m.prev_price = m.price.copy()
    m.price[i] *= 1.20
    m.last_ret = [0.0] * m.n
    m.last_ret[i] = 0.18
    portfolio_news.generate(p, m)
    count1 = len(p.inbox)
    portfolio_news.generate(p, m)
    count2 = len(p.inbox)
    assert count1 == count2
