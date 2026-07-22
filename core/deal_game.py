"""
deal_game.py — Mini-jeux de résolution de deals (logique pure, sans pygame).

Au lieu d'une réussite tirée au dé, traiter un deal demande une vraie DÉCISION
financière, propre à la voie du deal (M&A, Portfolio, Risk, Quant, Advisory).
La qualité du choix détermine le résultat :
  "good" → succès plein   "ok" → succès partiel   "bad" → échec

Chaque défi : {prompt, context, choices:[{text, quality}], expl}. Les textes
sont localisés au moment de la CONSTRUCTION (le défi n'est pas persisté ; il est
régénéré à chaque ouverture de la scène) via _L(fr, en).
Les valeurs s'appuient sur core/finmath (VaR, Black-Scholes, Sharpe...).
"""
import random


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def _mna(rng):
    ebitda = rng.randint(80, 220)
    fair_mult = rng.choice([8, 9, 10, 11])
    fair_ev = ebitda * fair_mult
    low, high = fair_mult - 3, fair_mult + 4
    choices = [
        {"text": _L(f"Offrir {fair_mult}× EBITDA (EV {fair_ev}M) — au prix de marché",
                    f"Offer {fair_mult}× EBITDA (EV {fair_ev}M) — at market price"),
         "quality": "good"},
        {"text": _L(f"Offrir {low}× EBITDA (EV {ebitda*low}M) — agressif, risque de refus",
                    f"Offer {low}× EBITDA (EV {ebitda*low}M) — aggressive, risk of refusal"),
         "quality": "ok"},
        {"text": _L(f"Offrir {high}× EBITDA (EV {ebitda*high}M) — surpayer pour sécuriser",
                    f"Offer {high}× EBITDA (EV {ebitda*high}M) — overpay to secure"),
         "quality": "bad"},
    ]
    expl = _L(f"À {fair_mult}× pour {ebitda}M d'EBITDA, l'offre reflète la juste valeur "
              f"sectorielle. Surpayer ({high}×) détruit de la valeur ; trop bas, la cible refuse.",
              f"At {fair_mult}× for {ebitda}M of EBITDA, the offer reflects fair sector "
              f"value. Overpaying ({high}×) destroys value; too low, the target refuses.")
    return {"prompt": _L("Quelle offre proposez-vous pour cette acquisition ?",
                         "What offer do you make for this acquisition?"),
            "context": _L(f"Cible : EBITDA {ebitda}M, multiple sectoriel ~{fair_mult}× EV/EBITDA.",
                          f"Target: EBITDA {ebitda}M, sector multiple ~{fair_mult}× EV/EBITDA."),
            "choices": choices, "expl": expl}


def _portfolio(rng):
    opts = []
    for _ in range(3):
        ret = rng.uniform(6, 16)
        vol = rng.uniform(8, 26)
        opts.append((round(ret, 1), round(vol, 1)))
    rf = 2.0
    sharpes = [(r - rf) / v for r, v in opts]
    best = max(range(3), key=lambda i: sharpes[i])
    worst = min(range(3), key=lambda i: sharpes[i])
    choices = []
    for i, (r, v) in enumerate(opts):
        q = "good" if i == best else ("bad" if i == worst else "ok")
        choices.append({"text": _L(f"Portefeuille {chr(65+i)} : rendement {r}%, volatilité {v}%",
                                   f"Portfolio {chr(65+i)}: return {r}%, volatility {v}%"),
                        "quality": q})
    expl = _L(f"Le ratio de Sharpe = (rendement − {rf}%) / volatilité. Le portefeuille "
              f"{chr(65+best)} offre le meilleur rendement ajusté du risque.",
              f"The Sharpe ratio = (return − {rf}%) / volatility. Portfolio "
              f"{chr(65+best)} offers the best risk-adjusted return.")
    return {"prompt": _L("Quel portefeuille recommandez-vous au client ?",
                         "Which portfolio do you recommend to the client?"),
            "context": _L("Objectif : meilleur rendement ajusté du risque (Sharpe).",
                          "Objective: best risk-adjusted return (Sharpe)."),
            "choices": choices, "expl": expl}


