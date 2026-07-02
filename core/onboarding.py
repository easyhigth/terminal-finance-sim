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
def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


STEPS = [
    {"id": "career", "title": ("Découvrir votre feuille de route", "Discover your roadmap"),
     "hint": ("Tapez CAREER pour voir votre progression, vos objectifs du trimestre et votre grade.",
              "Type CAREER to see your progress, quarterly goals and grade."),
     "check": lambda p: p.flags.get("onboarding_seen_career", False)},
    {"id": "mission", "title": ("Réaliser une mission", "Complete a mission"),
     "hint": ("Tapez MISSION pour accomplir le travail de votre grade et gagner de la réputation.",
              "Type MISSION to do your grade's work and earn reputation."),
     "check": lambda p: p.missions_done > 0},
    {"id": "advance", "title": ("Laisser le temps s'écouler", "Let time flow"),
     "hint": ("Le temps avance tout seul : reprenez ▶ (ou Espace) en haut à droite et laissez le marché vivre.",
              "Time flows on its own: resume ▶ (or Space) top-right and let the market move."),
     "check": lambda p: p.day > 1},
    {"id": "inbox", "title": ("Consulter votre messagerie", "Check your inbox"),
     "hint": ("Tapez INBOX pour lire les messages de votre manager, vos clients et la conformité.",
              "Type INBOX to read messages from your manager, clients and compliance."),
     "check": lambda p: p.flags.get("onboarding_seen_inbox", False)},
    {"id": "eval", "title": ("Viser la promotion", "Aim for promotion"),
     "hint": ("Tapez EVAL pour voir ce qui vous sépare de votre prochaine promotion.",
              "Type EVAL to see what stands between you and your next promotion."),
     "check": lambda p: p.flags.get("onboarding_seen_eval", False)},
]


def step_title(step):
    return _L(*step["title"])


def step_hint(step):
    return _L(*step["hint"])


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
    title = step_title(step)
    p.adjust_reputation(2, reason=_L(f"Intégration : {title}", f"Onboarding: {title}"))
    finished = p.onboarding_step >= len(STEPS)
    if finished:
        p.onboarding_done = True
    if app is not None:
        app.notify(_L(f"✓ {title} (+2 réputation)", f"✓ {title} (+2 reputation)"), "good")
        if finished:
            app.notify(_L("🎓 Parcours d'intégration terminé — vous connaissez l'essentiel.",
                          "🎓 Onboarding complete — you know the essentials."), "prestige")
    return step


def skip(p):
    p.onboarding_done = True
