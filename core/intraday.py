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
visiblement (mini-variations ~0.05-0.1%) même à l'échelle « 5 minutes »,
sans jamais affecter le prix d'exécution des ordres : BUY/SELL/SHORT/COVER
continuent d'utiliser `market.price`/`market.index_value`, inchangés.

Reconstruit entièrement depuis (seed, step_count, clé, minute) : pas d'état
à persister, pas de tirage rng consommé (donc aucun décalage des saves).
"""
from core import config, market_hours

MINUTES_PER_DAY = 24 * 60

# Résolutions des octaves de bruit (minutes), du plus grossier au plus fin —
# la plus fine (5 min) garantit de la texture même sur la fenêtre la plus
# zoomée (« 5 dernières minutes »).
_RESOLUTIONS = (720, 60, 5)
_AMPLITUDES = (1.0, 0.45, 0.2)
_NOISE_PCT = 0.0009  # amplitude relative max du bruit (~0.09%, "vraie vie")


def minutes_per_step():
    return config.DAYS_PER_STEP * MINUTES_PER_DAY


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


def region_open_factor(region, day, minute_of_day):
    """1.0 si la place régionale est ouverte, 0.0 sinon (gèle le bruit —
    la dérive linéaire vers la prochaine clôture continue malgré tout : c'est
    une approximation volontaire, le moteur de marché n'a pas de notion de
    "prix de clôture exact à l'instant de fermeture")."""
    if region is None:
        return 1.0
    return 1.0 if market_hours.is_region_open(region, day, minute_of_day) else 0.0


def wiggle(seed, step_count, key, prev_close, cur_close, progress_minutes, damp=1.0):
    """Valeur animée entre `prev_close` (progress=0) et `cur_close`
    (progress=minutes_per_step()), avec bruit multiplicatif pondéré par
    `damp` (0..1)."""
    total = minutes_per_step()
    t = max(0.0, min(1.0, progress_minutes / total))
    base = prev_close * (1 - t) + cur_close * t
    if damp <= 0:
        return base
    pinned = _pinned_noise(seed, step_count, key, progress_minutes)
    return base * (1 + _NOISE_PCT * damp * pinned)


def live_point(market, sim_clock, day, key, history, region=None):
    """Point "en direct" à ajouter en fin d'une série historique par pas
    (`history[-1]` = clôture du pas courant, `history[-2]` = clôture
    précédente) — pour faire bouger n'importe quel graphe existant sans
    changer sa résolution de données."""
    if not history:
        return None
    cur = history[-1]
    prev = history[-2] if len(history) >= 2 else cur
    progress = sim_clock.game_minutes_acc
    damp = region_open_factor(region, day, sim_clock.current_time(day)[1]) if region else 1.0
    return wiggle(market.seed, market.step_count, key, prev, cur, progress, damp=damp)


def append_live(market, sim_clock, day, key, history, region=None):
    """Renvoie une COPIE de `history` avec un point animé ajouté en fin
    (n'altère jamais la liste d'origine — utile quand `history` est une
    référence interne au moteur de marché, p. ex. `index_hist`)."""
    pt = live_point(market, sim_clock, day, key, history, region=region)
    if pt is None:
        return list(history)
    return list(history) + [pt]


def intraday_series(market, sim_clock, day, key, history, window_minutes, n_points=60,
                     region=None):
    """`n_points` valeurs animées régulièrement espacées sur les
    `window_minutes` dernières minutes de jeu écoulées jusqu'à "maintenant"
    (remonte dans le(s) pas précédent(s) de `history` si la fenêtre dépasse
    les minutes déjà écoulées dans le pas courant — cas rare juste après un
    changement de pas)."""
    if not history or n_points < 2:
        return []
    total_minutes = minutes_per_step()
    progress = sim_clock.game_minutes_acc
    minute_of_day = sim_clock.current_time(day)[1] if region else 0
    damp = region_open_factor(region, day, minute_of_day) if region else 1.0
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
        val = wiggle(market.seed, market.step_count - back_steps, key, prev, cur, pm, damp=damp)
        out.append(val)
    return out


# Granularités intraday proposées dans les sélecteurs de période, en minutes
# de jeu — toutes en plus des périodes "par pas" existantes (1A/3A/5A/MAX).
INTRADAY_WINDOWS = [
    ("5M", 5), ("10M", 10), ("30M", 30), ("1H", 60), ("2H", 120),
]
