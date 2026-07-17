"""
unlock_briefs.py — Contenu du GUIDE DE DÉMARRAGE et des fiches « NOUVEAUTÉS »
de promotion (logique pure, sans pygame).

Deux besoins couverts :

1. `INTRO_PAGES` : le guide multi-pages affiché au tout début d'une partie
   (carte modale du bureau, `DesktopScene`). Il explique la BOUCLE CENTRALE
   du jeu — faire des missions pour gagner réputation et cash, remplir les
   critères, passer l'examen, être promu, débloquer de nouveaux outils — puis
   le fonctionnement du poste de travail. Objectif : qu'un nouveau joueur
   sache exactement QUOI faire et POURQUOI en refermant le guide.

2. `FEATURE_BRIEFS` : une fiche détaillée par fonctionnalité déblocable
   (core/unlocks.py::UNLOCKS) — ce que c'est, comment y accéder, ce que ça
   apporte, les premiers pas concrets. Affichées par la carte « NOUVEAUTÉS »
   du bureau à chaque promotion (une page par fonctionnalité débloquée).

Toute la prose est FR/EN (tuples), résolue par `_L` selon la langue courante.
"""


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


# ---------------------------------------------------------------------------
# Guide de démarrage (multi-pages)
# ---------------------------------------------------------------------------
# Chaque page : {"title": (fr, en), "body": [(fr, en), ...]} — chaque entrée
# du corps est un PARAGRAPHE (retour à la ligne automatique au rendu).
INTRO_PAGES = [
    {
        "title": ("Bienvenue dans votre carrière", "Welcome to your career"),
        "body": [
            ("Vous démarrez tout en bas de l'échelle d'une grande banque "
             "d'investissement : stagiaire. Votre objectif : gravir les 12 grades "
             "jusqu'à Partner, en bâtissant deux choses — votre RÉPUTATION et "
             "votre FORTUNE.",
             "You start at the very bottom of a large investment bank: intern. "
             "Your goal: climb the 12 grades to Partner, building two things — "
             "your REPUTATION and your WEALTH."),
            ("Tout se passe depuis ce POSTE DE TRAVAIL : chaque icône ouvre une "
             "application dans une fenêtre (comme un vrai ordinateur). Le marché "
             "vit en continu pendant que vous travaillez : 320 sociétés, des "
             "indices, des crises, des actualités.",
             "Everything happens from this WORKSTATION: each icon opens an "
             "application in a window (like a real computer). The market lives "
             "continuously while you work: 320 companies, indices, crises, news."),
            ("Ce guide tient en 6 pages. Il vous explique exactement quoi faire "
             "pour progresser — prenez une minute, ça change tout.",
             "This guide is 6 pages long. It explains exactly what to do to "
             "progress — take a minute, it changes everything."),
        ],
    },
    {
        "title": ("La boucle centrale : les MISSIONS", "The core loop: MISSIONS"),
        "body": [
            ("Votre levier de progression n° 1, ce sont les MISSIONS : le travail "
             "concret de votre grade (analyses, notes de synthèse, décisions). "
             "Chaque mission terminée rapporte de la RÉPUTATION et du CASH.",
             "Your #1 progression lever is MISSIONS: the concrete work of your "
             "grade (analyses, briefing notes, decisions). Every completed "
             "mission earns REPUTATION and CASH."),
            ("La réputation est LA monnaie de votre carrière : c'est elle qui "
             "conditionne votre promotion. Sans missions, pas de réputation ; "
             "sans réputation, pas d'examen ; sans examen, pas de grade suivant.",
             "Reputation is THE currency of your career: it gates your "
             "promotion. No missions, no reputation; no reputation, no exam; "
             "no exam, no next grade."),
            ("→ Où : icône MISSION sur le bureau (ou tapez MISSION dans le "
             "Terminal). Faites-en une routine : chaque trimestre a un objectif "
             "de missions à remplir.",
             "→ Where: the MISSION icon on the desktop (or type MISSION in the "
             "Terminal). Make it a routine: each quarter has a missions target."),
        ],
    },
    {
        "title": ("L'examen et la promotion", "The exam and promotion"),
        "body": [
            ("Quand votre réputation atteint le seuil requis ET que les critères "
             "du grade sont remplis (missions du trimestre, deals conclus, "
             "ancienneté...), vous pouvez passer l'EXAMEN DE PROMOTION : un vrai "
             "entretien technique (calculs, QCM, lecture de graphes).",
             "When your reputation reaches the required threshold AND the "
             "grade's criteria are met (quarterly missions, closed deals, "
             "seniority...), you can take the PROMOTION EXAM: a real technical "
             "interview (calculations, MCQs, chart reading)."),
            ("Réussite = grade suivant, salaire plus élevé, réputation bonus — "
             "et surtout de NOUVEAUX OUTILS : trading, deals, mandats, produits "
             "dérivés... À chaque promotion, un écran « Nouveautés » vous "
             "expliquera précisément ce qui vient de s'ouvrir.",
             "Success = next grade, higher salary, bonus reputation — and above "
             "all NEW TOOLS: trading, deals, mandates, derivatives... At every "
             "promotion, a “What's new” screen will explain exactly what just "
             "opened up."),
            ("→ Où : CARRIÈRE (menu Apps) montre votre feuille de route et ce "
             "qui vous manque ; EXAM/CERTIF sur le bureau lance l'examen quand "
             "vous êtes prêt. L'Académie (LEARN) aide à réviser.",
             "→ Where: CAREER (Apps menu) shows your roadmap and what you're "
             "missing; EXAM/CERTIF on the desktop starts the exam when ready. "
             "The Academy (LEARN) helps you revise."),
        ],
    },
    {
        "title": ("Le temps et le marché", "Time and the market"),
        "body": [
            ("Le temps s'écoule EN CONTINU, comme dans la vraie vie : réglez la "
             "vitesse (▶ / ▶▶ / ▶▶▶) ou mettez en pause (Espace) en haut à "
             "droite. Le TERMINAL est le moteur de la partie — le temps avance "
             "même sa fenêtre fermée.",
             "Time flows CONTINUOUSLY, like in real life: set the speed "
             "(▶ / ▶▶ / ▶▶▶) or pause (Space) in the top right. The TERMINAL is "
             "the game engine — time advances even with its window closed."),
            ("Le marché bouge en permanence : cours, indices, devises, "
             "actualités, résultats trimestriels, crises. Vos décisions (et vos "
             "positions, plus tard) vivent dans ce flux. Chaque trimestre, un "
             "BILAN résume vos objectifs et votre performance.",
             "The market moves constantly: prices, indices, currencies, news, "
             "quarterly earnings, crises. Your decisions (and positions, later) "
             "live in this flow. Every quarter, a REVIEW sums up your "
             "objectives and performance."),
            ("Conseil : laissez le temps filer pendant que vous travaillez vos "
             "missions — mais gardez un œil sur le widget PATRIMOINE (en bas à "
             "droite) et le widget À FAIRE, qui liste vos actions en attente.",
             "Tip: let time run while you work your missions — but keep an eye "
             "on the NET WORTH widget (bottom right) and the TO-DO widget, "
             "which lists your pending actions."),
        ],
    },
    {
        "title": ("Vos outils d'aujourd'hui", "Your tools for today"),
        "body": [
            ("Au grade Stagiaire, vous disposez des outils d'ANALYSE : "
             "Recherche (explorer les sociétés), Watchlist (suivre des valeurs), "
             "Alertes de prix, Comparaison, États financiers. Aucun risque : "
             "c'est de la lecture — profitez-en pour apprendre le marché.",
             "As an Intern you have the ANALYSIS tools: Research (explore "
             "companies), Watchlist (follow stocks), price Alerts, Compare, "
             "Financial statements. Zero risk: it's all read-only — use it to "
             "learn the market."),
            ("L'ACADÉMIE (LEARN) propose des leçons notées qui rapportent de la "
             "réputation ; le GLOSSAIRE explique chaque terme ; les TUTORIELS "
             "illustrés détaillent chaque action clé du jeu, pas à pas.",
             "The ACADEMY (LEARN) offers graded lessons that earn reputation; "
             "the GLOSSARY explains every term; the illustrated TUTORIALS "
             "detail every key action in the game, step by step."),
            ("Le reste — trading, deals, mandats, dérivés, M&A... — se débloque "
             "grade après grade. C'est voulu : la complexité arrive quand vous "
             "êtes prêt, et chaque déblocage vous sera expliqué à ce moment-là.",
             "The rest — trading, deals, mandates, derivatives, M&A... — "
             "unlocks grade after grade. That's by design: complexity arrives "
             "when you're ready, and each unlock will be explained then."),
        ],
    },
    {
        "title": ("Le poste de travail, en bref", "The workstation, in short"),
        "body": [
            ("Les fenêtres se déplacent, s'ancrent (glisser vers un bord), "
             "s'agrandissent (double-clic sur la barre de titre) et se "
             "parcourent avec Alt+Tab. Clic DROIT sur une icône, une fenêtre ou "
             "le fond : menu d'actions.",
             "Windows can be moved, snapped (drag to an edge), maximized "
             "(double-click the title bar) and cycled with Alt+Tab. RIGHT-click "
             "an icon, a window or the background: action menu."),
            ("Raccourcis à retenir : Ctrl+K (palette universelle — tout ouvrir "
             "au clavier), Ctrl+/ (chercher dans VOS données : positions, "
             "inbox, mandats), F1 (Assistant « que faire maintenant ? »).",
             "Shortcuts to remember: Ctrl+K (universal palette — open anything "
             "from the keyboard), Ctrl+/ (search YOUR data: positions, inbox, "
             "mandates), F1 (the “what should I do now?” Assistant)."),
            ("Le TERMINAL reste le moteur : le temps s'écoule même sa fenêtre "
             "fermée (▌▌/▶▶ en haut à droite règlent la vitesse), et le widget "
             "en bas à droite du bureau suit votre patrimoine en direct.",
             "The TERMINAL stays the engine: time flows even with its window "
             "closed (▌▌/▶▶ top-right control speed), and the bottom-right "
             "desktop widget tracks your net worth live."),
            ("C'est tout ce qu'il faut savoir pour commencer. Résumé en une "
             "phrase : faites des MISSIONS, montez votre RÉPUTATION, passez "
             "l'EXAMEN — le reste s'ouvrira à vous. Bonne carrière !",
             "That's all you need to get started. One-sentence summary: do "
             "MISSIONS, raise your REPUTATION, pass the EXAM — the rest will "
             "open up. Enjoy your career!"),
        ],
    },
]


