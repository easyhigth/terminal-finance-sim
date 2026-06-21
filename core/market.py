"""
market.py — Moteur de marché à facteurs (déterministe, vectorisé numpy).

Idée centrale : le rendement de chaque société à un pas de temps se décompose en
facteurs partagés + un bruit propre :

    r_i = drift_i
        + beta_i      * F_monde        (choc de marché global du pas)
        + b_secteur_i * F_secteur(i)   (choc sectoriel : tech, luxe, agro...)
        + b_region_i  * F_region(i)    (choc régional : USA / Europe / Asie)
        + sigma_i     * bruit_i        (spécifique à la société)

Conséquences « gratuites », comme dans le réel :
  - les indices ÉMERGENT de leurs constituants (pondérés par capitalisation) :
    le KAK 40 dépend donc mécaniquement de LWNH, le C&D 500 de MVC, etc. ;
  - les corrélations sont réalistes (deux valeurs tech co-bougent, USA et Europe
    co-bougent via F_monde...) ;
  - une CRISE = un choc injecté sur les bons facteurs sur plusieurs pas
    (2008 → F_monde + F_finance effondrés ; tornade → F_agro négatif...).

Déterminisme : tout est piloté par un numpy RandomState(seed). L'état se
reconstruit donc exactement via (seed, nombre de pas) — pratique pour le save.
"""
import numpy as np

from core.applog import logger
from data import companies as comp_data
from core.market_constants import (
    HIST_LEN, STEPS_PER_YEAR, WARMUP_YEARS, WARMUP_STEPS,
    MU_WORLD, VOL_WORLD, VOL_SECTOR, VOL_REGION, DRIFT_MULT,
    T_DF_WORLD, T_DF_SECTOR, T_DF_REGION, T_DF_IDIO,
    _T_SCALE_WORLD, _T_SCALE_SECTOR, _T_SCALE_REGION, _T_SCALE_IDIO,
    JUMP_PROBA, JUMP_MAGNITUDE_MEAN, JUMP_MAGNITUDE_VOL, JUMP_DOWN_BIAS,
    ASYM_VOL_MEAN_REV, ASYM_VOL_DOWN_GAIN, ASYM_VOL_UP_GAIN,
    ASYM_VOL_MAX_MULT, ASYM_VOL_MIN_MULT, _ASYM_VOL_GAIN_AVG,
    STRESS_VOLMULT_NEUTRAL, STRESS_REGIME_FLOOR, STRESS_BLEND_W_MAX,
    _stress_level, _blend_factor_toward_world, nonworld_variance_correction,
    REGIMES, REGIME_TRANSITIONS,
    EARN_PERIOD, SURPRISE_VOL, EARN_PRICE_K, EARN_NEWS_THRESH,
    EARN_ANTICIPATION_WINDOW, EARN_ANTICIPATION_K,
    GUIDANCE_VOL, GUIDANCE_SURPRISE_CORR, GUIDANCE_PRICE_K,
    GUIDANCE_TO_ANTICIPATION_K, GUIDANCE_RAISE_THRESH, GUIDANCE_LABELS,
    REVISION_PROBA, REVISION_VOL, REVISION_PRICE_K,
    PEAD_HORIZON_STEPS, PEAD_DECAY, PEAD_K,
    CRISIS_SEVERE_SEVERITY, CRISIS_COOLDOWN_STEPS,
    CURVE_TENORS, CURVE_TERM_PREMIUM, CURVE_NS_LAMBDA, _REGIME_SLOPE_BIAS,
    CURVE_CURVATURE_STRESS_GAIN, CURVE_FACTOR_MEAN_REV,
    CURVE_SLOPE_BOUND, CURVE_CURV_BOUND,
    _curve_ns_loadings, _curve_slope_target, _curve_curvature_target,
    BASE_CREDIT_IG_BPS, BASE_CREDIT_HY_BPS, _REGIME_BASE_TENSION,
    Crisis,
)
from core.market_query import MarketQueryMixin

