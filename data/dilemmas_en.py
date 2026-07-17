"""
dilemmas_en.py — Traduction EN de la banque de dilemmes (core/dilemmas.py).
Dict id -> {"title", "scenario", "options": [{"label", "outcome"}, ...]}.
Les options sont alignées par index avec DILEMMAS ; cash_k/rep/heat restent
partagés avec la version FR (cf. dilemmas.localized()).
"""

DILEMMAS_EN = {
    "insider": {
        "title": "Confidential tip",
        "scenario": "A client lets slip non-public information about a target ahead of a "
                    "deal announcement. Exploiting it would be very profitable… and illegal.",
        "options": [
            {"label": "Exploit the information",
             "outcome": "Quick gain pocketed. But insider trading like this leaves traces."},
            {"label": "Politely ignore it",
             "outcome": "You stay within the rules. No consequences."},
            {"label": "Report it to compliance",
             "outcome": "Your integrity is noticed. Compliance now trusts you."},
        ],
    },
    "missell": {
        "title": "Borderline product",
        "scenario": "A complex structured product, poorly suited to the client, would earn a "
                    "big commission if sold to an unsophisticated investor.",
        "options": [
            {"label": "Sell it anyway",
             "outcome": "Commission pocketed. The client may end up disappointed…"},
            {"label": "Offer a suitable alternative",
             "outcome": "Less commission, but a loyal and confident client."},
        ],
    },
    "window": {
        "title": "Window dressing",
        "scenario": "Two days before quarter-end, temporarily dressing up the book would make "
                    "your numbers look great in front of the committee.",
        "options": [
            {"label": "Dress up the numbers",
             "outcome": "The committee is impressed… as long as nobody looks too closely."},
            {"label": "Present the real numbers",
             "outcome": "Transparency embraced. The committee appreciates the honesty."},
        ],
    },
    "riskalert": {
        "title": "Risk management alert",
        "scenario": "Risk management flags an overexposed position. Cutting it costs money, "
                    "but keeping it could amplify future losses.",
        "options": [
            {"label": "Ignore the alert, keep the position",
             "outcome": "You're betting on luck. Risk management notes your refusal."},
            {"label": "Hedge the position",
             "outcome": "Exposure reduced. Caution praised."},
        ],
    },
    "conflict": {
        "title": "Conflict of interest",
        "scenario": "You're advising two parties with opposing interests on the same deal. "
                    "Disclosing it could sink a commission.",
        "options": [
            {"label": "Disclose the conflict",
             "outcome": "Ethics respected. Reputation strengthened with the regulator."},
            {"label": "Stay silent",
             "outcome": "The commission is saved… at the cost of real regulatory risk."},
        ],
    },
    "aggressive": {
        "title": "Pressure for an aggressive deal",
        "scenario": "Management is pushing for a very aggressive structuring of a deal, right "
                    "at the edge of the rules. More leverage, more risk.",
        "options": [
            {"label": "Force the aggressive structuring",
             "outcome": "Deal closed by force. Spectacular, but closely watched."},
            {"label": "Structure it prudently",
             "outcome": "Solid, defensible deal. Management grumbles a bit."},
        ],
    },
    "mandate": {
        "title": "Prestigious but time-consuming mandate",
        "scenario": "A highly visible mandate comes up. It will absorb your teams but would "
                    "strongly boost your standing.",
        "options": [
            {"label": "Accept the mandate",
             "outcome": "Mandate secured. A lot of pressure, but what a showcase!"},
            {"label": "Decline to stay focused",
             "outcome": "You preserve your resources, but the opportunity goes to a rival."},
        ],
    },
    "poach": {
        "title": "Poach a rival's talent",
        "scenario": "A star analyst from a competitor is ready to join you — for a costly "
                    "package. It would weaken a rival.",
        "options": [
            {"label": "Hire them",
             "outcome": "Top recruit. Your desk gets stronger, a rival fumes."},
            {"label": "Let it go",
             "outcome": "You preserve your budget. The talent stays with the competitor."},
        ],
    },
    "headhunt": {
        "title": "Offer from a rival firm",
        "scenario": "A headhunter passes you a firm offer from a competing house: an "
                    "immediate transfer bonus, but you start from scratch with your "
                    "clients — and your current firm will know.",
        "options": [
            {"label": "Accept the transfer",
             "outcome": "Bonus pocketed, new firm culture. Your former clients resent "
                        "you — everything must be rebuilt."},
            {"label": "Decline out of loyalty",
             "outcome": "Your firm hears about your refusal. Loyalty gets noticed, "
                        "and remembered."},
            {"label": "Negotiate a counter-offer",
             "outcome": "Your firm partially matches: your base salary increases. The "
                        "headhunter notes your pragmatism."},
        ],
    },
    "megamerger": {
        "title": "Transformative mega-merger",
        "scenario": "You're entrusted with a merger that would reshape an entire industry. "
                    "Historic success possible — or a resounding fiasco.",
        "options": [
            {"label": "Lead the mega-merger",
             "outcome": "Deal of the century closed. Your name circulates across the Street."},
            {"label": "Hand it to someone more experienced",
             "outcome": "A cautious choice. History will remember another name."},
        ],
    },
    "bailout": {
        "title": "Save the firm",
        "scenario": "In the middle of a storm, injecting your personal capital would stabilize "
                    "the firm and make a statement — at the cost of a heavy immediate sacrifice.",
        "options": [
            {"label": "Inject my capital",
             "outcome": "A bold, noticed gesture. The firm holds, your legend grows."},
            {"label": "Preserve my liquidity",
             "outcome": "You protect your cash. Some won't forget your withdrawal."},
        ],
    },
    "frontrun": {
        "title": "Front-running",
        "scenario": "You know of a large client order coming. Positioning ahead of it would "
                    "be lucrative… and constitutes market abuse.",
        "options": [
            {"label": "Position ahead of the client",
             "outcome": "Immediate profit, but front-running is heavily sanctioned if detected."},
            {"label": "Execute the client order first",
             "outcome": "You respect client priority. Trust strengthened."},
        ],
    },
    "expenses": {
        "title": "Expense reports",
        "scenario": "You could inflate your expense reports for a private 'client' dinner.",
        "options": [
            {"label": "Inflate the expenses",
             "outcome": "Small gain, but internal audit is watching."},
            {"label": "Stay honest",
             "outcome": "Everyday integrity. Nothing to report."},
        ],
    },
    "layoffs": {
        "title": "Desk restructuring",
        "scenario": "Cutting your desk's headcount would improve profitability short term, at "
                    "the cost of morale and lost talent.",
        "options": [
            {"label": "Lay off for margin",
             "outcome": "Costs reduced, but the team is shaken and talent leaves."},
            {"label": "Preserve the team",
             "outcome": "You protect your people. Loyalty and stability preserved."},
        ],
    },
    "greenwash": {
        "title": "'ESG' label",
        "scenario": "Labeling a fund 'sustainable' without real justification would attract "
                    "capital — it's greenwashing.",
        "options": [
            {"label": "Apply the ESG label",
             "outcome": "Inflows boosted, but the regulator is tracking greenwashing."},
            {"label": "Label honestly",
             "outcome": "Sincere communication. Less inflows, more credibility."},
        ],
    },
    "whistle": {
        "title": "Internal fraud discovered",
        "scenario": "You discover fraud orchestrated by an influential partner. Reporting it "
                    "is courageous but costly; covering it up is lucrative and dangerous.",
        "options": [
            {"label": "Report the fraud",
             "outcome": "You clean up the firm. Integrity praised at the highest level."},
            {"label": "Cover it up and profit",
             "outcome": "Easy money, but you're now complicit. Very risky."},
        ],
    },
    "greenwashing": {
        "title": "Tempting greenwashing",
        "scenario": "A client wants to label their fund 'ESG' while 40% of the portfolio is "
                    "invested in fossil fuels. Labeling it would bring in a lot of money.",
        "options": [
            {"label": "Refuse the label",
             "outcome": "You refuse. The client is disappointed but your integrity is intact."},
            {"label": "Label it anyway",
             "outcome": "The money comes in, but if word gets out, the scandal will be huge."},
        ],
    },
    "short_squeeze": {
        "title": "Short squeeze ahead",
        "scenario": "You hold a short position on a stock that is up 30% pre-market. Covering "
                    "now limits the damage, but if it falls back...",
        "options": [
            {"label": "Cover immediately",
             "outcome": "You cut your loss. The stock kept rising."},
            {"label": "Hold the short",
             "outcome": "You held on. The stock eventually fell back down."},
        ],
    },
    "crypto_dilemma": {
        "title": "Crypto bet",
        "scenario": "A client wants to invest 30% of their portfolio in an unregulated crypto "
                    "token. Potential returns are huge, but so is the risk.",
        "options": [
            {"label": "Refuse outright",
             "outcome": "The client complains, but you honored your duty of advice."},
            {"label": "Accept with a warning",
             "outcome": "The client signs a waiver. If it goes wrong, they will hold you responsible."},
        ],
    },
    "layoff_decision": {
        "title": "Restructuring plan",
        "scenario": "The board demands a 15% cost cut. You must choose between a layoff plan "
                    "or a bonus cut.",
        "options": [
            {"label": "Lay off 10% of staff",
             "outcome": "Costs fall, the board is happy, but morale collapses."},
            {"label": "Cut bonuses by 30%",
             "outcome": "Teams grumble, but no one loses their job."},
        ],
    },
    "data_leak": {
        "title": "Customer data leak",
        "scenario": "Your intern accidentally emailed a file of 500 clients to an external "
                    "address. GDPR requires notification within 72 hours.",
        "options": [
            {"label": "Notify clients and regulator",
             "outcome": "Full transparency. Clients appreciate it, and so does the regulator."},
            {"label": "Bury the incident",
             "outcome": "No one knows... for now."},
        ],
    },
    "activist_investor": {
        "title": "Activist investor",
        "scenario": "An activist fund has built a 5% stake in one of your clients and demands a "
                    "spin-off of the most profitable division.",
        "options": [
            {"label": "Defend the status quo",
             "outcome": "You help the client fend off the activist."},
            {"label": "Advise the spin-off",
             "outcome": "The spin-off creates short-term value, but the client loses its crown jewel."},
        ],
    },
    "sanctions_breach": {
        "title": "Sanctions breach",
        "scenario": "A client wants to transfer funds to a sanctioned country via a shell "
                    "structure. It is illegal but very well paid.",
        "options": [
            {"label": "Refuse and report",
             "outcome": "You report it to the compliance officer. You are clean."},
            {"label": "Look the other way",
             "outcome": "The money hits your account. But if the Treasury discovers the scheme, "
                         "it's prison."},
        ],
    },
    "ai_trading": {
        "title": "In-house algo",
        "scenario": "Your Quant team developed an algorithm that outperforms the market by 8% "
                    "per year in backtest. Do you deploy it with firm capital?",
        "options": [
            {"label": "Deploy gradually",
             "outcome": "The algo proves itself in live conditions."},
            {"label": "Wait 6 more months of testing",
             "outcome": "Prudent. The algo had a hidden bug that would have cost dearly."},
        ],
    },
    "client_bankruptcy": {
        "title": "Client near bankruptcy",
        "scenario": "Your oldest client is on the brink of bankruptcy. You can help hide losses "
                    "while finding a buyer, or cut ties.",
        "options": [
            {"label": "Help restructure",
             "outcome": "The client survives, finds a buyer, and you remain their hero."},
            {"label": "Cut ties",
             "outcome": "You save your own book but lose a 15-year client."},
        ],
    },
    "bonus_allocation": {
        "title": "Bonus allocation",
        "scenario": "It's bonus season. You have 500K to split among 5 teams. M&A and Trading "
                    "both claim the lion's share.",
        "options": [
            {"label": "Split equally",
             "outcome": "Everyone is happy. Team cohesion improves."},
            {"label": "Favor top performers",
             "outcome": "The stars are thrilled, but the other teams are already looking for new jobs."},
        ],
    },
}