def intro_page_count():
    return len(INTRO_PAGES)


def intro_page(idx):
    """Page localisée : (titre, [paragraphes])."""
    pg = INTRO_PAGES[max(0, min(idx, len(INTRO_PAGES) - 1))]
    return _L(*pg["title"]), [_L(*para) for para in pg["body"]]


# ---------------------------------------------------------------------------
# Fiches par fonctionnalité débloquée (carte « NOUVEAUTÉS » de promotion)
# ---------------------------------------------------------------------------
# feature (clé core/unlocks.py) -> fiche : ce que c'est / comment y accéder /
# ce que ça apporte / premiers pas. Chaque champ est un tuple (fr, en).
FEATURE_BRIEFS = {
    "track": {
        "title": ("Voie de spécialisation", "Specialization track"),
        "what": ("Choisissez une VOIE de carrière — M&A, Risk, Quant, Portfolio "
                 "ou Advisory. Elle oriente vos missions, votre app dédiée sur "
                 "le bureau et certains contenus exclusifs.",
                 "Choose a career TRACK — M&A, Risk, Quant, Portfolio or "
                 "Advisory. It shapes your missions, your dedicated desktop app "
                 "and some exclusive content."),
        "how": ("Menu Apps → « Voie (spécialisation) », ou tapez TRACK dans le "
                "Terminal.",
                "Apps menu → “Track (specialization)”, or type TRACK in the "
                "Terminal."),
        "why": ("Des missions plus riches et une identité de carrière : chaque "
                "voie a son écran métier (fusions-acquisitions, gestion des "
                "risques, pricing quantitatif...). Au grade maximal, toutes les "
                "voies se rouvrent librement.",
                "Richer missions and a career identity: each track has its own "
                "professional screen (M&A, risk management, quant pricing...). "
                "At the top grade, all tracks reopen freely."),
        "first": ("Ouvrez TRACK, lisez les 5 voies et choisissez celle qui vous "
                  "attire — ce choix n'est pas anodin, mais aucun n'est mauvais.",
                  "Open TRACK, read the 5 tracks and pick the one that appeals "
                  "to you — the choice matters, but none is wrong."),
    },
    "deals": {
        "title": ("Deals (opportunités à délai)", "Deals (time-limited opportunities)"),
        "what": ("Des OPPORTUNITÉS d'affaires arrivent régulièrement : pitch de "
                 "financement, due diligence, restructuration... Chacune a une "
                 "date limite, une récompense et une pénalité d'échec.",
                 "Business OPPORTUNITIES arrive regularly: financing pitches, "
                 "due diligence, restructuring... Each has a deadline, a reward "
                 "and a failure penalty."),
        "how": ("Icône DEALS sur le bureau (Ctrl+D), ou tapez DEALS. Un deal se "
                "résout par une vraie décision financière (mini-cas), pas un "
                "tirage au sort.",
                "The DEALS icon on the desktop (Ctrl+D), or type DEALS. A deal "
                "resolves through a real financial decision (mini-case), not a "
                "coin flip."),
        "why": ("Gros gains de cash et de réputation — et les deals conclus "
                "comptent dans les critères de promotion de plusieurs grades.",
                "Big cash and reputation gains — and closed deals count toward "
                "several grades' promotion criteria."),
        "first": ("Ouvrez DEALS dès qu'une opportunité apparaît (le widget « À "
                  "FAIRE » vous prévient) et lisez bien l'énoncé avant de "
                  "trancher : la qualité du choix module la récompense.",
                  "Open DEALS as soon as an opportunity appears (the TO-DO "
                  "widget warns you) and read the case carefully before "
                  "deciding: choice quality scales the reward."),
    },
    "calendar": {
        "title": ("Calendrier macro", "Macro calendar"),
        "what": ("L'agenda des évènements économiques programmés (décisions de "
                 "taux, chiffres d'inflation, emploi...) — avec la possibilité "
                 "de prendre position sur leur issue.",
                 "The schedule of upcoming economic events (rate decisions, "
                 "inflation prints, jobs data...) — with the option to take a "
                 "view on their outcome."),
        "how": ("Menu Apps → « Calendrier macro », ou tapez AGENDA. Le widget "
                "calendrier du bureau montre les prochains évènements.",
                "Apps menu → “Macro calendar”, or type AGENDA. The desktop "
                "calendar widget shows upcoming events."),
        "why": ("Anticiper les évènements qui font bouger TOUT le marché — et "
                "gagner cash/réputation en pariant juste sur les issues.",
                "Anticipate the events that move the WHOLE market — and earn "
                "cash/reputation by calling outcomes right."),
        "first": ("Ouvrez AGENDA, repérez le prochain évènement et faites un "
                  "premier pronostic modeste pour comprendre la mécanique.",
                  "Open AGENDA, spot the next event and make a first modest "
                  "call to learn the mechanics."),
    },
    "trade": {
        "title": ("Trading : investir votre argent", "Trading: investing your money"),
        "what": ("Le grand déblocage : acheter et vendre des ACTIONS (et ETF) "
                 "avec votre propre argent. Votre patrimoine ne dépend plus "
                 "seulement de votre salaire — il vit avec le marché.",
                 "The big unlock: buying and selling STOCKS (and ETFs) with "
                 "your own money. Your net worth no longer depends only on "
                 "your salary — it lives with the market."),
        "how": ("Icône TRADING sur le bureau, ou BUY/SELL dans le Terminal "
                "(ex. BUY MVC 100). L'app Recherche a un bouton « Trader » sur "
                "chaque société.",
                "The TRADING icon on the desktop, or BUY/SELL in the Terminal "
                "(e.g. BUY MVC 100). The Research app has a “Trade” button on "
                "every company."),
        "why": ("C'est le moteur de votre FORTUNE (l'autre moitié de votre "
                "score final, avec la réputation). Dividendes, plus-values, "
                "allocation : votre argent travaille enfin.",
                "This is the engine of your WEALTH (the other half of your "
                "final score, with reputation). Dividends, capital gains, "
                "allocation: your money finally works."),
        "first": ("Commencez petit : achetez une petite ligne d'une société de "
                  "votre watchlist et posez un stop-loss (bouton ORD) pour "
                  "limiter la casse. Le tutoriel « Acheter & vendre » détaille tout.",
                  "Start small: buy a small line in a watchlist company and set "
                  "a stop-loss (ORD button) to cap the downside. The “Buy & "
                  "sell” tutorial covers everything."),
    },
    "pitch": {
        "title": ("Démarcher des mandats (PITCH)", "Pitching for mandates (PITCH)"),
        "what": ("Aller chercher vous-même des clients : le PITCH tente de "
                 "convaincre un prospect de vous confier un mandat de gestion.",
                 "Go get clients yourself: a PITCH tries to convince a prospect "
                 "to entrust you with a management mandate."),
        "how": ("Tapez PITCH dans le Terminal, ou passez par l'écran MANDATS.",
                "Type PITCH in the Terminal, or go through the MANDATES screen."),
        "why": ("Plus de mandats = plus de frais de gestion réguliers et plus "
                "de réputation quand vous tenez les objectifs.",
                "More mandates = more recurring management fees and more "
                "reputation when you hit the targets."),
        "first": ("Attendez d'avoir un portefeuille stable avant de démarcher : "
                  "un mandat raté coûte cher en réputation.",
                  "Wait until your portfolio is stable before pitching: a "
                  "failed mandate is costly in reputation."),
    },
    "ma": {
        "title": ("M&A : acheter des sociétés", "M&A: buying companies"),
        "what": ("Acquérir des CIBLES PRIVÉES entières (LBO) : vous financez "
                 "l'opération, la société rejoint votre holding et génère des "
                 "flux — ou des pertes.",
                 "Acquire entire PRIVATE TARGETS (LBO): you finance the deal, "
                 "the company joins your holding and generates cash flows — or "
                 "losses."),
        "how": ("Icône de votre voie M&A (si choisie) ou menu Apps → « M&A », "
                "ou tapez MA (Ctrl+F depuis le terminal).",
                "Your M&A track icon (if chosen) or Apps menu → “M&A”, or type "
                "MA (Ctrl+F from the terminal)."),
        "why": ("Les opérations les plus rentables du jeu — effet de levier, "
                "synergies, revente. C'est aussi le cœur de la voie M&A.",
                "The most profitable operations in the game — leverage, "
                "synergies, resale. Also the heart of the M&A track."),
        "first": ("Ouvrez l'écran M&A, étudiez une cible (valorisation, dette, "
                  "multiples) et exportez la fiche vers le TABLEUR pour la "
                  "modéliser avant d'engager quoi que ce soit.",
                  "Open the M&A screen, study a target (valuation, debt, "
                  "multiples) and export its sheet to the SPREADSHEET to model "
                  "it before committing anything."),
    },
    "ipo": {
        "title": ("Souscription aux IPO", "Subscribing to IPOs"),
        "what": ("Participer aux INTRODUCTIONS EN BOURSE : souscrire avant la "
                 "cotation et jouer le premier jour de trading.",
                 "Take part in IPOs: subscribe before listing and play the "
                 "first day of trading."),
        "how": ("Menu Apps → « IPO », ou tapez IPO dans le Terminal.",
                "Apps menu → “IPO”, or type IPO in the Terminal."),
        "why": ("Des gains rapides quand l'IPO est sursouscrite... et des "
                "gamelles quand elle déçoit. Un vrai jeu d'analyse de dossier.",
                "Quick gains when the IPO is oversubscribed... and losses when "
                "it disappoints. A real case-analysis game."),
        "first": ("Lisez le dossier de la prochaine IPO (valorisation, "
                  "comparables) avant de souscrire — ne souscrivez pas à tout.",
                  "Read the next IPO's file (valuation, comparables) before "
                  "subscribing — don't subscribe to everything."),
    },
    "fx": {
        "title": ("Desk FX (devises)", "FX desk (currencies)"),
        "what": ("Trader les DEVISES : spot (au comptant) et forward (à terme) "
                 "sur les grandes paires (EUR/USD, USD/JPY...).",
                 "Trade CURRENCIES: spot and forward on the major pairs "
                 "(EUR/USD, USD/JPY...)."),
        "how": ("Menu Apps → « FX / Devises », ou tapez FX. Les taux défilent "
                "en permanence dans le ticker du Terminal.",
                "Apps menu → “FX / Currencies”, or type FX. Rates stream "
                "continuously in the Terminal ticker."),
        "why": ("Une classe d'actifs de plus pour diversifier — et couvrir "
                "l'exposition devise de vos positions étrangères.",
                "One more asset class to diversify — and hedge the currency "
                "exposure of your foreign positions."),
        "first": ("Regardez quelles devises pèsent déjà dans votre portefeuille "
                  "(PA, analyse) avant de prendre une position FX sèche.",
                  "Check which currencies already weigh on your portfolio "
                  "(PA, analytics) before taking an outright FX position."),
    },
    "hedge": {
        "title": ("Couverture (HEDGE)", "Hedging (HEDGE)"),
        "what": ("Réduire l'exposition de votre portefeuille aux chocs de "
                 "marché : couverture d'indice, protection contre la baisse.",
                 "Reduce your portfolio's exposure to market shocks: index "
                 "hedging, downside protection."),
        "how": ("Menu Apps → « Couverture », ou tapez HEDGE (ou PROTECT).",
                "Apps menu → “Hedging”, or type HEDGE (or PROTECT)."),
        "why": ("Les crises frappent sans prévenir : une couverture bien "
                "dimensionnée transforme un krach en simple secousse.",
                "Crises strike without warning: a well-sized hedge turns a "
                "crash into a mere bump."),
        "first": ("Ouvrez HEDGE après avoir regardé votre bêta (PA) : couvrez "
                  "une fraction (25-50%) plutôt que tout — la couverture a un "
                  "coût.",
                  "Open HEDGE after checking your beta (PA): hedge a fraction "
                  "(25-50%) rather than everything — hedging has a cost."),
    },
    "leverage": {
        "title": ("Levier & vente à découvert", "Leverage & short selling"),
        "what": ("Emprunter pour investir plus que votre cash (LEVIER), et "
                 "parier à la BAISSE en vendant à découvert (SHORT puis COVER).",
                 "Borrow to invest beyond your cash (LEVERAGE), and bet on the "
                 "DOWNSIDE by short selling (SHORT then COVER)."),
        "how": ("SHORT <ticker> <qté> et COVER dans le Terminal ou l'app "
                "Trading ; MARGIN affiche votre marge et vos intérêts.",
                "SHORT <ticker> <qty> and COVER in the Terminal or the Trading "
                "app; MARGIN shows your margin and interest."),
        "why": ("Amplifier vos convictions à la hausse comme à la baisse — "
                "l'outil des pros, pour le meilleur et pour le pire.",
                "Amplify your convictions both ways — the pros' tool, for "
                "better and for worse."),
        "first": ("Attention : le levier a un coût d'intérêts PERMANENT et un "
                  "APPEL DE MARGE force la liquidation si ça tourne mal. "
                  "Restez sous 1.5x de levier au début, et surveillez MARGIN.",
                  "Careful: leverage has a PERMANENT interest cost and a "
                  "MARGIN CALL forces liquidation if things go wrong. Stay "
                  "under 1.5x leverage at first, and watch MARGIN."),
    },
    "mandates": {
        "title": ("Mandats clients", "Client mandates"),
        "what": ("Gérer l'argent DES AUTRES : un client vous confie un capital "
                 "avec un objectif de rendement et une limite de risque à "
                 "respecter sur une période donnée.",
                 "Manage OTHER PEOPLE'S money: a client entrusts you with "
                 "capital, a return target and a risk limit to respect over a "
                 "given period."),
        "how": ("Icône MANDATS sur le bureau (Ctrl+A), ou tapez MANDATES.",
                "The MANDATES icon on the desktop (Ctrl+A), or type MANDATES."),
        "why": ("Des frais de gestion réguliers, de grosses primes de succès, "
                "et la réputation qui va avec — le cœur de la voie Advisory.",
                "Recurring management fees, big success bonuses, and the "
                "reputation that comes with them — the heart of the Advisory "
                "track."),
        "first": ("Acceptez UN premier mandat prudent (objectif modeste, risque "
                  "large) et tenez-le jusqu'au bout avant d'en empiler d'autres.",
                  "Accept ONE first conservative mandate (modest target, loose "
                  "risk limit) and see it through before stacking more."),
    },
    "options": {
        "title": ("Options sur actions", "Stock options"),
        "what": ("Acheter des CALLS (pari haussier) et des PUTS (pari baissier "
                 "ou assurance) sur les actions individuelles.",
                 "Buy CALLS (bullish bet) and PUTS (bearish bet or insurance) "
                 "on individual stocks."),
        "how": ("Menu Apps → « Options », ou tapez OPTIONS. Le module QUANT "
                "aide à comprendre le pricing (Black-Scholes).",
                "Apps menu → “Options”, or type OPTIONS. The QUANT module "
                "helps understand pricing (Black-Scholes)."),
        "why": ("Un levier énorme pour un capital limité, et le seul moyen de "
                "s'assurer contre la chute d'UNE valeur précise.",
                "Huge leverage for limited capital, and the only way to insure "
                "against the fall of ONE specific stock."),
        "first": ("Commencez par un PUT de protection sur votre plus grosse "
                  "ligne : vous comprendrez la prime, le strike et l'échéance "
                  "sans risquer plus que la prime payée.",
                  "Start with a protective PUT on your biggest position: "
                  "you'll learn premium, strike and expiry while risking no "
                  "more than the premium paid."),
    },
    "team": {
        "title": ("Équipe d'analystes", "Analyst team"),
        "what": ("Recruter des analystes JUNIORS qui travaillent pour vous : "
                 "ils génèrent des idées et boostent vos revenus passifs.",
                 "Hire JUNIOR analysts who work for you: they generate ideas "
                 "and boost your passive income."),
        "how": ("Menu Apps → « Équipe », ou tapez TEAM.",
                "Apps menu → “Team”, or type TEAM."),
        "why": ("Déléguer, enfin : votre carrière ne dépend plus que de vos "
                "seules heures. Un signe que vous devenez senior.",
                "Delegate, at last: your career no longer depends only on your "
                "own hours. A sign you're becoming senior."),
        "first": ("Recrutez UN junior d'abord — son salaire est un coût fixe, "
                  "assurez-vous que vos revenus l'absorbent.",
                  "Hire ONE junior first — their salary is a fixed cost, make "
                  "sure your income absorbs it."),
    },
    "credit": {
        "title": ("Titrisation / crédit structuré", "Securitization / structured credit"),
        "what": ("Investir dans des TRANCHES de pools de prêts (ABS/CLO) : du "
                 "senior sécurisé à l'equity explosive, chaque tranche a son "
                 "couple rendement/risque.",
                 "Invest in TRANCHES of loan pools (ABS/CLO): from safe senior "
                 "to explosive equity, each tranche has its own risk/return "
                 "profile."),
        "how": ("Menu Apps → « Titrisation », ou tapez CREDIT.",
                "Apps menu → “Securitization”, or type CREDIT."),
        "why": ("Des rendements introuvables ailleurs — contre un risque de "
                "défaut qu'il faut savoir lire (waterfall, subordination).",
                "Yields you can't find elsewhere — against a default risk you "
                "must know how to read (waterfall, subordination)."),
        "first": ("Lisez d'abord le tutoriel Titrisation, puis achetez une "
                  "tranche SENIOR d'un pool sain avant de toucher au mezzanine.",
                  "Read the Securitization tutorial first, then buy a SENIOR "
                  "tranche of a healthy pool before touching mezzanine."),
    },
    "structured": {
        "title": ("Produits structurés", "Structured products"),
        "what": ("Souscrire des produits sur mesure : capital garanti, "
                 "autocall, reverse convertible... Un profil de gain défini à "
                 "l'avance contre des conditions de marché.",
                 "Subscribe to tailor-made products: capital-protected notes, "
                 "autocalls, reverse convertibles... A predefined payoff "
                 "profile against market conditions."),
        "how": ("Menu Apps → « Produits structurés », ou tapez STRUCT.",
                "Apps menu → “Structured products”, or type STRUCT."),
        "why": ("Des profils rendement/risque impossibles à répliquer avec des "
                "actions seules — le terrain de jeu de la voie Portfolio.",
                "Risk/return profiles impossible to replicate with stocks "
                "alone — the Portfolio track's playground."),
        "first": ("Comparez deux produits sur le même sous-jacent et lisez leur "
                  "scénario défavorable AVANT de souscrire : le pire cas est "
                  "toute l'information.",
                  "Compare two products on the same underlying and read their "
                  "adverse scenario BEFORE subscribing: the worst case is all "
                  "the information."),
    },
    "valuation": {
        "title": ("Desk Valorisation", "Valuation desk"),
        "what": ("DCF, droite de marché SML/CAPM et pont d'IRR de LBO — les "
                 "trois lentilles classiques pour juger si un cours est cher.",
                 "DCF, the SML/CAPM market line, and an LBO IRR bridge — the "
                 "three classic lenses for judging whether a price is rich."),
        "how": ("Menu Apps → « Desk Valorisation ».",
                "Apps menu → “Valuation desk”."),
        "why": ("Réservé à la voie M&A : juger une cible avant de l'approcher "
                "est le cœur du métier.",
                "Reserved for the M&A track: judging a target before "
                "approaching it is the heart of the job."),
        "first": ("Lancez un DCF sur une société suivie et comparez au cours.",
                  "Run a DCF on a followed company and compare it to the price."),
    },
    "creditdesk": {
        "title": ("Desk Crédit", "Credit desk"),
        "what": ("Modèle de Merton (défaut implicite), cascade de titrisation, "
                 "CDS, TRS (rendement total) et obligations convertibles.",
                 "Merton default model, securitization waterfall, CDS, total "
                 "return swaps and convertible bonds."),
        "how": ("Menu Apps → « Desk Crédit ».", "Apps menu → “Credit desk”."),
        "why": ("Réservé à la voie M&A : évaluer la solvabilité d'une cible "
                "avant de l'endetter davantage.",
                "Reserved for the M&A track: assessing a target's solvency "
                "before loading it with more debt."),
        "first": ("Ouvrez l'onglet Merton sur une société et lisez sa "
                  "probabilité de défaut implicite.",
                  "Open the Merton tab on a company and read its implied "
                  "default probability."),
    },
    "attribution": {
        "title": ("Attribution de performance", "Performance attribution"),
        "what": ("Décomposition Brinson-Fachler (allocation/sélection) et "
                 "régression factorielle de votre performance vs le marché.",
                 "Brinson-Fachler decomposition (allocation/selection) and "
                 "factor regression of your performance vs the market."),
        "how": ("Menu Apps → « Attribution ».", "Apps menu → “Attribution”."),
        "why": ("Réservé à la voie Portfolio : comprendre D'OÙ vient votre "
                "performance, pas juste combien.",
                "Reserved for the Portfolio track: understanding WHERE your "
                "performance comes from, not just how much."),
        "first": ("Ouvrez l'onglet Brinson et repérez votre plus gros secteur "
                  "de sur/sous-performance.",
                  "Open the Brinson tab and spot your biggest over/"
                  "underperforming sector."),
    },
    "backtester": {
        "title": ("Backtesteur de stratégies", "Strategy backtester"),
        "what": ("Rejouez une stratégie systématique (croisement de "
                 "moyennes, momentum, retour à la moyenne) sur l'historique "
                 "réel d'un titre.",
                 "Replay a systematic strategy (moving-average crossover, "
                 "momentum, mean reversion) on a stock's real history."),
        "how": ("Menu Apps → « Backtesteur ».", "Apps menu → “Backtester”."),
        "why": ("Réservé à la voie Portfolio : tester une idée avant d'y "
                "mettre du vrai cash.",
                "Reserved for the Portfolio track: testing an idea before "
                "putting real cash behind it."),
        "first": ("Choisissez une valeur détenue et comparez SMA vs "
                  "acheter-conserver.",
                  "Pick a held stock and compare SMA vs buy-and-hold."),
    },
    "pnlexplain": {
        "title": ("P&L Explain", "P&L Explain"),
        "what": ("Décomposition de la variation de votre patrimoine en "
                 "revenus passifs (dividendes, coupons, carry...) et effet "
                 "prix, ventilé par secteur.",
                 "Breakdown of your net worth change into passive income "
                 "(dividends, coupons, carry...) and price effect, split by "
                 "sector."),
        "how": ("Menu Apps → « P&L Explain ».", "Apps menu → “P&L Explain”."),
        "why": ("Réservé à la voie Portfolio : savoir si vous gagnez de "
                "l'argent en dormant ou en pariant.",
                "Reserved for the Portfolio track: knowing whether you earn "
                "money while sleeping or by betting."),
        "first": ("Ouvrez l'app après un pas de marché et lisez le plus gros "
                  "contributeur du jour.",
                  "Open the app after a market step and read today's "
                  "biggest contributor."),
    },
    "themes": {
        "title": ("Thématiques de marché", "Market themes"),
        "what": ("Investir par TENDANCE plutôt que titre par titre : des "
                 "paniers (IA, transition énergétique, santé...) achetables "
                 "en un clic, avec un classement de rotation « chaud/froid ».",
                 "Invest by TREND rather than stock by stock: baskets (AI, "
                 "energy transition, health...) buyable in one click, with a "
                 "hot/cold rotation ranking."),
        "how": ("Menu Apps → « Thématiques ».", "Apps menu → “Themes”."),
        "why": ("Diversifier au-delà du stock-picking et surfer une "
                "tendance de fond en une seule décision.",
                "Diversify beyond stock-picking and ride a structural "
                "trend in a single decision."),
        "first": ("Repérez le thème le plus chaud du classement et achetez "
                  "son panier avec un petit budget.",
                  "Spot the hottest theme in the ranking and buy its basket "
                  "with a small budget."),
    },
    "mergerarb": {
        "title": ("Arbitrage de fusion", "Merger arbitrage"),
        "what": ("Un mode de trading ÉVÉNEMENTIEL : quand une OPA est "
                 "annoncée sur une société cotée, achetez la cible sous le "
                 "prix d'offre et capturez l'écart si l'opération se conclut "
                 "— gros risque si elle rompt.",
                 "An EVENT-DRIVEN trading mode: when a takeover is announced "
                 "on a listed company, buy the target below the offer price "
                 "and capture the spread if the deal closes — big risk if it "
                 "breaks."),
        "how": ("Menu Apps → « Arbitrage de fusion ».",
                "Apps menu → “Merger arbitrage”."),
        "why": ("Un profil de rendement décorrélé du marché : on parie sur "
                "la RÉUSSITE d'une opération, pas sur la direction des cours.",
                "A return profile decorrelated from the market: you bet on a "
                "deal COMPLETING, not on price direction."),
        "first": ("Prenez une petite position sur l'opération à l'écart le "
                  "plus large et regardez-la se resserrer jusqu'à la clôture.",
                  "Take a small position on the widest-spread deal and watch "
                  "it tighten toward close."),
    },
    "footballfield": {
        "title": ("Football Field", "Football Field"),
        "what": ("Le graphique de valorisation des banques d'affaires : "
                 "comparables non cotés, DCF, transactions précédentes et "
                 "comparables publics décotés, superposés en une seule "
                 "fourchette.",
                 "The investment-banking valuation chart: private comps, "
                 "DCF, precedent transactions and discounted public comps, "
                 "overlaid into a single range."),
        "how": ("Menu Apps → « Football Field » (voie M&A).",
                "Apps menu → “Football Field” (M&A track)."),
        "why": ("Exclusif à la voie M&A : juger un prix demandé en un coup "
                "d'œil, méthode par méthode, avant d'acquérir une cible.",
                "M&A-track exclusive: judge an asking price at a glance, "
                "method by method, before acquiring a target."),
        "first": ("Ouvrez une cible et repérez si le prix demandé tombe "
                  "dans la fourchette ou hors des clous.",
                  "Open a target and see whether the asking price falls "
                  "inside the range or well outside it."),
    },
    "pitchbook": {
        "title": ("Pitch Book", "Pitch Book"),
        "what": ("Démarchage ACTIF de mandats : choisissez un profil client "
                 "et une ambition, lisez votre probabilité de succès, puis "
                 "pitchez.",
                 "ACTIVE mandate pitching: pick a client profile and an "
                 "ambition level, read your win probability, then pitch."),
        "how": ("Menu Apps → « Pitch Book » (voie Advisory).",
                "Apps menu → “Pitch Book” (Advisory track)."),
        "why": ("Exclusif à la voie Advisory : ne plus attendre qu'un "
                "mandat arrive au hasard, aller le chercher.",
                "Advisory-track exclusive: stop waiting for a mandate to "
                "arrive at random — go get one."),
        "first": ("Pitchez un profil client avec une ambition modérée pour "
                  "voir comment la probabilité réagit.",
                  "Pitch a client profile at moderate ambition to see how "
                  "the probability reacts."),
    },
    "strategicalloc": {
        "title": ("Allocation stratégique", "Strategic allocation"),
        "what": ("Répartition de votre patrimoine entre actions, "
                 "obligations, matières premières, crypto et cash — le "
                 "niveau qui explique le plus la performance à long terme.",
                 "Your wealth split across equities, bonds, commodities, "
                 "crypto and cash — the level that explains most long-term "
                 "performance."),
        "how": ("Menu Apps → « Allocation stratégique » (voie Portfolio).",
                "Apps menu → “Strategic allocation” (Portfolio track)."),
        "why": ("Exclusif à la voie Portfolio : piloter le patrimoine "
                "entier, pas seulement le choix de titres.",
                "Portfolio-track exclusive: steer the whole wealth, not "
                "just stock picking."),
        "first": ("Choisissez un profil cible et regardez quels buckets "
                  "dérivent hors de la bande de tolérance.",
                  "Pick a target profile and see which buckets drift "
                  "outside the tolerance band."),
    },
    # Fonctionnalités ouvertes dès le grade 0 : pas de fiche de promotion
    # nécessaire (jamais « nouvellement débloquées ») mais présentes pour
    # robustesse si les paliers changent un jour.
    "charts": {
        "title": ("Graphes de cours", "Price charts"),
        "what": ("Les graphes : ligne, bougies, comparaison de plusieurs titres "
                 "et corrélation. De quoi LIRE un historique de prix.",
                 "Price charts: line, candles, multi-name comparison and "
                 "correlation. The tools to READ a price history."),
        "how": ("Icône Graphes du bureau, ou le bouton graphe d'une fiche société.",
                "Graphs desktop icon, or the chart button on a company sheet."),
        "why": ("Un stagiaire lit des chiffres ; un analyste lit des tendances. "
                "Les graphes n'ont de sens qu'une fois qu'on peut agir dessus.",
                "An intern reads numbers; an analyst reads trends. Charts only "
                "matter once you can act on them."),
        "first": ("Ouvrez le graphe d'un titre de votre watchlist et repérez sa tendance.",
                  "Open the chart of a watchlisted name and spot its trend."),
    },
    "tools": {
        "title": ("Boîte à outils quant", "Quant toolbox"),
        "what": ("Ratio de Sharpe, Z-score, frontière efficiente, tableur à "
                 "formules et labo de crise : des outils d'analyse autonomes.",
                 "Sharpe ratio, Z-score, efficient frontier, formula spreadsheet "
                 "and crisis lab: standalone analysis tools."),
        "how": ("Icônes dédiées du bureau (section Marché & Analyse).",
                "Dedicated desktop icons (Market & Analysis section)."),
        "why": ("Mesurer, comparer et stresser vos idées avec la rigueur d'un pro.",
                "Measure, compare and stress-test your ideas like a pro."),
        "first": ("Calculez le ratio de Sharpe de votre portefeuille.",
                  "Compute your portfolio's Sharpe ratio."),
    },
    "analyst": {
        "title": ("Outils d'analyse", "Analysis tools"),
        "what": ("Recherche de sociétés, watchlist, alertes de prix, "
                 "comparaisons et valeur relative.",
                 "Company research, watchlist, price alerts, comparisons and "
                 "relative value."),
        "how": ("Icônes Recherche/Watchlist du bureau, ou SEARCH/WATCHLIST/"
                "ALERT dans le Terminal.",
                "Research/Watchlist desktop icons, or SEARCH/WATCHLIST/ALERT "
                "in the Terminal."),
        "why": ("Comprendre le marché avant d'y risquer un centime.",
                "Understand the market before risking a cent in it."),
        "first": ("Mettez 3 sociétés en watchlist et posez une alerte de prix.",
                  "Watchlist 3 companies and set a price alert."),
    },
    "alm": {
        "title": ("Desk ALM bancaire", "Bank ALM desk"),
        "what": ("Simulation actif-passif d'un bilan bancaire (sandbox).",
                 "Asset-liability simulation of a bank balance sheet (sandbox)."),
        "how": ("Menu Apps → « ALM », ou tapez ALM.", "Apps menu → “ALM”, or type ALM."),
        "why": ("Comprendre la mécanique d'une banque de l'intérieur.",
                "Understand a bank's mechanics from the inside."),
        "first": ("Ouvrez le desk et testez un choc de taux sur le bilan.",
                  "Open the desk and test a rate shock on the balance sheet."),
    },
    "risk": {
        "title": ("Module risque / VaR", "Risk / VaR module"),
        "what": ("VaR, CVaR et stress tests sur une exposition de référence "
                 "(sandbox).",
                 "VaR, CVaR and stress tests on a reference exposure (sandbox)."),
        "how": ("Menu Apps → « Risk », ou tapez RISK.", "Apps menu → “Risk”, or type RISK."),
        "why": ("Le vocabulaire du risque servira à chaque examen — et à votre "
                "survie de trader.",
                "Risk vocabulary will serve in every exam — and in your "
                "survival as a trader."),
        "first": ("Lancez un stress test et lisez la décomposition de la VaR.",
                  "Run a stress test and read the VaR decomposition."),
    },
    "quant": {
        "title": ("Module quant", "Quant module"),
        "what": ("Pricing d'options (Black-Scholes), grecques et simulations "
                 "(sandbox).",
                 "Options pricing (Black-Scholes), greeks and simulations "
                 "(sandbox)."),
        "how": ("Menu Apps → « Quant », ou tapez QUANT.", "Apps menu → “Quant”, or type QUANT."),
        "why": ("Comprendre ce que vaut une option avant d'en acheter une "
                "(grade 8).",
                "Understand what an option is worth before buying one "
                "(grade 8)."),
        "first": ("Pricez un call et regardez comment la volatilité change la "
                  "prime.",
                  "Price a call and watch how volatility changes the premium."),
    },
}


def brief_for(feature):
    """Fiche localisée d'une fonctionnalité : dict(title, what, how, why,
    first) — ou None si la fonctionnalité n'a pas de fiche."""
    raw = FEATURE_BRIEFS.get(feature)
    if not raw:
        return None
    return {k: _L(*v) for k, v in raw.items()}


def newly_unlocked(player, old_grade_index):
    """Fonctionnalités devenues accessibles entre `old_grade_index` et le
    grade ACTUEL du joueur (après promotion) — via le grade effectif
    (core/unlocks.effective_required_grade), donc cohérent avec les
    raccourcis vétéran et les verrous de voie. Ordre stable (déclaration)."""
    from core import unlocks
    out = []
    for feat in unlocks.UNLOCKS:
        eff = unlocks.effective_required_grade(player, feat)
        if old_grade_index < eff <= player.grade_index:
            out.append(feat)
    return out
