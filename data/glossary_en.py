"""
glossary_en.py — English glossary (mirror of data/glossary_data.GLOSSARY).

Same keys as the French glossary; each entry is (category_en, definition_en).
Selected at runtime via core.i18n language. Self-contained (no import of the
French module) to avoid import cycles.
"""

# Noms d'affichage EN pour les termes dont la CLÉ est française (la clé reste
# l'identifiant ; seul l'affichage change). Les termes neutres/anglais sont omis.
NAME_EN = {
    "Valeur terminale": "Terminal value", "Obligation": "Bond", "Action": "Stock",
    "Dérivé": "Derivative", "Option Call": "Call option", "Option Put": "Put option",
    "Volatilité implicite": "Implied volatility", "Taux continu": "Continuous compounding",
    "Modèle de Gordon": "Gordon model", "Convexité": "Convexity",
    "Courbe des taux": "Yield curve", "Taux spot / forward": "Spot / forward rate",
    "PIB": "GDP", "Taux réel": "Real rate", "TIPS / OATi": "TIPS / linkers",
    "Taux directeur": "Policy rate", "Volatilité réalisée": "Realised volatility",
    "Spread de crédit": "Credit spread", "Modèle de Merton": "Merton model",
    "Titrisation": "Securitisation", "Carnet d'ordres": "Order book",
    "Ordre marché / limite": "Market / limit order", "Impact de marché": "Market impact",
    "Spirale de liquidité": "Liquidity spiral", "Bilan": "Balance sheet",
    "Compte de résultat": "Income statement", "Tableau de flux": "Cash flow statement",
    "Bâle III": "Basel III", "Devoir fiduciaire": "Fiduciary duty",
    "Muraille de Chine": "Chinese wall", "Produit structuré": "Structured product",
    "Biais d'ancrage": "Anchoring bias", "Aversion aux pertes": "Loss aversion",
    "Biais de confirmation": "Confirmation bias", "Régime de marché": "Market regime",
    "Taxonomie verte": "Green taxonomy", "Risque de transition": "Transition risk",
    "Facteurs (Fama-French)": "Factors (Fama-French)", "Rendement log": "Log return",
    "Attribution de performance": "Performance attribution",
}


def display_name(term, lang):
    return NAME_EN.get(term, term) if lang == "en" else term


