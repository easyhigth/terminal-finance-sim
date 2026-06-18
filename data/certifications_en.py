"""
certifications_en.py — Traduction EN des descriptions de programmes
(core/certifications.py). Dict id -> {"desc"}. Les autres champs (fee, rep,
levels, track, tier...) restent partagés avec la version FR (cf.
certifications.desc_for()).
"""

PROGRAMS_EN = {
    "CFA": {
        "desc": "The benchmark in portfolio management and investment analysis.",
    },
    "FRM": {
        "desc": "The benchmark in risk management (market, credit, operational).",
    },
    "CQF": {
        "desc": "Quantitative finance: derivatives, stochastic models, ML.",
    },
    "ACI": {
        "desc": "The trading floor benchmark in FX: quoting conventions, "
                "settlement, currency risk management.",
    },
}
