"""
shortcuts_data.py — Catalogue déclaratif des raccourcis clavier du jeu.

Source unique affichée par le panneau « ⌨ RACCOURCIS » (ui/shortcutspanel.py).
Organisé par section ; chaque section est une liste de (touches, description).
Garder ce fichier à jour quand un raccourci est ajouté/retiré dans une scène.
"""

SECTIONS = [
    ("Général — partout dans le jeu", [
        ("ÉCHAP", "Remonter d'un niveau : sort d'un bloc focalisé, ferme une fenêtre "
                   "flottante, efface une recherche, ou revient à l'écran précédent"),
        ("TAB / MAJ+TAB", "Passer au bloc/zone interactive suivant ou précédent"),
        ("↑ / ↓ / ← / →", "Déplacer le focus selon la position visuelle réelle des "
                           "blocs ou des éléments d'une liste/grille"),
        ("ENTRÉE", "Descendre dans le bloc focalisé (1ʳᵉ pression) puis activer "
                    "l'élément interne focalisé (2ᵉ pression) — équivalent à un clic"),
        ("Lettres/chiffres", "Taper dans le champ de recherche actif (curseur clignotant = "
                              "champ éditable)"),
        ("RETOUR ARRIÈRE", "Effacer le dernier caractère du champ de recherche"),
        ("Molette souris", "Faire défiler une liste ou un panneau sous le curseur"),
        ("Focus clavier", "Liseré BLANC à coins marqués = focus clavier (distinct du "
                           "survol souris en cyan et de la sélection ambre)"),
    ]),
    ("Terminal (hub principal) — navigation hiérarchique", [
        ("Lettres/chiffres (focus console)", "Écrire une commande dans la ligne CMD> "
            "— par défaut le focus est dans la console, donc la saisie marche "
            "immédiatement comme avant"),
        ("ENTRÉE (focus console)", "Exécuter la commande tapée"),
        ("↑ / ↓ (focus console)", "Rappeler les commandes précédentes/suivantes de l'historique"),
        ("TAB (focus console)", "Auto-complétion de la commande en cours"),
        ("PAGE PRÉC. / PAGE SUIV.", "Faire défiler l'historique de la console"),
        ("ÉCHAP (focus console)", "Remonte au niveau bloc (la console reste sélectionnée, "
            "liseré blanc visible) — un 2ᵉ usage d'ÉCHAP au niveau bloc ouvre le menu"),
        ("TAB (niveau bloc)", "Passe au bloc suivant : CONSOLE → RAIL → INDICES → "
            "SANTÉ → SOCIÉTÉS → CARRIÈRE → FLUX (MAJ+TAB pour reculer)"),
        ("↑ / ↓ / ← / → (niveau bloc)", "Déplace le focus vers le bloc le plus proche "
            "dans cette direction, selon sa position réelle à l'écran"),
        ("ENTRÉE (bloc RAIL/INDICES/SOCIÉTÉS)", "Entre dans le bloc : les flèches "
            "naviguent alors ses lignes internes (commandes, indices, sociétés suivies)"),
        ("ENTRÉE (bloc SANTÉ/CARRIÈRE/FLUX)", "Ouvre directement la scène associée "
            "(ces blocs n'ont pas de contenu interne navigable)"),
        ("ENTRÉE (item interne)", "Active l'élément : lance la commande du rail, ouvre "
            "le graphe d'un indice, ouvre la fiche d'une société suivie"),
        ("ÉCHAP (niveau bloc, dans un bloc)", "Remonte du contenu interne au niveau "
            "bloc (ex. sort de la liste du rail sans quitter le terminal)"),
        ("Exemple concret", "Focus sur le bloc CONSOLE (vide) → ÉCHAP pour remonter au "
            "niveau bloc → ↓ pour aller au bloc situé en dessous (RAIL) → ENTRÉE pour "
            "y entrer → ↑/↓ pour choisir une commande → ENTRÉE pour la lancer"),
        ("Clic rail / NOM_COMMANDE", "Chaque bouton du rail correspond à une commande tapable "
                                     "(ex. SHOP, INBOX, NEWS, MORE, SHORTCUTS…)"),
        ("CTRL+M", "Marché (MARKETHUB)"),
        ("CTRL+P", "Portefeuille (PORTFOLIO)"),
        ("CTRL+I", "Inbox"),
        ("CTRL+N", "News"),
        ("CTRL+J", "Mission"),
        ("CTRL+A", "Mandats clients (MANDATES)"),
        ("CTRL+D", "Deals"),
        ("CTRL+F", "M&A (Fusions-acquisitions)"),
        ("CTRL+E", "Décider (dilemme en attente)"),
        ("CTRL+V", "ADV (avancer le temps)"),
        ("CTRL+X", "Exam / Certif"),
        ("CTRL+B", "Boutique (SHOP)"),
        ("CTRL+T", "Tableur (SHEET)"),
        ("CTRL+L", "Académie (LEARN)"),
        ("CTRL+G", "Glossaire"),
        ("CTRL+O", "Plus (toutes les pages)"),
        ("CTRL+S", "Sauvegarder"),
        ("CTRL+H", "Aide (catalogue des commandes)"),
        ("CTRL+K", "Palette de commandes (recherche rapide)"),
    ]),
    ("Terminal — pages disponibles seulement depuis PLUS", [
        ("CTRL+MAJ+E", "Explorateur de marché (EXPLORE)"),
        ("CTRL+MAJ+C", "Carrière (CAREER)"),
        ("CTRL+MAJ+B", "Portefeuille détaillé (BOOK)"),
        ("CTRL+MAJ+H", "Historique complet (TIMELINE)"),
        ("CTRL+MAJ+T", "Équipe / analystes (TEAM)"),
        ("CTRL+MAJ+R", "Risque / VaR (RISK)"),
        ("CTRL+MAJ+A", "Calendrier macro (AGENDA)"),
        ("CTRL+MAJ+V", "Revue annuelle (REVIEW)"),
        ("CTRL+MAJ+L", "Rivaux / classement (RIVALS)"),
        ("CTRL+MAJ+S", "Stress test régulateur (STRESS)"),
        ("CTRL+MAJ+W", "Sauvegardes (SAVES)"),
        ("CTRL+MAJ+O", "Voie / spécialisation (TRACK)"),
        ("Autres pages PLUS", "Toujours accessibles via CTRL+O (MORE) puis flèches/recherche, "
            "ou en tapant directement leur commande (ETF, BONDS, CMDTY, CRYPTO, STRUCT, "
            "CREDIT, SWAP, GOV, FX, OPTIONS, IPO, GP, PA, ATTR, ALERT, QUANT, FRONTIER, "
            "HEDGE, ALM, TUTO, CERT…)"),
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
        ("↑ / ↓ / ← / →", "Déplacer le focus vers le bouton le plus proche dans cette "
                           "direction, selon sa position réelle dans la grille"),
        ("ENTRÉE", "Ouvrir la page sélectionnée (liseré blanc = focus clavier)"),
        ("Lettres", "Filtrer les pages par nom"),
        ("ÉCHAP", "Vider la recherche, sinon revenir à l'écran précédent"),
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
