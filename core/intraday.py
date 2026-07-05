"""
intraday.py — Animation de prix intraday en direct (Round 11 Phase 3).

Le moteur de marché (`core/market.py`) reste par paliers de
`config.DAYS_PER_STEP` jours : aucune donnée intraday n'est calculée ni
persistée par lui (le save ne stocke toujours que `market_seed`/`market_step`).
Ce module est une couche d'AFFICHAGE pure, recalculée à la volée à partir de
(seed, step, clé de série, minutes de jeu écoulées dans le pas courant) —
jamais sérialisée — qui anime le prix entre la clôture précédente et la
clôture courante avec un bruit déterministe multi-octaves, épinglé à zéro
aux deux bornes du pas (le point affiché vaut exactement `prev_close` au
début du pas et `cur_close` à la fin). Ça permet aux graphes de bouger
visiblement (variations de l'ordre du ‰ à quelques % selon la volatilité de
l'actif, cf. `_NOISE_PCT`/`_VOL_MULT_RANGE`) même à l'échelle « 5 minutes »,
sans jamais affecter le prix d'exécution des ordres : BUY/SELL/SHORT/COVER
continuent d'utiliser `market.price`/`market.index_value`, inchangés.

Reconstruit entièrement depuis (seed, step_count, clé, minute) : pas d'état
à persister, pas de tirage rng consommé (donc aucun décalage des saves).
"""
from core import config, market_hours

MINUTES_PER_DAY = 24 * 60

# Résolutions des octaves de bruit (minutes), du plus grossier au plus fin —
# la plus fine (5 min) garantit de la texture même sur la fenêtre la plus
# zoomée (« 5 dernières minutes »). Poids de l'octave fine relevé (0.3 → 0.5)
# et amplitude globale augmentée pour un tracé dense/dentelé façon app de
# trading grand public (retour joueur : les graphes "de vraie appli" montrent
# des piques et zigzags bien visibles, cf. captures eToro fournies).
_RESOLUTIONS = (720, 60, 5)
_AMPLITUDES = (1.0, 0.5, 0.5)
# Amplitude relative max du bruit affiché (~0.85%) : purement visuel (n'affecte
# jamais market.price/index_value, donc jamais le prix d'exécution des ordres).
# Cette amplitude suffit pour faire apparaître des pics/spikes sur les fenêtres
# courtes sans dénaturer les tendances de fond sur les vues longues.
_NOISE_PCT = 0.0060

# Sigma "moyen" du roster (cf. data/companies.py, profils sectoriels ~0.018-0.055) ;
# sert de référence pour que les sociétés volatiles (tech/semicon...) bougent
# visiblement plus que les défensives (utilities...) à l'écran. Plancher
# relevé (0.6 → 0.8) pour que même les valeurs défensives restent lisiblement
# animées plutôt que quasi plates.
_TYPICAL_SIGMA = 0.035
_VOL_MULT_RANGE = (0.8, 3.2)


def minutes_per_step():
    return config.DAYS_PER_STEP * MINUTES_PER_DAY


# Pas de rafraîchissement de l'animation « en direct » (minutes de jeu) :
# Ajusté pour 1 rafraîchissement par seconde réelle à vitesse x1.
# 90 minutes de jeu = 1 seconde réelle, donc QUANTIZE_MINUTES = 90 donne
# environ 16 rafraîchissements/jour. Pour un rafraîchissement exactement
# toutes les secondes, on garde cette valeur car c'est déjà le comportement.
QUANTIZE_MINUTES = 90


