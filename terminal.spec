# -*- mode: python ; coding: utf-8 -*-
"""
terminal.spec — Recette de build PyInstaller pour TERMINAL — Finance Career Simulator.

Usage :
    pip install pyinstaller
    pyinstaller terminal.spec            # build dans dist/

Résultat :
    - macOS   : dist/TERMINAL.app   (bundle double-cliquable)
    - Windows : dist/TERMINAL/TERMINAL.exe (dossier) ou dist/TERMINAL.exe (onefile)

Le dossier "assets" est embarqué. Les sauvegardes ne sont PAS embarquées :
elles sont écrites à l'exécution dans l'espace utilisateur (cf. core/config.py).
"""
import sys
import os

block_cipher = None

# On embarque le dossier assets s'il existe (icônes, images...).
datas = []
if os.path.isdir("assets"):
    datas.append(("assets", "assets"))

# Imports parfois non détectés automatiquement par l'analyse statique.
hiddenimports = [
    "scipy.special.cython_special",
    "scipy._lib.messagestream",
    "pygame",
    "numpy",
]

a = Analysis(
    ["main.py"],
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # on exclut quelques gros modules inutiles pour alléger le binaire
    excludes=["tkinter", "matplotlib", "PIL", "pytest", "IPython"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Icône optionnelle : assets/icon.icns (Mac) / assets/icon.ico (Windows)
_icon_mac = "assets/icon.icns" if os.path.exists("assets/icon.icns") else None
_icon_win = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

if sys.platform == "darwin":
    # macOS : exécutable + collecte + bundle .app
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="TERMINAL",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,            # pas de console : application fenêtrée
        disable_windowed_traceback=False,
        target_arch=None,         # universal2 possible si Python le supporte
        codesign_identity=None,
        entitlements_file=None,
        icon=_icon_mac,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=True, upx_exclude=[], name="TERMINAL",
    )
    app = BUNDLE(
        coll,
        name="TERMINAL.app",
        icon=_icon_mac,
        bundle_identifier="com.financesim.terminal",
        info_plist={
            "CFBundleName": "TERMINAL",
            "CFBundleDisplayName": "TERMINAL — Finance Career Simulator",
            "CFBundleShortVersionString": "0.2.0",
            "NSHighResolutionCapable": True,
        },
    )
else:
    # Windows / Linux : un exécutable onefile fenêtré
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name="TERMINAL",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,            # pas de console : application fenêtrée
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=_icon_win,
    )
