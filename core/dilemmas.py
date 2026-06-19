"""
dilemmas.py — Décisions « signature » et arbitrages éthiques/réglementaires.

Des dilemmes surgissent au fil de la carrière : chaque option a un coût et une
conséquence CLAIRS (trésorerie, réputation, et « scrutin réglementaire »).
Couper les coins paie à court terme mais fait monter le scrutin (heat) — et au
delà d'un seuil, le régulateur peut ouvrir une enquête : amende + réputation.

Logique pure, sans pygame.

Catégories : ethique · reglementaire · strategie · signature (rares, gros).
Effets d'une option :
  cash_k : milliers (base, mis à l'échelle du grade), peut être négatif
  rep    : delta de réputation
  heat   : delta de scrutin réglementaire (+ = plus risqué)
  outcome: texte d'issue affiché après le choix
"""
import random

# ---------------------------------------------------------------------------
# Banque de dilemmes
# ---------------------------------------------------------------------------
DILEMMAS = [
    # ------------------------------- éthique -------------------------------
    {"id": "insider", "category": "ethique", "min_grade": 2, "weight": 3,
     "title": "Tuyau confidentiel",
     "scenario": "Un client laisse échapper une information non publique sur une cible "
                 "avant l'annonce d'un deal. L'exploiter serait très rentable… et illégal.",
     "options": [
         {"label": "Exploiter l'information", "cash_k": 60, "rep": 3, "heat": 35,
          "outcome": "Gain rapide encaissé. Mais un tel délit d'initié laisse des traces."},
         {"label": "Ignorer poliment", "cash_k": 0, "rep": 0, "heat": 0,
          "outcome": "Vous restez dans les clous. Aucune conséquence."},
         {"label": "Signaler à la conformité", "cash_k": 0, "rep": 6, "heat": -10,
          "outcome": "Votre intégrité est remarquée. La conformité vous fait confiance."},
     ]},
    {"id": "missell", "category": "ethique", "min_grade": 1, "weight": 3,
     "title": "Produit limite",
     "scenario": "Un produit structuré complexe et peu adapté rapporterait une grosse "
                 "commission s'il était vendu à un client peu averti.",
     "options": [
         {"label": "Le vendre quand même", "cash_k": 40, "rep": -2, "heat": 25,
          "outcome": "Commission empochée. Le client risque de déchanter…"},
         {"label": "Proposer une solution adaptée", "cash_k": 12, "rep": 5, "heat": -5,
          "outcome": "Moins de commission, mais un client fidèle et confiant."},
     ]},
    {"id": "window", "category": "ethique", "min_grade": 3, "weight": 2,
     "title": "Habillage de bilan",
     "scenario": "À deux jours de la clôture trimestrielle, maquiller temporairement le "
                 "book embellirait vos chiffres devant le comité.",
     "options": [
         {"label": "Habiller les chiffres", "cash_k": 0, "rep": 4, "heat": 30,
          "outcome": "Le comité est impressionné… tant que personne ne regarde de près."},
         {"label": "Présenter les chiffres réels", "cash_k": 0, "rep": 1, "heat": -5,
          "outcome": "Transparence assumée. Le comité apprécie l'honnêteté."},
     ]},
    # ---------------------------- réglementaire ----------------------------
    {"id": "riskalert", "category": "reglementaire", "min_grade": 2, "weight": 3,
     "title": "Alerte du risk management",
     "scenario": "Le risk management signale une position trop exposée. La couper coûte, "
                 "mais la garder pourrait amplifier de futures pertes.",
     "options": [
         {"label": "Ignorer l'alerte, garder la position", "cash_k": 20, "rep": 0, "heat": 25,
          "outcome": "Vous pariez sur la chance. Le risk management note votre refus."},
         {"label": "Couvrir la position", "cash_k": -10, "rep": 3, "heat": -8,
          "outcome": "Exposition réduite. Prudence saluée."},
     ]},
    {"id": "conflict", "category": "reglementaire", "min_grade": 4, "weight": 2,
     "title": "Conflit d'intérêts",
     "scenario": "Vous conseillez deux parties aux intérêts opposés sur une même opération. "
                 "Le divulguer pourrait faire capoter une commission.",
     "options": [
         {"label": "Divulguer le conflit", "cash_k": -8, "rep": 6, "heat": -10,
          "outcome": "Déontologie respectée. Réputation renforcée auprès du régulateur."},
         {"label": "Garder le silence", "cash_k": 35, "rep": 0, "heat": 30,
          "outcome": "La commission est sauvée… au prix d'un risque réglementaire réel."},
     ]},
    {"id": "aggressive", "category": "reglementaire", "min_grade": 5, "weight": 2,
     "title": "Pression sur un deal agressif",
     "scenario": "La direction pousse pour une structuration très agressive d'un deal, "
                 "à la limite des règles. Plus de levier, plus de risque.",
     "options": [
         {"label": "Forcer la structuration agressive", "cash_k": 80, "rep": 4, "heat": 28,
          "outcome": "Deal bouclé en force. Spectaculaire, mais surveillé de près."},
         {"label": "Structurer prudemment", "cash_k": 30, "rep": 3, "heat": -5,
          "outcome": "Deal solide et défendable. La direction râle un peu."},
     ]},
    # ------------------------------ stratégie ------------------------------
    {"id": "mandate", "category": "strategie", "min_grade": 3, "weight": 3,
     "title": "Mandat prestigieux mais chronophage",
     "scenario": "Un mandat très visible se présente. Il accaparera vos équipes mais "
                 "rehausserait fortement votre stature.",
     "options": [
         {"label": "Accepter le mandat", "cash_k": 55, "rep": 7, "heat": 5,
          "outcome": "Mandat décroché. Beaucoup de pression, mais quelle vitrine !"},
         {"label": "Décliner pour rester concentré", "cash_k": 0, "rep": -1, "heat": 0,
          "outcome": "Vous gardez vos forces, mais l'occasion file chez un rival."},
     ]},
    {"id": "poach", "category": "strategie", "min_grade": 6, "weight": 2,
     "title": "Débaucher un talent rival",
     "scenario": "Un analyste star d'un concurrent est prêt à vous rejoindre — moyennant "
                 "un package coûteux. Cela affaiblirait un rival.",
     "options": [
         {"label": "Le recruter", "cash_k": -40, "rep": 5, "heat": 5,
          "outcome": "Recrue de choix. Votre desk monte en puissance, un rival fulmine."},
         {"label": "Laisser tomber", "cash_k": 0, "rep": 0, "heat": 0,
          "outcome": "Vous préservez votre budget. Le talent reste chez le concurrent."},
     ]},
    # ------------------------------ signature ------------------------------
    {"id": "megamerger", "category": "signature", "min_grade": 8, "weight": 2,
     "title": "Méga-fusion transformative",
     "scenario": "On vous confie une fusion qui redessinerait tout un secteur. Réussite "
                 "historique possible — ou fiasco retentissant.",
     "options": [
         {"label": "Mener la méga-fusion", "cash_k": 220, "rep": 12, "heat": 18,
          "outcome": "Opération du siècle bouclée. Votre nom circule dans toute la place."},
         {"label": "Confier à plus expérimenté", "cash_k": 20, "rep": -2, "heat": 0,
          "outcome": "Choix prudent. L'Histoire retiendra un autre nom."},
     ]},
    {"id": "bailout", "category": "signature", "min_grade": 6, "weight": 2,
     "title": "Sauver la firme",
     "scenario": "En pleine tempête, injecter votre capital personnel stabiliserait la "
                 "firme et marquerait les esprits — au prix d'un lourd sacrifice immédiat.",
     "options": [
         {"label": "Injecter mon capital", "cash_k": -120, "rep": 14, "heat": -10,
          "outcome": "Geste fort et remarqué. La firme tient, votre légende grandit."},
         {"label": "Préserver mes liquidités", "cash_k": 0, "rep": -6, "heat": 5,
          "outcome": "Vous protégez votre cash. Certains n'oublieront pas votre retrait."},
     ]},
    {"id": "frontrun", "category": "ethique", "min_grade": 3, "weight": 2,
     "title": "Front-running",
     "scenario": "Vous connaissez un gros ordre client à venir. Vous positionner avant "
                 "serait lucratif… et constitue un abus de marché.",
     "options": [
         {"label": "Se positionner avant le client", "cash_k": 55, "rep": 1, "heat": 33,
          "outcome": "Profit immédiat, mais le front-running est lourdement sanctionné s'il est détecté."},
         {"label": "Exécuter l'ordre client d'abord", "cash_k": 6, "rep": 4, "heat": -6,
          "outcome": "Vous respectez la priorité du client. Confiance renforcée."},
     ]},
    {"id": "expenses", "category": "ethique", "min_grade": 1, "weight": 2,
     "title": "Notes de frais",
     "scenario": "Vous pourriez gonfler vos notes de frais d'un dîner « client » privé.",
     "options": [
         {"label": "Gonfler les frais", "cash_k": 8, "rep": -1, "heat": 12,
          "outcome": "Petit gain, mais l'audit interne veille."},
         {"label": "Rester honnête", "cash_k": 0, "rep": 2, "heat": -3,
          "outcome": "Intégrité au quotidien. Rien à signaler."},
     ]},
    {"id": "layoffs", "category": "strategie", "min_grade": 8, "weight": 2,
     "title": "Restructuration du desk",
     "scenario": "Réduire les effectifs de votre desk améliorerait la rentabilité à court "
                 "terme, au prix du moral et de talents perdus.",
     "options": [
         {"label": "Licencier pour la marge", "cash_k": 70, "rep": -5, "heat": 6,
          "outcome": "Coûts réduits, mais l'équipe est ébranlée et des talents partent."},
         {"label": "Préserver l'équipe", "cash_k": -10, "rep": 5, "heat": 0,
          "outcome": "Vous protégez vos gens. Loyauté et stabilité préservées."},
     ]},
    {"id": "greenwash", "category": "reglementaire", "min_grade": 5, "weight": 2,
     "title": "Étiquette « ESG »",
     "scenario": "Labelliser un fonds « durable » sans le justifier vraiment attirerait des "
                 "capitaux — c'est du greenwashing.",
     "options": [
         {"label": "Apposer l'étiquette ESG", "cash_k": 50, "rep": 2, "heat": 26,
          "outcome": "Collecte dopée, mais le régulateur traque le greenwashing."},
         {"label": "Étiqueter honnêtement", "cash_k": 10, "rep": 4, "heat": -5,
          "outcome": "Communication sincère. Moins de collecte, plus de crédibilité."},
     ]},
    {"id": "whistle", "category": "signature", "min_grade": 9, "weight": 2,
     "title": "Fraude interne découverte",
     "scenario": "Vous découvrez une fraude orchestrée par un associé influent. La dénoncer "
                 "est courageux mais coûteux ; la couvrir, lucratif et dangereux.",
     "options": [
         {"label": "Dénoncer la fraude", "cash_k": -30, "rep": 15, "heat": -25,
          "outcome": "Vous assainissez la firme. Intégrité saluée au plus haut niveau."},
         {"label": "Couvrir et profiter", "cash_k": 90, "rep": -4, "heat": 45,
          "outcome": "Argent facile, mais vous êtes désormais complice. Très risqué."},
     ]},
]


