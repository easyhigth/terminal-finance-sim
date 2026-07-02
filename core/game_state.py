"""
game_state.py — Modèle de données de l'état de jeu et du joueur.
Sérialisable en JSON pour la sauvegarde/chargement.
"""
import json
import os
import time
from dataclasses import asdict, dataclass, field

from core import config
from core.applog import logger


@dataclass
class PlayerState:
    """Toutes les données persistantes du joueur."""
    name: str = "Trainee"
    continent: str = "Europe"
    track: str = "General"          # spécialisation (après Analyst)
    archetype: str = ""             # philosophie de run choisie au départ (core/archetypes.py)
    firm: str = ""                  # ADN de la firme de départ (core/firms.py)
    grade_index: int = 0            # index dans config.GRADES
    reputation: int = 50            # 0–100
    cash: float = 0.0               # capital personnel / de la firme
    firm_name: str = ""             # nom de la boîte si fondée
    day: int = 1                    # temps de jeu en jours
    quarter: int = 1                # trimestre courant
    hardcore: bool = False          # désactive les sauvegardes manuelles
    sandbox: bool = False           # mode bac à sable : aucune sauvegarde, run jetable
    competencies: dict = field(default_factory=dict)  # compétence -> niveau 0-100
    flags: dict = field(default_factory=dict)         # événements/déblocages
    deals: list = field(default_factory=list)         # deals actifs (dicts)
    deals_history: list = field(default_factory=list)  # derniers deals résolus (UI, replay, capé)
    event_log: list = field(default_factory=list)     # historique d'événements récents
    cash_history: list = field(default_factory=list)  # net worth au fil du temps
    next_deal_id: int = 1                              # compteur d'identifiants de deals
    conditional_orders: list = field(default_factory=list)  # stop-loss/take-profit en attente
    next_conditional_order_id: int = 1                  # compteur d'identifiants d'ordres conditionnels
    market_seed: int = 0                               # graine du moteur de marché (0 = non initialisé)
    market_step: int = 0                               # nb de pas de marché écoulés (resync au chargement)
    portfolio: dict = field(default_factory=dict)      # holdings : ticker -> {"shares","avg"}
    bonds: dict = field(default_factory=dict)          # obligations : bond_id -> {"qty","avg"}
    commodities: dict = field(default_factory=dict)    # matières premières : id -> {"qty","avg"}
    crypto: dict = field(default_factory=dict)         # crypto-actifs : id -> {"qty","avg"}
    etfs: dict = field(default_factory=dict)           # ETF (fonds indiciels) : id -> {"qty","avg"}
    structured: list = field(default_factory=list)     # produits structurés souscrits
    securitised: list = field(default_factory=list)    # tranches de titrisation détenues
    hedges: list = field(default_factory=list)         # puts protecteurs (couverture) en cours
    options: list = field(default_factory=list)        # options sur actions (calls/puts) en cours
    currency_swaps: list = field(default_factory=list)  # swaps de devises actifs
    next_swap_id: int = 1                                # compteur d'identifiants de swaps
    fx_positions: list = field(default_factory=list)   # desk FX : spots ouverts (mark-to-market)
    fx_forwards: list = field(default_factory=list)    # desk FX : forwards en cours (règlement à échéance)
    ma_owned: dict = field(default_factory=dict)        # sociétés M&A détenues : ticker -> instance
    ma_history: list = field(default_factory=list)      # historique M&A (cessions, défauts)
    eval_state: dict = field(default_factory=dict)     # examen en pause (reprise possible)
    realized_pnl: float = 0.0                          # P&L réalisé cumulé (ventes)
    total_fees_paid: float = 0.0                       # commissions/frais d'exécution cumulés (achats/ventes/short/cover)
    total_margin_penalty: float = 0.0                  # surcoûts cumulés de liquidation forcée (appels de marge)
    total_financing_paid: float = 0.0                  # intérêts marge + frais d'emprunt de titres cumulés
    investigations_count: int = 0                       # nb d'enquêtes réglementaires subies (cf. core/dilemmas.py)
    # ----- progression de carrière -----
    deals_won: int = 0                                 # deals conclus (cumulatif)
    missions_done: int = 0                             # missions réalisées (cumulatif)
    grade_deals: int = 0                               # deals conclus depuis l'entrée dans le grade
    grade_missions: int = 0                            # missions réalisées depuis l'entrée dans le grade
    grade_start_quarter: int = 1                       # trimestre d'entrée dans le grade courant
    objectives: list = field(default_factory=list)     # objectifs du trimestre en cours
    objectives_quarter: int = 0                        # trimestre auquel se rapportent les objectifs
    journal: list = field(default_factory=list)        # journal de carrière (événements marquants)
    watchlist: list = field(default_factory=list)      # tickers suivis (max 10, accès rapide)
    bond_watchlist: list = field(default_factory=list)       # bond_id suivis
    commodity_watchlist: list = field(default_factory=list)  # id matières premières suivies
    gov_watchlist: list = field(default_factory=list)        # codes pays suivis
    titles: list = field(default_factory=list)         # titres de prestige obtenus
    best_cash: float = 0.0                             # meilleure trésorerie atteinte
    # ----- monde vivant -----
    inbox: list = field(default_factory=list)          # messages reçus (manager/client/conformité/desk)
    next_msg_id: int = 1                               # compteur d'identifiants de messages
    news_history: list = field(default_factory=list)   # fil d'actualités persistant (jusqu'à 3 ans)
    rivals: list = field(default_factory=list)         # concurrents : [{name, firm, track, score}]
    rival_owned_targets: list = field(default_factory=list)  # tickers de cibles M&A prises par des rivaux
    rival_events: list = field(default_factory=list)   # historique court des actions de rivaux (max ~15)
    # ----- décisions & éthique -----
    heat: int = 0                                      # scrutin réglementaire 0-100 (risque d'enquête)
    pending_dilemmas: list = field(default_factory=list)  # dilemmes en attente de décision
    decisions_log: list = field(default_factory=list)  # historique des choix marquants
    badges: list = field(default_factory=list)         # ids de succès/prestige débloqués
    streak_badges: list = field(default_factory=list)  # ids de badges à enjeu actifs (core/badges.py, révocables)
    legacy: list = field(default_factory=list)         # ids d'objectifs de légende (core/legacy.py) débloqués
    # ----- contenu : mandats / recherche / alertes -----
    mandates: list = field(default_factory=list)       # mandats clients actifs
    mandate_offers: list = field(default_factory=list)  # offres de mandats en attente
    next_mandate_id: int = 1
    mandate_history: list = field(default_factory=list)  # postmortems résolus (succès/échec, capé)
    ipos: list = field(default_factory=list)            # positions IPO souscrites (en attente de cotation)
    ipo_offers: list = field(default_factory=list)       # offres d'IPO en attente de souscription/refus
    next_ipo_id: int = 1                                 # compteur d'identifiants d'offres d'IPO
    research: dict = field(default_factory=dict)        # ticker -> {fair, rating, day}
    alerts: list = field(default_factory=list)          # [{ticker, price, above}]
    learned: list = field(default_factory=list)         # ids des leçons lues (Académie)
    certs: dict = field(default_factory=dict)           # programme -> niveau obtenu (CFA/FRM/CQF)
    game_over: bool = False
    game_over_reason: str = ""
    # ----- revue de performance annuelle (négociation de bonus) -----
    last_review_quarter: int = 0        # dernier trimestre où une revue a eu lieu
    pending_review: dict = None         # offre de revue en attente de réponse, ou None
    salary_bonus_per_step: float = 0.0  # supplément de salaire fixe négocié (revues)
    analysts: list = field(default_factory=list)  # équipe d'analystes juniors : [{profile_id, hired_step}]
    team_rep_accum: float = 0.0  # accumulateur fractionnaire du bonus de réputation de l'équipe
    rep_log: list = field(default_factory=list, repr=False, compare=False)  # journal transitoire
    # (raison, delta) des variations de réputation du tour en cours — non
    # sérialisé (pas de save) : vidé et repeuplé à chaque advance_step(), lu
    # par le terminal pour expliquer au joueur le « bilan du tour ».
    # ----- calendrier macro (paris directionnels sur évènements programmés) -----
    macro_events: list = field(default_factory=list)    # évènements programmés (annoncés, pas encore résolus)
    macro_bets: list = field(default_factory=list)       # paris placés en attente de résolution
    next_macro_event_id: int = 1                         # compteur d'identifiants d'évènements macro
    macro_bet_history: list = field(default_factory=list)  # historique des derniers paris résolus (UI)
    # ----- stress test réglementaire périodique -----
    last_stresstest_quarter: int = 0    # dernier trimestre où un stress test a eu lieu
    pending_stresstest: dict = None     # stress test en attente de réponse, ou None
    stresstest_history: list = field(default_factory=list)  # derniers résultats résolus (UI, max ~10)
    # ----- parcours d'intégration (premiers jours guidés) -----
    onboarding_step: int = 0            # index de l'étape courante (core/onboarding.py)
    onboarding_done: bool = False       # terminé ou explicitement passé
    # ----- journal d'investissement (core/journal.py) -----
    trade_journal: list = field(default_factory=list)  # entrées de trades : voir core/journal.py
    next_journal_id: int = 1            # compteur d'identifiants d'entrées de journal
    # ----- idées/opportunités (core/opportunities.py) -----
    saved_screens: list = field(default_factory=list)  # critères de recherche sauvegardés
    next_screen_id: int = 1             # compteur d'identifiants de critères sauvegardés
    # ----- profil de limites de risque (core/risklimits.py) -----
    risk_limit_profile: str = "default"  # "strict" / "default" / "souple"
    # ----- espace de travail (fenêtres flottantes du terminal) -----
    workspace: list = field(default_factory=list)  # [{"cls","ticker"/"kind","pos":[x,y]}]
    # ----- attribution de performance par source (core/career.py, scene_history.py) -----
    quarter_flows: dict = field(default_factory=dict)       # catégorie -> delta cash cumulé du trimestre en cours
    quarter_nw_anchor: float = 0.0                            # valeur nette au début du trimestre en cours
    last_quarter_attribution: dict = field(default_factory=dict)  # catégorie -> delta du dernier trimestre clos

    @property
    def grade(self):
        return config.GRADES[self.grade_index]

    def can_promote(self):
        return self.grade_index < len(config.GRADES) - 1

    def promote(self):
        if self.can_promote():
            self.grade_index += 1
            # réinitialise les compteurs propres au grade
            self.grade_deals = 0
            self.grade_missions = 0
            self.grade_start_quarter = self.quarter

    # ----- Économie / réputation ----------------------------------------
    def adjust_cash(self, delta, category=None):
        """Modifie la trésorerie. Si `category` est fourni, cumule le delta dans
        `quarter_flows` (catégorie -> delta) pour l'attribution de performance par
        source du trimestre en cours (cf. `core/career.py::close_quarter`,
        `scenes/scene_history.py`). Les flux liés au trading pur (frais, marge,
        règlements de dérivés...) ne sont volontairement pas tagués : ils
        retombent dans le résidu « marchés » calculé à la clôture du trimestre."""
        self.cash += delta
        if category and delta:
            self.quarter_flows[category] = self.quarter_flows.get(category, 0.0) + delta

    def adjust_reputation(self, delta, reason=None):
        """Modifie la réputation (bornée 0-100). Si `reason` est fourni et que le
        delta réellement appliqué (après bornage) est non nul, l'enregistre dans
        `rep_log` (liste transitoire de (raison, delta) consommée par
        `advance_step` pour expliquer au joueur la variation du tour — cf.
        `scenes/scene_terminal_commands.py::_advance_time`). Pure traçabilité :
        ne change aucune formule de calcul de réputation."""
        before = self.reputation
        self.reputation = max(0, min(100, before + delta))
        applied = self.reputation - before
        if reason and applied:
            self.rep_log.append((reason, applied))

    def quarter_of_day(self, day=None):
        d = self.day if day is None else day
        return (d - 1) // config.DAYS_PER_QUARTER + 1

    def salary_per_step(self):
        """Salaire net crédité par tour d'avancement, croissant avec le grade."""
        base = 4_000 + self.grade_index * 9_000
        return base * (config.DAYS_PER_STEP / 30.0)

    def costs_per_step(self):
        """Coûts opérationnels par tour (plus élevés aux grades supérieurs)."""
        base = 2_000 + self.grade_index * 4_500
        return base * (config.DAYS_PER_STEP / 30.0)

    def check_game_over(self, net_worth=None):
        """Met à jour game_over si faillite (liquidité ou valeur nette) ou
        réputation nulle. Retourne bool."""
        nw = self.cash if net_worth is None else net_worth
        if self.cash <= config.BANKRUPTCY_CASH or nw <= 0:
            self.game_over = True
            self.game_over_reason = (
                f"Faillite : liquidités à {self.cash:,.0f}, valeur nette {nw:,.0f}. "
                "Vos créanciers ont saisi la firme.")
        elif self.reputation <= config.MIN_REPUTATION:
            self.game_over = True
            self.game_over_reason = (
                "Réputation anéantie : vous êtes écarté de la profession.")
        return self.game_over


