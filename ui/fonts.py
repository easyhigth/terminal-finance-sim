"""
fonts.py — Chargement et cache des polices.

On EMBARQUE JetBrains Mono (OFL, dans assets/fonts/) pour un rendu IDENTIQUE sur
macOS, Windows et Linux — fini les glyphes « tofu » qui dépendaient de la police
système. La graisse Bold est une vraie fonte dédiée (pas un gras synthétique).

Repli : si les fichiers embarqués manquent, on retombe sur une monospace système
puis sur la police par défaut de pygame.
"""
import os
import sys
import pygame
from core import config


def _assets_dir():
    """Dossier des polices embarquées (gère le bundle PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "fonts")


_REG = os.path.join(_assets_dir(), "JetBrainsMono-Regular.ttf")
_BOLD = os.path.join(_assets_dir(), "JetBrainsMono-Bold.ttf")
_HAS_EMBEDDED = os.path.exists(_REG) and os.path.exists(_BOLD)

# Repli système (si la police embarquée est absente)
_MONO_CANDIDATES = [
    "Menlo", "Monaco", "SFMono-Regular", "Consolas",
    "DejaVu Sans Mono", "Courier New", "monospace",
]

_cache = {}


def _resolve_system_mono():
    available = set(pygame.font.get_fonts())
    for name in _MONO_CANDIDATES:
        norm = name.lower().replace(" ", "").replace("-", "")
        if norm in available:
            return pygame.font.match_font(name)
    return pygame.font.match_font("monospace") or None


def get(size, bold=False):
    """Retourne une police monospace de la taille demandée (avec cache)."""
    key = (size, bold)
    if key in _cache:
        return _cache[key]

    if _HAS_EMBEDDED:
        font = pygame.font.Font(_BOLD if bold else _REG, size)
    else:
        path = _resolve_system_mono()
        if path:
            font = pygame.font.Font(path, size)
        else:
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
