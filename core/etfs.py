"""
etfs.py — Fonds indiciels (ETF) tradables (logique pure, sans pygame).

Un ETF est un PANIER : il n'a pas de prix propre tiré au hasard, sa valeur
liquidative (NAV) ÉMERGE de son exposition, exactement comme les indices du
moteur de marché. Conséquence « gratuite » : un ETF réagit de façon cohérente
aux mêmes facteurs que ses sous-jacents — monde, secteur, région, taux,
inflation — sans aléa supplémentaire (déterminisme préservé : la NAV se
reconstruit depuis les historiques déjà stockés par core/market.py).

Familles d'ETF (cf. CATEGORIES) :
  - actions : large/monde/régions/pays/secteurs/styles/thématiques/ESG/REIT ;
  - obligataires : souverains, corporate, high yield, indexés inflation, court/long ;
  - commodities : adossés aux trajectoires de core/commodities ;
  - devises : panier FX déterministe sensible aux taux ;
  - à effet de levier / inverses : transformation quotidienne d'un ETF de base
    (clairement marqués « risque élevé » — décroissance de volatilité réaliste).

Moteur de prix
--------------
Pour chaque ETF on construit une SÉRIE de NAV alignée sur l'historique du marché
(``market.price_hist_all`` pour les actions, ``market.macro_hist['rate']`` pour
les taux, ``core/commodities.history`` pour les matières premières). La NAV est
un rendement TOTAL (dividendes/coupons réinvestis), nette des frais de gestion.

Holdings : PlayerState.etfs = { etf_id : {"qty": parts, "avg": NAV moyenne} }.
Instruments au comptant (long only, réglés cash), comme les obligations : pas de
levier sur la position elle-même — l'effet de levier est porté par les ETF
dédiés (TQQ, SQQ…).
"""
import numpy as np

from core import config, finmath
from data import companies as comp_data

COMMISSION = 0.001        # 10 bps sur le notionnel échangé
_DT = config.DAYS_PER_STEP / 365.0   # fraction d'année par pas de marché
_FACE = 1000.0            # nominal de référence pour le pricing obligataire

# Spread de crédit par rating (repris de core/bonds, cohérence du marché).
_RATING_SPREAD = {"AAA": 0.002, "AA": 0.004, "A": 0.007,
                  "BBB": 0.013, "BB": 0.030, "B": 0.055}

# Ordre + libellés d'affichage des grandes familles (lisibilité joueur).
CATEGORIES = [
    ("broad",     "Large / Broad"),
    ("world",     "Monde"),
    ("region",    "Régions"),
    ("country",   "Pays"),
    ("sector",    "Secteurs"),
    ("style",     "Styles (factoriel)"),
    ("thematic",  "Thématiques"),
    ("esg",       "ESG / Durable"),
    ("reit",      "Immobilier / REIT"),
    ("bond",      "Obligataire"),
    ("commodity", "Commodities"),
    ("currency",  "Devises"),
    ("leveraged", "Levier / Inverse"),
]
CATEGORY_LABEL = {k: v for k, v in CATEGORIES}


# --------------------------------------------------------------------------
# Définition de l'univers d'ETF (déterministe, construit une fois à l'import)
# --------------------------------------------------------------------------
def _eq(regions=None, sectors=None, style=None, theme=None, n=60,
        exclude_sectors=None, glob=False):
    return {"type": "equity", "regions": regions, "sectors": sectors,
            "style": style, "theme": theme, "n": n,
            "exclude_sectors": exclude_sectors or [], "glob": glob}


def _bd(years, rating="AAA", coupon=None, infl=False, eq_beta=0.0, region=None):
    return {"type": "bond", "years": years, "rating": rating,
            "coupon": coupon, "infl": infl, "eq_beta": eq_beta, "region": region}


def _cm(basket):
    return {"type": "commodity", "basket": basket}


def _fx(drift=0.0, vol=0.07, rate_beta=0.0):
    return {"type": "currency", "drift": drift, "vol": vol, "rate_beta": rate_beta}


def _lev(base, factor):
    return {"type": "leveraged", "base": base, "factor": factor}


