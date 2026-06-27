"""
market_hours.py — Ouverture des places régionales, modèle **par pas de marché**.

Avec le temps de jeu accéléré (cf. core/sim_clock : 1 min réelle = 1 pas à x1),
un modèle d'horaires « dans la journée » faisait clignoter les sessions toutes
les quelques secondes — injouable. On adopte donc un modèle plus digeste, par
PAS de marché :

  À chaque pas, exactement DEUX des trois sessions (Asie / Europe / Amériques)
  sont OUVERTES et UNE est FERMÉE. La session fermée tourne à chaque pas. Sur un
  cycle de 3 pas, chaque PAIRE de sessions est ouverte simultanément exactement
  une fois — donc chaque place « croise » les deux autres tour à tour :

    pas %3 == 0 : fermé AMÉRIQUES   → ouverts ASIE + EUROPE
    pas %3 == 1 : fermé ASIE        → ouverts EUROPE + AMÉRIQUES
    pas %3 == 2 : fermé EUROPE      → ouverts AMÉRIQUES + ASIE

Une session reste donc ouverte tout un pas (~60 s à x1 / ~20 s à x3) puis se
ferme un seul pas avant de rouvrir : on a toujours le temps de trader, et une
place fermée rouvre toujours au pas suivant. Réalisme volontairement sacrifié
au profit de la jouabilité.
"""
MINUTES_PER_DAY = 24 * 60

SESSIONS = ("ASIA", "EUROPE", "AMERICAS")

# Les 7 continents jouables (cf. config.CONTINENTS) regroupés sur la session de
# cotation la plus proche géographiquement.
REGION_SESSION = {
    "Asia": "ASIA",
    "Océanie": "ASIA",
    "Europe": "EUROPE",
    "Afrique": "EUROPE",
    "USA": "AMERICAS",
    "Am.Nord": "AMERICAS",
    "Am.Sud": "AMERICAS",
}

SESSION_LABEL = {
    "ASIA": "Asie",
    "EUROPE": "Europe",
    "AMERICAS": "Amériques",
}
SESSION_LABEL_EN = {
    "ASIA": "Asia",
    "EUROPE": "Europe",
    "AMERICAS": "Americas",
}

# Session fermée selon le pas (rotation). L'ordre garantit que chaque paire de
# sessions est ouverte simultanément une fois par cycle de 3 pas.
_CLOSED_BY_STEP = ("AMERICAS", "ASIA", "EUROPE")


def session_for_region(region):
    return REGION_SESSION.get(region, "AMERICAS")


def closed_session(step):
    """Session fermée au pas `step`."""
    return _CLOSED_BY_STEP[int(step) % len(_CLOSED_BY_STEP)]


def is_session_open(session, step):
    """Une session est ouverte tant qu'elle n'est pas la session fermée du pas."""
    return session != closed_session(step)


def is_region_open(region, step):
    return is_session_open(session_for_region(region), step)


def open_sessions(step):
    return tuple(s for s in SESSIONS if is_session_open(s, step))


def steps_until_reopen(region, step):
    """Nombre de pas avant réouverture (0 si déjà ouvert). Une place fermée
    rouvre toujours au pas suivant -> 1."""
    return 0 if is_region_open(region, step) else 1


def session_labels(lang="fr"):
    return SESSION_LABEL_EN if lang == "en" else SESSION_LABEL


def region_status_label(region, step, lang="fr"):
    """Texte court pour l'UI : « Europe ouvert » / « Asie fermé, réouvre au
    prochain pas »."""
    session = session_for_region(region)
    name = session_labels(lang).get(session, session)
    if is_region_open(region, step):
        return f"{name} {'open' if lang == 'en' else 'ouvert'}"
    return (f"{name} closed, reopens next step" if lang == "en"
            else f"{name} fermé, réouvre au prochain pas")


def fmt_hhmm(minute_of_day):
    """Affichage de l'heure de jeu (le bandeau du terminal garde une horloge
    HH:MM purement cosmétique, indépendante des sessions par pas)."""
    minute_of_day = int(minute_of_day) % MINUTES_PER_DAY
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"
