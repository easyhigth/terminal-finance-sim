"""
scene_graph_common.py — Constantes et petits helpers PARTAGÉS entre
`scene_graph.py` (GraphScene, cœur : cycle de vie, données, chrome) et son
mixin de rendu (`scene_graph_render.py`, GraphRenderMixin). Module à part
pour éviter tout import circulaire (même principe que
`scenes/scene_desktop_common.py`).
"""
from core import bonds as BND
from core import commodities as CMD
from core import config, intraday
from core import crypto as CRY
from core import etfs as ETF


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

# (code, libellé court, kind, multi-actifs ?)
TYPES = [
    ("GP", "Ligne", "line", False),
    ("GPC", "Chandel.", "candles", False),
    ("GPO", "Barres", "bars", False),
    ("GPCH", "Var %", "change", False),
    ("COMP", "Comparer", "compare", True),
    ("HS", "Spread", "spread", True),
    ("HVOL", "Volatilité", "vol", False),
    ("BETA", "Bêta", "beta", False),
    ("CORR", "Corrél.", "corr", True),
    ("GEG", "Macro", "macro", False),
    ("GC", "Courbe", "curve", False),
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
