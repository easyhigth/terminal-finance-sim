"""
difficulty.py — Presets de difficulté + « Défi du jour » (logique pure).

Trois presets choisis à la création de partie (scene_runsetup), stockés dans
`player.flags["difficulty"]` (persiste au save, défaut "normal" pour les
sauvegardes antérieures) :

  - Détendu  : capital de départ +50 %, salaire +25 %, marge de maintenance
               plus clémente — pour explorer sans pression.
  - Normal   : l'équilibre actuel du jeu, inchangé (tous multiplicateurs à 1).
  - Exigeant : capital -25 %, salaire -20 %, marge de maintenance plus
               stricte — chaque levier compte.

Consommé par `PlayerState.salary_per_step` (salaire) et
`core/portfolio_margin._maint_margin` (marge), sur le même modèle que les
perks de voie/firme. Le capital de départ est ajusté une fois, à la création
(`apply`), APRÈS le scénario de départ (qui fixe le cash de base).

« Défi du jour » : `daily_seed()` dérive une graine de marché de la DATE du
jour — tous les joueurs qui cochent l'option le même jour affrontent
exactement le même marché (le moteur étant reconstruit depuis (seed, pas),
c'est gratuit par construction). Le run est marqué dans
`flags["daily_challenge"]` (date ISO) pour l'affichage.
"""
import datetime


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


DEFAULT = "normal"

PRESETS = [
    {"id": "relaxed",
     "name": ("Détendu", "Relaxed"),
     "desc": ("Capital +50 %, salaire +25 %, marge clémente — pour explorer sans pression.",
              "Capital +50%, salary +25%, lenient margin — explore without pressure."),
     "cash_mult": 1.5, "salary_mult": 1.25, "maint_margin_mult": 0.8},
    {"id": "normal",
     "name": ("Normal", "Normal"),
     "desc": ("L'équilibre de référence du jeu.",
              "The game's reference balance."),
     "cash_mult": 1.0, "salary_mult": 1.0, "maint_margin_mult": 1.0},
    {"id": "demanding",
     "name": ("Exigeant", "Demanding"),
     "desc": ("Capital -25 %, salaire -20 %, marge stricte — chaque levier compte.",
              "Capital -25%, salary -20%, strict margin — every lever counts."),
     "cash_mult": 0.75, "salary_mult": 0.8, "maint_margin_mult": 1.25},
]

_BY_ID = {p["id"]: p for p in PRESETS}


def preset(preset_id):
    return _BY_ID.get(preset_id, _BY_ID[DEFAULT])


def get_id(player):
    return player.flags.get("difficulty", DEFAULT)


def label(p):
    return _L(*p["name"])


def desc(p):
    return _L(*p["desc"])


def salary_mult(player):
    return preset(get_id(player))["salary_mult"]


def maint_margin_mult(player):
    return preset(get_id(player))["maint_margin_mult"]


def apply(player, preset_id):
    """Fixe la difficulté du run et ajuste le capital de départ (une seule
    fois, à la création — après le scénario de départ qui fixe le cash)."""
    p = preset(preset_id)
    player.flags["difficulty"] = p["id"]
    player.cash = round(player.cash * p["cash_mult"], 2)
    return p


def daily_seed(date=None):
    """Graine de marché du jour : identique pour tous les joueurs le même
    jour (défi partagé), déterministe et stable dans la plage int32."""
    d = date or datetime.date.today()
    return (d.year * 10_000 + d.month * 100 + d.day) % 2_000_000_000 + 1


def mark_daily(player, date=None):
    d = date or datetime.date.today()
    player.flags["daily_challenge"] = d.isoformat()