def quantize_to_day(minutes):
    """Ramène une progression en minutes de jeu à la borne de palier
    (`QUANTIZE_MINUTES`) inférieure. L'animation « en direct » ne se met alors
    à jour que par paliers (au lieu de chaque frame) : les chiffres avancent
    par petits sauts vers la destination du prochain pas, plus lisible qu'un
    glissement continu tout en restant nettement plus réactif qu'un seul
    rafraîchissement par jour de jeu."""
    return (int(minutes) // QUANTIZE_MINUTES) * QUANTIZE_MINUTES


def vol_mult_for_sigma(sigma, scale=1.0):
    """Multiplicateur de bruit affiché à partir de la volatilité idiosyncratique
    `sigma` d'une société (cf. `core/market.py::self.sigma`), borné pour rester
    perceptible sans devenir illisible. `scale` permet d'amortir (indices) ou de
    garder (sociétés individuelles) l'écart relatif."""
    lo, hi = _VOL_MULT_RANGE
    return max(lo, min(hi, (sigma / _TYPICAL_SIGMA) * scale))


def _mix(h, x):
    h ^= x & 0xFFFFFFFFFFFFFFFF
    h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def _hash01(*parts):
    """Hash déterministe (stable entre runs, indépendant de PYTHONHASHSEED)
    -> float dans [0, 1)."""
    h = 1469598103934665603
    for p in parts:
        if isinstance(p, str):
            for ch in p:
                h = _mix(h, ord(ch))
        else:
            h = _mix(h, int(p))
    return (h % 1_000_003) / 1_000_003.0


def _node(seed, step, key, resolution, node_index):
    return 2.0 * _hash01(seed, step, key, resolution, node_index) - 1.0


def _octave(seed, step, key, resolution, minute):
    import math
    pos = minute / resolution
    i0 = int(pos)
    frac = pos - i0
    a = _node(seed, step, key, resolution, i0)
    b = _node(seed, step, key, resolution, i0 + 1)
    ft = (1 - math.cos(frac * math.pi)) / 2.0
    return a * (1 - ft) + b * ft


def _fbm(seed, step, key, minute):
    total = 0.0
    wsum = 0.0
    for res, amp in zip(_RESOLUTIONS, _AMPLITUDES):
        total += amp * _octave(seed, step, key, res, minute)
        wsum += amp
    return total / wsum


def _pinned_noise(seed, step, key, minute):
    """Bruit fBm épinglé à 0 en minute=0 et minute=minutes_per_step(), pour
    que le prix affiché coïncide exactement avec les clôtures du moteur de
    marché aux deux bornes du pas."""
    total = minutes_per_step()
    raw = _fbm(seed, step, key, minute)
    raw0 = _fbm(seed, step, key, 0)
    raw1 = _fbm(seed, step, key, total)
    t = minute / total
    return raw - (raw0 * (1 - t) + raw1 * t)


def speed_factor(sim_clock):
    """DÉPRÉCIÉ — plus appliqué au chemin canonique : moduler l'amplitude du
    bruit par la vitesse de jeu faisait qu'un même instant du passé changeait
    de valeur selon la vitesse courante, cassant le recoupement entre vues
    (le 1J ne retombait pas sur le 1W après un changement de vitesse). La
    « vivacité » vient désormais du glissement réel de la fenêtre sur le
    chemin figé, à chaque palier de QUANTIZE_MINUTES. Conservé pour
    compatibilité (renvoie 1.0)."""
    return 1.0


def region_open_factor(region, step):
    """1.0 si la place régionale est ouverte au pas `step`, 0.0 sinon (gèle le
    bruit intraday quand la place est fermée — modèle de sessions par pas, cf.
    core/market_hours.py)."""
    if region is None:
        return 1.0
    return 1.0 if market_hours.is_region_open(region, step) else 0.0


def wiggle(seed, step_count, key, prev_close, cur_close, progress_minutes, damp=1.0,
           vol_mult=1.0):
    """Valeur animée entre `prev_close` (progress=0) et `cur_close`
    (progress=minutes_per_step()), avec bruit multiplicatif pondéré par
    `damp` (0..1, ouverture de place/coupe-circuit) et `vol_mult` (>=0,
    intensité relative à la volatilité propre de l'actif, cf.
    `vol_mult_for_sigma`)."""
    from core import anim_settings
    total = minutes_per_step()
    t = max(0.0, min(1.0, progress_minutes / total))
    base = prev_close * (1 - t) + cur_close * t
    factor = damp * vol_mult
    if factor <= 0 or anim_settings.reduce_motion():
        return base
    pinned = _pinned_noise(seed, step_count, key, progress_minutes)
    return base * (1 + _NOISE_PCT * factor * pinned)


# ---------------------------------------------------------------------------
# CHEMIN DE PRIX CANONIQUE
# ---------------------------------------------------------------------------
# Toutes les vues (fenêtres 1J/1W, point « en direct » des tickers/sparklines,
# densification des graphes par pas) échantillonnent LE MÊME chemin de prix
# déterministe — comme dans une vraie app de trading, où chaque période n'est
# qu'une fenêtre différente sur la même série. Convention FORWARD : le pont du
# pas s va de close(s) vers close(s+1) (bruit épinglé à 0 aux deux bornes,
# seedé par (market_seed, s, clé)) ; pendant le pas courant, le pont vers la
# clôture suivante (déterministe, `Market.next_price_of`) se révèle au fil des
# minutes de jeu. Conséquences garanties par construction :
#   - le 1J est exactement la QUEUE du 1W (mêmes valeurs aux mêmes instants) ;
#   - la courbe passe EXACTEMENT par chaque clôture du moteur (bornes des
#     ponts), donc recoupe les vues 1M/3M/1A… ;
#   - le dernier point de toute fenêtre == le point « en direct » du ticker ;
#   - un point du PASSÉ ne change JAMAIS quand le temps avance (le bruit d'un
#     pas ne dépend que de (seed, pas, clé), pas de « maintenant »).

def close_at(market, history, step_index, target=None):
    """Clôture du pas `step_index`, lue depuis la fin de `history`
    (`history[-1]` = clôture du pas courant `market.step_count`). Au-delà du
    pas courant, renvoie `target` (clôture suivante déterministe) ; avant le
    début de l'historique, la plus ancienne clôture disponible."""
    j = market.step_count - int(step_index)
    idx = len(history) - 1 - j
    if idx < 0:
        return history[0]
    if idx >= len(history):
        return float(target) if target is not None else history[-1]
    return history[idx]


def canonical_point(market, key, history, step_index, minute, region=None,
                    vol_mult=1.0, target=None):
    """Valeur du chemin canonique au pas `step_index`, minute `minute` du pas
    (0..minutes_per_step()) — pont close(step_index) → close(step_index+1)."""
    start = close_at(market, history, step_index, target)
    end = close_at(market, history, step_index + 1, target)
    damp = region_open_factor(region, step_index) if region else 1.0
    return wiggle(market.seed, int(step_index), key, start, end, minute,
                  damp=damp, vol_mult=vol_mult)


def live_point(market, sim_clock, day, key, history, region=None, vol_mult=1.0, target=None):
    """Point "en direct" à ajouter en fin d'une série historique par pas.

    Avec `target` (clôture DÉTERMINISTE du prochain pas, cf.
    `Market.next_price_of/next_index_value`) : point du CHEMIN CANONIQUE au
    pas courant — identique, à l'instant près, au dernier point des fenêtres
    1J/1W du graphe (cohérence ticker ↔ graphes). Sans `target` (classes
    d'actifs sans anticipation), on retombe sur l'ancien pont
    `history[-2] → history[-1]`."""
    if not history:
        return None
    progress = quantize_to_day(sim_clock.game_minutes_acc)
    if target is not None:
        return canonical_point(market, key, history, market.step_count, progress,
                               region=region, vol_mult=vol_mult, target=target)
    cur = history[-1]
    start = history[-2] if len(history) >= 2 else cur
    damp = region_open_factor(region, market.step_count) if region else 1.0
    return wiggle(market.seed, market.step_count, key, start, cur, progress,
                  damp=damp, vol_mult=vol_mult)


def live_pct(series):
    """Variation « en direct » d'une série animée par `append_live` : valeur
    animée (`series[-1]`) vs la clôture du pas COURANT (`series[-2]`). Part de
    ~0 % au début du pas et se dirige vers la variation du prochain pas — bouge
    donc par palier chaque jour de jeu, de façon directionnelle."""
    if len(series) < 2 or not series[-2]:
        return 0.0
    return (series[-1] / series[-2] - 1.0) * 100.0


# Fenêtre par défaut (en PAS de marché) pour la variation « depuis la durée
# affichée » des bandeaux d'indices — alignée sur la période 3M par défaut des
# graphes (cf. scenes/scene_graph.py::STEP_PERIODS, 3M = 18 pas).
WINDOW_PCT_LOOKBACK = 18


def window_pct(series, lookback=WINDOW_PCT_LOOKBACK):
    """Variation CUMULÉE de la valeur animée courante (`series[-1]`) depuis
    `lookback` pas plus tôt (borné à la longueur de la série). Contrairement à
    `live_pct` (qui repart de ~0 % à chaque pas), ce pourcentage reflète le
    gain/la perte « depuis la durée affichée » et ne se remet donc pas à zéro à
    chaque pas — il glisse jour par jour au gré du dernier point animé."""
    if len(series) < 2:
        return 0.0
    n = min(int(lookback), len(series) - 1)
    base = series[-1 - n]
    if not base:
        return 0.0
    return (series[-1] / base - 1.0) * 100.0


def append_live(market, sim_clock, day, key, history, region=None, vol_mult=1.0, target=None):
    """Renvoie une COPIE de `history` avec un point animé ajouté en fin
    (n'altère jamais la liste d'origine — utile quand `history` est une
    référence interne au moteur de marché, p. ex. `index_hist`)."""
    pt = live_point(market, sim_clock, day, key, history, region=region,
                    vol_mult=vol_mult, target=target)
    if pt is None:
        return list(history)
    return list(history) + [pt]


def intraday_series(market, sim_clock, day, key, history, window_minutes, n_points=60,
                     region=None, vol_mult=1.0, target=None):
    """FENÊTRE GLISSANTE sur le chemin canonique : `n_points` valeurs
    régulièrement espacées sur les `window_minutes` dernières minutes de jeu
    jusqu'à « maintenant » (progression quantifiée dans le pas courant).

    Comme dans une vraie app de trading : 1J est la queue de 1W, la courbe
    passe exactement par les clôtures du moteur (bornes des ponts), le
    dernier point coïncide avec `live_point` (ticker/sparkline), et quand le
    temps avance la fenêtre GLISSE sur un chemin figé — les points du passé
    sortent par la gauche sans jamais changer de valeur."""
    if not history or n_points < 2:
        return []
    total = minutes_per_step()
    progress = quantize_to_day(sim_clock.game_minutes_acc)
    now_abs = market.step_count * total + progress   # minute absolue « maintenant »
    out = []
    for k in range(n_points):
        m_abs = now_abs - window_minutes * (n_points - 1 - k) / (n_points - 1)
        m_abs = max(0.0, m_abs)
        s = int(m_abs // total)
        out.append(canonical_point(market, key, history, s, m_abs - s * total,
                                   region=region, vol_mult=vol_mult, target=target))
    return out


def points_per_segment_for_n_steps(n_steps):
    """Densité de bruit à insérer entre deux clôtures consécutives d'une série
    "par pas" (1M/3M/1A/3A/5A/MAX), en fonction du nombre de pas affichés —
    "l'adaptation du graphe à la taille de la période cliquée" (retour joueur) :
    plus la fenêtre est courte/zoomée, plus chaque segment mérite du détail ;
    plus elle est longue (5A/MAX), plus il y a déjà de points réels à l'écran
    et moins la densification apporte (tout en coûtant plus cher à calculer/
    dessiner) — désactivée au-delà de 3A."""
    if n_steps is None:
        return 0                       # MAX : historique long, déjà assez dense
    if n_steps <= 6:
        return 6                       # 1M
    if n_steps <= 18:
        return 4                       # 3M
    if n_steps <= 73:
        return 2                       # 1A
    if n_steps <= 219:
        return 1                       # 3A
    return 0                           # 5A : trop de segments pour que ça vaille le coût


def densify_step_series(market, key, closes, points_per_segment=4, region=None, vol_mult=1.0):
    """Remplace les segments de droite nus entre clôtures "par pas" consécutives
    par le CHEMIN CANONIQUE sous-échantillonné (même pont brownien que les
    fenêtres 1J/1W, même convention forward : le segment closes[i]→closes[i+1]
    est le pont du pas `base_step + i`) — chaque clôture réelle reste un point
    EXACT de la série retournée (bruit épinglé à 0 aux bornes), et la texture
    entre deux clôtures d'une vue 1M/3M est EXACTEMENT celle qu'on voit en
    zoomant sur la même période en 1W. `closes[-1]` doit correspondre au pas
    courant (`market.step_count`)."""
    n = len(closes)
    if n < 2 or points_per_segment < 1:
        return list(closes)
    total = minutes_per_step()
    base_step = market.step_count - (n - 1)
    out = [closes[0]]
    for i in range(n - 1):
        prev, cur = closes[i], closes[i + 1]
        step_k = base_step + i
        damp = region_open_factor(region, step_k) if region else 1.0
        for j in range(1, points_per_segment + 1):
            pm = total * j / (points_per_segment + 1)
            out.append(wiggle(market.seed, step_k, key, prev, cur, pm, damp=damp,
                              vol_mult=vol_mult))
        out.append(cur)
    return out


# Fenêtres « courtes » proposées dans les sélecteurs de période, en minutes de
# jeu — reconstruites par animation intraday (pont brownien) car plus fines que
# le pas du moteur (DAYS_PER_STEP=5 jours). En plus des périodes « par pas »
# (1M/3M/1A/3A/5A/MAX). 1J = 1 jour (1440 min), 1W = 1 semaine (7×1440 min).
INTRADAY_WINDOWS = [
    ("1J", 1440),
    ("1W", 10080),
]