# (id, nom, catégorie, sous-catégorie, risque 1-5, frais annuels, moteur)
_DEFS = [
    # ---- Large / Broad ----
    ("VTW", "Monde Actions Total", "broad", "Capi mondiale", 2, 0.0020,
     _eq(glob=True, n=320)),
    ("SPX", "C&D 500 Tracker", "broad", "Grandes capi USA", 2, 0.0009,
     _eq(regions=["USA"], n=90)),
    ("MID", "Mid Caps Monde", "broad", "Moyennes capi", 3, 0.0025,
     _eq(glob=True, n=320, style="mid")),
    ("SML", "Small Caps Monde", "broad", "Petites capi", 4, 0.0030,
     _eq(glob=True, n=320, style="small")),
    ("EWQ", "Monde Équipondéré", "broad", "Équipondéré", 3, 0.0022,
     _eq(glob=True, n=160, style="equal")),

    # ---- Monde ----
    ("DEV", "Marchés Développés", "world", "Développés", 2, 0.0018,
     _eq(regions=["USA", "Europe", "Asia", "Am.Nord", "Océanie"], n=180)),
    ("EMG", "Marchés Émergents", "world", "Émergents", 4, 0.0035,
     _eq(regions=["Am.Sud", "Afrique", "Asia"], n=120)),
    ("EXUS", "Monde hors USA", "world", "Ex-USA", 3, 0.0025,
     _eq(regions=["Europe", "Asia", "Am.Nord", "Am.Sud", "Afrique", "Océanie"], n=160)),

    # ---- Régions ----
    ("USA", "Actions USA", "region", "USA", 2, 0.0012, _eq(regions=["USA"], n=90)),
    ("EUR", "Actions Europe", "region", "Europe", 2, 0.0018, _eq(regions=["Europe"], n=60)),
    ("ASI", "Actions Asie", "region", "Asia", 3, 0.0022, _eq(regions=["Asia"], n=80)),
    ("NAM", "Actions Am. Nord", "region", "Am.Nord", 3, 0.0020, _eq(regions=["Am.Nord"], n=45)),
    ("LAT", "Actions Am. Latine", "region", "Am.Sud", 4, 0.0035, _eq(regions=["Am.Sud"], n=50)),
    ("AFR", "Actions Afrique", "region", "Afrique", 5, 0.0045, _eq(regions=["Afrique"], n=35)),
    ("OCE", "Actions Océanie", "region", "Océanie", 3, 0.0030, _eq(regions=["Océanie"], n=45)),

    # ---- Pays (sous-paniers déterministes au sein d'une région) ----
    ("JPN", "Actions Japon", "country", "Japon", 3, 0.0025, _eq(regions=["Asia"], theme="jpn", n=80)),
    ("CHN", "Actions Chine", "country", "Chine", 4, 0.0035, _eq(regions=["Asia"], theme="chn", n=80)),
    ("DEU", "Actions Allemagne", "country", "Allemagne", 2, 0.0022, _eq(regions=["Europe"], theme="deu", n=60)),
    ("FRA", "Actions France", "country", "France", 2, 0.0022, _eq(regions=["Europe"], theme="fra", n=60)),
    ("GBR", "Actions Royaume-Uni", "country", "Royaume-Uni", 3, 0.0024, _eq(regions=["Europe"], theme="gbr", n=60)),
    ("BRA", "Actions Brésil", "country", "Brésil", 4, 0.0040, _eq(regions=["Am.Sud"], theme="bra", n=50)),
    ("IND", "Actions Inde", "country", "Inde", 4, 0.0040, _eq(regions=["Asia"], theme="ind", n=80)),
    ("CAN", "Actions Canada", "country", "Canada", 3, 0.0026, _eq(regions=["Am.Nord"], theme="can", n=45)),
    ("ZAF", "Actions Afrique du Sud", "country", "Afrique du Sud", 5, 0.0048, _eq(regions=["Afrique"], theme="zaf", n=35)),

    # ---- Secteurs ----
    ("XLK", "Secteur Technologie", "sector", "Tech", 3, 0.0012, _eq(sectors=["Tech"], n=80)),
    ("XSM", "Secteur Semiconducteurs", "sector", "Semicon", 4, 0.0015, _eq(sectors=["Semicon"], n=60)),
    ("XLF", "Secteur Finance", "sector", "Finance", 3, 0.0012, _eq(sectors=["Finance"], n=80)),
    ("XLE", "Secteur Énergie", "sector", "Energie", 3, 0.0013, _eq(sectors=["Energie"], n=60)),
    ("XLV", "Secteur Santé", "sector", "Sante", 2, 0.0012, _eq(sectors=["Sante"], n=60)),
    ("XLI", "Secteur Industrie", "sector", "Industrie", 3, 0.0013, _eq(sectors=["Industrie"], n=70)),
    ("XLP", "Secteur Conso de base", "sector", "Conso", 2, 0.0012, _eq(sectors=["Conso"], n=70)),
    ("XLU", "Secteur Utilities", "sector", "Utilities", 1, 0.0012, _eq(sectors=["Utilities"], n=50)),
    ("XLB", "Secteur Matériaux", "sector", "Materiaux", 3, 0.0013, _eq(sectors=["Materiaux"], n=60)),
    ("XLC", "Secteur Télécoms", "sector", "Telecom", 2, 0.0013, _eq(sectors=["Telecom"], n=50)),
    ("XLY", "Secteur Luxe & Disc.", "sector", "Luxe", 3, 0.0014, _eq(sectors=["Luxe"], n=40)),
    ("XAU", "Secteur Auto", "sector", "Auto", 4, 0.0015, _eq(sectors=["Auto"], n=40)),
    ("XAG", "Secteur Agro", "sector", "Agro", 3, 0.0014, _eq(sectors=["Agro"], n=50)),

    # ---- Styles (factoriel) ----
    ("VAL", "Facteur Value", "style", "Value", 2, 0.0020, _eq(glob=True, style="value", n=80)),
    ("GRW", "Facteur Growth", "style", "Growth", 3, 0.0020, _eq(glob=True, style="growth", n=80)),
    ("DIV", "Hauts Dividendes", "style", "Dividend", 2, 0.0018, _eq(glob=True, style="dividend", n=80)),
    ("QAL", "Facteur Quality", "style", "Quality", 2, 0.0022, _eq(glob=True, style="quality", n=80)),
    ("MOM", "Facteur Momentum", "style", "Momentum", 4, 0.0025, _eq(glob=True, style="momentum", n=80)),
    ("LOV", "Faible Volatilité", "style", "Min Vol", 1, 0.0020, _eq(glob=True, style="lowvol", n=80)),

    # ---- Thématiques ----
    ("AIQ", "Intelligence Artificielle", "thematic", "IA", 4, 0.0045, _eq(sectors=["Tech", "Semicon"], theme="ai", n=80)),
    ("SOX", "Semiconducteurs Global", "thematic", "Semis", 5, 0.0045, _eq(sectors=["Semicon"], theme="sox", n=60)),
    ("ROB", "Robotique & Automation", "thematic", "Robotique", 4, 0.0048, _eq(sectors=["Tech", "Industrie"], theme="rob", n=80)),
    ("CYB", "Cybersécurité", "thematic", "Cyber", 4, 0.0050, _eq(sectors=["Tech"], theme="cyb", n=80)),
    ("CLN", "Énergie Propre", "thematic", "Clean Energy", 5, 0.0055, _eq(sectors=["Utilities", "Energie", "Industrie"], theme="cln", n=80)),
    ("DEF", "Défense & Aéro", "thematic", "Défense", 3, 0.0045, _eq(sectors=["Industrie"], theme="def", n=70)),
    ("INF", "Infrastructure", "thematic", "Infrastructure", 2, 0.0040, _eq(sectors=["Industrie", "Utilities", "Materiaux"], theme="inf", n=90)),
    ("FIN", "Fintech", "thematic", "Fintech", 4, 0.0050, _eq(sectors=["Finance", "Tech"], theme="fin", n=80)),
    ("GEN", "Génomique & Biotech", "thematic", "Biotech", 5, 0.0055, _eq(sectors=["Sante"], theme="gen", n=60)),
    ("CON", "Consommateur Digital", "thematic", "E-commerce", 4, 0.0048, _eq(sectors=["Conso", "Tech"], theme="con", n=80)),
    ("WTR", "Eau & Ressources", "thematic", "Eau", 2, 0.0042, _eq(sectors=["Utilities", "Materiaux"], theme="wtr", n=70)),

    # ---- ESG / Durable ----
    ("ESG", "Monde ESG Leaders", "esg", "ESG Monde", 2, 0.0025,
     _eq(glob=True, exclude_sectors=["Energie", "Materiaux"], theme="esg", n=160)),
    ("ESU", "USA ESG", "esg", "ESG USA", 2, 0.0022,
     _eq(regions=["USA"], exclude_sectors=["Energie"], theme="esu", n=90)),
    ("SRI", "ISR Best-in-Class", "esg", "ISR", 3, 0.0030,
     _eq(glob=True, exclude_sectors=["Energie", "Auto", "Materiaux"], theme="sri", n=140)),

    # ---- Immobilier / REIT ----
    ("RET", "REIT Monde", "reit", "Immobilier", 3, 0.0030, _eq(sectors=["Immobilier"], n=60)),
    ("REU", "REIT USA", "reit", "Immobilier USA", 3, 0.0028, _eq(regions=["USA"], sectors=["Immobilier"], n=40)),

    # ---- Obligataire ----
    ("AGG", "Obligataire Agrégé", "bond", "Agrégé IG", 1, 0.0008, _bd(7, "AA", coupon=0.034)),
    ("GOV", "Souverain 7-10 ans", "bond", "Souverain", 1, 0.0007, _bd(9, "AAA", coupon=0.032)),
    ("SHY", "Souverain Court Terme", "bond", "Court terme", 1, 0.0007, _bd(2, "AAA", coupon=0.030)),
    ("TLT", "Souverain Long Terme", "bond", "Long terme", 2, 0.0009, _bd(25, "AAA", coupon=0.035)),
    ("LQD", "Corporate IG", "bond", "Corporate IG", 2, 0.0012, _bd(8, "BBB", coupon=0.050, eq_beta=0.05)),
    ("HYG", "High Yield", "bond", "High Yield", 3, 0.0045, _bd(5, "B", coupon=0.085, eq_beta=0.20)),
    ("TIP", "Indexé Inflation", "bond", "Inflation", 2, 0.0010, _bd(8, "AAA", coupon=0.015, infl=True)),
    ("EMB", "Souverain Émergent", "bond", "EM Debt", 4, 0.0040, _bd(10, "BB", coupon=0.075, eq_beta=0.12, region="Am.Sud")),

    # ---- Commodities ----
    ("DBC", "Commodities Diversifié", "commodity", "Diversifié", 3, 0.0035,
     _cm([("OIL", 0.20), ("BRENT", 0.10), ("GOLD", 0.15), ("COPP", 0.15),
          ("WHEAT", 0.10), ("CORN", 0.10), ("ALUM", 0.10), ("GAS", 0.10)])),
    ("GLD", "Or Physique", "commodity", "Or", 2, 0.0025, _cm([("GOLD", 1.0)])),
    ("SLV", "Argent Physique", "commodity", "Argent", 3, 0.0030, _cm([("SILV", 1.0)])),
    ("USO", "Pétrole", "commodity", "Énergie", 4, 0.0045, _cm([("OIL", 0.6), ("BRENT", 0.4)])),
    ("DBA", "Agriculture", "commodity", "Agriculture", 3, 0.0040,
     _cm([("WHEAT", 0.25), ("CORN", 0.25), ("SOYB", 0.25), ("SUGA", 0.25)])),
    ("PIC", "Métaux Industriels", "commodity", "Métaux", 3, 0.0040,
     _cm([("COPP", 0.35), ("ALUM", 0.25), ("ZINC", 0.20), ("NICK", 0.20)])),

    # ---- Devises ----
    ("UUP", "Dollar US (DXY)", "currency", "USD", 2, 0.0030, _fx(drift=0.0, vol=0.06, rate_beta=0.5)),
    ("FXE", "Euro", "currency", "EUR", 2, 0.0030, _fx(drift=0.0, vol=0.07, rate_beta=-0.3)),
    ("FXY", "Yen Japonais", "currency", "JPY", 2, 0.0030, _fx(drift=-0.01, vol=0.08, rate_beta=-0.4)),
    ("EMF", "Devises Émergentes", "currency", "EM FX", 4, 0.0040, _fx(drift=-0.02, vol=0.11, rate_beta=-0.2)),

    # ---- Levier / Inverse (RISQUE ÉLEVÉ) ----
    ("SPXL", "C&D 500 x3 (Levier)", "leveraged", "Long x3", 5, 0.0090, _lev("SPX", 3.0)),
    ("TQQ", "Tech x3 (Levier)", "leveraged", "Long x3", 5, 0.0095, _lev("XLK", 3.0)),
    ("SPXS", "C&D 500 x-1 (Inverse)", "leveraged", "Inverse x1", 5, 0.0090, _lev("SPX", -1.0)),
    ("SQQ", "Tech x-2 (Inverse)", "leveraged", "Inverse x2", 5, 0.0095, _lev("XLK", -2.0)),
    ("SOXL", "Semis x3 (Levier)", "leveraged", "Long x3", 5, 0.0100, _lev("XSM", 3.0)),
    ("TBT", "Souverain LT x-2 (Inverse)", "leveraged", "Inverse x2", 5, 0.0090, _lev("TLT", -2.0)),
]


