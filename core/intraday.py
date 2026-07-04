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
# zoomée (« 5 dernières minutes »). Poids de l'octave fine relevé (0.2 → 0.3)
# pour un tracé plus dense/dentelé, façon appli de trading grand public
# (retour joueur : les graphes "de vraie appli" zigzaguent beaucoup plus que
# notre courbe lissée précédente, cf. captures eToro fournies).
_RESOLUTIONS = (720, 60, 5)
_AMPLITUDES = (1.0, 0.5, 0.3)
# Amplitude relative max du bruit affiché (~0.45%) : purement visuel (n'affecte
# jamais market.price/index_value, donc jamais le prix d'exécution des ordres)
# — réduit pour assurer une meilleure cohérence entre périodes courtes et longues
# tout en restant visuellement dynamique.
_NOISE_PCT = 0.0035

# Sigma "moyen" du roster (cf. data/companies.py, profils sectoriels ~0.018-0.055) ;
# sert de référence pour que les sociétés volatiles (tech/semicon...) bougent
# visiblement plus que les défensives (utilities...) à l'écran. Plancher
# relevé (0.6 → 0.8) pour que même les valeurs défensives restent lisiblement
# animées plutôt que quasi plates.
_TYPICAL_SIGMA = 0.035
_VOL_MULT_RANGE = (0.8, 3.2)


def minutes_per_step():
    return config.DAYS_PER_STEP * MINUTES_PER_DAY


# Pas de rafraîchissement de l'animation « en direct » (minutes de jeu) : plus
# fin qu'un jour entier (90 min = 16 rafraîchissements/jour, ~toutes les 1-2s
# réelles à x1) pour que le marché bouge visiblement plusieurs fois par seconde
# de jeu au lieu d'un unique saut quotidien — tout en restant assez espacé
# pour rester lisible (pas un glissement continu à chaque frame).
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
    """Intensité de bruit relative à la vitesse de jeu (x1/x2/x3) : plus le temps
    défile vite, plus le marché doit sembler "vivant" à l'écran (sans toucher au
    pas du moteur ni au prix d'exécution). Augmenté pour more responsive real-time feel."""
    speed = getattr(sim_clock, "speed", 1)
    # Enhanced speed factor for more dynamic real-time updates
    base_factor = 1.0 + 0.25 * (speed - 1)  # Increased from 0.15 to 0.25
    # Add additional responsiveness for real-time feel
    return base_factor * 1.3  # 30% boost for more lively animation


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


