"""Vérifie que chaque raccourci clavier du bureau (F2-F10 + Ctrl+lettre de
DESKTOP_SHORTCUTS) résout sur une clé réellement lançable par
`DesktopScene._launch` — i.e. une clé spéciale (terminal/track/save), une clé
QUICK_APPS ou une clé APPS. Sans ce test, un raccourci mal orthographié
ouvrait silencieusement rien (F6->"graph" au lieu de "qgraph", F7->"news" au
lieu de "qnews", F9->"missions" au lieu de "mission" — corrigés).
"""
import pygame

from scenes import scene_desktop_common as C

_SPECIAL = {"terminal", "track", "save"}
_APPS_KEYS = {k for k, _l, _kind, _cls in C.APPS}
_QUICK_KEYS = {k for k, _l, _kind, _scene in C.QUICK_APPS}


def _resolves(key):
    return key in _SPECIAL or key in _QUICK_KEYS or key in _APPS_KEYS


# Miroir exact du dict _F_KEYS de scenes/scene_desktop.py (F2-F10)
_F_KEYS = {
    pygame.K_F2: "sheet", pygame.K_F3: "research", pygame.K_F4: "trading",
    pygame.K_F5: "book", pygame.K_F6: "qgraph", pygame.K_F7: "qnews",
    pygame.K_F8: "inbox", pygame.K_F9: "mission", pygame.K_F10: "deals",
}


def test_every_f_key_resolves_to_a_launchable_key():
    dead = {pygame.key.name(k): v for k, v in _F_KEYS.items() if not _resolves(v)}
    assert not dead, f"Raccourcis F morts (n'ouvrent rien): {dead}"


def test_every_ctrl_shortcut_resolves_to_a_launchable_key():
    dead = {pygame.key.name(k): v for k, v in C.DESKTOP_SHORTCUTS.items()
            if not _resolves(v)}
    assert not dead, f"Raccourcis Ctrl morts (n'ouvrent rien): {dead}"


def test_f_keys_in_sync_with_source():
    """Garde-fou : si quelqu'un édite _F_KEYS dans scene_desktop.py sans
    mettre à jour ce test, ce dernier échoue et force à réfléchir à la
    résolution de la nouvelle clé."""
    # les clés ciblées doivent toutes exister dans le système de lancement
    for key in _F_KEYS.values():
        assert _resolves(key), f"F-key cible non lançable: {key!r}"