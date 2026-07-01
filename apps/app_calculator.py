"""
app_calculator.py — Application « Calculatrice » du bureau.

Jusqu'ici la calculatrice scientifique (`ui/calculator.py`) n'était accessible
que depuis les missions/examens (bouton dédié, overlay flottant). Elle devient
une app à part entière du bureau, ouvrable à tout moment — le chrome de
fenêtre (déplacer/fermer/redimensionner) est fourni par `ui/window_manager.py`,
donc cette app réutilise uniquement la logique de calcul (`ui.calculator.
safe_eval`) et le clavier de touches, sans le cadre/titre/glisser du widget
flottant d'origine (redondant avec la fenêtre qui l'héberge).
"""
import pygame

from apps.base import DesktopApp
from core import config
from ui import fonts, widgets
from ui.calculator import _INSERT, _KEYS, _KP_MAP, _TYPABLE, safe_eval

PADX = 10


class CalculatorApp(DesktopApp):
    title = "Calculatrice"
    icon_kind = "calc"
    default_size = (280, 400)
    min_size = (240, 340)

    def on_open(self):
        self.expr = ""
        self.result = ""
        self._btn_rects = {}

    def _press(self, key):
        if key == "C":
            self.expr = ""
            self.result = ""
        elif key == "<":
            self.expr = self.expr[:-1]
        elif key == "=":
            val, ok = safe_eval(self.expr)
            if ok and val is not None:
                self.result = f"{val:g}" if isinstance(val, float) else str(val)
            else:
                self.result = "erreur"
        else:
            self.expr += _INSERT.get(key, key)

    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, r in self._btn_rects.items():
                if r.collidepoint(event.pos):
                    self._press(key)
                    return True
            return True
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._press("=")
                return True
            if event.key == pygame.K_BACKSPACE:
                self._press("<")
                return True
            if event.key in _KP_MAP:
                self.expr += _KP_MAP[event.key]
                return True
            if event.unicode and (event.unicode in _TYPABLE or event.unicode.isalpha()):
                self.expr += event.unicode
                return True
        return False

    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        # écran
        disp = pygame.Rect(rect.x + PADX, rect.y + PADX, rect.w - 2 * PADX, 44)
        pygame.draw.rect(surf, (6, 8, 12), disp)
        pygame.draw.rect(surf, config.COL_BORDER, disp, 1)
        shown = self.expr or "0"
        widgets.draw_text(surf, shown[-20:], (disp.x + 6, disp.y + 4),
                          fonts.small(bold=True), config.COL_WHITE)
        if self.result != "":
            widgets.draw_text(surf, "= " + self.result, (disp.right - 6, disp.y + 22),
                              fonts.small(bold=True), config.COL_AMBER, align="right")
        # touches
        self._btn_rects = {}
        gx, gy = rect.x + PADX, disp.bottom + 8
        avail_w = rect.w - 2 * PADX
        bw = (avail_w - 3 * 6) // 4
        n_rows = len(_KEYS)
        bh = max(24, min(34, (rect.bottom - PADX - gy - (n_rows - 1) * 6) // n_rows))
        mp = pygame.mouse.get_pos()
        for row in _KEYS:
            x = gx
            for key in row:
                w = avail_w if key == "=" else bw
                r = pygame.Rect(x, gy, w, bh)
                self._btn_rects[key] = r
                hover = r.collidepoint(mp)
                op = key in "+-*/^()=C<"
                sci = key in _INSERT
                acc = (config.COL_AMBER if key == "=" else
                       config.COL_CYAN if op else
                       config.COL_PRESTIGE if sci else config.COL_BORDER)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD if hover else config.COL_BG,
                                 r, border_radius=4)
                pygame.draw.rect(surf, acc, r, 1, border_radius=4)
                label = {"<": "⌫"}.get(key, key)
                img = fonts.small(bold=True).render(
                    label, True, config.COL_WHITE if not (op or sci) else acc)
                surf.blit(img, img.get_rect(center=r.center))
                x += bw + 6
            gy += bh + 6
