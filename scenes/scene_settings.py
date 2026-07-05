"""
scene_settings.py — Écran RÉGLAGES (paramètres globaux du jeu).

Regroupe au même endroit les préférences jusqu'ici éparpillées (langue,
animations) et en ajoute de nouvelles : mode d'affichage de la fenêtre
(fenêtré / plein écran / plein écran fenêtré), son (sourdine + volume) et
vitesse de jeu. Accessible depuis le menu principal et depuis le terminal
(bouton ⚙ à côté des raccourcis), ainsi que par la palette Ctrl+K.

Chaque préférence est persistée par son module dédié (core/display_settings,
core/audio, core/i18n, core/anim_settings) ; cette scène n'est qu'une façade
de pilotage. Lecture seule vis-à-vis de l'état de jeu : aucune partie n'est
requise pour ouvrir les réglages.
"""
import pygame

from core import (
    anim_settings,
    audio,
    autosave_settings,
    colorblind_settings,
    config,
    daily_checklist,
    display_settings,
    experience_mode,
)
from core.i18n import get_lang, set_lang
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.shortcutspanel import ShortcutsPanel


# Libellés bilingues locaux (le contenu fin du jeu reste FR, mais le chrome
# des réglages mérite l'anglais comme le reste du menu).
def _L(fr, en):
    return en if get_lang() == "en" else fr


