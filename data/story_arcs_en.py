"""
story_arcs_en.py — English translation of the inbox narrative arcs
(data/story_arcs.ARCS). Keyed by arc id → list of {subject, body} in stage
order (parallel to the FR stages). Sender names are proper nouns and are NOT
translated (kept from the FR data). Selected at runtime by core.i18n language
in core/story_arcs.py::_deliver.
"""

STAGES_EN = {
    "mentor": [
        {"subject": "News from the old desk",
         "body": ("So, keeping up the pace? I've been following your start from a "
                  "distance. A piece of old-timer advice: never mistake a rising "
                  "market for talent. Keep a journal of your decisions — you'll "
                  "thank me at the first turn.")},
        {"subject": "A discreet favor",
         "body": ("One of my old clients wants a view on the industrial names in "
                  "your region. My eye isn't what it was. Take a look at your "
                  "Research screen and tell me what you think — no commitment, "
                  "it's your read I'm interested in.")},
        {"subject": "Thanks — and well spotted",
         "body": ("Your read was right, my client avoided an uncomfortable "
                  "position. I dropped your name to two or three people who "
                  "matter. Keep it up: reputation is built slowly and lost "
                  "quickly.")},
    ],
    "journalist": [
        {"subject": "Interview request",
         "body": ("I'm preparing a profile of the new faces on the Street. Your "
                  "name keeps coming up in conversations. Would you answer a few "
                  "questions about how you work? Nothing tricky — it's the desk "
                  "I'm interested in, not the rumors.")},
        {"subject": "The article is coming along",
         "body": ("Thanks for your time. The piece is progressing; my editor wants "
                  "a 'new generation, old virtues' angle. I'm cross-checking two "
                  "more accounts and I'll keep you posted on publication.")},
        {"subject": "Published — good press",
         "body": ("The article came out this morning. The portrait is flattering "
                  "but honest: rigor, composure, no showing off. Several "
                  "institutional readers have already asked me for your contact "
                  "details. All the best — I'll follow the rest of your career.")},
    ],
    "client_worried": [
        {"subject": "I'm worried about my savings",
         "body": ("Someone gave me your name. I'm not a big client — a "
                  "pharmacist's life savings — but the papers talk of market "
                  "tremors and I'm sleeping badly. Can you explain simply what's "
                  "going on?")},
        {"subject": "Thank you for your patience",
         "body": ("Your explanation reassured me — no one had taken the time to "
                  "speak to me like an adult rather than a file. I've decided not "
                  "to pull everything out. My daughter says it was the right call. "
                  "We'll see.")},
        {"subject": "A token of gratitude",
         "body": ("The markets calmed down and my savings held. I'm sending you a "
                  "small management mandate as a sign of trust — it's not much for "
                  "your desk, but for me it's a lot. Thank you for being honest "
                  "when it was easy not to be.")},
    ],
    "rival_truce": [
        {"subject": "We keep crossing paths",
         "body": ("We always end up on the same deals, you and I. I'd rather tell "
                  "you to your face than behind your back: I'll keep fighting you "
                  "for every deal. Nothing personal — it's the job.")},
        {"subject": "Nice move, that one",
         "body": ("I don't congratulate you often, so I might as well when it's "
                  "deserved: what you did on your last deal was clean. Don't get "
                  "used to the compliments — they won't come every month.")},
        {"subject": "A truce, for once",
         "body": ("A shared deal awaits us both this quarter — too big to fight "
                  "over foolishly. I suggest we compare our reads before charging "
                  "in separately. It stays between us: the rivalry resumes "
                  "afterwards.")},
    ],
    "regulator": [
        {"subject": "Routine review",
         "body": ("Nothing alarming: it's a routine review of your desk's "
                  "leveraged positions. I'll get back to you if a point needs an "
                  "explanation from you. Nothing to lose sleep over.")},
        {"subject": "File closed, cleanly",
         "body": ("The file is closed without reservation — your record-keeping is "
                  "tidier than the Street average, which is not a compliment I "
                  "hand out lightly. Keep it up, it makes everyone's job easier.")},
        {"subject": "A question, off the record",
         "body": ("Outside of any review: we're preparing a new leverage-risk "
                  "framework and I'd like a practitioner's view rather than just a "
                  "committee's. Your name came up naturally. Nothing mandatory, "
                  "just a call when you have a moment.")},
    ],
    "whale_client": [
        {"subject": "A test allocation",
         "body": ("I've heard good things about you, but I prefer to judge on the "
                  "evidence. I'm entrusting you with a small share of my capital — "
                  "a test, not yet earned trust. Let's see how you go the "
                  "distance.")},
        {"subject": "A direct question",
         "body": ("The market moved and you didn't panic, that's already "
                  "something. Tell me frankly: what would worry you today if you "
                  "were in my shoes? I prefer an honest answer to a reassuring "
                  "one.")},
        {"subject": "The test is passed",
         "body": ("Your candor was worth more than any sales pitch. I rarely trust "
                  "this quickly, but I'm going to expand what I entrust to you. "
                  "Don't make me regret this decision.")},
    ],
    "fraud_probe": [
        {"subject": "Alert — suspicious transaction",
         "body": ("A transaction on your client Kariba Mining's account triggered "
                  "an automatic alert. Nothing serious at first glance, but the "
                  "local regulator is asking for supporting documents. Send the "
                  "papers within 48 business hours to avoid escalation.")},
        {"subject": "RE: Kariba alert — update",
         "body": ("The regulator has acknowledged the supporting documents. The "
                  "preliminary investigation is closed, but your name stays on "
                  "file. Be beyond reproach over the coming quarters: a second "
                  "alert would trigger a full audit.")},
        {"subject": "Closure — Kariba file",
         "body": ("File closed with no further action. Your responsiveness worked "
                  "in your favor. Compliance thanks you. Keep it up.")},
    ],
    "hostile_bid": [
        {"subject": "Rumor: hostile bid on Nexora Technologies",
         "body": ("Takeover rumors are circulating on Nexora Technologies. An "
                  "activist fund is said to have built a 7% stake and to be "
                  "preparing a hostile bid. The stock jumped 12% after hours. One "
                  "to watch very closely.")},
        {"subject": "Nexora bid: the offer is filed",
         "body": ("It's official: the fund Valiance Capital launches a bid at $68 "
                  "per share on Nexora, a 25% premium. The board recommends not "
                  "tendering. A battle looms. Do you have clients exposed to the "
                  "stock?")},
        {"subject": "Nexora: outcome of the bid",
         "body": ("The bid failed: Valiance secured only 38% of the shares. The "
                  "price falls back to $52. Arbitrageurs lost big. I hope you "
                  "weren't exposed. Good lesson: a hostile bid is never won in "
                  "advance.")},
    ],
    "whistleblower": [
        {"subject": "You should look at this...",
         "body": ("I can't tell you who I am, but I work at GreenPeak Energy. "
                  "Their latest ESG report is riddled with false statements. CO2 "
                  "emissions are 3× higher than what they publish. An "
                  "investigative outlet will run the story in a few weeks. Do what "
                  "you want with this info.")},
        {"subject": "GreenPeak Energy: ESG scandal",
         "body": ("The FT reveals this morning that GreenPeak Energy massively "
                  "under-reported its emissions. The stock plunges 18% at the "
                  "open. The environmental regulator opens an investigation. "
                  "Several ESG funds announce their divestment.")},
        {"subject": "GreenPeak: were you informed?",
         "body": ("The ethics committee noted that you reduced your exposure to "
                  "GreenPeak BEFORE the FT publication. Mere coincidence or inside "
                  "information? We're dropping it given the modest amounts, but be "
                  "more careful in future.")},
    ],
    "startup_ipo": [
        {"subject": "IPO mandate — NovaTech AI",
         "body": ("NovaTech AI, a generative-AI startup, is preparing its IPO. "
                  "They're looking for a bookrunner. The deal is risky (a 3-year-old "
                  "company, not yet profitable) but the fees are huge. Want us to "
                  "pitch?")},
        {"subject": "NovaTech AI: we have the mandate!",
         "body": ("We landed the mandate! NovaTech picked us as bookrunner. The "
                  "price range is set at $22-26. The roadshow starts next week. "
                  "Get ready to sell the dream.")},
        {"subject": "NovaTech IPO: closing",
         "body": ("The IPO is a success: 8× oversubscribed, the stock opens at $34 "
                  "(+55%). Net fees for the firm come to $2.4M. Congratulations — "
                  "you've just led your first listing.")},
    ],
    "rival_poach": [
        {"subject": "Confidential opportunity",
         "body": ("A top-tier competitor has retained me to approach you. They're "
                  "ready to offer you a Managing Director role with a seven-figure "
                  "package. Interested in discussing it?")},
        {"subject": "So, that role with us?",
         "body": ("I heard you'd been approached. Let me give you a piece of "
                  "advice: here, you build YOUR career. There, you'll just be a "
                  "number. And besides... you wouldn't want me to buy your firm "
                  "without you there to defend it, would you?")},
        {"subject": "Loyalty",
         "body": ("I know you've been approached. That's normal, you're good. But "
                  "loyalty pays in this business — not right away, but always. "
                  "Stay, keep building, and you'll see that opportunities come to "
                  "you without having to switch shops.")},
    ],
}
