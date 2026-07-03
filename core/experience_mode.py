"""
experience_mode.py — Préférence "mode débutant / expert" (simplicité de jeu).

Persistée séparément (fichier JSON dédié sous config.SAVE_DIR, même patron
que core/anim_settings.py). En mode DÉBUTANT (opt-in explicite), le menu
Démarrer et la palette Ctrl+K masquent les pages financières les plus
avancées (produits structurés, titrisation, options, ALM, VaR…) tant
qu'elles ne sont pas pertinentes pour la voie choisie du joueur — moins de
choix à l'écran pour qui découvre le jeu, sans rien retirer ni verrouiller
(un joueur avancé qui a besoin d'un outil masqué n'a qu'à repasser en mode
EXPERT dans les Réglages). Défaut EXPERT : ne change rien pour les parties
déjà en cours ni pour un joueur qui n'a jamais touché ce réglage.
"""
import json
import os

from core import config

MODES = ("expert", "beginner")
_mode = "expert"
_PATH = os.path.join(config.SAVE_DIR, "experience_mode.json")

# Pages jugées « avancées » : concepts financiers pointus ou peu utilisés en
# dehors d'une voie de carrière précise — masquées en mode débutant sauf si
# pertinentes pour la voie courante du joueur (cf. TRACK_RELEVANT).
ADVANCED_SCENES = {
    "structured", "credit", "swaps", "governments", "options", "ipo",
    "risk", "quant", "ma", "hedge", "alm", "team", "stresstest",
    "portfolio", "frontier_lab", "portfolio_unified", "analytics", "performance",
}

# Voie du joueur -> sous-ensemble d'ADVANCED_SCENES qui reste visible même en
# mode débutant (ce sont justement les outils de sa spécialisation).
TRACK_RELEVANT = {
    "M&A": {"ma", "team"},
    "Risk": {"risk", "alm", "hedge", "stresstest"},
    "Quant": {"quant", "options"},
    "Portfolio": {"portfolio", "frontier_lab", "portfolio_unified", "analytics", "performance"},
    "Advisory": set(),
}


def _load():
    global _mode
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            m = json.load(f).get("mode", "expert")
            _mode = m if m in MODES else "expert"
    except Exception:
        _mode = "expert"


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"mode": _mode}, f)
    except Exception:
        pass


def get_mode():
    return _mode


def set_mode(mode):
    global _mode
    if mode in MODES:
        _mode = mode
        _save()


def is_beginner():
    return _mode == "beginner"


def scene_hidden(scene, player):
    """True si `scene` doit être masquée du menu Démarrer/palette : mode
    débutant actif, ET la scène est classée avancée, ET elle n'est pas
    pertinente pour la voie courante du joueur."""
    if _mode != "beginner" or scene not in ADVANCED_SCENES:
        return False
    track = getattr(player, "track", "General")
    relevant = TRACK_RELEVANT.get(track, set())
    return scene not in relevant


_load()
