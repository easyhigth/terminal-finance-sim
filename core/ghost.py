"""
ghost.py — RUNS FANTÔMES : la courbe de patrimoine d'un ami en surimpression.

Le partage par code (core/challenge_share.py) transportait un score final ;
il embarque désormais aussi la COURBE de patrimoine compressée du run
(`curve` : jusqu'à GHOST_POINTS ratios de croissance depuis le départ,
arrondis — quelques dizaines d'octets). Quand vous jouez le MÊME défi du
jour qu'un ami importé, sa trajectoire s'affiche en fantôme sur votre courbe
de patrimoine (widget du bureau + rétrospective de fin de run) : la
compétition asynchrone en direct, toujours sans serveur.

Les courbes sont normalisées en CROISSANCE (valeur / valeur initiale) : deux
joueurs aux capitaux différents se comparent à armes égales, et le fantôme
se projette sur l'échelle du joueur local (départ × ratio).
"""
GHOST_POINTS = 40      # points max embarqués dans un code (compacité)
MAX_GHOSTS = 3         # fantômes affichés simultanément (lisibilité)


def compress_curve(history, n_points=GHOST_POINTS):
    """Compresse un historique de valeur nette en ratios de croissance
    (premier point = 1.0), rééchantillonné à `n_points` max. Retourne None
    si l'historique est trop court ou dégénéré."""
    if not history or len(history) < 2 or not history[0]:
        return None
    base = float(history[0])
    if base <= 0:
        return None
    n = min(n_points, len(history))
    out = []
    for i in range(n):
        src_idx = round(i * (len(history) - 1) / (n - 1))
        out.append(round(float(history[src_idx]) / base, 4))
    return out


def ghosts_for(player):
    """Fantômes affichables pour CE run : les amis importés
    (core/hall_of_fame.load_friends) qui ont joué LE MÊME défi du jour et
    dont le code contenait une courbe. [] pour un run classique."""
    daily = player.flags.get("daily_challenge")
    if not daily:
        return []
    from core import hall_of_fame as hof
    out = []
    for entry in hof.load_friends():
        if entry.get("daily_date") != daily:
            continue
        curve = entry.get("curve")
        if not curve or len(curve) < 2:
            continue
        out.append({"name": entry.get("name", "?"), "curve": curve})
        if len(out) >= MAX_GHOSTS:
            break
    return out


def project(curve, start_value, n_points):
    """Projette une courbe fantôme (ratios) sur l'échelle du joueur local :
    `start_value` × ratio, rééchantillonnée à `n_points` pour partager l'axe
    des X avec la courbe locale."""
    if not curve or n_points < 2:
        return []
    out = []
    for i in range(n_points):
        src_idx = round(i * (len(curve) - 1) / (n_points - 1))
        out.append(start_value * curve[src_idx])
    return out
