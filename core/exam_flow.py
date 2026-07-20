"""
exam_flow.py — Logique PURE d'un examen (promotion OU certification), partagée
par la scène plein écran (`scenes/scene_evaluation.py`) et l'app native en
fenêtre (`apps/app_evaluation.py`).

Ces deux écrans ne diffèrent que par le RENDU (plein écran vs fenêtre) et le
cycle de vie ; toute la logique métier était dupliquée à l'identique — donc à
maintenir en double (le registre anti-répétition des questions, par exemple, a
dû être câblé des deux côtés). Elle vit désormais ICI, une seule fois :

  - `serve(...)`   : tire les questions de l'examen (un seul point de tirage,
                     branché sur le registre des questions déjà vues) et rend
                     (items, seuil de réussite, grade/intitulé visé).
  - `apply_result` : applique le RÉSULTAT (marque les questions vues, promotion
                     ou passage de niveau de certif, déblocages, inbox, journal,
                     sauvegarde) et RETOURNE les toasts à afficher — l'UI n'a
                     plus qu'à les jouer et dessiner le récap.

Aucun import pygame : `apply_result` renvoie les notifications au lieu de les
émettre, pour que la logique reste testable sans écran.
"""
from core import config
from core.i18n import get_lang


def _L(fr, en):
    return en if get_lang() == "en" else fr


def serve(player, mode="promotion", cert_program=None, cert_level=0, tier=None, avoid=None):
    """Sert un examen : (items, pass_threshold, target_grade).

    `avoid` : identités des questions déjà vues (core/question_log) — par défaut
    celles du joueur, pour ne jamais reposer une question (cf. question_log)."""
    from core import exam
    if avoid is None:
        from core import question_log
        avoid = question_log.seen_set(player)
    if mode == "cert":
        from core import certifications as C
        prog = C.PROGRAMS[cert_program]
        t = tier if tier is not None else prog["tier"]
        items = exam.generate(player.grade_index, difficulty=t, n=C.EXAM_N, avoid=avoid)
        return items, C.PASS_THRESHOLD, f"{prog['name']} niveau {cert_level + 1}"
    target = min(player.grade_index + 1, len(config.GRADES) - 1)
    items = exam.generate(player.grade_index, avoid=avoid)
    return items, exam.PASS_THRESHOLD, config.GRADES[target]


