"""
scene_commands.py — Catalogue COMPLET des commandes du terminal.

Ouvert via COMMANDS (ou ?). Liste catégorisée, DÉFILABLE (molette / ▲▼ / PgUp-
PgDn), sans chevauchement. Cliquer une commande la COPIE : elle est pré-remplie
dans le terminal (et placée dans le presse-papiers si disponible), prête à lancer.
"""
import pygame

from core import config, unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

# Source unique de vérité (catégorie -> [(libellé, description)]). Couvre toutes
# les commandes du parseur (alias regroupés). Les triches sont volontairement
# exclues (mode main_cheat uniquement).
CATALOG = [
    ("Navigation & système", [
        ("HELP", "Aide rapide (commandes essentielles)"),
        ("COMMANDS / ?", "Ce catalogue complet"),
        ("STATUS", "Votre situation : grade, cash, réputation, temps"),
        ("ADV / NEXT / T", "Avancer le temps de 5 jours (un pas de marché)"),
        ("MENU / ESC", "Retour au menu principal"),
        ("SAVE", "Sauvegarde manuelle (désactivée en hardcore)"),
        ("SAVES / LOAD", "Gestion des sauvegardes (slots)"),
    ]),
    ("Carrière & progression", [
        ("MISSION", "Jouer la mission du grade (réputation + honoraire)"),
        ("EVAL", "Examen de promotion (critères combinés requis)"),
        ("CAREER", "Tableau de bord : roadmap, objectifs, stats, journal"),
        ("ROADMAP / OBJECTIVES", "Raccourcis vers l'écran carrière"),
        ("HISTORY / JOURNAL", "Journal de carrière"),
        ("TRACK", "Choisir / voir sa voie de spécialisation"),
        ("CERT", "Certifications CFA / FRM / CQF (boost de carrière)"),
    ]),
    ("Monde vivant", [
        ("INBOX / MAIL", "Messagerie (manager, clients, conformité, desk)"),
        ("DECIDE / DILEMMA", "Trancher un dilemme en attente (éthique/régl.)"),
        ("RIVALS", "Rivaux : classement, némésis, dernières actions"),
        ("MANDATES", "Voir offres et mandats clients en cours"),
        ("MANDATE ACCEPT <id>", "Accepter un mandat (objectif + risque)"),
        ("MANDATE DECLINE <id>", "Refuser une offre de mandat"),
        ("DEALS", "Lister les deals / opportunités en cours"),
        ("DEAL <id>", "Traiter un deal avant son échéance"),
        ("CALENDAR / CAL", "Échéances : trimestre et deals"),
        ("NEWS", "Actualités du continent"),
        ("REG", "Cadre réglementaire de la région"),
    ]),
    ("Savoir & macro", [
        ("LEARN / ACADEMY", "Académie : leçons (DCF, Sharpe, VaR, options…)"),
        ("TUTO / GUIDE", "Tutoriels illustrés : acheter/vendre, bonds, futures…"),
        ("GLOSSARY", "Glossaire des termes financiers"),
        ("DEFINE <terme>", "Définition rapide. Ex : DEFINE WACC"),
        ("ECO / MACRO", "Indicateurs : taux, inflation, croissance, chômage"),
    ]),
    ("Marché & sociétés", [
        ("MARKET / WEI", "Indices mondiaux (C&D 500, KAK 40, NKX 225…)"),
        ("TOP [region] / RANKING", "Meilleures sociétés (USA / Europe / Asia…)"),
        ("MOVERS", "Plus fortes hausses / baisses du dernier pas"),
        ("COMPANY / DES <tk>", "Fiche société type Bloomberg. Ex : DES MVC"),
        ("FA <tk>", "États financiers : résultat + bilan (N/N-1/N-2)"),
        ("RV <tk>", "Valeur relative : multiples vs pairs du secteur"),
        ("SEARCH <texte>", "Rechercher une société par nom ou ticker"),
        ("SECTOR [nom]", "Vue par secteur"),
        ("REGION [nom]", "Vue par région"),
        ("SCREEN / EQS", "Filtre value (P/E bas, grandes capis)"),
        ("BENCHMARK", "Votre performance vs indice régional"),
        ("WATCHLIST <ADD/REMOVE> <tk>", "Suivre des valeurs"),
        ("COMPARE <t1> <t2>", "Comparer deux sociétés (multiples)"),
        ("RESEARCH <tk>", "Valeur intrinsèque + reco analyste"),
        ("ALERT <tk> <prix>", "Alerte au franchissement d'un cours"),
        ("ALERTS", "Lister vos alertes de cours"),
    ]),
    ("Graphes analytiques (5 ans d'historique dès le jour 1)", [
        ("GP <tk>", "Ligne de prix + moyennes mobiles MM20/MM50"),
        ("GPC <tk>", "Chandeliers japonais (OHLC agrégé)"),
        ("GPO <tk>", "Barres OHLC"),
        ("GPCH <tk>", "Variation % depuis une référence"),
        ("COMP <tk> <tk>…", "Performances comparées (base 0 %)"),
        ("HS <tk> <tk>", "Spread / ratio entre deux actifs"),
        ("HVOL <tk>", "Volatilité historique annualisée glissante"),
        ("BETA <tk>", "Nuage de points + régression vs indice régional"),
        ("CORR <tk>…", "Matrice de corrélation (défaut : vos positions)"),
        ("GEG", "Indicateurs macro superposés (taux, inflation, PIB…)"),
        ("GC / YCRV", "Courbe des taux (maturité × rendement)"),
    ]),
    ("Portefeuille & trading", [
        ("PORTFOLIO / BOOK / PRT", "Livre de positions (valeur nette, P&L)"),
        ("PA / ANALYSE", "Analyse détaillée : poids, risque, corrél., frontière"),
        ("BUY / LONG <tk> <qté>", "Acheter des actions (position longue)"),
        ("SELL <tk> <qté|ALL>", "Vendre des actions"),
        ("SHORT <tk> <qté>", "Vente à découvert (parier à la baisse)"),
        ("COVER <tk> <qté|ALL>", "Racheter une position courte"),
        ("MARGIN", "État de marge : equity, levier, pouvoir d'achat"),
        ("ALLOCATE <tk> <pct>", "Ajuster une position à pct% de la valeur nette"),
        ("HEDGE [pct]", "Réduire l'exposition (bêta) du portefeuille"),
        ("PROTECT", "Acheter un put protecteur sur l'indice (couverture par options)"),
        ("REBALANCE", "Ramener les positions à poids égaux"),
        ("FRONTIER", "Frontière efficiente, optimisation Sharpe"),
        ("PITCH", "Démarcher un client pour un mandat"),
    ]),
    ("Classes d'actifs", [
        ("BONDS", "Obligations souveraines & corporate : YTM, duration, prix"),
        ("BUYBOND / SELLBOND <id> <qté>", "Acheter / vendre des obligations"),
        ("GOV / PAYS", "Pays : note souveraine, dette, stabilité, histoire, bonds"),
        ("CMDTY", "Matières premières : futures, contango/backwardation"),
        ("BUYCMDTY / SELLCMDTY <id> <qté>", "Trader des commodities"),
        ("CRYPTO", "Crypto-actifs & stablecoin (volatil, depeg)"),
        ("BUYCRYPTO / SELLCRYPTO <id> <qté>", "Trader des crypto-actifs"),
        ("STRUCT", "Produits structurés (capital garanti, autocallable…)"),
        ("CREDIT", "Desk crédit : tranches de titrisation & waterfall"),
        ("ALM", "Gestion actif-passif : gaps de taux, NII, ΔEVE"),
        ("OPTIONS / OPTION", "Desk d'options vanille (calls/puts) sur une action"),
        ("IPO / IPOS", "Desk d'IPO : souscrire à une introduction en bourse"),
    ]),
    ("Modules d'analyse", [
        ("MA", "M&A : LBO, accretion / dilution"),
        ("RISK", "VaR / CVaR, stress tests"),
        ("QUANT", "Black-Scholes, Greeks, payoff"),
        ("SHEET / TABLEUR", "Tableur intégré (formules)"),
    ]),
]


