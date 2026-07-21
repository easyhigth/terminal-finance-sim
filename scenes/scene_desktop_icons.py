"""
scene_desktop_icons.py — DesktopIconsMixin : la GRILLE D'ICÔNES du bureau
(visibilité par déblocage, sections repliables, ordre personnalisé par
glisser-déposer, détection des nouveautés, dessin des icônes vectorielles).

Extrait VERBATIM de scenes/scene_desktop.py (aucun changement de logique) :
même principe que les autres mixins du bureau — méthodes hébergées par
DesktopScene via héritage, constantes partagées via
`scene_desktop_common.py`. Piège toujours actif : les grilles se remplissent
en ordre LIGNE (`row, col = divmod(i, cols)`), cf. CLAUDE.md.
"""
import pygame

from core import config
from core import unlocks as unlocks_mod
from scenes.scene_desktop_common import (
    _ICON_SHORTCUT,
    _L,
    APPS,
    ICON_CATEGORY_ORDER,
    ICON_FEATURE,
    ICON_GAP,
    ICON_H,
    ICON_W,
    QUICK_APPS,
    TASKBAR_H,
    TOPBAR_H,
    TRACK_APP,
    app_label,
    icon_category,
    section_label,
)
from ui import desktop_icons, fonts, keynav, style, widgets

_ICON_DRAG_THRESHOLD = 6   # px : sous ce seuil un glisser d'icône reste un simple clic


