"""
inbox_en.py — Traduction EN des modèles de messages de la boîte de réception
(core/inbox.py). Dict id -> {"sender", "subject", "body"} où subject/body sont
des format-strings (mêmes placeholders que la version FR), et "sender" une
traduction du libellé d'expéditeur statique (RH, Desk, Conformité...).
Les noms de managers (_MANAGERS) sont des noms propres, non traduits.
"""

INBOX_EN = {
    "promotion": {
        "subject": "Congratulations on your promotion",
        "body": "{name}, your move to grade {grade} is well earned. New responsibilities "
                "await you — don't disappoint the committee.",
    },
    "promotion_package": {
        "sender": "HR",
        "subject": "New package",
        "body": "Your access to strategic mandates and premium deals is now active. "
                "The desk is counting on you.",
    },
    "quarter_all": {
        "sender": "HR",
        "subject": "Exceptional quarterly bonus",
        "body": "All your quarterly objectives were met ({done}/{total}). The committee "
                "praises the performance: bonus and increased visibility.",
    },
    "quarter_none": {
        "subject": "Disappointing quarter",
        "body": "No objectives met this quarter. The committee is watching your results. "
                "Get back on track: missions, deals, book management.",
    },
    "quarter_partial": {
        "subject": "Quarterly review",
        "body": "{done}/{total} objectives met. Decent, but the committee expects better "
                "to validate a promotion.",
    },
    "crisis_good": {
        "sender": "Desk",
        "subject": "Opportunity: {name}",
        "body": "The market is rallying favorably. The desk recommends reviewing positions "
                "to add to — but watch out for reversals.",
    },
    "crisis_bad": {
        "subject": "Market alert: {name}",
        "body": "The market is dropping. Stay level-headed: check your exposure (beta), "
                "your liquidity and your hedges. We're counting on your composure.",
    },
    "deal_sniped": {
        "sender": "Client — {title}",
        "subject": "Mandate awarded elsewhere",
        "body": "Due to your lack of response, we have awarded “{title}” to "
                "{rival_name}. Please be more responsive next time.",
    },
    "compliance_beta": {
        "sender": "Compliance",
        "subject": "High market exposure",
        "body": "Your portfolio shows a beta of {beta:.2f}. In case of a reversal, losses "
                "would be amplified. Consider HEDGE.",
    },
    "compliance_concentration": {
        "sender": "Compliance",
        "subject": "Sector concentration",
        "body": "{top:.0f}% of the book is in the {sector} sector. Diversification is "
                "insufficient relative to our internal limits (REBALANCE).",
    },
    "periodic_brief": {
        "sender": "Desk",
        "subject": "Brief: {index_name} {sens}",
        "body": "{index_name} {sens} {chg:+.2f}% in the session. Desk meeting to adjust "
                "views. Stay alert to flows.",
    },
}

# verbes ("bondit"/"recule") et libellés statiques sans interpolation complexe
_SENS_EN = {"bondit": "jumps", "recule": "falls"}
