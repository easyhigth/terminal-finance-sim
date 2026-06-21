import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from ui import keynav


def _rect(x, y, w=40, h=20):
    return pygame.Rect(x, y, w, h)


def _key_event(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)


# ---------------------------------------------------------------------------
# nearest_in_direction
# ---------------------------------------------------------------------------

def test_nearest_in_direction_picks_closest_aligned_neighbor():
    rects = {
        "a": _rect(0, 0),
        "b": _rect(0, 100),    # directement en dessous de a
        "c": _rect(200, 100),  # plus loin, désaligné
    }
    assert keynav.nearest_in_direction(rects, "a", "down") == "b"
    assert keynav.nearest_in_direction(rects, "b", "up") == "a"


def test_nearest_in_direction_penalizes_perpendicular_offset():
    rects = {
        "a": _rect(0, 0),
        "b": _rect(300, 20),   # même ligne à peu près, très désaligné horizontalement
        "c": _rect(10, 120),   # un peu plus bas mais quasi aligné verticalement
    }
    # "down" depuis a : c est plus pertinent que b malgré une distance brute
    # comparable, car bien mieux aligné sur l'axe perpendiculaire.
    assert keynav.nearest_in_direction(rects, "a", "down") == "c"


def test_nearest_in_direction_no_candidate_returns_current():
    rects = {"a": _rect(0, 0), "b": _rect(0, -100)}  # b est au-dessus de a
    assert keynav.nearest_in_direction(rects, "a", "down") == "a"


def test_nearest_in_direction_unknown_current_returns_current():
    rects = {"a": _rect(0, 0)}
    assert keynav.nearest_in_direction(rects, "missing", "down") == "missing"


def test_nearest_in_direction_empty_rects():
    assert keynav.nearest_in_direction({}, "a", "down") == "a"


def test_nearest_in_direction_left_right():
    rects = {"a": _rect(0, 0), "b": _rect(100, 0), "c": _rect(-100, 0)}
    assert keynav.nearest_in_direction(rects, "a", "right") == "b"
    assert keynav.nearest_in_direction(rects, "a", "left") == "c"


# ---------------------------------------------------------------------------
# grid_nav
# ---------------------------------------------------------------------------

def test_grid_nav_ignores_non_keydown_events():
    rects = {0: _rect(0, 0)}
    ev = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0))
    cur, activate = keynav.grid_nav(ev, rects, 0)
    assert (cur, activate) == (0, False)


def test_grid_nav_empty_rects_noop():
    ev = _key_event(pygame.K_DOWN)
    cur, activate = keynav.grid_nav(ev, {}, 0)
    assert (cur, activate) == (0, False)


def test_grid_nav_invalid_current_resets_to_first():
    rects = {0: _rect(0, 0), 1: _rect(0, 100)}
    ev = _key_event(pygame.K_DOWN)
    cur, activate = keynav.grid_nav(ev, rects, 99)
    assert cur == 1
    assert activate is False


def test_grid_nav_arrow_moves_without_activating():
    rects = {0: _rect(0, 0), 1: _rect(0, 100)}
    ev = _key_event(pygame.K_DOWN)
    cur, activate = keynav.grid_nav(ev, rects, 0)
    assert cur == 1
    assert activate is False


def test_grid_nav_enter_activates_without_moving():
    rects = {0: _rect(0, 0), 1: _rect(0, 100)}
    for key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        ev = _key_event(key)
        cur, activate = keynav.grid_nav(ev, rects, 0)
        assert (cur, activate) == (0, True)


def test_grid_nav_accepts_list_of_rects():
    rects = [_rect(0, 0), _rect(0, 100)]
    ev = _key_event(pygame.K_DOWN)
    cur, activate = keynav.grid_nav(ev, rects, 0)
    assert cur == 1
    assert activate is False


def test_grid_nav_other_key_noop():
    rects = {0: _rect(0, 0)}
    ev = _key_event(pygame.K_a)
    cur, activate = keynav.grid_nav(ev, rects, 0)
    assert (cur, activate) == (0, False)


# ---------------------------------------------------------------------------
# draw_focus_ring
# ---------------------------------------------------------------------------

def test_draw_focus_ring_noop_when_not_focused():
    surf = pygame.Surface((100, 100))
    before = pygame.image.tostring(surf, "RGB")
    keynav.draw_focus_ring(surf, _rect(10, 10), False)
    after = pygame.image.tostring(surf, "RGB")
    assert before == after


def test_draw_focus_ring_draws_when_focused():
    surf = pygame.Surface((100, 100))
    before = pygame.image.tostring(surf, "RGB")
    keynav.draw_focus_ring(surf, _rect(10, 10), True)
    after = pygame.image.tostring(surf, "RGB")
    assert before != after


# ---------------------------------------------------------------------------
# ZoneStack
# ---------------------------------------------------------------------------

def test_zonestack_starts_at_first_zone_outside():
    zs = keynav.ZoneStack(["a", "b", "c"])
    assert zs.zone == "a"
    assert zs.inside is False
    assert zs.item is None


def test_zonestack_empty_order():
    zs = keynav.ZoneStack([])
    assert zs.zone is None
    zs.cycle_zone()  # ne doit pas lever d'exception
    assert zs.zone is None


def test_zonestack_cycle_zone_wraps_around():
    zs = keynav.ZoneStack(["a", "b", "c"])
    zs.cycle_zone(1)
    assert zs.zone == "b"
    zs.cycle_zone(1)
    assert zs.zone == "c"
    zs.cycle_zone(1)
    assert zs.zone == "a"
    zs.cycle_zone(-1)
    assert zs.zone == "c"


def test_zonestack_cycle_zone_resets_inside_state():
    zs = keynav.ZoneStack(["a", "b"])
    zs.enter()
    zs.item = "x"
    zs.cycle_zone(1)
    assert zs.inside is False
    assert zs.item is None
    assert zs.zone == "b"


def test_zonestack_enter_sets_inside_and_clears_item():
    zs = keynav.ZoneStack(["a"])
    zs.item = "stale"
    zs.enter()
    assert zs.inside is True
    assert zs.item is None


def test_zonestack_escape_pops_inside_then_returns_false_at_top():
    zs = keynav.ZoneStack(["a"])
    zs.enter()
    zs.item = "x"
    assert zs.escape() is True
    assert zs.inside is False
    assert zs.item is None
    # déjà au niveau bloc : escape() ne consomme rien, laisse l'appelant gérer
    assert zs.escape() is False


def test_zonestack_move_zone_uses_spatial_nav_and_resets_inside():
    zs = keynav.ZoneStack(["a", "b"])
    zs.enter()
    zs.item = "x"
    rects = {"a": _rect(0, 0), "b": _rect(0, 100)}
    zs.move_zone(rects, "down")
    assert zs.zone == "b"
    assert zs.inside is False
    assert zs.item is None
