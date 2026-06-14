"""
build.py — Construit l'exécutable du jeu via PyInstaller.

Usage :
    pip install -r requirements.txt
    pip install pyinstaller
    python build.py            # build standard depuis terminal.spec
    python build.py --clean    # nettoie d'abord build/ et dist/

Résultat dans dist/ :
    - macOS   : dist/TERMINAL.app
    - Windows : dist/TERMINAL.exe

Ce script encapsule simplement `pyinstaller terminal.spec` et vérifie au
préalable que PyInstaller est installé.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "terminal.spec")


def main():
    clean = "--clean" in sys.argv

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller n'est pas installé. Faites : pip install pyinstaller")
        return 1

    if clean:
        for d in ("build", "dist"):
            path = os.path.join(HERE, d)
            if os.path.isdir(path):
                print(f"Nettoyage de {d}/ ...")
                shutil.rmtree(path)

    cmd = [sys.executable, "-m", "PyInstaller", SPEC, "--noconfirm"]
    if clean:
        cmd.append("--clean")
    print("Lancement :", " ".join(cmd))
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode == 0:
        print("\nBuild terminé. Voir le dossier dist/.")
        if sys.platform == "darwin":
            print("  → dist/TERMINAL.app")
        elif sys.platform.startswith("win"):
            print("  → dist/TERMINAL.exe")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
