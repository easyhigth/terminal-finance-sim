"""
sim_clock.py — Horloge de jeu temps réel (remplace l'avance par à-coups « ADV »).

Le temps de jeu avance en continu, à une vitesse réglable (pause, x1, x2, x3).
À x1, 1 minute réelle = 1 heure de jeu. Le moteur de marché reste celui par
paliers de `config.DAYS_PER_STEP` jours (`core/market.py::step`) : l'horloge
ne fait qu'accumuler des minutes de jeu et les convertir en « pas de marché en
attente » (`App.pending_market_steps`), exécutés par
`TerminalTimeMixin._drain_pending_steps()` quand le joueur est sur le terminal.

Mise en pause automatique : le jeu se met en pause dès que le joueur quitte
la scène terminal (mission, examen, deal, dilemme...) et reprend exactement
où il en était au retour — aucune minute de jeu n'est comptée pendant ce
temps, donc aucun pas de marché ne s'accumule en arrière-plan.
"""

# 1 minute réelle = 1 heure de jeu à vitesse x1 (cf. décision produit).
GAME_MINUTES_PER_REAL_SECOND_AT_X1 = 60.0 / 60.0  # = 1.0 minute de jeu / seconde réelle

# Un pas de marché = config.DAYS_PER_STEP jours de jeu.
MINUTES_PER_DAY = 24 * 60

# Nom de la seule scène où le temps avance « au premier plan » (Phase 1).
# Les scènes de trading rejoindront cet ensemble en Phase 3.
LIVE_SCENE_NAMES = {"terminal"}

SPEEDS = (1, 2, 3)


class SimClock:
    """Horloge de jeu : vitesse, pause manuelle/auto, minutes de jeu accumulées."""

    def __init__(self):
        self.speed = 1            # 1, 2 ou 3 (x1/x2/x3)
        self.paused = False       # pause manuelle (bouton ⏸ / touche)
        self.auto_paused = False  # pause automatique (scène hors terminal)
        self.game_minutes_acc = 0.0   # minutes de jeu en attente de conversion en pas

    def effective_speed(self):
        """Vitesse réellement appliquée (0 si en pause, manuelle ou auto)."""
        if self.paused or self.auto_paused:
            return 0
        return self.speed

    def is_running(self):
        return self.effective_speed() > 0

    def set_speed(self, speed):
        if speed in SPEEDS:
            self.speed = speed
            self.paused = False

    def toggle_pause(self):
        self.paused = not self.paused

    def set_auto_paused(self, value):
        self.auto_paused = bool(value)

    def current_time(self, base_day):
        """(jour, minute du jour) courants, dérivés des minutes de jeu
        accumulées depuis le dernier pas de marché complet — `base_day` est
        le jour de jeu courant (`player.day`), qui n'avance que par pas
        complets de `config.DAYS_PER_STEP` jours. Utilisé par
        `core.market_hours` pour déterminer si un marché régional est ouvert."""
        sub_day, minute_of_day = divmod(self.game_minutes_acc, MINUTES_PER_DAY)
        return base_day + int(sub_day), int(minute_of_day)

    def advance(self, dt_real_seconds, days_per_step):
        """Avance l'horloge de `dt_real_seconds` secondes réelles. Retourne le
        nombre de pas de marché (`days_per_step` jours chacun) à exécuter."""
        speed = self.effective_speed()
        if speed <= 0:
            return 0
        self.game_minutes_acc += dt_real_seconds * speed * GAME_MINUTES_PER_REAL_SECOND_AT_X1
        minutes_per_step = days_per_step * MINUTES_PER_DAY
        steps = 0
        while self.game_minutes_acc >= minutes_per_step:
            self.game_minutes_acc -= minutes_per_step
            steps += 1
        return steps
