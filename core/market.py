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

from core import credit
from core.applog import logger
from data import companies as comp_data

HIST_LEN = 400          # ~5.4 ans d'historique conservé (pour les graphes)

# Passé reconstruit AVANT le jour 1 d'une nouvelle partie : les graphes ont ainsi
# de l'ancienneté dès le début (analyse technique, vol, bêta, corrélations...).
# Le marché restant déterministe (graine, nb de pas), ce passé est simplement le
# fait de démarrer la carrière à market_step = WARMUP_STEPS.
STEPS_PER_YEAR = 73     # ~365 jours / DAYS_PER_STEP(5) — pas de marché par an
WARMUP_YEARS = 5
WARMUP_STEPS = WARMUP_YEARS * STEPS_PER_YEAR   # = 365 pas (~5 ans) de préhistoire

# Paramètres des facteurs (par pas ≈ une semaine de marché). Calibrés (sur 12
# graines, 10 ans) pour une PRIME DE RISQUE ACTIONS positive : action moyenne
# ~7%/an (vs cash ~3%, obligations IG ~5%), volatilité ~16%, indice phare ~16%
# (dominé par les grandes capi). Voir tests/test_market.py.
MU_WORLD = 0.0011       # dérive de marché (prime de risque actions)
VOL_WORLD = 0.017
VOL_SECTOR = 0.012
VOL_REGION = 0.010
DRIFT_MULT = 0.2        # atténue les dérives propres des sociétés (anti sur-bull)

# Régimes de marché — toile de fond lente (déterministe) par-dessus les crises.
# Chaque régime module la dérive et la volatilité du facteur MONDE. Les écarts
# entre régimes sont volontairement marqués (et leur persistance élevée, cf.
# REGIME_TRANSITIONS) pour que des phases bull/bear durables émergent, lisibles
# et exploitables par le market timing — au-delà des chocs ponctuels (Crisis).
REGIMES = {
    "Expansion":  {"drift": 0.0008,  "vol": 0.85, "label": "Expansion"},
    "Calme":      {"drift": 0.0001,  "vol": 0.75, "label": "Marché calme"},
    "Volatil":    {"drift": -0.0004, "vol": 1.70, "label": "Marché volatil"},
    "Récession":  {"drift": -0.0016, "vol": 2.00, "label": "Récession"},
}
# Matrice de transition (par pas ≈ 1 semaine) : forte probabilité de rester dans
# le régime courant -> durée moyenne d'un cycle de l'ordre de plusieurs trimestres
# (1/(1-p_auto) pas), pour des phases identifiables plutôt que du bruit régime à
# régime. Les voisins probables restent cohérents (Expansion <-> Calme,
# Volatil <-> Récession) ; un retournement direct Expansion <-> Récession est rare.
REGIME_TRANSITIONS = {
    "Expansion":  [("Expansion", 0.96), ("Calme", 0.025), ("Volatil", 0.015)],
    "Calme":      [("Calme", 0.95), ("Expansion", 0.035), ("Volatil", 0.015)],
    "Volatil":    [("Volatil", 0.92), ("Calme", 0.04), ("Récession", 0.04)],
    "Récession":  [("Récession", 0.94), ("Volatil", 0.05), ("Calme", 0.01)],
}

# Résultats trimestriels (« earnings ») — saison échelonnée, déterministe
EARN_PERIOD = 13        # ~13 pas (semaines) = un trimestre ; report échelonné
SURPRISE_VOL = 0.05     # écart-type de la surprise de résultats (en % de croissance)
EARN_PRICE_K = 0.9      # conversion surprise -> choc de cours du jour de publication
EARN_NEWS_THRESH = 0.06 # |surprise| au-delà de laquelle on génère une news


CRISIS_SEVERE_SEVERITY = 1.35  # seuil au-delà duquel une crise est jugée "majeure"
CRISIS_COOLDOWN_STEPS = 5      # accalmie forcée après une crise majeure (pas de nouveau choc)

