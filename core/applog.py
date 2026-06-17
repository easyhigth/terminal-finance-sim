"""
applog.py — Logging minimal, désactivé par défaut.

Couche de journalisation purement additive : aucune dépendance hors stdlib,
aucun effet sur le comportement du jeu. Désactivée par défaut (NullHandler,
niveau WARNING) pour ne jamais polluer stdout/stderr en jeu normal.

Activation : variable d'environnement FINSIM_DEBUG=1 (ou toute valeur non
vide/"0"/"false"). Une fois activé, le logger "finsim" passe en niveau DEBUG
et écrit sur stderr, ce qui permet de tracer les sauvegardes/chargements,
les pas de marché, et d'autres transitions d'état pour le débogage.
"""
import logging
import os


def _debug_enabled():
    v = os.environ.get("FINSIM_DEBUG", "")
    return v.strip().lower() not in ("", "0", "false", "no")


DEBUG = _debug_enabled()

logger = logging.getLogger("finsim")

if DEBUG:
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setFormatter(
            logging.Formatter("[finsim] %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(_handler)
else:
    logger.setLevel(logging.WARNING)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

# Évite la double-propagation vers le root logger (qui pourrait avoir sa
# propre config et dupliquer/afficher les messages de façon inattendue).
logger.propagate = False
