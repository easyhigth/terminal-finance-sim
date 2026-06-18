"""
deal_game.py — Mini-jeux de résolution de deals (logique pure, sans pygame).

Au lieu d'une réussite tirée au dé, traiter un deal demande une vraie DÉCISION
financière, propre à la voie du deal (M&A, Portfolio, Risk, Quant, Advisory).
La qualité du choix détermine le résultat :
  "good" → succès plein   "ok" → succès partiel   "bad" → échec

Chaque défi : {prompt, context, choices:[{text, quality}], expl}.
Les valeurs s'appuient sur core/finmath (VaR, Black-Scholes, Sharpe...).
"""
import random


def _mna(rng):
    ebitda = rng.randint(80, 220)
    fair_mult = rng.choice([8, 9, 10, 11])
    fair_ev = ebitda * fair_mult
    low, high = fair_mult - 3, fair_mult + 4
    choices = [
        {"text": f"Offrir {fair_mult}× EBITDA (EV {fair_ev}M) — au prix de marché",
         "quality": "good"},
        {"text": f"Offrir {low}× EBITDA (EV {ebitda*low}M) — agressif, risque de refus",
         "quality": "ok"},
        {"text": f"Offrir {high}× EBITDA (EV {ebitda*high}M) — surpayer pour sécuriser",
         "quality": "bad"},
    ]
    expl = (f"À {fair_mult}× pour {ebitda}M d'EBITDA, l'offre reflète la juste valeur "
            f"sectorielle. Surpayer ({high}×) détruit de la valeur ; trop bas, la cible refuse.")
    return {"prompt": "Quelle offre proposez-vous pour cette acquisition ?",
            "context": f"Cible : EBITDA {ebitda}M, multiple sectoriel ~{fair_mult}× EV/EBITDA.",
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
        choices.append({"text": f"Portefeuille {chr(65+i)} : rendement {r}%, volatilité {v}%",
                        "quality": q})
    expl = (f"Le ratio de Sharpe = (rendement − {rf}%) / volatilité. Le portefeuille "
            f"{chr(65+best)} offre le meilleur rendement ajusté du risque.")
    return {"prompt": "Quel portefeuille recommandez-vous au client ?",
            "context": "Objectif : meilleur rendement ajusté du risque (Sharpe).",
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
    expl = (f"VaR 99% 1j ≈ notionnel × z × σ = {notional} × {z} × {vol}% ≈ {correct}M. "
            "C'est la perte qui ne sera dépassée qu'1 jour sur 100.")
    return {"prompt": "Quelle est la VaR 99% à 1 jour de cette position ?",
            "context": f"Position {notional}M, volatilité quotidienne {vol}%, z(99%)=2,33.",
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
    expl = (f"Valeur intrinsèque d'un {typ} = max(S−K, 0) pour un call, max(K−S, 0) pour "
            f"un put. Ici S={S}, K={K} → {correct}.")
    return {"prompt": f"Valeur intrinsèque de ce {typ} à l'échéance ?",
            "context": f"Sous-jacent S={S}, strike K={K}, option de type {typ}.",
            "choices": triples, "expl": expl}


def _advisory(rng):
    choices = [
        {"text": "Diagnostiquer le besoin du client avant de proposer une structure",
         "quality": "good"},
        {"text": "Proposer d'emblée le produit le plus margé pour la banque",
         "quality": "bad"},
        {"text": "Reprendre la structure du dernier deal comparable", "quality": "ok"},
    ]
    rng.shuffle(choices)
    return {"prompt": "Comment abordez-vous ce mandat de conseil ?",
            "context": "Un client corporate cherche un financement stratégique.",
            "choices": choices,
            "expl": "Le bon conseil part du besoin du client, pas du produit le plus rentable "
                    "pour la banque (conflit d'intérêts) ni d'un copier-coller."}


def _general(rng):
    choices = [
        {"text": "Recommander des valeurs financières (marges accrues)", "quality": "good"},
        {"text": "Surpondérer la tech non rentable et l'immobilier", "quality": "bad"},
        {"text": "Rester neutre en attendant plus de visibilité", "quality": "ok"},
    ]
    rng.shuffle(choices)
    return {"prompt": "La banque centrale relève ses taux. Votre note recommande de…",
            "context": "Hausse des taux directeurs ce trimestre.",
            "choices": choices,
            "expl": "Quand les taux montent, les banques profitent de marges accrues tandis "
                    "que la tech non rentable et l'immobilier souffrent (cf. leçon Taux)."}


_BUILDERS = {
    "M&A": _mna, "Portfolio": _portfolio, "Risk": _risk,
    "Quant": _quant, "Advisory": _advisory, "General": _general,
}


def make_challenge(deal, rng=None):
    """Construit le défi correspondant à la voie du deal."""
    rng = rng or random
    builder = _BUILDERS.get(deal.get("kind"), _general)
    ch = builder(rng)
    ch["deal"] = deal
    return ch
