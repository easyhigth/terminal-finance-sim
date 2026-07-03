"""
scene_terminal_windows.py — TerminalWindowsMixin : fenêtres de données
déplaçables (overlay) du terminal (`self.datawins`) — ouverture (tableaux,
fiches société, graphes, accès rapide favoris) et persistance dans la save
(`_sync_workspace`/`_restore_workspace`). Extrait de scene_terminal.py
(découpage en mixins, même principe que scene_terminal_market/_trading/
_career/_time/_render).
"""
from core import config
from core import news as news_mod
from core.i18n import get_lang


def _L(fr, en):
    return en if get_lang() == "en" else fr


class TerminalWindowsMixin:

    def _datawin_row_click(self, w, idx):
        """Si la 1ʳᵉ cellule de la ligne est un ticker connu, ouvre sa fiche.
        Cas particulier : fenêtre d'actualités (cf. _open_news_window) — un
        clic navigue vers la scène NEWS avec une recherche pré-remplie sur
        cette actu précise, pour la retrouver dans le fil complet."""
        entries = getattr(w, "news_entries", None)
        if entries is not None:
            if idx < len(entries):
                self.app.scenes.go("news", return_to="terminal", search=entries[idx]["text"][:60])
            return
        if idx >= len(w.rows):
            return
        cell = w.rows[idx][0]
        text = cell[0] if isinstance(cell, tuple) else cell
        ticker = str(text).replace("↑", "").replace("↓", "").strip().split()[0:1]
        if ticker and self.market.price_of(ticker[0].upper()) is not None:
            self._open_company_popup(ticker[0].upper())

    def _open_window(self, title, columns, rows, accent=config.COL_CYAN):
        """Ouvre une fenêtre de données déplaçable (en cascade). Retourne la
        fenêtre créée (pour que l'appelant puisse y attacher des métadonnées,
        ex. les entrées d'actualité sous-jacentes pour le clic-pour-naviguer)."""
        from ui.datawindow import DataWindow
        offset = 16 * (len(self.datawins) % 6)
        pos = (config.MARGIN + 30 + offset, 90 + offset)
        w = DataWindow(title, columns, rows, pos=pos, accent=accent)
        self.datawins.append(w)
        if len(self.datawins) > 5:
            self.datawins.pop(0)
        return w

    def _open_news_window(self, region):
        """Détaille les news du jour à un emplacement de la carte (clic marqueur)."""
        p = self.app.gs.player
        items = [e for e in news_mod.for_day(p, p.day) if e["region"] == region]
        kcol = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_CYAN}
        rows = []
        for e in items:
            cat = news_mod.category_label(e["cat"])
            rows.append(((cat, kcol.get(e["kind"], config.COL_TEXT)), e["text"]))
        if not rows:
            rows = [("—", _L("Aucune actualité détaillée.", "No detailed news."))]
        loc = region or _L("Mondial", "Global")
        w = self._open_window(_L(f"NEWS — {loc} (jour {p.day})", f"NEWS — {loc} (day {p.day})"),
                              [(_L("Type", "Type"), 110), (_L("Actualité", "Headline"), 360)],
                              rows, accent=config.COL_PRESTIGE)
        w.news_entries = items  # clic sur une ligne → navigue vers NEWS (cf. _datawin_row_click)

    def _open_company_popup(self, ticker):
        """Ouvre la fiche flottante d'une société (en cascade), sans changer de scène."""
        from ui.popups import CompanyPopup
        if not ticker or not self.market or self.market.metrics(ticker.upper()) is None:
            return
        offset = 16 * (len(self.datawins) % 6)
        pos = (config.MARGIN + 30 + offset, 90 + offset)
        self.datawins.append(CompanyPopup(ticker, self.market, pos=pos))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _open_index_chart(self, name):
        """Ouvre l'historique d'un indice (clic souris ou Entrée au clavier sur
        le bloc INDICES)."""
        from ui.datawindow import DataWindow
        self.datawins.append(DataWindow(
            f"{name} — historique", [], [],
            pos=(config.MARGIN + 40, 100),
            accent=config.COL_AMBER,
            chart=list(self.market.index_history(name)),
            resizable=True, min_size=(320, 220)))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _open_quick_access(self):
        """Ouvre le gestionnaire « accès rapide » des favoris (watchlist)."""
        from ui.popups import QuickAccessWindow
        offset = 16 * (len(self.datawins) % 6)
        pos = (config.MARGIN + 30 + offset, 90 + offset)
        p = self.app.gs.player
        self.datawins.append(QuickAccessWindow(p, self.market, self._open_company_popup, pos=pos))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _open_chart_popup(self, ticker, kind="line"):
        """Ouvre un graphe flottant agrandi (en cascade) pour un ticker donné."""
        from ui.popups import ChartPopup
        offset = 16 * (len(self.datawins) % 6)
        pos = (config.MARGIN + 30 + offset, 90 + offset)
        self.datawins.append(ChartPopup(f"GRAPHE — {ticker.upper()}", market=self.market,
                                        ticker=ticker, kind=kind, pos=pos))
        if len(self.datawins) > 5:
            self.datawins.pop(0)

    def _sync_workspace(self):
        """Reflète les fenêtres flottantes persistables (fiches société, graphes)
        dans la sauvegarde, pour les retrouver à la reprise de la partie. Les
        fenêtres génériques (tableaux figés type TOP/COMPARE) et l'accès rapide
        (callback non sérialisable) sont volontairement exclus."""
        from ui.popups import ChartPopup, CompanyPopup
        entries = []
        for w in self.datawins:
            if getattr(w, "closed", False):
                continue
            if isinstance(w, CompanyPopup):
                entries.append({"cls": "company", "ticker": w.ticker,
                                "pos": [w.rect.x, w.rect.y]})
            elif isinstance(w, ChartPopup) and w.render_fn is None and w.ticker:
                entries.append({"cls": "chart", "ticker": w.ticker, "kind": w.kind,
                                "pos": [w.rect.x, w.rect.y]})
        self.app.gs.player.workspace = entries

    def _restore_workspace(self):
        """Reconstruit les fenêtres flottantes sauvegardées (reprise de partie),
        à l'unique premier on_enter de la scène (cf. garde hasattr appelante)."""
        from ui.popups import ChartPopup, CompanyPopup
        p = self.app.gs.player
        for entry in getattr(p, "workspace", []) or []:
            pos = tuple(entry.get("pos") or (160, 120))
            ticker = entry.get("ticker")
            if not ticker or self.market.metrics(ticker.upper()) is None:
                continue
            if entry.get("cls") == "company":
                self.datawins.append(CompanyPopup(ticker, self.market, pos=pos))
            elif entry.get("cls") == "chart":
                kind = entry.get("kind", "line")
                self.datawins.append(ChartPopup(f"GRAPHE — {ticker.upper()}", market=self.market,
                                                ticker=ticker, kind=kind, pos=pos))
