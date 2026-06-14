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
import math
import numpy as np

from data import companies as comp_data

HIST_LEN = 120          # longueur d'historique conservée (pour les graphes)

# Paramètres des facteurs (par pas ≈ une semaine de marché)
# Calibrés pour ~8-12% de rendement annuel moyen et ~15-18% de volatilité.
MU_WORLD = 0.0006       # dérive de marché
VOL_WORLD = 0.017
VOL_SECTOR = 0.012
VOL_REGION = 0.010
DRIFT_MULT = 0.3        # atténue les dérives propres des sociétés (anti sur-bull)


class Crisis:
    """Un scénario de crise actif : chocs additionnels sur des facteurs, sur N pas."""
    def __init__(self, name, steps, world=0.0, regions=None, sectors=None, vol_mult=1.0):
        self.name = name
        self.steps_left = steps
        self.world = world                      # choc additif sur F_monde / pas
        self.regions = regions or {}            # {region_name: choc additif}
        self.sectors = sectors or {}            # {sector_name: choc additif}
        self.vol_mult = vol_mult                # amplificateur de volatilité


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
        self.last_world = 0.0
        self.last_sector = np.zeros(len(self.sectors))
        self.last_region = np.zeros(len(self.regions))
        self.crises = []
        self._last_news = []

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
        }
        self.macro_hist = {k: [self.macro[k]["v"]] for k in self.macro}

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

        # macro : mise à jour + influence (pédagogique) sur les facteurs
        self._step_macro()
        mc = self.macro
        world_shock += (mc["growth"]["v"] - 2.0) * 0.0004        # croissance → vent porteur
        if "Finance" in self._sector_idx:
            sec_shock[self._sector_idx["Finance"]] += -(mc["rate"]["v"] - 2.5) * 0.0016
        if "Immobilier" in self._sector_idx:
            sec_shock[self._sector_idx["Immobilier"]] += -(mc["rate"]["v"] - 2.5) * 0.0020

        F_world = self.rng.normal(MU_WORLD, VOL_WORLD * vol_mult) + world_shock
        F_sector = self.rng.normal(0.0, VOL_SECTOR * vol_mult, size=len(self.sectors)) + sec_shock
        F_region = self.rng.normal(0.0, VOL_REGION * vol_mult, size=len(self.regions)) + reg_shock
        eps = self.rng.normal(0.0, 1.0, size=self.n)

        ret = (self.drift
               + self.beta * F_world
               + self.b_sector * F_sector[self.sec_id]
               + self.b_region * F_region[self.reg_id]
               + self.sigma * eps)
        # borne les rendements par pas pour éviter les valeurs aberrantes
        np.clip(ret, -0.35, 0.35, out=ret)
        self.price *= np.exp(ret)
        np.maximum(self.price, 0.01, out=self.price)

        self.last_world = float(F_world)
        self.last_sector = F_sector
        self.last_region = F_region
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

        # crises : décrément
        for cr in self.crises:
            cr.steps_left -= 1
        self.crises = [cr for cr in self.crises if cr.steps_left > 0]

        self._last_news = self._generate_news(F_world, F_sector, F_region)
        return self._last_news

    def _step_macro(self):
        """Met à jour les indicateurs macro (AR(1) à retour à la moyenne)."""
        m = self.macro
        # banque centrale : la cible de taux suit l'inflation (règle simplifiée)
        m["rate"]["mean"] = max(0.5, 1.0 + 1.0 * m["inflation"]["v"])
        # confiance liée au dernier choc de marché
        m["confidence"]["mean"] = 100.0 + self.last_world * 300
        # chômage inversement lié à la croissance
        m["unemployment"]["mean"] = 5.0 - (m["growth"]["v"] - 2.0) * 0.4
        for d in m.values():
            d["v"] += d["k"] * (d["mean"] - d["v"]) + self.rng.normal(0, d["vol"])
        m["rate"]["v"] = min(12.0, max(0.0, m["rate"]["v"]))
        m["inflation"]["v"] = min(15.0, max(-2.0, m["inflation"]["v"]))
        m["growth"]["v"] = min(8.0, max(-6.0, m["growth"]["v"]))
        m["unemployment"]["v"] = min(20.0, max(2.0, m["unemployment"]["v"]))
        m["confidence"]["v"] = min(140.0, max(50.0, m["confidence"]["v"]))
        for k in m:
            self.macro_hist[k].append(m[k]["v"])
            if len(self.macro_hist[k]) > HIST_LEN:
                self.macro_hist[k].pop(0)

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
        """Démarre le suivi d'historique d'une société (au 1er accès)."""
        if ticker not in self.price_hist and ticker in self.ticker_idx:
            self.price_hist[ticker] = [float(self.price[self.ticker_idx[ticker]])]
        return self.price_hist.get(ticker, [])

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
        net_income = c["revenue"] * c["net_margin"]
        ebitda = c["revenue"] * c["ebitda_margin"]
        eps = net_income / shares if shares else 0.0
        pe = price / eps if eps > 0 else None
        ev = mktcap + c["net_debt"]
        ev_ebitda = ev / ebitda if ebitda > 0 else None
        # variation depuis le début de l'historique suivi
        hist = self.price_hist.get(ticker)
        chg = ((hist[-1] / hist[0] - 1) * 100.0) if hist and len(hist) > 1 and hist[0] else 0.0
        ps = mktcap / c["revenue"] if c["revenue"] else None
        fcf_yield = (net_income / mktcap * 100) if mktcap else None   # proxy FCF≈RN
        nd_ebitda = c["net_debt"] / ebitda if ebitda > 0 else None
        div_per_share = price * c["div_yield"]
        payout = (div_per_share / eps * 100) if eps > 0 else None
        return {
            "ticker": ticker, "name": c["name"], "region": c["region"],
            "sector": c["sector"], "price": price, "shares": shares,
            "mktcap": mktcap, "revenue": c["revenue"], "ebitda": ebitda,
            "net_income": net_income, "eps": eps, "pe": pe, "ev": ev,
            "ev_ebitda": ev_ebitda, "net_debt": c["net_debt"],
            "div_yield": c["div_yield"], "beta": c["beta"],
            "net_margin": c["net_margin"], "ebitda_margin": c["ebitda_margin"],
            "ps": ps, "fcf_yield": fcf_yield, "nd_ebitda": nd_ebitda,
            "payout": payout, "change_pct": chg,
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

    def top_companies(self, region=None, n=8, by="mktcap"):
        """Top sociétés (par capi par défaut, ou 'gain'/'loss' du dernier pas)."""
        idx = [i for i in range(self.n)
               if region is None or self.companies[i]["region"] == region]
        if by == "mktcap":
            idx.sort(key=lambda i: self.price[i] * self.shares[i], reverse=True)
        else:
            # mouvement du dernier pas approché par le rendement implicite
            ret = (self.beta * self.last_world
                   + self.b_sector * self.last_sector[self.sec_id]
                   + self.b_region * self.last_region[self.reg_id])
            order = list(idx)
            order.sort(key=lambda i: ret[i], reverse=(by == "gain"))
            idx = order
        out = []
        for i in idx[:n]:
            c = self.companies[i]
            out.append({"ticker": c["ticker"], "name": c["name"],
                        "sector": c["sector"], "region": c["region"],
                        "price": float(self.price[i]),
                        "mktcap": float(self.price[i] * self.shares[i])})
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

    def latest_news(self):
        return self._last_news