def _copy_text(label):
    """Texte à pré-remplir/copier depuis un libellé : commande sans placeholders.
    Ex : 'BUY <tk> <qté>' -> 'BUY ' ; 'DES / FA <tk>' -> 'DES ' ; 'MARGIN' -> 'MARGIN'."""
    base = label.split("/")[0].strip()        # 1er alias
    cut = base.split("<")[0].strip()          # retire les placeholders
    has_arg = "<" in label
    return (cut + " ") if has_arg else cut


def _label_lock_grade(label, player):
    """Grade minimal requis pour utiliser cette commande, ou None si déjà débloquée.
    Compare chaque alias du libellé (avant les placeholders) aux features de unlocks.py."""
    base = label.split("<")[0].strip()
    best = None
    for alias in base.split("/"):
        words = alias.strip().split()
        if not words:
            continue
        feat = unlocks.CMD_FEATURE.get(words[0].upper())
        if feat and not unlocks.unlocked(player, feat):
            g = unlocks.required_grade(feat)
            best = g if best is None else max(best, g)
    return best


def _try_clipboard(text):
    """Copie best-effort dans le presse-papiers système (silencieux si indispo)."""
    try:
        import pygame.scrap as scrap
        if not scrap.get_init():
            scrap.init()
        scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
    except Exception:
        pass


