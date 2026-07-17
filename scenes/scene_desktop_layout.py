"""
scene_desktop_layout.py — DesktopLayoutMixin : persistance de l'ESPACE DE
TRAVAIL du bureau (fenêtres ouvertes, positions, épinglage, layout par
défaut d'une nouvelle partie).

Extrait VERBATIM de scenes/scene_desktop.py (aucun changement de logique) :
même principe que les autres mixins du bureau (`scene_desktop_widgets.py`,
`scene_desktop_menus.py`) — les méthodes vivent sur DesktopScene via
héritage et partagent ses attributs (self.wm, self.app…). Les constantes
communes viennent de `scene_desktop_common.py` (jamais du cœur, pour éviter
tout import circulaire).
"""
import pygame

from core import config
from scenes.scene_desktop_common import _L, TASKBAR_H, TOPBAR_H, TRACK_APP


class DesktopLayoutMixin:
    # ------------------------------------------- espace de travail (layout)
    def _sync_layout_flag(self):
        """Tient `player.flags["desktop_layout"]` à jour à CHAQUE frame (coût
        négligeable : quelques fenêtres tout au plus) — pour qu'une
        sauvegarde, à quelque moment qu'elle survienne (auto ou manuelle,
        cf. core/autosave_settings.py), capture toujours la disposition
        COURANTE plutôt qu'un instantané figé à un point d'appel précis."""
        self.app.gs.player.flags["desktop_layout"] = self._snapshot_layout()

    def _snapshot_layout(self):
        layout = []
        for w in self.wm.windows:
            entry = {"rect": [w.rect.x, w.rect.y, w.rect.w, w.rect.h],
                     "minimized": w.minimized, "pinned": w.pinned}
            if w.key == "scene:terminal":
                entry["kind"] = "terminal"
            elif w.key.startswith("scene:"):
                entry["kind"] = "scene"
                entry["name"] = w.key[len("scene:"):]
                entry["kwargs"] = dict(getattr(w.app_obj, "_kwargs", None) or {})
            else:
                entry["kind"] = "app"
                entry["key"] = w.key
            layout.append(entry)
        return layout

    def _restore_layout(self):
        """Rouvre les fenêtres mémorisées dans `player.flags["desktop_layout"]`
        (tenu à jour en continu, cf. `_sync_layout_flag`) à leur position/
        taille/état d'origine — appelé une seule fois, à la création de
        l'instance TERMINAL persistante (cf. on_enter) : la disposition de
        la DERNIÈRE session (nouvelle partie, reprise depuis le menu…).
        Si AUCUNE disposition n'a jamais été enregistrée (tout premier
        atterrissage sur le bureau de cette carrière — pas juste de cette
        App() : la clé `flags["desktop_seeded"]` distingue « jamais vu » de
        « vu mais tout fermé »), ouvre une disposition de départ adaptée à la
        voie choisie plutôt qu'un bureau totalement vide — moins de clics
        pour un joueur qui découvre le jeu."""
        layout = self.app.gs.player.flags.get("desktop_layout")
        if layout:
            self._apply_layout(layout)
        elif not self.app.gs.player.flags.get("desktop_seeded"):
            self._seed_default_layout()
        self.app.gs.player.flags["desktop_seeded"] = True

    # Marge réservée à gauche pour la grille d'icônes du bureau (jusqu'à ~4
    # colonnes à 94px, cf. ICON_W/ICON_GAP dans scene_desktop_common.py) — la
    # disposition de départ ne doit JAMAIS recouvrir les icônes, sous peine de
    # les rendre injoignables au tout premier lancement.
    _SEED_ICON_MARGIN = 420

    def _seed_default_layout(self):
        """Ouvre 2-3 fenêtres pertinentes déjà bien rangées (Marché à gauche,
        Portefeuille/app de la voie à droite), entièrement dans la moitié
        DROITE du bureau pour ne jamais recouvrir la grille d'icônes — au
        lieu d'un bureau vide, seulement au tout premier atterrissage (cf.
        `_restore_layout`)."""
        area = self.wm.work_area
        free_x = area.x + self._SEED_ICON_MARGIN
        win = pygame.Rect(free_x, area.y + 12, area.right - free_x - 12, area.h - 24)
        if win.w < 300:
            return   # écran trop étroit pour une disposition à 2 colonnes : rien ne s'ouvre
        left = pygame.Rect(win.x, win.y, win.w // 2 - 6, win.h)
        right_x = left.right + 12
        right_w = win.right - right_x
        track = getattr(self.app.gs.player, "track", "General")
        info = TRACK_APP.get(track)
        track_scene = info[0] if info else None
        if track_scene:
            top = pygame.Rect(right_x, win.y, right_w, win.h // 2 - 6)
            bottom = pygame.Rect(right_x, top.bottom + 12, right_w, win.h - top.h - 12)
            w = self._open_scene_window("markethub")
            if w:
                w.rect = left
            w = self._open_scene_window("book")
            if w:
                w.rect = top
            w = self._open_scene_window(track_scene)
            if w:
                w.rect = bottom
        else:
            right = pygame.Rect(right_x, win.y, right_w, win.h)
            w = self._open_scene_window("markethub")
            if w:
                w.rect = left
            w = self._open_scene_window("book")
            if w:
                w.rect = right

    def _save_pinned_layout(self):
        """« Enregistrer ma disposition » (menu contextuel) : fige un
        instantané SÉPARÉ de la disposition courante (`desktop_layout_pinned`,
        distinct de `desktop_layout` qui change à chaque frame) — pour y
        revenir plus tard d'un clic sans dépendre de ce qui était ouvert à la
        toute dernière sauvegarde."""
        self.app.gs.player.flags["desktop_layout_pinned"] = self._snapshot_layout()
        self.app.notify(_L("Disposition de fenêtres enregistrée.",
                           "Window layout saved."), "good")

    def _restore_pinned_layout(self):
        """« Restaurer ma disposition » (menu contextuel) : rouvre
        l'instantané figé par `_save_pinned_layout`, à tout moment de la
        partie (pas seulement au lancement, contrairement à `_restore_layout`)."""
        layout = self.app.gs.player.flags.get("desktop_layout_pinned")
        if not layout:
            self.app.notify(_L("Aucune disposition enregistrée pour l'instant.",
                               "No saved layout yet."), "warn")
            return
        self._apply_layout(layout)

    def _apply_layout(self, layout):
        """Rouvre chaque fenêtre décrite par `layout` (liste de dicts, cf.
        `_snapshot_layout`) à sa position/taille/état d'origine. Une entrée
        dont la scène/l'app n'existe plus (retirée depuis) est simplement
        ignorée, jamais une erreur bloquante."""
        if not layout:
            return
        term_win = next((w for w in self.wm.windows if w.key == "scene:terminal"), None)
        for entry in layout:
            kind = entry.get("kind")
            w = None
            try:
                if kind == "terminal":
                    w = term_win
                elif kind == "scene":
                    w = self._open_scene_window(entry.get("name", ""), **entry.get("kwargs", {}))
                elif kind == "app":
                    w = self._launch(entry.get("key", ""))
            except Exception:
                w = None
            if w is None:
                continue
            rect = entry.get("rect")
            if rect and len(rect) == 4:
                # borne le rect restauré (il vient TEL QUEL du JSON de
                # sauvegarde) : une valeur dégénérée/hors écran (fichier
                # édité à la main, future résolution différente…) rendrait la
                # fenêtre invisible ou ferait planter le rendu (smoothscale
                # sur taille négative) à CHAQUE frame — sauvegarde briquée.
                min_w, min_h = getattr(w.app_obj, "min_size", (300, 200))
                r = pygame.Rect(*rect)
                r.w = max(min_w, min(r.w, config.SCREEN_WIDTH))
                r.h = max(min_h, min(r.h, config.SCREEN_HEIGHT - TOPBAR_H - TASKBAR_H))
                r.x = max(0, min(r.x, config.SCREEN_WIDTH - 60))
                r.y = max(TOPBAR_H, min(r.y, config.SCREEN_HEIGHT - TASKBAR_H - 40))
                w.rect = r
            w.minimized = bool(entry.get("minimized", False))
            w.pinned = bool(entry.get("pinned", False))
