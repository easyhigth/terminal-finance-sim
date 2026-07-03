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
# — poussé une 2e fois au-delà de la valeur précédente (0.22%, elle-même déjà
# au-delà de la "vraie vie" à 0.09% à l'origine) : à 0.22%, l'intraday restait
# visuellement trop plat comparé à une vraie appli de trading (retour joueur,
# captures eToro à l'appui) — viser une variation intrajournalière de l'ordre
# de quelques % plutôt que quelques dixièmes de %.
_NOISE_PCT = 0.0045

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
# fin qu'un jour entier (360 min = 4 rafraîchissements/jour, ~toutes les 4s
# réelles à x1) pour que le marché bouge visiblement plusieurs fois par jour
# de jeu au lieu d'un unique saut quotidien — tout en restant assez espacé
# pour rester lisible (pas un glissement continu à chaque frame).
QUANTIZE_MINUTES = 360


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
    pas du moteur ni au prix d'exécution)."""
    speed = getattr(sim_clock, "speed", 1)
    return 1.0 + 0.15 * (speed - 1)


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
    anticipation), on retombe sur l'ancien pont `history[-2] → history[-1]`."""
    if not history:
        return None
    cur = history[-1]
    if target is not None:
        start, end = cur, float(target)
    else:
        start, end = (history[-2] if len(history) >= 2 else cur), cur
    progress = quantize_to_day(sim_clock.game_minutes_acc)
    damp = region_open_factor(region, market.step_count) if region else 1.0
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
    changement de pas)."""
    if not history or n_points < 2:
        return []
    total_minutes = minutes_per_step()
    progress = quantize_to_day(sim_clock.game_minutes_acc)
    out = []
    for k in range(n_points):
        ago = window_minutes * (n_points - 1 - k) / (n_points - 1)
        pm = progress - ago
        back_steps = 0
        while pm < 0:
            pm += total_minutes
            back_steps += 1
        idx_cur = len(history) - 1 - back_steps
        idx_prev = idx_cur - 1
        cur = history[idx_cur] if 0 <= idx_cur < len(history) else history[0]
        prev = history[idx_prev] if 0 <= idx_prev < len(history) else cur
        step_k = market.step_count - back_steps
        damp = region_open_factor(region, step_k) if region else 1.0
        val = wiggle(market.seed, step_k, key, prev, cur, pm, damp=damp,
                     vol_mult=vol_mult * speed_factor(sim_clock))
        out.append(val)
    return out


# Fenêtres « courtes » proposées dans les sélecteurs de période, en minutes de
# jeu — reconstruites par animation intraday (pont brownien) car plus fines que
# le pas du moteur (DAYS_PER_STEP=5 jours). En plus des périodes « par pas »
# (1M/3M/1A/3A/5A/MAX). 1J = 1 jour (1440 min), 1W = 1 semaine (7×1440 min).
INTRADAY_WINDOWS = [
    ("1J", 1440),
    ("1W", 10080),
]
