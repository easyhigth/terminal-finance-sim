"""
scene_host.py — Héberge n'importe quelle scène plein écran EXISTANTE dans une
fenêtre du bureau (refonte UI « Jeu PC », étape 2 : « tout en fenêtres »).

Principe : une scène (`scenes/scene_*.py`) est écrite pour dessiner sur toute la
surface logique (`config.SCREEN_WIDTH x SCREEN_HEIGHT`) en coordonnées absolues.
Plutôt que de la réécrire, on la fait dessiner dans une SURFACE hors-champ à
taille logique pleine, puis on met à l'échelle le résultat dans le rectangle de
la fenêtre. Les évènements souris sont retransformés de l'espace fenêtre vers
l'espace logique, et `pygame.mouse.get_pos` est temporairement redirigé pendant
`update/draw/handle_event` de la scène pour que le survol reste aligné.

La navigation de la scène (`self.app.scenes.go(...)`) est interceptée par un
routeur : au lieu de remplacer la scène courante, elle OUVRE (ou ramène au
premier plan) une autre fenêtre sur le bureau — le comportement attendu d'un
bureau où tout coexiste. On y parvient en passant à la scène une App *proxy*
dont l'attribut `.scenes` est le routeur (le reste est délégué à l'App réelle).
"""
import contextlib

import pygame

from apps.base import DesktopApp
from core import config


class _Router:
    """Imite le sous-ensemble de `SceneManager` utilisé par les scènes, mais
    `go()` ouvre une fenêtre au lieu de changer de scène."""

    def __init__(self, real_scenes, opener, host_name):
        self._real = real_scenes
        self._opener = opener            # callable(name, **kwargs)
        self._host_name = host_name
        self._closer = None              # callable() -> ferme la fenêtre de CETTE scène

    @property
    def scenes(self):
        return self._real.scenes

    @property
    def current(self):
        return self._real.current

    @property
    def current_name(self):
        return self._host_name

    def bind_closer(self, cb):
        self._closer = cb

    def go(self, name, **kwargs):
        self._opener(name, **kwargs)

    def back(self, name, **kwargs):
        """« Retour » (bouton précédent/continuer) : ferme la fenêtre
        hébergeant CETTE scène plutôt que d'en ouvrir une AUTRE pour `name` —
        contrairement à `go()`, qui ouvre toujours une fenêtre supplémentaire
        sans jamais fermer l'appelante (correct pour une navigation
        délibérée, ex. "Acheter" → terminal, mais faux pour un bouton retour :
        avant ce correctif, cliquer « retour » ouvrait/focalisait la fenêtre
        `name` tout en laissant la fenêtre courante ouverte derrière — un
        bureau qui s'encombre et un focus volé de façon inattendue)."""
        if self._closer is not None:
            self._closer()
        else:
            self.go(name, **kwargs)

    def __getattr__(self, k):
        return getattr(self._real, k)


class _ProxyApp:
    """App déléguant tout à l'App réelle, sauf `.scenes` (→ routeur)."""

    def __init__(self, real, router):
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "_router", router)

    @property
    def scenes(self):
        return object.__getattribute__(self, "_router")

    def __getattr__(self, k):
        return getattr(object.__getattribute__(self, "_real"), k)

    def __setattr__(self, k, v):
        setattr(object.__getattribute__(self, "_real"), k, v)


class SceneHostApp(DesktopApp):
    # Proche de la résolution logique (1280x720) pour limiter le facteur de
    # réduction du smoothscale (source de flou visible) — les scènes hébergées
    # couvrent la majorité des écrans du jeu, contrairement aux apps natives.
    default_size = (1180, 620)
    min_size = (420, 300)
    icon_kind = "generic"

    def __init__(self, app, scene_name, title, kwargs=None):
        super().__init__(app)
        self.scene_name = scene_name
        self.title = title
        self._kwargs = dict(kwargs or {})
        self._rect = None
        self._offscreen = None
        self._scaled_surf = None
        self._scaled_size = None
        self._opener_cb = None
        self.router = _Router(app.scenes, self._route_open, scene_name)
        self.proxy = _ProxyApp(app, self.router)
        scene_cls = type(app.scenes.scenes[scene_name])
        self.scene = scene_cls(self.proxy)

    # --- navigation (routée vers l'ouverture de fenêtres) -----------------
    def bind_opener(self, cb):
        self._opener_cb = cb

    def bind_closer(self, cb):
        """cb: callable() qui ferme la fenêtre du BUREAU hébergeant cette
        scène — câblé par DesktopScene._open_scene_window pour que
        `self.app.scenes.back(...)`, appelé DANS la scène hébergée, ferme la
        bonne fenêtre (cf. _Router.back)."""
        self.router.bind_closer(cb)

    def _route_open(self, name, **kwargs):
        if self._opener_cb is not None:
            self._opener_cb(name, **kwargs)

    def on_open(self):
        self.scene.on_enter(**self._kwargs)

    def reenter(self, **kwargs):
        self._kwargs = dict(kwargs) if kwargs else self._kwargs
        self.scene.on_enter(**self._kwargs)

    # --- transformation de coordonnées ------------------------------------
    def _to_logical(self, pos):
        r = self._rect
        if not r or r.w == 0 or r.h == 0:
            return pos
        lx = (pos[0] - r.x) * config.SCREEN_WIDTH / r.w
        ly = (pos[1] - r.y) * config.SCREEN_HEIGHT / r.h
        return (int(lx), int(ly))

    @contextlib.contextmanager
    def _mouse_patch(self):
        orig = pygame.mouse.get_pos
        self_ref = self
        pygame.mouse.get_pos = lambda: self_ref._to_logical(orig())
        try:
            yield
        finally:
            pygame.mouse.get_pos = orig

    # --- cycle -------------------------------------------------------------
    def update(self, dt):
        with self._mouse_patch():
            self.scene.update(dt)

    def draw(self, surf, rect):
        self._rect = rect
        if rect.w < 1 or rect.h < 1:
            # fenêtre dégénérée (ex. rect restauré d'une sauvegarde corrompue,
            # cf. DesktopScene._apply_layout) : smoothscale planterait sur une
            # taille négative/nulle — on ne dessine simplement rien.
            return
        if self._offscreen is None:
            self._offscreen = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        with self._mouse_patch():
            self.scene.draw(self._offscreen)
        # smoothscale est coûteux : on ne rescale que si la taille de la
        # fenêtre a changé ; le contenu logique est quoi qu'il en soit redessiné
        # sur l'offscreen à chaque frame.
        size = (rect.w, rect.h)
        if self._scaled_surf is None or self._scaled_size != size:
            self._scaled_surf = pygame.transform.smoothscale(self._offscreen, size)
            self._scaled_size = size
        surf.blit(self._scaled_surf, rect.topleft)

    def handle_event(self, event, rect):
        self._rect = rect
        ev = event
        if hasattr(event, "pos"):
            d = dict(event.dict)
            d["pos"] = self._to_logical(event.pos)
            ev = pygame.event.Event(event.type, d)
        with self._mouse_patch():
            self.scene.handle_event(ev)
        return True
