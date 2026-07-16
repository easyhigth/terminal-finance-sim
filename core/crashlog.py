"""
crashlog.py — Journal de plantage minimal, best-effort.

Écrit les tracebacks non attrapées survenues dans la boucle principale
(cf. main.py::App.run, filet de sécurité) dans un fichier texte sous
config.SAVE_DIR, pour qu'un joueur puisse transmettre un diagnostic après un
comportement inattendu — même en dehors du mode debug (core/applog.py,
désactivé par défaut, qui n'écrit nulle part tant que FINSIM_DEBUG n'est pas
posé). Purement additif et best-effort : toute erreur d'écriture est avalée
(ce module ne doit JAMAIS lui-même faire planter le jeu qu'il est censé
protéger). Le fichier est borné à MAX_ENTRIES tracebacks (les plus anciens
sont éliminés) pour ne jamais grossir indéfiniment.
"""
import datetime
import os
import traceback

from core import config

MAX_ENTRIES = 20
_PATH = os.path.join(config.SAVE_DIR, "crash.log")
_SEP = "=" * 70 + "\n"


def record(exc, context=""):
    """Ajoute le traceback de `exc` au journal (best-effort, ne lève jamais)."""
    try:
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        entry = (f"{_SEP}{ts}  [{context}]\n"
                  + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        entries = []
        if os.path.exists(_PATH):
            with open(_PATH, "r", encoding="utf-8") as f:
                existing = f.read()
            entries = [_SEP + chunk for chunk in existing.split(_SEP) if chunk.strip()]
        entries.append(entry)
        entries = entries[-MAX_ENTRIES:]
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            f.write("".join(entries))
    except Exception:
        pass


def swallowed(context=""):
    """À appeler dans un `except Exception:` best-effort À LA PLACE d'un
    `pass` nu : trace l'exception en cours via le logger applog (visible avec
    FINSIM_DEBUG=1) au lieu de l'avaler sans AUCUNE trace. N'écrit jamais dans
    crash.log (réservé aux vrais plantages de la boucle principale : ces
    handlers best-effort peuvent se déclencher à chaque frame et évinceraient
    les 20 entrées utiles), ne lève jamais, coût nul hors mode debug
    (NullHandler). Ne change RIEN au comportement du handler : l'exception
    reste absorbée."""
    try:
        from core.applog import logger
        logger.warning("exception avalée (best-effort) [%s]", context, exc_info=True)
    except Exception:
        pass


def path():
    """Chemin du fichier de journal (pour l'afficher au joueur/le diagnostic)."""
    return _PATH


def read():
    """Contenu brut du journal, ou "" s'il n'existe pas/est illisible — pour
    un écran de diagnostic accessible sans accès au système de fichiers
    (ex. joueur sur une machine où il ne peut pas ouvrir le dossier de
    sauvegarde)."""
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def clear():
    """Vide le journal (best-effort, ne lève jamais)."""
    try:
        if os.path.exists(_PATH):
            os.remove(_PATH)
    except Exception:
        pass
