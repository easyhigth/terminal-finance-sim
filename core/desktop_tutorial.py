"""
desktop_tutorial.py — Tutoriel INTERACTIF de prise en main du bureau.

Complète la carte d'accueil statique (`core/desktop_onboarding.py`, un simple
pavé de texte refermé d'un clic) par une vraie séquence guidée : chaque étape
désigne une icône du bureau (surlignée à l'écran) et se valide sur l'ÉTAT réel
du poste de travail (fenêtre ouverte, fenêtre ancrée…), pas sur le clic — le
joueur reste libre d'explorer dans le désordre, comme le parcours du terminal
(`core/onboarding.py`). L'état (étape courante / terminé) est persisté dans un
JSON dédié sous `config.SAVE_DIR`, par machine et non par sauvegarde — on
n'apprend le bureau qu'une fois, pas à chaque nouvelle partie. « Revoir le
tutoriel » (menu contextuel du fond du bureau) remet à zéro.

Logique sans pygame ; les `check` reçoivent la DesktopScene (accès à `wm`).
"""
import json
import os

from core import config

_PATH = os.path.join(config.SAVE_DIR, "desktop_tutorial.json")


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def _win(desktop, key):
    return next((w for w in desktop.wm.windows if w.key == key), None)


def _research_open(desktop):
    return _win(desktop, "research") is not None


def _terminal_visible(desktop):
    w = _win(desktop, "scene:terminal")
    return w is not None and not w.minimized


def _market_open(desktop):
    return _win(desktop, "scene:markethub") is not None


def _window_snapped(desktop):
    return any(w._restore_rect is not None for w in desktop.wm.windows)


def _mission_open(desktop):
    return _win(desktop, "scene:mission") is not None


STEPS = [
    {"id": "research", "target": "research",
     "title": ("Ouvrez l'app Recherche", "Open the Research app"),
     "hint": ("Cliquez sur l'icône « Recherche » : chaque icône ouvre une application dans une FENÊTRE déplaçable.",
              "Click the “Research” icon: every icon opens an application in a draggable WINDOW."),
     "check": _research_open},
    {"id": "terminal", "target": "terminal",
     "title": ("Affichez le Terminal", "Show the Terminal"),
     "hint": ("Ouvrez l'icône « Terminal » : c'est le moteur de la partie — le temps s'y écoule même fenêtre fermée.",
              "Open the “Terminal” icon: it's the game engine — time flows even with its window closed."),
     "check": _terminal_visible},
    {"id": "market", "target": "qmarket",
     "title": ("Consultez le Marché", "Check the Market"),
     "hint": ("Ouvrez « Marché » pour suivre indices, secteurs et devises pendant que le temps passe.",
              "Open “Market” to follow indices, sectors and currencies while time passes."),
     "check": _market_open},
    {"id": "snap", "target": None,
     "title": ("Ancrez une fenêtre", "Snap a window"),
     "hint": ("Glissez une fenêtre vers un bord de l'écran (ou double-cliquez sa barre de titre) pour l'ancrer.",
              "Drag a window to a screen edge (or double-click its title bar) to snap it."),
     "check": _window_snapped},
    {"id": "mission", "target": "qmission",
     "title": ("Faites votre travail", "Do your job"),
     "hint": ("Ouvrez « Mission » : accomplir le travail de votre grade rapporte cash et réputation.",
              "Open “Mission”: doing your grade's work earns cash and reputation."),
     "check": _mission_open},
]


# ------------------------------------------------------------- persistance
def _load():
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return {"step": int(d.get("step", 0)), "done": bool(d.get("done", False))}
    except Exception:
        return {"step": 0, "done": False}


def _save(state):
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass    # jamais bloquant (disque en lecture seule, CI…)


# --------------------------------------------------------------------- API
def done():
    st = _load()
    return st["done"] or st["step"] >= len(STEPS)


def active_step():
    """(index, étape) courante, ou None si terminé/passé."""
    st = _load()
    if st["done"] or st["step"] >= len(STEPS):
        return None
    return st["step"], STEPS[st["step"]]


def advance():
    """Valide l'étape courante ; retourne True si le tutoriel vient de se
    terminer (dernière étape validée)."""
    st = _load()
    st["step"] += 1
    if st["step"] >= len(STEPS):
        st["done"] = True
    _save(st)
    return st["done"]


def skip():
    _save({"step": len(STEPS), "done": True})


def reset():
    _save({"step": 0, "done": False})


def step_title(step):
    return _L(*step["title"])


def step_hint(step):
    return _L(*step["hint"])
