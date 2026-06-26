"""
market_hours.py — Horaires d'ouverture des marchés par région (Round 11 Phase 2).

Trois sessions de cotation (Asie, Europe, Amériques), chacune ouverte du lundi
au vendredi sur une plage horaire fixe exprimée en minutes depuis minuit
« heure de jeu » (0..1439, commune à toute la partie — pas de fuseaux
horaires réels à gérer). Les plages se chevauchent partiellement comme dans
la réalité (Asie/Europe, Europe/Amériques) mais ne sont jamais toutes les
trois ouvertes en même temps. `core.sim_clock.SimClock` fournit le couple
(jour, minute du jour) courant ; ce module ne fait que la calendaristique.
"""
MINUTES_PER_DAY = 24 * 60

# (minute d'ouverture, minute de fermeture) — bornes [open, close).
SESSION_HOURS = {
    "ASIA":     (0 * 60,    8 * 60),         # 00:00–08:00
    "EUROPE":   (7 * 60,    15 * 60 + 30),   # 07:00–15:30
    "AMERICAS": (13 * 60 + 30, 20 * 60),     # 13:30–20:00
}

# Les 7 continents jouables (cf. config.CONTINENTS) regroupés sur la session
# de cotation la plus proche géographiquement.
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


def session_for_region(region):
    return REGION_SESSION.get(region, "AMERICAS")


def is_weekday_open(day):
    """Lundi=jour 1 (convention de jeu) ; marché fermé le week-end."""
    return (day - 1) % 7 < 5


def is_session_open(session, minute_of_day):
    open_m, close_m = SESSION_HOURS[session]
    return open_m <= minute_of_day < close_m


def is_region_open(region, day, minute_of_day):
    session = session_for_region(region)
    return is_weekday_open(day) and is_session_open(session, minute_of_day)


def fmt_hhmm(minute_of_day):
    minute_of_day = int(minute_of_day) % MINUTES_PER_DAY
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def next_open(region, day, minute_of_day):
    """Renvoie (jour, minute) de la prochaine ouverture de `region` à partir
    de (day, minute_of_day) — strictement après l'instant courant si le
    marché est déjà ouvert pile à cet instant n'a pas d'importance ici (on
    n'appelle ceci que quand c'est fermé)."""
    session = session_for_region(region)
    open_m, _close_m = SESSION_HOURS[session]
    d = day
    if minute_of_day < open_m and is_weekday_open(d):
        return d, open_m
    d += 1
    while not is_weekday_open(d):
        d += 1
    return d, open_m


def region_status_label(region, day, minute_of_day, lang="fr"):
    """Texte court pour l'UI : « Europe ouvert » / « Asie fermé, réouverture
    lundi 00:00 »."""
    session = session_for_region(region)
    labels = SESSION_LABEL_EN if lang == "en" else SESSION_LABEL
    name = labels.get(session, session)
    if is_region_open(region, day, minute_of_day):
        return f"{name} {'open' if lang=='en' else 'ouvert'}"
    nd, nm = next_open(region, day, minute_of_day)
    when = "auj." if nd == day else ("dem." if nd == day + 1 else f"j{nd}")
    when_en = "today" if nd == day else ("tomorrow" if nd == day + 1 else f"day {nd}")
    if lang == "en":
        return f"{name} closed, reopens {when_en} {fmt_hhmm(nm)}"
    return f"{name} fermé, réouvre {when} {fmt_hhmm(nm)}"
