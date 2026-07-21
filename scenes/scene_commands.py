"""
scene_commands.py — Catalogue COMPLET des commandes du terminal.

Ouvert via COMMANDS (ou ?). Liste catégorisée, DÉFILABLE (molette / ▲▼ / PgUp-
PgDn), sans chevauchement. Cliquer une commande la COPIE : elle est pré-remplie
dans le terminal (et placée dans le presse-papiers si disponible), prête à lancer.
"""
import pygame

from core import config, unlocks
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr

# Source unique de vérité (catégorie -> [(libellé, description)]). Couvre toutes
# les commandes du parseur (alias regroupés). Les triches sont volontairement
# exclues (mode main_cheat uniquement).
CATALOG = [
    (("Navigation & système", "Navigation & system"), [
        ("HELP", ("Aide rapide (commandes essentielles)", "Quick help (essential commands)")),
        ("COMMANDS / ?", ("Ce catalogue complet", "This full catalog")),
        ("STATUS", ("Votre situation : grade, cash, réputation, temps", "Your status: grade, cash, reputation, time")),
        ("MENU / ESC", ("Retour au menu principal", "Back to the main menu")),
        ("SETTINGS / REGLAGES", ("Réglages : affichage (plein écran), son, langue, vitesse", "Settings: display (fullscreen), sound, language, speed")),
        ("SAVE", ("Sauvegarde manuelle (désactivée en hardcore)", "Manual save (disabled in hardcore)")),
        ("SAVES / LOAD", ("Gestion des sauvegardes (slots)", "Save management (slots)")),
    ]),
    (("Carrière & progression", "Career & progression"), [
        ("MISSION", ("Jouer la mission du grade (réputation + honoraire)", "Play the grade mission (reputation + fee)")),
        ("EVAL", ("Examen de promotion (critères combinés requis)", "Promotion exam (combined criteria required)")),
        ("CAREER", ("Tableau de bord : roadmap, objectifs, stats, journal", "Dashboard: roadmap, objectives, stats, journal")),
        ("ROADMAP / OBJECTIVES", ("Raccourcis vers l'écran carrière", "Shortcuts to the career screen")),
        ("HISTORY / JOURNAL", ("Journal de carrière", "Career journal")),
        ("TRACK", ("Choisir / voir sa voie de spécialisation", "Choose / view your specialization track")),
        ("RECONVERT [voie]", ("Changer de voie après le choix initial (coût cash + rodage)", "Change track after the initial choice (cash cost + ramp-up)")),
        ("ARCHETYPE", ("Philosophie de run choisie au départ : avantages et coûts", "Run philosophy chosen at start: perks and costs")),
        ("CERT", ("Certifications CFA / FRM / CQF (boost de carrière)", "CFA / FRM / CQF certifications (career boost)")),
        ("LEGACY", ("Objectifs de légende : ambitions de carrière long terme", "Legend objectives: long-term career ambitions")),
    ]),
    (("Monde vivant", "Living world"), [
        ("INBOX / MAIL", ("Messagerie (manager, clients, conformité, desk)", "Mailbox (manager, clients, compliance, desk)")),
        ("DECIDE / DILEMMA", ("Trancher un dilemme en attente (éthique/régl.)", "Settle a pending dilemma (ethics/reg.)")),
        ("RIVALS", ("Rivaux : classement, némésis, dernières actions", "Rivals: ranking, nemesis, latest moves")),
        ("RECLAIM [ticker]", ("Contre-offre sur une cible M&A raflée par un rival", "Counter-bid on an M&A target grabbed by a rival")),
        ("MANDATES", ("Voir offres et mandats clients en cours", "View active client offers and mandates")),
        ("MANDATE ACCEPT <id>", ("Accepter un mandat (objectif + risque)", "Accept a mandate (objective + risk)")),
        ("MANDATE DECLINE <id>", ("Refuser une offre de mandat", "Decline a mandate offer")),
        ("DEALS", ("Lister les deals / opportunités en cours", "List active deals / opportunities")),
        ("DEAL <id>", ("Traiter un deal avant son échéance", "Handle a deal before its deadline")),
        ("CALENDAR / CAL", ("Échéances : trimestre et deals", "Deadlines: quarter and deals")),
        ("NEWS", ("Actualités du continent", "Continent news")),
        ("REG", ("Cadre réglementaire de la région", "Regulatory framework of the region")),
    ]),
    (("Savoir & macro", "Knowledge & macro"), [
        ("LEARN / ACADEMY", ("Académie : leçons (DCF, Sharpe, VaR, options…)", "Academy: lessons (DCF, Sharpe, VaR, options…)")),
        ("TUTO / GUIDE", ("Tutoriels illustrés : acheter/vendre, bonds, futures…", "Illustrated tutorials: buy/sell, bonds, futures…")),
        ("GLOSSARY", ("Glossaire des termes financiers", "Glossary of financial terms")),
        ("DEFINE <terme>", ("Définition rapide. Ex : DEFINE WACC", "Quick definition. E.g.: DEFINE WACC")),
        ("ECO / MACRO", ("Indicateurs : taux, inflation, croissance, chômage", "Indicators: rates, inflation, growth, unemployment")),
    ]),
    (("Marché & sociétés", "Market & companies"), [
        ("MARKET / WEI", ("Indices mondiaux (C&D 500, KAK 40, NKX 225…)", "World indices (C&D 500, KAK 40, NKX 225…)")),
        ("WALL", ("Mur de trading plein écran : mosaïque d'indices + positions ouvertes en direct", "Full-screen trading wall: index mosaic + live open positions")),
        ("HOURS", ("Statut des sessions de cotation Asie/Europe/Amériques (ouvert/fermé, "
                  "heure de réouverture) — le trading actions est bloqué hors session",
                  "Trading session status Asia/Europe/Americas (open/closed, "
                  "reopening time) — equity trading is blocked out of session")),
        ("TENSION", ("Arc de tension du marché : phase, niveau, crises actives", "Market tension arc: phase, level, active crises")),
        ("TOP [region] / RANKING", ("Meilleures sociétés (USA / Europe / Asia…)", "Best companies (USA / Europe / Asia…)")),
        ("MOVERS", ("Plus fortes hausses / baisses du dernier pas", "Biggest gainers / losers of the last step")),
        ("COMPANY / DES <tk>", ("Fiche société type Bloomberg. Ex : DES MVC", "Bloomberg-style company sheet. E.g.: DES MVC")),
        ("FA <tk>", ("États financiers : résultat + bilan (N/N-1/N-2)", "Financial statements: income + balance sheet (Y/Y-1/Y-2)")),
        ("RV <tk>", ("Valeur relative : multiples vs pairs du secteur", "Relative value: multiples vs sector peers")),
        ("SHOP", ("Boutique unifiée : acheter actions, ETF, obligations, commodities, crypto…", "Unified shop: buy stocks, ETFs, bonds, commodities, crypto…")),
        ("SEARCH <texte>", ("Rechercher une société par nom ou ticker", "Search a company by name or ticker")),
        ("SECTOR [nom]", ("Vue par secteur", "View by sector")),
        ("REGION [nom]", ("Vue par région", "View by region")),
        ("SCREEN [clé=valeur...]", ("Filtre actions (region/sector/pe_max/beta_max/growth_min…)", "Stock screener (region/sector/pe_max/beta_max/growth_min…)")),
        ("SCREEN ETF [clé=valeur...]", ("Filtre ETF (category/region/expense_max/rating_min…)", "ETF screener (category/region/expense_max/rating_min…)")),
        ("BENCHMARK", ("Votre performance vs indice régional", "Your performance vs regional index")),
        ("WATCHLIST <ADD/REMOVE> <tk>", ("Suivre des valeurs", "Track securities")),
        ("COMPARE <t1> <t2> [t3] [t4]", ("Comparer jusqu'à 4 sociétés OU ETF (multiples)", "Compare up to 4 companies OR ETFs (multiples)")),
        ("RESEARCH <tk>", ("Valeur intrinsèque + reco analyste", "Intrinsic value + analyst reco")),
        ("ALERT <tk> <prix>", ("Alerte au franchissement d'un cours", "Alert when a price is crossed")),
        ("ALERTS", ("Lister vos alertes de cours", "List your price alerts")),
        ("CRITERIA ADD <stock|etf> [clé=valeur...]", ("Sauvegarder un critère de recherche (idées)", "Save a screening criterion (ideas)")),
        ("CRITERIA LIST / REMOVE <id>", ("Lister / supprimer vos critères sauvegardés", "List / remove your saved criteria")),
        ("IDEAS [id]", ("Remonte les actifs correspondant à vos critères sauvegardés", "Surfaces assets matching your saved criteria")),
        ("TRADES [classe]", ("Journal de trading : date, taille, P&L, contexte macro", "Trading journal: date, size, P&L, macro context")),
        ("NOTE <id> <texte>", ("Annoter une entrée du journal de trading", "Annotate a trading journal entry")),
        ("JSTATS [regime|reason]", ("Bilan du journal : P&L réalisé par régime/raison", "Journal summary: realized P&L by regime/reason")),
    ]),
    (("Graphes analytiques (5 ans d'historique dès le jour 1)", "Analytical charts (5 years of history from day 1)"), [
        ("GP <tk>", ("Ligne de prix + moyennes mobiles MM20/MM50", "Price line + moving averages MA20/MA50")),
        ("GPC <tk>", ("Chandeliers japonais (OHLC agrégé)", "Japanese candlesticks (aggregated OHLC)")),
        ("GPO <tk>", ("Barres OHLC", "OHLC bars")),
        ("GPCH <tk>", ("Variation % depuis une référence", "% change from a reference")),
        ("COMP <tk> <tk>…", ("Performances comparées (base 0 %)", "Compared performance (base 0%)")),
        ("HS <tk> <tk>", ("Spread / ratio entre deux actifs", "Spread / ratio between two assets")),
        ("HVOL <tk>", ("Volatilité historique annualisée glissante", "Rolling annualized historical volatility")),
        ("BETA <tk>", ("Nuage de points + régression vs indice régional", "Scatter plot + regression vs regional index")),
        ("CORR <tk>…", ("Matrice de corrélation (défaut : vos positions)", "Correlation matrix (default: your positions)")),
        ("GEG", ("Indicateurs macro superposés (taux, inflation, PIB…)", "Overlaid macro indicators (rates, inflation, GDP…)")),
        ("GC / YCRV", ("Courbe des taux (maturité × rendement)", "Yield curve (maturity × yield)")),
    ]),
    (("Portefeuille & trading", "Portfolio & trading"), [
        ("PORTFOLIO / BOOK / PRT", ("Livre de positions (valeur nette, P&L)", "Book of positions (net worth, P&L)")),
        ("PA / ANALYSE", ("Analyse détaillée : poids, risque, corrél., frontière", "Detailed analysis: weights, risk, corr., frontier")),
        ("ATTR / ATTRIBUTION", ("Attribution de performance : secteur, région, style, sélection, timing", "Performance attribution: sector, region, style, selection, timing")),
        ("BUY / LONG <tk> <qté>", ("Acheter des actions (position longue)", "Buy shares (long position)")),
        ("SELL <tk> <qté|ALL>", ("Vendre des actions", "Sell shares")),
        ("SHORT <tk> <qté>", ("Vente à découvert (parier à la baisse)", "Short selling (bet on a fall)")),
        ("COVER <tk> <qté|ALL>", ("Racheter une position courte", "Buy back a short position")),
        ("MARGIN", ("État de marge : equity, levier, pouvoir d'achat", "Margin status: equity, leverage, buying power")),
        ("ALLOCATE <tk> <pct>", ("Ajuster une position à pct% de la valeur nette", "Adjust a position to pct% of net worth")),
        ("HEDGE [pct]", ("Réduire l'exposition (bêta) du portefeuille", "Reduce the portfolio's exposure (beta)")),
        ("PROTECT", ("Acheter un put protecteur sur l'indice (couverture par options)", "Buy a protective put on the index (options hedge)")),
        ("REBALANCE", ("Ramener les positions à poids égaux", "Bring positions back to equal weights")),
        ("FRONTIER", ("Frontière efficiente, optimisation Sharpe", "Efficient frontier, Sharpe optimization")),
        ("PITCH", ("Démarcher un client pour un mandat", "Prospect a client for a mandate")),
    ]),
    (("Classes d'actifs", "Asset classes"), [
        ("BONDS", ("Obligations souveraines & corporate : YTM, duration, prix", "Sovereign & corporate bonds: YTM, duration, price")),
        ("BUYBOND / SELLBOND <id> <qté>", ("Acheter / vendre des obligations", "Buy / sell bonds")),
        ("GOV / PAYS", ("Pays : note souveraine, dette, stabilité, histoire, bonds", "Countries: sovereign rating, debt, stability, history, bonds")),
        ("CMDTY", ("Matières premières : futures, contango/backwardation", "Commodities: futures, contango/backwardation")),
        ("BUYCMDTY / SELLCMDTY <id> <qté>", ("Trader des commodities", "Trade commodities")),
        ("CRYPTO", ("Crypto-actifs & stablecoin (volatil, depeg)", "Crypto-assets & stablecoin (volatile, depeg)")),
        ("BUYCRYPTO / SELLCRYPTO <id> <qté>", ("Trader des crypto-actifs", "Trade crypto-assets")),
        ("STRUCT", ("Produits structurés (capital garanti, autocallable…)", "Structured products (capital-guaranteed, autocallable…)")),
        ("CREDIT", ("Desk crédit : tranches de titrisation & waterfall", "Credit desk: securitization tranches & waterfall")),
        ("ALM", ("Gestion actif-passif : gaps de taux, NII, ΔEVE", "Asset-liability management: rate gaps, NII, ΔEVE")),
        ("OPTIONS / OPTION", ("Desk d'options vanille (calls/puts) sur une action", "Vanilla options desk (calls/puts) on a stock")),
        ("IPO / IPOS", ("Desk d'IPO : souscrire à une introduction en bourse", "IPO desk: subscribe to a stock market listing")),
    ]),
    (("Modules d'analyse", "Analysis modules"), [
        ("MA", ("M&A : LBO, accretion / dilution", "M&A: LBO, accretion / dilution")),
        ("RISK", ("VaR / CVaR, stress tests", "VaR / CVaR, stress tests")),
        ("QUANT", ("Black-Scholes, Greeks, payoff", "Black-Scholes, Greeks, payoff")),
        ("SHEET / TABLEUR", ("Tableur intégré (formules)", "Built-in spreadsheet (formulas)")),
    ]),
]