class DesktopIconsMixin:
    def _icon_visible(self, key):
        """Une icône soumise au déblocage progressif (ICON_FEATURE) n'apparaît
        que si la fonctionnalité est ouverte au grade courant. « Décide »
        (qdecide) n'apparaît que quand un dilemme attend réellement une
        décision — sinon l'icône ouvrait un écran vide, redondant avec le
        widget « À FAIRE »."""
        if key == "qdecide":
            return bool(self.app.gs.player.pending_dilemmas)
        feat = ICON_FEATURE.get(key)
        return feat is None or unlocks_mod.unlocked(self.app.gs.player, feat)

    # apps NATIVES enregistrées dans APPS uniquement pour que `_launch`/
    # `_open_scene_window` trouvent leur classe factory (popups forcés par le
    # jeu ou navigation interne) — PAS des icônes de bureau à part entière :
    # "dilemma"/"review" restent conditionnées à "qdecide" (widget À FAIRE,
    # cf. commentaire de `_icon_visible`) ou déclenchées par le jeu, jamais un
    # clic direct ; "evaluation" ne doit JAMAIS être un accès direct, sinon un
    # joueur pourrait lancer un examen de promotion sans remplir les critères
    # vérifiés par `scene_examcert.py::_go_exam` (réputation, missions, deals)
    # avant de router vers "evaluation" ; "deals" a déjà son icône via
    # QUICK_APPS ("qdeals") — une seconde ferait doublon ; "company" n'a
    # jamais eu d'icône (toujours ouverte avec un ticker précis depuis un
    # contexte — Recherche, Portefeuille, notifications…) ; "shop" a déjà son
    # icône via QUICK_APPS ("qshop") — une seconde ferait doublon.
    # "analytics" n'a jamais eu d'icône non plus (accessible via PLUS et les
    # boutons ANALYSE (PA) de Trading/Portefeuille) ; "explorer" a déjà son
    # icône via QUICK_APPS ("qexplorer") — une seconde ferait doublon.
    _FACTORY_ONLY_APPS = {"dilemma", "review", "evaluation", "deals", "company",
                          "shop", "analytics", "explorer"}

    def _icon_list(self):
        """Liste (clé, libellé, icon_kind, couleur accent) des icônes du
        bureau : apps natives + Terminal (toujours) + app de la voie (une fois
        choisie) — dans une grille, pas une colonne, pour rester lisible même
        si la liste s'allonge. Les icônes verrouillées (ICON_FEATURE) sont
        masquées jusqu'au grade requis."""
        items = [(k, lbl, kind, config.COL_AMBER) for k, lbl, kind, _cls in APPS
                 if k not in self._FACTORY_ONLY_APPS and self._icon_visible(k)]
        items.append(("terminal", "Terminal", "terminal", config.COL_CYAN))
        track = getattr(self.app.gs.player, "track", "General")
        info = TRACK_APP.get(track)
        if info:
            scene_name, label, kind = info
            # pas de doublon : si la scène de la voie a déjà son icône d'accès
            # rapide (ex. Portfolio→book/« Portef. », Advisory→mandates), on ne
            # l'affiche pas une seconde fois en icône de voie.
            quick_scenes = {scene for _k, _l, _kind2, scene in QUICK_APPS}
            if scene_name not in quick_scenes:
                items.append(("track", label, kind, config.COL_PRESTIGE))
        # anciens boutons du rail latéral du terminal : icônes du bureau
        items += [(k, lbl, kind, config.COL_CYAN) for k, lbl, kind, _scene in QUICK_APPS
                  if self._icon_visible(k)]
        return self._apply_icon_order(items)

    def _grouped_icon_sections(self):
        """Regroupe `_icon_list()` en sections repliables (façon dossiers),
        selon `scene_desktop_common.ICON_CATEGORY` — une icône nouvellement
        débloquée atterrit automatiquement dans la bonne section (catégorie
        fixe par clé, pas de tri à faire). Renvoie [(libellé, [items])],
        dans l'ordre `ICON_CATEGORY_ORDER`, sans section vide."""
        buckets = {}
        for item in self._icon_list():
            key = item[0]
            buckets.setdefault(icon_category(key), []).append(item)
        return [(label, buckets[label]) for label in ICON_CATEGORY_ORDER
                if buckets.get(label)]

    def _collapsed_sections(self):
        return self.app.gs.player.flags.get("desktop_collapsed_sections", [])

    def _is_section_collapsed(self, label):
        return label in self._collapsed_sections()

    def _toggle_section(self, label):
        """Replie/déplie une section — persisté dans player.flags (survit à
        une sauvegarde), comme la difficulté ou l'ordre des icônes."""
        p = self.app.gs.player
        collapsed = list(p.flags.get("desktop_collapsed_sections", []))
        if label in collapsed:
            collapsed.remove(label)
        else:
            collapsed.append(label)
        p.flags["desktop_collapsed_sections"] = collapsed

    def _apply_icon_order(self, items):
        """Réordonne `items` selon `player.flags["desktop_icon_order"]`, une
        disposition libre choisie par le joueur (glisser-déposer, cf.
        `_reorder_icon`). Les clés jamais vues (nouvelle icône débloquée,
        1re partie) gardent l'ordre par défaut et se glissent à la fin — pas
        de trou ni de crash si le joueur n'a jamais réorganisé son bureau."""
        order = self.app.gs.player.flags.get("desktop_icon_order")
        if not order:
            return items
        rank = {k: i for i, k in enumerate(order)}
        ranked = sorted(enumerate(items),
                        key=lambda pair: rank.get(pair[1][0], len(order) + pair[0]))
        return [it for _i, it in ranked]

    def _reorder_icon(self, key, pos):
        """Dépose l'icône `key` près de `pos` (position souris au relâcher) :
        retrouve la case la plus proche parmi les icônes actuellement
        affichées (`self._icon_rects`, peuplé par le dernier dessin) et
        insère `key` à cet emplacement. Persisté dans `player.flags` (comme
        la difficulté ou les apps déjà vues) — survit à une sauvegarde."""
        order = list(self._icon_rects.keys())
        if key not in order:
            return
        order.remove(key)
        target, best_d = None, None
        for k, (r, _kind, _label) in self._icon_rects.items():
            if k == key:
                continue
            d = (r.centerx - pos[0]) ** 2 + (r.centery - pos[1]) ** 2
            if best_d is None or d < best_d:
                best_d, target = d, k
        insert_at = order.index(target) if target in order else len(order)
        order.insert(insert_at, key)
        self.app.gs.player.flags["desktop_icon_order"] = order

    def _check_new_icons(self):
        """Toast « nouvelle app installée » quand une icône verrouillée vient
        d'apparaître (promotion) — l'état vu est persisté dans la sauvegarde
        (player.flags) pour ne notifier qu'une fois par partie."""
        p = self.app.gs.player
        items = self._icon_list()
        keys = [k for k, _lbl, _kind, _acc in items]
        seen = p.flags.get("desktop_seen_apps")
        if seen is None:
            p.flags["desktop_seen_apps"] = keys
            return
        # qdecide apparaît/disparaît au gré des dilemmes : ce n'est pas un
        # déblocage, pas de toast « nouvelle app » pour elle.
        new = [(k, lbl) for k, lbl, _kind, _acc in items
               if k not in seen and k != "qdecide"]
        for k, label in new:
            cat = icon_category(k)
            self.app.notify(_L(f"Nouvelle app dans « {section_label(cat)} » : {app_label(label)}",
                               f"New app in “{section_label(cat)}”: {app_label(label)}"), "prestige")
        if new:
            p.flags["desktop_seen_apps"] = keys

    def _dragging_icon(self):
        """True si un glisser d'icône a dépassé le seuil de clic (donc en
        train de réorganiser, pas juste un clic qui n'a pas encore bougé)."""
        d = self._icon_drag
        if d is None:
            return None
        sx, sy = d["start"]
        px, py = d["pos"]
        if (px - sx) ** 2 + (py - sy) ** 2 < _ICON_DRAG_THRESHOLD ** 2:
            return None
        return d["key"]

    _SECTION_HEADER_H = 24
    _SECTION_GAP = 10
    _SECTION_ICON_COLS = 3   # icônes par colonne au sein d'une section
    _SECTION_COL_GAP = 20    # espace entre deux colonnes de sections

    @property
    def _section_col_w(self):
        return self._SECTION_ICON_COLS * (ICON_W + ICON_GAP) - ICON_GAP + 16

    def _section_height(self, n_items, collapsed):
        if collapsed:
            return self._SECTION_HEADER_H + self._SECTION_GAP
        n_rows = -(-n_items // self._SECTION_ICON_COLS)  # arrondi au-dessus
        return (self._SECTION_HEADER_H + n_rows * (ICON_H + ICON_GAP)
                + self._SECTION_GAP)

    def _draw_section_header(self, surf, label, x, y, w, n_items, collapsed):
        """En-tête de section repliable (façon dossier) : chevron + libellé +
        compte d'icônes quand repliée. Renvoie le Rect cliquable (stocké dans
        `self._section_header_rects` par l'appelant)."""
        r = pygame.Rect(x, y, w, self._SECTION_HEADER_H)
        hov = r.collidepoint(pygame.mouse.get_pos())
        if hov:
            pygame.draw.rect(surf, (*config.COL_PANEL, 90), r, border_radius=4)
        cx, cy = r.x + 12, r.centery
        # chevron vectoriel (▸ replié / ▾ déplié) — jamais un glyphe emoji.
        if collapsed:
            pts = [(cx - 3, cy - 5), (cx - 3, cy + 5), (cx + 4, cy)]
        else:
            pts = [(cx - 5, cy - 3), (cx + 5, cy - 3), (cx, cy + 4)]
        pygame.draw.polygon(surf, config.COL_AMBER if hov else config.COL_TEXT_DIM, pts)
        suffix = f" ({n_items})" if collapsed else ""
        widgets.draw_text(surf, widgets.fit_text(section_label(label).upper() + suffix,
                                                  fonts.tiny(bold=True), w - 28),
                          (r.x + 24, r.y + 5), fonts.tiny(bold=True),
                          config.COL_AMBER if hov else config.COL_TEXT_DIM)
        pygame.draw.line(surf, config.COL_BORDER, (r.x + 24, r.bottom - 2),
                         (r.right - 4, r.bottom - 2))
        return r

    def _draw_desktop_icons(self, surf):
        self._icon_rects = {}
        self._section_header_rects = {}
        mp = pygame.mouse.get_pos()
        dragging_key = self._dragging_icon()
        col_w = self._section_col_w
        y_top = TOPBAR_H + 8
        y_bottom = config.SCREEN_HEIGHT - TASKBAR_H - 8
        col_x, y = 16, y_top
        for label, section_items in self._grouped_icon_sections():
            collapsed = self._is_section_collapsed(label)
            need_h = self._section_height(len(section_items), collapsed)
            if y > y_top and y + need_h > y_bottom:
                # ne tient plus dans cette colonne : on passe à la suivante,
                # comme des dossiers qui débordent sur le bureau (flux « en
                # colonnes de journal ») plutôt que de dessiner hors écran.
                col_x += col_w + self._SECTION_COL_GAP
                y = y_top
            self._section_header_rects[label] = self._draw_section_header(
                surf, label, col_x, y, col_w, len(section_items), collapsed)
            y += self._SECTION_HEADER_H
            if collapsed:
                y += self._SECTION_GAP
                continue
            for i, (key, item_label, kind, accent) in enumerate(section_items):
                row, col = divmod(i, self._SECTION_ICON_COLS)
                x = col_x + col * (ICON_W + ICON_GAP)
                iy = y + row * (ICON_H + ICON_GAP)
                r = pygame.Rect(x, iy, ICON_W, ICON_H)
                self._draw_one_icon(surf, r, key, item_label, kind, accent,
                                    mp, dragging_key)
            n_rows = -(-len(section_items) // self._SECTION_ICON_COLS)
            y += n_rows * (ICON_H + ICON_GAP) + self._SECTION_GAP
        # dépôt en cours : liseré pointillé sur la case cible la plus proche
        # du curseur, pour prévisualiser où l'icône va atterrir.
        if dragging_key is not None:
            best_d, target_r = None, None
            for k, (r, _kind, _label) in self._icon_rects.items():
                if k == dragging_key:
                    continue
                d = (r.centerx - mp[0]) ** 2 + (r.centery - mp[1]) ** 2
                if best_d is None or d < best_d:
                    best_d, target_r = d, r
            if target_r is not None:
                pygame.draw.rect(surf, config.COL_AMBER, target_r, 2, border_radius=8)

    def _draw_one_icon(self, surf, r, key, label, kind, accent, mp, dragging_key):
        self._icon_rects[key] = (r, kind, label)
        hov_t = self._icon_hover_t.get(key, 0.0)
        hov = hov_t > 0.01
        if hov:
            halo = r.inflate(int(6 * hov_t), int(6 * hov_t))
            halo_col = (*config.COL_PANEL, int(120 * hov_t))
            pygame.draw.rect(surf, halo_col, halo, border_radius=10)
            pygame.draw.rect(surf, (*accent, int(160 * hov_t)), halo, 1, border_radius=10)
        keynav.draw_focus_ring(surf, r, key == self._icon_focus)
        ghost = dragging_key is not None and key == dragging_key
        # icône avec halo/scale au survol, sans smoothscale coûteux :
        # on décale juste l'icône de 1px vers le haut et on dessine un glow.
        if hov_t > 0.01:
            glow = int(4 * hov_t)
            pygame.draw.circle(surf, (*accent, int(60 * hov_t)),
                               (r.centerx, r.y + 28), 20 + glow)
            offset_y = -int(1.5 * hov_t)
        else:
            offset_y = 0
        desktop_icons.draw(surf, (r.centerx, r.y + 28 + offset_y), kind,
                           size=36, alpha=110 if ghost else 255)
        label_col = config.COL_TEXT_DIM if ghost else (
            style._lerp_color(config.COL_TEXT, accent, 0.3 * hov_t))
        widgets.draw_text(surf, widgets.fit_text(app_label(label), fonts.small(bold=True), ICON_W - 6),
                          (r.centerx, r.bottom - 18), fonts.small(bold=True),
                          label_col, align="center")
        # tooltip raccourci clavier (seulement si aucune fenêtre ne
        # recouvre l'icône — sinon le survol appartient à la fenêtre)
        sc_label = _ICON_SHORTCUT.get(key)
        if hov and sc_label and self.wm._topmost_at(mp) is None:
            widgets.draw_tooltip(surf, f"{app_label(label)} · {sc_label}", (r.x, r.bottom + 2))