# ---- accès localisé (FR / EN) ----------------------------------------------
from data.dilemmas_en import DILEMMAS_EN


def _localize_dilemma(d):
    e = DILEMMAS_EN.get(d["id"])
    if not e:
        return d
    out = dict(d)
    out["title"] = e.get("title", d["title"])
    out["scenario"] = e.get("scenario", d["scenario"])
    options = []
    for i, o in enumerate(d["options"]):
        eo = e.get("options", [])
        eo = eo[i] if i < len(eo) else {}
        no = dict(o)
        no["label"] = eo.get("label", o["label"])
        no["outcome"] = eo.get("outcome", o["outcome"])
        options.append(no)
    out["options"] = options
    return out


def localized(lang):
    """Renvoie la liste de dilemmes dans la langue demandée."""
    if lang == "en":
        return [_localize_dilemma(d) for d in DILEMMAS]
    return DILEMMAS


def _scale(grade_index):
    return 1.0 + 0.5 * grade_index


def eligible(player):
    from core.i18n import get_lang
    pool = localized(get_lang())
    return [d for d in pool if d["min_grade"] <= player.grade_index]


def generate(player, rng=None, category=None):
    """Crée une instance de dilemme avec montants mis à l'échelle du grade."""
    rng = rng or random
    pool = eligible(player)
    if category:
        pool = [d for d in pool if d["category"] == category] or pool
    if not pool:
        return None
    tmpl = rng.choices(pool, weights=[d["weight"] for d in pool], k=1)[0]
    scale = _scale(player.grade_index)
    options = []
    for o in tmpl["options"]:
        options.append({
            "label": o["label"],
            "cash": round(o["cash_k"] * 1000 * scale, 2),
            "rep": o["rep"], "heat": o["heat"], "outcome": o["outcome"],
        })
    return {"id": tmpl["id"], "category": tmpl["category"], "title": tmpl["title"],
            "scenario": tmpl["scenario"], "options": options}


