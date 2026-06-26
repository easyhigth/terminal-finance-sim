"""
tests/test_company_scene.py — Visite chaque onglet de la fenêtre société
(scene_company.py), pour attraper les régressions de rendu spécifiques à un
onglet que le test de fumée générique (qui ne visite que l'onglet par défaut)
ne verrait pas.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

import main
from scenes.scene_company import _CHART_KINDS, _TABS


@pytest.fixture(scope="module")
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    p.heat = 10
    yield a


@pytest.mark.parametrize("tab_id,_label", _TABS)
def test_company_tab_renders(app, tab_id, _label):
    tk = app.market.companies[0]["ticker"]
    app.scenes.go("company", ticker=tk)
    scene = app.scenes.current
    scene.tab = tab_id
    scene.update(0.016)
    scene.draw(app.screen)
    scene.update(0.016)
    scene.draw(app.screen)


@pytest.mark.parametrize("kind,_label", _CHART_KINDS)
def test_company_chart_kinds_render(app, kind, _label):
    tk = app.market.companies[0]["ticker"]
    app.scenes.go("company", ticker=tk)
    scene = app.scenes.current
    scene.tab = "chart"
    scene.chart_kind = kind
    scene.update(0.016)
    scene.draw(app.screen)


def test_company_unknown_ticker_shows_error(app):
    app.scenes.go("company", ticker="ZZZZ_NOPE")
    scene = app.scenes.current
    scene.update(0.016)
    scene.draw(app.screen)
    assert scene.metrics is None
    assert scene.search == "ZZZZ_NOPE"


def test_company_no_ticker_opens_picker_with_top_companies(app):
    """Arriver sans ticker (depuis PLUS) doit afficher le sélecteur de
    recherche plutôt qu'un simple panneau d'erreur, pré-rempli avec les plus
    grandes capitalisations."""
    app.scenes.go("company")
    scene = app.scenes.current
    assert scene.metrics is None
    assert scene.search == ""
    items = scene._picker_items()
    assert len(items) > 0
    scene.update(0.016)
    scene.draw(app.screen)
    assert len(scene._picker_rects) == len(items)


def test_company_picker_search_filters_results(app):
    tk = app.market.companies[5]["ticker"]
    app.scenes.go("company")
    scene = app.scenes.current
    scene.search = tk
    items = scene._picker_items()
    assert any(c["ticker"] == tk for c in items)
    scene.draw(app.screen)


def test_company_picker_select_navigates_to_company(app):
    tk = app.market.companies[3]["ticker"]
    app.scenes.go("company")
    scene = app.scenes.current
    scene._select_company(tk)
    new_scene = app.scenes.current
    assert new_scene.ticker == tk
    assert new_scene.metrics is not None


def test_company_news_tab_filters_by_ticker_or_name(app):
    """Les news ne mentionnant pas le ticker/nom de la société ne doivent pas
    apparaître — vérifie que le filtre substring fonctionne (pas juste qu'il
    ne plante pas)."""
    from core import news as N

    tk = app.market.companies[0]["ticker"]
    name = app.market.companies[0]["name"]
    p = app.gs.player
    p.news_history = []
    N.record(p, [
        N.make("corporate", "good", f"{name} annonce des résultats record."),
        N.make("market", "info", "Un événement totalement sans rapport."),
    ], day=1)

    app.scenes.go("company", ticker=tk)
    items = N.query(p)
    needles = {tk.lower(), (name or "").lower()}
    filtered = [e for e in items if any(nd and nd in e["text"].lower() for nd in needles)]
    assert len(filtered) == 1
    assert "résultats record" in filtered[0]["text"]