def _risk(rng):
    notional = rng.choice([50, 80, 120, 200])      # M
    vol = round(rng.uniform(1.2, 3.0), 1)           # % quotidien
    z = 2.33                                        # 99 %
    var = notional * z * vol / 100.0                # en M
    distractors = [round(var * 0.5, 2), round(var * 1.8, 2)]
    correct = round(var, 2)
    triples = [{"text": f"≈ {correct}M", "quality": "good"},
               {"text": f"≈ {distractors[0]}M", "quality": "bad"},
               {"text": f"≈ {distractors[1]}M", "quality": "ok"}]
    rng.shuffle(triples)
    expl = _L(f"VaR 99% 1j ≈ notionnel × z × σ = {notional} × {z} × {vol}% ≈ {correct}M. "
              "C'est la perte qui ne sera dépassée qu'1 jour sur 100.",
              f"1d 99% VaR ≈ notional × z × σ = {notional} × {z} × {vol}% ≈ {correct}M. "
              "It is the loss exceeded only 1 day in 100.")
    return {"prompt": _L("Quelle est la VaR 99% à 1 jour de cette position ?",
                         "What is the 1-day 99% VaR of this position?"),
            "context": _L(f"Position {notional}M, volatilité quotidienne {vol}%, z(99%)=2,33.",
                          f"Position {notional}M, daily volatility {vol}%, z(99%)=2.33."),
            "choices": triples, "expl": expl}


def _quant(rng):
    S = rng.randint(90, 140)
    K = rng.choice([80, 90, 100, 110, 120])
    typ = rng.choice(["call", "put"])
    intrinsic = max(0.0, (S - K) if typ == "call" else (K - S))
    distractors = [max(0.0, (K - S) if typ == "call" else (S - K)), abs(S - K) + 5]
    correct = round(intrinsic, 1)
    triples = [{"text": f"{correct}", "quality": "good"},
               {"text": f"{round(distractors[0],1)}", "quality": "bad"},
               {"text": f"{round(distractors[1],1)}", "quality": "ok"}]
    rng.shuffle(triples)
    expl = _L(f"Valeur intrinsèque d'un {typ} = max(S−K, 0) pour un call, max(K−S, 0) pour "
              f"un put. Ici S={S}, K={K} → {correct}.",
              f"Intrinsic value of a {typ} = max(S−K, 0) for a call, max(K−S, 0) for "
              f"a put. Here S={S}, K={K} → {correct}.")
    return {"prompt": _L(f"Valeur intrinsèque de ce {typ} à l'échéance ?",
                         f"Intrinsic value of this {typ} at expiry?"),
            "context": _L(f"Sous-jacent S={S}, strike K={K}, option de type {typ}.",
                          f"Underlying S={S}, strike K={K}, {typ} option."),
            "choices": triples, "expl": expl}


def _advisory(rng):
    choices = [
        {"text": _L("Diagnostiquer le besoin du client avant de proposer une structure",
                    "Diagnose the client's need before proposing a structure"),
         "quality": "good"},
        {"text": _L("Proposer d'emblée le produit le plus margé pour la banque",
                    "Immediately pitch the highest-margin product for the bank"),
         "quality": "bad"},
        {"text": _L("Reprendre la structure du dernier deal comparable",
                    "Reuse the structure of the last comparable deal"), "quality": "ok"},
    ]
    rng.shuffle(choices)
    return {"prompt": _L("Comment abordez-vous ce mandat de conseil ?",
                         "How do you approach this advisory mandate?"),
            "context": _L("Un client corporate cherche un financement stratégique.",
                          "A corporate client is seeking strategic financing."),
            "choices": choices,
            "expl": _L("Le bon conseil part du besoin du client, pas du produit le plus rentable "
                       "pour la banque (conflit d'intérêts) ni d'un copier-coller.",
                       "Good advice starts from the client's need, not from the most profitable "
                       "product for the bank (conflict of interest) nor from a copy-paste.")}


