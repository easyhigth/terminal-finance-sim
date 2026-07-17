"""
preview_panel.py — Panneau AVANT → APRÈS réutilisable (rendu pygame du
simulateur core/trade_preview.py).

TOUTES les apps de trading affichent le même panneau avec la même grille —
cash, levier, bêta, VaR vs limite, FLUX PAR TOUR — pour que l'action la plus
exotique (TRS, repo…) se lise exactement comme un achat d'action. Fournit
aussi la rangée de STRESS (« Marché -10 % / Taux +1 pt / Vol ×2 ») avec
l'effet avant/après.

Usage (dans le draw d'un ticket, après avoir calculé la preview UNE fois au
changement de saisie — jamais à chaque frame, la VaR coûte) :

    h = preview_panel.draw(surf, rect, pv, cur="$")
    preview_panel.draw_stress(surf, rect2, stress_rows)
"""
import pygame

from core import config
from core.i18n import get_lang
from ui import fonts, widgets

ROW_H = 17


def _L(fr, en):
    return en if get_lang() == "en" else fr


def _fmt_money(v, cur):
    return widgets.format_money(v, cur)


def _delta_color(delta, higher_is_worse=False):
    if abs(delta) < 1e-9:
        return config.COL_TEXT_DIM
    good = (delta < 0) if higher_is_worse else (delta > 0)
    return config.COL_UP if good else config.COL_DOWN


def draw(surf, rect, pv, cur="$"):
    """Dessine la grille avant→après de `pv` (cf. trade_preview.preview) dans
    `rect`. Retourne la hauteur utilisée. Si l'action a été refusée, affiche
    la raison et s'arrête là."""
    x, y = rect.x, rect.y
    widgets.draw_text(surf, _L("IMPACT SUR VOTRE PORTEFEUILLE",
                               "IMPACT ON YOUR PORTFOLIO"),
                      (x, y), fonts.tiny(bold=True), config.COL_CYAN)
    y += ROW_H
    result = pv.get("result") or {}
    if pv.get("after") is None:
        reason = result.get("reason", "?") if isinstance(result, dict) else "?"
        widgets.draw_text_wrapped(
            surf, _L(f"Ordre refusé ({reason}).", f"Order rejected ({reason})."),
            (x, y), fonts.tiny(), config.COL_DOWN, rect.w)
        return (y + ROW_H) - rect.y

    b, a = pv["before"], pv["after"]
    rows = [
        (_L("Cash", "Cash"),
         _fmt_money(b["cash"], cur), _fmt_money(a["cash"], cur),
         _delta_color(a["cash"] - b["cash"])),
        (_L("Levier", "Leverage"),
         f"{b['leverage']:.2f}x", f"{a['leverage']:.2f}x",
         _delta_color(a["leverage"] - b["leverage"], higher_is_worse=True)),
        (_L("Bêta", "Beta"),
         f"{b['beta']:.2f}", f"{a['beta']:.2f}",
         config.COL_TEXT),
    ]
    if b.get("var") is not None and a.get("var") is not None:
        limit = a.get("var_limit") or 0.0
        var_col = (config.COL_DOWN if limit and a["var"] > limit else
                   config.COL_WARN if limit and a["var"] > 0.8 * limit else
                   config.COL_TEXT)
        rows.append((_L("VaR 95 %", "95% VaR"),
                     f"{b['var']:.2f} M", f"{a['var']:.2f} M" +
                     (f"  ({_L('limite', 'limit')} {limit:.2f})" if limit else ""),
                     var_col))
    fb, fa = pv.get("flux_before"), pv.get("flux_after")
    if fb is not None and fa is not None:
        rows.append((_L("Flux/tour", "Flow/step"),
                     f"{fb:+,.0f}", f"{fa:+,.0f}",
                     _delta_color(fa - fb)))

    label_w = 74
    mid_w = (rect.w - label_w - 24) // 2
    for label, before_txt, after_txt, col in rows:
        widgets.draw_text(surf, label, (x, y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.fit_text(before_txt, fonts.tiny(), mid_w),
                          (x + label_w, y), fonts.tiny(), config.COL_TEXT)
        # flèche vectorielle (pas de glyphe unicode, cf. convention icônes)
        ax = x + label_w + mid_w + 4
        ay = y + 6
        pygame.draw.line(surf, config.COL_TEXT_DIM, (ax, ay), (ax + 8, ay), 1)
        pygame.draw.line(surf, config.COL_TEXT_DIM, (ax + 5, ay - 3), (ax + 8, ay), 1)
        pygame.draw.line(surf, config.COL_TEXT_DIM, (ax + 5, ay + 3), (ax + 8, ay), 1)
        widgets.draw_text(surf, widgets.fit_text(after_txt, fonts.tiny(), mid_w + 40),
                          (ax + 14, y), fonts.tiny(bold=True), col)
        y += ROW_H
    return y - rect.y


def draw_stress(surf, rect, stress_rows, cur="$"):
    """Rangée de stress (cf. trade_preview.stress_compare) : pour chaque
    scénario, la perte AVANT → APRÈS l'action. Retourne la hauteur utilisée."""
    x, y = rect.x, rect.y
    widgets.draw_text(surf, _L("ET SI… (effet sur tout le portefeuille)",
                               "WHAT IF… (whole portfolio effect)"),
                      (x, y), fonts.tiny(bold=True), config.COL_CYAN)
    y += ROW_H
    for row in stress_rows:
        label = _L(*row["label"])
        widgets.draw_text(surf, label, (x, y), fonts.tiny(), config.COL_TEXT_DIM)
        before_txt = f"{row['before']:+,.0f}"
        col_b = config.COL_DOWN if row["before"] < 0 else config.COL_TEXT
        widgets.draw_text(surf, before_txt, (x + 120, y), fonts.tiny(), col_b)
        if row.get("after") is not None:
            ax = x + 214
            ay = y + 6
            pygame.draw.line(surf, config.COL_TEXT_DIM, (ax, ay), (ax + 8, ay), 1)
            pygame.draw.line(surf, config.COL_TEXT_DIM, (ax + 5, ay - 3), (ax + 8, ay), 1)
            pygame.draw.line(surf, config.COL_TEXT_DIM, (ax + 5, ay + 3), (ax + 8, ay), 1)
            delta = row["after"] - row["before"]
            col_a = (config.COL_DOWN if delta < -1 else
                     config.COL_UP if delta > 1 else config.COL_TEXT)
            widgets.draw_text(surf, f"{row['after']:+,.0f}", (ax + 14, y),
                              fonts.tiny(bold=True), col_a)
        y += ROW_H
    return y - rect.y
