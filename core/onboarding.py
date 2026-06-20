"""
onboarding.py — Parcours d'intégration des premiers jours.
Une suite d'étapes courtes (analyser, investir, avancer le temps, travailler,
consulter sa messagerie, poser une alerte) guide le joueur dans le terminal
sans bloquer l'accès au reste du jeu : chaque étape se détecte sur l'état du
joueur (pas sur la commande tapée), donc le joueur reste libre d'explorer
dans le désordre. Affichée en bandeau dans scene_terminal ; ignorable (skip).
"""

# NB : les premières étapes ne portent volontairement que sur des commandes
# toujours accessibles au grade Stagiaire (absentes de core/unlocks.py::CMD_FEATURE,
# ou débloquées dès le grade 0 comme RESEARCH/ALERT — seul BUY/SELL reste
# verrouillé jusqu'au grade Associate) — sans ça, le parcours pourrait rester
# bloqué indéfiniment sur une commande encore inaccessible. Les outils
# d'investissement (trading, mandats...) sont introduits plus tard, à leur
# déblocage (core/unlocks.py::FEATURE_TUTORIAL).
STEPS = [
    {"id": "career", "title": "Découvrir votre feuille de route",
     "hint": "Tapez CAREER pour voir votre progression, vos objectifs du trimestre et votre grade.",
     "check": lambda p: p.flags.get("onboarding_seen_career", False)},
    {"id": "mission", "title": "Réaliser une mission",
     "hint": "Tapez MISSION pour accomplir le travail de votre grade et gagner de la réputation.",
     "check": lambda p: p.missions_done > 0},
    {"id": "advance", "title": "Avancer dans le temps",
     "hint": "Tapez ADV pour faire avancer le marché de 5 jours et voir l'effet sur votre portefeuille.",
     "check": lambda p: p.day > 1},
    {"id": "inbox", "title": "Consulter votre messagerie",
     "hint": "Tapez INBOX pour lire les messages de votre manager, vos clients et la conformité.",
     "check": lambda p: p.flags.get("onboarding_seen_inbox", False)},
    {"id": "eval", "title": "Viser la promotion",
     "hint": "Tapez EVAL pour voir ce qui vous sépare de votre prochaine promotion.",
     "check": lambda p: p.flags.get("onboarding_seen_eval", False)},
]


def active_step(p):
    """Étape courante du parcours, ou None si terminé/désactivé."""
    if getattr(p, "onboarding_done", False):
        return None
    idx = getattr(p, "onboarding_step", 0)
    if idx >= len(STEPS):
        return None
    return STEPS[idx]


def progress(p, app=None):
    """Vérifie si l'étape courante vient d'être complétée ; si oui, avance le
    parcours, récompense (+2 réputation) et notifie. Retourne l'étape franchie,
    ou None si rien n'a changé."""
    step = active_step(p)
    if step is None or not step["check"](p):
        return None
    p.onboarding_step = getattr(p, "onboarding_step", 0) + 1
    p.adjust_reputation(2, reason=f"Intégration : {step['title']}")
    finished = p.onboarding_step >= len(STEPS)
    if finished:
        p.onboarding_done = True
    if app is not None:
        app.notify(f"✓ {step['title']} (+2 réputation)", "good")
        if finished:
            app.notify("🎓 Parcours d'intégration terminé — vous connaissez l'essentiel.", "prestige")
    return step


def skip(p):
    p.onboarding_done = True
