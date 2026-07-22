"""
tutorials_en.py — English translation of the illustrated "How to" tutorials
(data/tutorials.TUTORIALS). Keyed by tutorial id → {title, intro, steps,
concept}. Image and id come from the FR source (language-independent) and are
merged in at runtime by data/tutorials.get(). Selected by core.i18n language.
"""

TUTORIALS_EN = {
    "buy_sell": {
        "title": "Buying & selling stocks",
        "intro": "Everything is driven from the keyboard, in the console (bottom of the "
                 "terminal). Commands are case-insensitive.",
        "steps": [
            "Find a company: SEARCH <name>  (e.g. SEARCH mavric) or COMPANY MVC.",
            "Buy: BUY <ticker> <quantity>   →   e.g. BUY MVC 200.",
            "Sell: SELL <ticker> <quantity|ALL>   →   e.g. SELL MVC ALL.",
            "Bet on a fall: SHORT <ticker> <qty>, then COVER to buy back.",
            "Track the result: PRT (book) or PA (detailed analysis).",
        ],
        "concept": "On a buy, a commission is charged and the execution price includes "
                   "a small spread. You can exceed your cash using LEVERAGE (margin "
                   "borrowing) — watch MARGIN: too much leverage = margin call and "
                   "forced liquidation.",
    },
    "bonds": {
        "title": "Bonds: sovereigns & corporates",
        "intro": "A bond is a LOAN: you receive a regular coupon and the principal is "
                 "repaid at maturity. There are two families — SOVEREIGN (issued by a "
                 "state/country) and CORPORATE (issued by a company). Open the market "
                 "with BONDS.",
        "steps": [
            "Show the market: BONDS — the list separates SOVEREIGN and CORPORATE.",
            "SOVEREIGN = a COUNTRY's debt (e.g. US Treasury, German Bund). Its yield "
            "depends on the country's rating, its debt/GDP and its stability. Type GOV "
            "to see countries, their rating and their history.",
            "CORPORATE = a COMPANY's debt (e.g. Pomme, Toyota). The riskier the issuer "
            "(low rating), the higher the coupon/required yield.",
            "Read each row: RATING, COUPON, MAT. (maturity), YTM (yield), PRICE, "
            "DUR (rate sensitivity).",
            "Buy: BUYBOND <id> <qty>   ·   Sell: SELLBOND <id> <qty>. Coupons are paid "
            "automatically at each step (ADV).",
            "Example row on BONDS: \"FR-2034  AA  COUPON 3.2%  MAT 8y  YTM 3.6%  "
            "PRICE 97.4  DUR 6.9\". The YTM (3.6%) > coupon (3.2%) because the price "
            "(97.4) is below par (100) — the market demands a higher yield than the "
            "stated coupon.",
            "The CREDIT SPREAD is the YTM gap between a risky bond and a \"risk-free\" "
            "bond of the same maturity (often the best-rated sovereign of the region). "
            "E.g.: a BBB corporate at 5.1% YTM against a AAA sovereign at 3.0% on the "
            "same maturity = a 2.1-point spread (210 bp). The lower the rating, the "
            "wider the spread — it is the premium demanded for default risk.",
        ],
        "concept": "Price and yield move in OPPOSITE directions: if rates rise, the "
                   "price falls — the more so the longer the DURATION. The YIELD breaks "
                   "down into: curve (policy rate) + term premium + CREDIT spread "
                   "(rating) + COUNTRY risk premium (sovereigns). A well-rated sovereign "
                   "(AAA/AA) has a near-zero spread; a speculative corporate (BB and "
                   "below) can show several points of spread. A regional political event "
                   "(see the Countries tutorial) widens the zone's spreads: the prices "
                   "of both sovereigns AND corporates of the region fall, then recover "
                   "— a chance to buy yield on a dip.",
    },
    "governments": {
        "title": "Countries, governments & politics",
        "intro": "The world is populated by real countries, grouped by region. Each "
                 "government has a sovereign rating, a debt/GDP, political stability and "
                 "a ~5-year history. Open the screen with GOV.",
        "steps": [
            "Type GOV: countries by region on the left, the detailed sheet on the right.",
            "Read the sheet: sovereign RATING, DEBT/GDP, STABILITY, regime, currency, and "
            "the HISTORY of the last 5 years (inspired by reality).",
            "At the bottom of the sheet: the country's BONDS, with their live yield.",
            "As the game goes on, POLITICAL EVENTS occur in a country and hit its "
            "REGION: budget crisis, elections, geopolitical tensions, stimulus…",
            "Watch the news feed (⚑) and the map: the event is shown on the affected "
            "region.",
        ],
        "concept": "A political event has two REAL, exploitable effects: (1) it shocks "
                   "the region's STOCKS (the zone's companies rise or fall via the "
                   "regional factor); (2) it moves the zone's credit SPREAD, hence the "
                   "price of the region's sovereign and corporate BONDS. Bad news "
                   "(instability, default) widens spreads (prices fall); good news "
                   "(reforms, stimulus) tightens them. Anticipating the affected region "
                   "= anticipating who wins and who loses.",
    },
    "futures": {
        "title": "Futures & commodities",
        "intro": "A future (or forward) is a commitment to buy/sell an asset at a future "
                 "date, at a price set today. Open with CMDTY.",
        "steps": [
            "Show the contracts: CMDTY (gold, oil, gas, copper, wheat…).",
            "Read the STRUCTURE: Contango or Backwardation, and the roll/yr.",
            "Buy: BUYCMDTY <id> <quantity>   ·   Sell: SELLCMDTY <id> <qty>.",
            "At each step, the position \"rolls\" to the next expiry (cost/gain).",
        ],
        "concept": "CONTANGO: the future trades ABOVE spot → when rolling, you sell low "
                   "and buy back high = NEGATIVE roll (it costs). BACKWARDATION: future "
                   "BELOW spot → POSITIVE roll (it earns). A forward and a future share "
                   "the same idea; the future is standardized and exchange-traded.",
    },
    "portfolio": {
        "title": "Tracking & analyzing your portfolio",
        "intro": "The PA command opens the detailed analysis of your WHOLE portfolio "
                 "(stocks, bonds, commodities, crypto).",
        "steps": [
            "Type PA (or the ANALYSIS button in the PRT book).",
            "Read the tiles: net worth, P&L, beta, leverage, volatility, drawdown.",
            "Check the WEIGHTS and the allocation (class / sector / region).",
            "Study the CORRELATIONS and the EFFICIENT FRONTIER (the \"YOU\" point).",
        ],
        "concept": "A portfolio that is too CONCENTRATED (one dominant weight, highly "
                   "correlated assets) is fragile. Diversifying moves your point closer "
                   "to the efficient frontier: better expected return for a given risk.",
    },
    "graph": {
        "title": "Reading a chart (technical analysis)",
        "intro": "The chart workshop shows 5 years of history from day 1. Open it with "
                 "GP <ticker> then switch type at the top.",
        "steps": [
            "Line + moving averages: GP <ticker>   (search by name accepted).",
            "Candlesticks: GPC · OHLC bars: GPO · % change: GPCH.",
            "Compare several assets: COMP · Spread/ratio: HS.",
            "Risk: HVOL (volatility), BETA (regression), CORR (correlations).",
        ],
        "concept": "Moving averages (MA20/MA50) smooth the trend; an upward crossover is "
                   "often seen as a positive signal. Candlesticks show "
                   "open/high/low/close of each period.",
    },
    "short": {
        "title": "Short selling (short / cover)",
        "intro": "Going LONG (BUY) is betting the price will RISE. Going SHORT is "
                 "betting the price will FALL: you borrow shares, sell them right away, "
                 "then must BUY them BACK later to return them. Unlocked at the Leverage "
                 "grade (see the 🔒 badge in COMMANDS).",
        "steps": [
            "Open the target company's sheet: DES <ticker> or COMPANY <ticker>.",
            "Short sell: SHORT <ticker> <quantity>   →   e.g. SHORT MVC 100. The sale "
            "proceeds credit your cash, but the position appears negative in PRT.",
            "Watch your margin with MARGIN: a short position consumes margin, like a "
            "leveraged borrowing.",
            "If the price FALLS as expected, buy back cheaper: COVER <ticker> <qty|ALL> "
            "→   e.g. COVER MVC ALL. The difference (sold high − bought back low) is "
            "your gain.",
            "If the price RISES instead, COVER costs more than you received on the sale: "
            "that's a LOSS — close early if the thesis fails.",
        ],
        "concept": "Key asymmetry: when buying (LONG), the maximum loss is limited to "
                   "your stake (the price never goes below 0) while the gain is, in "
                   "theory, unlimited. When SHORT, it's the OPPOSITE: the maximum gain "
                   "is limited (the price can't go below 0) while the LOSS is unlimited "
                   "— the price can rise without a cap. That's why a SHORT consumes "
                   "margin and can trigger a margin call if the position moves against "
                   "you. A SHORT SQUEEZE occurs when a rising price forces many short "
                   "sellers to COVER urgently to limit their losses — their forced "
                   "buying pushes the price even higher, amplifying the rise in a loop.",
    },
    "ma": {
        "title": "M&A: targets, LBO & exit",
        "intro": "The M&A module (MA command) lets you ACQUIRE private companies fully "
                 "or partly on credit (leverage), hold them, then SELL them (exit) later "
                 "for a gain. Unlocked at the M&A grade.",
        "steps": [
            "Open the hub: MA — the TARGETS tab lists available private companies "
            "(filterable by sector or search).",
            "Click a target to open its sheet: price, EBITDA, entry multiple, risk "
            "profile.",
            "Set the LEVERAGE: the \"debt / EV\" slider fixes the share of the deal "
            "financed by debt rather than by your cash (up to a cap).",
            "Click ACQUIRE: your cash funds the equity share, the rest is debt carried "
            "by the acquired company.",
            "Track your acquisitions in the PORTFOLIO tab: current value, remaining "
            "debt, dividends received.",
            "When the time is right, click DIVEST (EXIT) on the target's sheet to sell "
            "the company back and book the gain (or loss).",
        ],
        "concept": "This is the LBO (Leveraged Buy-Out) principle: the larger the share "
                   "financed by DEBT, the smaller your equity stake — and so the more "
                   "the MOIC (Multiple On Invested Capital, gain ÷ initial stake) is "
                   "AMPLIFIED if the exit happens at a higher multiple than entry. But "
                   "leverage also amplifies LOSSES if the target's EBITDA deteriorates "
                   "or the exit multiple is below the entry one — the debt must be "
                   "repaid whatever happens. See the Academy lessons \"LBO\" and "
                   "\"Accretion/Dilution\" for the numeric mechanics.",
    },
    "crypto": {
        "title": "Crypto-assets & stablecoins",
        "intro": "A class apart: no coupon, no dividend, only a price change — often "
                 "very volatile. Open the market with CRYPTO.",
        "steps": [
            "Show the market: CRYPTO — each row shows the spot, annualized volatility "
            "and the TYPE (Crypto, Stablecoin, CBDC).",
            "A classic CRYPTO (type \"Crypto\") has no anchor: its price can double or "
            "halve over the year — read VOL/YR carefully before investing.",
            "A STABLECOIN targets a fixed price (often 1.0). If it BREAKS ITS PEG "
            "(depeg, flagged ⚠), its price drifts from its anchor — a warning signal, "
            "not an upside opportunity.",
            "A CBDC (central bank digital currency) pays a regular yield (+%/yr shown), "
            "close to remunerated cash: the least risky profile of the class.",
            "Buy/sell by clicking +1/-1 on each row, or by keyboard: "
            "BUYCRYPTO <id> <qty>   ·   SELLCRYPTO <id> <qty>.",
        ],
        "concept": "Volatility (VOL/YR) is the key indicator: a crypto at 80-150% annual "
                   "vol can lose half its value in a few weeks, with no cash flow "
                   "(coupon/dividend) to reward the wait. A stablecoin DEPEG is a stress "
                   "signal (loss of confidence, reserve problem): don't mistake it for a "
                   "mere fluctuation — it's often a sign to exit, not to average down.",
    },
    "credit": {
        "title": "Securitisation: tranches & waterfall",
        "intro": "The credit desk (CREDIT) securitises a loan pool into several TRANCHES "
                 "— equity, mezzanine, senior — that absorb the pool's losses in a "
                 "precise order: the \"waterfall\".",
        "steps": [
            "Open the desk: CREDIT — each row is a tranche with its ATTACH-DETACH, its "
            "COUPON and its RATING.",
            "ATTACH-DETACH defines the range of pool losses the tranche absorbs: e.g. a "
            "\"0%-5%\" tranche takes the first 5 points of pool losses, a \"20%-100%\" "
            "tranche is only hit beyond 20% of losses.",
            "The EQUITY tranche (0% attach) pays the highest coupon because it is hit "
            "FIRST in case of defaults — it's the riskiest.",
            "The SENIOR tranche (100% detach) pays the lowest coupon but is only hit "
            "last — it's the most protected (often rated AAA).",
            "Invest: click INVEST on the chosen tranche. The realized return depends on "
            "the pool's default rate over its lifetime.",
        ],
        "concept": "This is the SUBORDINATION principle: the pool's losses climb from "
                   "the bottom up, from the most junior tranches (equity) to the most "
                   "senior. An EXPECTED LOSS of 6% on the pool barely touches a senior "
                   "tranche that detaches at 20%, but can consume the entire 5%-thick "
                   "equity tranche. Choosing your tranche means choosing where you sit "
                   "in the loss queue — from high, risky yield (equity) to low, "
                   "protected yield (senior).",
    },
    "alm": {
        "title": "ALM: bank asset-liability management",
        "intro": "The ALM desk (ALM) simulates a bank's balance sheet: masses and "
                 "durations of assets and liabilities, then the impact of a rate shock "
                 "on net interest income (NII) and the economic value of equity (ΔEVE).",
        "steps": [
            "Open the tool: ALM — adjust the masses (total Assets/Liabilities) and the "
            "durations with the +/- buttons.",
            "The REPRICING GAP (1 year) = rate-sensitive assets minus rate-sensitive "
            "liabilities over a one-year horizon. A positive gap = the bank is "
            "\"asset-sensitive\", it gains when rates rise.",
            "The DURATION GAP compares the price sensitivity of assets to that of "
            "liabilities, weighted by their respective masses.",
            "Apply a RATE SHOCK (buttons -200/-100/+100/+200 bps) and read Δ NII "
            "(impact on 1-year interest margin) and Δ EVE (impact on the economic value "
            "of equity).",
            "Watch Δ EVE / equity: beyond roughly 15-20%, the balance sheet's rate risk "
            "is deemed excessive by regulators (see Basel III).",
        ],
        "concept": "A positive REPRICING GAP and a positive DURATION GAP tell two "
                   "complementary stories: in the short term (NII), a rate rise benefits "
                   "the bank if more assets than liabilities reprice quickly. But in the "
                   "long term (EVE), a positive duration gap (assets longer than "
                   "liabilities) means the VALUE of assets falls more than that of "
                   "liabilities when rates rise — the opposite of the NII reasoning. A "
                   "well-run bank watches BOTH measures: NII for the short term, EVE for "
                   "long-term economic value.",
    },
    "quant": {
        "title": "Option pricing (Black-Scholes & Greeks)",
        "intro": "The QUANT module computes in real time the Black-Scholes price of a "
                 "call/put option and its Greeks (delta, gamma, vega, theta, rho) from "
                 "5 parameters.",
        "steps": [
            "Open the tool: QUANT — set Spot (S), Strike (K), Maturity (T), Rate (r) "
            "and Volatility (σ) with the +/- buttons.",
            "Toggle CALL/PUT with the TYPE button to compare the two profiles.",
            "Read the PRICE shown large: it's the option's theoretical premium under "
            "Black-Scholes, compared to the INTRINSIC VALUE on the \"Price vs Spot\" "
            "chart.",
            "The GREEKS measure the price sensitivity: Delta (underlying move), Gamma "
            "(delta move), Vega (vol move), Theta (time decay), Rho (rate move).",
            "The PAYOFF diagram (bottom) shows the P&L net of premium at expiry: it "
            "reveals the maximum loss (the premium paid) for an option buyer.",
        ],
        "concept": "Increasing VOLATILITY (σ) ALWAYS increases an option's price (call "
                   "or put): the more the underlying can move, the more optionality is "
                   "worth — that's what Vega measures. Conversely, THETA is almost "
                   "always negative for an option buyer: each day that passes without an "
                   "underlying move erodes the premium, especially near expiry. An "
                   "at-the-money option (S ≈ K) has the highest GAMMA: its delta changes "
                   "fast, so its risk is the hardest to hedge dynamically.",
    },
    "risk": {
        "title": "VaR, CVaR & stress tests",
        "intro": "The RISK module measures your portfolio's risk (or a demo book's) via "
                 "VaR, CVaR and stress scenarios. Open it with RISK.",
        "steps": [
            "Open the tool: RISK — in REAL PORTFOLIO MODE, the exposure comes from your "
            "positions; in DEMO MODE, adjust the exposure by factor yourself (Equities, "
            "Rates, Credit, FX, Commodities).",
            "Choose a CONFIDENCE LEVEL (90/95/99%): the higher it is, the larger the "
            "displayed VaR (you cover a wider distribution tail).",
            "Read the HISTOGRAM: the red zone left of the VaR line represents the worst "
            "simulated scenarios.",
            "Compare HISTORICAL VaR, PARAMETRIC VaR and CVaR: the CVaR (average loss "
            "beyond the VaR) is always ≥ the VaR — it captures the severity of the "
            "tail, not just its threshold.",
            "Click a STRESS SCENARIO (equity crisis, rate shock…) to see the instant "
            "impact on your book, broken down by factor.",
        ],
        "concept": "VaR answers \"what loss should not be exceeded X% of the time?\" but "
                   "stays SILENT on the magnitude beyond that threshold — two "
                   "portfolios can share the same 95% VaR and have radically different "
                   "extreme losses. CVaR (Expected Shortfall) fills this gap by "
                   "averaging the losses WITHIN the tail. STRESS TESTS complement the "
                   "statistical approach with extreme historical or hypothetical "
                   "scenarios (crashes, rate shocks) that the \"normal\" distribution "
                   "often underestimates — VaR assumes a calmer world than reality is "
                   "during crises.",
    },
    "structured": {
        "title": "Structured products: capital guarantee, reverse convertible, autocall",
        "intro": "The STRUCTURED DESK sells products whose final payoff is not linear "
                 "with the underlying index: it depends on thresholds, barriers and "
                 "maturity. Open it with STRUCT.",
        "steps": [
            "Open the catalog: STRUCT — each product has a name, a payoff description "
            "and a fixed maturity (in years).",
            "The CAPITAL GUARANTEE returns the invested notional whatever happens, plus "
            "a fraction of the index's rise: safety first, performance second.",
            "The REVERSE CONVERTIBLE pays a high fixed coupon, but if the index falls "
            "below a barrier, the capital is NOT protected: the coupon rewards this "
            "downside risk.",
            "The AUTOCALLABLE can be redeemed early (before maturity) if the index "
            "exceeds a certain level on an observation date — otherwise it continues to "
            "the next maturity.",
            "Subscribe with SUBSCRIBE (button in the catalog); the payoff is only "
            "computed AT MATURITY, based on the final level of the underlying regional "
            "index.",
        ],
        "concept": "A structured product combines a bond (or a deposit) with one or "
                   "more options to shape a non-linear payoff profile: protected "
                   "capital in exchange for capped upside, or a high coupon in exchange "
                   "for unprotected downside risk. There is always an ISSUER (the bank "
                   "that structures the product): its credit risk adds to the market "
                   "risk — if the issuer defaults, the product is worthless, regardless "
                   "of the index's performance.",
    },
    "swaps": {
        "title": "Currency swaps: exchanging a rate differential",
        "intro": "The SWAPS DESK exchanges the interest-rate differential between your "
                 "domestic currency and a foreign one, without ever exchanging the "
                 "principal (the notional is only a calculation reference). Opened with "
                 "SWAP or SWAPS.",
        "steps": [
            "Open the desk: SWAP — choose a FOREIGN CURRENCY among the available "
            "regions (all but yours).",
            "Choose the DIRECTION: \"Receives foreign rate / Pays domestic rate\" if you "
            "think the foreign rate will stay higher, or the reverse if you think your "
            "domestic rate will earn more.",
            "Set the MATURITY (2, 3 or 5 years) and the NOTIONAL (+/- in steps of "
            "100k): this notional is only used to compute the flows, it is never "
            "debited from your cash at entry.",
            "Click ENTER THE SWAP: at each turn until maturity, the net rate "
            "differential (received leg minus paid leg) is settled in cash — positive "
            "if it works in your favor, negative otherwise.",
            "Track your positions in \"Your swaps\": estimated annual carry and time "
            "left before expiry, where the swap stops with no further settlement.",
        ],
        "concept": "A currency swap never transfers the principal: only the rate "
                   "differential between the two legs (domestic and foreign) is settled "
                   "net, like a simplified real cross-currency swap. The regional rate "
                   "reuses that of sovereign bonds (policy rate + country credit "
                   "premium): entering a swap therefore amounts to a BET ON THE RATE "
                   "GAP between two zones, with no direct exchange-rate or equity "
                   "exposure. The risk: if the rate gap moves against your position "
                   "during the swap's life, the negative carry accumulates each turn "
                   "until maturity.",
    },
    "spreadsheet": {
        "title": "The built-in spreadsheet: formulas and DCF model",
        "intro": "The SPREADSHEET (Excel-like) lets you build your own financial models "
                 "with formulas. A mini-DCF is preloaded as an example. Open it with "
                 "SHEET.",
        "steps": [
            "Open the tool: SHEET — navigate with the arrows or by clicking a cell; the "
            "formula bar shows the reference (e.g. B12).",
            "Press ENTER or F2 to edit a cell, or type a character directly to start "
            "writing.",
            "A formula starts with = (e.g. =B3/POWER(1+B5,2)) and can reference other "
            "cells; SUM, NPV, IRR, POWER, IF are available.",
            "The preloaded model computes an Enterprise Value by DCF: B5 is the WACC, "
            "B6 the terminal growth, B12 the final result.",
            "Change B5 or B6 and watch B12 recompute at once — that's the point of a "
            "model: testing assumptions without redoing everything by hand.",
        ],
        "concept": "A DCF model (Discounted Cash Flow) values a company by discounting "
                   "its future cash flows at the WACC (weighted average cost of "
                   "capital), then adding a TERMINAL VALUE that represents all flows "
                   "beyond the explicit horizon (often via the Gordon-Growth formula: "
                   "FCF×(1+g)/(WACC-g)). The terminal value almost always dominates the "
                   "total — hence the extreme sensitivity of the result to the (WACC, "
                   "terminal growth) pair.",
    },
    "hedge": {
        "title": "Hedging: buying a protective put",
        "intro": "The HEDGING DESK lets you buy a PUT on your region's flagship index "
                 "to reduce your portfolio's net beta without selling your positions. "
                 "Opened with PROTECT.",
        "steps": [
            "Open the desk: PROTECT — choose a STRIKE (100% = at the money, 95% or 90% "
            "= out of the money, so cheaper but protects later).",
            "Choose the MATURITY (3, 6 or 12 months): the longer it is, the higher the "
            "premium (more time for the index to fall).",
            "The PREMIUM shown is debited from your cash immediately on purchase — it's "
            "the cost of the insurance, lost if the index doesn't fall below the strike "
            "at maturity.",
            "Click SUBSCRIBE: the hedge is notional (a reference amount), not a real "
            "sale of your positions.",
            "At maturity, if the index ends below the strike, the put pays the "
            "difference proportional to the notional, offsetting part of your book's "
            "losses; otherwise it expires worthless.",
            "PAIR tab (position): hedges a SPECIFIC position (not the whole book) by "
            "shorting a correlated stock — the app computes the min-variance hedge ratio "
            "and sizes the short for you.",
        ],
        "concept": "A protective put is the most classic equity-portfolio insurance: "
                   "you pay a PREMIUM (computed by Black-Scholes, like any option) for "
                   "the right to sell the index at the STRIKE at maturity, whatever its "
                   "real level. The closer the strike to the current level, the broader "
                   "the protection but the pricier the premium. It's a trade-off: you "
                   "accept a certain cost (the premium) to limit an uncertain loss, "
                   "without touching your underlying positions.",
    },
    "options": {
        "title": "Equity options: calls and puts",
        "intro": "The OPTIONS DESK lets you buy CALLS (upside bet) or PUTS (downside "
                 "bet) on an individual stock from your watchlist or portfolio. Opened "
                 "with OPTIONS.",
        "steps": [
            "Open the desk: OPTIONS — choose a security (watchlist or portfolio).",
            "Choose CALL (you gain if the stock rises above the strike) or PUT (you "
            "gain if it falls below the strike).",
            "Choose the STRIKE (90%, 100% or 110% of the current price) and the "
            "MATURITY (3, 6 or 12 months).",
            "The PREMIUM shown (computed by Black-Scholes) is debited immediately — it's "
            "your maximum stake, your loss is limited to this amount.",
            "Choose the number of CONTRACTS then click BUY. At maturity, the contract "
            "settles automatically: intrinsic payoff credited in cash, or zero if it "
            "ends out of the money.",
        ],
        "concept": "An option gives the right (not the obligation) to buy (call) or sell "
                   "(put) an asset at a set price (the strike) at a given expiry. Its "
                   "price (the premium) depends on the current price, the strike, the "
                   "time left and the stock's volatility (Black-Scholes model). Unlike a "
                   "plain equity position, the loss is capped at the premium paid, but a "
                   "call's potential gain is unlimited — an asymmetric leverage effect.",
    },
    "ipo": {
        "title": "IPO: subscribing to a public listing",
        "intro": "The IPO DESK lists companies about to go public. You can subscribe "
                 "before listing, without knowing the final definitive price. Opened "
                 "with IPO.",
        "steps": [
            "Open the desk: IPO — check the current offers (indicative price range, "
            "estimated oversubscription, market sentiment).",
            "Choose an amount to invest then click SUBSCRIBE: the cash is debited "
            "immediately, at the low end of the range (reference listing price).",
            "If the estimated oversubscription is high, your actual allocation is "
            "reduced proportionally (the unallocated surplus is refunded to you right "
            "away): strong demand = fewer shares per euro invested.",
            "On the listing date, the definitive price is drawn (influenced by the "
            "announced market sentiment): your shares are credited at that price, the "
            "balance (gain or loss vs your stake) adjusted in cash.",
            "You can also DECLINE an offer to recover your right to subscribe to "
            "another.",
        ],
        "concept": "An IPO (Initial Public Offering) lets you subscribe to shares before "
                   "they are publicly listed, usually at a discounted price to attract "
                   "investors. The \"pop\" (change between the subscription price and "
                   "the first listed price) can be positive or negative: it's a bet on "
                   "the market's appetite at listing time, distinct from classic "
                   "fundamental analysis.",
    },
    "fx": {
        "title": "FX Desk: spot and forward on currencies",
        "intro": "The FX DESK lets you take positions on major currency pairs, in SPOT "
                 "(freely opened/closed) or FORWARD (locked in advance, settled at "
                 "maturity). Opened with FX.",
        "steps": [
            "Open the desk: FX — choose a pair (e.g. EUR/USD) and a direction: LONG "
            "(you gain if the base currency rises) or SHORT (you gain if it falls).",
            "In SPOT: no cash debited at opening (notional position, like a hedge) — "
            "the unrealized P&L follows the gap between the current rate and the entry "
            "rate; close whenever you like to realize the P&L in cash.",
            "In FORWARD: choose a maturity (1, 3 or 6 months) — the rate is locked in "
            "immediately, with no cash debit, and the contract settles automatically at "
            "maturity based on the final rate.",
            "The FORWARD requires a higher grade than the SPOT — the ACI certification "
            "(FX desk) reduces that requirement.",
        ],
        "concept": "An FX SPOT position is a direct bet on the current exchange rate, "
                   "with no formal leverage and no immediate cash debit (the notional is "
                   "only a calculation reference). A FORWARD locks in today a rate for a "
                   "future date: it's the classic FX hedging tool for exporting "
                   "companies, but also a speculative instrument if the direction taken "
                   "diverges from the realized rate.",
    },
    "calendar": {
        "title": "Macro calendar: betting on scheduled events",
        "intro": "The MACRO CALENDAR announces economic events in advance (central bank "
                 "decision, inflation, employment...) on which you can bet an outcome "
                 "before they resolve. Opened with AGENDA.",
        "steps": [
            "Open the agenda: AGENDA — check the scheduled events (type, steps "
            "remaining, prior probabilities of each outcome: positive/neutral/"
            "negative).",
            "Choose an outcome and a stake: the cash is debited immediately.",
            "The payout multiplier depends on the prior probability of the chosen "
            "outcome (the rarer it is, the higher the multiplier, capped).",
            "At resolution, the actual outcome is drawn: if it matches your bet, the "
            "gain (stake × multiplier) is credited; otherwise the stake is lost.",
        ],
        "concept": "This calendar is a standalone betting market: it does not modify the "
                   "real market, it only materializes a bet on the collective "
                   "anticipation of a macroeconomic event. The multiplier inversely "
                   "proportional to the prior probability reproduces the logic of a "
                   "bookmaker's odds: the more surprising the outcome, the more it pays "
                   "— but the rarer it is.",
    },
    "team": {
        "title": "Team: hiring junior analysts",
        "intro": "From an advanced grade, you can build a small team of junior "
                 "analysts: a recurring cost per turn in exchange for a passive bonus "
                 "(reputation, deal-offer probability). Opened with TEAM.",
        "steps": [
            "Open the screen: TEAM — check the catalog of profiles (equity, credit, "
            "quant, macro), each with a one-off hiring cost and a recurring cost per "
            "turn.",
            "Hire a profile you're interested in: the one-off cost is debited "
            "immediately, the recurring cost then adds to your charges each turn.",
            "Each analyst brings a simple passive effect depending on their profile: a "
            "bit of reputation per turn, and/or a slightly increased probability of new "
            "deal offers.",
            "Fire an analyst at any time if their recurring cost becomes too heavy for "
            "the benefit they bring.",
        ],
        "concept": "A team turns part of your recurring cash into cumulative passive "
                   "effects — a classic management calculation: the fixed cost must be "
                   "justified by a marginal gain (reputation, deal-flow) that exceeds "
                   "its charge over time.",
    },
    "stresstest": {
        "title": "Regulatory stress test",
        "intro": "Periodically (roughly every two quarters), a fictional supervisor "
                 "tests your real portfolio's resilience to a randomly drawn shock "
                 "scenario. Opened with STRESS when a test is pending.",
        "steps": [
            "The imposed scenario (equity crash, rate shock, volatility shock, "
            "recession) is applied instantly to your book to estimate a simulated loss.",
            "The verdict depends on the loss/net-worth ratio: beyond the tolerance "
            "threshold, the test is deemed failed.",
            "Respond: \"Acknowledge\" (no immediate cost, but a reputation penalty on "
            "failure) or \"Reinforce the hedge immediately\" (symbolic hedging cost, but "
            "a softened penalty).",
        ],
        "concept": "This stress test reuses the instant-shock calculation of the RISK "
                   "module (VaR/CVaR, exposure) applied to your real portfolio — a "
                   "simulation of the regulatory oversight that governs any trading "
                   "floor: resilience to extreme scenarios matters as much as current "
                   "performance.",
    },
    "history": {
        "title": "Career timeline",
        "intro": "A screen viewable at any time (not just at the end of the game) "
                 "retracing the evolution of your net worth and the key milestones of "
                 "your career. Opened with TIMELINE.",
        "steps": [
            "The chart plots your net worth (cash + positions) over the last turns.",
            "The timeline lists your career milestones (promotions, certifications, "
            "notable deals...) from most recent to oldest.",
        ],
        "concept": "Reviewing your trajectory helps judge your decisions in hindsight — "
                   "a useful reflex to distinguish luck (a rising market) from skill (a "
                   "real risk management) in the displayed performance.",
    },
    "sharpe": {
        "title": "Sharpe Ratio: your risk-adjusted performance",
        "intro": "Two portfolios with the same return are not equal if one took twice "
                 "the risk. The SHARPE app compares your real book to the regional "
                 "benchmark and to reference allocations.",
        "steps": [
            "Open the \"Sharpe Ratio\" desktop icon: the top tiles give your annualized "
            "Sharpe, return, volatility, beta and Jensen's alpha vs your region's "
            "index.",
            "Choose the period (3M/1Y/3Y/5Y) and the risk-free rate (−/+ buttons) to "
            "see how the ratio reacts.",
            "The COMPARISON chart places your portfolio next to the benchmark, the "
            "minimum-variance portfolio and the maximum-Sharpe portfolio (computed on "
            "the same universe).",
            "The ROLLING SHARPE curve shows whether your ratio is improving or "
            "deteriorating over time — not just a frozen number.",
            "The BY-POSITION table details each line's return/volatility/Sharpe: spot "
            "those dragging performance down.",
            "\"→ FRONTIER\" button: switches directly to the Efficient Frontier app to "
            "act on what you just read.",
        ],
        "concept": "Sharpe = (return − risk-free rate) / volatility, annualized. A high "
                   "Sharpe means a good return PER UNIT of risk taken, not just a big "
                   "gross return — a very risky portfolio can have a flattering return "
                   "and a mediocre Sharpe. Jensen's alpha isolates what remains once the "
                   "market beta is removed: the \"true\" skill, if non-zero.",
    },
    "zscore": {
        "title": "Z-Score: how many standard deviations from the norm?",
        "intro": "The z-score measures how far a value strays from its RECENT behavior — "
                 "a statistical signal of mean reversion or anomaly, on price, return, "
                 "volatility or correlation.",
        "steps": [
            "Choose a stock by chip (your positions and watchlist appear first) or type "
            "a ticker in \"Other ticker…\".",
            "Select the READING: PRICE (z of the price vs its moving average), RETURN "
            "(unusual shock at the last step), VOLATILITY (abnormal vol regime) or "
            "CORRELATION (unusual decorrelation vs the index).",
            "The large \"z = …\" value gives the verdict: beyond ±2σ, the deviation is "
            "statistically rare.",
            "The curve plots the z-score OVER TIME with ±1σ/±2σ bands — look at whether "
            "past excursions returned toward zero.",
            "TRADE / ALERT buttons: act directly on the signal without re-entering the "
            "ticker elsewhere.",
        ],
        "concept": "An extreme z-score doesn't tell you WHAT TO DO on its own: on a "
                   "price, a very negative z can be an opportunity (mean reversion) or "
                   "the start of a real downtrend (the mean itself has changed). Always "
                   "cross-check with the company sheet before acting on the number "
                   "alone.",
    },
    "frontier": {
        "title": "Efficient frontier: optimize THEN execute",
        "intro": "The efficient frontier plots, for each risk level, the BEST "
                 "achievable return with a given basket of stocks — and here, unlike a "
                 "finance course, you can click on it to place the real orders.",
        "steps": [
            "Check the universe (left column): your held positions are marked ✶ and "
            "checked by default.",
            "The curve on the right shows the annualized return/risk pair of each "
            "possible weight combination, with MIN VAR and MAX SHARPE marked.",
            "Click a point on the curve (or the MIN VAR / MAX SHARPE buttons) to pick "
            "it as the TARGET — your CURRENT point is also shown for comparison.",
            "The bottom panel translates the target into CURRENT → TARGET weights and a "
            "precise ORDER LIST (buys/sells in whole quantities).",
            "APPLY places these orders for real (game fees and market impact included), "
            "after a confirmation.",
        ],
        "concept": "The efficient frontier illustrates diversification: combining stocks "
                   "that aren't perfectly correlated reduces total risk without "
                   "necessarily sacrificing return. MIN VAR minimizes volatility, MAX "
                   "SHARPE maximizes return per unit of risk — two different objectives, "
                   "not always at the same spot on the curve.",
    },
    "greeks": {
        "title": "Options Desk: strategies, models, Greeks",
        "intro": "The Options Desk has three tabs: building a STRATEGY (a package of "
                 "options), comparing pricing MODELS, and tracking the GREEKS of your "
                 "whole book.",
        "steps": [
            "Choose a stock then a STRATEGY (plain call/put, straddle, strangle, "
            "protective put) — never a short sale of an option, only purchases.",
            "Set the maturity and the number of contracts; the chart shows the P&L AT "
            "EXPIRY vs the final price, with the breakeven marked.",
            "The right panel details the total premium and the package's Greeks: Δ "
            "(delta, directional exposure), Γ (gamma), v (vega, P&L per +1 point of "
            "vol) and θ (theta, cost of time per day).",
            "MODELS tab: the SAME option priced under Black-Scholes, CRR binomial, "
            "Monte-Carlo, Merton jump-diffusion and implied vol — to see where they "
            "diverge (American options, jump markets).",
            "BOOK tab: all your open options, revalued at the day's market, with the "
            "vol edge (implied paid vs realized since purchase).",
        ],
        "concept": "A lone call or put BETS on a direction; a straddle or a strangle BET "
                   "on VOLATILITY (they gain if the stock moves a lot, either way); a "
                   "protective put INSURES a held position. Theta is the rent you pay "
                   "each day to hold optionality — the move (or the gamma) must repay "
                   "it.",
    },
    "vardesk": {
        "title": "Risk: VaR, CVaR, contributions, backtest",
        "intro": "The VaR (Value at Risk) answers: \"what loss, at worst, with 95% (or "
                 "99%) confidence, over the next step?\". This desk computes it on YOUR "
                 "real book and checks that it is reliable.",
        "steps": [
            "Choose the confidence level (95% or 99%): the top tiles give VaR, CVaR "
            "(average loss BEYOND the VaR), parametric VaR and the standard deviation "
            "of the simulated P&L.",
            "The SIMULATED DISTRIBUTION histogram shows the shape of your possible "
            "losses/gains; the red bars are the TAIL beyond the VaR.",
            "VAR BY POSITION (Euler allocation): each line's contribution to the total "
            "VaR — a NEGATIVE contribution is a hedge that reduces overall risk.",
            "KUPIEC BACKTEST: compares the number of exceptions (days where the loss "
            "exceeded the stated VaR) observed vs expected — a model \"NOT rejected\" is "
            "well calibrated.",
            "\"STRESS TEST\" button: switches to extreme shock scenarios, complementary "
            "to the VaR (which assumes a \"normal\" world).",
        ],
        "concept": "VaR says nothing about the magnitude of a loss BEYOND the threshold "
                   "— that's CVaR's role. The Euler allocation is the only "
                   "mathematically consistent way to decompose a VaR by line: the "
                   "contributions SUM exactly to the total, unlike a simple weighting by "
                   "position size.",
    },
    "rates": {
        "title": "Rates Desk: curve, duration, DV01, shocks",
        "intro": "The Rates Desk covers the sovereign yield curve, your bond book "
                 "(duration/DV01/convexity), commodity futures and your interest-rate "
                 "swaps (IRS).",
        "steps": [
            "RATES tab: the sovereign yield curve by maturity — steep (normal), flat or "
            "inverted (recession signal).",
            "CURVE SHOCKS simulates rate changes (parallel, steepening, flattening) and "
            "shows YOUR book's P&L, duration AND convexity included.",
            "BOND BOOK (right): each line with its modified duration, its convexity and "
            "its DV01 — the P&L of a one-basis-point rise.",
            "SHORTEN / LENGTHEN buttons: rotate the book toward shorter or longer "
            "maturities at constant DV01 (the game does not short bonds — you move the "
            "risk, you don't create it).",
            "FUTURES/IMMUNISATION/SWAPS (IRS) tabs: commodity forward curves, "
            "duration-matching to a liability's horizon, and hedging the book's DV01 "
            "with a payer/receiver swap.",
        ],
        "concept": "DV01 (Dollar Value of 01) is a rates desk's unit of account: P&L ≈ "
                   "value × duration × 0.0001 for +1 basis point. CONVEXITY softens rate "
                   "shocks — a rise loses slightly LESS than duration alone predicts, "
                   "and a fall gains slightly MORE.",
    },
    "attribution": {
        "title": "Performance attribution: good or lucky?",
        "intro": "You beat the market — but is it because you picked the right SECTORS, "
                 "the right STOCKS within them, or just got lucky on factor bets?",
        "steps": [
            "BRINSON tab: the total gap (YOU − MARKET) breaks down into ALLOCATION "
            "(overweighting the right sectors) + SELECTION (picking the right stocks "
            "within them) + interaction — the three SUM exactly to the total gap.",
            "The by-sector table details weight and return you/market, with each one's "
            "allocation and selection contribution.",
            "FACTORS tab: regression of your return on observable factors (world, "
            "sector, region) — betas, annualized ALPHA and R².",
            "A very high R² with an alpha near zero means your P&L is ONLY factor bets "
            "(\"closet tracker\") — no measurable stock selection.",
        ],
        "concept": "Allocation rewards being in the right sectors BEFORE they perform; "
                   "selection rewards picking the right lines WITHIN a given sector. A "
                   "manager can have good allocation and bad selection (or the reverse) "
                   "— the two skills are different.",
    },
    "pairs": {
        "title": "Pairs Trading: statistical arbitrage",
        "intro": "Two COINTEGRATED stocks form an elastic band: their price gap (the "
                 "spread) oscillates around zero. You sell the gap when it's stretched, "
                 "you cash in when it comes back.",
        "steps": [
            "The SCANNER lists the roster's most cointegrated pairs (sorted by ADF "
            "statistic) — the more negative the ADF, the stronger the cointegration.",
            "Click a pair: the chart plots the SPREAD (log-price minus β times the "
            "other log-price) with ±2σ entry bands.",
            "The DIAGNOSTIC panel gives the β (hedge ratio), the ADF vs the −3.0 "
            "threshold, the correlation, the COINTEGRATED/NOT verdict and the half-life "
            "(typical time of mean reversion).",
            "z = the spread's current z-score: beyond ±2, an entry signal; near 0, an "
            "exit signal.",
            "Choose a notional and EXECUTE THE PAIR: opens long one stock / short the "
            "other, sized by the β.",
        ],
        "concept": "A strong CORRELATION is not enough — two correlated stocks can drift "
                   "apart indefinitely. COINTEGRATION (Engle-Granger test: the RESIDUAL "
                   "of the log-price regression is stationary) guarantees that the gap "
                   "returns, statistically, toward its mean — the real condition for the "
                   "strategy to work.",
    },
    "creditdesk": {
        "title": "Credit Desk: Merton, CDS, convertibles, securitisation",
        "intro": "A company's credit risk shows up in ITS STOCK: Merton's model treats "
                 "it as an option on its assets. This desk derives default probability, "
                 "CDS, convertibles and securitisation from it.",
        "steps": [
            "MERTON tab: the SCANNER ranks the roster by decreasing PD (default "
            "probability) — click a company to see the detail (assets, leverage, "
            "distance to default, implied spread).",
            "The bottom chart shows how the PD reacts to a shock on the stock price — "
            "the direct link between equity and credit.",
            "CDS tab: buy protection (pay an accrued premium each step) — its "
            "mark-to-market moves with the spread; a credit event (stock below 25% of "
            "its entry level) triggers the payout.",
            "CONVERTIBLES tab: the price breaks down into a bond floor + option value — "
            "participates on the upside, protects on the downside.",
            "WATERFALL tab: slide the pool-loss cursor of the securitised pool to see "
            "the equity → mezzanine → senior cascade activate.",
        ],
        "concept": "Merton: at maturity, shareholders receive max(0, assets − debt) — "
                   "exactly the payoff of a CALL on the assets, strike = the debt. Hence "
                   "PD = N(−distance to default). A CDS doesn't bet on THE default "
                   "itself but on the FEAR of default: its price moves well before a "
                   "default occurs.",
    },
    "crisislab": {
        "title": "Crisis lab: set your own scenario",
        "intro": "Rather than waiting for a real crisis, set the magnitude of an equity "
                 "crash and a rate shock yourself, and see IMMEDIATELY the impact on "
                 "each of your positions.",
        "steps": [
            "Slide the EQUITIES (down to −40%) and RATES (up to +300 bp) cursors — the "
            "scenario P&L updates live.",
            "The LINE-BY-LINE REVALUATION table revalues each position (stocks by beta, "
            "bonds by duration+convexity, options and hedging puts re-priced "
            "Black-Scholes) — your hedging puts should appear in GREEN (they gain in a "
            "crash).",
            "Check \"CORRELATIONS → 1\": simulates the moment when, in a real crisis, "
            "everything falls TOGETHER (diversification stops protecting) — compare the "
            "P&L with and without.",
            "The gap between the two is the \"cost of the diversification illusion\": "
            "what your apparent diversification would cost you if it vanished precisely "
            "when you need it.",
        ],
        "concept": "In normal times, correlations between stocks are MODERATE — that's "
                   "what makes diversification effective. In a systemic crisis, "
                   "correlations often rise toward 1: everything falls at the same time, "
                   "and a portfolio that seemed diversified behaves like a single big "
                   "position.",
    },
    "valuation": {
        "title": "Valuation: DCF, CAPM, LBO bridge",
        "intro": "Is a stock's price justified by its fundamentals? The DCF discounts "
                 "future cash flows to estimate an intrinsic value, independent of "
                 "market sentiment.",
        "steps": [
            "DCF tab: choose a company — the computed price per share is shown large, "
            "compared to the real price with the UNDERVALUED / OVERVALUED / near-price "
            "verdict.",
            "The detail shows the starting FCF, the explicit 5-year growth, the present "
            "value of the flows AND of the terminal value — look at what share of the "
            "EV comes from the terminal value (often the majority, hence the most "
            "uncertain).",
            "Set WACC and g∞ (perpetual growth) with the −/+ buttons: the SENSITIVITY "
            "table on the right shows the value per share for each combination, with a "
            "white box on the cells compatible with the current price.",
            "SML (CAPM) tab: places each company on the security market line "
            "expected-return vs beta — the gap to the line is an alpha.",
            "LBO BRIDGE tab: decomposes an equity gain into growth + multiple expansion "
            "+ deleveraging, summing exactly.",
        ],
        "concept": "A DCF is only as good as its assumptions — WACC and perpetual growth "
                   "(g∞) have an OUTSIZED effect on the result because the terminal "
                   "value often dominates the EV. The sensitivity table exists precisely "
                   "to never present a single figure as a certainty.",
    },
    "fxdesk": {
        "title": "FX Desk: carry trade & rate parity",
        "intro": "Borrowing in a low-rate currency to lend in a high-rate one earns a "
                 "daily differential (the carry) — at the risk of a brutal drop in the "
                 "pair.",
        "steps": [
            "The table lists the pairs sorted by |carry|: each currency's rate, the "
            "annualized carry of a long position, and the 3-month forward's term "
            "points.",
            "Click a pair: the right panel shows the carry, the pair's volatility and "
            "the carry/vol ratio (does the carry compensate for the drop risk?).",
            "Choose a notional then LONG (bet the carry continues) or SHORT (bet the "
            "reverse) — the position really increases/hedges your currency exposure.",
            "The accrued carry adds to/subtracts from your cash AT EACH STEP (a real "
            "daily income or cost, not just at close).",
        ],
        "concept": "Long the pair = long the BASE currency: the carry is the policy-rate "
                   "gap (r_base − r_quote). Without FX risk, this carry should disappear "
                   "(covered interest parity): a forward's term points offset the "
                   "differential almost exactly — otherwise a risk-free arbitrage would "
                   "exist.",
    },
    "vollab": {
        "title": "Vol lab: GARCH, forecast, regimes",
        "intro": "Volatility is not constant: it comes in CLUSTERS (calm periods "
                 "followed by turbulent ones). GARCH models and forecasts it; the "
                 "regime filter infers the market's hidden state.",
        "steps": [
            "GARCH tab: choose a stock — the formula shows α (reaction to recent shocks) "
            "and β (memory of old shocks), and their sum α+β measures the PERSISTENCE "
            "of volatility.",
            "\"Vol rich\"/\"Vol cheap\": compares what GARCH forecasts to what the "
            "options desk currently prices into its premiums.",
            "The 12-step forecast curve CONVERGES toward the long term at speed "
            "(α+β)^h — the closer α+β is to 1, the longer vol shocks last.",
            "REGIMES tab: a 2-state Bayesian filter infers P(stress) over time from the "
            "observed returns ALONE, compared to the engine's real truth "
            "(Expansion/Calm/Volatile/Recession).",
        ],
        "concept": "σ²(t) = ω + α·r²(t−1) + β·σ²(t−1): tomorrow's variance depends on "
                   "yesterday's shock AND yesterday's variance. A regime is not just an "
                   "isolated turbulent day — the Bayesian filter requires CONSISTENCY "
                   "over time (sticky 0.95 transition) before declaring a regime change.",
    },
    "funding": {
        "title": "Funding Desk: repo, securities lending, cash",
        "intro": "Three ways to put your balance sheet to work: borrowing against bonds "
                 "(repo), lending your held stocks to short sellers, or placing idle "
                 "cash.",
        "steps": [
            "REPO tab: choose a sovereign collateral and a quantity — you only pay the "
            "HAIRCUT in cash, the rest is borrowed at the repo rate (rolled each step). "
            "The EQUITY CARRY shown is the collateral's yield minus the borrowing cost, "
            "amplified by the implicit leverage.",
            "In a crisis, haircut AND repo rate rise together — a margin call can "
            "liquidate the position at the worst moment (see LTCM/2008).",
            "SECURITIES LENDING tab: check \"LEND MY SECURITIES\" to earn income on your "
            "held long positions (lender share 40% of the market rate) — the table also "
            "shows what your own short positions cost you in borrowing fees.",
            "CASH tab: enable the SWEEP (idle cash beyond a cushion, placed overnight "
            "automatically) or open a term deposit (locked, better paid).",
        ],
        "concept": "The repo is the classic bond leverage: a small haircut (often "
                   "3-10%) lets you carry a bond position much larger than the cash "
                   "committed. A small cap is \"hard to borrow\" (rare to lend) — its "
                   "borrowing cost is high, which makes shorting it more expensive.",
    },
    "pnlexplain": {
        "title": "P&L Explain: where does each euro come from?",
        "intro": "A real desk's #1 ritual: every morning, explaining where EACH euro of "
                 "yesterday came from. This app breaks down the move of your net worth "
                 "over the last step.",
        "steps": [
            "The top line gives the total Δ net worth of the last step, in green (gain) "
            "or red (loss).",
            "It breaks down into PASSIVE INCOME (dividends, coupons, FX carry, repo, "
            "securities lending, sweep, derivative flows — everything the engine ran "
            "automatically) and PRICE & REST (your positions moving, salary, fees, your "
            "own orders).",
            "The POT PRICE EFFECT panel splits the price effect by SECTOR — which "
            "sectors pulled your net worth up or down this step.",
            "At the bottom, the FIRM RISK BUDGET gauge shows your current VaR vs the "
            "limit set by your grade — beyond it, a warning, then reputation, then a "
            "forced reduction of your largest line after 5 steps in breach.",
        ],
        "concept": "Separating PASSIVE income (which arrives whether you trade or not) "
                   "from the PRICE effect (the real market risk taken) avoids confusing "
                   "a good quarter with mere carry — a book that gains ONLY carry with "
                   "no real price conviction is more fragile than it looks.",
    },
    "backtester": {
        "title": "Backtester: testing a strategy on real history",
        "intro": "Before risking real cash, replay a MECHANICAL trading rule (no AI) on "
                 "a stock's REAL history — career prehistory (5 years) included.",
        "steps": [
            "Choose a stock (positions/watchlist chips, or free search) then a "
            "strategy: Buy & hold, Moving-average crossover, Momentum, or Mean "
            "reversion.",
            "The tiles compare the strategy's total return to that of a simple Buy & "
            "hold, with the annualized Sharpe, the maximum drawdown and the average "
            "market exposure.",
            "The equity curve (base 1.0) plots how €1 invested would have evolved with "
            "this rule, over all available history.",
            "Switch strategy to compare — a strategy that beats the market on ONE stock "
            "does not necessarily beat it on another.",
        ],
        "concept": "Each signal is decided with the data available UP TO the current "
                   "step ONLY, then applied to the NEXT return — no look-ahead bias, the "
                   "most common trap of a poorly built backtest. A good past result "
                   "never guarantees a future one: it's a judgment tool, not a "
                   "money-machine.",
    },
    "footballfield": {
        "title": "Football Field: valuation in a range",
        "intro": "Exclusive to the M&A track: the classic investment-bank valuation "
                 "chart — several methods, stacked as bars, to judge a price at a "
                 "glance.",
        "steps": [
            "Choose a target in the chips (already-owned targets are marked) — the sheet "
            "shows its EBITDA and net debt.",
            "Each bar is a METHOD: Private comparables, DCF, Precedent sector "
            "transactions, Discounted public comparables — the white line in the middle "
            "is the retained midpoint.",
            "The amber vertical marker shows the seller's ASK PRICE: if it falls within "
            "several ranges, the price is defensible; outside all of them, it's "
            "expensive or discounted.",
            "ACQUIRE button (or MANAGE for an already-owned target): switches directly "
            "to the M&A screen to act on this judgment.",
        ],
        "concept": "No isolated valuation method is reliable: the DCF depends on "
                   "debatable growth/WACC assumptions, comparables depend on a sample of "
                   "companies never perfectly identical. Stacking several independent "
                   "methods and looking at where they CONVERGE (rather than a single "
                   "figure) is standard investment-banking practice — hence the name, "
                   "the chart's shape recalling a football field seen from above.",
    },
    "pitchbook": {
        "title": "Pitch Book: pitching a mandate instead of waiting for it",
        "intro": "Exclusive to the Advisory track: until now, a client mandate only "
                 "arrived by random draw. The Pitch Book lets you CHOOSE a client "
                 "profile and actively pitch it.",
        "steps": [
            "Left column: the 5 client profiles (Insurer, Pension fund, Family office, "
            "Opportunistic client, Conservative institutional) with your AFFINITY for "
            "each (reputation, grade, Advisory track) — an \"unavailable\" profile just "
            "declined a recent pitch (2-quarter cooldown).",
            "Right column: set the pitch AMBITION with −/+ — more ambitious (higher "
            "targeted capital and objective) LOWERS the displayed success probability, "
            "more modest raises it.",
            "PITCH draws the result: a success creates a REAL mandate offer (found in "
            "your mandates/offers, like a normal offer); a failure costs reputation and "
            "puts this client on pause before retrying.",
            "The pitch log at the bottom keeps a trace of the latest attempts, won or "
            "lost.",
        ],
        "concept": "A successful pitch is not pure luck: your reputation, your grade and "
                   "having chosen the Advisory track really increase your success "
                   "probability — and aiming too high (ambition) lowers it, like a real "
                   "client who negotiates harder against an aggressive proposal.",
    },
    "strategicalloc": {
        "title": "Strategic allocation: the level that matters most",
        "intro": "Exclusive to the Portfolio track: the split of your wealth between "
                 "stocks, bonds, commodities, crypto and cash — not the selection of "
                 "individual stocks.",
        "steps": [
            "The donut on the left shows your CURRENT split; the legend compares each "
            "class to its TARGET and flags (⚠) those outside the 5-point tolerance "
            "band.",
            "On the right, choose a profile (Conservative/Balanced/Dynamic) or "
            "\"Custom\" to set your own targets with −/+.",
            "The REBALANCE button (stocks) resizes your existing equity positions "
            "PROPORTIONALLY toward the target; the other out-of-band classes are only "
            "FLAGGED with the amount to move — head to the relevant desk to choose the "
            "instrument.",
        ],
        "concept": "The financial literature (Brinson et al.) shows that the SPLIT "
                   "between major asset classes explains most of a portfolio's "
                   "performance variance over time — well before the choice of which "
                   "specific stocks to buy. A professional portfolio manager therefore "
                   "spends as much time on THIS decision as on stock selection itself.",
    },
}
