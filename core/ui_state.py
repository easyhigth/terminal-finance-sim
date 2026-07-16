"""
ui_state.py — Persistance de l'état UI du bureau.

Sauvegarde/restaure séparément de `GameState` (qui stocke la progression
métier) : disposition des fenêtres, classeur, watchlist, onglets.
Fichier : `ui_state.json` sous `SAVE_DIR`, lié au slot de sauvegarde par
son nom (ex. `ui_state_slot1.json`).

L'état UI n'est PAS critique : si le fichier est absent/corrompu, la
partie se charge normalement avec un bureau vierge.
"""
import json
import os

from core import config, crashlog
from core.workbook import Workbook

_PATH = lambda slot: os.path.join(config.SAVE_DIR, f"ui_state_{slot}.json")


def _empty():
    return {"version": 1}


def save(slot, app):
    """Sauvegarde l'état UI courant pour le slot donné."""
    data = {"version": 1}
    player = getattr(app.gs, "player", None)
    # disposition des fenêtres du bureau : snapshot riche (kind/name/kwargs)
    # si on est sur le bureau, sinon dernière disposition mémorisée dans GS.
    if app.scenes.current_name == "desktop":
        data["windows"] = getattr(app.scenes.current, "_snapshot_layout", lambda: None)()
    if data.get("windows") is None:
        if player is not None:
            data["windows"] = player.flags.get("desktop_layout")
    # onglets
    pages = getattr(app, "pages", None)
    if pages is not None:
        data["pages"] = {
            "active": pages.active,
            "tabs": [
                {"scene": t.scene_name, "kwargs": dict(t.kwargs)}
                for t in pages.pages
            ],
        }
    # classeur
    if getattr(app, "workbook", None) is not None:
        data["workbook"] = app.workbook.to_dict()
    # watchlist
    if player is not None:
        data["watchlist"] = list(getattr(player, "watchlist", []))

    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH(slot), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        crashlog.swallowed("core.ui_state")


def load(slot, app):
    """Restaure l'état UI pour le slot donné. Retourne le dict chargé ou None."""
    path = _PATH(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    # watchlist
    player = getattr(app.gs, "player", None)
    if player is not None and "watchlist" in data:
        try:
            player.watchlist = list(data["watchlist"])[:10]
        except Exception:
            crashlog.swallowed("core.ui_state")  # onglets : recréer les pages sauvegardées si PageManager existe
    pages = getattr(app, "pages", None)
    if pages is not None and "pages" in data:
        try:
            pd = data["pages"]
            tabs = pd.get("tabs", [])
            if tabs:
                # on garde la page initiale si elle correspond à la première
                # page sauvegardée ; sinon on recrée proprement.
                new_pages = []
                for td in tabs:
                    name = td.get("scene")
                    if not name:
                        continue
                    is_first = (not new_pages and pages.pages
                                and name == pages.pages[0].scene_name)
                    if is_first:
                        new_pages.append(pages.pages[0])
                        continue
                    kw = td.get("kwargs", {})
                    new_pages.append(pages._create_page(name, kw))
                if new_pages:
                    pages.pages = new_pages
                    # Après un chargement on atterrit toujours sur le bureau.
                    desktop_idx = next(
                        (i for i, p in enumerate(pages.pages)
                         if p.scene_name == "desktop"), 0)
                    pages.active = desktop_idx
                    pages._ensure_manager()
        except Exception:
            crashlog.swallowed("core.ui_state")  # classeur : restaurer si un workbook existe déjà
    if getattr(app, "workbook", None) is not None and "workbook" in data:
        try:
            app.workbook = Workbook.from_dict(
                data["workbook"], app.workbook.n_rows, app.workbook.n_cols)
        except Exception:
            crashlog.swallowed("core.ui_state")  # fenêtres : stocké dans l'app pour application dès que le bureau est prêt
    app._pending_ui_layout = data.get("windows")
    return data


def delete(slot):
    """Supprime l'état UI d'un slot."""
    try:
        os.remove(_PATH(slot))
    except FileNotFoundError:
        pass
    except Exception:
        crashlog.swallowed("core.ui_state")
