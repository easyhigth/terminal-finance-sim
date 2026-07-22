"""
scene_terminal_career.py — Commandes de carrière/progression du terminal
(TerminalCareerMixin) : triches, crises sandbox, examen, mandats, légende,
archétype, tension, deals, badges. Extrait de scene_terminal_commands.py pour
limiter sa taille ; mixé dans TerminalScene avec les autres mixins de commandes.
"""

from core import archetypes as archetypes_mod
from core import audio, config
from core import badges as badges_mod
from core import career as career_mod
from core import deals as deals_mod
from core import legacy as legacy_mod
from core import ma as ma_mod
from core import mandates as mandates_mod
from core import market as market_mod
from core import rivals as rivals_mod
from core import scenarios as scenarios_mod
from core import tracks as tracks_mod
from core.i18n import get_lang
from ui import widgets


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante (logs de la console)."""
    return en if get_lang() == "en" else fr


class TerminalCareerMixin:
    def _cmd_cheat(self, cmd, args):
        """Commandes de TEST (mode triche, via main_cheat.py)."""
        p = self.app.gs.player
        if cmd in ("CHEAT", "CHEATS"):
            self._log(_L("  ⊕ TRICHE : GRADE <0-11> · CASH <montant> · REP <0-100> · MAXUNLOCK","  ⊕ CHEAT: GRADE <0-11> · CASH <amount> · REP <0-100> · MAXUNLOCK"))
            self._log(_L("  Grades : ","  Grades: ") + " ".join(f"{i}={g}" for i, g in enumerate(config.GRADES)))
            return
        if cmd == "GRADE":
            if not args or not args[0].lstrip("-").isdigit():
                self._log(_L("  Usage : GRADE <0-11>  (voir CHEAT pour la liste).","  Usage: GRADE <0-11>  (see CHEAT for the list)."))
                return
            gi = max(0, min(len(config.GRADES) - 1, int(args[0])))
            p.grade_index = gi
            p.grade_deals = 0
            p.grade_missions = 0
            p.grade_start_quarter = p.quarter
            if gi >= 2 and p.track == "General":
                p.flags["can_choose_track"] = True
            self._log(_L(f"  ⊕ Grade réglé sur {gi} = {config.GRADES[gi]}.", f"  ⊕ Grade set to {gi} = {config.GRADES[gi]}."))
            self._check_badges()
        elif cmd == "CASH":
            if not args or not args[0].lstrip("-").replace(".", "").isdigit():
                self._log(_L("  Usage : CASH <montant>.","  Usage: CASH <amount>."))
                return
            p.cash = float(args[0])
            self._log(_L(f"  ⊕ Trésorerie réglée sur {widgets.format_money(p.cash, self._cur())}.", f"  ⊕ Cash set to {widgets.format_money(p.cash, self._cur())}."))
        elif cmd in ("REP", "REPUTATION"):
            if not args or not args[0].lstrip("-").isdigit():
                self._log(_L("  Usage : REP <0-100>.","  Usage: REP <0-100>."))
                return
            p.reputation = max(0, min(100, int(args[0])))
            self._log(_L(f"  ⊕ Réputation réglée sur {p.reputation}/100.", f"  ⊕ Reputation set to {p.reputation}/100."))
        elif cmd == "MAXUNLOCK":
            p.grade_index = len(config.GRADES) - 1
            p.reputation = max(p.reputation, 80)
            if p.track == "General":
                p.flags["can_choose_track"] = True
            self._log(_L(f"  ⊕ Grade max ({config.GRADES[-1]}) : toutes les actions débloquées.", f"  ⊕ Top grade ({config.GRADES[-1]}): all actions unlocked."))
            self._check_badges()

    def _cmd_reclaim(self, args):
        """RECLAIM : liste les cibles M&A raflées par un rival (act(), branche
        claim_target) et donc contestables. RECLAIM <ticker> : tente une
        contre-offre (frais non remboursés en cas d'échec, succès non garanti)."""
        p = self.app.gs.player
        targets = rivals_mod.contestable_targets(p)
        if not args:
            if not targets:
                self._log(_L("  Aucune cible M&A contestable pour le moment.",
                             "  No contestable M&A target right now."))
                return
            rows = [((t["ticker"], config.COL_AMBER), t["name"],
                     widgets.format_money(ma_mod.ask_price(t) * rivals_mod.CONTEST_COST_PCT, self._cur()))
                    for t in targets]
            self._open_window(_L("CIBLES CONTESTABLES", "CONTESTABLE TARGETS"),
                              [("Tk", 60), ("Nom", 160), (_L("Frais", "Fee"), 120)], rows)
            self._log(_L("  RECLAIM <ticker> pour tenter une contre-offre.",
                         "  RECLAIM <ticker> to attempt a counter-bid."))
            return
        ticker = args[0].upper()
        res = rivals_mod.contest_target(p, ticker)
        if not res["ok"]:
            reasons = {
                "not_claimed": _L("  Cette cible n'est pas détenue par un rival.",
                                  "  This target isn't held by a rival."),
                "target": _L("  Cible inconnue.", "  Unknown target."),
                "cash": _L(f"  Trésorerie insuffisante (frais : {widgets.format_money(res.get('cost', 0), self._cur())}).",
                           f"  Insufficient cash (fee: {widgets.format_money(res.get('cost', 0), self._cur())})."),
            }
            self._log(reasons.get(res["reason"], _L("  Échec.", "  Failed.")))
            return
        if res["success"]:
            self._log(_L(
                f"  ✓ Contre-offre réussie : {res['target']} reprise sur {res['rival']} "
                f"(frais {widgets.format_money(res['cost'], self._cur())}).",
                f"  ✓ Counter-bid succeeded: {res['target']} reclaimed from {res['rival']} "
                f"(fee {widgets.format_money(res['cost'], self._cur())})."))
        else:
            self._log(_L(
                f"  ✗ Contre-offre échouée face à {res['rival']} sur {res['target']} "
                f"(frais perdus : {widgets.format_money(res['cost'], self._cur())}).",
                f"  ✗ Counter-bid failed against {res['rival']} on {res['target']} "
                f"(fee lost: {widgets.format_money(res['cost'], self._cur())})."))

    def _cmd_reconvert(self, args):
        """RECONVERT <voie> : change de voie de spécialisation après le choix
        initial (gratuit, via TRACK), contre un coût cash (% de la valeur
        nette) et une période de rodage pendant laquelle les avantages de la
        nouvelle voie montent en puissance progressivement."""
        p = self.app.gs.player
        names = [n for n in tracks_mod.PERKS if n != "General"]
        if p.track == "General":
            self._log(_L("  Vous n'avez pas encore choisi de voie : utilisez TRACK.",
                         "  You haven't chosen a track yet: use TRACK."))
            return
        if p.grade_index < tracks_mod.TOP_GRADE_INDEX:
            self._log(_L(
                f"  Voie verrouillée : la reconversion redevient libre et gratuite "
                f"au grade {config.GRADES[tracks_mod.TOP_GRADE_INDEX]} (vous : {p.grade}).",
                f"  Track locked: switching becomes free at grade "
                f"{config.GRADES[tracks_mod.TOP_GRADE_INDEX]} (you: {p.grade})."))
            return
        if not args:
            cost = tracks_mod.reconversion_cost(p, self.market)
            self._log(_L(
                f"  Usage : RECONVERT <voie>  (voies : {', '.join(names)}).",
                f"  Usage: RECONVERT <track>  (tracks: {', '.join(names)})."))
            self._log(_L(
                f"  Grade max atteint : reconversion libre, gratuite et instantanée "
                f"(coût actuel : {widgets.format_money(cost, self._cur())}).",
                f"  Top grade reached: free, instant track switch "
                f"(current cost: {widgets.format_money(cost, self._cur())})."))
            return
        target = next((n for n in names if n.upper() == args[0].upper()), None)
        if not target:
            self._log(_L(f"  Voie inconnue. Voies : {', '.join(names)}.",
                         f"  Unknown track. Tracks: {', '.join(names)}."))
            return
        res = tracks_mod.switch_track(p, self.market, target)
        if not res["ok"]:
            reasons = {
                "same_track": _L("  Vous êtes déjà sur cette voie.",
                                  "  You are already on that track."),
                "cash": _L(f"  Trésorerie insuffisante (coût : {widgets.format_money(res.get('cost', 0), self._cur())}).",
                           f"  Insufficient cash (cost: {widgets.format_money(res.get('cost', 0), self._cur())})."),
                "locked_until_top_grade": _L(
                    f"  Voie verrouillée jusqu'au grade {config.GRADES[tracks_mod.TOP_GRADE_INDEX]}.",
                    f"  Track locked until grade {config.GRADES[tracks_mod.TOP_GRADE_INDEX]}."),
            }
            self._log(reasons.get(res["reason"], _L("  Échec.", "  Failed.")))
            return
        if res["ramp_days"] > 0:
            self._log(_L(
                f"  ⊕ Reconversion vers {target} : -{widgets.format_money(res['cost'], self._cur())}, "
                f"rodage {res['ramp_days']}j avant pleine efficacité des avantages.",
                f"  ⊕ Switched to {target}: -{widgets.format_money(res['cost'], self._cur())}, "
                f"{res['ramp_days']}d break-in before full perk strength."))
        else:
            self._log(_L(
                f"  ⊕ Reconversion libre vers {target} : gratuite, pleinement effective immédiatement.",
                f"  ⊕ Free switch to {target}: no cost, fully effective immediately."))
        career_mod.log(p, "info", _L(f"Reconversion vers la voie {target}", f"Switched to {target} track"))
        self.app.notify(_L(f"Reconversion : {target}", f"Track switch: {target}"), "info")

    def _cmd_crisis(self, args):
        """Déclenche un scénario de crise/stress test ad hoc — mode bac à sable
        uniquement (sandbox=True), pour ne jamais perturber une partie normale."""
        p = self.app.gs.player
        if not getattr(p, "sandbox", False):
            self._log(_L("  CRISIS n'est disponible qu'en mode bac à sable.",
                         "  CRISIS is only available in sandbox mode."))
            return
        if not args:
            self._log(_L("  Usage : CRISIS <id> [sévérité]  — scénarios disponibles :",
                         "  Usage: CRISIS <id> [severity]  — available scenarios:"))
            for s in scenarios_mod.SCENARIOS:
                self._log(f"   {s['id']:<18} {s['name']}")
            return
        scenario_id = args[0].lower()
        severity = 1.0
        if len(args) > 1:
            try:
                severity = float(args[1])
            except ValueError:
                self._log(_L(f"  Sévérité invalide : {args[1]}.", f"  Invalid severity: {args[1]}."))
                return
        result = scenarios_mod.trigger_by_id(self.market, scenario_id, severity)
        if result is None:
            self._log(_L(f"  Scénario inconnu : {scenario_id}. Tapez CRISIS sans argument pour la liste.",
                         f"  Unknown scenario: {scenario_id}. Type CRISIS with no argument for the list."))
            return
        self._log(_L(f"  ⊕ Crise déclenchée : {result['name']} (sévérité {result['severity']:.2f}).",
                     f"  ⊕ Crisis triggered: {result['name']} (severity {result['severity']:.2f})."))
        self._log("  " + result["story"])

    def _cmd_eval(self):
        """Ouvre l'examen si TOUS les critères de promotion sont remplis."""
        p = self.app.gs.player
        p.flags["onboarding_seen_eval"] = True
        # un examen mis en pause se reprend directement (peu importe les critères)
        if isinstance(p.eval_state, dict) and p.eval_state.get("mode") == "promotion" \
                and p.eval_state.get("items"):
            self._log(_L("  Reprise de l'examen en pause…","  Resuming the paused exam…"))
            self.app.scenes.go("evaluation")
            return
        if not p.can_promote():
            self._log(_L("  Vous êtes au grade maximal : aucune promotion possible.","  You are at the top grade: no promotion possible."))
            return
        if not career_mod.promotion_ready(p):
            self._log(_L("  Critères de promotion non remplis :","  Promotion criteria not met:"))
            for r in career_mod.promotion_requirements(p):
                if not r["met"]:
                    self._log(_L(f"   ○ {r['label']} : {int(r['current'])}/{int(r['target'])}", f"   ○ {r['label']}: {int(r['current'])}/{int(r['target'])}"))
            self._log(_L("  Voir CAREER pour la roadmap complète.","  See CAREER for the full roadmap."))
            return
        self.app.scenes.go("evaluation")

    # ------------------------------------------------------------- mandats
    def _cmd_mandates(self):
        self.app.scenes.go("mandates", return_to="terminal")

    def _cmd_mandate(self, args):
        p = self.app.gs.player
        if len(args) < 2 or not args[1].isdigit():
            self._log(_L("  Usage : MANDATE ACCEPT|DECLINE <id>","  Usage: MANDATE ACCEPT|DECLINE <id>"))
            return
        op, mid = args[0].upper(), int(args[1])
        if op in ("ACCEPT", "ACCEPTER"):
            res = mandates_mod.accept(p, mid, self.market)
            if res == "full":
                self._log(_L(f"  Déjà {mandates_mod.MAX_ACTIVE} mandats en cours.", f"  Already {mandates_mod.MAX_ACTIVE} active mandates."))
            elif res:
                profile_txt = f" ({mandates_mod.profile_label(res['client_profile'])})" if res.get("client_profile") else ""
                self._log(_L(f"  ✓ Mandat #{mid} accepté : {res['client']}{profile_txt} — objectif "
                          f"+{res['target_pct']:.0f}% en {res['horizon']}T, bêta ≤ {res['max_beta']:.2f}.",
                          f"  ✓ Mandate #{mid} accepted: {res['client']}{profile_txt} — target "
                          f"+{res['target_pct']:.0f}% in {res['horizon']}Q, beta ≤ {res['max_beta']:.2f}."))
                career_mod.log(p, "deal", _L(f"Mandat accepté : {res['client']}", f"Mandate accepted: {res['client']}"))
            else:
                self._log(_L(f"  Offre #{mid} introuvable.", f"  Offer #{mid} not found."))
        elif op in ("DECLINE", "REFUSER"):
            self._log(_L("  Offre déclinée.","  Offer declined.") if mandates_mod.decline(p, mid)
                      else _L(f"  Offre #{mid} introuvable.", f"  Offer #{mid} not found."))
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    def _cmd_legacy(self):
        """Affiche l'avancement des 5 objectifs de légende (ambitions de carrière)."""
        p = self.app.gs.player
        rows = []
        for g in legacy_mod.all_goals():
            done = g["id"] in p.legacy
            cur, target = g["progress"](p, self.market)
            status = _L("✓ ATTEINT", "✓ ACHIEVED") if done else f"{min(cur, target)}/{target}"
            col = config.COL_UP if done else config.COL_TEXT
            rows.append(((legacy_mod.goal_name(g), config.COL_PRESTIGE), legacy_mod.goal_desc(g), (status, col)))
        self._open_window(_L("OBJECTIFS DE LÉGENDE", "LEGACY GOALS"),
                          [(_L("Objectif", "Goal"), 180), (_L("Description", "Description"), 420),
                           (_L("Avancement", "Progress"), 110)],
                          rows, accent=config.COL_PRESTIGE)

    def _cmd_archetype(self):
        """Affiche l'archétype de run du joueur (philosophie de jeu choisie au
        départ) et le détail de ses avantages/coûts mécaniques."""
        p = self.app.gs.player
        arch = archetypes_mod.get(p.archetype)
        if arch is None:
            self._log(_L("  Aucun archétype (parties créées avant cette mise à jour).",
                          "  No archetype (game started before this update)."))
            return
        self._log(f"  {arch['name']} — {arch['tagline']}")
        rows = []
        for key, label, direction in archetypes_mod.PERK_INFO:
            value = archetypes_mod.perk(p, key)
            default = archetypes_mod._DEFAULTS.get(key)
            if value == default:
                continue
            additive = key == "deal_success_bonus"
            shown = f"{value*100:+.0f}%" if additive else f"x{value:.2f}"
            better = (value > default) if direction == "higher" else (value < default)
            col = config.COL_UP if better else config.COL_DOWN
            rows.append((label, (shown, col)))
        self._open_window(_L(f"ARCHÉTYPE : {arch['name']}", f"ARCHETYPE: {arch['name']}"),
                          [("Effet", 280), ("Valeur", 110)],
                          rows, accent=config.COL_AMBER)

    def _cmd_tension(self):
        """Affiche l'arc de tension courant : phase qualitative (Calme/Préparation/
        Tension/Panique/Accalmie), niveau 0-100, régime, et crises actives avec
        leur temps restant — pour que le joueur lise le rythme de la partie plutôt
        que de subir des chocs sans contexte."""
        m = self.market
        phase = m.tension_phase()
        lvl = m.tension_level()
        phase_col = {"Calme": config.COL_UP, "Préparation": config.COL_AMBER,
                     "Tension": config.COL_DOWN, "Panique": config.COL_DOWN,
                     "Accalmie": config.COL_UP}.get(phase, config.COL_TEXT)
        self._log(_L(f"  Phase : {phase} (tension {lvl:.0f}/100) — régime {m.regime_label()}.",
                      f"  Phase: {phase} (tension {lvl:.0f}/100) — regime {m.regime_label()}."))
        rows = [((phase, phase_col), f"{lvl:.0f}/100", m.regime_label())]
        for cr in m.crises:
            rows.append((cr.name, f"{cr.steps_left}/{cr.total_steps}",
                         (_L("majeure", "major") if cr.severity >= market_mod.CRISIS_SEVERE_SEVERITY
                          else _L("modérée", "moderate"))))
        if not m.crises:
            rows.append((_L("(aucune crise active)", "(no active crisis)"), "", ""))
        self._open_window(_L("TENSION DU MARCHÉ", "MARKET TENSION"),
                          [(_L("Phase / crise", "Phase / crisis"), 220),
                           (_L("Niveau / pas restants", "Level / steps left"), 140),
                           (_L("Régime / sévérité", "Regime / severity"), 120)],
                          rows, accent=config.COL_AMBER)

    def _check_badges(self):
        """Attribue les nouveaux badges et notifie (toast + journal)."""
        new_badges = badges_mod.check_new(self.app.gs.player, self.market)
        for b in new_badges:
            bname = badges_mod.badge_name(b)
            self.app.notify(_L(f"✶ Badge : {bname}", f"✶ Badge: {bname}"), "prestige")
            career_mod.log(self.app.gs.player, "info", _L(f"Badge débloqué : {bname}", f"Badge unlocked: {bname}"))
        earned, revoked = badges_mod.check_streaks(self.app.gs.player)
        if new_badges or earned:
            audio.play("badge")
        for b in earned:
            bname = badges_mod.streak_badge_name(b)
            self.app.notify(_L(f"✶ Badge à enjeu : {bname}", f"✶ Streak badge: {bname}"), "prestige")
            career_mod.log(self.app.gs.player, "info", _L(f"Badge à enjeu débloqué : {bname}", f"Streak badge unlocked: {bname}"))
        for b in revoked:
            bname = badges_mod.streak_badge_name(b)
            self.app.notify(_L(f"✕ Badge perdu : {bname}", f"✕ Badge lost: {bname}"), "bad")
            career_mod.log(self.app.gs.player, "info", _L(f"Badge à enjeu révoqué : {bname}", f"Streak badge revoked: {bname}"))
        self._check_legacy()

    def _check_legacy(self):
        """Attribue les objectifs de légende nouvellement atteints et notifie
        (toast renforcé + journal) : ce sont les ambitions de carrière, pas de
        simples jalons."""
        for g in legacy_mod.check_new(self.app.gs.player, self.market):
            self.app.notify(_L(f"✶ OBJECTIF DE LÉGENDE : {g['name']}", f"✶ LEGEND OBJECTIVE: {g['name']}"), "prestige")
            career_mod.log(self.app.gs.player, "info", _L(f"Objectif de légende atteint : {g['name']}", f"Legend objective reached: {g['name']}"))

    def _cmd_pitch(self):
        """PITCH : démarche un client pour décrocher un mandat (selon réputation)."""
        import random
        p = self.app.gs.player
        prob = 0.3 + 0.5 * (p.reputation / 100.0)
        if random.random() < prob:
            d = deals_mod.maybe_generate(p)
            if d:
                self._log(_L(f"  ✓ Pitch réussi : nouveau mandat #{d[0]['id']} — {d[0]['title']}.", f"  ✓ Pitch won: new mandate #{d[0]['id']} — {d[0]['title']}."))
            else:
                self._log(_L("  ✓ Pitch réussi, mais votre pipeline de deals est déjà plein.","  ✓ Pitch won, but your deal pipeline is already full."))
        else:
            p.adjust_reputation(-1, reason=_L("Pitch infructueux", "Pitch failed"))
            self._log(_L("  ✗ Pitch infructueux. Le client passe son tour (-1 réputation).","  ✗ Pitch failed. The client passes (-1 reputation)."))
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

    def _cmd_deals(self):
        self.app.scenes.go("deals", return_to="terminal")

    def _cmd_deal(self, arg):
        p = self.app.gs.player
        if arg is None or not arg.isdigit():
            self._log(_L("  Usage : DEAL <id>  (voir DEALS).","  Usage: DEAL <id>  (see DEALS)."))
            return
        if deals_mod.find_deal(p, int(arg)) is None:
            self._log(_L(f"  Deal #{arg} introuvable.", f"  Deal #{arg} not found."))
            return
        # mini-jeu : vraie décision financière (au lieu d'une résolution au dé)
        self.app.scenes.go("deal", deal_id=int(arg), return_to="terminal")
