"""
game_calendar.py — Calendrier de jeu (logique pure, sans pygame).

Le jeu ne compte que des JOURS (`player.day`, 1 pas de marché =
`config.DAYS_PER_STEP` jours). Pour des axes de graphes lisibles (« mars
2026 » plutôt que « -385j »), on ancre un calendrier fictif : le jour 1 est
le 1er janvier de `BASE_YEAR`, années de 365 jours (pas d'années
bissextiles — la simplicité prime, personne ne comptera les 29 février
d'une simulation). Les jours ≤ 0 (préhistoire de marché, graphes 5A/MAX en
tout début de carrière) tombent naturellement dans les années antérieures.

Échelle adaptative des étiquettes (demande joueur) : minutes → heures →
jours → nom du mois → année, selon l'étendue affichée.
"""

BASE_YEAR = 2025
MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)   # 365 j
_MONTHS_FR = ("janv.", "févr.", "mars", "avril", "mai", "juin",
              "juil.", "août", "sept.", "oct.", "nov.", "déc.")
_MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

MINUTES_PER_DAY = 24 * 60


def _months():
    from core.i18n import get_lang
    return _MONTHS_EN if get_lang() == "en" else _MONTHS_FR


def date_of(day):
    """(année, index de mois 0-11, jour du mois 1-31) pour un jour de jeu.
    Fonctionne aussi pour les jours ≤ 0 (préhistoire) via le modulo Python
    (toujours positif) — le jour 0 est le 31 décembre de BASE_YEAR - 1."""
    d = int(day) - 1
    year = BASE_YEAR + d // 365
    doy = d % 365
    for m, length in enumerate(MONTH_LENGTHS):
        if doy < length:
            return year, m, doy + 1
        doy -= length
    return year, 11, 31   # inatteignable (garde-fou)


def day_label(day):
    """« 12 mars » — pour les étendues de quelques mois."""
    _y, m, dm = date_of(day)
    return f"{dm} {_months()[m]}"


def month_label(day):
    """« mars 2026 » — pour les étendues de quelques mois à ~2 ans."""
    y, m, _dm = date_of(day)
    return f"{_months()[m]} {y}"


def year_label(day):
    """« 2027 » — pour les étendues de plusieurs années."""
    return str(date_of(day)[0])


def axis_label(day, span_days):
    """Étiquette calendaire adaptée à l'étendue affichée `span_days`."""
    if span_days <= 190:
        return day_label(day)
    if span_days <= 750:
        return month_label(day)
    return year_label(day)


def rel_minutes_label(minutes_back):
    """Étiquette RELATIVE pour les fenêtres intraday : minutes jusqu'à 1 h,
    puis heures jusqu'à 48 h, puis jours — « -45min », « -12h », « -7j »."""
    from core.i18n import get_lang
    m = float(minutes_back)
    if m <= 0:
        return "now" if get_lang() == "en" else "maintenant"
    if m < 60:
        return f"-{m:g}min"
    if m < 48 * 60:
        return f"-{m / 60:g}h"
    return f"-{m / MINUTES_PER_DAY:g}{'d' if get_lang() == 'en' else 'j'}"
