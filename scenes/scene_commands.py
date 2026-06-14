"""
scene_commands.py — Catalogue complet des commandes du terminal.
Ouvert via la commande COMMANDS (ou ?). Liste catégorisée, consultable.
"""
import pygame
from core import config
from core.scene_manager import Scene
from ui import fonts, widgets


# Source unique de vérité des commandes (catégorie -> [(cmd, description)]).
CATALOG = [
    ("Navigation & système", [
        ("HELP", "Aide rapide (commandes essentielles)"),
        ("COMMANDS / ?", "Ce catalogue complet"),
        ("STATUS", "Votre situation (grade, cash, réputation, temps)"),
        ("MENU / ESC", "Retour au menu principal"),
        ("SAVES", "Gestion des sauvegardes (slots)"),
        ("SAVE", "Sauvegarde manuelle (désactivée en hardcore)"),
    ]),
    ("Temps & carrière", [
        ("ADV / NEXT", "Avancer le temps de 5 jours (un pas de marché)"),
        ("MISSION", "Jouer la mission du grade (réputation + honoraire)"),
        ("CAREER", "Tableau de bord : roadmap, objectifs, stats, journal"),
        ("ROADMAP / OBJECTIVES / HISTORY", "Raccourcis vers l'écran carrière"),
        ("INBOX / MAIL", "Messagerie (manager, clients, conformité, desk)"),
        ("RIVALS", "Classement face aux banquiers concurrents"),
        ("DECIDE", "Trancher un dilemme en attente (éthique/réglementaire)"),
        ("EVAL", "Examen de promotion (critères combinés requis)"),
        ("CERT", "Certifications CFA / FRM / CQF (boost de carrière)"),
        ("TRACK", "Choisir/voir sa voie de spécialisation"),
    ]),
    ("Savoir & macro", [
        ("LEARN", "Académie : leçons de finance (DCF, Sharpe, VaR, options...)"),
        ("ECO / MACRO", "Indicateurs : taux, inflation, croissance, chômage"),
        ("DEFINE <terme>", "Définition rapide (glossaire). Ex: DEFINE WACC"),
        ("RESEARCH <ticker>", "Valeur intrinsèque + reco analyste"),
        ("RV <ticker>", "Valeur relative : multiples vs pairs du secteur"),
    ]),
    ("Fonctions style Bloomberg", [
        ("DES / FA <tk>", "Fiche société / fondamentaux"),
        ("GP <tk>", "Graphe de prix"),
        ("RV <tk>", "Relative value (pairs)"),
        ("WEI", "World Equity Indices (indices mondiaux)"),
        ("EQS", "Equity Screener (filtre value)"),
        ("ECO", "Économie / macro"),
        ("PRT", "Portfolio (livre)"),
    ]),
    ("Marché & sociétés", [
        ("MARKET / INDEX", "Vue des indices mondiaux (C&D 500, KAK 40, NKX 225...)"),
        ("TOP [region] / RANKING", "Meilleures sociétés (USA / Europe / Asia)"),
        ("MOVERS", "Plus fortes hausses / baisses du dernier pas"),
        ("COMPANY <ticker>", "Fiche société type Bloomberg (ex: COMPANY MVC)"),
        ("FA <ticker>", "États financiers : compte de résultat + bilan (N/N-1/N-2)"),
        ("SEARCH <texte>", "Rechercher une société par nom/ticker"),
        ("WATCHLIST [ADD/REMOVE <tk>]", "Suivre des valeurs"),
        ("COMPARE <t1> <t2>", "Comparer deux sociétés"),
        ("SECTOR [nom] / REGION [nom]", "Vue par secteur / région"),
        ("SCREEN", "Filtre value (P/E bas, grandes capis)"),
        ("BENCHMARK", "Votre performance vs indice régional"),
        ("CALENDAR", "Échéances : trimestre et deals"),
        ("NEWS / REG", "Actualités / cadre réglementaire"),
    ]),
    ("Portefeuille & trading", [
        ("PORTFOLIO / BOOK", "Livre de positions (valeur nette, P&L)"),
        ("BUY <ticker> <qté>", "Acheter des actions (ex: BUY MVC 100)"),
        ("SELL <ticker> <qté|ALL>", "Vendre des actions"),
        ("SHORT <ticker> <qté>", "Vente à découvert (parier à la baisse)"),
        ("COVER <ticker> <qté|ALL>", "Racheter une position courte"),
        ("MARGIN", "État de marge : equity, levier, pouvoir d'achat"),
        ("ALLOCATE <ticker> <pct>", "Ajuster une position à pct% de la valeur nette"),
        ("HEDGE [pct]", "Réduire l'exposition (bêta) du portefeuille"),
        ("REBALANCE", "Ramener les positions à poids égaux"),
        ("RESEARCH <ticker>", "Estimer une valeur intrinsèque + reco"),
        ("ALERT <ticker> <prix>", "Alerte au franchissement d'un cours"),
        ("PITCH", "Démarcher un client pour un mandat"),
    ]),
    ("Mandats clients", [
        ("MANDATES", "Voir offres et mandats en cours"),
        ("MANDATE ACCEPT <id>", "Accepter un mandat (objectif + risque)"),
        ("MANDATE DECLINE <id>", "Refuser une offre de mandat"),
    ]),
    ("Opérations & deals", [
        ("DEALS", "Lister les deals/opportunités en cours"),
        ("DEAL <id>", "Traiter un deal avant son échéance"),
    ]),
    ("Modules d'analyse", [
        ("FRONTIER", "Frontière efficiente, optimisation Sharpe"),
        ("MA", "M&A : LBO, accretion/dilution"),
        ("RISK", "VaR / CVaR, stress tests"),
        ("QUANT", "Black-Scholes, Greeks, payoff"),
        ("SHEET", "Tableur intégré (formules)"),
        ("GLOSSARY", "Glossaire des termes financiers"),
    ]),
]


class CommandsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.back_btn = widgets.Button(
            config.back_button_rect(220), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "CATALOGUE DES COMMANDES", (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Tout se pilote au clavier depuis le terminal. "
                                "Les commandes sont insensibles à la casse.",
                          (42, 76), fonts.small(), config.COL_TEXT_DIM)

        # 4 colonnes : commande puis description (1 ligne tronquée) en dessous.
        # Placement dans la colonne la moins remplie, borné au footer réservé.
        cols = 4
        gap = 20
        col_w = (config.SCREEN_WIDTH - 80 - gap * (cols - 1)) // cols
        col_x = [40 + i * (col_w + gap) for i in range(cols)]
        top = 112
        col_y = [top] * cols
        item_h = 34
        cat_h = 26

        def cat_height(items):
            return cat_h + len(items) * item_h + 14

        dfont = fonts.tiny()
        for cat, items in CATALOG:
            ci = min(range(cols), key=lambda i: col_y[i])
            x = col_x[ci]
            y = col_y[ci]
            widgets.draw_text(surf, cat.upper(), (x, y), fonts.small(bold=True), config.COL_CYAN)
            pygame.draw.line(surf, config.COL_BORDER, (x, y + 19), (x + col_w, y + 19), 1)
            y += 26
            for cmd, desc in items:
                widgets.draw_text(surf, cmd, (x, y), fonts.small(bold=True), config.COL_AMBER)
                # description sur une seule ligne, tronquée à la largeur de colonne
                s = desc
                while dfont.size(s)[0] > col_w - 14 and len(s) > 4:
                    s = s[:-2]
                if s != desc:
                    s = s[:-1] + "…"
                widgets.draw_text(surf, s, (x + 12, y + 17), dfont, config.COL_TEXT_DIM)
                y += item_h
            y += 14
            col_y[ci] = y

        self.back_btn.draw(surf)
