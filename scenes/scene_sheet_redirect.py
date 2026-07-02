"""
scene_sheet_redirect.py — Alias « spreadsheet » vers l'app Tableur du bureau.

L'ancien tableur PLEIN ÉCRAN (scene_spreadsheet, avec son état `app.sheet`
distinct du classeur `app.workbook`) a été retiré : depuis que le bureau est
l'écran maître (étape 4), il n'était plus atteignable que par des navigations
plein écran marginales — et maintenait un DEUXIÈME état de tableur.

Le nom de scène "spreadsheet" reste enregistré (boutons « → TABLEUR » des
états financiers / fiches M&A, entrée PLUS, commande SHEET) mais atterrit
désormais TOUJOURS sur le bureau avec l'app Tableur native ouverte
(`apps/app_sheet.py`, classeur partagé `app.workbook`) — un seul tableur, un
seul état. Sur le bureau, `DesktopScene._open_scene_window` intercepte déjà
le nom AVANT cette scène ; elle ne sert que de filet aux navigations plein
écran (une frame de transition puis redirection).
"""
from core import config
from core.scene_manager import Scene
from ui import fonts, widgets


class SheetRedirectScene(Scene):
    def on_enter(self, **kwargs):
        self._import_data = kwargs.get("import_data")
        self._done = False

    def update(self, dt):
        if self._done:
            return
        self._done = True
        data = self._import_data
        self._import_data = None
        self.app.scenes.go("desktop")
        desk = self.app.scenes.current
        desk._open_sheet_app(data)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "Ouverture du tableur…",
                          (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2),
                          fonts.small(), config.COL_TEXT_DIM, align="center")