def live_point(market, sim_clock, day, key, history, region=None, vol_mult=1.0, target=None):
    """Point "en direct" à ajouter en fin d'une série historique par pas.

    Modèle **forward-looking** : si `target` (clôture DÉTERMINISTE du prochain
    pas, cf. `Market.next_price_of/next_index_value`) est fourni, la valeur
    animée simule le chemin de la clôture COURANTE (`history[-1]`) vers cette
    destination au fil du pas — la courbe « se dirige » réellement vers le
    prochain pas et le % bouge en continu. Sans `target` (classes d'actifs sans
    anticipation), on retombe sur l'ancien pont `history[-2] → history[-1]`.

    Ensures consistency with intraday movements by using the same noise characteristics
    across all time scales."""
    if not history:
        return None
    cur = history[-1]
    if target is not None:
        start, end = cur, float(target)
    else:
        start, end = (history[-2] if len(history) >= 2 else cur), cur
    progress = quantize_to_day(sim_clock.game_minutes_acc)
    damp = region_open_factor(region, market.step_count) if region else 1.0

    # Ensure the live point movement is consistent with the overall trend
    # but still shows realistic intraday volatility
    base_movement = start + (end - start) * (progress / minutes_per_step())

    # Add noise that's consistent with the asset's volatility
    return wiggle(market.seed, market.step_count, key, start, end, progress, damp=damp,
                  vol_mult=vol_mult * speed_factor(sim_clock))


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
                     region=None, vol_mult=1.0):
    """`n_points` valeurs animées régulièrement espacées sur les
    `window_minutes` dernières minutes de jeu écoulées jusqu'à "maintenant"
    (remonte dans le(s) pas précédent(s) de `history` si la fenêtre dépasse
    les minutes déjà écoulées dans le pas courant — cas rare juste après un
    changement de pas).

    Ensures consistency with step-based data by using a representative sample
    of the longer-term trend while adding realistic intraday movements."""
    if not history or n_points < 2:
        return []
    total_minutes = minutes_per_step()
    out = []

    # For intraday periods, we want to reflect the recent trend but not be
    # completely disconnected from longer-term movements. Use a reasonable
    # window that captures recent movement but aligns with longer trends.

    # Use at least 5 steps to establish a trend, but not more than we have
    steps_for_trend = min(5, len(history) - 1)
    if steps_for_trend < 1:
        # Very limited history, just repeat the available point
        return [history[-1]] * n_points

    # Get recent history to establish trend
    trend_start_idx = len(history) - 1 - steps_for_trend
    trend_end_idx = len(history) - 1
    trend_history = history[trend_start_idx:trend_end_idx + 1]

    # Calculate the overall trend direction from this history
    if trend_history[0] != 0:
        overall_trend = (trend_history[-1] - trend_history[0]) / trend_history[0]
    else:
        overall_trend = 0

    # For 1W and shorter periods, we want to show intraday movements that
    # are consistent with the recent trend but still show realistic volatility
    for k in range(n_points):
        # Position within the overall series (0 to 1)
        series_frac = k / (n_points - 1) if n_points > 1 else 0

        # Map to position within our trend history
        trend_position = series_frac * (len(trend_history) - 1)
        trend_idx = int(trend_position)
        intra_trend_frac = trend_position - trend_idx

        # Handle edge cases
        if trend_idx >= len(trend_history) - 1:
            trend_idx = len(trend_history) - 2
            intra_trend_frac = 1.0
        if trend_idx < 0:
            trend_idx = 0
            intra_trend_frac = 0.0

        # Get the two prices we're interpolating between
        price_prev = trend_history[trend_idx]
        price_cur = trend_history[trend_idx + 1]

        # Calculate step for this position (for noise generation)
        step_for_noise = market.step_count - (len(history) - 1 - (trend_start_idx + trend_idx))

        # Calculate base interpolated value
        base_value = price_prev + (price_cur - price_prev) * intra_trend_frac

        # Add realistic intraday noise that respects the overall trend direction
        damp = region_open_factor(region, step_for_noise) if region else 1.0

        # Position within the current step (for intraday animation)
        minute_in_step = int(intra_trend_frac * total_minutes)

        # Adjust volatility based on trend consistency - if the overall trend
        # is strong, allow more movement in that direction
        trend_aligned_vol_mult = vol_mult
        if abs(overall_trend) > 0.01:  # 1% trend threshold
            # If we're moving in the same direction as the trend, allow normal volatility
            # If we're moving against the trend, reduce volatility
            expected_direction = 1 if overall_trend > 0 else -1
            current_direction = 1 if (price_cur - price_prev) > 0 else -1
            if expected_direction == current_direction:
                trend_aligned_vol_mult = vol_mult
            else:
                trend_aligned_vol_mult = vol_mult * 0.5  # Reduce volatility when moving against trend

        val = wiggle(market.seed, step_for_noise, key, price_prev, price_cur, minute_in_step,
                     damp=damp, vol_mult=trend_aligned_vol_mult * speed_factor(sim_clock))
        out.append(val)

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
    par un tracé organique (pont brownien déterministe, réutilise `wiggle`) —
    chaque clôture réelle reste un point EXACT de la série retournée (le bruit
    est épinglé à 0 aux deux bornes de chaque segment), seuls des points
    intermédiaires sont ajoutés. `closes[-1]` doit correspondre au pas courant
    (`market.step_count`).

    Ensures consistency with intraday data by using the same volatility scaling
    and noise characteristics, while maintaining trend alignment across periods."""
    n = len(closes)
    if n < 2 or points_per_segment < 1:
        return list(closes)
    total = minutes_per_step()
    base_step = market.step_count - (n - 1)

    # Calculate overall trend to ensure consistency
    if len(closes) > 1 and closes[0] != 0:
        overall_trend = (closes[-1] - closes[0]) / closes[0]
    else:
        overall_trend = 0

    out = [closes[0]]
    for i in range(n - 1):
        prev, cur = closes[i], closes[i + 1]
        step_k = base_step + i + 1
        damp = region_open_factor(region, step_k) if region else 1.0

        # Calculate local trend between these two points
        if prev != 0:
            local_trend = (cur - prev) / prev
        else:
            local_trend = 0

        # Adjust volatility based on trend consistency
        # If local trend matches overall trend, use normal volatility
        # If they oppose each other, reduce volatility for more realistic movements
        trend_alignment = 1.0
        if overall_trend != 0 and local_trend != 0:
            # Same direction trends
            if (overall_trend > 0 and local_trend > 0) or (overall_trend < 0 and local_trend < 0):
                trend_alignment = 1.0
            else:
                # Opposing trends - reduce volatility
                trend_alignment = 0.7

        # Add intermediate points for smooth animation
        for j in range(1, points_per_segment + 1):
            frac = j / (points_per_segment + 1)
            pm = total * frac
            adjusted_vol_mult = vol_mult * trend_alignment
            out.append(wiggle(market.seed, step_k, key, prev, cur, pm, damp=damp,
                              vol_mult=adjusted_vol_mult))

        # Add the end point
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