GLOSSARY_EN = {
    # --- Valuation -------------------------------------------------------
    "DCF": ("Valuation", "Discounted Cash Flow: values a firm by discounting its "
        "future free cash flows at the WACC and adding a terminal value."),
    "WACC": ("Valuation", "Weighted Average Cost of Capital: blended after-tax cost "
        "of debt and equity; the discount rate in a DCF."),
    "Valeur terminale": ("Valuation", "Terminal value: the firm's value beyond the "
        "explicit forecast, via Gordon growth or an exit multiple."),
    "EV/EBITDA": ("Valuation", "Enterprise value over EBITDA: compares firms "
        "regardless of capital structure and tax."),
    "FCF": ("Valuation", "Free Cash Flow: cash generated after capex, available to "
        "capital providers."),
    "Comparables": ("Valuation", "Relative valuation from peer trading multiples or "
        "precedent transactions."),
    "PV / FV": ("Valuation", "Present/Future Value: PV = FV/(1+r)^n discounts a future "
        "cash flow; FV = PV·(1+r)^n compounds a present amount."),
    "NPV": ("Valuation", "Net Present Value: sum of discounted cash flows (t0 often "
        "negative). NPV > 0 means value-creating."),
    "IRR": ("Valuation", "Internal Rate of Return: the rate that sets NPV to zero; "
        "accept if it beats the cost of capital."),
    "EAR": ("Valuation", "Effective Annual Rate accounting for compounding: "
        "(1 + r/m)^m − 1 for m periods per year."),
    "Taux continu": ("Valuation", "Continuous compounding: FV = PV·e^(r·t); used in "
        "derivatives theory (Black-Scholes)."),
    "Modèle de Gordon": ("Valuation", "Gordon growth: Price = D1/(re − g); values a "
        "stock by perpetually growing dividends. Very sensitive to (re − g)."),
    "FCFE": ("Valuation", "Free Cash Flow to Equity: cash for shareholders; "
        "discounted at the cost of equity → equity value."),
    "FCFF": ("Valuation", "Free Cash Flow to Firm: cash for all capital providers; "
        "discounted at the WACC → enterprise value."),
    "P/E": ("Valuation", "Price/Earnings: price over EPS; years of earnings paid. A "
        "high P/E signals growth expectations — or an expensive stock."),
    "P/B": ("Valuation", "Price/Book: price over book value per share; useful for "
        "financials and asset-heavy firms."),
    "P/S": ("Valuation", "Price/Sales: market cap over revenue; useful when earnings "
        "are negative or volatile."),
    "EV": ("Valuation", "Enterprise Value = market cap + net debt: the cost to buy "
        "the whole firm; basis for asset multiples."),
    # --- Instruments -----------------------------------------------------
    "Obligation": ("Instruments", "Bond: a debt security paying periodic coupons and "
        "repaying principal at maturity; price moves inversely to rates."),
    "YTM": ("Instruments", "Yield to Maturity: the discount rate equating a bond's "
        "cash flows to its market price."),
    "Duration": ("Instruments", "Price sensitivity to rates; Macaulay duration is the "
        "cash-flow-weighted average maturity, modified duration the % price change."),
    "Action": ("Instruments", "Stock: an ownership share in a company, with dividend "
        "and voting rights."),
    "Dérivé": ("Instruments", "Derivative: an instrument whose value depends on an "
        "underlying (stock, rate, commodity). E.g. options, futures, swaps."),
    "Option Call": ("Instruments", "The right (not obligation) to BUY an underlying at "
        "a strike; gains value as the underlying rises."),
    "Option Put": ("Instruments", "The right to SELL an underlying at a strike; gains "
        "value as the underlying falls; common hedge."),
    "Swap": ("Instruments", "A contract to exchange cash flows, e.g. fixed for "
        "floating rate (IRS) or two currencies (cross-currency)."),
    # --- Options ---------------------------------------------------------
    "Black-Scholes": ("Options", "Pricing model for European options assuming "
        "geometric Brownian motion. Inputs: spot, strike, maturity, rate, vol."),
    "Volatilité implicite": ("Options", "Implied volatility: the vol that, fed into "
        "Black-Scholes, returns the market option price; the market's expectation."),
    "Delta": ("Options", "Greek: option price sensitivity to a 1-unit move in the "
        "underlying; used for delta-hedging."),
    "Gamma": ("Options", "Greek: rate of change of delta; highest near the money and "
        "close to expiry."),
    "Vega": ("Options", "Greek: option price sensitivity to a 1-point change in "
        "volatility."),
    "Theta": ("Options", "Greek: time decay; the option's value erodes as expiry "
        "approaches."),
    # --- Portfolio -------------------------------------------------------
    "Efficient Frontier": ("Portfolio", "Markowitz efficient frontier: portfolios with "
        "the highest return for each level of risk (or lowest risk per return)."),
    "Sharpe Ratio": ("Portfolio", "Excess return over the risk-free rate per unit of "
        "volatility; risk-adjusted return."),
    "Beta": ("Portfolio", "Sensitivity to market moves; beta > 1 = more volatile than "
        "the market; the CAPM's market factor."),
    "CAPM": ("Portfolio", "Capital Asset Pricing Model: expected return = risk-free + "
        "beta × market risk premium."),
    "Diversification": ("Portfolio", "Reducing specific risk by combining weakly "
        "correlated assets; does not remove systematic (market) risk."),
    "CML": ("Portfolio", "Capital Market Line: combinations of the risk-free asset and "
        "the tangency (max-Sharpe) portfolio — the best risk/return available."),
    "Facteurs (Fama-French)": ("Portfolio", "Systematic return sources: market, size "
        "(small/big), value (book-to-market), plus profitability and investment."),
    "Momentum": ("Portfolio", "Factor/signal: recent winners tend to keep winning "
        "short to medium term; prone to sharp reversals."),
    "Mean reversion": ("Portfolio", "Signal: prices/spreads tend to revert to a mean; "
        "opposite of momentum, useful in range-bound markets."),
    "Value vs Growth": ("Portfolio", "Style: value (cheap on fundamentals) vs growth "
        "(high expected growth, rich multiples); leadership alternates by regime."),
    "Risk parity": ("Portfolio", "Allocation where each asset contributes equally to "
        "total risk (not capital), often with leverage on the bond sleeve."),
    # --- Risk ------------------------------------------------------------
    "VaR": ("Risk", "Value at Risk: the loss not exceeded at a confidence level over "
        "a horizon (e.g. 95% 1-day). Says nothing about tail severity."),
    "CVaR": ("Risk", "Conditional VaR (Expected Shortfall): the average loss beyond "
        "the VaR; captures the tail."),
    "Stress Test": ("Risk", "Simulating extreme scenarios (crash, rate shock) to "
        "assess a portfolio's or institution's resilience."),
    "Hedge": ("Risk", "A position taken to offset the risk of another (e.g. buying "
        "puts to protect a stock portfolio)."),
    # --- M&A -------------------------------------------------------------
    "M&A": ("M&A", "Mergers & Acquisitions: combining two firms (merger) or buying a "
        "target (acquisition)."),
    "LBO": ("M&A", "Leveraged Buyout: buying a company mostly with debt repaid by its "
        "cash flows; targets a high IRR on invested equity."),
    "Synergies": ("M&A", "Gains expected from a merger: cost savings (cost synergies) "
        "or higher revenue (revenue synergies)."),
    "Due Diligence": ("M&A", "In-depth audit of a target (financial, legal, tax, "
        "operational) before a transaction."),
    "Accretion/Dilution": ("M&A", "Whether an acquisition raises (accretive) or lowers "
        "(dilutive) the acquirer's EPS."),
    "Goodwill": ("M&A", "Excess of price paid over the fair value of net assets "
        "acquired; an asset tested for impairment."),
    # --- Accounting ------------------------------------------------------
    "EBITDA": ("Accounting", "Earnings Before Interest, Taxes, Depreciation & "
        "Amortization: a proxy for operating profitability."),
    "Bilan": ("Accounting", "Balance sheet: Assets = Liabilities + Equity; a snapshot "
        "of the firm's position at a date."),
    "Compte de résultat": ("Accounting", "Income statement (P&L): revenue, expenses "
        "and net income over a period."),
    "Tableau de flux": ("Accounting", "Cash Flow Statement: splits cash into "
        "operating, investing and financing activities."),
    "ROE": ("Accounting", "Return on Equity: net income over shareholders' equity; "
        "profitability for owners."),
    "Working Capital": ("Accounting", "Current assets minus current liabilities; "
        "funds the operating cycle."),
    # --- Regulation ------------------------------------------------------
    "MiFID II": ("Regulation", "EU directive on financial markets: transparency, "
        "investor protection, transaction reporting."),
    "Bâle III": ("Regulation", "International bank prudential framework: capital "
        "(CET1), leverage and liquidity (LCR, NSFR) ratios."),
    "Dodd-Frank": ("Regulation", "US post-2008 law tightening financial regulation "
        "(Volcker Rule, systemic risk oversight)."),
    "IFRS": ("Regulation", "International Financial Reporting Standards used in Europe "
        "and many countries."),
    "US GAAP": ("Regulation", "US accounting standards, distinct from IFRS on several "
        "treatments."),
    "SEC": ("Regulation", "Securities and Exchange Commission: US markets regulator — "
        "disclosure, anti-fraud, supervision."),
    "Volcker Rule": ("Regulation", "Dodd-Frank provision limiting proprietary trading "
        "by deposit-taking banks."),
    "RWA": ("Regulation", "Risk-Weighted Assets: assets weighted by risk; the "
        "denominator of capital ratios."),
    "CET1": ("Regulation", "Common Equity Tier 1 / RWA: the core bank solvency ratio "
        "under Basel III."),
    "LCR / NSFR": ("Regulation", "Liquidity Coverage Ratio (liquid assets / 30-day "
        "outflows) and Net Stable Funding Ratio (stable funding / 1-year needs)."),
    "Leverage ratio": ("Regulation", "Capital / total exposure, unweighted; caps a "
        "bank's overall leverage."),
    "ALM": ("Regulation", "Asset-Liability Management: managing the banking book's "
        "rate and liquidity risk (rate/duration gaps)."),
    "Best execution": ("Regulation", "Duty to obtain the best possible result for the "
        "client (price, cost, speed, likelihood of execution)."),
    "Devoir fiduciaire": ("Regulation", "Fiduciary duty: acting in the client's sole "
        "interest, ahead of the firm's."),
    "Insider trading": ("Regulation", "Trading on material non-public information; "
        "illegal and heavily penalised."),
    "Muraille de Chine": ("Regulation", "Chinese wall: an information barrier between "
        "conflicting teams (e.g. M&A vs trading) to prevent market abuse."),
    # --- Rates & bonds ---------------------------------------------------
    "Convexité": ("Rates & bonds", "Curvature of the price/yield relation: "
        "ΔP/P ≈ −D*·Δy + ½·Convexity·Δy². Higher convexity helps when rates fall."),
    "Clean vs Dirty price": ("Rates & bonds", "Clean = quoted price ex accrued "
        "coupon; dirty = clean + accrued, the amount actually paid."),
    "Courbe des taux": ("Rates & bonds", "Yield curve: rate vs maturity. Normal "
        "(upward), flat, or inverted (short > long) — inversion often precedes recession."),
    "Taux spot / forward": ("Rates & bonds", "Spot: zero-coupon rate for a maturity. "
        "Forward: future rate implied between two dates from the spot curve."),
    "Roll-down": ("Rates & bonds", "On an upward curve, a bond that ages sees its "
        "yield fall → price rises, with no curve move."),
    "Carry": ("Rates & bonds", "Return if the market doesn't move. Bond: coupon + "
        "roll-down. FX: rate differential between two currencies."),
    "Carry trade": ("Rates & bonds", "Borrow in a low-rate currency, invest in a "
        "high-rate one; profitable until the exchange rate reverses."),
    # --- Macro -----------------------------------------------------------
    "PIB": ("Macro", "GDP: a measure of economic activity; its real growth drives "
        "earnings and the cycle."),
    "Inflation": ("Macro", "General rise in prices; guides the central bank; an "
        "inflation surprise repriced stocks and bonds sharply."),
    "Taux réel": ("Macro", "Real rate: nominal rate adjusted for inflation ≈ nominal "
        "− expected inflation (Fisher). What matters for purchasing power."),
    "TIPS / OATi": ("Macro", "Inflation-linked bonds: principal or coupons track a "
        "price index; protect against inflation but sensitive to real rates."),
    "Output gap": ("Macro", "Gap between actual and potential GDP. Positive = "
        "overheating (inflation pressure); negative = slack."),
    "Taux directeur": ("Macro", "Policy rate set by the central bank. Hikes raise the "
        "cost of credit: weigh on growth stocks and real estate, can help bank margins."),
    "QE / QT": ("Macro", "Quantitative Easing (asset purchases, liquidity) / "
        "Tightening (balance-sheet shrink). Unconventional tools acting on long rates."),
    "Hawkish / Dovish": ("Macro", "Central-bank tone: hawkish (restrictive, "
        "anti-inflation, rates up) vs dovish (accommodative, pro-growth, rates down)."),
    # --- Derivatives & vol -----------------------------------------------
    "Forward / Future": ("Derivatives & vol", "Commitment to buy/sell an underlying at "
        "a future date at a set price. Future = standardised, exchange-traded, margined; "
        "forward = OTC."),
    "Cost of carry": ("Derivatives & vol", "Forward price ≈ S0·(1+r)^T (less "
        "income, plus storage). Links the forward to the spot via carrying cost."),
    "Contango": ("Derivatives & vol", "Upward futures curve (futures > spot), often "
        "due to storage costs; gives a negative roll yield."),
    "Backwardation": ("Derivatives & vol", "Downward futures curve (futures < spot); "
        "reflects scarcity or strong immediate demand; positive roll yield."),
    "Roll yield": ("Derivatives & vol", "Return from rolling futures at expiry; "
        "negative in contango, positive in backwardation."),
    "IRS": ("Derivatives & vol", "Interest Rate Swap: exchanging fixed for floating "
        "rate cash flows; transforms/hedges a balance sheet's rate exposure."),
    "Cross-currency swap": ("Derivatives & vol", "Exchange of principal and interest "
        "in two different currencies; manages FX and multi-currency funding risk."),
    "Volatilité réalisée": ("Derivatives & vol", "Realised volatility: the vol "
        "actually observed on past returns, vs implied volatility."),
    "Skew / Smile": ("Derivatives & vol", "Variation of implied vol by strike. The "
        "equity skew (pricier OTM puts) reflects demand for downside protection."),
    "VIX": ("Derivatives & vol", "Implied-volatility index (the 'fear gauge') from "
        "index options; spikes during market shocks."),
    "Moneyness": ("Derivatives & vol", "Underlying vs strike: in-the-money (ITM), "
        "at-the-money (ATM), out-of-the-money (OTM)."),
    "Covered call": ("Derivatives & vol", "Hold the stock and sell a call: earn a "
        "premium, cap the upside. A yield strategy in calm markets."),
    "Protective put": ("Derivatives & vol", "Hold the stock and buy a put: downside "
        "insurance for a premium; a known loss floor."),
    # --- Credit & securitisation -----------------------------------------
    "PD / LGD / EAD": ("Credit & securitisation", "Probability of Default, Loss Given "
        "Default, Exposure at Default. Building blocks of credit risk: EL = PD × LGD × EAD."),
    "Expected Loss": ("Credit & securitisation", "Expected loss of a credit: "
        "EL = PD × LGD × EAD; provisioned. Unexpected loss (UL) is the variability (capital)."),
    "Modèle de Merton": ("Credit & securitisation", "Structural approach: equity is a "
        "call on the firm's assets; default if assets fall below debt at maturity."),
    "Spread de crédit": ("Credit & securitisation", "Extra yield of a risky bond over "
        "a risk-free rate; pays for default risk; widens under stress."),
    "CDS": ("Credit & securitisation", "Credit Default Swap: insurance against an "
        "issuer's default — buyer pays a premium, gets compensated on a credit event."),
    "Titrisation": ("Credit & securitisation", "Securitisation: pooling loans in an "
        "SPV that issues tranched securities (senior/mezzanine/equity)."),
    "Tranches / Waterfall": ("Credit & securitisation", "Payment cascade: losses hit "
        "equity first, then mezzanine, then senior (subordination); cash flows up in reverse."),
    "Downgrade": ("Credit & securitisation", "A rating cut by an agency; widens the "
        "spread, may force sales and raise funding costs."),
    # --- Microstructure & liquidity --------------------------------------
    "Carnet d'ordres": ("Microstructure & liquidity", "Order book: limit buy (bid) and "
        "sell (ask) orders by price and time priority; shows market depth."),
    "Bid / Ask / Mid": ("Microstructure & liquidity", "Bid = best buy price, Ask = "
        "best sell price, Mid = their average. The bid-ask spread is the instant trading cost."),
    "Spread bid-ask": ("Microstructure & liquidity", "Gap between ask and bid. Tight = "
        "liquid; wide = illiquid. The implicit cost of a round trip."),
    "Ordre marché / limite": ("Microstructure & liquidity", "Market: immediate fill at "
        "the best price (no price control). Limit: set price, but no guaranteed fill."),
    "Slippage": ("Microstructure & liquidity", "Gap between expected and actual "
        "execution price, due to order size or a fast-moving market."),
    "Impact de marché": ("Microstructure & liquidity", "An order's effect on price: a "
        "large order eats several book levels and moves the price against you."),
    "Dark pool": ("Microstructure & liquidity", "A venue with a hidden book where large "
        "orders execute without revealing size (limits market impact)."),
    "Circuit breaker": ("Microstructure & liquidity", "A trading halt mechanism on "
        "extreme moves, meant to calm panic."),
    "Repo": ("Microstructure & liquidity", "Sale of a security with a repurchase "
        "agreement: a collateralised loan; core of short-term funding liquidity."),
    "Haircut": ("Microstructure & liquidity", "Discount on collateral value (e.g. 2% "
        "on AAA, 20% on high yield); rises with perceived risk → more collateral required."),
    "Spirale de liquidité": ("Microstructure & liquidity", "Falling prices → losses → "
        "margin calls → forced sales → further falls. Amplified by leverage and rising correlations."),
    "CCP / IM / VM": ("Microstructure & liquidity", "Central counterparty between "
        "parties. Initial Margin (upfront collateral) + Variation Margin (daily mark-to-market)."),
    # --- Asset management ------------------------------------------------
    "NAV": ("Asset management", "Net Asset Value: a fund unit's value = (assets − "
        "liabilities) / units. Basis for subscriptions/redemptions."),
    "ETF": ("Asset management", "Exchange-Traded Fund: a listed fund; market makers "
        "arbitrage the gap between market price and NAV."),
    "Management fee": ("Asset management", "Annual management fee, a % of assets (e.g. "
        "1%/yr), charged regardless of performance."),
    "Performance fee": ("Asset management", "A cut of outperformance (e.g. 20%), often "
        "above a hurdle and a high-water mark."),
    "High-water mark": ("Asset management", "The highest value reached: the performance "
        "fee applies only above it, to avoid charging the same gain twice."),
    "Hurdle rate": ("Asset management", "Minimum return to clear before a performance "
        "fee is charged."),
    "TWR vs MWR": ("Asset management", "Time-Weighted Return neutralises flows and "
        "measures the manager's skill. Money-Weighted (IRR) reflects the investor's experience."),
    "Attribution de performance": ("Asset management", "Breaking down performance: "
        "allocation vs selection effects, by asset class, sector, or factor."),
    "Prospectus": ("Asset management", "Document describing a fund's strategy, risks, "
        "fees and constraints (concentration, max leverage, sector/ESG limits)."),
    # --- Performance -----------------------------------------------------
    "Drawdown": ("Performance", "Decline from a peak. Max drawdown is the worst "
        "peak-to-trough fall; an intuitive gauge of investor pain."),
    "Sortino": ("Performance", "A Sharpe variant using only downside deviation; it "
        "doesn't penalise upside volatility."),
    "Calmar": ("Performance", "Average annual return over the max drawdown; compares "
        "performance adjusted for extreme-loss risk."),
    "Downside deviation": ("Performance", "Standard deviation of returns below a target "
        "only; measures downside risk, not total volatility."),
    "Treynor": ("Performance", "Excess return per unit of market risk (beta): "
        "(Rp − rf)/βp. Relevant for a well-diversified portfolio."),
    "Information ratio": ("Performance", "Outperformance vs benchmark over tracking "
        "error; measures the consistency of an active manager's alpha."),
    "Tracking error": ("Performance", "Standard deviation of the return difference vs "
        "a benchmark; measures active deviation."),
    "Rendement log": ("Performance", "Log return r = ln(V1/V0); additive over time, "
        "handy for annualising; close to simple return for small moves."),
    # --- Alternatives & ESG ----------------------------------------------
    "Private equity": ("Alternatives & ESG", "Investing in unlisted equity (LBO, "
        "growth, venture). Locked capital, J-curve, measured by IRR and multiples (MOIC)."),
    "J-curve": ("Alternatives & ESG", "A PE fund's return profile: negative early "
        "(fees, investments) then positive as holdings mature."),
    "Private debt": ("Alternatives & ESG", "Non-bank direct lending (direct lending, "
        "mezzanine). Illiquid, paid via an illiquidity and risk premium."),
    "Hedge fund": ("Alternatives & ESG", "A flexible fund (long/short, macro, "
        "arbitrage, event-driven) using leverage and derivatives; often '2 and 20'."),
    "REIT": ("Alternatives & ESG", "Real Estate Investment Trust: a listed property "
        "vehicle paying out most income; a stock/bond hybrid, very rate-sensitive."),
    "Infrastructure": ("Alternatives & ESG", "Real assets with long, steady (often "
        "regulated/indexed) cash flows. SPV-financed, defensive, rate-sensitive."),
    "Project finance / SPV": ("Alternatives & ESG", "Financing a project via a "
        "dedicated entity (SPV), repaid only by the project's cash flows (non/limited recourse)."),
    "DSCR": ("Alternatives & ESG", "Debt Service Coverage Ratio = available cash flow "
        "/ debt service. A key covenant: below a threshold, distributions are restricted."),
    "ESG": ("Alternatives & ESG", "Environmental, Social and Governance criteria. "
        "Approaches: exclusion, best-in-class, engagement, impact investing."),
    "Green bond": ("Alternatives & ESG", "A bond whose proceeds (use of proceeds) fund "
        "green projects. Variant: sustainability-linked bond (coupon tied to ESG targets)."),
    "Taxonomie verte": ("Alternatives & ESG", "Green taxonomy: regulatory "
        "classification of sustainable activities; underpins reporting and fights greenwashing."),
    "Risque de transition": ("Alternatives & ESG", "Risk from the shift to a low-carbon "
        "economy (regulation, carbon price, stranded assets); distinct from physical climate risk."),
    "Stablecoin": ("Alternatives & ESG", "A crypto-asset pegged to a reference (often "
        "the dollar), collateralised or algorithmic. Main risk: losing the peg (depeg)."),
    "CBDC": ("Alternatives & ESG", "Central Bank Digital Currency: a public digital "
        "alternative to private stablecoins (privacy and monetary-policy stakes)."),
    "Produit structuré": ("Alternatives & ESG", "A bond + derivatives combo with a "
        "non-linear payoff (autocallable, reverse convertible, capital-guaranteed). Issuer and structure risk."),
    # --- Behavioural -----------------------------------------------------
    "Biais d'ancrage": ("Behavioural", "Anchoring bias: fixating on a reference number "
        "(purchase price, peak) and unconsciously returning to it."),
    "Aversion aux pertes": ("Behavioural", "Loss aversion: a loss hurts more than an "
        "equivalent gain pleases; biases risk-taking."),
    "Disposition effect": ("Behavioural", "Tendency to sell winners too early and hold "
        "losers too long."),
    "Herding": ("Behavioural", "Herd behaviour: following the consensus, which "
        "amplifies bubbles and crashes."),
    "Biais de confirmation": ("Behavioural", "Confirmation bias: seeking only "
        "information that confirms an existing view, ignoring contrary signals."),
    "Régime de marché": ("Behavioural", "Market regime: a phase with stable properties "
        "— low vol/trend, high vol/uncertainty, or trendless range. Regimes alternate."),
}