def _copy_text(label):
    """Texte à pré-remplir/copier depuis un libellé : commande sans placeholders.
    Ex : 'BUY <tk> <qté>' -> 'BUY ' ; 'DES / FA <tk>' -> 'DES ' ; 'MARGIN' -> 'MARGIN'."""
    base = label.split("/")[0].strip()        # 1er alias
    cut = base.split("<")[0].strip()          # retire les placeholders
    has_arg = "<" in label
    return (cut + " ") if has_arg else cut


def _split_canonical(label):
    """Découpe un libellé multi-alias en (nom canonique + placeholders, synonymes).
    Ex : 'BUY / LONG <tk> <qté>' -> ('BUY <tk> <qté>', 'LONG'). Un seul alias
    (pas de '/') renvoie le libellé tel quel et une chaîne de synonymes vide."""
    if "<" in label:
        base, _, args = label.partition("<")
        args = "<" + args
    else:
        base, args = label, ""
    aliases = [a.strip() for a in base.split("/") if a.strip()]
    if len(aliases) <= 1:
        return label, ""
    canonical = aliases[0] + (" " + args if args else "")
    return canonical, ", ".join(aliases[1:])


def all_command_tokens():
    """Liste plate de tous les tokens de commande valides (alias compris,
    placeholders <...> exclus), pour la suggestion « vouliez-vous dire ? »
    sur une commande inconnue."""
    tokens = []
    for _title, items in CATALOG:
        for label, _desc in items:
            base = label.split("<")[0].strip()
            tokens.extend(a.strip() for a in base.split("/") if a.strip())
    return tokens


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
            g = unlocks.effective_required_grade(player, feat)
            best = g if best is None else max(best, g)
    return best


