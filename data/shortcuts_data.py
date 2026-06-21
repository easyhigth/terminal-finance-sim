"""
shortcuts_data.py — Catalogue déclaratif des raccourcis clavier du jeu.

Source unique affichée par le panneau « ⌨ RACCOURCIS » (ui/shortcutspanel.py).
Organisé par section ; chaque section est une liste de (touches, description).
Volontairement condensé : les patrons de navigation communs à la plupart des
écrans (listes, grilles, recherche) sont expliqués une seule fois au global
plutôt que répétés scène par scène ; seules les vraies exceptions sont
détaillées. Garder ce fichier à jour quand un raccourci est ajouté/retiré.
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
                              "champ éditable) ; filtre la liste affichée en temps réel"),
        ("RETOUR ARRIÈRE", "Effacer le dernier caractère du champ de recherche"),
        ("Molette souris", "Faire défiler une liste ou un panneau sous le curseur"),
        ("Focus clavier", "Liseré BLANC à coins marqués = focus clavier (distinct du "
                           "survol souris en cyan et de la sélection ambre)"),
    ]),
    ("Listes, grilles et catalogues — la plupart des écrans", [
        ("↑ / ↓ / ← / →", "Sélectionner l'élément précédent/suivant (ligne, carte ou case "
                           "de grille selon l'écran : Inbox, Explorateur, Académie/Tutoriels/"
                           "Certifications, Glossaire, Deals, Mandats, Choix du continent, "
                           "PLUS, Palette de commandes…)"),
        ("ENTRÉE", "Activer l'élément sélectionné : ouvrir, acheter, charger, accepter ou "
                    "lancer selon le contexte de l'écran — toujours l'équivalent du clic"),
        ("Lettres/chiffres", "Filtrer la liste quand l'écran a un champ de recherche"),
        ("ÉCHAP", "Vider la recherche en cours, sinon revenir à l'écran précédent"),
    ]),
    ("Exceptions par écran", [
        ("Boutique (SHOP) — TAB", "Bascule le focus de saisie entre recherche et quantité"),
        ("Équipe — TAB", "Bascule le focus entre le catalogue de recrutement et l'équipe "
                          "actuelle ; ENTRÉE recrute ou licencie selon le volet actif"),
        ("Exam / Certif — TAB ou ← / →", "Bascule le focus entre la carte examen et la "
                                          "carte certification"),
        ("Mandats — D", "Refuser l'offre de mandat sélectionnée (ENTRÉE l'accepte)"),
        ("Sauvegardes — (souris uniquement)", "La suppression d'une sauvegarde reste "
            "volontairement accessible uniquement à la souris, pour éviter une perte "
            "accidentelle de partie"),
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
    ]),
    ("Raccourcis directs CTRL+lettre (terminal)", [
        ("Clic rail / NOM_COMMANDE", "Chaque bouton du rail correspond à une commande tapable "
                                     "(ex. SHOP, INBOX, NEWS, MORE, SHORTCUTS…)"),
        ("CTRL+M / P / I / N / J", "Marché / Portefeuille / Inbox / News / Mission"),
        ("CTRL+A / D / F / E / V", "Mandats / Deals / M&A / Décider / ADV (avancer le temps)"),
        ("CTRL+X / B / T / L / G", "Exam-Certif / Boutique / Tableur / Académie / Glossaire"),
        ("CTRL+O / S / H / K", "Plus (toutes les pages) / Sauvegarder / Aide / Palette de commandes"),
        ("CTRL+MAJ+lettre", "Pages disponibles seulement depuis PLUS (ex. CTRL+MAJ+E "
            "Explorateur, +C Carrière, +B Portefeuille détaillé, +H Historique, +T Équipe, "
            "+R Risque/VaR, +A Calendrier macro, +V Revue annuelle, +L Rivaux, +S Stress test, "
            "+W Sauvegardes, +O Voie/spécialisation) — voir le panneau PLUS (CTRL+O) pour "
            "la liste complète et la recherche par nom"),
        ("Autres pages", "Toujours accessibles via CTRL+O (MORE) puis flèches/recherche, "
            "ou en tapant directement leur commande (ETF, BONDS, CMDTY, CRYPTO, STRUCT, "
            "CREDIT, SWAP, GOV, FX, OPTIONS, IPO, GP, PA, ATTR, ALERT, QUANT, FRONTIER, "
            "HEDGE, ALM, TUTO, CERT…)"),
    ]),
    ("Fenêtres flottantes et ce panneau", [
        ("ÉCHAP", "Ferme la fenêtre flottante la plus récente, ou ce panneau s'il est ouvert"),
        ("↑ / ↓ / PAGE PRÉC. / PAGE SUIV.", "Faire défiler le contenu (graphe, fiche, "
                                            "liste de raccourcis…)"),
        ("(souris)", "Glisser la barre de titre pour déplacer la fenêtre/le panneau ; "
                     "✕ pour fermer ; molette pour défiler"),
    ]),
]