class Market(MarketQueryMixin):
    def __init__(self, seed=12345):
        self.seed = int(seed)
        self.rng = np.random.RandomState(self.seed)
        self.step_count = 0

        companies, index_defs = comp_data.COMPANIES, comp_data.INDICES
        self.companies = companies
        self.n = len(companies)

        self.sectors = list(comp_data.SECTORS.keys())
        self.regions = list(comp_data.REGIONS)
        self._sector_idx = {s: i for i, s in enumerate(self.sectors)}
        self._region_idx = {r: i for i, r in enumerate(self.regions)}

        # tableaux vectorisés
        self.price = np.array([c["price0"] for c in companies], dtype=np.float64)
        self.shares = np.array([c["shares"] for c in companies], dtype=np.float64)
        self.beta = np.array([c["beta"] for c in companies], dtype=np.float64)
        self.b_sector = np.array([c["b_sector"] for c in companies], dtype=np.float64)
        self.b_region = np.array([c["b_region"] for c in companies], dtype=np.float64)
        self.sigma = np.array([c["sigma"] for c in companies], dtype=np.float64)
        self.drift = np.array([c["drift"] for c in companies], dtype=np.float64) * DRIFT_MULT
        # fondamentaux DYNAMIQUES (dérivent au fil des résultats trimestriels)
        self.revenue = np.array([c["revenue"] for c in companies], dtype=np.float64)
        self.net_margin = np.array([c["net_margin"] for c in companies], dtype=np.float64)
        self.ebitda_margin = np.array([c["ebitda_margin"] for c in companies], dtype=np.float64)
        self._base_net_margin = self.net_margin.copy()
        self._base_ebitda_margin = self.ebitda_margin.copy()
        self.last_earnings = []      # rapports publiés au dernier pas
        self.earnings_log = {}       # ticker -> dernier rapport {surprise, growth, beat, step, guidance...}
        # ---- anticipation/guidance/PEAD (chantier 13) : état par société ----
        # surprise et guidance du PROCHAIN print, déjà tirées (cf. _prepare_next_earnings)
        # pour permettre le drift d'anticipation dans les pas qui précèdent l'annonce.
        self.next_surprise = np.zeros(self.n)
        self.next_guidance = np.zeros(self.n)
        # biais d'anticipation hérité de la guidance du cycle précédent (0 au 1er cycle)
        self.guidance_bias = np.zeros(self.n)
        # état de drift post-annonce (PEAD), décroissant géométriquement vers 0
        self.pead_state = np.zeros(self.n)
        # dernière guidance publiée (pour lecture UI / earnings_log), par société
        self.last_guidance = {}      # ticker -> {"value", "label", "step"}
        self._prepare_next_earnings(np.arange(self.n))
        self.regime = "Calme"        # régime de marché courant (toile de fond lente)
        self.regime_changed = False  # vrai au pas où le régime vient de basculer
        self.regime_since = 0        # step_count au moment où le régime courant a démarré
        self.sec_id = np.array([self._sector_idx[c["sector"]] for c in companies])
        self.reg_id = np.array([self._region_idx[c["region"]] for c in companies])
        self.ticker_idx = {c["ticker"]: i for i, c in enumerate(companies)}

        # indices : membres = top-N par capitalisation initiale dans la région
        self.index_defs = index_defs
        self.index_members = {}
        self.index_scale = {}
        self.index_region = {}
        for name, region, target, count in index_defs:
            cand = [i for i in range(self.n) if companies[i]["region"] == region]
            cand.sort(key=lambda i: self.price[i] * self.shares[i], reverse=True)
            members = cand[:count]
            self.index_members[name] = members
            self.index_region[name] = region
            cap = float(np.sum(self.price[members] * self.shares[members]))
            self.index_scale[name] = target / cap if cap else 1.0

        # historiques
        self.index_hist = {d[0]: [self.index_value(d[0])] for d in index_defs}
        self.price_hist = {}     # ticker -> liste de prix (rempli paresseusement)
        # historique COMPLET (toutes sociétés) : snapshots du vecteur de prix, borné
        # à HIST_LEN. Permet de grapher n'importe quel actif sans suivi préalable.
        self.price_hist_all = [self.price.copy()]
        self.last_world = 0.0
        self.last_sector = np.zeros(len(self.sectors))
        self.last_region = np.zeros(len(self.regions))
        self.prev_price = None      # prix avant le dernier pas (attribution P&L)
        self.last_ret = None        # rendements log du dernier pas (par société)
        # effet de levier asymétrique (cf. ASYM_VOL_*) : multiplicateur d'écart-type
        # du facteur MONDE, état persistant qui mean-reverte vers 1.0 mais est
        # poussé à la hausse plus fortement après un choc négatif que positif.
        self.world_vol_mult_state = 1.0
        self._last_world_noise = 0.0   # bruit Student-t (hors shock/jump) du dernier pas
        # corrélations dynamiques (cf. _stress_level/_blend_toward_world) : niveau
        # de stress du dernier pas (0..1), conservé pour lecture/diagnostic.
        self.last_stress_level = 0.0
        # courbe des taux à 3 facteurs (Nelson-Siegel, cf. constantes CURVE_*) :
        # états PERSISTANTS et lissés des composantes pente/courbure cycliques
        # (la composante niveau reste l'ancien short rate + prime de terme,
        # déjà mean-reverting via macro["rate"], pas dupliquée ici). Initialisés
        # à 0.0 = état neutre, identique à la cible à l'état neutre -> aucune
        # régression sur les tests existants qui mutent regime/macro SANS
        # appeler step() (la courbe reste alors une fonction instantanée, cf.
        # curve_point). Ces deux états ne sont PAS sérialisés dans les saves
        # (PlayerState ne stocke que market_seed/market_step) : ils se
        # reconstruisent exactement en rejouant step() depuis l'origine.
        self.curve_slope_state = 0.0
        self.curve_curv_state = 0.0
        self.crises = []
        self.ended_crises = []   # crises qui viennent de s'éteindre CE pas (pour postmortem)
        self.crisis_cooldown = 0  # pas restants d'accalmie forcée après une crise majeure
        self._last_news = []
        # bump de crédit RÉGIONAL transitoire (en décimal de rendement) injecté
        # par les événements politiques (core/politics.py) et lu par core/bonds.py :
        # un choc politique élargit les spreads de la zone puis se résorbe. État
        # de gameplay ÉPHÉMÈRE (comme les crises) : non sérialisé, décroît à chaque pas.
        self.region_credit_bump = {r: 0.0 for r in self.regions}

        # ---- macro-économie (déterministe, évolue à chaque pas) ----
        # chaque indicateur : valeur courante, moyenne de long terme, vitesse de
        # retour à la moyenne, volatilité par pas, et son historique récent.
        self.macro = {
            "rate":        {"v": 3.0, "mean": 2.5, "k": 0.03, "vol": 0.05, "unit": "%",
                            "label": "Taux directeur"},
            "inflation":   {"v": 2.6, "mean": 2.0, "k": 0.03, "vol": 0.08, "unit": "%",
                            "label": "Inflation"},
            "growth":      {"v": 2.2, "mean": 2.0, "k": 0.05, "vol": 0.20, "unit": "%",
                            "label": "Croissance PIB"},
            "unemployment":{"v": 5.0, "mean": 5.0, "k": 0.04, "vol": 0.10, "unit": "%",
                            "label": "Chômage"},
            "confidence":  {"v": 100.0, "mean": 100.0, "k": 0.05, "vol": 1.2, "unit": "",
                            "label": "Confiance"},
            "credit_ig":   {"v": BASE_CREDIT_IG_BPS, "mean": BASE_CREDIT_IG_BPS, "k": 0.04,
                            "vol": 3.0, "unit": "bps", "label": "Spread crédit IG"},
            "credit_hy":   {"v": BASE_CREDIT_HY_BPS, "mean": BASE_CREDIT_HY_BPS, "k": 0.05,
                            "vol": 14.0, "unit": "bps", "label": "Spread crédit HY"},
            "liquidity":   {"v": 70.0, "mean": 70.0, "k": 0.06, "vol": 1.5, "unit": "",
                            "label": "Liquidité de marché"},
        }
        self.macro_hist = {k: [self.macro[k]["v"]] for k in self.macro}
        logger.info("Market.__init__: seed=%s n_companies=%s", self.seed, self.n)

    # ------------------------------------------------------------------ pas
    def step(self):
        """Avance le marché d'un pas et renvoie la liste des news générées."""
        vol_mult = 1.0
        world_shock = 0.0
        reg_shock = np.zeros(len(self.regions))
        sec_shock = np.zeros(len(self.sectors))
        for cr in self.crises:
            vol_mult = max(vol_mult, cr.vol_mult)
            world_shock += cr.world
            for r, v in cr.regions.items():
                if r in self._region_idx:
                    reg_shock[self._region_idx[r]] += v
            for s, v in cr.sectors.items():
                if s in self._sector_idx:
                    sec_shock[self._sector_idx[s]] += v

        # régime de marché : toile de fond lente qui module dérive/vol du monde
        self._step_regime()
        reg = REGIMES[self.regime]
        vol_mult *= reg["vol"]

        # macro : mise à jour + influence (pédagogique) sur les facteurs
        self._step_macro()
        mc = self.macro
        world_shock += (mc["growth"]["v"] - 2.0) * 0.0004        # croissance → vent porteur
        if "Finance" in self._sector_idx:
            sec_shock[self._sector_idx["Finance"]] += -(mc["rate"]["v"] - 2.5) * 0.0016
        if "Immobilier" in self._sector_idx:
            sec_shock[self._sector_idx["Immobilier"]] += -(mc["rate"]["v"] - 2.5) * 0.0020
        if "Utilities" in self._sector_idx:
            # valeurs « obligataires » (rendement du dividende comparé au taux sans
            # risque) : pénalisées quand les taux montent, comme l'immobilier.
            sec_shock[self._sector_idx["Utilities"]] += -(mc["rate"]["v"] - 2.5) * 0.0014
        if "Tech" in self._sector_idx:
            # valorisation de croissance : sensible au taux LONG (actualisation de
            # cash-flows lointains), donc à la courbe plutôt qu'au seul taux court.
            sec_shock[self._sector_idx["Tech"]] += -(self.curve_point(10.0) * 100.0 - 4.5) * 0.0011
        if "Finance" in self._sector_idx:
            # les banques vivent de la marge d'intérêt nette : une courbe qui
            # s'aplatit ou s'inverse comprime leur rentabilité, en plus de l'effet
            # de niveau de taux déjà modélisé ci-dessus.
            sec_shock[self._sector_idx["Finance"]] += min(0.0, self.curve_slope() * 0.0009)
        if "Energie" in self._sector_idx:
            # secteur traditionnellement protecteur contre l'inflation (pouvoir
            # de fixation des prix sur les matières premières).
            sec_shock[self._sector_idx["Energie"]] += (mc["inflation"]["v"] - 2.0) * 0.0010
        if "Materiaux" in self._sector_idx:
            # cyclique : la demande de matières premières suit la croissance.
            sec_shock[self._sector_idx["Materiaux"]] += (mc["growth"]["v"] - 2.0) * 0.0009
        if "Industrie" in self._sector_idx:
            sec_shock[self._sector_idx["Industrie"]] += (mc["growth"]["v"] - 2.0) * 0.0008
        if "Semicon" in self._sector_idx:
            # même logique de duration longue que la tech, effet plus modéré.
            sec_shock[self._sector_idx["Semicon"]] += -(self.curve_point(10.0) * 100.0 - 4.5) * 0.0009
        if "Auto" in self._sector_idx:
            # achats à crédit (financement auto) sensibles au coût du crédit.
            sec_shock[self._sector_idx["Auto"]] += -(mc["rate"]["v"] - 2.5) * 0.0010
        if "Conso" in self._sector_idx:
            sec_shock[self._sector_idx["Conso"]] += (mc["confidence"]["v"] - 100.0) * 0.00006
        if "Luxe" in self._sector_idx:
            sec_shock[self._sector_idx["Luxe"]] += (mc["confidence"]["v"] - 100.0) * 0.00008
        for _defensif in ("Sante", "Telecom", "Agro"):
            if _defensif in self._sector_idx:
                # secteurs défensifs : surperformance relative quand le chômage
                # monte (demande peu cyclique, rotation défensive des flux).
                sec_shock[self._sector_idx[_defensif]] += (mc["unemployment"]["v"] - 5.0) * 0.0003

        # facteurs à queues épaisses (Student-t re-normalisée, cf. _t_scale) au
        # lieu d'une gaussienne pure : même volatilité par pas, mouvements
        # extrêmes plus fréquents qu'une gaussienne ne le permettrait.
        # Le facteur MONDE est en outre modulé par l'état d'asymétrie de levier
        # (cf. ASYM_VOL_*, mis à jour en fin de pas) : sa vol effective monte
        # plus après une mauvaise nouvelle que symétriquement après une bonne.
        world_noise_draw = self.rng.standard_t(T_DF_WORLD)
        world_noise = VOL_WORLD * vol_mult * self.world_vol_mult_state * _T_SCALE_WORLD * world_noise_draw
        F_world = MU_WORLD + reg["drift"] + world_noise + world_shock
        F_sector = (VOL_SECTOR * vol_mult * _T_SCALE_SECTOR
                    * self.rng.standard_t(T_DF_SECTOR, size=len(self.sectors)) + sec_shock)
        F_region = (VOL_REGION * vol_mult * _T_SCALE_REGION
                    * self.rng.standard_t(T_DF_REGION, size=len(self.regions)) + reg_shock)
        eps = _T_SCALE_IDIO * self.rng.standard_t(T_DF_IDIO, size=self.n)

        # ---- couche structurelle de sauts rares (jump-diffusion) -----------
        # Tirages CONSOMMÉS À CHAQUE PAS (déterminisme : la séquence de tirages
        # rng ne doit jamais dépendre du résultat d'un tirage précédent), même
        # quand aucun saut ne se déclenche, pour que fast_forward/sync_to par
        # nombre de pas restent parfaitement reproductibles.
        jump_roll = self.rng.random_sample()
        jump_dir_roll = self.rng.random_sample()
        jump_mag_draw = self.rng.standard_normal()
        if jump_roll < JUMP_PROBA:
            sign = -1.0 if jump_dir_roll < JUMP_DOWN_BIAS else 1.0
            magnitude = max(0.0, JUMP_MAGNITUDE_MEAN + JUMP_MAGNITUDE_VOL * jump_mag_draw)
            world_jump = sign * magnitude
            F_world += world_jump
            # tilt sectoriel/régional léger et déterministe (mêmes tirages que
            # ci-dessus, pas de tirage rng supplémentaire) : Finance et
            # Immobilier amplifient un peu un krach mondial, comme dans Crisis.
            if "Finance" in self._sector_idx:
                F_sector[self._sector_idx["Finance"]] += world_jump * 0.6
            if "Immobilier" in self._sector_idx:
                F_sector[self._sector_idx["Immobilier"]] += world_jump * 0.4

        # ---- corrélations dynamiques : mélange secteur/région/idio -> monde --
        # Le stress du pas est évalué AVANT la mise à jour de world_vol_mult_state
        # (cf. plus bas) : on utilise l'état entrant (déjà connu en début de pas,
        # reflet du clustering de volatilité accumulé jusqu'ici), pas une valeur
        # qui dépendrait du tirage de CE pas (déterminisme : aucun tirage rng
        # supplémentaire n'est introduit par ce mécanisme, on ne fait que
        # repondérer des réalisations déjà tirées ci-dessus).
        stress = _stress_level(self.world_vol_mult_state, self.regime)
        w_blend = STRESS_BLEND_W_MAX * stress
        self.last_stress_level = stress
        # écarts-types calibrés du pas (mêmes multiplicateurs vol_mult/world_vol_mult_state
        # que ceux utilisés ci-dessus pour les tirages) -- nécessaires au calcul exact
        # du facteur de correction de variance c(w) (cf. nonworld_variance_correction).
        world_std = VOL_WORLD * vol_mult * self.world_vol_mult_state
        sector_std = VOL_SECTOR * vol_mult
        region_std = VOL_REGION * vol_mult
        eps_std = 1.0
        if w_blend > 0.0:
            # partie centrée du monde (bruit + saut, hors dérive régime/macro/crise) :
            # cible de mélange, pour ne pas injecter de biais de niveau supplémentaire.
            world_centered = F_world - (MU_WORLD + reg["drift"] + world_shock)
            F_sector = _blend_factor_toward_world(F_sector, world_centered, w_blend, sector_std, world_std)
            F_region = _blend_factor_toward_world(F_region, world_centered, w_blend, region_std, world_std)
            eps = _blend_factor_toward_world(eps, world_centered, w_blend, eps_std, world_std)
            # facteur de correction PAR SOCIÉTÉ qui annule l'inflation de variance
            # introduite sur la jambe non-monde par le mélange ci-dessus (le mélange
            # préserve la variance MARGINALE de chaque facteur secteur/région/idio,
            # mais les rend mutuellement corrélés via le terme partagé w·F_monde,
            # ce qui gonflerait Var(secteur+région+idio) si on ne corrigeait pas).
            v_nonworld0 = (self.b_sector ** 2 * sector_std ** 2
                           + self.b_region ** 2 * region_std ** 2
                           + self.sigma ** 2 * eps_std ** 2)
            s_cross = 2.0 * (self.b_sector * self.b_region * sector_std * region_std
                              + self.b_sector * self.sigma * sector_std * eps_std
                              + self.b_region * self.sigma * region_std * eps_std)
            t_cross = (self.b_sector * sector_std + self.b_region * region_std
                       + self.sigma * eps_std)
            nonworld_corr = nonworld_variance_correction(
                w_blend, v_nonworld0, s_cross, t_cross, self.beta, world_std)
        else:
            nonworld_corr = 1.0

        # saison de résultats : anticipation/révisions/PEAD lus sur l'état D'AVANT
        # le print de ce pas, puis le print lui-même (gap + guidance) qui met à
        # jour cet état pour les pas suivants (cf. docstrings des helpers).
        anticipation_shock = self._step_anticipation()
        revision_shock = self._step_revisions()
        pead_shock = self._step_pead()
        earnings_shock = self._step_earnings()

        ret = (self.drift
               + self.beta * F_world
               + nonworld_corr * (self.b_sector * F_sector[self.sec_id]
                                   + self.b_region * F_region[self.reg_id]
                                   + self.sigma * eps)
               + earnings_shock + anticipation_shock + revision_shock + pead_shock)
        # borne les rendements par pas pour éviter les valeurs aberrantes
        np.clip(ret, -0.35, 0.35, out=ret)
        self.prev_price = self.price.copy()   # mémorise pour l'attribution du P&L
        self.price *= np.exp(ret)
        np.maximum(self.price, 0.01, out=self.price)

        self.last_world = float(F_world)
        self.last_sector = F_sector
        self.last_region = F_region
        self.last_ret = ret.copy()

        # ---- mise à jour de l'état d'asymétrie de levier (GJR-GARCH-like) --
        # On ne réagit qu'au BRUIT Student-t du facteur monde (hors dérive de
        # régime/macro, hors choc de crise scénarisé, hors saut structurel) :
        # c'est la part "nouvelle imprévue" du pas, celle qui doit déclencher
        # le clustering de volatilité. Le carré normalise l'ampleur (peu
        # importe le signe pour la TAILLE du choc) ; le gain appliqué diffère
        # selon le signe (asymétrie). Mean-reversion vers 1.0 en parallèle.
        raw_gain = ASYM_VOL_DOWN_GAIN if world_noise_draw < 0.0 else ASYM_VOL_UP_GAIN
        gain = raw_gain / _ASYM_VOL_GAIN_AVG    # cf. constantes : E[gain] == 1
        # normalisé à variance unitaire (cf. _t_scale) : sous stationnarité,
        # E[shock_sq] = 1, donc le terme (shock_sq - 1.0) est bien centré et
        # ne fait PAS dériver la moyenne de l'état (seule sa distribution
        # temporelle bouge -> clustering, pas d'inflation de la moyenne).
        normed_draw = world_noise_draw * _T_SCALE_WORLD
        shock_sq = normed_draw * normed_draw
        new_state = (self.world_vol_mult_state
                     + ASYM_VOL_MEAN_REV * (1.0 - self.world_vol_mult_state)
                     + ASYM_VOL_MEAN_REV * gain * (shock_sq - 1.0))
        self.world_vol_mult_state = min(ASYM_VOL_MAX_MULT, max(ASYM_VOL_MIN_MULT, new_state))

        # ---- courbe des taux : lissage des états persistants pente/courbure --
        # Mêmes cibles instantanées que curve_point()/curve_slope() (régime,
        # croissance, stress du pas déjà calculé ci-dessus), mais approchées
        # progressivement (mean-reversion, AUCUN tirage rng supplémentaire) au
        # lieu d'être atteintes en un seul pas -- une courbe réelle ne se
        # redessine pas instantanément à chaque nouvelle donnée macro.
        slope_target = _curve_slope_target(self.regime, self.macro["growth"]["v"])
        curv_target = _curve_curvature_target(self.last_stress_level)
        self.curve_slope_state += CURVE_FACTOR_MEAN_REV * (slope_target - self.curve_slope_state)
        self.curve_curv_state += CURVE_FACTOR_MEAN_REV * (curv_target - self.curve_curv_state)
        self.curve_slope_state = min(CURVE_SLOPE_BOUND, max(-CURVE_SLOPE_BOUND, self.curve_slope_state))
        self.curve_curv_state = min(CURVE_CURV_BOUND, max(-CURVE_CURV_BOUND, self.curve_curv_state))

        self.step_count += 1

        # historiques
        for name in self.index_hist:
            self.index_hist[name].append(self.index_value(name))
            if len(self.index_hist[name]) > HIST_LEN:
                self.index_hist[name].pop(0)
        for tk, hist in self.price_hist.items():
            hist.append(float(self.price[self.ticker_idx[tk]]))
            if len(hist) > HIST_LEN:
                hist.pop(0)
        # historique complet (toutes sociétés)
        self.price_hist_all.append(self.price.copy())
        if len(self.price_hist_all) > HIST_LEN:
            self.price_hist_all.pop(0)

        # crises : décrément + détection de fin (pour le postmortem et l'accalmie)
        for cr in self.crises:
            cr.steps_left -= 1
        self.ended_crises = [cr for cr in self.crises if cr.steps_left <= 0]
        self.crises = [cr for cr in self.crises if cr.steps_left > 0]
        if self.crisis_cooldown > 0:
            self.crisis_cooldown -= 1
        for cr in self.ended_crises:
            if cr.severity >= CRISIS_SEVERE_SEVERITY:
                self.crisis_cooldown = max(self.crisis_cooldown, CRISIS_COOLDOWN_STEPS)

        # résorption progressive des bumps de crédit régionaux (politique) :
        # décroissance déterministe (aucun tirage RNG → prix inchangés).
        for r in self.region_credit_bump:
            v = self.region_credit_bump[r] * 0.72
            self.region_credit_bump[r] = v if v > 1e-5 else 0.0

        self._last_news = self._generate_news(F_world, F_sector, F_region)
        self._last_news += self._earnings_news()
        if self.regime_changed:
            good = self.regime in ("Expansion", "Calme")
            self._last_news.insert(0, {
                "region": None, "kind": "good" if good else "bad",
                "text": f"Bascule de régime : {self.regime_label()}"})
        self._last_news = self._last_news[:4]
        logger.debug(
            "market.step: step_count=%s regime=%s world=%.5f news=%d",
            self.step_count, self.regime, self.last_world, len(self._last_news))
        return self._last_news

    # indicateurs pilotés par un AR(1) bruité (tirage rng) — le crédit et la
    # liquidité sont volontairement EXCLUS : ils sont dérivés déterministiquement
    # des autres indicateurs juste après (cf. _step_credit_liquidity), pour ne
    # pas consommer de tirage rng supplémentaire et décaler tout l'état de
    # marché qui suit dans step() (cf. CLAUDE.md, déterminisme).
    _STOCHASTIC_KEYS = ("rate", "inflation", "growth", "unemployment", "confidence")

    def _step_macro(self):
        """Met à jour les indicateurs macro (AR(1) à retour à la moyenne)."""
        m = self.macro
        # banque centrale : la cible de taux suit l'inflation (règle simplifiée)
        m["rate"]["mean"] = max(0.5, 1.0 + 1.0 * m["inflation"]["v"])
        # confiance liée au dernier choc de marché
        m["confidence"]["mean"] = 100.0 + self.last_world * 300
        # chômage inversement lié à la croissance
        m["unemployment"]["mean"] = 5.0 - (m["growth"]["v"] - 2.0) * 0.4
        for k in self._STOCHASTIC_KEYS:
            d = m[k]
            d["v"] += d["k"] * (d["mean"] - d["v"]) + self.rng.normal(0, d["vol"])
        m["rate"]["v"] = min(12.0, max(0.0, m["rate"]["v"]))
        m["inflation"]["v"] = min(15.0, max(-2.0, m["inflation"]["v"]))
        m["growth"]["v"] = min(8.0, max(-6.0, m["growth"]["v"]))
        m["unemployment"]["v"] = min(20.0, max(2.0, m["unemployment"]["v"]))
        m["confidence"]["v"] = min(140.0, max(50.0, m["confidence"]["v"]))
        self._step_credit_liquidity()
        for k in m:
            self.macro_hist[k].append(m[k]["v"])
            if len(self.macro_hist[k]) > HIST_LEN:
                self.macro_hist[k].pop(0)

    def _step_credit_liquidity(self):
        """Spreads de crédit IG/HY et liquidité de marché : dérivés (lissage
        déterministe, sans tirage rng propre) de la croissance, du chômage et
        du dernier choc de marché — s'élargissent/se réduisent quand la
        croissance/l'emploi se dégradent ou après un choc baissier marqué (fuite
        vers la qualité), cohérents avec un régime de stress plutôt qu'un
        tirage isolé indépendant du contexte macro."""
        m = self.macro
        growth_stress = max(0.0, 1.0 - m["growth"]["v"])
        unemp_stress = max(0.0, m["unemployment"]["v"] - 6.0)
        shock_stress = max(0.0, -self.last_world) * 4000.0
        target_ig = BASE_CREDIT_IG_BPS + growth_stress * 25.0 + unemp_stress * 9.0 \
            + shock_stress * 0.25
        target_hy = BASE_CREDIT_HY_BPS + growth_stress * 95.0 + unemp_stress * 35.0 \
            + shock_stress
        target_liq = 100.0 - (m["credit_hy"]["v"] - BASE_CREDIT_HY_BPS) * 0.05 \
            - (8.0 if self.regime in ("Volatil", "Récession") else 0.0)
        m["credit_ig"]["v"] += 0.06 * (target_ig - m["credit_ig"]["v"])
        m["credit_hy"]["v"] += 0.08 * (target_hy - m["credit_hy"]["v"])
        m["liquidity"]["v"] += 0.10 * (target_liq - m["liquidity"]["v"])
        m["credit_ig"]["v"] = min(400.0, max(20.0, m["credit_ig"]["v"]))
        m["credit_hy"]["v"] = min(1500.0, max(100.0, m["credit_hy"]["v"]))
        m["liquidity"]["v"] = min(100.0, max(10.0, m["liquidity"]["v"]))

    def _step_regime(self):
        """Fait évoluer le régime de marché (chaîne de Markov déterministe)."""
        self.regime_changed = False
        u = self.rng.random_sample()
        cum = 0.0
        for name, prob in REGIME_TRANSITIONS[self.regime]:
            cum += prob
            if u <= cum:
                if name != self.regime:
                    self.regime = name
                    self.regime_changed = True
                    self.regime_since = self.step_count
                return
        # reliquat de probabilité -> reste dans le régime courant

    def regime_label(self):
        return REGIMES[self.regime]["label"]

    def regime_age(self):
        """Nombre de pas (semaines) écoulés depuis le début du régime courant —
        donne au joueur une lecture de la maturité du cycle (utile pour le
        market timing et les mandats de gestion de risque)."""
        return max(0, self.step_count - self.regime_since)

    def tension_level(self):
        """Niveau de tension ambiant (0-100), lecture continue du rythme de la
        partie : régime de fond + crises actives (sévérité × volatilité), avec
        une décote pendant l'accalmie forcée qui suit une crise majeure. Donne
        au joueur un indicateur PERSISTANT (pas juste une notif éphémère) pour
        distinguer phase calme / préparation / panique."""
        base = _REGIME_BASE_TENSION.get(self.regime, 20.0)
        crisis_component = sum(
            min(35.0, 14.0 * cr.vol_mult * cr.severity) for cr in self.crises)
        level = base + crisis_component
        if self.crisis_cooldown > 0:
            level *= 0.5
        return round(min(100.0, max(0.0, level)), 1)

    def tension_phase(self):
        """Étiquette qualitative du niveau de tension, pour donner un arc de
        rythme lisible : Accalmie (post-crise) -> Calme -> Préparation ->
        Tension -> Panique."""
        if self.crisis_cooldown > 0:
            return "Accalmie"
        lvl = self.tension_level()
        if lvl < 15.0:
            return "Calme"
        if lvl < 35.0:
            return "Préparation"
        if lvl < 60.0:
            return "Tension"
        return "Panique"

    def _prepare_next_earnings(self, idx):
        """Tire À L'AVANCE la surprise et la guidance du PROCHAIN print pour les
        sociétés d'indice `idx` (appelé à l'initialisation pour le tout 1er
        cycle de chacune, puis une fois par société à chaque fois qu'elle vient
        de publier — jamais une fraction de tirage : la séquence rng consommée
        reste totalement déterminée par (seed, step_count)). C'est ce tirage
        anticipé qui permet le drift de pré-positionnement (cf. _step_anticipation) :
        sans lui, l'anticipation ne pourrait pas être orientée avant le print.

        La guidance est PARTIELLEMENT corrélée à la surprise (GUIDANCE_SURPRISE_CORR)
        mais comporte sa part propre (réalisme : un beat peut suivre une guidance
        prudente et inversement) — combinaison à variance unitaire pour ne pas
        changer l'échelle de GUIDANCE_VOL.
        """
        idx = np.asarray(idx, dtype=int)
        if len(idx) == 0:
            return
        surprise = self.rng.normal(0.0, SURPRISE_VOL, size=len(idx))
        guidance_own = self.rng.normal(0.0, 1.0, size=len(idx))
        rho = GUIDANCE_SURPRISE_CORR
        guidance = GUIDANCE_VOL * (rho * (surprise / SURPRISE_VOL)
                                    + np.sqrt(max(0.0, 1.0 - rho * rho)) * guidance_own)
        self.next_surprise[idx] = surprise
        self.next_guidance[idx] = guidance

    def _step_anticipation(self):
        """Drift de pré-positionnement ("smart money") dans la fenêtre qui
        précède la date de publication CONNUE de chaque société, orienté selon
        la surprise (et la guidance du cycle précédent) déjà tirées à l'avance
        (cf. _prepare_next_earnings). Aucun tirage rng ICI (déterminisme : pas
        de nouveau hasard, seulement une relecture d'état déjà fixé) -> ce
        helper peut être appelé sans risque de désynchroniser la séquence rng.
        Retourne le vecteur de chocs de cours (log) à ajouter au rendement du pas.
        """
        shock = np.zeros(self.n)
        idx = np.arange(self.n)
        steps_to_report = (idx - self.step_count) % EARN_PERIOD
        # strictement AVANT le print (steps_to_report == 0 == jour du print
        # lui-même, déjà couvert par le gap de _step_earnings -> exclu ici).
        in_window = (steps_to_report >= 1) & (steps_to_report <= EARN_ANTICIPATION_WINDOW)
        if not np.any(in_window):
            return shock
        # plus proche du print -> drift plus marqué (rampe linéaire 1/W .. W/W)
        ramp = (EARN_ANTICIPATION_WINDOW - steps_to_report + 1) / float(EARN_ANTICIPATION_WINDOW + 1)
        signal = (self.next_surprise
                  + GUIDANCE_TO_ANTICIPATION_K * self.guidance_bias)
        shock[in_window] = (EARN_ANTICIPATION_K * ramp[in_window] / EARN_ANTICIPATION_WINDOW
                            * signal[in_window])
        return shock

    def _step_revisions(self):
        """Petites révisions d'analystes entre deux trimestres : un tirage de
        Bernoulli (probabilité REVISION_PROBA) PAR SOCIÉTÉ ET PAR PAS, consommé
        systématiquement (même hors fenêtre d'annonce -> jamais de tirage
        sauté), distinct d'un vrai print (pas de mise à jour CA/marges). N'a
        lieu que pour les sociétés qui ne publient pas ce pas-ci (sinon le gap
        de surprise domine déjà). Choc petit et borné, dans le sens du
        signal de révision tiré (indépendant des autres tirages)."""
        shock = np.zeros(self.n)
        idx = np.arange(self.n)
        not_reporting = (idx % EARN_PERIOD) != (self.step_count % EARN_PERIOD)
        roll = self.rng.random_sample(self.n)
        magnitude = self.rng.normal(0.0, REVISION_VOL, size=self.n)
        hit = not_reporting & (roll < REVISION_PROBA)
        if np.any(hit):
            shock[hit] = REVISION_PRICE_K * magnitude[hit]
            # la révision nourrit aussi (modestement) le biais d'anticipation du
            # prochain print, comme une mise à jour d'attentes du marché.
            self.guidance_bias[hit] += 0.3 * magnitude[hit]
        return shock

    def _step_pead(self):
        """Post Earnings Announcement Drift : applique le drift persistant
        accumulé (cf. pead_state, alimenté au moment du print dans
        _step_earnings) puis le fait décroître géométriquement vers 0. Aucun
        tirage rng (pur état déterministe déjà fixé au print)."""
        shock = self.pead_state.copy()
        self.pead_state *= PEAD_DECAY
        return shock

    def _step_earnings(self):
        """Saison de résultats échelonnée : ~1/EARN_PERIOD des sociétés publient
        chaque pas (donc chacune une fois par trimestre). La surprise (beat/miss)
        ÉTAIT DÉJÀ CONNUE à l'avance (cf. _prepare_next_earnings, consommée par le
        drift d'anticipation des pas précédents) : elle fait dériver le CA/les
        marges et injecte un GAP de cours discret (proportionnel à son ampleur,
        au-delà du bruit lissé du pas). La société émet aussi une GUIDANCE
        (composante distincte, impact prix propre plus petit) qui biaise
        l'anticipation du cycle SUIVANT, puis un drift post-annonce (PEAD) est
        amorcé pour les pas suivants. Retourne le vecteur de chocs de cours
        (log) à ajouter au rendement du pas (gap de surprise + impact guidance).
        """
        shock = np.zeros(self.n)
        self.last_earnings = []
        idx = np.arange(self.n)
        due = idx[(idx % EARN_PERIOD) == (self.step_count % EARN_PERIOD)]
        if len(due) == 0:
            return shock
        # croissance trimestrielle « attendue » (déjà dans les cours), liée à la macro
        base_growth = 0.005 + (self.macro["growth"]["v"] - 2.0) * 0.0025
        for i in due:
            i = int(i)
            surprise = float(self.next_surprise[i])
            guidance = float(self.next_guidance[i])
            growth = base_growth + surprise
            self.revenue[i] *= max(0.5, 1.0 + growth)
            # marges : petite dérive bornée autour du profil de base du secteur
            self.net_margin[i] = float(np.clip(
                self.net_margin[i] + self.rng.normal(0, 0.004),
                0.4 * self._base_net_margin[i], 1.6 * self._base_net_margin[i]))
            self.ebitda_margin[i] = float(np.clip(
                self.ebitda_margin[i] + self.rng.normal(0, 0.004),
                0.4 * self._base_ebitda_margin[i], 1.6 * self._base_ebitda_margin[i]))
            # ---- gap d'annonce : choc DISCRET (au-delà du bruit lissé du pas) ----
            # le marché ne réagit qu'à la SURPRISE (la part attendue est déjà
            # priced-in, en partie via l'anticipation des pas précédents) + un
            # impact de guidance distinct, plus petit, dans son propre sens.
            gap = EARN_PRICE_K * surprise
            guidance_impact = GUIDANCE_PRICE_K * guidance
            shock[i] = gap + guidance_impact
            # ---- amorce le drift post-annonce (PEAD), dans le sens de la surprise --
            self.pead_state[i] = PEAD_K * surprise
            # la guidance de CE cycle devient le biais d'anticipation du PROCHAIN
            # (remplace l'ancien biais — pas de cumul indéfini d'un cycle à l'autre)
            self.guidance_bias[i] = guidance
            if guidance > GUIDANCE_RAISE_THRESH:
                g_label = GUIDANCE_LABELS["up"]
            elif guidance < -GUIDANCE_RAISE_THRESH:
                g_label = GUIDANCE_LABELS["down"]
            else:
                g_label = GUIDANCE_LABELS["flat"]
            rep = {"ticker": self.companies[i]["ticker"],
                   "name": self.companies[i]["name"],
                   "surprise": surprise, "growth": growth,
                   "beat": surprise >= 0, "step": self.step_count + 1,
                   "guidance": guidance, "guidance_label": g_label}
            self.last_earnings.append(rep)
            self.earnings_log[rep["ticker"]] = rep
            self.last_guidance[rep["ticker"]] = {
                "value": guidance, "label": g_label, "step": self.step_count + 1}
        # tire dès maintenant la surprise/guidance du PROCHAIN cycle de ces
        # mêmes sociétés (dans EARN_PERIOD pas), pour alimenter l'anticipation
        # à venir -- un seul tirage par société par cycle (cf. docstring ci-dessus).
        self._prepare_next_earnings(due)
        return shock