# Courbe des taux : DÉRIVÉE du taux directeur courant + une pente qui dépend du
# cycle (régime + croissance), pas un indicateur mean-reverting séparé. À l'état
# neutre (régime Calme, croissance = mean macro), elle se réduit à l'ancienne
# prime de terme fixe (CURVE_TERM_PREMIUM == ancien core.bonds.TERM_PREMIUM),
# pour ne pas changer les niveaux de rendement déjà calibrés.
CURVE_TENORS = {"3M": 0.25, "2Y": 2.0, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0}
CURVE_TERM_PREMIUM = 0.0015
# pentification en expansion (le marché anticipe une croissance soutenue),
# aplatissement/inversion en marché volatil/récession (le marché anticipe des
# baisses de taux directeur futures) — capé aux 10 premières années (la partie
# longue de la courbe réagit peu au cycle court terme).
_REGIME_SLOPE_BIAS = {"Expansion": 0.0028, "Calme": 0.0, "Volatil": -0.0065, "Récession": -0.015}

# Spreads de crédit IG/HY — niveaux de référence (en points de base), utilisés
# comme indicateurs macro centraux de stress de marché (core.bonds les lit pour
# faire varier le coût d'emprunt des émetteurs notés, core.scenarios pour faire
# dépendre la probabilité de crise de conditions macro cohérentes).
BASE_CREDIT_IG_BPS = 90.0
BASE_CREDIT_HY_BPS = 380.0

# tension ambiante de fond par régime (toile de fond lente, cf. _step_regime) —
# base du niveau de tension affiché au joueur, avant prise en compte des crises actives.
_REGIME_BASE_TENSION = {"Expansion": 8.0, "Calme": 4.0, "Volatil": 42.0, "Récession": 58.0}


class Crisis:
    """Un scénario de crise actif : chocs additionnels sur des facteurs, sur N pas."""
    def __init__(self, name, steps, world=0.0, regions=None, sectors=None, vol_mult=1.0,
                 severity=1.0, kind="bad"):
        self.name = name
        self.steps_left = steps
        self.total_steps = steps
        self.world = world                      # choc additif sur F_monde / pas
        self.regions = regions or {}            # {region_name: choc additif}
        self.sectors = sectors or {}            # {sector_name: choc additif}
        self.vol_mult = vol_mult                # amplificateur de volatilité
        self.severity = severity                # intensité tirée à l'origine (cf. scenarios.py)
        self.kind = kind                         # "bad"/"good" — pour la narration du postmortem
        self.start_nw = None                    # snapshot patrimoine net, posé par l'appelant