class SettingsScene(Scene):
    pageable = False   # écran de configuration : pas d'onglet dédié

    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "menu")
        self.shortcuts_panel = None   # overlay raccourcis clavier (déplaçable)
        self._build()

    # --- construction des contrôles (rejouée à chaque changement de langue) ---
    def _build(self):
        self.rows = []          # [(label, [Button, ...])]
        self.back_btn = widgets.Button(
            config.back_button_rect(220),
            f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

        lang = get_lang()
        # AFFICHAGE — mode de fenêtre
        disp = [(m, display_settings.label(m, lang)) for m in display_settings.MODES]
        self.rows.append((_L("Affichage", "Display"),
                          self._seg([(("window", m), lbl,
                                      self.app.window_mode == m) for m, lbl in disp])))
        # RÉSOLUTION — presets 16:9 (nécessite un redémarrage de la fenêtre)
        cur_res = display_settings.get_resolution()
        res_opts = []
        for key, preset in config.RESOLUTION_PRESETS.items():
            lbl = preset["label"][1] if lang == "en" else preset["label"][0]
            res_opts.append(((("resolution", key), lbl, cur_res == key)))
        self.rows.append((_L("Résolution", "Resolution"),
                          self._seg(res_opts)))
        # SON — sourdine
        self.rows.append((_L("Son", "Sound"),
                          self._seg([(("mute", False), _L("Activé", "On"), not audio.is_muted()),
                                     (("mute", True), _L("Coupé", "Muted"), audio.is_muted())])))
        # SON — volume (− valeur +)
        self.rows.append((_L("Volume", "Volume"),
                          self._seg([(("vol", -1), "−", False),
                                     (("vol", 0), f"{int(round(audio.get_volume()*100))}%", True),
                                     (("vol", +1), "+", False)])))
        # LANGUE
        self.rows.append((_L("Langue", "Language"),
                          self._seg([(("lang", "fr"), "FR", lang == "fr"),
                                     (("lang", "en"), "EN", lang == "en")])))
        # ANIMATIONS
        self.rows.append((_L("Animations", "Animations"),
                          self._seg([(("anim", False), _L("Normales", "Normal"), not anim_settings.reduce_motion()),
                                     (("anim", True), _L("Réduites", "Reduced"), anim_settings.reduce_motion())])))
        # DALTONISME / CONTRASTE — remplace vert/rouge par bleu/orange sur les
        # paires hausse-baisse / favorable-défavorable (cf. core/colorblind_settings)
        self.rows.append((_L("Contraste", "Contrast"),
                          self._seg([(("colorblind", False), _L("Standard", "Standard"),
                                      not colorblind_settings.is_enabled()),
                                     (("colorblind", True), _L("Daltonien (bleu/orange)", "Colorblind (blue/orange)"),
                                      colorblind_settings.is_enabled())])))
        # SAUVEGARDE AUTOMATIQUE — cadence (0 = à chaque action, historique)
        cur_interval = autosave_settings.get_interval()
        self.rows.append((_L("Sauvegarde auto", "Autosave"),
                          self._seg([(("autosave", v), autosave_settings.preset_label(v, lang),
                                      cur_interval == v)
                                     for v, _label in autosave_settings.PRESETS])))
        # MODE DÉBUTANT/EXPERT — masque les pages financières avancées non
        # pertinentes pour la voie choisie (menu Démarrer + palette Ctrl+K)
        cur_mode = experience_mode.get_mode()
        self.rows.append((_L("Mode d'affichage des pages", "Page display mode"),
                          self._seg([(("xpmode", "beginner"), _L("Débutant (simplifié)", "Beginner (simplified)"),
                                      cur_mode == "beginner"),
                                     (("xpmode", "expert"), _L("Expert (tout afficher)", "Expert (show all)"),
                                      cur_mode == "expert")])))
        # CHECKLIST DE ROUTINE QUOTIDIENNE — pense-bête désactivable une fois
        # maîtrisée (widget « ROUTINE DU JOUR » du bureau)
        cur_checklist = daily_checklist.is_enabled(self.app.gs.player)
        self.rows.append((_L("Routine quotidienne", "Daily routine"),
                          self._seg([(("checklist", True), _L("Affichée", "Shown"), cur_checklist),
                                     (("checklist", False), _L("Masquée", "Hidden"), not cur_checklist)])))
        # VITESSE DE JEU (live ; l'horloge n'avance qu'au terminal)
        cur_speed = getattr(self.app.sim_clock, "speed", 1)
        self.rows.append((_L("Vitesse du jeu", "Game speed"),
                          self._seg([(("speed", s), f"×{s}", cur_speed == s) for s in (1, 2, 3)])))
        self._layout()
        # bouton dédié : ouvre le panneau des raccourcis clavier (déplacé ici
        # depuis la barre du terminal pour la désencombrer).
        ry = self.rows[-1][1][0].rect.bottom + 18
        self.shortcuts_btn = widgets.Button((360, ry, 320, 38),
                                            _L("⌨ Raccourcis clavier", "⌨ Keyboard shortcuts"),
                                            config.COL_CYAN)

    def _seg(self, options):
        """Construit une rangée de boutons-segments ; `options` = liste de
        (action, label, actif). Le bouton actif est mis en avant (cyan)."""
        btns = []
        for action, label, active in options:
            accent = config.COL_CYAN if active else config.COL_NEUTRAL
            b = widgets.Button((0, 0, 10, 10), label, accent)
            b.action = action
            b.active = active
            btns.append(b)
        return btns

    def _layout(self):
        """Pas de ligne ADAPTATIF : l'écran a gagné des réglages au fil des
        versions (sauvegarde auto, mode débutant/expert, routine quotidienne…)
        et un pas FIXE finissait par pousser les dernières lignes et le bouton
        « Raccourcis clavier » SOUS le bord de l'écran — réglages injoignables
        (bug V1.0). On répartit désormais la hauteur disponible (entre le
        titre et le pied de page, bouton raccourcis déduit) entre toutes les
        lignes, bornée à [40, 68] px pour rester lisible."""
        x0 = 360
        y0 = config.content_top() + 10
        shortcuts_reserve = 38 + 24          # bouton « Raccourcis » + respiration
        avail = config.footer_y() - 36 - y0 - shortcuts_reserve
        pitch = max(40, min(68, avail // max(1, len(self.rows))))
        btn_h = min(40, pitch - 6)
        y = y0
        for _label, btns in self.rows:
            x = x0
            for b in btns:
                # largeur ajustée au libellé (jamais de texte qui déborde sur le
                # bouton voisin — ex. « Plein écran fenêtré »).
                if b.label in ("−", "+"):
                    w = 56
                else:
                    w = max(96, fonts.body(bold=True).size(b.label)[0] + 28)
                b.rect = pygame.Rect(x, y, w, btn_h)
                x += w + 8
            y += pitch

    # ----------------------------------------------------------------- events
    def handle_event(self, event):
        # le panneau des raccourcis (overlay) capte tout tant qu'il est ouvert
        if self.shortcuts_panel is not None:
            if self.shortcuts_panel.handle(event):
                if self.shortcuts_panel.closed:
                    self.shortcuts_panel = None
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.shortcuts_btn.handle(event):
            self.shortcuts_panel = ShortcutsPanel()
            return
        for _label, btns in self.rows:
            for b in btns:
                if b.handle(event):
                    self._apply(b.action)
                    return

    def _apply(self, action):
        kind, val = action
        if kind == "window":
            self.app.set_window_mode(val)
        elif kind == "resolution":
            if val != display_settings.get_resolution():
                display_settings.set_resolution(val)
                display_settings.apply_resolution()
                self.app._apply_window_mode()
        elif kind == "mute":
            audio.set_muted(val)
            if not val:
                audio.play("tick_up")
        elif kind == "vol":
            if val != 0:
                audio.set_volume(round(audio.get_volume() + 0.1 * val, 2))
                audio.play("tick_up")
        elif kind == "lang":
            set_lang(val)
        elif kind == "anim":
            anim_settings.set_reduce_motion(val)
        elif kind == "colorblind":
            colorblind_settings.set_enabled(val)
        elif kind == "speed":
            self.app.sim_clock.set_speed(val)
        elif kind == "autosave":
            autosave_settings.set_interval(val)
        elif kind == "xpmode":
            experience_mode.set_mode(val)
        elif kind == "checklist":
            daily_checklist.set_enabled(self.app.gs.player, val)
        self._build()   # reconstruit libellés + états actifs

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.shortcuts_btn.update(mp, dt)
        for _label, btns in self.rows:
            for b in btns:
                b.update(mp, dt)

    # ------------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("RÉGLAGES", "SETTINGS"), (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L("Affichage, son, langue et confort de jeu — "
                                   "enregistré automatiquement.",
                                   "Display, sound, language and comfort — saved "
                                   "automatically."),
                          (42, 70), fonts.small(), config.COL_TEXT_DIM)

        for label, btns in self.rows:
            ry = btns[0].rect.y
            widgets.draw_text(surf, label, (60, ry + 10), fonts.body(bold=True),
                              config.COL_TEXT)
            for b in btns:
                b.draw(surf)
                if getattr(b, "active", False):
                    pygame.draw.rect(surf, config.COL_CYAN, b.rect, 2, border_radius=6)

        self.shortcuts_btn.draw(surf)
        # aide contextuelle bas d'écran
        hint = _L("Astuce : F11 bascule plein écran · Espace met le jeu en pause.",
                  "Tip: F11 toggles fullscreen · Space pauses the game.")
        widgets.draw_text(surf, hint, (60, config.footer_y() - 30),
                          fonts.small(), config.COL_TEXT_DIM)
        self.back_btn.draw(surf)
        if self.shortcuts_panel is not None:
            self.shortcuts_panel.draw(surf)
