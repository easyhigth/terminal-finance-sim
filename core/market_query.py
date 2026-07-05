"""
market_query.py — MarketQueryMixin : méthodes de LECTURE du moteur de marché
(courbe des taux, index/sociétés, recherche, news, attribution P&L...).

Extrait verbatim de core/market.py (aucun changement de logique) : aucune de
ces méthodes ne consomme de tirage rng ni ne fait partie de la séquence
déterministe de Market.step()/_step_* — seul le moteur stochastique reste
dans market.py, pour qu'il soit aussi compact et facile à auditer que possible.
"""
import numpy as np

from core import credit
from core.market_constants import (
    BASE_CREDIT_HY_BPS,
    BASE_CREDIT_IG_BPS,
    CURVE_TENORS,
    CURVE_TERM_PREMIUM,
    EARN_ANTICIPATION_WINDOW,
    EARN_NEWS_THRESH,
    EARN_PERIOD,
    GUIDANCE_LABELS,
    STEPS_PER_YEAR,
    VOL_REGION,
    VOL_SECTOR,
    VOL_WORLD,
    _curve_curvature_target,
    _curve_ns_loadings,
    _curve_slope_target,
)


class MarketQueryMixin:
    def curve_point(self, years, smoothed=False):
        """Rendement de la courbe (décimal) pour une maturité (en années) donnée,
        modèle de Nelson-Siegel à 3 facteurs NIVEAU / PENTE / COURBURE :

            y(years) = [niveau = short + CURVE_TERM_PREMIUM*years]   (legacy, inchangé)
                     + pente_cyclique    * h1(years)
                     + courbure_cyclique * g2(years)

        Par défaut (`smoothed=False`), pente/courbure utilisent la cible
        INSTANTANÉE (fonction pure du régime/croissance/stress courants) :
        lecture réactive immédiate, identique au comportement historique de
        cette méthode (utilisée par les tests, le pricing obligataire au vol,
        et tout code qui lit la courbe APRÈS avoir mute regime/macro à la main
        sans rejouer step()). Avec `smoothed=True`, utilise l'état persistant
        et lissé (curve_slope_state/curve_curv_state, mis à jour pas après pas
        dans step(), mean-reverting vers la cible instantanée) : dynamique
        réaliste pour le gameplay normal, où la courbe ne se redessine pas
        intégralement en un seul pas (cf. curve_slope_state/curve_curv_state).

        À l'état neutre (régime Calme, croissance = mean macro de 2.0, stress
        nul), pente et courbure valent 0 dans les deux cas : la courbe équivaut
        alors exactement à l'ancienne prime de terme fixe (taux court + 0.15%/an)."""
        short = self.macro["rate"]["v"] / 100.0
        h1, g2 = _curve_ns_loadings(years)
        if smoothed:
            slope = self.curve_slope_state
            curv = self.curve_curv_state
        else:
            slope = _curve_slope_target(self.regime, self.macro["growth"]["v"])
            curv = _curve_curvature_target(self.last_stress_level)
        cycle_bias = slope * h1 + curv * g2
        return max(0.0, short + CURVE_TERM_PREMIUM * years + cycle_bias)

    def yield_curve(self, smoothed=False):
        """Courbe complète {tenor: rendement décimal} pour les maturités usuelles."""
        return {tenor: self.curve_point(years, smoothed=smoothed)
                for tenor, years in CURVE_TENORS.items()}

    def curve_slope(self, smoothed=False):
        """Pente 10 ans - 2 ans (en points de %) : lecture usuelle de la forme
        de la courbe (positive = pentue/normale, négative = inversée)."""
        return (self.curve_point(10.0, smoothed=smoothed)
                - self.curve_point(2.0, smoothed=smoothed)) * 100.0

    def curve_curvature(self, smoothed=True):
        """Composante de courbure courante (en points de %) : la "bosse" de
        mi-courbe, qui s'accentue avec le stress de marché. Lissée par défaut
        (état persistant curve_curv_state, dynamique de gameplay normale)."""
        if smoothed:
            return self.curve_curv_state * 100.0
        return _curve_curvature_target(self.last_stress_level) * 100.0

    def curve_inverted(self, smoothed=False):
        return self.curve_slope(smoothed=smoothed) < 0.0

    def curve_phase(self, smoothed=False):
        """Étiquette qualitative de la forme courante de la courbe."""
        slope = self.curve_slope(smoothed=smoothed)
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

    def fast_forward(self, n, progress_cb=None):
        """Rejoue n pas (utilisé au chargement pour resynchroniser l'état).
        `progress_cb(current, total)` est appelé tous les ~50 pas si fourni."""
        total = max(0, int(n))
        for i in range(total):
            self.step()
            if progress_cb and (i % 50 == 0 or i == total - 1):
                progress_cb(i + 1, total)

    def sync_to(self, step_count, progress_cb=None):
        """Resynchronise le marché jusqu'au pas demandé depuis l'origine."""
        if step_count <= self.step_count:
            return
        self.fast_forward(step_count - self.step_count, progress_cb=progress_cb)

    def add_crisis(self, crisis):
        self.crises.append(crisis)
        self.crisis_log.append({"step": self.step_count, "name": crisis.name,
                                 "kind": crisis.kind, "severity": crisis.severity})
        # Son de crise (import lazy pour éviter les imports circulaires)
        try:
            from core import audio
            audio.play("crisis")
        except Exception:
            pass

    def bump_region_credit(self, region, amount):
        """Élargit (amount>0) ou resserre (amount<0) le spread de crédit d'une
        région. Utilisé par les événements politiques pour faire réagir le marché
        obligataire (souverains ET corporates de la zone)."""
        if region in self.region_credit_bump:
            self.region_credit_bump[region] += amount
        else:
            self.region_credit_bump[region] = amount

    # ------------------------------------------------- anticipation (forward-looking)
    def next_step_snapshot(self):
        """Clôtures DÉTERMINISTES du PROCHAIN pas (step_count+1), calculées sans
        muter l'état réel (clone du marché + un step, jeté ensuite). Sert à
        l'animation intraday « forward-looking » : la courbe simule le chemin du
        pas COURANT vers sa destination (le prochain pas), au lieu de rejouer le
        passé. Le déterminisme du moteur est préservé (le clone copie le rng).
        Caché par step_count → un seul clonage par pas, négligeable."""
        if getattr(self, "_next_snap_step", None) == self.step_count:
            return self._next_snap
        import copy
        prev = getattr(self, "_next_snap", None)
        self._next_snap = None                 # ne pas recopier l'ancien snapshot
        try:
            clone = copy.deepcopy(self)
        finally:
            self._next_snap = prev
        clone.step()
        snap = {"price": clone.price.copy(),
                "index": {name: clone.index_value(name) for name in self.index_hist}}
        self._next_snap_step = self.step_count
        self._next_snap = snap
        return snap

    def next_index_value(self, name):
        return self.next_step_snapshot()["index"].get(name)

    def next_price_of(self, ticker):
        i = self.ticker_idx.get(ticker)
        if i is None:
            return None
        return float(self.next_step_snapshot()["price"][i])

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

    def index_history(self, name, sim_clock=None, day=None):
        """Historique par pas de l'indice. Si `sim_clock`/`day` sont fournis,
        un point animé (Round 11 Phase 3 — `core/intraday.py`) est ajouté en
        fin de série pour que le graphe bouge entre deux pas de marché —
        affichage uniquement, n'affecte jamais `index_value()`. Bruit amorti
        (0.6x) par rapport à une société individuelle : un indice diversifié
        bouge naturellement moins que ses constituants."""
        hist = self.index_hist.get(name, [])
        if sim_clock is not None and day is not None and hist:
            from core import intraday
            members = self.index_members.get(name, [])
            sigma = float(np.mean(self.sigma[members])) if len(members) else 0.035
            vol_mult = intraday.vol_mult_for_sigma(sigma, scale=0.6)
            return intraday.append_live(self, sim_clock, day, name, hist, vol_mult=vol_mult,
                                        target=self.next_index_value(name))
        return hist

    def track_company(self, ticker, sim_clock=None, day=None):
        """Démarre le suivi d'historique d'une société (au 1er accès).
        L'historique est pré-rempli depuis le passé complet (5 ans de préhistoire).
        Cf. `index_history` pour `sim_clock`/`day` (animation intraday)."""
        if ticker not in self.price_hist and ticker in self.ticker_idx:
            self.price_hist[ticker] = self.history_of(ticker)
        hist = self.price_hist.get(ticker, [])
        if sim_clock is not None and day is not None and hist:
            from core import intraday
            i = self.ticker_idx.get(ticker)
            region = self.companies[i].get("region") if i is not None else None
            vol_mult = intraday.vol_mult_for_sigma(float(self.sigma[i])) if i is not None else 1.0
            return intraday.append_live(self, sim_clock, day, ticker, hist, region=region,
                                         vol_mult=vol_mult, target=self.next_price_of(ticker))
        return hist

    def history_of(self, ticker, n=None, sim_clock=None, day=None):
        """Historique de prix complet d'une société (depuis la préhistoire de 5 ans).
        `n` borne au dernier n points si fourni. Retourne une liste de floats.
        Cf. `index_history` pour `sim_clock`/`day` (animation intraday).

        Ensures consistent data that can be used for both step-based and intraday
        visualization with proper alignment."""
        i = self.ticker_idx.get(ticker)
        if i is None:
            return []
        snaps = self.price_hist_all[-n:] if n else self.price_hist_all
        hist = [float(s[i]) for s in snaps]

        # Ensure we have enough history points for intraday calculations
        # by extending with the earliest available point if needed
        if n and len(hist) < n:
            needed = n - len(hist)
            if hist:
                # Extend with the first point to maintain consistency
                hist = [hist[0]] * needed + hist

        if sim_clock is not None and day is not None and hist:
            from core import intraday
            region = self.companies[i].get("region")
            vol_mult = intraday.vol_mult_for_sigma(float(self.sigma[i]))
            return intraday.append_live(self, sim_clock, day, ticker, hist, region=region,
                                         vol_mult=vol_mult, target=self.next_price_of(ticker))
        return hist

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
        last_guid = self.last_guidance.get(ticker)
        credit_rating = credit.rating_for(nd_ebitda, float(self.sigma[i]))
        steps_to_report = int((i - self.step_count) % EARN_PERIOD)
        in_anticipation = 1 <= steps_to_report <= EARN_ANTICIPATION_WINDOW
        pead_remaining = float(self.pead_state[i])
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
            "last_guidance": last_guid, "steps_to_earnings": steps_to_report,
            "earnings_anticipation": in_anticipation,
            "pead_drift_remaining": pead_remaining,
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

    def returns_over(self, n_steps):
        """Variation en % sur les `n_steps` derniers pas pour chaque société
        (vectorisé, basé sur l'historique de prix déjà conservé)."""
        hist = self.price_hist_all
        cur = hist[-1]
        idx = max(0, len(hist) - 1 - max(0, int(n_steps)))
        past = hist[idx]
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(past > 0, (cur / past - 1.0) * 100.0, 0.0)

    def top_movers(self, period_steps, region=None, sector=None, by="gain", n=10):
        """Plus fortes hausses/baisses sur une période donnée (en pas de
        marché), au lieu du seul dernier pas (cf. top_companies)."""
        chg = self.returns_over(period_steps)
        idx = [i for i in range(self.n)
               if (region is None or self.companies[i]["region"] == region)
               and (sector is None or self.companies[i]["sector"] == sector)]
        idx.sort(key=lambda i: chg[i], reverse=(by == "gain"))
        out = []
        for i in idx[:n]:
            c = self.companies[i]
            out.append({"ticker": c["ticker"], "name": c["name"], "sector": c["sector"],
                        "region": c["region"], "price": float(self.price[i]),
                        "change_pct": float(chg[i])})
        return out

    def breadth(self, period_steps=1, ma_window=20, lookback_steps=None):
        """Largeur de marché : hausses/baisses, % au-dessus de la moyenne
        mobile, plus hauts/bas sur la fenêtre `lookback_steps` (1 an par
        défaut)."""
        chg = self.returns_over(period_steps)
        advancers = int((chg > 0).sum())
        decliners = int((chg < 0).sum())
        unchanged = self.n - advancers - decliners
        hist = self.price_hist_all
        window = hist[-ma_window:] if len(hist) >= ma_window else hist
        ma = np.mean(np.array(window), axis=0)
        above_ma = int((self.price > ma).sum())
        lb = lookback_steps or STEPS_PER_YEAR
        look = hist[-lb:] if len(hist) >= lb else hist
        arr = np.array(look)
        new_highs = int((self.price >= arr.max(axis=0)).sum())
        new_lows = int((self.price <= arr.min(axis=0)).sum())
        return {
            "advancers": advancers, "decliners": decliners, "unchanged": unchanged,
            "pct_above_ma": (above_ma / self.n * 100.0) if self.n else 0.0,
            "new_highs": new_highs, "new_lows": new_lows,
            "advance_decline_ratio": (advancers / decliners) if decliners else float(advancers),
        }

    def heatmap(self):
        """Grille de performance secteur × région (dernier pas, pondérée par
        capitalisation), pour une vue thermique du marché."""
        ret = (self.beta * self.last_world
               + self.b_sector * self.last_sector[self.sec_id]
               + self.b_region * self.last_region[self.reg_id])
        cap = self.price * self.shares
        grid = []
        for sector in self.sectors:
            row = {"sector": sector, "regions": {}}
            sec_mask = (self.sec_id == self._sector_idx[sector])
            for region in self.regions:
                mask = sec_mask & (self.reg_id == self._region_idx[region])
                w = cap[mask]
                row["regions"][region] = float((ret[mask] * w).sum() / w.sum() * 100.0) if w.sum() > 0 else None
            grid.append(row)
        return grid

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
            text = f"Résultats : {r['ticker']} {verb} ({r['surprise']*100:+.0f}%)"
            g_label = r.get("guidance_label")
            # guidance en désaccord avec la surprise -> info notable pour le joueur
            if g_label and ((r["beat"] and g_label == GUIDANCE_LABELS["down"])
                             or (not r["beat"] and g_label == GUIDANCE_LABELS["up"])):
                text += f", guidance {g_label}"
            news.append({"region": region, "kind": "good" if r["beat"] else "bad", "text": text})
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