class Market:
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
        self.earnings_log = {}       # ticker -> dernier rapport {surprise, growth, beat, step}
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

        F_world = self.rng.normal(MU_WORLD + reg["drift"], VOL_WORLD * vol_mult) + world_shock
        F_sector = self.rng.normal(0.0, VOL_SECTOR * vol_mult, size=len(self.sectors)) + sec_shock
        F_region = self.rng.normal(0.0, VOL_REGION * vol_mult, size=len(self.regions)) + reg_shock
        eps = self.rng.normal(0.0, 1.0, size=self.n)

        # saison de résultats : choc de cours sur les sociétés qui publient ce pas
        earnings_shock = self._step_earnings()

        ret = (self.drift
               + self.beta * F_world
               + self.b_sector * F_sector[self.sec_id]
               + self.b_region * F_region[self.reg_id]
               + self.sigma * eps
               + earnings_shock)
        # borne les rendements par pas pour éviter les valeurs aberrantes
        np.clip(ret, -0.35, 0.35, out=ret)
        self.prev_price = self.price.copy()   # mémorise pour l'attribution du P&L
        self.price *= np.exp(ret)
        np.maximum(self.price, 0.01, out=self.price)

        self.last_world = float(F_world)
        self.last_sector = F_sector
        self.last_region = F_region
        self.last_ret = ret.copy()
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

    def _step_earnings(self):
        """Saison de résultats échelonnée : ~1/EARN_PERIOD des sociétés publient
        chaque pas (donc chacune une fois par trimestre). Une SURPRISE (beat/miss)
        fait dériver le CA et les marges et injecte un choc de cours déterministe.
        Retourne le vecteur de chocs de cours (log) à ajouter au rendement du pas.
        """
        shock = np.zeros(self.n)
        self.last_earnings = []
        idx = np.arange(self.n)
        due = idx[(idx % EARN_PERIOD) == (self.step_count % EARN_PERIOD)]
        if len(due) == 0:
            return shock
        # croissance trimestrielle « attendue » (déjà dans les cours), liée à la macro
        base_growth = 0.005 + (self.macro["growth"]["v"] - 2.0) * 0.0025
        surprises = self.rng.normal(0.0, SURPRISE_VOL, size=len(due))
        for k, i in enumerate(due):
            surprise = float(surprises[k])
            growth = base_growth + surprise
            self.revenue[i] *= max(0.5, 1.0 + growth)
            # marges : petite dérive bornée autour du profil de base du secteur
            self.net_margin[i] = float(np.clip(
                self.net_margin[i] + self.rng.normal(0, 0.004),
                0.4 * self._base_net_margin[i], 1.6 * self._base_net_margin[i]))
            self.ebitda_margin[i] = float(np.clip(
                self.ebitda_margin[i] + self.rng.normal(0, 0.004),
                0.4 * self._base_ebitda_margin[i], 1.6 * self._base_ebitda_margin[i]))
            # le marché ne réagit qu'à la SURPRISE (la part attendue est déjà priced-in)
            shock[i] = EARN_PRICE_K * surprise
            rep = {"ticker": self.companies[i]["ticker"],
                   "name": self.companies[i]["name"],
                   "surprise": surprise, "growth": growth,
                   "beat": surprise >= 0, "step": self.step_count + 1}
            self.last_earnings.append(rep)
            self.earnings_log[rep["ticker"]] = rep
        return shock

    def curve_point(self, years):
        """Rendement de la courbe (décimal) pour une maturité (en années) donnée.
        À l'état neutre (régime Calme, croissance = mean macro de 2.0), équivaut
        exactement à l'ancienne prime de terme fixe (taux court + 0.15%/an)."""
        short = self.macro["rate"]["v"] / 100.0
        growth_bias = (self.macro["growth"]["v"] - 2.0) * 0.0015
        # poids 0 (très court terme) -> 1 (10 ans et plus) : la partie courte de
        # la courbe suit surtout le taux directeur, la partie longue capte le
        # cycle (pentification/inversion).
        weight = min(years, 10.0) / 10.0
        cycle_bias = (_REGIME_SLOPE_BIAS.get(self.regime, 0.0) + growth_bias) * weight
        return max(0.0, short + CURVE_TERM_PREMIUM * years + cycle_bias)

    def yield_curve(self):
        """Courbe complète {tenor: rendement décimal} pour les maturités usuelles."""
        return {tenor: self.curve_point(years) for tenor, years in CURVE_TENORS.items()}

    def curve_slope(self):
        """Pente 10 ans - 2 ans (en points de %) : lecture usuelle de la forme
        de la courbe (positive = pentue/normale, négative = inversée)."""
        return (self.curve_point(10.0) - self.curve_point(2.0)) * 100.0

    def curve_inverted(self):
        return self.curve_slope() < 0.0

    def curve_phase(self):
        """Étiquette qualitative de la forme courante de la courbe."""
        slope = self.curve_slope()
        if slope < -0.05:
            return "Inversion"
        if slope < 0.30:
            return "Aplatissement"
        if slope < 1.0:
            return "Normale"
        return "Pentification"

    def credit_spread_multiplier(self, rating):
        """Multiplicateur (autour de 1.0) à appliquer au spread de crédit de base
        d'un rating, selon que les conditions de crédit IG/HY courantes sont plus
        tendues ou plus détendues que leur niveau de référence. Lu par core.bonds
        pour faire varier dynamiquement le coût d'emprunt des émetteurs notés."""
        if rating in ("BB", "B"):
            return max(0.4, self.macro["credit_hy"]["v"] / BASE_CREDIT_HY_BPS)
        return max(0.4, self.macro["credit_ig"]["v"] / BASE_CREDIT_IG_BPS)

    def macro_change(self, key):
        """Variation de l'indicateur depuis ~1 an (20 pas) pour l'affichage."""
        h = self.macro_hist.get(key, [])
        if len(h) < 2:
            return 0.0
        ref = h[-min(len(h), 20)]
        return h[-1] - ref

    def fast_forward(self, n):
        """Rejoue n pas (utilisé au chargement pour resynchroniser l'état)."""
        for _ in range(max(0, int(n))):
            self.step()

    def sync_to(self, step_count):
        """Resynchronise le marché jusqu'au pas demandé depuis l'origine."""
        if step_count <= self.step_count:
            return
        self.fast_forward(step_count - self.step_count)

    def add_crisis(self, crisis):
        self.crises.append(crisis)

    def bump_region_credit(self, region, amount):
        """Élargit (amount>0) ou resserre (amount<0) le spread de crédit d'une
        région. Utilisé par les événements politiques pour faire réagir le marché
        obligataire (souverains ET corporates de la zone)."""
        if region in self.region_credit_bump:
            self.region_credit_bump[region] += amount
        else:
            self.region_credit_bump[region] = amount

    # -------------------------------------------------------------- requêtes
    def index_value(self, name):
        members = self.index_members[name]
        cap = float(np.sum(self.price[members] * self.shares[members]))
        return cap * self.index_scale[name]

    def index_change_pct(self, name):
        hist = self.index_hist.get(name)
        if not hist or len(hist) < 2 or hist[-2] == 0:
            return 0.0
        return (hist[-1] / hist[-2] - 1.0) * 100.0

    def index_history(self, name):
        return self.index_hist.get(name, [])

    def track_company(self, ticker):
        """Démarre le suivi d'historique d'une société (au 1er accès).
        L'historique est pré-rempli depuis le passé complet (5 ans de préhistoire)."""
        if ticker not in self.price_hist and ticker in self.ticker_idx:
            self.price_hist[ticker] = self.history_of(ticker)
        return self.price_hist.get(ticker, [])

    def history_of(self, ticker, n=None):
        """Historique de prix complet d'une société (depuis la préhistoire de 5 ans).
        `n` borne au dernier n points si fourni. Retourne une liste de floats."""
        i = self.ticker_idx.get(ticker)
        if i is None:
            return []
        snaps = self.price_hist_all[-n:] if n else self.price_hist_all
        return [float(s[i]) for s in snaps]

    def price_of(self, ticker):
        i = self.ticker_idx.get(ticker)
        return float(self.price[i]) if i is not None else None

    def metrics(self, ticker):
        """Renvoie les fondamentaux + métriques de valorisation d'une société."""
        i = self.ticker_idx.get(ticker)
        if i is None:
            return None
        c = self.companies[i]
        price = float(self.price[i])
        shares = c["shares"]
        mktcap = price * shares
        revenue = float(self.revenue[i])        # fondamentaux dynamiques (earnings)
        net_margin = float(self.net_margin[i])
        ebitda_margin = float(self.ebitda_margin[i])
        net_income = revenue * net_margin
        ebitda = revenue * ebitda_margin
        eps = net_income / shares if shares else 0.0
        pe = price / eps if eps > 0 else None
        ev = mktcap + c["net_debt"]
        ev_ebitda = ev / ebitda if ebitda > 0 else None
        # variation sur 1 an (YoY) — disponible dès le jour 1 grâce à la préhistoire
        hist = self.history_of(ticker, STEPS_PER_YEAR + 1)
        chg = ((hist[-1] / hist[0] - 1) * 100.0) if len(hist) > 1 and hist[0] else 0.0
        ps = mktcap / revenue if revenue else None
        fcf_yield = (net_income / mktcap * 100) if mktcap else None   # proxy FCF≈RN
        nd_ebitda = c["net_debt"] / ebitda if ebitda > 0 else None
        div_per_share = price * c["div_yield"]
        payout = (div_per_share / eps * 100) if eps > 0 else None
        last_earn = self.earnings_log.get(ticker)
        credit_rating = credit.rating_for(nd_ebitda, float(self.sigma[i]))
        return {
            "ticker": ticker, "name": c["name"], "region": c["region"],
            "sector": c["sector"], "price": price, "shares": shares,
            "mktcap": mktcap, "revenue": revenue, "ebitda": ebitda,
            "net_income": net_income, "eps": eps, "pe": pe, "ev": ev,
            "ev_ebitda": ev_ebitda, "net_debt": c["net_debt"],
            "div_yield": c["div_yield"], "beta": c["beta"],
            "net_margin": net_margin, "ebitda_margin": ebitda_margin,
            "ps": ps, "fcf_yield": fcf_yield, "nd_ebitda": nd_ebitda,
            "payout": payout, "change_pct": chg, "last_earnings": last_earn,
            "credit_rating": credit_rating,
        }

    def sector_medians(self, sector):
        """Médianes sectorielles des multiples (pour la valeur relative RV)."""
        import statistics
        pes, evs, pss = [], [], []
        for c in self.companies:
            if c["sector"] != sector:
                continue
            mt = self.metrics(c["ticker"])
            if mt["pe"]:
                pes.append(mt["pe"])
            if mt["ev_ebitda"]:
                evs.append(mt["ev_ebitda"])
            if mt["ps"]:
                pss.append(mt["ps"])
        med = lambda xs: statistics.median(xs) if xs else None
        return {"pe": med(pes), "ev_ebitda": med(evs), "ps": med(pss), "n": len(pes)}

    def top_companies(self, region=None, sector=None, n=8, by="mktcap"):
        """Top sociétés (par capi par défaut, ou 'gain'/'loss' du dernier pas)."""
        idx = [i for i in range(self.n)
               if (region is None or self.companies[i]["region"] == region)
               and (sector is None or self.companies[i]["sector"] == sector)]
        ret = (self.beta * self.last_world
               + self.b_sector * self.last_sector[self.sec_id]
               + self.b_region * self.last_region[self.reg_id])
        if by == "mktcap":
            idx.sort(key=lambda i: self.price[i] * self.shares[i], reverse=True)
        else:
            # mouvement du dernier pas approché par le rendement implicite
            order = list(idx)
            order.sort(key=lambda i: ret[i], reverse=(by == "gain"))
            idx = order
        out = []
        for i in idx[:n]:
            c = self.companies[i]
            out.append({"ticker": c["ticker"], "name": c["name"],
                        "sector": c["sector"], "region": c["region"],
                        "price": float(self.price[i]),
                        "mktcap": float(self.price[i] * self.shares[i]),
                        "change_pct": float(ret[i]) * 100.0})
        return out

    def sector_performance(self):
        """Performance moyenne (du dernier pas, pondérée par capi) de chaque
        secteur, triée du plus fort au plus faible. Réutilise l'approximation
        de rendement de top_companies(by='gain'/'loss')."""
        ret = (self.beta * self.last_world
               + self.b_sector * self.last_sector[self.sec_id]
               + self.b_region * self.last_region[self.reg_id])
        cap = self.price * self.shares
        out = []
        for sector in self.sectors:
            mask = (self.sec_id == self._sector_idx[sector])
            w = cap[mask]
            if w.sum() <= 0:
                avg = 0.0
            else:
                avg = float((ret[mask] * w).sum() / w.sum())
            out.append({"sector": sector, "change_pct": avg * 100.0,
                        "mktcap": float(w.sum()), "n": int(mask.sum())})
        out.sort(key=lambda s: s["change_pct"], reverse=True)
        return out

    def search(self, query, limit=12):
        """Recherche par ticker ou nom (insensible à la casse)."""
        q = query.strip().lower()
        if not q:
            return []
        out = []
        for c in self.companies:
            if q in c["ticker"].lower() or q in c["name"].lower():
                out.append(c["ticker"])
            if len(out) >= limit:
                break
        return out

    def suggest(self, query, limit=8):
        """Recherche INTELLIGENTE : suggestions (ticker, name) pour une saisie
        libre (ticker ou nom, partiel), classées par pertinence — exact, puis
        préfixe, puis sous-chaîne. Évite d'avoir à connaître les tickers par cœur."""
        q = query.strip().lower()
        if not q:
            return []
        exact, prefix, contains = [], [], []
        for c in self.companies:
            tk, nm = c["ticker"].lower(), c["name"].lower()
            pair = (c["ticker"], c["name"])
            if tk == q:
                exact.append(pair)
            elif tk.startswith(q) or nm.startswith(q):
                prefix.append(pair)
            elif q in tk or q in nm:
                contains.append(pair)
        return (exact + prefix + contains)[:limit]

    def resolve(self, query):
        """Meilleur ticker correspondant à une recherche libre, ou None.
        'MVC' -> MVC ; 'mavric' -> MVC ; 'comp' -> 1re société contenant 'comp'."""
        q = query.strip().upper()
        if q in self.ticker_idx:
            return q
        hits = self.suggest(query, 1)
        return hits[0][0] if hits else None

    # -------------------------------------------------------------- news
    def _generate_news(self, F_world, F_sector, F_region):
        """Génère 0..3 news selon l'ampleur des chocs du pas (pour la carte)."""
        news = []
        # choc mondial marquant
        if abs(F_world) > VOL_WORLD * 1.6:
            kind = "good" if F_world > 0 else "bad"
            txt = ("Vague d'optimisme sur les marchés mondiaux"
                   if F_world > 0 else "Aversion au risque généralisée")
            news.append({"region": None, "kind": kind, "text": txt})
        # secteurs marquants
        order = np.argsort(-np.abs(F_sector))
        for k in order[:2]:
            if abs(F_sector[k]) > VOL_SECTOR * 1.7:
                sec = self.sectors[k]
                up = F_sector[k] > 0
                news.append({"region": None, "kind": "good" if up else "bad",
                             "text": f"Secteur {sec} {'en forte hausse' if up else 'sous pression'}"})
        # régions marquantes
        for ri, region in enumerate(self.regions):
            if abs(F_region[ri]) > VOL_REGION * 1.8:
                up = F_region[ri] > 0
                news.append({"region": region, "kind": "good" if up else "bad",
                             "text": f"{region} : séance {'haussière' if up else 'baissière'} marquée"})
        return news[:3]

    def _earnings_news(self):
        """News pour les surprises de résultats les plus marquantes du pas."""
        news = []
        big = sorted(self.last_earnings, key=lambda r: -abs(r["surprise"]))
        for r in big[:2]:
            if abs(r["surprise"]) < EARN_NEWS_THRESH:
                break
            region = next((c["region"] for c in self.companies
                           if c["ticker"] == r["ticker"]), None)
            verb = "dépasse les attentes" if r["beat"] else "déçoit"
            news.append({"region": region, "kind": "good" if r["beat"] else "bad",
                         "text": f"Résultats : {r['ticker']} {verb} ({r['surprise']*100:+.0f}%)"})
        return news

    def latest_news(self):
        return self._last_news

    # -------------------------------------------------------- attribution P&L
    def factor_attribution(self, holdings):
        """Décompose le P&L de PRIX des positions sur le dernier pas par facteur.

        `holdings` : dict ticker -> nombre d'actions.
        Le rendement de chaque société se décompose (en log) en
        dérive + monde + secteur + région + spécifique ; on répartit le gain/perte
        en devise de chaque position au prorata de ces composantes. La somme des
        composantes égale exactement le P&L de prix total des positions.

        Retourne {world, sector, region, specific, drift, total} (en devise).
        """
        out = {"world": 0.0, "sector": 0.0, "region": 0.0,
               "specific": 0.0, "drift": 0.0, "total": 0.0}
        if self.prev_price is None or self.last_ret is None:
            return out
        for tk, shares in holdings.items():
            i = self.ticker_idx.get(tk)
            if i is None or not shares:
                continue
            prev = float(self.prev_price[i])
            pnl = shares * (float(self.price[i]) - prev)
            out["total"] += pnl
            total_log = float(self.last_ret[i])
            if abs(total_log) < 1e-12:
                out["specific"] += pnl
                continue
            c_drift = float(self.drift[i])
            c_world = float(self.beta[i]) * self.last_world
            c_sector = float(self.b_sector[i]) * float(self.last_sector[self.sec_id[i]])
            c_region = float(self.b_region[i]) * float(self.last_region[self.reg_id[i]])
            c_specific = total_log - c_drift - c_world - c_sector - c_region
            out["drift"] += pnl * c_drift / total_log
            out["world"] += pnl * c_world / total_log
            out["sector"] += pnl * c_sector / total_log
            out["region"] += pnl * c_region / total_log
            out["specific"] += pnl * c_specific / total_log
        return out
