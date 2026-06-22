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
        "menu.sandbox": "BAC À SABLE",
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
        # académie
        "academy.title": "ACADÉMIE DE FINANCE",
        "academy.progress": "{n}/{m} leçons lues · cliquez une leçon pour l'étudier",
        "academy.program": "Programme",
        "academy.lesson": "Leçon",
        "academy.formula": "FORMULE",
        "academy.example": "EXEMPLE",
        "academy.takeaway": "À RETENIR",
        # écran de sélection
        "continent.title": "CHOISISSEZ VOTRE PLACE FINANCIÈRE",
        "continent.subtitle": "Chaque région impose son propre régulateur, ses normes "
                              "comptables et ses contraintes.",
        "continent.hint": "Cliquez sur une région du globe, ou sur une fiche →",
        "continent.hardcore_on": "MODE HARDCORE : ON",
        "continent.hardcore_off": "MODE HARDCORE : OFF",
        "continent.confirm": "CONFIRMER ET DÉMARRER",
        "continent.next": "SUIVANT →",
        "continent.currency": "Devise",
        # écran de configuration de la partie (scénario / archétype / hardcore)
        "runsetup.title": "CONFIGUREZ VOTRE PARTIE",
        "runsetup.subtitle": "Place financière : {continent}. Choisissez les conditions de départ.",
        "runsetup.scenario": "Scénario de départ",
        "runsetup.archetype": "Archétype de jeu",
        "runsetup.firm": "Firme de départ",
        "runsetup.hardcore_title": "MODE HARDCORE",
        "runsetup.hardcore_on": "Permadeath activé : aucune reprise après une faillite, "
                                "la sauvegarde est définitive.",
        "runsetup.hardcore_off": "Mode normal : vous pouvez recharger une sauvegarde "
                                 "après un échec.",
        "runsetup.confirm": "CONFIRMER ET DÉMARRER",
        "runsetup.back": "← RÉGION",
        "runsetup.next": "SUIVANT →",
        "runsetup.prev": "← PRÉCÉDENT",
        "runsetup.step1": "Étape 1/2 : scénario et archétype",
        "runsetup.step2": "Étape 2/2 : firme de départ",
        # écran de configuration du mode bac à sable (run jetable, non sauvegardé)
        "sandbox.title": "BAC À SABLE",
        "sandbox.subtitle": "Run libre pour tester portefeuilles, paramètres de marché et "
                            "scénarios de crise — jamais sauvegardé.",
        "sandbox.continent": "Place financière",
        "sandbox.cash": "Capital de départ",
        "sandbox.regime": "Régime de marché",
        "sandbox.unlock_label": "Déblocage",
        "sandbox.unlock_all": "TOUT DÉBLOQUER",
        "sandbox.launch": "LANCER",
        "sandbox.hint": "Aucune sauvegarde n'est créée ni écrasée en mode bac à sable. "
                        "Utilisez la commande CRISIS au terminal pour déclencher un "
                        "scénario de stress test à la demande.",
        "sandbox.badge": "BAC À SABLE",
        # terminal : panneaux
        "term.commands": "Commandes",
        "term.indices": "Indices",
        "term.health": "Santé financière",
        "term.topco": "Explorer",
        "term.career": "Carrière",
        "term.feed": "Flux & événements",
        "term.networth": "Valeur nette",
        "term.reputation": "Réputation",
        "term.world_hint": "MONDE — cliquez une région pour zoomer",
        # rail (libellés des boutons)
        "rail.ADV": "AVANCER ▸",
        "rail.MISSION": "MISSION",
        "rail.EVAL": "EXAMEN",
        "rail.DEALS": "DEALS",
        "rail.MA": "M&A",
        "rail.MARKET": "MARCHÉ",
        "rail.MARKETHUB": "MARCHÉ",
        "rail.SHOP": "SHOP",
        "rail.TOP": "TOP",
        "rail.MOVERS": "VARIATIONS",
        "rail.PORTFOLIO": "PORTEF.",
        "rail.MANDATES": "MANDATS",
        "rail.SHEET": "TABLEUR",
        "rail.EXPLORER": "EXPLORATEUR",
        "rail.ECO": "ÉCO",
        "rail.LEARN": "ACADÉMIE",
        "rail.GP": "GRAPHES",
        "rail.CERT": "CERTIF.",
        "rail.EXAMCERT": "EXAM/CERTIF",
        "rail.GLOSSARY": "GLOSSAIRE",
        "rail.TEAM": "ÉQUIPES/ANALYSTES",
        "rail.INBOX": "INBOX",
        "rail.NEWS": "NEWS",
        "rail.ETF": "ETF",
        "rail.MORE": "PLUS",
        "rail.DECIDE": "DÉCISIONS",
        "rail.CAREER": "CARRIÈRE",
        "rail.RIVALS": "RIVAUX",
        "rail.SAVE": "SAUVER",
        "rail.COMMANDS": "AIDE",
        # panneau raccourcis clavier
        "shortcuts.title": "⌨ RACCOURCIS CLAVIER — jouer sans la souris",
    },
    "en": {
        # menu
        "menu.subtitle": "FINANCE CAREER SIMULATOR",
        "menu.tagline": "From intern to the head of a global firm.",
        "menu.continue": "CONTINUE",
        "menu.new": "NEW CAREER",
        "menu.load": "LOAD / SAVES",
        "menu.sandbox": "SANDBOX",
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
        # academy
        "academy.title": "FINANCE ACADEMY",
        "academy.progress": "{n}/{m} lessons read · click a lesson to study",
        "academy.program": "Program",
        "academy.lesson": "Lesson",
        "academy.formula": "FORMULA",
        "academy.example": "EXAMPLE",
        "academy.takeaway": "KEY TAKEAWAY",
        # selection screen
        "continent.title": "CHOOSE YOUR FINANCIAL HUB",
        "continent.subtitle": "Each region has its own regulator, accounting "
                              "standards and constraints.",
        "continent.hint": "Click a region on the globe, or a card →",
        "continent.hardcore_on": "HARDCORE MODE: ON",
        "continent.hardcore_off": "HARDCORE MODE: OFF",
        "continent.confirm": "CONFIRM & START",
        "continent.next": "NEXT →",
        "continent.currency": "Currency",
        # run setup screen (scenario / archetype / hardcore)
        "runsetup.title": "SET UP YOUR CAREER",
        "runsetup.subtitle": "Financial hub: {continent}. Choose your starting conditions.",
        "runsetup.scenario": "Starting scenario",
        "runsetup.archetype": "Run archetype",
        "runsetup.firm": "Starting firm",
        "runsetup.hardcore_title": "HARDCORE MODE",
        "runsetup.hardcore_on": "Permadeath on: no recovery after bankruptcy, "
                                "the save is final.",
        "runsetup.hardcore_off": "Normal mode: you can reload a save after a setback.",
        "runsetup.confirm": "CONFIRM & START",
        "runsetup.back": "← REGION",
        "runsetup.next": "NEXT →",
        "runsetup.prev": "← BACK",
        "runsetup.step1": "Step 1/2: scenario and archetype",
        "runsetup.step2": "Step 2/2: starting firm",
        # sandbox mode setup screen (free-play run, never saved)
        "sandbox.title": "SANDBOX MODE",
        "sandbox.subtitle": "Free-play run to test portfolios, market parameters and "
                            "crisis scenarios — never saved.",
        "sandbox.continent": "Financial hub",
        "sandbox.cash": "Starting cash",
        "sandbox.regime": "Market regime",
        "sandbox.unlock_label": "Unlocks",
        "sandbox.unlock_all": "UNLOCK ALL",
        "sandbox.launch": "LAUNCH",
        "sandbox.hint": "No save is created or overwritten in sandbox mode. Use the "
                        "CRISIS command in the terminal to trigger a stress test "
                        "scenario on demand.",
        "sandbox.badge": "SANDBOX",
        # terminal panels
        "term.commands": "Commands",
        "term.indices": "Indices",
        "term.health": "Financial health",
        "term.topco": "Explorer",
        "term.career": "Career",
        "term.feed": "Feed & events",
        "term.networth": "Net worth",
        "term.reputation": "Reputation",
        "term.world_hint": "WORLD — click a region to zoom",
        # rail (button labels)
        "rail.ADV": "ADVANCE ▸",
        "rail.MISSION": "MISSION",
        "rail.EVAL": "EXAM",
        "rail.DEALS": "DEALS",
        "rail.MA": "M&A",
        "rail.MARKET": "MARKET",
        "rail.MARKETHUB": "MARKET",
        "rail.SHOP": "SHOP",
        "rail.TOP": "TOP",
        "rail.MOVERS": "MOVERS",
        "rail.PORTFOLIO": "BOOK",
        "rail.MANDATES": "MANDATES",
        "rail.SHEET": "SHEET",
        "rail.EXPLORER": "EXPLORER",
        "rail.ECO": "ECO",
        "rail.LEARN": "ACADEMY",
        "rail.GP": "GRAPHS",
        "rail.CERT": "CERTS",
        "rail.EXAMCERT": "EXAM/CERT",
        "rail.GLOSSARY": "GLOSSARY",
        "rail.TEAM": "TEAM/ANALYSTS",
        "rail.INBOX": "INBOX",
        "rail.NEWS": "NEWS",
        "rail.ETF": "ETF",
        "rail.MORE": "MORE",
        "rail.DECIDE": "DECISIONS",
        "rail.CAREER": "CAREER",
        "rail.RIVALS": "RIVALS",
        "rail.SAVE": "SAVE",
        "rail.COMMANDS": "HELP",
        # keyboard shortcuts panel
        "shortcuts.title": "⌨ KEYBOARD SHORTCUTS — play without a mouse",
    },
}

_load()
