"""
colorblind_settings.py — Mode contraste élevé / daltonien (persisté).

Certaines paires de couleurs du jeu portent un sens binaire fort (hausse/
baisse, favorable/défavorable, critique/opportunité) codé en vert/rouge
classique — peu distinguable pour une part significative des joueurs
daltoniens (deutéranopie/protanopie, la confusion la plus fréquente). Ce
module bascule ces paires vers une alternative bleu/orange, nettement plus
distinguable même en cas de déficience rouge-vert.

Fonctionne SANS toucher aux ~150 sites d'appel qui lisent ces couleurs : tout
le code consomme `config.COL_UP`/`config.COL_DOWN`/... par attribut de module
(`config.COL_UP`, jamais `from core.config import COL_UP`), résolu à chaque
frame — réassigner l'attribut à l'exécution reteint donc tout le jeu
immédiatement. Un seul piège identifié et corrigé : un défaut de paramètre de
fonction (`def f(color=config.COL_DOWN)`) se FIGE à la définition, pas à
l'appel — `ui/widgets.py::draw_error_panel` a été corrigé pour résoudre sa
couleur par défaut au moment de l'appel (`title_color=None` puis résolution
dans le corps).

Étendu au-delà de la seule paire hausse/baisse à deux autres familles où la
distinguabilité pose problème en daltonisme rouge-vert : (1) l'échelle de
priorité à 3 niveaux (critique/urgent/bonus, cf. `core/todo.py` et les cartes
de dilemme) — `COL_PRIO_URGENT` et `COL_WARN` basculent vers un jaune
intermédiaire, pour rester une 3ᵉ teinte distincte des deux extrêmes
critique/bonus plutôt qu'un simple mélange des deux ; (2) les 7 couleurs de
continent de la carte du monde (`ui/worldmap.py`), remplacées par la palette
catégorielle Okabe-Ito — conçue spécifiquement pour rester distinguable en
protanopie/deutéranopie/tritanopie, alors que la palette d'origine confondait
par exemple Asie (orange-rouge) et « urgent »/« baisse » (rouge).

Persisté séparément (`colorblind_settings.json` sous `config.SAVE_DIR`),
comme `core/anim_settings.py`/`core/audio.py`. Appliqué une fois à l'import de
ce module (donc dès que `main.py` l'importe, avant toute scène ne dessine) et
à chaque bascule depuis les Réglages (`scenes/scene_settings.py`).
"""
import json
import os

from core import config

_PATH = os.path.join(config.SAVE_DIR, "colorblind_settings.json")

_ENABLED = False

# palette d'origine (capturée à l'import, avant toute mutation) — permet de
# revenir en arrière proprement quand le mode est désactivé.
_DEFAULTS = {
    "COL_UP": config.COL_UP,
    "COL_DOWN": config.COL_DOWN,
    "COL_EVENT_GOOD": config.COL_EVENT_GOOD,
    "COL_EVENT_BAD": config.COL_EVENT_BAD,
    "COL_PRIO_BONUS": config.COL_PRIO_BONUS,
    "COL_PRIO_CRITICAL": config.COL_PRIO_CRITICAL,
    "COL_PRIO_URGENT": config.COL_PRIO_URGENT,
    "COL_WARN": config.COL_WARN,
    "COL_EUROPE": config.COL_EUROPE,
    "COL_USA": config.COL_USA,
    "COL_ASIA": config.COL_ASIA,
    "COL_NORTHAM": config.COL_NORTHAM,
    "COL_SOUTHAM": config.COL_SOUTHAM,
    "COL_AFRICA": config.COL_AFRICA,
    "COL_OCEANIA": config.COL_OCEANIA,
}
_CB_UP = (64, 156, 255)      # bleu vif : équivalent "hausse / favorable"
_CB_DOWN = (255, 149, 0)     # orange vif : équivalent "baisse / défavorable"
_CB_WARN = (240, 228, 66)    # jaune : 3ᵉ teinte pour "urgent / attention",
                              # distincte des deux extrêmes critique/bonus
_ALT = {
    "COL_UP": _CB_UP,
    "COL_DOWN": _CB_DOWN,
    "COL_EVENT_GOOD": _CB_UP,
    "COL_EVENT_BAD": _CB_DOWN,
    "COL_PRIO_BONUS": _CB_UP,
    "COL_PRIO_CRITICAL": _CB_DOWN,
    "COL_PRIO_URGENT": _CB_WARN,
    "COL_WARN": _CB_WARN,
    # palette catégorielle Okabe-Ito (colorblind-safe) pour les 7 continents
    "COL_EUROPE":  (0, 114, 178),    # bleu
    "COL_USA":     (0, 158, 115),    # vert bleuté
    "COL_ASIA":    (213, 94, 0),     # vermillon
    "COL_NORTHAM": (86, 180, 233),   # bleu ciel
    "COL_SOUTHAM": (240, 228, 66),   # jaune
    "COL_AFRICA":  (230, 159, 0),    # orange
    "COL_OCEANIA": (204, 121, 167),  # pourpre rougeâtre
}


def _load():
    global _ENABLED
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            _ENABLED = bool(json.load(f).get("enabled", False))
    except Exception:
        _ENABLED = False


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"enabled": _ENABLED}, f)
    except Exception:
        pass    # jamais bloquant (disque en lecture seule, CI…)


def is_enabled():
    return _ENABLED


def apply():
    """(Ré)applique la palette courante (alternative ou d'origine) à
    core.config — à appeler après tout changement d'état."""
    table = _ALT if _ENABLED else _DEFAULTS
    for name, value in table.items():
        setattr(config, name, value)


def set_enabled(value):
    global _ENABLED
    _ENABLED = bool(value)
    _save()
    apply()


def toggle():
    set_enabled(not _ENABLED)
    return _ENABLED


_load()
apply()
