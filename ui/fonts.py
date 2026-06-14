"""
fonts.py — Chargement et cache des polices.
On privilégie une police monospace pour l'ambiance terminal.
Pygame utilise une police système monospace si aucune n'est fournie ;
on tente plusieurs noms courants avant le fallback par défaut.
"""
import pygame
from core import config

# Noms de polices monospace courantes (macOS, Windows, Linux)
_MONO_CANDIDATES = [
    "Menlo", "Monaco", "SFMono-Regular", "Consolas",
    "DejaVu Sans Mono", "Courier New", "monospace",
]

_cache = {}


def _resolve_mono_path():
    """Retourne un nom/chemin de police monospace disponible, ou None."""
    available = set(pygame.font.get_fonts())
    for name in _MONO_CANDIDATES:
        # get_fonts() renvoie des noms normalisés (minuscules, sans espaces)
        norm = name.lower().replace(" ", "").replace("-", "")
        if norm in available:
            return pygame.font.match_font(name)
    return pygame.font.match_font("monospace") or None


def get(size, bold=False):
    """Retourne une police monospace de la taille demandée (avec cache)."""
    key = (size, bold)
    if key in _cache:
        return _cache[key]

    path = _resolve_mono_path()
    if path:
        font = pygame.font.Font(path, size)
    else:
        # Fallback ultime : police par défaut de pygame
        font = pygame.font.Font(None, int(size * 1.1))
    font.set_bold(bold)
    _cache[key] = font
    return font


# Raccourcis pratiques --------------------------------------------------------
def tiny(bold=False):  return get(config.FONT_SIZE_TINY, bold)
def small(bold=False): return get(config.FONT_SIZE_SMALL, bold)
def body(bold=False):  return get(config.FONT_SIZE_BODY, bold)
def head(bold=False):  return get(config.FONT_SIZE_HEAD, bold)
def title(bold=False): return get(config.FONT_SIZE_TITLE, bold)
def huge(bold=False):  return get(config.FONT_SIZE_HUGE, bold)
