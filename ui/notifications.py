"""
notifications.py — Centre de notifications (toasts animés).

Une instance unique vit sur l'App (app.notes). N'importe quelle scène peut
pousser une notification via app.notify(texte, kind). Les toasts s'empilent en
haut à droite, glissent à l'entrée et s'estompent à la sortie. Dessinés en
overlay par le SceneManager après la scène courante.
"""
import pygame

from core import config, crashlog
from ui import fonts

_KIND_COLOR = {
    "good": config.COL_EVENT_GOOD,
    "bad": config.COL_EVENT_BAD,
    "warn": config.COL_WARN,
    "info": config.COL_CYAN,
    "prestige": config.COL_PRESTIGE,
}

TTL = 3.4          # durée de vie (s)
SLIDE = 0.25       # durée d'entrée (s)
FADE = 0.6         # durée de sortie (s)
WIDTH = 320
HEIGHT = 46
MARGIN = 14
GAP = 8


class NotificationCenter:
    def __init__(self):
        self.toasts = []      # actifs : {text, kind, age, rect, on_click}
        self.history = []     # derniers messages, pour le centre de
        #                        notifications (apps/app_notifications.py)

    def push(self, text, kind="info", action=None, action_kwargs=None, day=None,
             on_click=None):
        """`action` : nom de scène optionnel (cf. `App.route_scene`) ouvert en
        cliquant la ligne d'historique correspondante dans le centre de
        notifications — retrouver le contexte d'un évènement passé sans
        rejouer la partie pour le voir. `day` : jour de jeu au moment de la
        notification (affiché dans le panneau), passé par l'appelant car ce
        module ne connaît pas `player`.

        `on_click` : callable optionnel exécuté quand le toast est cliqué.
        Les toasts avec on_click affichent une petite indication visuelle."""
        self.toasts.append({"text": text, "kind": kind, "age": 0.0,
                            "on_click": on_click})
        self.history.append({"text": text, "kind": kind, "action": action,
                             "action_kwargs": action_kwargs or {}, "day": day})
        if len(self.history) > 60:
            self.history.pop(0)
        # limite le nombre de toasts simultanés
        if len(self.toasts) > 5:
            self.toasts.pop(0)

    def update(self, dt):
        for t in self.toasts:
            t["age"] += dt
        self.toasts = [t for t in self.toasts if t["age"] < TTL]

    def handle_event(self, event):
        """Retourne True si un toast a été cliqué et son action exécutée."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        for t in self.toasts:
            rect = t.get("rect")
            if rect and rect.collidepoint(event.pos):
                cb = t.get("on_click")
                if cb:
                    try:
                        cb()
                    except Exception:
                        crashlog.swallowed("ui.notifications")  # retire le toast cliqué (feedback immédiat)
                t["age"] = TTL
                return True
        return False

    def draw(self, surf):
        if not self.toasts:
            return
        sw = surf.get_width()
        # ancrage en bas à droite (empilage vers le haut), au-dessus de la console
        y = surf.get_height() - 140
        for t in reversed(self.toasts):
            age = t["age"]
            # alpha : fondu d'entrée et de sortie
            if age < SLIDE:
                appear = age / SLIDE
            elif age > TTL - FADE:
                appear = max(0.0, (TTL - age) / FADE)
            else:
                appear = 1.0
            # glissement horizontal à l'entrée (depuis le bord droit)
            slide = 1.0 if age >= SLIDE else (age / SLIDE)
            x = sw - MARGIN - WIDTH + int((1 - slide) * WIDTH)
            col = _KIND_COLOR.get(t["kind"], config.COL_CYAN)
            clickable = t.get("on_click") is not None

            chip = pygame.Surface((WIDTH, HEIGHT + 4), pygame.SRCALPHA)
            a = int(255 * appear)        # fond OPAQUE : le texte derrière ne transparaît plus
            chip.fill((0, 0, 0, 0))
            # ombre portée (lit le toast comme une carte flottant au-dessus du contenu)
            pygame.draw.rect(chip, (0, 0, 0, int(120 * appear)), (2, 4, WIDTH, HEIGHT), border_radius=6)
            pygame.draw.rect(chip, (*config.COL_BG, a), (0, 0, WIDTH, HEIGHT), border_radius=6)
            pygame.draw.rect(chip, (*config.COL_PANEL_HEAD, a), (0, 0, WIDTH, HEIGHT), border_radius=6)
            pygame.draw.rect(chip, (*col, a), (0, 0, WIDTH, HEIGHT), 1, border_radius=6)
            pygame.draw.rect(chip, (*col, a), (0, 0, 4, HEIGHT), border_top_left_radius=6,
                             border_bottom_left_radius=6)
            # texte (tronqué)
            font = fonts.small(bold=True)
            text = t["text"]
            max_text_w = WIDTH - 42 if clickable else WIDTH - 24
            while font.size(text)[0] > max_text_w and len(text) > 4:
                text = text[:-2]
            img = font.render(text, True, col)
            img.set_alpha(a)
            chip.blit(img, (14, (HEIGHT - img.get_height()) // 2))
            # indicateur visuel de cliquable
            if clickable:
                indicator = fonts.tiny(bold=True).render("→", True, col)
                indicator.set_alpha(a)
                chip.blit(indicator, (WIDTH - indicator.get_width() - 10,
                                      (HEIGHT - indicator.get_height()) // 2))
            surf.blit(chip, (x, y))
            # mémorise le rect absolu pour le clic
            t["rect"] = pygame.Rect(x, y, WIDTH, HEIGHT)
            y -= HEIGHT + GAP