def _general(rng):
    choices = [
        {"text": _L("Recommander des valeurs financières (marges accrues)",
                    "Recommend financial stocks (higher margins)"), "quality": "good"},
        {"text": _L("Surpondérer la tech non rentable et l'immobilier",
                    "Overweight unprofitable tech and real estate"), "quality": "bad"},
        {"text": _L("Rester neutre en attendant plus de visibilité",
                    "Stay neutral pending more visibility"), "quality": "ok"},
    ]
    rng.shuffle(choices)
    return {"prompt": _L("La banque centrale relève ses taux. Votre note recommande de…",
                         "The central bank hikes rates. Your note recommends…"),
            "context": _L("Hausse des taux directeurs ce trimestre.",
                          "Policy rate hike this quarter."),
            "choices": choices,
            "expl": _L("Quand les taux montent, les banques profitent de marges accrues tandis "
                       "que la tech non rentable et l'immobilier souffrent (cf. leçon Taux).",
                       "When rates rise, banks benefit from wider margins while unprofitable "
                       "tech and real estate suffer (see the Rates lesson).")}


def _dcm(rng):
    from core import bonds as bonds_mod
    from core import credit
    from data import companies as comp_data
    c = rng.choice(comp_data.COMPANIES)
    ebitda = c["revenue"] * c["ebitda_margin"]
    nd_ebitda = c["net_debt"] / ebitda if ebitda > 0 else None
    rating = credit.rating_for(nd_ebitda, c["sigma"])
    years = rng.choice([3, 5, 7, 10])
    fair_bps = round(bonds_mod._RATING_SPREAD.get(rating, 0.02) * 10000)
    tight = max(5, round(fair_bps * 0.6))
    wide = round(fair_bps * 1.6)
    choices = [
        {"text": _L(f"Émettre à {fair_bps} pb au-dessus de la courbe (spread de marché pour {rating})",
                    f"Issue at {fair_bps} bp over the curve (market spread for {rating})"),
         "quality": "good"},
        {"text": _L(f"Émettre à {tight} pb — trop serré, risque d'échec du book-building",
                    f"Issue at {tight} bp — too tight, risk of failed book-building"),
         "quality": "bad"},
        {"text": _L(f"Émettre à {wide} pb — trop large, {c['name']} paierait un coupon excessif",
                    f"Issue at {wide} bp — too wide, {c['name']} would pay an excessive coupon"),
         "quality": "ok"},
    ]
    rng.shuffle(choices)
    expl = _L(f"{c['name']} est notée {rating} (levier dette nette/EBITDA ≈ "
              f"{nd_ebitda:.1f}x). Une émission à {years} ans se price autour de {fair_bps} pb "
              "au-dessus de la courbe : trop serré, les investisseurs ne souscrivent pas ; "
              "trop large, l'émetteur surpaie inutilement.",
              f"{c['name']} is rated {rating} (net debt/EBITDA leverage ≈ "
              f"{nd_ebitda:.1f}x). A {years}-year issue prices around {fair_bps} bp "
              "over the curve: too tight, investors don't subscribe; "
              "too wide, the issuer overpays needlessly.") if nd_ebitda is not None else _L(
              f"{c['name']} est notée {rating}. Une émission à {years} ans se price autour "
              f"de {fair_bps} pb au-dessus de la courbe.",
              f"{c['name']} is rated {rating}. A {years}-year issue prices around "
              f"{fair_bps} bp over the curve.")
    return {"prompt": _L(f"À quel spread structurez-vous l'émission obligataire de {c['name']} "
                         f"({years} ans, notée {rating}) ?",
                         f"At what spread do you structure {c['name']}'s bond issue "
                         f"({years}y, rated {rating})?"),
            "context": _L("Mandat DCM : origination et book-building d'une émission de dette.",
                          "DCM mandate: origination and book-building of a debt issue."),
            "choices": choices, "expl": expl}


_BUILDERS = {
    "M&A": _mna, "Portfolio": _portfolio, "Risk": _risk,
    "Quant": _quant, "Advisory": _advisory, "General": _general,
    "DCM": _dcm,
}


def make_challenge(deal, rng=None):
    """Construit le défi correspondant à la voie du deal."""
    rng = rng or random
    builder = _BUILDERS.get(deal.get("kind"), _general)
    ch = builder(rng)
    ch["deal"] = deal
    return ch