def maybe_trigger(player, rng=None, base_prob=0.10):
    """Déclenche éventuellement un dilemme (rien si un est déjà en attente)."""
    rng = rng or random
    if player.pending_dilemmas:
        return None
    if rng.random() > base_prob:
        return None
    d = generate(player, rng)
    if d:
        player.pending_dilemmas.append(d)
    return d


def apply_choice(player, dilemma, option_index):
    """Applique l'option choisie. Retourne l'option (avec son issue)."""
    from core import archetypes
    opt = dilemma["options"][option_index]
    player.adjust_cash(opt["cash"])
    player.adjust_reputation(opt["rep"])
    heat_delta = opt["heat"]
    if heat_delta > 0:
        heat_delta *= archetypes.perk(player, "heat_gain_mult")
    player.heat = max(0, min(100, player.heat + heat_delta))
    # retire le dilemme de la file
    player.pending_dilemmas = [d for d in player.pending_dilemmas
                               if d.get("id") != dilemma.get("id")]
    # trace
    player.decisions_log.append({"day": player.day, "title": dilemma["title"],
                                 "choice": opt["label"]})
    from core import career
    tag = "§" if dilemma["category"] in ("ethique", "reglementaire") else "✶"
    bits = []
    if opt["cash"]:
        bits.append(f"{'+' if opt['cash'] >= 0 else ''}{opt['cash']:.0f}")
    if opt["rep"]:
        bits.append(f"rép. {opt['rep']:+d}")
    if heat_delta:
        bits.append(f"scrutin {heat_delta:+.0f}")
    detail = f" ({', '.join(bits)})" if bits else ""
    career.log(player, "info", f"{tag} {dilemma['title']} → {opt['label']}{detail}")
    return opt


