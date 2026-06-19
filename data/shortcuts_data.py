"""
shortcuts_data.py — Catalogue déclaratif des raccourcis clavier du jeu.

Source unique affichée par le panneau « ⌨ RACCOURCIS » (ui/shortcutspanel.py).
Organisé par section ; chaque section est une liste de (touches, description).
Garder ce fichier à jour quand un raccourci est ajouté/retiré dans une scène.
"""

SECTIONS = [
    ("Général — partout dans le jeu", [
        ("ÉCHAP", "Retour à l'écran précédent (ou efface la recherche en cours, "
                   "ou ferme la fenêtre flottante la plus récente)"),
        ("↑ / ↓", "Naviguer dans une liste sélectionnable (messages, produits, lignes…)"),
        ("ENTRÉE", "Activer l'élément sélectionné — équivalent à un clic dessus"),
        ("Lettres/chiffres", "Taper dans le champ de recherche actif (curseur clignotant = "
                              "champ éditable)"),
        ("RETOUR ARRIÈRE", "Effacer le dernier caractère du champ de recherche"),
        ("Molette souris", "Faire défiler une liste ou un panneau sous le curseur"),
    ]),
    ("Terminal (hub principal)", [
        ("Lettres/chiffres", "Écrire une commande dans la ligne CMD>"),
        ("ENTRÉE", "Exécuter la commande tapée (équivaut à COMMANDS pour la liste complète)"),
        ("↑ / ↓", "Rappeler les commandes précédentes/suivantes de l'historique"),
        ("TAB", "Auto-complétion de la commande en cours"),
        ("PAGE PRÉC. / PAGE SUIV.", "Faire défiler l'historique de la console"),
        ("ÉCHAP", "Fermer la fenêtre flottante la plus récente, sinon ouvrir le menu"),
        ("Clic rail / NOM_COMMANDE", "Chaque bouton du rail correspond à une commande tapable "
                                     "(ex. SHOP, INBOX, NEWS, MORE, SHORTCUTS…)"),
    ]),
    ("Inbox (messagerie)", [
        ("↑ / ↓", "Sélectionner le message précédent/suivant dans la liste filtrée"),
        ("ENTRÉE", "Ouvrir le message sélectionné"),
    ]),
    ("Explorateur de marché", [
        ("↑ / ↓", "Sélectionner la société précédente/suivante dans le tableau"),
        ("ENTRÉE", "Ouvrir la fiche/graphe de la société sélectionnée"),
    ]),
    ("Boutique (SHOP)", [
        ("↑ / ↓", "Sélectionner l'actif précédent/suivant du catalogue (hors saisie de quantité)"),
        ("ENTRÉE", "Acheter l'actif sélectionné"),
        ("TAB", "Basculer le focus de saisie entre recherche et quantité"),
    ]),
    ("Académie / Tutoriels / Certifications", [
        ("↑ / ↓", "Sélectionner la leçon, le tutoriel ou le programme précédent/suivant"),
        ("ENTRÉE", "Ouvrir la leçon/le tutoriel, ou tenter l'examen du programme sélectionné"),
    ]),
    ("Glossaire", [
        ("↑ / ↓", "Sélectionner le terme précédent/suivant dans la liste filtrée"),
        ("ENTRÉE", "Afficher la définition détaillée du terme sélectionné"),
        ("Lettres", "Filtrer les termes par nom"),
    ]),
    ("Deals (transactions en cours)", [
        ("↑ / ↓", "Sélectionner le deal précédent/suivant"),
        ("ENTRÉE", "Ouvrir le deal sélectionné"),
    ]),
    ("Mandats clients", [
        ("↑ / ↓", "Sélectionner l'offre de mandat précédente/suivante"),
        ("ENTRÉE", "Accepter l'offre sélectionnée"),
        ("D", "Refuser l'offre sélectionnée"),
    ]),
    ("Équipe / analystes", [
        ("TAB", "Basculer le focus entre le catalogue (recrutement) et l'équipe actuelle"),
        ("↑ / ↓", "Sélectionner l'analyste précédent/suivant dans la liste active"),
        ("ENTRÉE", "Recruter (catalogue) ou licencier (équipe) l'analyste sélectionné"),
    ]),
    ("Sauvegardes", [
        ("↑ / ↓", "Sélectionner le slot de sauvegarde précédent/suivant"),
        ("ENTRÉE", "Charger la sauvegarde sélectionnée"),
        ("(souris uniquement)", "La suppression d'une sauvegarde reste volontairement "
                                "accessible uniquement à la souris, pour éviter une perte "
                                "accidentelle de partie"),
    ]),
    ("Choix du continent (nouvelle partie)", [
        ("↑ / ↓ / ← / →", "Sélectionner la région précédente/suivante"),
        ("ENTRÉE", "Choisir la région sélectionnée"),
    ]),
    ("PLUS (raccourcis vers toutes les pages)", [
        ("↑ / ↓", "Sélectionner le bouton de page précédent/suivant"),
        ("ENTRÉE", "Ouvrir la page sélectionnée"),
        ("Lettres", "Filtrer les pages par nom"),
    ]),
    ("Exam / Certif (carte de progression)", [
        ("TAB ou ← / →", "Basculer le focus entre les deux cartes (examen / certification)"),
        ("ENTRÉE", "Activer l'action de la carte ayant le focus"),
    ]),
    ("Palette de commandes (si activée)", [
        ("↑ / ↓", "Parcourir les résultats de la palette"),
        ("ENTRÉE", "Exécuter l'entrée sélectionnée"),
        ("ÉCHAP", "Fermer la palette"),
    ]),
    ("Barres de recherche (toutes scènes)", [
        ("Curseur clignotant", "Indique que le champ est éditable, même vide"),
        ("Lettres/chiffres", "Filtrer la liste affichée en temps réel"),
        ("RETOUR ARRIÈRE", "Effacer le dernier caractère"),
        ("ÉCHAP", "Vider la recherche (un 2ᵉ ÉCHAP revient à l'écran précédent)"),
    ]),
    ("Fenêtres flottantes (fiches, graphes, accès rapide)", [
        ("ÉCHAP", "Ferme la fenêtre flottante la plus récente"),
        ("(souris)", "Glisser la barre de titre pour déplacer ; ✕ pour fermer ; molette pour "
                     "défiler le contenu si nécessaire"),
    ]),
    ("Ce panneau (RACCOURCIS)", [
        ("↑ / ↓", "Faire défiler la liste des raccourcis"),
        ("PAGE PRÉC. / PAGE SUIV.", "Défiler par page"),
        ("ÉCHAP", "Fermer ce panneau"),
        ("(souris)", "Glisser la barre de titre pour déplacer le panneau ; molette pour défiler"),
    ]),
]
