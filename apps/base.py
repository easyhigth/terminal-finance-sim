"""
base.py — Classe de base des applications du bureau.

Une `DesktopApp` dessine dans le rectangle de contenu de sa fenêtre (fourni à
chaque frame, coordonnées ABSOLUES à l'écran) et reçoit les évènements pygame
quand sa fenêtre est focalisée. Convention de layout : les sous-rectangles
cliquables sont recalculés dans `draw()` et mémorisés sur l'instance, puis
testés dans `handle_event()` (même pattern que les scènes existantes).
"""


class DesktopApp:
    title = "Application"
    icon_kind = "generic"   # clé d'icône vectorielle (cf. ui/desktop_icons.py)
    default_size = (760, 480)
    min_size = (340, 240)

    def __init__(self, app):
        self.app = app          # référence à l'App globale (marché, gs, horloge…)
        self.desktop = None     # back-ref vers DesktopScene (liens inter-apps),
        #                         posée par DesktopScene lors du lancement.

    def on_open(self):
        """Appelé une fois, à l'ouverture de la fenêtre."""
        pass

    def update(self, dt):
        pass

    def draw(self, surf, rect):
        """Dessine le contenu dans `rect` (Rect absolu)."""
        pass

    def handle_event(self, event, rect):
        """Traite un évènement (fenêtre focalisée). `rect` = zone de contenu.
        Retourne True si consommé."""
        return False
