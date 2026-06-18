"""
calculator.py — Calculatrice déplaçable (pour les calculs des missions).

Boutons cliquables (pas de capture clavier → n'interfère pas avec la saisie des
réponses). Évaluation sûre d'expressions arithmétiques via ast :
  + - * / parenthèses, ^ (puissance), % (modulo), décimales, signe négatif.
"""
import ast
import operator

import pygame

from core import config
from ui import fonts, widgets

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def safe_eval(expr):
    """Évalue une expression arithmétique simple. Retourne (valeur|None, ok)."""
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
    if not expr.strip():
        return None, False
    try:
        node = ast.parse(expr, mode="eval").body
        return _ev(node), True
    except Exception:
        return None, False


def _ev(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_ev(node.left), _ev(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_ev(node.operand))
    raise ValueError


# disposition des touches
_KEYS = [
    ["C", "(", ")", "<"],
    ["7", "8", "9", "/"],
    ["4", "5", "6", "*"],
    ["1", "2", "3", "-"],
    ["0", ".", "^", "+"],
    ["="],
]

TITLE_H = 22
PADX = 10


class Calculator:
    def __init__(self, pos=(900, 120)):
        self.expr = ""
        self.result = ""
        self.dragging = False
        self.closed = False
        self._drag_off = (0, 0)
        self._btn_rects = {}
        self.rect = pygame.Rect(pos[0], pos[1], 232, 286)

    def _title_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, TITLE_H)

    def _close_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H, self.rect.y, TITLE_H, TITLE_H)

    def _press(self, key):
        if key == "C":
            self.expr = ""
            self.result = ""
        elif key == "<":
            self.expr = self.expr[:-1]
        elif key == "=":
            val, ok = safe_eval(self.expr)
            if ok and val is not None:
                # affichage propre (entiers sans décimale)
                self.result = (f"{val:g}" if isinstance(val, float) else str(val))
            else:
                self.result = "erreur"
        else:
            self.expr += key

    def handle(self, event):
        """Retourne True si l'event est consommé."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_rect().collidepoint(event.pos):
                self.closed = True
                return True
            if self._title_rect().collidepoint(event.pos):
                self.dragging = True
                self._drag_off = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                return True
            for key, r in self._btn_rects.items():
                if r.collidepoint(event.pos):
                    self._press(key)
                    return True
            if self.rect.collidepoint(event.pos):
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.rect.x = max(0, min(config.SCREEN_WIDTH - self.rect.w,
                                     event.pos[0] - self._drag_off[0]))
            self.rect.y = max(config.TOPBAR_H, min(config.SCREEN_HEIGHT - 40,
                                                  event.pos[1] - self._drag_off[1]))
            return True
        return False

    def draw(self, surf):
        pygame.draw.rect(surf, (0, 0, 0), self.rect.move(0, 3), border_radius=6)
        pygame.draw.rect(surf, config.COL_PANEL, self.rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_AMBER, self.rect, 1, border_radius=6)
        tr = self._title_rect()
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, tr,
                         border_top_left_radius=6, border_top_right_radius=6)
        widgets.draw_text(surf, "CALCULATRICE", (tr.x + 8, tr.y + 4),
                          fonts.tiny(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "✕", (self._close_rect().centerx, tr.y + 4),
                          fonts.small(bold=True), config.COL_TEXT_DIM, align="center")
        # écran
        disp = pygame.Rect(self.rect.x + PADX, tr.bottom + 6, self.rect.w - 2 * PADX, 40)
        pygame.draw.rect(surf, (6, 8, 12), disp)
        pygame.draw.rect(surf, config.COL_BORDER, disp, 1)
        shown = self.expr or "0"
        widgets.draw_text(surf, shown[-18:], (disp.x + 6, disp.y + 4),
                          fonts.small(bold=True), config.COL_WHITE)
        if self.result != "":
            widgets.draw_text(surf, "= " + self.result, (disp.right - 6, disp.y + 20),
                              fonts.small(bold=True), config.COL_AMBER, align="right")
        # touches
        self._btn_rects = {}
        gx, gy = self.rect.x + PADX, disp.bottom + 8
        bw = (self.rect.w - 2 * PADX - 3 * 6) // 4
        bh = 30
        mp = pygame.mouse.get_pos()
        for row in _KEYS:
            x = gx
            for key in row:
                w = (self.rect.w - 2 * PADX) if key == "=" else bw
                r = pygame.Rect(x, gy, w, bh)
                self._btn_rects[key] = r
                hover = r.collidepoint(mp)
                op = key in "+-*/^()=C<"
                acc = config.COL_AMBER if key == "=" else (config.COL_CYAN if op else config.COL_BORDER)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_PANEL,
                                 r, border_radius=4)
                pygame.draw.rect(surf, acc, r, 1, border_radius=4)
                label = {"<": "⌫"}.get(key, key)
                img = fonts.small(bold=True).render(
                    label, True, config.COL_WHITE if not op else acc)
                surf.blit(img, img.get_rect(center=r.center))
                x += bw + 6
            gy += bh + 6
