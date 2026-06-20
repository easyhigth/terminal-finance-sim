"""
firms.py — ADN de la firme de départ (logique pure, sans pygame).

L'ARCHÉTYPE (core/archetypes.py) est une PHILOSOPHIE DE JOUEUR ; le TRACK
(core/tracks.py) est une spécialisation de milieu de carrière. La FIRME est
une troisième dimension, ORTHOGONALE aux deux premières, choisie elle aussi à
la création de la partie : c'est l'institution qui vous emploie, avec ses
propres règles de financement, ses contraintes mécaniques et sa sensibilité
de marché — pas un simple habillage cosmétique. Une boutique M&A et un hedge
fund avec le même archétype et le même track doivent quand même se sentir
différents au quotidien (levier, marge, deals, mandats, obligations).

Clés de perk (toutes optionnelles ; valeur par défaut = neutre) :
  starting_cash_mult       : multiplie le capital de départ                (def 1.0)
  deal_gen_prob_mult        : multiplie la fréquence d'apparition des deals  (def 1.0)
  deal_reward_mult          : multiplie le gain cash des deals réussis      (def 1.0)
  deal_success_bonus        : bonus additif de proba de réussite des deals  (def 0.0)
  rep_loss_mult             : multiplie la perte de réputation en cas d'échec (def 1.0)
  heat_gain_mult            : multiplie la hausse de scrutin réglementaire   (def 1.0)
  margin_call_penalty_mult  : multiplie la pénalité de liquidation forcée   (def 1.0)
  mandate_offer_mult        : multiplie la proba d'offre de mandat          (def 1.0)
  mandate_reward_mult       : multiplie la récompense des mandats          (def 1.0)
  max_leverage_add          : levier maximal supplémentaire (règle de financement) (def 0.0)
  margin_spread_mult        : multiplie le surcoût d'emprunt sur marge      (def 1.0)
  maint_margin_mult         : multiplie la marge de maintenance effective   (def 1.0)
  bond_commission_mult      : multiplie la commission sur les obligations   (def 1.0)
  beta_exposure_mult        : multiplie le bêta effectif du portefeuille actions
                               (sensibilité de marché, lu par core/portfolio_views.py) (def 1.0)
  excluded_sectors          : secteurs actions interdits à l'achat (contrainte) (def [])

Ces clés se composent MULTIPLICATIVEMENT avec les perks d'archétype et de
track : firme, archétype et track sont trois dimensions indépendantes,
stockées séparément sur le joueur (`player.firm`, `player.archetype`,
`player.track`).
"""

FIRMS = [
    {
        "id": "boutique_ma", "name": "Boutique M&A",
        "tagline": "Peu de deals, mais les bons.",
        "desc": ("Une petite structure de conseil pure, focalisée sur les "
                 "rapprochements d'entreprises. Les deals rapportent nettement "
                 "plus et les clients confient plus volontiers des mandats, mais "
                 "le capital de départ est modeste et le levier accordé reste "
                 "prudent — pas de book de trading à faire tourner."),
        "perks": {
            "starting_cash_mult": 0.8,
            "deal_reward_mult": 1.25,
            "mandate_offer_mult": 1.2,
            "mandate_reward_mult": 1.15,
            "max_leverage_add": -0.5,
        },
    },
    {
        "id": "asset_manager", "name": "Gestionnaire d'actifs",
        "tagline": "Le mandat avant tout.",
        "desc": ("Une société de gestion classique, rémunérée à la confiance des "
                 "clients plutôt qu'au coup par coup. Les mandats sont bien plus "
                 "fréquents et mieux payés, le financement est avantageux (gros "
                 "volumes), mais le bêta du portefeuille est bridé : pas question "
                 "de s'écarter trop du marché pour un client institutionnel."),
        "perks": {
            "mandate_offer_mult": 1.5,
            "mandate_reward_mult": 1.25,
            "margin_spread_mult": 0.8,
            "beta_exposure_mult": 0.85,
            "deal_gen_prob_mult": 0.8,
        },
    },
    {
        "id": "hedge_fund", "name": "Hedge fund",
        "tagline": "Le risque est le métier.",
        "desc": ("Levier maximal et sensibilité de marché bien supérieurs à la "
                 "norme : on cherche l'alpha en s'exposant plus que les autres. "
                 "En contrepartie, la marge de maintenance est plus stricte et "
                 "un appel de marge coûte nettement plus cher — la liquidité est "
                 "le prix de l'agressivité."),
        "perks": {
            "max_leverage_add": 1.25,
            "beta_exposure_mult": 1.25,
            "maint_margin_mult": 1.3,
            "margin_call_penalty_mult": 1.4,
            "deal_success_bonus": 0.04,
        },
    },
    {
        "id": "banque_universelle", "name": "Banque universelle",
        "tagline": "Un bilan solide pour tout faire, sans excès.",
        "desc": ("Le bilan le plus large : capital de départ supérieur et coût de "
                 "financement réduit grâce à la taille. Aucune spécialisation "
                 "particulière — pas d'avantage de marché, mais pas de faiblesse "
                 "non plus, un profil neutre et robuste pour qui veut tout "
                 "essayer sans angle mort."),
        "perks": {
            "starting_cash_mult": 1.2,
            "margin_spread_mult": 0.75,
            "margin_call_penalty_mult": 0.85,
        },
    },
    {
        "id": "maison_esg", "name": "Maison ESG",
        "tagline": "L'impact comme mandat, pas comme option.",
        "desc": ("Une maison entièrement tournée vers la finance durable : "
                 "mandats ESG nettement plus fréquents et mieux rémunérés, "
                 "scrutin réglementaire qui grimpe plus lentement (réputation "
                 "soignée). Contrainte forte en retour : interdiction d'acheter "
                 "des actions Énergie ou Matériaux, jugées incompatibles avec le "
                 "mandat d'impact."),
        "perks": {
            "mandate_offer_mult": 1.3,
            "mandate_reward_mult": 1.2,
            "heat_gain_mult": 0.7,
            "deal_gen_prob_mult": 0.9,
            "excluded_sectors": ["Energie", "Materiaux"],
        },
    },
    {
        "id": "desk_obligataire", "name": "Desk obligataire",
        "tagline": "Le crédit et les taux, rien d'autre ne compte vraiment.",
        "desc": ("Spécialiste pur du fixed income : commission sur obligations "
                 "réduite de moitié et coût de financement nettement plus bas. "
                 "En échange, la sensibilité du portefeuille actions est réduite "
                 "(le desk n'est pas taillé pour le directionnel actions) et les "
                 "deals actions/M&A se font plus rares."),
        "perks": {
            "bond_commission_mult": 0.5,
            "margin_spread_mult": 0.7,
            "beta_exposure_mult": 0.75,
            "deal_gen_prob_mult": 0.75,
        },
    },
]

