"""Tests des apps Desk Crédit (Merton/Waterfall) et Labo de crise + les
extensions du Desk Taux (onglet FUTURES, rotation DV01)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import bonds as B
from core import portfolio as pf

pygame.font.init()

RECT = pygame.Rect(0, 0, 1080, 640)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    for _ in range(60):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def _open(app, key):
    desk = app.scenes.current
    return desk, desk._open_scene_window(key)


# ============================================================== Desk Crédit
def test_creditdesk_merton_scanner_and_fiche(app):
    desk, w = _open(app, "creditdesk")
    cd = w.app_obj
    cd.draw(app.screen, RECT)
    assert len(cd._scan) >= 5
    assert cd.ticker == cd._scan[0]["ticker"]         # le plus risqué présélectionné
    assert cd._fiche is not None and cd._curve
    # cliquer une autre société du scanner recharge la fiche
    other = cd._scan[1]["ticker"]
    cd.handle_event(_click(cd._scan_rects[other].center), RECT)
    cd.draw(app.screen, RECT)
    assert cd.ticker == other and cd._fiche["ticker"] == other


def test_creditdesk_waterfall_slider_moves_losses(app):
    desk, w = _open(app, "creditdesk")
    cd = w.app_obj
    cd.tab = "waterfall"
    cd.draw(app.screen, RECT)
    assert cd._slider_rect is not None
    # cliquer au bout de la jauge → perte de pool ≈ 100 %
    cd.handle_event(_click((cd._slider_rect.right - 1, cd._slider_rect.centery)),
                    RECT)
    assert cd.pool_loss > 0.95
    cd.draw(app.screen, RECT)                         # toutes tranches touchées : ok
    # début de jauge → 0 %
    cd.handle_event(_click((cd._slider_rect.x + 1, cd._slider_rect.centery)), RECT)
    assert cd.pool_loss < 0.05


# ============================================================ Labo de crise
def test_crisislab_sliders_and_crunch_toggle(app):
    for c in app.market.top_companies(n=3):
        pf.buy(app.gs.player, app.market, c["ticker"], 60)
    desk, w = _open(app, "crisislab")
    cl = w.app_obj
    cl.draw(app.screen, RECT)
    assert cl._res is not None and cl._res["total"] < 0
    total_normal = cl._res["total"]
    cl.handle_event(_click(cl._crunch_rect.center), RECT)
    cl.draw(app.screen, RECT)
    assert cl.crunch is True
    assert cl._res["total"] <= total_normal + 1e-6    # corrélations → 1 : pire
    # glisser le curseur actions à fond à gauche → choc −40 %
    cl.handle_event(_click((cl._eq_rect.x + 1, cl._eq_rect.centery)), RECT)
    assert cl.eq_shock == pytest.approx(-0.40, abs=0.02)


def test_crisislab_empty_book_message(app):
    desk, w = _open(app, "crisislab")
    w.app_obj.draw(app.screen, RECT)                  # pas de crash book vide
    assert not w.app_obj._res["lines"]


# ========================================================== Desk Taux (ext)
def test_rates_futures_tab_draws_curves(app):
    desk, w = _open(app, "rates")
    ra = w.app_obj
    ra.tab = "futures"
    ra.draw(app.screen, RECT)                         # grilles contango : ok


def test_rates_rotation_button_rotates_the_book(app):
    p = app.gs.player
    quotes = sorted(B.sovereign_quotes(app.market), key=lambda q: q["years"])
    assert B.buy_bond(p, app.market, quotes[-1]["id"], 40)["ok"]
    desk, w = _open(app, "rates")
    ra = w.app_obj
    ra.draw(app.screen, RECT)
    assert ra._shorten_btn is not None
    ra.handle_event(_click(ra._shorten_btn.center), RECT)
    assert quotes[0]["id"] in p.bonds                 # la jambe courte est entrée
    assert "Rotation" in ra.msg


def test_new_desk_icons_gating(app):
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert {"creditdesk", "crisislab"} <= keys
    app.gs.player.grade_index = 0
    keys0 = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "creditdesk" not in keys0                  # credit : grade 6
    assert "crisislab" in keys0                       # libre dès le début
