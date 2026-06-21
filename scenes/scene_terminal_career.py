"""
scene_terminal_career.py — Commandes de carrière/progression du terminal
(TerminalCareerMixin) : triches, crises sandbox, examen, mandats, légende,
archétype, tension, deals, badges. Extrait de scene_terminal_commands.py pour
limiter sa taille ; mixé dans TerminalScene avec les autres mixins de commandes.
"""

from core import archetypes as archetypes_mod
from core import badges as badges_mod
from core import career as career_mod
from core import config
from core import deals as deals_mod
from core import legacy as legacy_mod
from core import mandates as mandates_mod
from core import market as market_mod
from core import scenarios as scenarios_mod
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
                career_mod.log(p, "deal", f"Mandat accepté : {res['client']}")
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
            status = "✓ ATTEINT" if done else f"{min(cur, target)}/{target}"
            col = config.COL_UP if done else config.COL_TEXT
            rows.append(((g["name"], config.COL_PRESTIGE), g["desc"], (status, col)))
        self._open_window(_L("OBJECTIFS DE LÉGENDE", "LEGACY GOALS"),
                          [("Objectif", 180), ("Description", 420), ("Avancement", 110)],
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
        for b in badges_mod.check_new(self.app.gs.player, self.market):
            self.app.notify(f"✶ Badge : {b['name']}", "prestige")
            career_mod.log(self.app.gs.player, "info", f"Badge débloqué : {b['name']}")
        self._check_legacy()

    def _check_legacy(self):
        """Attribue les objectifs de légende nouvellement atteints et notifie
        (toast renforcé + journal) : ce sont les ambitions de carrière, pas de
        simples jalons."""
        for g in legacy_mod.check_new(self.app.gs.player, self.market):
            self.app.notify(f"★ OBJECTIF DE LÉGENDE : {g['name']}", "prestige")
            career_mod.log(self.app.gs.player, "info", f"Objectif de légende atteint : {g['name']}")

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
