"""
difficulty.py — Presets de difficulté + « Défi du jour » (logique pure).

Trois presets choisis à la création de partie (scene_runsetup), stockés dans
`player.flags["difficulty"]` (persiste au save, défaut "normal" pour les
sauvegardes antérieures) :

  - Détendu  : capital de départ +50 %, salaire +25 %, marge de maintenance
               plus clémente, crises plus rares/légères, rivaux plus passifs
               — pour explorer sans pression.
  - Normal   : l'équilibre actuel du jeu, inchangé (tous multiplicateurs à 1).
  - Exigeant : capital -25 %, salaire -20 %, marge de maintenance plus
               stricte, crises plus fréquentes/sévères, rivaux plus mordants
               — chaque levier compte.

Consommé par `PlayerState.salary_per_step` (salaire),
`core/portfolio_margin._maint_margin` (marge), `core/scenarios.maybe_trigger`
(crises) et `core/rivals.act` (agressivité des rivaux), sur le même modèle
que les perks de voie/firme. Le capital de départ est ajusté une fois, à la
création (`apply`), APRÈS le scénario de départ (qui fixe le cash de base).

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
     "desc": ("Capital +50 %, salaire +25 %, marge clémente, crises plus rares, rivaux plus passifs.",
              "Capital +50%, salary +25%, lenient margin, rarer crises, more passive rivals."),
     "cash_mult": 1.5, "salary_mult": 1.25, "maint_margin_mult": 0.8,
     "crisis_bad_mult": 0.7, "crisis_sev_mult": 0.9, "rival_aggro_mult": 0.7},
    {"id": "normal",
     "name": ("Normal", "Normal"),
     "desc": ("L'équilibre de référence du jeu.",
              "The game's reference balance."),
     "cash_mult": 1.0, "salary_mult": 1.0, "maint_margin_mult": 1.0,
     "crisis_bad_mult": 1.0, "crisis_sev_mult": 1.0, "rival_aggro_mult": 1.0},
    {"id": "demanding",
     "name": ("Exigeant", "Demanding"),
     "desc": ("Capital -25 %, salaire -20 %, marge stricte, crises plus dures, rivaux plus mordants.",
              "Capital -25%, salary -20%, strict margin, harsher crises, more aggressive rivals."),
     "cash_mult": 0.75, "salary_mult": 0.8, "maint_margin_mult": 1.25,
     "crisis_bad_mult": 1.35, "crisis_sev_mult": 1.15, "rival_aggro_mult": 1.4},
    {"id": "custom",
     "name": ("Personnalisé", "Custom"),
     "desc": ("Réglez chaque paramètre indépendamment.",
              "Tune each parameter independently."),
     "cash_mult": 1.0, "salary_mult": 1.0, "maint_margin_mult": 1.0,
     "crisis_bad_mult": 1.0, "crisis_sev_mult": 1.0, "rival_aggro_mult": 1.0},
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


def apply(player, preset_id):
    """Fixe la difficulté du run et ajuste le capital de départ (une seule
    fois, à la création — après le scénario de départ qui fixe le cash)."""
    p = preset(preset_id)
    player.flags["difficulty"] = p["id"]
    player.cash = round(player.cash * p["cash_mult"], 2)


# ---------------------------------------------------------------------------
# Paramètres personnalisés (difficulté "custom")
# ---------------------------------------------------------------------------
_CUSTOM_KEYS = ["cash_mult", "salary_mult", "maint_margin_mult",
                "crisis_bad_mult", "crisis_sev_mult", "rival_aggro_mult"]


def get_custom_param(player, key):
    """Lit un paramètre personnalisé (ou la valeur du preset par défaut)."""
    if get_id(player) != "custom":
        return preset(get_id(player)).get(key, 1.0)
    return player.flags.get(f"diff_{key}", 1.0)


def set_custom_param(player, key, value):
    """Définit un paramètre personnalisé (uniquement en mode custom)."""
    if get_id(player) != "custom":
        return
    player.flags[f"diff_{key}"] = max(0.1, min(3.0, float(value)))


def salary_mult(player):
    if get_id(player) == "custom":
        return get_custom_param(player, "salary_mult")
    return preset(get_id(player))["salary_mult"]


def maint_margin_mult(player):
    if get_id(player) == "custom":
        return get_custom_param(player, "maint_margin_mult")
    return preset(get_id(player))["maint_margin_mult"]


def crisis_bad_mult(player):
    """Multiplicateur du poids des scénarios NÉFASTES (core/scenarios.py) —
    les booms (kind good) ne sont pas touchés."""
    if get_id(player) == "custom":
        return get_custom_param(player, "crisis_bad_mult")
    return preset(get_id(player))["crisis_bad_mult"]


def crisis_sev_mult(player):
    """Multiplicateur de la sévérité tirée pour un scénario néfaste."""
    if get_id(player) == "custom":
        return get_custom_param(player, "crisis_sev_mult")
    return preset(get_id(player))["crisis_sev_mult"]


def rival_aggro_mult(player):
    """Multiplicateur des probabilités d'action des rivaux (core/rivals.py::act) —
    Exigeant les rend plus mordants, Détendu plus passifs."""
    if get_id(player) == "custom":
        return get_custom_param(player, "rival_aggro_mult")
    return preset(get_id(player))["rival_aggro_mult"]


def daily_seed(date=None):
    """Graine de marché du jour : identique pour tous les joueurs le même
    jour (défi partagé), déterministe et stable dans la plage int32."""
    d = date or datetime.date.today()
    return (d.year * 10_000 + d.month * 100 + d.day) % 2_000_000_000 + 1


def mark_daily(player, date=None):
    d = date or datetime.date.today()
    player.flags["daily_challenge"] = d.isoformat()


def is_daily_challenge(player):
    return bool(player.flags.get("daily_challenge"))


def status_label(player):
    """Libellé court pour un badge en jeu (topbar, écran Carrière) — inclut
    le preset seulement s'il diffère du défaut (Normal, cas le plus courant,
    n'a pas besoin d'être rappelé en permanence) et le défi du jour s'il est
    actif. Retourne None si rien à signaler (Normal + pas de défi)."""
    bits = []
    pid = get_id(player)
    if pid != DEFAULT:
        bits.append(label(preset(pid)))
    if is_daily_challenge(player):
        bits.append(_L("Défi du jour", "Daily challenge"))
    return " · ".join(bits) if bits else None