def maybe_investigate(player, rng=None):
    """Décroissance du scrutin + risque d'enquête réglementaire si heat élevé.
    Retourne un dict d'enquête (avec amende appliquée) ou None."""
    rng = rng or random
    if player.heat > 0:
        player.heat = max(0, player.heat - 1)
    if player.heat < 55:
        return None
    prob = (player.heat - 45) / 120.0
    if rng.random() >= prob:
        return None
    heat_before = player.heat
    scale = _scale(player.grade_index)
    fine = round(rng.uniform(40, 120) * 1000 * scale, 2)
    rep_loss = rng.randint(6, 12)
    player.adjust_cash(-fine)
    player.adjust_reputation(-rep_loss)
    player.heat = max(0, player.heat - 35)
    from core import career, inbox
    career.log(player, "crisis", f"Enquête réglementaire : scrutin {heat_before}/100 (seuil 55) "
                                  f"a déclenché un contrôle. Amende {fine/1000:.0f}K, "
                                  f"réputation -{rep_loss}.")
    inbox.push(player, "compliance", "Régulateur",
               "Enquête et sanction",
               f"Votre scrutin réglementaire a atteint {heat_before}/100, au-delà du seuil "
               f"de tolérance (55) — accumulé par vos décisions récentes les plus risquées. "
               f"Une enquête conclut à des manquements. Amende de {fine/1000:.0f}K et "
               f"atteinte à votre réputation (-{rep_loss}). Réduisez votre exposition au risque réglementaire.")
    return {"fine": fine, "rep_loss": rep_loss, "heat_before": heat_before}