class ETF:
    def __init__(self, eid, name, category, sub, risk, expense, engine):
        self.id = eid
        self.name = name
        self.category = category
        self.sub = sub
        self.risk = risk
        self.expense = expense
        self.engine = engine
        self._idxs = None       # constituants (indices dans market.companies)
        self._w = None          # poids (capi de base) des constituants
        self._divy = None       # rendement de dividende annuel pondéré
        self._beta = None       # bêta monde pondéré

    # ---- construction paresseuse des constituants (engine equity) ----
    def _ensure_basket(self):
        if self._idxs is not None or self.engine["type"] != "equity":
            return
        e = self.engine
        comps = comp_data.COMPANIES
        pool = list(range(len(comps)))
        if e["regions"]:
            pool = [i for i in pool if comps[i]["region"] in e["regions"]]
        if e["sectors"]:
            pool = [i for i in pool if comps[i]["sector"] in e["sectors"]]
        if e["exclude_sectors"]:
            pool = [i for i in pool if comps[i]["sector"] not in e["exclude_sectors"]]
        # sous-panier thématique/pays : tri déterministe par hash(theme+ticker)
        if e["theme"]:
            th = e["theme"]
            pool = [i for i in pool if (_hash(th + comps[i]["ticker"]) % 5) != 0]
        cap = lambda i: comps[i]["price0"] * comps[i]["shares"]
        style = e["style"]
        if style in (None, "equal"):
            pool.sort(key=cap, reverse=True)
        elif style == "mid":
            pool.sort(key=cap, reverse=True)
            pool = pool[len(pool) // 5: len(pool) // 5 + e["n"]]
        elif style == "small":
            pool.sort(key=cap)
            pool = pool[:e["n"]]
        elif style == "value":
            pool.sort(key=lambda i: _earn_yield(comps[i]), reverse=True)
        elif style == "growth":
            pool.sort(key=lambda i: comps[i]["drift"], reverse=True)
        elif style == "dividend":
            pool.sort(key=lambda i: comps[i]["div_yield"], reverse=True)
        elif style == "quality":
            pool.sort(key=lambda i: _quality(comps[i]), reverse=True)
        elif style == "momentum":
            pool.sort(key=lambda i: comps[i]["beta"] + comps[i]["drift"] * 60, reverse=True)
        elif style == "lowvol":
            pool.sort(key=lambda i: comps[i]["sigma"])
        else:
            pool.sort(key=cap, reverse=True)
        pool = pool[:max(1, e["n"])]
        self._idxs = np.array(pool, dtype=np.int64)
        if style == "equal":
            w = np.ones(len(pool), dtype=np.float64)
        else:
            w = np.array([comps[i]["shares"] for i in pool], dtype=np.float64)
        self._w = w
        tot = float(np.sum(w * np.array([comps[i]["price0"] for i in pool])))
        self._divy = (float(np.sum(w * np.array(
            [comps[i]["price0"] * comps[i]["div_yield"] for i in pool]))) / tot
            if tot else 0.0)
        self._beta = (float(np.sum(w * np.array(
            [comps[i]["price0"] * comps[i]["beta"] for i in pool]))) / tot
            if tot else 1.0)


def _hash(s):
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def _earn_yield(c):
    mc = c["price0"] * c["shares"]
    return (c["revenue"] * c["net_margin"]) / mc if mc else 0.0


def _quality(c):
    lev = (c["net_debt"] / c["revenue"]) if c["revenue"] else 0.0
    return c["net_margin"] - 0.1 * max(0.0, lev)


ETFS = [ETF(*d) for d in _DEFS]
_BY_ID = {e.id: e for e in ETFS}


def all_etfs():
    return ETFS


def get(eid):
    return _BY_ID.get(eid)


def exists(eid):
    return eid in _BY_ID


# --------------------------------------------------------------------------
# Moteur de NAV (séries reconstruites depuis les historiques du marché)
# --------------------------------------------------------------------------
_cache = {}          # (seed, step, id) -> np.ndarray NAV
_cache_step = None


def _reset_cache_if_needed(market):
    global _cache_step
    step = int(getattr(market, "step_count", 0))
    if step != _cache_step:
        _cache.clear()
        _cache_step = step


def _world_returns(market):
    """Rendements (par pas) d'un panier actions monde — proxy du facteur monde,
    utilisé par les ETF obligataires HY/EM (corrélation aux actions)."""
    key = (getattr(market, "seed", 0), int(getattr(market, "step_count", 0)), "__world__")
    cached = _cache.get(key)
    if cached is not None:
        return cached
    snaps = market.price_hist_all
    shares = market.shares
    vals = np.array([float(np.dot(shares, s)) for s in snaps])
    rets = np.zeros(len(vals))
    if len(vals) > 1:
        rets[1:] = vals[1:] / np.maximum(vals[:-1], 1e-9) - 1.0
    _cache[key] = rets
    return rets


def _equity_nav(market, etf):
    etf._ensure_basket()
    snaps = market.price_hist_all
    idxs, w = etf._idxs, etf._w
    vals = np.array([float(np.dot(w, s[idxs])) for s in snaps])
    if len(vals) < 2:
        return np.array([100.0])
    rets = vals[1:] / np.maximum(vals[:-1], 1e-9) - 1.0
    rets = rets + (etf._divy - etf.expense) * _DT          # total return net de frais
    nav = 100.0 * np.cumprod(1.0 + rets)
    return np.concatenate(([100.0], nav))


def _bond_nav(market, etf):
    e = etf.engine
    rates = list(getattr(market, "macro_hist", {}).get("rate", []))
    if not rates:
        rates = [market.macro["rate"]["v"]] if hasattr(market, "macro") else [3.0]
    years = e["years"]
    coupon = e["coupon"] if e["coupon"] is not None else 0.03
    spread = _RATING_SPREAD.get(e["rating"], 0.01)
    if e["region"]:
        spread += getattr(market, "region_credit_bump", {}).get(e["region"], 0.0)
    prices = np.array([finmath.bond_price(_FACE, coupon, r / 100.0 + spread, years)
                       for r in rates])
    if len(prices) < 2:
        return np.array([100.0])
    rets = prices[1:] / np.maximum(prices[:-1], 1e-9) - 1.0
    carry = coupon
    if e["infl"]:
        infl = list(getattr(market, "macro_hist", {}).get("inflation", []))
        if len(infl) == len(rates):
            carry = coupon + np.array(infl[1:]) / 100.0    # principal indexé
    rets = rets + (np.asarray(carry) - etf.expense) * _DT
    if e["eq_beta"]:
        rets = rets + e["eq_beta"] * _world_returns(market)[1:]
    nav = 100.0 * np.cumprod(1.0 + rets)
    return np.concatenate(([100.0], nav))


def _commodity_nav(market, etf):
    from core import commodities
    L = len(market.price_hist_all)
    basket = etf.engine["basket"]
    agg = None
    for cid, wgt in basket:
        h = commodities.history(market, cid)
        if not h:
            continue
        h = np.array(h[-L:], dtype=np.float64)
        if len(h) < L:                                     # alignement
            h = np.concatenate((np.full(L - len(h), h[0]), h))
        norm = h / max(h[0], 1e-9)
        agg = norm * wgt if agg is None else agg + norm * wgt
    if agg is None or len(agg) < 2:
        return np.array([100.0])
    rets = agg[1:] / np.maximum(agg[:-1], 1e-9) - 1.0
    rets = rets - etf.expense * _DT
    nav = 100.0 * np.cumprod(1.0 + rets)
    return np.concatenate(([100.0], nav))


def _currency_nav(market, etf):
    e = etf.engine
    L = len(market.price_hist_all)
    seed = (int(getattr(market, "seed", 12345)) + _hash(etf.id)) & 0xFFFFFFFF
    rng = np.random.RandomState(seed)
    vol = e["vol"] / np.sqrt(52)
    mu = e["drift"] / 52.0 - 0.5 * vol ** 2
    rets = rng.normal(mu, vol, max(1, L - 1))
    # sensibilité aux taux : un écart de taux pousse la devise (porté par le carry)
    rates = list(getattr(market, "macro_hist", {}).get("rate", []))
    if e["rate_beta"] and len(rates) >= L:
        dr = np.diff(np.array(rates[-L:]) / 100.0)
        rets = rets + e["rate_beta"] * dr
    rets = rets - etf.expense * _DT
    nav = 100.0 * np.cumprod(1.0 + rets)
    return np.concatenate(([100.0], nav))


def _leveraged_nav(market, etf):
    e = etf.engine
    base = _BY_ID.get(e["base"])
    if base is None:
        return np.array([100.0])
    bnav = _nav_series(market, base)
    if len(bnav) < 2:
        return np.array([100.0])
    bret = bnav[1:] / np.maximum(bnav[:-1], 1e-9) - 1.0
    # levier QUOTIDIEN (reset par pas) → décroissance de volatilité réaliste
    rets = e["factor"] * bret - etf.expense * _DT
    rets = np.clip(rets, -0.95, 5.0)
    nav = 100.0 * np.cumprod(1.0 + rets)
    return np.concatenate(([100.0], nav))


_BUILDERS = {
    "equity": _equity_nav, "bond": _bond_nav, "commodity": _commodity_nav,
    "currency": _currency_nav, "leveraged": _leveraged_nav,
}


def _nav_series(market, etf):
    _reset_cache_if_needed(market)
    key = (getattr(market, "seed", 0), int(getattr(market, "step_count", 0)), etf.id)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    nav = _BUILDERS[etf.engine["type"]](market, etf)
    _cache[key] = nav
    return nav


# --------------------------------------------------------------------------
# Requêtes publiques
# --------------------------------------------------------------------------
def nav_history(market, eid, n=None):
    etf = _BY_ID.get(eid)
    if not etf or market is None:
        return []
    nav = _nav_series(market, etf)
    out = nav.tolist()
    return out[-n:] if n else out


def price(market, eid):
    etf = _BY_ID.get(eid)
    if not etf or market is None:
        return None
    nav = _nav_series(market, etf)
    return float(nav[-1]) if len(nav) else None


def change_pct(market, eid):
    nav = nav_history(market, eid)
    if len(nav) < 2 or nav[-2] == 0:
        return 0.0
    return (nav[-1] / nav[-2] - 1.0) * 100.0


def change_pct_period(market, eid, steps):
    nav = nav_history(market, eid)
    if len(nav) < 2:
        return 0.0
    ref = nav[-min(len(nav), steps + 1)]
    return (nav[-1] / ref - 1.0) * 100.0 if ref else 0.0


def indicative_yield(etf):
    """Rendement indicatif annuel (dividendes/coupons)."""
    e = etf.engine
    if e["type"] == "equity":
        etf._ensure_basket()
        return etf._divy
    if e["type"] == "bond":
        return e["coupon"] if e["coupon"] is not None else 0.0
    if e["type"] == "leveraged":
        base = _BY_ID.get(e["base"])
        return indicative_yield(base) * e["factor"] if base else 0.0
    return 0.0


def beta_world(etf):
    """Bêta approximatif au facteur monde (exposition actions)."""
    e = etf.engine
    if e["type"] == "equity":
        etf._ensure_basket()
        return etf._beta
    if e["type"] == "bond":
        return e["eq_beta"]
    if e["type"] == "commodity":
        return 0.30
    if e["type"] == "currency":
        return 0.0
    if e["type"] == "leveraged":
        base = _BY_ID.get(e["base"])
        return beta_world(base) * e["factor"] if base else 0.0
    return 1.0


def exposure_label(etf):
    """Description courte et lisible de l'exposition (pour la fiche)."""
    e = etf.engine
    if e["type"] == "equity":
        bits = []
        if e["glob"]:
            bits.append("Monde")
        if e["regions"]:
            bits.append("/".join(e["regions"]))
        if e["sectors"]:
            bits.append("/".join(e["sectors"]))
        if e["style"]:
            bits.append(f"style {e['style']}")
        if e["exclude_sectors"]:
            bits.append("ex-" + "/".join(e["exclude_sectors"]))
        return ", ".join(bits) or "Actions"
    if e["type"] == "bond":
        s = f"Obligations {e['rating']} ~{e['years']} ans"
        if e["infl"]:
            s += " (indexé inflation)"
        return s
    if e["type"] == "commodity":
        return "Panier : " + ", ".join(c for c, _ in e["basket"])
    if e["type"] == "currency":
        return f"Devise {etf.sub} vs panier"
    if e["type"] == "leveraged":
        base = _BY_ID.get(e["base"])
        bn = base.name if base else e["base"]
        return f"{e['factor']:+.0f}x {bn} (reset quotidien)"
    return ""


def quote(market, eid):
    """Cotation complète d'un ETF (pour listes, fiches, comparaison)."""
    etf = _BY_ID.get(eid)
    if not etf:
        return None
    p = price(market, eid)
    return {
        "id": etf.id, "name": etf.name, "category": etf.category,
        "category_label": CATEGORY_LABEL.get(etf.category, etf.category),
        "sub": etf.sub, "risk": etf.risk, "expense": etf.expense,
        "price": p, "change_pct": change_pct(market, eid),
        "change_1y": change_pct_period(market, eid, 73),
        "yield": indicative_yield(etf), "beta": beta_world(etf),
        "exposure": exposure_label(etf), "leveraged": etf.engine["type"] == "leveraged",
        "type": etf.engine["type"],
    }


def all_quotes(market):
    return [quote(market, e.id) for e in ETFS]


# --------------------------------------------------------------------------
# Trading (long only, réglé cash — modèle des obligations)
# --------------------------------------------------------------------------
def buy(player, market, eid, qty):
    etf = _BY_ID.get(eid)
    if etf is None:
        return {"ok": False, "reason": "id"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    p = price(market, eid)
    if p is None:
        return {"ok": False, "reason": "id"}
    cost = p * qty
    fee = cost * COMMISSION
    total = cost + fee
    if total > player.cash:
        return {"ok": False, "reason": "cash", "need": total}
    player.cash -= total
    pos = player.etfs.get(eid)
    if pos:
        n = pos["qty"] + qty
        pos["avg"] = (pos["qty"] * pos["avg"] + cost) / n
        pos["qty"] = n
    else:
        player.etfs[eid] = {"qty": float(qty), "avg": p}
    return {"ok": True, "price": p, "qty": qty, "total": total, "fee": fee}


def sell(player, market, eid, qty):
    pos = player.etfs.get(eid)
    if not pos:
        return {"ok": False, "reason": "noposition"}
    p = price(market, eid)
    if p is None:
        return {"ok": False, "reason": "id"}
    if qty == "ALL" or qty >= pos["qty"]:
        qty = pos["qty"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    proceeds = p * qty
    fee = proceeds * COMMISSION
    net = proceeds - fee
    realized = (p - pos["avg"]) * qty - fee
    player.cash += net
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    pos["qty"] -= qty
    if pos["qty"] <= 1e-9:
        del player.etfs[eid]
    return {"ok": True, "price": p, "qty": qty, "net": net, "realized": realized}


def holdings_value(player, market):
    total = 0.0
    for eid, pos in getattr(player, "etfs", {}).items():
        p = price(market, eid)
        if p is not None:
            total += p * pos["qty"]
    return total


def holdings(player, market):
    out = []
    for eid, pos in getattr(player, "etfs", {}).items():
        q = quote(market, eid)
        if not q:
            continue
        value = q["price"] * pos["qty"]
        out.append({"id": eid, "name": q["name"], "qty": pos["qty"], "avg": pos["avg"],
                    "price": q["price"], "category": q["category"], "sub": q["sub"],
                    "change_pct": q["change_pct"], "risk": q["risk"],
                    "value": value, "pnl": value - pos["avg"] * pos["qty"]})
    out.sort(key=lambda h: h["value"], reverse=True)
    return out