@dataclass
class GameState:
    """Conteneur global : joueur + métadonnées de partie."""
    player: PlayerState = field(default_factory=PlayerState)
    created_at: float = field(default_factory=time.time)
    last_saved: float = 0.0
    version: str = "0.1.0"

    # ----- Sérialisation -------------------------------------------------
    def to_dict(self):
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d):
        """Reconstruit un GameState depuis un dict JSON. Tolérant aux
        sauvegardes incomplètes ou d'une version antérieure du jeu : tout
        champ absent, du mauvais type ou inconnu retombe sur le défaut de
        PlayerState plutôt que de lever — une sauvegarde ancienne/partielle
        ne doit jamais empêcher le joueur de continuer."""
        if not isinstance(d, dict):
            d = {}
        gs = cls()
        gs.created_at = d.get("created_at", time.time())
        gs.last_saved = d.get("last_saved", 0.0)
        gs.version = d.get("version", "0.1.0")
        p = d.get("player", {})
        if not isinstance(p, dict):
            p = {}
        defaults = PlayerState()
        gs.player = PlayerState(**{
            k: p.get(k, getattr(defaults, k))
            for k in defaults.__dataclass_fields__
        })
        # sauvegardes antérieures au parcours d'intégration : pas de clé du tout
        # -> partie déjà en cours, on ne l'impose pas après coup.
        if "onboarding_done" not in p:
            gs.player.onboarding_done = True
        return gs

    # ----- Fichiers ------------------------------------------------------
    def save(self, slot="manual"):
        if self.player.sandbox:
            # mode bac à sable : run jetable, ne touche jamais aux sauvegardes
            # réelles. Chokepoint unique plutôt que de patcher chaque call site.
            logger.info("save: ignoré (mode sandbox, slot=%s)", slot)
            return None
        logger.info("save: début (slot=%s)", slot)
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        self.last_saved = time.time()
        path = os.path.join(config.SAVE_DIR, f"{slot}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception:
            logger.warning("save: échec (slot=%s, path=%s)", slot, path, exc_info=True)
            raise
        logger.info("save: succès (slot=%s, path=%s)", slot, path)
        return path

    @classmethod
    def load(cls, slot="manual"):
        """Charge un slot de sauvegarde. Retourne None (jamais d'exception)
        si le fichier est absent, illisible, corrompu (JSON invalide) ou
        d'une structure inattendue — les appelants (scene_menu, scene_saves)
        traitent déjà ce cas comme un échec de chargement affiché au joueur,
        plutôt que de faire planter le jeu sur une sauvegarde abîmée."""
        logger.info("load: début (slot=%s)", slot)
        path = os.path.join(config.SAVE_DIR, f"{slot}.json")
        if not os.path.exists(path):
            logger.info("load: aucune sauvegarde trouvée (slot=%s, path=%s)", slot, path)
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                gs = cls.from_dict(json.load(f))
        except Exception:
            logger.warning("load: échec (slot=%s, path=%s)", slot, path, exc_info=True)
            return None
        logger.info("load: succès (slot=%s, path=%s)", slot, path)
        return gs

    def export_to(self, path):
        """Écrit la partie dans un fichier JSON autonome à un chemin ARBITRAIRE
        (hors `config.SAVE_DIR`) — permet de transporter une sauvegarde d'une
        machine à l'autre (clé USB, cloud perso…) sans dépendre d'un service
        tiers. Même format que `save()` (compatible avec `import_from`/`load`).
        Fonctionne aussi en mode sandbox (contrairement à `save()`) : c'est une
        action explicite du joueur, pas un point de sauvegarde automatique."""
        logger.info("export_to: début (path=%s)", path)
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception:
            logger.warning("export_to: échec (path=%s)", path, exc_info=True)
            raise
        logger.info("export_to: succès (path=%s)", path)
        return path

    @classmethod
    def import_from(cls, path):
        """Charge une partie depuis un fichier JSON autonome à un chemin
        ARBITRAIRE (cf. `export_to`). Retourne None (jamais d'exception) si le
        fichier est absent, illisible ou corrompu — même contrat que `load()`."""
        logger.info("import_from: début (path=%s)", path)
        if not path or not os.path.exists(path):
            logger.info("import_from: fichier introuvable (path=%s)", path)
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                gs = cls.from_dict(json.load(f))
        except Exception:
            logger.warning("import_from: échec (path=%s)", path, exc_info=True)
            return None
        logger.info("import_from: succès (path=%s)", path)
        return gs

    @staticmethod
    def delete(slot):
        """Supprime un slot de sauvegarde. Retourne True si supprimé."""
        path = os.path.join(config.SAVE_DIR, f"{slot}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    @staticmethod
    def list_saves():
        """Retourne la liste des slots de sauvegarde disponibles."""
        if not os.path.isdir(config.SAVE_DIR):
            return []
        out = []
        for fn in os.listdir(config.SAVE_DIR):
            if fn.endswith(".json"):
                out.append(fn[:-5])
        return sorted(out)

    @staticmethod
    def slot_meta(slot):
        """Retourne un résumé d'un slot (sans tout charger), ou None si absent."""
        path = os.path.join(config.SAVE_DIR, f"{slot}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return None
        p = d.get("player", {})
        gi = p.get("grade_index", 0)
        grade = config.GRADES[gi] if 0 <= gi < len(config.GRADES) else "?"
        return {
            "name": p.get("name", "Trainee"),
            "grade": grade,
            "continent": p.get("continent", "?"),
            "track": p.get("track", "General"),
            "day": p.get("day", 1),
            "cash": p.get("cash", 0.0),
            "hardcore": p.get("hardcore", False),
            "game_over": p.get("game_over", False),
            "last_saved": d.get("last_saved", 0.0),
        }

    # ----- Boucle de temps ----------------------------------------------
    def advance_step(self, market=None):
        """
        Fait avancer le temps d'un tour (config.DAYS_PER_STEP jours) :
        salaire/coûts, vieillissement des deals, événements de marché,
        génération éventuelle de nouveaux deals, contrôle de fin de partie.
        Si `market` est fourni, la valeur nette (cash + positions) est utilisée
        pour l'historique, le record et le contrôle de faillite.
        Retourne un dict-résumé pour affichage par le terminal.
        """
        from core import career, deals, events  # imports locaux : logique pure, pas de pygame
        p = self.player
        if p.game_over:
            return {"events": [], "expired": [], "new_deals": [],
                    "net": 0.0, "game_over": True, "quarter_report": None}

        # journal transitoire des raisons de variation de réputation de CE tour :
        # vidé ici, repeuplé par adjust_reputation(..., reason=...) au fil du
        # tour, lu en fin de fonction pour le résumé puis exposé au terminal.
        p.rep_log = []

        # ancre de l'attribution de performance par source : valeur nette au
        # tout premier appel (avant toute mutation), pour amorcer le résidu
        # « marchés » dès le premier trimestre, y compris sur une sauvegarde
        # antérieure à l'ajout de ce mécanisme.
        if "attribution_anchor_set" not in p.flags:
            p.quarter_nw_anchor = p.cash_history[-1] if p.cash_history else p.cash
            p.flags["attribution_anchor_set"] = True

        prev_quarter = p.quarter
        p.day += config.DAYS_PER_STEP
        p.quarter = p.quarter_of_day()

        # salaire net du tour (salaire - coûts + supplément négocié en revue de performance
        # - coût récurrent de l'équipe d'analystes)
        team_cost = 0.0
        if getattr(p, "analysts", None):
            from core import team as _team
            team_cost = _team.team_cost_per_step(p)
            p.team_rep_accum = getattr(p, "team_rep_accum", 0.0) + _team.team_bonus_rep_per_step(p)
            whole = int(p.team_rep_accum)
            if whole:
                from core.i18n import get_lang
                reason = ("Analyst team reputation bonus" if get_lang() == "en"
                          else "Bonus de réputation de l'équipe d'analystes")
                p.adjust_reputation(whole, reason=reason)
                p.team_rep_accum -= whole
        net = (p.salary_per_step() - p.costs_per_step()
               + getattr(p, "salary_bonus_per_step", 0.0) - team_cost)
        p.adjust_cash(net, category="salaire")

        # vieillissement des deals : ceux arrivés à échéance non traités pénalisent
        expired = deals.age_deals(p)

        # événements de marché
        evts = events.roll_events(p)

        # génération de nouveaux deals (probabilité dépend du grade)
        new_deals = deals.maybe_generate(p)

        # dividendes des positions (longs touchent, shorts paient) + financement
        # (intérêts sur marge + frais d'emprunt de titres) + appel de marge éventuel
        dividends = 0.0
        financing = None
        margin_call = None
        structured_due = None
        securitised_due = None
        hedges_due = None
        options_due = None
        ipos_settled = None
        fx_due = None
        macro_resolved = None
        swaps_expired = []
        conditional_orders_executed = None
        if market is not None:
            from core import portfolio
            dividends = portfolio.dividends(p, market, config.DAYS_PER_STEP)
            if dividends:
                p.adjust_cash(dividends, category="revenus")
            # coupons obligataires (revenu de portage)
            if getattr(p, "bonds", None):
                from core import bonds as _bonds
                coup = _bonds.coupons(p, market, config.DAYS_PER_STEP)
                if coup:
                    p.adjust_cash(coup, category="revenus")
                    dividends += coup   # agrégé dans le revenu passif affiché
            # roulement des futures commodities (roll yield : coût en contango)
            if getattr(p, "commodities", None):
                from core import commodities as _cmdty
                roll = _cmdty.roll_cost(p, market, config.DAYS_PER_STEP)
                if roll:
                    p.adjust_cash(roll, category="revenus")
                    dividends += roll
            # intérêt de la CBDC (actif sûr rémunéré au taux directeur)
            if getattr(p, "crypto", None):
                from core import crypto as _crypto
                cbi = _crypto.interest(p, market, config.DAYS_PER_STEP)
                if cbi:
                    p.adjust_cash(cbi, category="revenus")
                    dividends += cbi
            # ordres conditionnels (stop-loss/take-profit) : exécutés AVANT le
            # contrôle de marge, comme un vrai ordre du joueur (voulu) passerait
            # avant une liquidation forcée (subie) sur la position réduite.
            if getattr(p, "conditional_orders", None):
                from core import conditional_orders as _condord
                conditional_orders_executed = _condord.execute_due(p, market)
            financing = portfolio.accrue_financing(p, market, config.DAYS_PER_STEP)
            margin_call = portfolio.check_margin_call(p, market)
            # échantillonnage du levier (style de jeu, indépendant de la progression de
            # grade) : utilisé par career.risk_profile() pour moduler les mandats proposés.
            if portfolio.leverage(p, market) >= 2.5:
                p.flags["high_leverage_steps"] = p.flags.get("high_leverage_steps", 0) + 1
            # dépassement persistant des limites de risque (cf. core/risklimits.py,
            # scenes/scene_risk.py) : un dépassement isolé ne coûte rien, mais le
            # laisser filer pénalise la réputation (mandataire qui tolère le
            # risque non maîtrisé) tant qu'il n'est pas corrigé.
            from core import risklimits as _risklimits
            if _risklimits.check_limits(p, market)["breaches"]:
                p.flags["risk_breach_streak"] = p.flags.get("risk_breach_streak", 0) + 1
                if p.flags["risk_breach_streak"] >= 3:
                    from core.i18n import get_lang
                    reason = ("Persistent risk limit breach" if get_lang() == "en"
                              else "Dépassement persistant des limites de risque")
                    p.adjust_reputation(-2, reason=reason)
            else:
                p.flags["risk_breach_streak"] = 0
            # veille marché : critères sauvegardés (core/opportunities.py) ->
            # notification inbox dès qu'un nouveau titre matche (une seule fois
            # par titre/critère, cf. `_seen` mémorisé sur le critère)
            if getattr(p, "saved_screens", None):
                from core import opportunities as _opportunities
                _opportunities.check_alerts(p, market)
            # produits structurés arrivés à échéance
            if getattr(p, "structured", None):
                from core import structured as _struct
                structured_due = _struct.evaluate_due(p, market)
            if getattr(p, "securitised", None):
                from core import securitisation as _sec
                securitised_due = _sec.evaluate_due(p, market)
            if getattr(p, "hedges", None):
                from core import hedging as _hedging
                hedges_due = _hedging.evaluate_due(p, market)
            if getattr(p, "options", None):
                from core import options as _options
                options_due = _options.evaluate_due(p, market)
            if getattr(p, "ipos", None):
                from core import ipo as _ipo
                ipos_settled = _ipo.evaluate_listings(p, market)
            if getattr(p, "fx_forwards", None):
                from core import fx as _fx
                fx_due = _fx.evaluate_due(p, market)
            if getattr(p, "macro_events", None):
                from core import macrocal as _macrocal
                macro_resolved = _macrocal.resolve_due_events(p, market)
            if getattr(p, "currency_swaps", None):
                from core import swaps as _swaps
                swap_flow, swaps_expired = _swaps.accrue(p, market, config.DAYS_PER_STEP)
                if swap_flow:
                    p.adjust_cash(swap_flow, category="revenus")
                    dividends += swap_flow
            nw = portfolio.net_worth(p, market)
        else:
            nw = p.cash

        # bascule de trimestre : clôture des objectifs + génération des suivants
        quarter_report = None
        ma_events = []
        review_offer = None
        if p.quarter != prev_quarter:
            # attribution de performance par source : tout ce qui n'est pas
            # passé par adjust_cash(..., category=...) ce trimestre (frais,
            # marge, règlements de dérivés, plus/moins-values de marché...)
            # retombe dans le résidu « marchés », garantissant une somme
            # exacte avec la variation de valeur nette du trimestre.
            attribution = dict(p.quarter_flows)
            attribution["marches"] = (nw - p.quarter_nw_anchor) - sum(p.quarter_flows.values())
            p.last_quarter_attribution = attribution
            p.quarter_flows = {}
            p.quarter_nw_anchor = nw
            quarter_report = career.close_quarter(p)
            # mémorisé pour la carte « Bilan du trimestre » du bureau
            # (scenes/scene_desktop.py) — JSON-sérialisable, persiste au save.
            p.flags["last_quarter_report"] = dict(quarter_report,
                                                  quarter=prev_quarter,
                                                  nw=round(nw, 2))
            career.ensure_objectives(p)
            from core import review as _review
            review_offer = _review.maybe_trigger(p, True)
            # secteur mis en avant pour le nouveau trimestre (guidance)
            import random as _r

            from data.companies import SECTORS as _SEC
            p.flags["hot_sector"] = _r.choice(list(_SEC.keys()))
            if getattr(p, "ma_owned", None):
                from core import ma as ma_mod
                ma_events = ma_mod.evolve_quarter(p)
        p.best_cash = max(p.best_cash, nw)

        # mémorise la valeur nette pour la sparkline du terminal
        p.cash_history.append(round(nw, 2))
        if len(p.cash_history) > 80:
            p.cash_history.pop(0)

        # journal d'événements borné
        for e in evts + [{"title": x["title"], "kind": "bad",
                          "desc": "Deal expiré non traité."} for x in expired]:
            p.event_log.append(e["title"])
        for sw in swaps_expired:
            p.event_log.append(f"Swap {sw['foreign_region']} arrivé à échéance.")
        for title in ma_events:
            p.event_log.append(title)
        p.event_log = p.event_log[-12:]

        p.check_game_over(net_worth=nw)

        logger.debug(
            "advance_step: day=%s quarter=%s cash=%.2f net_worth=%.2f game_over=%s",
            p.day, p.quarter, p.cash, nw, p.game_over)

        return {
            "events": evts,
            "expired": expired,
            "new_deals": new_deals,
            "net": net,
            "dividends": dividends,
            "financing": financing,
            "margin_call": margin_call,
            "structured_due": structured_due,
            "securitised_due": securitised_due,
            "hedges_due": hedges_due,
            "options_due": options_due,
            "ipos_settled": ipos_settled,
            "fx_due": fx_due,
            "macro_resolved": macro_resolved,
            "swaps_expired": swaps_expired,
            "conditional_orders_executed": conditional_orders_executed,
            "quarter_changed": p.quarter != prev_quarter,
            "quarter_report": quarter_report,
            "ma_events": ma_events,
            "review_offer": review_offer,
            "game_over": p.game_over,
            # copie du journal de variations de réputation du tour (raison, delta) —
            # rep_log lui-même continuera d'être enrichi après ce point par des
            # actions hors advance_step (PITCH, deals résolus...) ; le terminal lit
            # cette copie pour le bilan du tour, indépendamment de ce qui suit.
            "rep_log": list(p.rep_log),
        }
