"""
scene_graph_common.py — Constantes et petits helpers PARTAGÉS entre
`scene_graph.py` (GraphScene, cœur : cycle de vie, données, chrome) et son
mixin de rendu (`scene_graph_render.py`, GraphRenderMixin). Module à part
pour éviter tout import circulaire (même principe que
`scenes/scene_desktop_common.py`).
"""
from core import bonds as BND
from core import commodities as CMD
from core import config, game_calendar, intraday
from core import crypto as CRY
from core import etfs as ETF
from core.i18n import get_lang


def _asset_exists(market, tk):
    return (tk in market.ticker_idx or ETF.exists(tk) or tk in BND._BY_ID
            or tk in CMD._BY_ID or tk in CRY._BY_ID)


def _asset_kind(tk):
    if tk in BND._BY_ID:
        return "bond"
    if tk in CMD._BY_ID:
        return "commodity"
    if tk in CRY._BY_ID:
        return "crypto"
    if ETF.exists(tk):
        return "etf"
    return "stock"

def _L(fr, en):
    return en if get_lang() == "en" else fr


# (code, libellé court [(fr, en)], kind, multi-actifs ?)
TYPES = [
    ("GP", ("Ligne", "Line"), "line", False),
    ("GPC", ("Chandel.", "Candles"), "candles", False),
    ("GPO", ("Barres", "Bars"), "bars", False),
    ("GPCH", ("Var %", "Chg %"), "change", False),
    ("COMP", ("Comparer", "Compare"), "compare", True),
    ("HS", ("Spread", "Spread"), "spread", True),
    ("HVOL", ("Volatilité", "Volatility"), "vol", False),
    ("BETA", ("Bêta", "Beta"), "beta", False),
    ("CORR", ("Corrél.", "Corr."), "corr", True),
    ("GEG", ("Macro", "Macro"), "macro", False),
    ("GC", ("Courbe", "Curve"), "curve", False),
]
_KIND_BY_CODE = {c: k for c, _, k, _ in TYPES}
_MULTI = {k for _, _, k, multi in TYPES if multi}
_NO_ASSET = {"macro", "curve"}     # types sans saisie d'actif

# Périodes "par pas" (jours de jeu, cf. moteur de marché par paliers) +
# fenêtres intraday animées (Round 11 Phase 3) encodées en minutes de jeu
# négatives pour les distinguer des pas — uniquement valables pour les types
# de graphe à série unique (ligne/chandeliers/barres/variation %), où la
# liste de clôtures suffit (`_aggregate_ohlc` re-agrège lui-même l'OHLC).
INTRADAY_PERIODS = [(label, -minutes) for label, minutes in intraday.INTRADAY_WINDOWS]
STEP_PERIODS = [("1M", 6), ("3M", 18), ("1A", 73), ("3A", 219), ("5A", 365), ("MAX", None)]
PERIODS = INTRADAY_PERIODS + STEP_PERIODS
_INTRADAY_KINDS = {"line", "candles", "bars", "change", "compare"}
_MAX_TICKERS = 10   # au-delà, légendes/puces deviennent illisibles
SERIES_COLS = [config.COL_AMBER, config.COL_CYAN, config.COL_UP, config.COL_WARN,
               config.COL_PRESTIGE, config.COL_DOWN]


def stock_series(market, sim_clock, day, tk, period, region=None):
    """Série de clôtures d'une ACTION pour une `period` du sélecteur
    `PERIODS` (fenêtre intraday en minutes négatives, ou nombre de pas —
    None = MAX) — échantillonne le CHEMIN DE PRIX CANONIQUE (cf.
    core/intraday.py), donc recoupe exactement les autres vues sur la même
    société (fiche société, popup, tickers). Factorisé depuis
    `GraphScene._series` pour que `scene_company.py` (fiche société, onglet
    « graphique avancé ») partage EXACTEMENT la même logique — deux calculs
    indépendants avaient déjà dérivé une fois (cf. audit V1.0)."""
    i = market.ticker_idx.get(tk)
    vol_mult = intraday.vol_mult_for_sigma(float(market.sigma[i])) if i is not None else 1.0
    if region is None and i is not None:
        region = market.companies[i].get("region")
    target = market.next_price_of(tk)
    if period is not None and period < 0:
        window_days = -period / (24 * 60)
        steps_needed = max(2, int(window_days / config.DAYS_PER_STEP) + 2)
        hist = market.history_of(tk, steps_needed)
        # Fenêtre 1J → 80 points, 1W → 140 points pour révéler la texture fine
        # du chemin canonique (plus de piques/zigzags, façon app mobile).
        n_points = 80 if -period <= 1440 else 140
        return intraday.intraday_series(
            market, sim_clock, day, tk, hist, window_minutes=-period, n_points=n_points,
            region=region, vol_mult=vol_mult, target=target)
    pps = intraday.points_per_segment_for_n_steps(period)
    hist = market.history_of(tk, period)
    dense = intraday.densify_step_series(market, tk, hist, pps, region=region, vol_mult=vol_mult)
    return intraday.append_live(market, sim_clock, day, tk, dense, region=region,
                                vol_mult=vol_mult, target=target)


def x_label_positions(period, n, today):
    """Libellés d'axe X à ÉCHELLE HUMAINE pour une série temporelle de `n`
    points sur `period` (fenêtre intraday en minutes négatives, ou nombre de
    pas — None = MAX), le point le plus à droite étant « maintenant » :
    - fenêtres intraday : minutes → heures → jours (« -12h », « -3.5j ») ;
    - fenêtres par pas courtes (≤ ~1 mois) : jours relatifs (« -15j ») ;
    - fenêtres moyennes : dates calendaires (« 12 mars », « mars 2026 ») ;
    - fenêtres longues (3A/5A/MAX) : années (« 2027 »).
    Renvoie une liste `[(frac, texte), ...]` pour `widgets.draw_chart_x_labels`,
    ou `[]` si `n < 2`. Factorisé entre `GraphRenderMixin` (atelier de
    graphes) et `scene_company.py` (fiche société, onglet graphique avancé) —
    ils doivent afficher EXACTEMENT la même échelle pour la même période."""
    if n < 2:
        return []
    today_lbl = "today" if get_lang() == "en" else "aujourd'hui"
    if period is not None and period < 0:
        window = -period
        return [(f, game_calendar.rel_minutes_label(window * (1 - f)))
                for f in (0.0, 0.5, 1.0)]
    # étendue RÉELLE affichée : depuis la période choisie (en pas), PAS depuis
    # len(série) — la densification (points intermédiaires entre clôtures)
    # gonfle n et fausserait l'étendue (ex. « -180j » sur la vue 1M).
    span = period * config.DAYS_PER_STEP if period is not None \
        else (n - 1) * config.DAYS_PER_STEP   # MAX : pas de densification
    if span <= 35:
        return [(0.0, f"-{span}j"), (0.5, f"-{span // 2}j"), (1.0, today_lbl)]
    labels = []
    prev_text = None
    for f in (0.0, 0.25, 0.5, 0.75):
        text = game_calendar.axis_label(today - round(span * (1 - f)), span)
        if text != prev_text:     # évite « 2026  2026 » sur les fenêtres longues
            labels.append((f, text))
            prev_text = text
    labels.append((1.0, today_lbl))
    return labels
