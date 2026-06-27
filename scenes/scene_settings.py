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

from core import anim_settings, audio, config, display_settings
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
        x0 = 360
        y = config.content_top() + 30
        row_h, gap = 58, 10
        for _label, btns in self.rows:
            x = x0
            for b in btns:
                # largeur ajustée au libellé (jamais de texte qui déborde sur le
                # bouton voisin — ex. « Plein écran fenêtré »).
                if b.label in ("−", "+"):
                    w = 56
                else:
                    w = max(96, fonts.body(bold=True).size(b.label)[0] + 28)
                b.rect = pygame.Rect(x, y, w, 40)
                x += w + 8
            y += row_h + gap

    # ----------------------------------------------------------------- events
    def handle_event(self, event):
        # le panneau des raccourcis (overlay) capte tout tant qu'il est ouvert
        if self.shortcuts_panel is not None:
            if self.shortcuts_panel.handle(event):
                if self.shortcuts_panel.closed:
                    self.shortcuts_panel = None
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
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
        elif kind == "speed":
            self.app.sim_clock.set_speed(val)
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