_BY_ID = {f["id"]: f for f in FIRMS}

# (clé, libellé FR, "higher"|"lower" = sens dans lequel la valeur est un AVANTAGE)
PERK_INFO = [
    ("starting_cash_mult", "Capital de départ", "higher"),
    ("deal_gen_prob_mult", "Fréquence des deals", "higher"),
    ("deal_reward_mult", "Gain des deals réussis", "higher"),
    ("deal_success_bonus", "Bonus de réussite des deals", "higher"),
    ("mandate_offer_mult", "Fréquence des offres de mandat", "higher"),
    ("mandate_reward_mult", "Rémunération des mandats", "higher"),
    ("heat_gain_mult", "Hausse du scrutin réglementaire", "lower"),
    ("margin_call_penalty_mult", "Pénalité d'appel de marge", "lower"),
    ("max_leverage_add", "Levier maximal supplémentaire", "higher"),
    ("margin_spread_mult", "Surcoût d'emprunt sur marge", "lower"),
    ("maint_margin_mult", "Marge de maintenance", "lower"),
    ("bond_commission_mult", "Commission obligataire", "lower"),
    ("beta_exposure_mult", "Sensibilité de marché (bêta)", "higher"),
]

_DEFAULTS = {
    "starting_cash_mult": 1.0, "deal_gen_prob_mult": 1.0, "deal_reward_mult": 1.0,
    "deal_success_bonus": 0.0, "rep_loss_mult": 1.0, "heat_gain_mult": 1.0,
    "margin_call_penalty_mult": 1.0, "mandate_offer_mult": 1.0,
    "mandate_reward_mult": 1.0, "max_leverage_add": 0.0, "margin_spread_mult": 1.0,
    "maint_margin_mult": 1.0, "bond_commission_mult": 1.0, "beta_exposure_mult": 1.0,
    "excluded_sectors": [],
}


def get(firm_id):
    return _BY_ID.get(firm_id)


def perk(player, key):
    """Valeur du perk `key` pour la firme du joueur (ou défaut neutre)."""
    firm = _BY_ID.get(getattr(player, "firm", None))
    if firm is None:
        return _DEFAULTS.get(key)
    return firm["perks"].get(key, _DEFAULTS.get(key))


def excluded_sectors(player):
    """Liste des secteurs interdits à l'achat pour la firme du joueur."""
    return perk(player, "excluded_sectors") or []


def sector_allowed(player, sector):
    """Faux si le secteur est exclu par la contrainte de la firme du joueur."""
    return sector not in excluded_sectors(player)


def apply(player, firm_id):
    """Fixe la firme d'un joueur neuf et applique son effet sur le capital de
    départ (les autres perks sont lus en continu via `perk()`)."""
    firm = get(firm_id) or FIRMS[0]
    player.firm = firm["id"]
    player.cash *= firm["perks"].get("starting_cash_mult", 1.0)
    if player.cash_history:
        player.cash_history[-1] = player.cash
    return firm
