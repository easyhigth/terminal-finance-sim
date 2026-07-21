"""
scene_compare.py — Comparateur interactif d'actions ou d'ETF.
Remplace l'ancienne fenêtre figée ouverte par COMPARE : on peut ajouter ou
retirer des tickers à la volée et cliquer un ticker pour ouvrir sa fiche
société (les ETF n'ont pas de fiche dédiée, on renvoie vers le hub ETF).
"""
import pygame

from core import config
from core import etfs as etfs_mod
from core import screener as screener_mod
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets

MAX_TICKERS = 6


def _L(fr, en):
    return en if get_lang() == "en" else fr


class CompareScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        seen, terms = set(), []
        for t in (kwargs.get("tickers") or []):
            t = t.upper()
            if t not in seen:
                seen.add(t)
                terms.append(t)
        self.terms = terms[:MAX_TICKERS]
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.add_box = widgets.SearchBox((220, config.SCREEN_HEIGHT - 66, 260, 38),
                                         _L("AJOUTER UN TICKER…", "ADD A TICKER…"))
        self.chip_rects = []
        self.open_rects = []
        self.mode = None
        self.entities = []
        self.fields = []
        self.error = None
        self._recompute()

    def _market(self):
        return self.app.market

    def _recompute(self):
        m = self._market()
        self.mode = None
        self.entities = []
        self.fields = []
        self.error = None
        if len(self.terms) < 2 or m is None:
            return
        if all(etfs_mod.exists(t) for t in self.terms):
            self.mode = "etf"
            quotes = screener_mod.compare_etfs(m, self.terms)
            if len(quotes) < 2:
                self.error = _L("Au moins un ETF est introuvable.",
                                 "At least one ETF has no match.")
                return
            self.entities = [(q["id"], q) for q in quotes]
            self.fields = [
                ("NAV", "price", lambda v: f"{v:.2f}"),
                (_L("Catégorie", "Category"), "category_label", lambda v: str(v)),
                (_L("Var 1 an", "1y change"), "change_1y", lambda v: f"{v:+.1f}%"),
                (_L("Rendement", "Yield"), "yield", lambda v: f"{v*100:.1f}%"),
                (_L("Frais", "Expense"), "expense", lambda v: f"{v*100:.2f}%"),
                (_L("Bêta monde", "World beta"), "beta", lambda v: f"{v:+.2f}"),
                (_L("Risque", "Risk"), "risk", lambda v: "●" * v),
            ]
            return
        self.mode = "stock"
        tickers = [m.resolve(t) or t for t in self.terms]
        metrics = screener_mod.compare_stocks(m, tickers)
        if len(metrics) < 2:
            self.error = _L("Au moins un terme est introuvable.",
                             "At least one term has no match.")
            return
        for mt in metrics:
            hist = m.history_of(mt["ticker"], 31)
            for label, lookback in (("var_1j", 1), ("var_7j", 7), ("var_30j", 30)):
                if len(hist) > lookback and hist[-1 - lookback]:
                    mt[label] = (hist[-1] / hist[-1 - lookback] - 1) * 100
                else:
                    mt[label] = None
        self.entities = [(mt["ticker"], mt) for mt in metrics]
        self.fields = [
            (_L("Prix", "Price"), "price", lambda v: f"{v:.2f}"),
            (_L("Capi(M)", "Mktcap(M)"), "mktcap", lambda v: f"{v:,.0f}"),
            ("P/E", "pe", lambda v: f"{v:.1f}"),
            ("EV/EBITDA", "ev_ebitda", lambda v: f"{v:.1f}"),
            (_L("Marge nette", "Net margin"), "net_margin", lambda v: f"{v*100:.0f}%"),
            (_L("Bêta", "Beta"), "beta", lambda v: f"{v:.2f}"),
            (_L("Var 1j", "1d chg"), "var_1j", lambda v: f"{v:+.1f}%"),
            (_L("Var 7j", "7d chg"), "var_7j", lambda v: f"{v:+.1f}%"),
            (_L("Var 30j", "30d chg"), "var_30j", lambda v: f"{v:+.1f}%"),
        ]

    def _add_term(self, raw):
        raw = (raw or "").strip().upper()
        if not raw or len(self.terms) >= MAX_TICKERS or raw in self.terms:
            return
        m = self._market()
        ok = etfs_mod.exists(raw) or (m and m.resolve(raw))
        if not ok:
            self.app.notify(_L(f"{raw} introuvable.", f"{raw} not found."), "warn")
            return
        self.terms.append(raw)
        self._recompute()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.add_box.handle_clear_click(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._add_term(self.add_box.text)
            self.add_box.text = ""
            return
        if self.add_box.handle_typing(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, idx in self.chip_rects:
                if rect.collidepoint(event.pos):
                    del self.terms[idx]
                    self._recompute()
                    return
            for rect, tk, kind in self.open_rects:
                if rect.collidepoint(event.pos):
                    if kind == "stock":
                        self.app.scenes.go("company", ticker=tk, return_to="compare",
                                           return_kwargs={"tickers": list(self.terms)})
                    else:
                        self.app.scenes.go("etfs", return_to="compare")
                    return

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.add_box.update(dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("COMPARATEUR", "COMPARE"), (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L(
            "Cliquez un ticker pour ouvrir sa fiche · ✕ pour retirer · "
            "jusqu'à 6 actifs (actions OU ETF, pas de mélange)",
            "Click a ticker to open its profile · ✕ to remove · "
            "up to 6 assets (stocks OR ETFs, no mixing)"),
            (40, 70), fonts.small(), config.COL_TEXT_DIM)

        # chips des tickers sélectionnés
        self.chip_rects = []
        x, y = 40, 104
        for i, tk in enumerate(self.terms):
            w = fonts.small(bold=True).size(tk)[0] + 44
            rect = pygame.Rect(x, y, w, 32)
            pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=6)
            pygame.draw.rect(surf, config.COL_CYAN, rect, 1, border_radius=6)
            widgets.draw_text(surf, tk, (rect.x + 10, rect.y + 7),
                              fonts.small(bold=True), config.COL_WHITE)
            close_rect = pygame.Rect(rect.right - 26, rect.y, 26, rect.h)
            widgets.draw_text(surf, "✕", close_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")
            self.chip_rects.append((close_rect, i))
            x += w + 10

        body = pygame.Rect(40, 154, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - 154)
        self.open_rects = []
        if len(self.terms) < 2:
            widgets.draw_text(surf, _L("Ajoutez au moins 2 tickers à comparer.",
                                       "Add at least 2 tickers to compare."),
                              (body.x, body.y), fonts.small(), config.COL_TEXT_DIM)
        elif self.error:
            widgets.draw_error_panel(surf, self.error, top=body.y)
        else:
            inner = widgets.draw_panel(
                surf, body, "COMPARER " + " / ".join(tk for tk, _ in self.entities),
                config.COL_CYAN)
            n = max(1, len(self.entities))
            label_w = 140
            colw = (inner.w - label_w) // n
            for k, (tk, _e) in enumerate(self.entities):
                cx = inner.x + label_w + k * colw
                rect = pygame.Rect(cx, inner.y, colw - 8, 22)
                widgets.draw_text(surf, tk, (cx + (colw - 8) // 2, inner.y + 11),
                                  fonts.small(bold=True), config.COL_CYAN, align="center")
                self.open_rects.append((rect, tk, self.mode))
            yy = inner.y + 28
            row_h = max(18, min(26, (inner.h - 28) // max(1, len(self.fields))))
            for lbl, key, fmt in self.fields:
                widgets.draw_text(surf, lbl, (inner.x, yy), fonts.tiny(), config.COL_TEXT_DIM)
                for k, (tk, e) in enumerate(self.entities):
                    cx = inner.x + label_w + k * colw
                    v = e.get(key)
                    txt = fmt(v) if v is not None else "n.m."
                    col = config.COL_TEXT
                    if (key.startswith("var_") or key == "change_1y") and v is not None:
                        col = config.COL_UP if v >= 0 else config.COL_DOWN
                    widgets.draw_text(surf, txt, (cx + colw - 12, yy),
                                      fonts.small(bold=True), col, align="right")
                yy += row_h

        self.add_box.draw(surf)
        self.back_btn.draw(surf)
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.SCREEN_HEIGHT - 70),
                             [(_L("ENTRÉE", "ENTER"), _L("ajouter", "add")), ("ESC", _L("retour", "back"))])