class CommandsScene(Scene):
    HEAD_H = 26          # hauteur d'un en-tête de catégorie
    ITEM_H = 36          # hauteur d'une commande (libellé + description)
    CAT_GAP = 14         # espace après une catégorie
    COLS = 2

    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.scroll = 0
        self.search = ""
        self._search_clear_rect = None
        self._t = 0.0
        self._hit = []                 # [(rect, label)] pour le clic (coord. écran)
        self.back_btn = widgets.Button(
            config.back_button_rect(220), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._layout()

    # ------------------------------------------------------------- layout
    def _search_rect(self):
        return pygame.Rect(40, 100, 320, 24)

    def _viewport(self):
        top = 138
        return pygame.Rect(40, top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - top)

    def _filtered_catalog(self):
        q = self.search.strip().lower()
        if not q:
            return CATALOG
        out = []
        for cat, items in CATALOG:
            kept = [(label, desc) for label, desc in items
                    if q in label.lower() or q in desc.lower()]
            if kept:
                out.append((cat, kept))
        return out

    def _layout(self):
        """Répartit les catégories (filtrées par recherche) en COLS colonnes équilibrées (greedy)."""
        self._col_w = (self._viewport().w - 24 * (self.COLS - 1)) // self.COLS
        col_blocks = [[] for _ in range(self.COLS)]
        col_h = [0] * self.COLS
        for cat, items in self._filtered_catalog():
            h = self.HEAD_H + len(items) * self.ITEM_H + self.CAT_GAP
            ci = min(range(self.COLS), key=lambda i: col_h[i])
            col_blocks[ci].append((cat, items))
            col_h[ci] += h
        self._col_blocks = col_blocks
        self._content_h = max(col_h) if col_h else 0

    def _max_scroll(self):
        return max(0, self._content_h - self._viewport().h)

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    self._layout()
                    return
                self.app.scenes.go(self.return_to)
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                self.scroll = 0
                self._layout()
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 240)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll(), self.scroll + 240)
            elif event.key == pygame.K_HOME:
                self.scroll = 0
            elif event.key == pygame.K_END:
                self.scroll = self._max_scroll()
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                self._layout()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scroll = max(0, self.scroll - 60)
            elif event.button == 5:
                self.scroll = min(self._max_scroll(), self.scroll + 60)
            elif event.button == 1:
                if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                    self.search = ""
                    self.scroll = 0
                    self._layout()
                    return
                for rect, label in self._hit:
                    if rect.collidepoint(event.pos):
                        self._copy(label)
                        return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)

    def _copy(self, label):
        text = _copy_text(label)
        self.app.pending_input = text          # pré-rempli dans le terminal au retour
        _try_clipboard(text)
        self.app.notify(f"Copié : {text.strip()} — collé dans le terminal", "good")

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # -------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "CATALOGUE DES COMMANDES", (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Cliquez une commande pour la copier dans le terminal · "
                                "molette / ▲▼ PgUp-PgDn pour défiler · 🔒 = verrouillée à votre grade.",
                          (42, 76), fonts.small(), config.COL_TEXT_DIM)

        # ---- recherche ----
        search_rect = self._search_rect()
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.search else config.COL_BORDER,
                          search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else "Rechercher une commande…"
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y,
                                                   22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        p = self.app.gs.player
        vp = self._viewport()
        self._hit = []
        prev_clip = surf.get_clip()
        surf.set_clip(vp)
        mouse = pygame.mouse.get_pos()
        if not any(blocks for blocks in self._col_blocks):
            widgets.draw_text(surf, "Aucune commande ne correspond à cette recherche.",
                              (vp.x, vp.y), fonts.small(), config.COL_TEXT_DIM)
        for ci, blocks in enumerate(self._col_blocks):
            x = vp.x + ci * (self._col_w + 24)
            y = vp.y - self.scroll
            for cat, items in blocks:
                widgets.draw_text(surf, widgets.fit_text(cat.upper(), fonts.small(bold=True),
                                                         self._col_w),
                                  (x, y), fonts.small(bold=True), config.COL_CYAN)
                pygame.draw.line(surf, config.COL_BORDER, (x, y + 19), (x + self._col_w, y + 19), 1)
                y += self.HEAD_H
                for label, desc in items:
                    lock_g = _label_lock_grade(label, p)
                    row = pygame.Rect(x - 4, y - 2, self._col_w + 8, self.ITEM_H - 2)
                    hovered = row.collidepoint(mouse) and vp.collidepoint(mouse)
                    if hovered:
                        pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=4)
                    if vp.top - self.ITEM_H < y < vp.bottom:
                        self._hit.append((row.copy(), label))
                        label_col = config.COL_TEXT_DIM if lock_g is not None else (
                            config.COL_WHITE if hovered else config.COL_AMBER)
                        badge = f"🔒 {config.GRADES[lock_g]}" if lock_g is not None else ""
                        avail_w = self._col_w - 8 - (fonts.tiny().size(badge)[0] + 6 if badge else 0)
                        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(bold=True),
                                                                 avail_w),
                                          (x, y), fonts.small(bold=True), label_col)
                        if badge:
                            widgets.draw_text(surf, badge, (x + self._col_w - 4, y + 2),
                                              fonts.tiny(bold=True), config.COL_AMBER_DIM,
                                              align="right")
                        widgets.draw_text(surf, widgets.fit_text(desc, fonts.tiny(),
                                                                 self._col_w - 12),
                                          (x + 12, y + 17), fonts.tiny(), config.COL_TEXT_DIM)
                    y += self.ITEM_H
                y += self.CAT_GAP
        surf.set_clip(prev_clip)

        # barre de défilement
        self._draw_scrollbar(surf, vp)
        self.back_btn.draw(surf)

    def _draw_scrollbar(self, surf, vp):
        ms = self._max_scroll()
        if ms <= 0:
            return
        track = pygame.Rect(vp.right + 6, vp.y, 6, vp.h)
        pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
        frac = vp.h / self._content_h
        bar_h = max(24, int(vp.h * frac))
        bar_y = vp.y + int((vp.h - bar_h) * (self.scroll / ms))
        pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)
