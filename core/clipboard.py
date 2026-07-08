"""
clipboard.py — Accès best-effort au presse-papiers système (pygame.scrap),
partagé par tous les champs de saisie texte du jeu (Ctrl+C copie déjà via
scenes/scene_commands._try_clipboard ; ce module ajoute le côté LECTURE,
Ctrl+V, pour les boîtes de dialogue comme « Importer un code » de
scenes/scene_gameover.py ou les chemins d'export/import de
scenes/scene_saves.py).

pygame.scrap n'est pas toujours disponible (headless/CI, plateforme sans
presse-papiers) : toutes les fonctions sont silencieuses en cas d'échec,
jamais bloquantes ni levantes.
"""


def copy(text):
    """Copie `text` dans le presse-papiers système (silencieux si indispo)."""
    try:
        import pygame.scrap as scrap
        if not scrap.get_init():
            scrap.init()
        scrap.put(_scrap_text_type(), text.encode("utf-8"))
    except Exception:
        pass


def paste():
    """Retourne le texte du presse-papiers système, ou "" si indisponible/vide."""
    try:
        import pygame.scrap as scrap
        if not scrap.get_init():
            scrap.init()
        raw = scrap.get(_scrap_text_type())
        if not raw:
            return ""
        text = raw.decode("utf-8", errors="ignore")
        # certaines plateformes terminent la donnée par un octet nul
        return text.split("\x00", 1)[0]
    except Exception:
        return ""


def _scrap_text_type():
    import pygame
    return pygame.SCRAP_TEXT


def is_paste_shortcut(event):
    """Vrai si l'évènement clavier est le raccourci Ctrl+V (ou Cmd+V sur Mac)."""
    import pygame
    return (event.type == pygame.KEYDOWN and event.key == pygame.K_v
            and (event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)))
