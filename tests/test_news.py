"""Tests du fil d'actualités persistant (core/news.py) et des deals souverains."""
from core import news
from core import deals
from core.game_state import PlayerState


def _p():
    return PlayerState()


def test_record_and_query():
    p = _p()
    news.record(p, [news.make("market", "good", "Marché en hausse"),
                    news.make("political", "bad", "Crise budgétaire", region="Europe")], day=10)
    assert len(p.news_history) == 2
    assert news.query(p)[0]["text"] == "Crise budgétaire"     # plus récent en premier ? même jour : ordre d'insertion inversé
    assert len(news.query(p, cat="market")) == 1
    assert len(news.query(p, region="Europe")) == 1
    assert len(news.query(p, kind="bad")) == 1


def test_three_year_purge():
    p = _p()
    news.record(p, [news.make("market", "info", "vieille news")], day=1)
    news.record(p, [news.make("market", "info", "news récente")], day=1 + news.MAX_AGE_DAYS + 50)
    texts = [e["text"] for e in p.news_history]
    assert "vieille news" not in texts    # purgée (plus de 3 ans)
    assert "news récente" in texts


def test_history_size_capped():
    p = _p()
    for d in range(news.MAX_HISTORY + 200):
        news.record(p, [news.make("market", "info", f"n{d}")], day=10 + d)
    assert len(p.news_history) <= news.MAX_HISTORY


def test_categorize_market():
    assert news.categorize_market({"text": "Résultats : MVC dépasse les attentes (+8%)"}) == "corporate"
    assert news.categorize_market({"text": "Bascule de régime : Récession"}) == "macro"
    assert news.categorize_market({"text": "Secteur Tech en forte hausse"}) == "market"


def test_for_day():
    p = _p()
    news.record(p, [news.make("market", "good", "jour 5")], day=5)
    news.record(p, [news.make("market", "good", "jour 6")], day=6)
    assert [e["text"] for e in news.for_day(p, 5)] == ["jour 5"]


def test_government_deal_generation():
    p = _p()
    p.grade_index = 6           # VP : éligible
    p.cash = 1_000_000
    event = {"kind": "bad", "country": "États-Unis", "country_en": "United States",
             "region": "USA", "gov": "US"}
    # force la génération (proba) via un RNG déterministe favorable
    import random
    created = None
    for seed in range(50):
        d = deals.maybe_government_deal(p, event, random.Random(seed))
        if d:
            created = d
            break
    assert created is not None
    assert created["gov"] == "États-Unis"
    assert created["region"] == "USA"
    assert created in p.deals
    assert created["kind"] == "Risk"     # 'bad' → restructuration de dette


def test_government_deal_requires_grade():
    p = _p()
    p.grade_index = 0            # Trainee : pas de deals souverains
    event = {"kind": "good", "country": "France", "region": "Europe"}
    import random
    assert all(deals.maybe_government_deal(p, event, random.Random(s)) is None for s in range(20))
