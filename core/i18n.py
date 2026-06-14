"""
i18n.py — Internationalisation (français / anglais).

Usage :
    from core.i18n import t, set_lang, get_lang, toggle_lang
    t("menu.new")            -> "Nouvelle carrière" / "New career"

La langue est persistée dans SAVE_DIR/settings.json et survit aux redémarrages.
Les chaînes inconnues retombent sur le français puis sur la clé brute, donc une
clé non encore traduite n'a jamais d'effet bloquant.

Couverture : chrome de l'UI (menu, terminal, écran de sélection, boutons
communs). Le CONTENU finance (glossaire, leçons, examens, sociétés) reste en
français pour l'instant — extensible en ajoutant des clés ici.
"""
import json
import os

from core import config

_LANG = "fr"
_SETTINGS = os.path.join(config.SAVE_DIR, "settings.json")


def _load():
    global _LANG
    try:
        with open(_SETTINGS, "r", encoding="utf-8") as f:
            _LANG = json.load(f).get("lang", "fr")
    except Exception:
        _LANG = "fr"


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_SETTINGS, "w", encoding="utf-8") as f:
            json.dump({"lang": _LANG}, f)
    except Exception:
        pass


def get_lang():
    return _LANG


def set_lang(lang):
    global _LANG
    _LANG = "en" if lang == "en" else "fr"
    _save()


def toggle_lang():
    set_lang("en" if _LANG == "fr" else "fr")
    return _LANG


def t(key, **kwargs):
    s = TR.get(_LANG, {}).get(key)
    if s is None:
        s = TR["fr"].get(key, key)
    return s.format(**kwargs) if kwargs else s


# ---------------------------------------------------------------------------
# Table de traductions (chrome UI)
# ---------------------------------------------------------------------------
TR = {
    "fr": {
        # menu
        "menu.subtitle": "FINANCE CAREER SIMULATOR",
        "menu.tagline": "De stagiaire à la tête d'une firme mondiale.",
        "menu.continue": "CONTINUER",
        "menu.new": "NOUVELLE CARRIÈRE",
        "menu.load": "CHARGER / SAUVEGARDES",
        "menu.quit": "QUITTER",
        "menu.last_run": "DERNIÈRE PARTIE",
        "menu.lang": "LANGUE : FR",
        # commun
        "common.back_terminal": "← TERMINAL",
        "common.back": "← RETOUR",
        "common.confirm": "CONFIRMER",
        # glossaire
        "gloss.title": "GLOSSAIRE FINANCIER",
        "gloss.search": "Recherche",
        "gloss.categories": "Catégories",
        "gloss.terms": "Termes",
        "gloss.definition": "Définition",
        "gloss.all": "Tous",
        # écran de sélection
        "continent.title": "CHOISISSEZ VOTRE PLACE FINANCIÈRE",
        "continent.subtitle": "Chaque région impose son propre régulateur, ses normes "
                              "comptables et ses contraintes.",
        "continent.hint": "Cliquez sur une région du globe, ou sur une fiche →",
        "continent.hardcore_on": "MODE HARDCORE : ON",
        "continent.hardcore_off": "MODE HARDCORE : OFF",
        "continent.confirm": "CONFIRMER ET DÉMARRER",
        "continent.currency": "Devise",
        # terminal : panneaux
        "term.commands": "Commandes",
        "term.indices": "Indices",
        "term.health": "Santé financière",
        "term.topco": "Top sociétés",
        "term.priorities": "Priorités",
        "term.feed": "Flux & événements",
        "term.networth": "Valeur nette",
        "term.reputation": "Réputation",
        "term.world_hint": "MONDE — cliquez une région pour zoomer",
        # rail (libellés des boutons)
        "rail.ADV": "AVANCER ▸",
        "rail.MISSION": "MISSION",
        "rail.EVAL": "EXAMEN",
        "rail.DEALS": "DEALS",
        "rail.MARKET": "MARCHÉ",
        "rail.TOP": "TOP",
        "rail.MOVERS": "VARIATIONS",
        "rail.PORTFOLIO": "PORTEF.",
        "rail.MANDATES": "MANDATS",
        "rail.SHEET": "TABLEUR",
        "rail.ECO": "ÉCO",
        "rail.LEARN": "ACADÉMIE",
        "rail.CERT": "CERTIF.",
        "rail.INBOX": "INBOX",
        "rail.DECIDE": "DÉCIDE",
        "rail.CAREER": "CARRIÈRE",
        "rail.RIVALS": "RIVAUX",
        "rail.SAVE": "SAUVER",
        "rail.COMMANDS": "AIDE",
    },
    "en": {
        # menu
        "menu.subtitle": "FINANCE CAREER SIMULATOR",
        "menu.tagline": "From intern to the head of a global firm.",
        "menu.continue": "CONTINUE",
        "menu.new": "NEW CAREER",
        "menu.load": "LOAD / SAVES",
        "menu.quit": "QUIT",
        "menu.last_run": "LAST RUN",
        "menu.lang": "LANGUAGE: EN",
        # common
        "common.back_terminal": "← TERMINAL",
        "common.back": "← BACK",
        "common.confirm": "CONFIRM",
        # glossary
        "gloss.title": "FINANCIAL GLOSSARY",
        "gloss.search": "Search",
        "gloss.categories": "Categories",
        "gloss.terms": "Terms",
        "gloss.definition": "Definition",
        "gloss.all": "All",
        # selection screen
        "continent.title": "CHOOSE YOUR FINANCIAL HUB",
        "continent.subtitle": "Each region has its own regulator, accounting "
                              "standards and constraints.",
        "continent.hint": "Click a region on the globe, or a card →",
        "continent.hardcore_on": "HARDCORE MODE: ON",
        "continent.hardcore_off": "HARDCORE MODE: OFF",
        "continent.confirm": "CONFIRM & START",
        "continent.currency": "Currency",
        # terminal panels
        "term.commands": "Commands",
        "term.indices": "Indices",
        "term.health": "Financial health",
        "term.topco": "Top companies",
        "term.priorities": "Priorities",
        "term.feed": "Feed & events",
        "term.networth": "Net worth",
        "term.reputation": "Reputation",
        "term.world_hint": "WORLD — click a region to zoom",
        # rail (button labels)
        "rail.ADV": "ADVANCE ▸",
        "rail.MISSION": "MISSION",
        "rail.EVAL": "EXAM",
        "rail.DEALS": "DEALS",
        "rail.MARKET": "MARKET",
        "rail.TOP": "TOP",
        "rail.MOVERS": "MOVERS",
        "rail.PORTFOLIO": "BOOK",
        "rail.MANDATES": "MANDATES",
        "rail.SHEET": "SHEET",
        "rail.ECO": "ECO",
        "rail.LEARN": "ACADEMY",
        "rail.CERT": "CERTS",
        "rail.INBOX": "INBOX",
        "rail.DECIDE": "DECIDE",
        "rail.CAREER": "CAREER",
        "rail.RIVALS": "RIVALS",
        "rail.SAVE": "SAVE",
        "rail.COMMANDS": "HELP",
    },
}

_load()
