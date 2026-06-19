"""
archetypes.py — Archétypes de run (logique pure, sans pygame).

Le TRACK (core/tracks.py) est une spécialisation de milieu de carrière, choisie
au grade Analyst. L'ARCHÉTYPE est une PHILOSOPHIE DE DÉPART, choisie à la
création de la partie, orthogonale au track : il ne change pas le contenu
proposé mais la manière dont le joueur EN TIRE PARTI — avec un vrai avantage
ET un vrai coût, pas un simple bonus cosmétique. Deux parties avec le même
track mais un archétype différent doivent se sentir mécaniquement différentes
du premier au dernier trimestre.

Clés de perk (toutes optionnelles ; valeur par défaut = neutre) :
  starting_cash_mult     : multiplie le capital de départ              (def 1.0)
  deal_gen_prob_mult      : multiplie la fréquence d'apparition des deals (def 1.0)
  deal_reward_mult        : multiplie le gain cash des deals réussis    (def 1.0)
  deal_success_bonus      : bonus additif de proba de réussite des deals (def 0.0)
  rep_loss_mult           : multiplie la perte de réputation en cas d'échec
                             (deal manqué/raté, mandat échoué)           (def 1.0)
  heat_gain_mult          : multiplie la HAUSSE de scrutin réglementaire
                             (jamais la baisse) lors des dilemmes        (def 1.0)
  margin_call_penalty_mult: multiplie la pénalité de liquidation forcée  (def 1.0)
  mandate_offer_mult      : multiplie la proba d'offre de mandat         (def 1.0)
  mandate_reward_mult     : multiplie la récompense des mandats         (def 1.0)

Ces clés se composent MULTIPLICATIVEMENT avec les perks de track (deal_edge,
mandats...) : l'archétype et le track sont deux dimensions indépendantes.
"""

ARCHETYPES = [
    {
        "id": "prudence", "name": "Prudence extrême",
        "tagline": "Survivre avant de gagner.",
        "desc": ("Capital de départ +15%, scrutin et appels de marge bien plus "
                 "cléments. En contrepartie, les deals rapportent moins et "
                 "se présentent moins souvent : une carrière lente, mais "
                 "rarement en danger."),
        "perks": {
            "starting_cash_mult": 1.15,
            "heat_gain_mult": 0.65,
            "margin_call_penalty_mult": 0.6,
            "deal_gen_prob_mult": 0.85,
            "deal_reward_mult": 0.8,
            "mandate_reward_mult": 0.85,
        },
    },
    {
        "id": "agressif", "name": "Ambition agressive",
        "tagline": "Tout pour la croissance, quel qu'en soit le prix.",
        "desc": ("Deals et mandats nettement plus rémunérateurs. Mais le "
                 "scrutin réglementaire grimpe plus vite, les appels de "
                 "marge coûtent plus cher, et un échec entame davantage la "
                 "réputation. Capital de départ réduit : pas de filet."),
        "perks": {
            "starting_cash_mult": 0.85,
            "deal_reward_mult": 1.3,
            "mandate_reward_mult": 1.2,
            "heat_gain_mult": 1.4,
            "margin_call_penalty_mult": 1.35,
            "rep_loss_mult": 1.25,
        },
    },
    {
        "id": "compliance", "name": "Compliance first",
        "tagline": "L'intégrité comme stratégie, pas comme contrainte.",
        "desc": ("Le scrutin réglementaire monte presque trois fois plus "
                 "lentement, et un échec pèse moins lourd sur la réputation. "
                 "En échange, l'activité est plus prudente : deals moins "
                 "fréquents et moins rémunérateurs, mandats légèrement "
                 "réduits."),
        "perks": {
            "heat_gain_mult": 0.35,
            "rep_loss_mult": 0.8,
            "margin_call_penalty_mult": 0.8,
            "deal_gen_prob_mult": 0.85,
            "deal_reward_mult": 0.85,
            "mandate_reward_mult": 0.9,
        },
    },
    {
        "id": "dealmaker", "name": "Dealmaker",
        "tagline": "Toujours une affaire en cours.",
        "desc": ("Les deals tombent plus souvent et rapportent plus, les "
                 "clients proposent davantage de mandats. Mais chaque échec "
                 "coûte cher en réputation, et l'agitation permanente attire "
                 "l'attention du régulateur."),
        "perks": {
            "deal_gen_prob_mult": 1.35,
            "deal_reward_mult": 1.2,
            "mandate_offer_mult": 1.25,
            "rep_loss_mult": 1.35,
            "heat_gain_mult": 1.15,
        },
    },
    {
        "id": "quant", "name": "Quant opportuniste",
        "tagline": "Le modèle a raison plus souvent qu'il n'a tort.",
        "desc": ("Une meilleure lecture des deals (proba de réussite plus "
                 "élevée) et un flux d'opportunités plus dense. Mais les "
                 "clients confient moins facilement leur capital à une "
                 "approche jugée trop technique, et les raccourcis algo "
                 "attirent un peu plus l'attention du régulateur."),
        "perks": {
            "deal_success_bonus": 0.08,
            "deal_gen_prob_mult": 1.15,
            "mandate_offer_mult": 0.75,
            "heat_gain_mult": 1.1,
            "margin_call_penalty_mult": 1.1,
        },
    },
]

_BY_ID = {a["id"]: a for a in ARCHETYPES}

# (clé, libellé FR, "higher"|"lower" = sens dans lequel la valeur est un AVANTAGE)
PERK_INFO = [
    ("deal_gen_prob_mult", "Fréquence des deals", "higher"),
    ("deal_reward_mult", "Gain des deals réussis", "higher"),
    ("deal_success_bonus", "Bonus de réussite des deals", "higher"),
    ("rep_loss_mult", "Perte de réputation (échec)", "lower"),
    ("heat_gain_mult", "Hausse du scrutin réglementaire", "lower"),
    ("margin_call_penalty_mult", "Pénalité d'appel de marge", "lower"),
    ("mandate_offer_mult", "Fréquence des offres de mandat", "higher"),
    ("mandate_reward_mult", "Rémunération des mandats", "higher"),
]

_DEFAULTS = {
    "starting_cash_mult": 1.0, "deal_gen_prob_mult": 1.0, "deal_reward_mult": 1.0,
    "deal_success_bonus": 0.0, "rep_loss_mult": 1.0, "heat_gain_mult": 1.0,
    "margin_call_penalty_mult": 1.0, "mandate_offer_mult": 1.0,
    "mandate_reward_mult": 1.0,
}


def get(archetype_id):
    return _BY_ID.get(archetype_id)


def perk(player, key):
    """Valeur du perk `key` pour l'archétype du joueur (ou défaut neutre)."""
    arch = _BY_ID.get(getattr(player, "archetype", None))
    if arch is None:
        return _DEFAULTS.get(key)
    return arch["perks"].get(key, _DEFAULTS.get(key))


def apply(player, archetype_id):
    """Fixe l'archétype d'un joueur neuf et applique son effet sur le capital
    de départ (les autres perks sont lus en continu via `perk()`)."""
    arch = get(archetype_id) or ARCHETYPES[0]
    player.archetype = arch["id"]
    player.cash *= arch["perks"].get("starting_cash_mult", 1.0)
    if player.cash_history:
        player.cash_history[-1] = player.cash
    return arch
