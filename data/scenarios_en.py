"""
scenarios_en.py — Traduction EN de la banque de scénarios (core/scenarios.py).
Dict id -> {"name", "story"}. Les chocs (world/sectors/regions/vol/steps/poids)
restent partagés avec la version FR (cf. scenarios.localized()).
"""

SCENARIOS_EN = {
    "krach": {
        "name": "Systemic crash",
        "story": "A cascade of defaults freezes interbank credit — reminiscent of 2008.",
    },
    "taux": {
        "name": "Rate shock",
        "story": "A brutal rate hike weakens regional banks and real estate (2023-style).",
    },
    "tornade": {
        "name": "Agricultural catastrophe",
        "story": "Tornadoes and droughts devastate crops: agribusiness stocks plunge.",
    },
    "techbust": {
        "name": "Tech bubble burst",
        "story": "Tech multiples violently deflate after disappointing earnings.",
    },
    "energie": {
        "name": "Energy shock",
        "story": "A supply disruption sends the energy sector soaring then crashing.",
    },
    "asia": {
        "name": "Geopolitical tensions (Asia)",
        "story": "Regional tensions in Asia trigger a flight to quality.",
    },
    "techboom": {
        "name": "Tech boom",
        "story": "An AI breakthrough propels tech and semiconductor stocks.",
    },
    "relance": {
        "name": "Global stimulus plan",
        "story": "A massive public investment plan boosts industry and materials.",
    },
    "pandemie": {
        "name": "Health shock",
        "story": "A health crisis paralyzes activity; healthcare outperforms, the rest plunges.",
    },
    "credit": {
        "name": "Regional banking crisis",
        "story": "Credit conditions tighten sharply in one region; banks and real estate suffer.",
    },
    "ipo": {
        "name": "Wave of IPOs",
        "story": "An euphoric market fuels a wave of IPOs; tech and finance benefit.",
    },
    "matieres": {
        "name": "Commodity price surge",
        "story": "Commodity prices soar: clear sectoral winners and losers.",
    },
    "scandale_finance": {
        "name": "Banking accounting scandal",
        "story": "An accounting manipulation scandal breaks at a major bank: the Finance "
                 "sector tumbles on investor distrust.",
    },
    "antitrust_tech": {
        "name": "Tech antitrust fine",
        "story": "Regulators impose a record fine for abuse of dominant position: the Tech "
                 "sector absorbs the regulatory shock.",
    },
    "immo_asie": {
        "name": "Real estate crisis (Asia)",
        "story": "An over-leveraged developer defaults in Asia: the regional real estate "
                 "crisis spreads to sector stocks.",
    },
    "immo_europe": {
        "name": "Real estate crisis (Europe)",
        "story": "Rising credit costs burst a real estate bubble in Europe, weakening "
                 "developers and REITs in the region.",
    },
    "fx_emergent": {
        "name": "Currency crisis (emerging market)",
        "story": "A brutal devaluation hits an emerging currency, draining capital flows "
                 "from the region.",
    },
    "sante_sectoriel": {
        "name": "Massive health recall",
        "story": "A large-scale product recall reveals manufacturing defects: the Health "
                 "sector falls on fears of cascading litigation.",
    },
    "hist1987": {
        "name": "1987 crash (\"Black Monday\")",
        "story": "A global flash crash with no clear macro trigger — programme trading "
                 "amplifies the panic within a few sessions (October 19, 1987).",
    },
    "hist2000": {
        "name": "Dot-com bust (2000)",
        "story": "Speculative tech valuations deflate over a long stretch — no single "
                 "crash, but no respite either (2000-2002).",
    },
    "hist2008": {
        "name": "Global financial crisis (2008)",
        "story": "The mortgage credit collapse freezes the global financial system: a "
                 "long, deep shock centred on banks and real estate.",
    },
    "hist2020": {
        "name": "COVID crash (2020)",
        "story": "The sudden global economic shutdown triggers the fastest crash in "
                 "history — as brief as it is violent (February-March 2020).",
    },
}