def apply_result(app, mode, items, score, pass_threshold,
                 cert_program=None, cert_level=0):
    """Applique le résultat d'un examen terminé et retourne un dict :
        {"passed", "new_title", "ratio", "toasts": [(texte, kind), ...]}
    Effets de bord : marque les questions vues, efface l'état en pause, fait
    avancer le temps d'un tic, promotion / certif + déblocages + inbox + journal,
    puis sauvegarde. Les toasts sont RENDUS par l'appelant (pas de notify ici)."""
    from core import career, question_log
    p = app.gs.player
    toasts = []
    question_log.mark_seen(p, items)   # questions de cet examen : jamais reposées
    p.eval_state = {}                  # examen terminé : on efface l'état en pause
    app.pending_market_steps += 1      # passer une éval fait avancer le temps d'un tic
    ratio = score / max(1, len(items))
    passed = ratio >= pass_threshold
    new_title = None

    if mode == "cert":
        new_title, ct = _apply_cert(app, p, passed, ratio, pass_threshold, cert_program)
        toasts += ct
        app.gs.save(config.AUTOSAVE_SLOT)
        return {"passed": passed, "new_title": new_title, "ratio": ratio, "toasts": toasts}

    if passed and p.can_promote():
        from core import audio, inbox, profile, unlock_briefs, unlocks
        old_grade_index = p.grade_index
        p.promote()
        audio.play("promotion")
        profile.record_grade_reached(p.grade_index)
        p.reputation = min(100, p.reputation + 8)
        if p.grade_index >= 2 and p.track == "General":
            p.flags["can_choose_track"] = True
        new_title = career.award_promotion(p)
        career.log(p, "promo", f"Promotion : {p.grade}"
                   + (f" — titre « {new_title} »" if new_title else ""))
        inbox.on_promotion(p)
        toasts.append((_L(f"Promotion : {p.grade}", f"Promotion: {p.grade}"), "good"))
        if new_title:
            toasts.append((_L(f"Titre : {new_title}", f"Title: {new_title}"), "prestige"))
        # fonctionnalités devenues accessibles avec CE grade — via le grade
        # EFFECTIF (raccourci vétéran, verrous de voie), pas le palier brut
        new_feats = unlock_briefs.newly_unlocked(p, old_grade_index)
        if new_feats:
            # carte « NOUVEAUTÉS » du bureau : une page détaillée par
            # fonctionnalité, affichée au retour sur le bureau, acquittée d'un clic.
            p.flags["pending_unlock_briefs"] = {"grade": p.grade,
                                                "features": list(new_feats)}
        for feat in new_feats:
            toasts.append((_L(f"⊘→✓ Débloqué : {unlocks.feature_label(feat)}",
                              f"⊘→✓ Unlocked: {unlocks.feature_label(feat)}"), "good"))
            tid = unlocks.FEATURE_TUTORIAL.get(feat)
            if tid and not p.flags.get("pending_tutorial"):
                p.flags["pending_tutorial"] = tid
            # trace persistante (le toast est éphémère) : un mot du manager
            # explique le nouveau périmètre et renvoie vers le tutoriel dédié.
            label = unlocks.feature_label(feat)
            body = (f"Votre promotion au grade {p.grade} ouvre un nouveau "
                    f"périmètre : {label}. Prenez le temps de vous y faire "
                    "la main avant d'engager du capital.")
            if tid:
                body += (" Un tutoriel dédié vous attend (écran TUTORIELS, "
                         "ou l'icône Aide du bureau).")
            inbox.push(p, "manager", "Votre manager",
                       f"Nouveau périmètre : {label}", body)
    else:
        p.reputation = max(0, p.reputation - 5)
        pct = int(ratio * 100)
        req = int(pass_threshold * 100)
        toasts.append((_L(f"Évaluation échouée : {pct}% < {req}% requis (−5 réputation)",
                          f"Evaluation failed: {pct}% < {req}% required (−5 reputation)"), "bad"))
        career.log(p, "promo", _L(
            f"Évaluation de promotion échouée ({pct}% < seuil {req}%, −5 réputation)",
            f"Promotion evaluation failed ({pct}% < threshold {req}%, −5 reputation)"))
    app.gs.save(config.AUTOSAVE_SLOT)
    return {"passed": passed, "new_title": new_title, "ratio": ratio, "toasts": toasts}


def _apply_cert(app, p, passed, ratio, pass_threshold, cert_program):
    """Passage (ou échec) d'un niveau de certification. Retourne
    (new_title, [toasts])."""
    from core import badges, career
    from core import certifications as C
    name = C.PROGRAMS[cert_program]["name"]
    toasts = []
    if passed:
        res = C.pass_stage(p, cert_program)
        new_title = res.get("title") if res else None
        toasts.append((_L(f"{name} : niveau réussi", f"{name}: level passed"), "prestige"))
        for b in badges.check_new(p, app.market):
            bname = badges.badge_name(b)
            toasts.append((_L(f"✶ Badge : {bname}", f"✶ Badge: {bname}"), "prestige"))
        return new_title, toasts
    pct = int(ratio * 100)
    req = int(pass_threshold * 100)
    toasts.append((_L(f"{name} échouée : {pct}% < {req}% requis",
                      f"{name} failed: {pct}% < {req}% required"), "bad"))
    career.log(p, "promo", _L(
        f"Certification {name} échouée ({pct}% < seuil {req}%)",
        f"Certification {name} failed ({pct}% < threshold {req}%)"))
    return None, toasts
