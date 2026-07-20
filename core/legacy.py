"""
legacy.py — Objectifs de légende (logique pure, sans pygame).

Au-delà des objectifs trimestriels (`core.career`, court terme) et des badges
(`core.badges`, jalons ponctuels), ces 5 objectifs incarnent des AMBITIONS DE
CARRIÈRE qui se construisent sur la durée et donnent un sens à la partie :
  - dominer durablement le classement des rivaux (pas un instant, une PÉRIODE) ;
  - survivre à une crise de marché MAJEURE (severity élevée, pas n'importe laquelle) ;
  - bâtir un track record (croissance soutenue de la valeur nette) ;
  - décrocher un mandat transformant (cf. core.mandates, capital hors-norme) ;
  - rester performant SANS sacrifier son intégrité (réputation haute, scrutin
    bas ET valeur nette significative, tenus ensemble sur la durée).

`on_quarter_close(player, market)` met à jour les compteurs de série (streaks)
à chaque changement de trimestre — à appeler juste après `career.close_quarter`.
`check_new(player, market)` attribue les objectifs nouvellement atteints et les
retourne pour affichage (toast + journal), sur le même modèle que `core.badges`.
Stockés dans player.legacy (liste d'ids).
"""

def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


RANK_STREAK_TARGET = 4        # trimestres consécutifs en tête du classement
PROFIT_STREAK_TARGET = 6      # trimestres consécutifs de valeur nette croissante
INTEGRITY_STREAK_TARGET = 4   # trimestres consécutifs intègre ET performant
INTEGRITY_MIN_REP = 85
INTEGRITY_MAX_HEAT = 10
INTEGRITY_NW_BASE = 200_000   # seuil de "performant", mis à l'échelle du grade


def _net_worth(player, market):
    try:
        from core import portfolio
        return portfolio.net_worth(player, market)
    except Exception:
        return player.cash


def _performant_threshold(player):
    return INTEGRITY_NW_BASE * (1 + player.grade_index)


GOALS = [
    {
        "id": "desk_no1", "name": ("Numéro 1 du desk", "Desk #1"),
        "desc": (f"Dominer le classement des rivaux {RANK_STREAK_TARGET} trimestres de suite.",
                 f"Dominate the rivals leaderboard for {RANK_STREAK_TARGET} quarters in a row."),
        "progress": lambda p, m: (p.flags.get("top_rank_streak", 0), RANK_STREAK_TARGET),
        "test": lambda p, m: p.flags.get("top_rank_streak", 0) >= RANK_STREAK_TARGET,
    },
    {
        "id": "major_crisis_survivor", "name": ("Rescapé d'une crise majeure", "Major crisis survivor"),
        "desc": ("Traverser une crise de marché sévère sans que la firme ne coule.",
                 "Weather a severe market crisis without the firm going under."),
        "progress": lambda p, m: (min(1, p.flags.get("major_crises", 0)), 1),
        "test": lambda p, m: p.flags.get("major_crises", 0) >= 1,
    },
    {
        "id": "track_record", "name": ("Track record", "Track record"),
        "desc": (f"Faire croître votre valeur nette {PROFIT_STREAK_TARGET} trimestres de suite.",
                 f"Grow your net worth for {PROFIT_STREAK_TARGET} quarters in a row."),
        "progress": lambda p, m: (p.flags.get("profit_streak", 0), PROFIT_STREAK_TARGET),
        "test": lambda p, m: p.flags.get("profit_streak", 0) >= PROFIT_STREAK_TARGET,
    },
    {
        "id": "transformant_mandate", "name": ("Mandat transformant", "Transformative mandate"),
        "desc": ("Remporter un mandat client hors-norme, capable de transformer la firme.",
                 "Win an extraordinary client mandate capable of transforming the firm."),
        "progress": lambda p, m: (min(1, p.flags.get("mandates_transformant_won", 0)), 1),
        "test": lambda p, m: p.flags.get("mandates_transformant_won", 0) >= 1,
    },
    {
        "id": "integrity_performant", "name": ("Intégrité et performance", "Integrity and performance"),
        "desc": ((f"Tenir réputation ≥ {INTEGRITY_MIN_REP}, scrutin ≤ {INTEGRITY_MAX_HEAT} ET "
                  f"valeur nette élevée, {INTEGRITY_STREAK_TARGET} trimestres de suite."),
                 (f"Maintain reputation ≥ {INTEGRITY_MIN_REP}, scrutiny ≤ {INTEGRITY_MAX_HEAT} AND "
                  f"high net worth, for {INTEGRITY_STREAK_TARGET} quarters in a row.")),
        "progress": lambda p, m: (p.flags.get("integrity_streak", 0), INTEGRITY_STREAK_TARGET),
        "test": lambda p, m: p.flags.get("integrity_streak", 0) >= INTEGRITY_STREAK_TARGET,
    },
]

_BY_ID = {g["id"]: g for g in GOALS}


def goal_name(goal):
    return _L(*goal["name"])


def goal_desc(goal):
    return _L(*goal["desc"])


def on_quarter_close(player, market):
    """Met à jour les compteurs de série au changement de trimestre. À appeler
    une fois par trimestre écoulé (juste après `career.close_quarter`)."""
    # classement : série de trimestres consécutifs en tête
    if player.rivals:
        try:
            from core import rivals
            rank, _ = rivals.player_rank(player, market)
        except Exception:
            rank = 0
        if rank == 1:
            player.flags["top_rank_streak"] = player.flags.get("top_rank_streak", 0) + 1
        else:
            player.flags["top_rank_streak"] = 0

    # track record : valeur nette en croissance trimestre après trimestre
    nw = _net_worth(player, market)
    last_nw = player.flags.get("legacy_last_nw")
    if last_nw is not None:
        if nw > last_nw:
            player.flags["profit_streak"] = player.flags.get("profit_streak", 0) + 1
            player.flags["loss_streak"] = 0
        elif nw < last_nw:
            player.flags["loss_streak"] = player.flags.get("loss_streak", 0) + 1
            player.flags["profit_streak"] = 0
        else:
            player.flags["profit_streak"] = 0
            player.flags["loss_streak"] = 0
    player.flags["legacy_last_nw"] = nw

    # intégrité tenue ET performance maintenue, ensemble, sur la durée
    if (player.reputation >= INTEGRITY_MIN_REP and player.heat <= INTEGRITY_MAX_HEAT
            and nw >= _performant_threshold(player)):
        player.flags["integrity_streak"] = player.flags.get("integrity_streak", 0) + 1
    else:
        player.flags["integrity_streak"] = 0


def check_new(player, market):
    """Attribue les objectifs de légende nouvellement atteints. Retourne la
    liste des objectifs gagnés (pour toast + journal)."""
    earned = []
    for g in GOALS:
        if g["id"] in player.legacy:
            continue
        try:
            ok = g["test"](player, market)
        except Exception:
            ok = False
        if ok:
            player.legacy.append(g["id"])
            earned.append(g)
    return earned


def get(goal_id):
    return _BY_ID.get(goal_id)


def all_goals():
    return GOALS
