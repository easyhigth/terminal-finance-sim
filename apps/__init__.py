"""
apps — Applications du BUREAU (refonte UI « Jeu PC »).

Chaque application est un objet `DesktopApp` (cf. `apps/base.py`) hébergé dans
une fenêtre déplaçable par `ui/window_manager.py`. Les apps ne dessinent QUE
dans le rectangle de contenu qu'on leur passe (coordonnées absolues) et
réutilisent la logique de jeu existante (marché, portefeuille, tableur) sans la
dupliquer.
"""