def _try_clipboard(text):
    """Copie best-effort dans le presse-papiers système (silencieux si indispo)."""
    from core import clipboard
    clipboard.copy(text)


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
                    if q in label.lower() or q in _L(*desc).lower()]
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
                self.app.scenes.back(self.return_to)
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
            self.app.scenes.back(self.return_to)

    def _copy(self, label):
        text = _copy_text(label)
        self.app.pending_input = text          # pré-rempli dans le terminal au retour
        _try_clipboard(text)
        self.app.notify(_L(f"Copié : {text.strip()} — collé dans le terminal", f"Copied: {text.strip()} — pasted into the terminal"), "good")

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # -------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, _L("CATALOGUE DES COMMANDES", "COMMAND CATALOG"), (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L("Cliquez une commande pour la copier dans le terminal · "
                                "molette / ▲▼ PgUp-PgDn pour défiler · [verr.] = verrouillée à votre grade.",
                                "Click a command to copy it into the terminal · "
                                "wheel / ▲▼ PgUp-PgDn to scroll · [locked] = locked at your grade."),
                          (42, 76), fonts.small(), config.COL_TEXT_DIM)

        # ---- recherche ----
        search_rect = self._search_rect()
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + _L("Rechercher une commande…", "Search a command…"))
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
            widgets.draw_text(surf, _L("Aucune commande ne correspond à cette recherche.", "No command matches this search."),
                              (vp.x, vp.y), fonts.small(), config.COL_TEXT_DIM)
        for ci, blocks in enumerate(self._col_blocks):
            x = vp.x + ci * (self._col_w + 24)
            y = vp.y - self.scroll
            for cat, items in blocks:
                widgets.draw_text(surf, widgets.fit_text(_L(*cat).upper(), fonts.small(bold=True),
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
                            config.COL_CYAN if hovered else config.COL_AMBER)
                        badge = (_L("[verr.]", "[locked]") + f" {config.GRADES[lock_g]}") if lock_g is not None else ""
                        avail_w = self._col_w - 8 - (fonts.tiny().size(badge)[0] + 6 if badge else 0)
                        canonical, synonyms = _split_canonical(label)
                        name_rect = widgets.draw_text(surf, widgets.fit_text(canonical, fonts.small(bold=True),
                                                                             avail_w),
                                                       (x, y), fonts.small(bold=True), label_col)
                        syn_w = avail_w - name_rect.w
                        if synonyms and syn_w > 20:
                            widgets.draw_text(surf, widgets.fit_text(f" ≡ {synonyms}", fonts.tiny(), syn_w),
                                              (name_rect.right, y + 3), fonts.tiny(), config.COL_TEXT_DIM)
                        if badge:
                            widgets.draw_text(surf, badge, (x + self._col_w - 4, y + 2),
                                              fonts.tiny(bold=True), config.COL_AMBER_DIM,
                                              align="right")
                        widgets.draw_text(surf, widgets.fit_text(_L(*desc), fonts.tiny(),
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

        # clic-glisser (cf. ui/widgets.py::draw_scrollbar pour la même logique
        # appliquée aux autres écrans à liste défilante) : sans ça la barre a
        # l'air draggable mais seule la molette défile vraiment.
        grab_zone = track.inflate(10, 0)
        mx, my = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0] and grab_zone.collidepoint(mx, my):
            rel = (my - bar_h // 2 - vp.y) / max(1, vp.h - bar_h)
            self.scroll = max(0, min(ms, int(rel * ms)))
