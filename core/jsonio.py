"""
jsonio.py — Écriture JSON ATOMIQUE (+ backup) pour tout ce qui est précieux.

Écrire directement dans le fichier final expose à la corruption : un crash,
une coupure de courant ou un disque plein en plein `json.dump` laisse un
fichier à moitié écrit — et pour un slot de sauvegarde, c'est une partie
perdue. Ici :

  1. on sérialise d'abord dans un fichier temporaire du MÊME dossier ;
  2. `os.replace()` (atomique sur POSIX et Windows) bascule le temporaire
     à la place du fichier final — le fichier est soit l'ancien, soit le
     nouveau, jamais un état intermédiaire ;
  3. si un fichier existait déjà, il est d'abord conservé en `<nom>.bak`
     (rotation à 1 : le .bak précédent est écrasé) — un filet de plus si
     le NOUVEAU contenu s'avère mauvais (bug de sérialisation).

`read_json_with_backup()` fait le chemin inverse : lit le fichier principal,
et retombe sur le `.bak` s'il est absent/corrompu.
"""
import json
import os
import tempfile

from core.applog import logger


def backup_path(path):
    """Chemin du backup associé à `path` (rotation à 1)."""
    return path + ".bak"


def write_json_atomic(path, data, indent=2, keep_backup=True):
    """Écrit `data` en JSON à `path` de façon atomique. Si `keep_backup`,
    l'ancien fichier (s'il existe) survit en `<path>.bak`. Lève en cas
    d'échec (l'appelant décide si c'est fatal) mais ne laisse JAMAIS un
    fichier final tronqué."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d or ".", prefix=os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        if keep_backup and os.path.exists(path):
            try:
                os.replace(path, backup_path(path))
            except OSError:
                # le backup est un bonus, pas une condition : on n'échoue
                # pas une sauvegarde valide parce que le .bak est bloqué.
                from core import crashlog
                crashlog.swallowed("jsonio.backup_rotate")
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return path


def read_json_with_backup(path):
    """Lit un JSON écrit par `write_json_atomic`. Si le fichier principal est
    absent, illisible ou corrompu, tente le `.bak`. Retourne (data, source)
    où source vaut "main", "backup", ou (None, None) si rien d'exploitable."""
    for candidate, label in ((path, "main"), (backup_path(path), "backup")):
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as exc:
            logger.warning("jsonio: %s illisible (%s), on tente la suite", candidate, exc)
            continue
        if label == "backup":
            logger.warning("jsonio: fichier principal perdu, backup utilisé (%s)", candidate)
        return data, label
    return None, None
