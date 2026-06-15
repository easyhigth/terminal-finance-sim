"""
lessons_en.py — English Academy lessons (mirror of data/lessons.LESSONS).

Keyed by lesson id; each value has title/body/formula/example/takeaway in EN.
Topics are mapped via TOPIC_EN. Selected at runtime by core.i18n language.
"""

TOPIC_EN = {
    "Valorisation": "Valuation", "Risque": "Risk", "Taux": "Rates",
    "Dérivés": "Derivatives", "Crédit": "Credit", "Marché": "Market",
    "Performance": "Performance", "Macro": "Macro", "M&A": "M&A",
    "Comportement": "Behavioural", "ESG": "ESG", "Banque": "Banking",
    "Bloomberg": "Bloomberg",
}

LESSONS_EN = {
    "pe": {"title": "P/E ratio",
           "body": "The Price/Earnings ratio compares price to earnings per share. It "
                   "says how many years of earnings you pay for a share. A high P/E "
                   "reflects strong growth expectations — or an expensive stock.",
           "formula": "P/E = Price / EPS   (EPS = Net income / Shares)",
           "example": "Stock at 200, EPS 10 → P/E = 20x (you pay 20 years of earnings).",
           "takeaway": "Always compare a P/E to sector peers (see RV)."},
    "ev_ebitda": {"title": "EV / EBITDA",
           "body": "Enterprise Value includes net debt: the cost to buy the whole firm. "
                   "Over EBITDA it neutralises capital structure and tax — ideal to "
                   "compare companies.",
           "formula": "EV = Market cap + Net debt ;  multiple = EV / EBITDA",
           "example": "Cap 800, net debt 200 → EV 1000 ; EBITDA 100 → 10x.",
           "takeaway": "EV/EBITDA beats P/E when comparing differently-levered firms."},
    "dcf": {"title": "DCF",
           "body": "The Discounted Cash Flow discounts future free cash flows at the "
                   "WACC and adds a terminal value. It is intrinsic value, independent "
                   "of market mood.",
           "formula": "TV = FCF×(1+g)/(WACC − g) ;  Value = Σ FCF/(1+WACC)^t + disc. TV",
           "example": "FCF 100, g 2.5%, WACC 9% → TV = 100×1.025/0.065 ≈ 1577.",
           "takeaway": "DCF is very sensitive to WACC and g: test several scenarios."},
    "capvsev": {"title": "Market cap vs EV",
           "body": "Market cap = equity value (price × shares). Enterprise Value = value "
                   "of the whole firm (equity + debt − cash). Two firms with equal cap "
                   "can have very different EVs.",
           "formula": "Cap = Price × Shares ;  EV = Cap + Net debt",
           "example": "Cap 500 + net debt 300 = EV 800.",
           "takeaway": "Asset multiples (EBITDA, sales) go with EV."},
    "diversification": {"title": "Diversification & correlation",
           "body": "Combining weakly-correlated assets cuts risk without sacrificing "
                   "expected return — the only 'free lunch' in finance. The lower the "
                   "correlation (even negative), the stronger the effect.",
           "formula": "σ²(A+B) = w²σ²A + w²σ²B + 2w²·ρ·σA·σB",
           "example": "Two assets correlated +0.9: little effect. At −0.2: strong cut.",
           "takeaway": "Diversify sectors AND regions (see ALLOCATE, REBALANCE)."},
    "sharpe": {"title": "Sharpe ratio",
           "body": "The Sharpe measures excess return per unit of total risk. It lets "
                   "you compare strategies of different risk levels.",
           "formula": "Sharpe = (return − risk-free) / volatility",
           "example": "Return 12%, risk-free 2%, vol 16% → (0.12−0.02)/0.16 = 0.63.",
           "takeaway": "An abnormally high Sharpe should raise suspicion (hidden risk)."},
    "var": {"title": "VaR & CVaR",
           "body": "Value-at-Risk is the loss that will be exceeded only with low "
                   "probability over a horizon. CVaR (Expected Shortfall) is the AVERAGE "
                   "loss beyond the VaR: it captures the extreme tail.",
           "formula": "VaR 99% 1d: 1% chance of losing more than this in a day",
           "example": "VaR 99% 1d = €1M: 1 day in 100, the loss exceeds €1M.",
           "takeaway": "VaR doesn't cap the max loss; watch CVaR and stress (RISK)."},
    "beta": {"title": "Beta & market risk",
           "body": "Beta measures an asset's sensitivity to the market. Beta 1 = moves "
                   "with the market; >1 amplifies; <1 dampens. Market (systematic) risk "
                   "can't be diversified away, unlike specific risk.",
           "formula": "E[r] = rf + β·(E[rm] − rf)   (CAPM)",
           "example": "Beta 1.4: if the market does +10%, the asset tends to +14%.",
           "takeaway": "Lower beta to hedge market risk (see HEDGE)."},
    "options": {"title": "Options: call & put",
           "body": "A call gives the right to BUY at a strike; a put, to SELL. Used to "
                   "speculate with leverage or to hedge. The buyer pays a premium; their "
                   "loss is capped at that premium.",
           "formula": "Call at expiry = max(S − K, 0) ;  Put = max(K − S, 0)",
           "example": "Call K=100, premium 5. At S=120: gain 120−100−5 = 15.",
           "takeaway": "Buying puts protects a portfolio on the downside (insurance)."},
    "greeks": {"title": "The Greeks",
           "body": "The Greeks measure an option's price sensitivity. Delta (to the "
                   "underlying), Gamma (delta's change), Vega (volatility), Theta (time), "
                   "Rho (rates). Essential to run an options book.",
           "formula": "Delta ∈ [0,1] for a call ; Gamma peaks ATM near expiry",
           "example": "Negative theta: an option loses value each passing day.",
           "takeaway": "The QUANT module computes Black-Scholes and the Greeks live."},
    "rates": {"title": "Interest rates & markets",
           "body": "When the central bank hikes rates, money costs more: existing bonds "
                   "fall, growth stocks and real estate suffer, banks can enjoy wider "
                   "margins.",
           "formula": "Bond price ↓ when rates ↑ (inverse relationship)",
           "example": "Rates 2%→4%: real estate and unprofitable tech sell off.",
           "takeaway": "Track macro via ECO: rates, inflation, growth drive everything."},
    "yield_curve": {"title": "Yield curve & inversion",
           "body": "The yield curve links rates to maturities. Normally upward (long "
                   "pays more). When it INVERTS (short > long), the market expects a "
                   "slowdown: a historical recession signal.",
           "formula": "Spread 10y − 2y < 0  →  inverted curve",
           "example": "10y at 3.5% and 2y at 4.2%: spread −0.7% = inversion.",
           "takeaway": "A lasting inversion often precedes an economic downturn."},
    "lbo": {"title": "The LBO",
           "body": "A Leveraged Buy-Out buys a firm mostly with debt. Leverage "
                   "amplifies equity returns (IRR) if all goes well — and losses if not. "
                   "Deleveraging creates value.",
           "formula": "IRR amplified by leverage ;  MOIC = exit value / invested capital",
           "example": "Entry 100 (20 equity + 80 debt), exit 160, debt repaid to 40 "
                      "→ equity = 120 for 20 invested = MOIC 6x.",
           "takeaway": "More leverage = more potential IRR but more default risk."},
    "accretion": {"title": "Accretive / dilutive",
           "body": "An acquisition is accretive if it raises the acquirer's EPS, "
                   "dilutive if it lowers it. Paying with expensive shares to buy cheaper "
                   "ones tends to be accretive.",
           "formula": "Compare pro-forma (combined) EPS to the acquirer's stand-alone EPS",
           "example": "An acquirer at P/E 25 buying a target at P/E 15 in shares → accretive.",
           "takeaway": "The MA module simulates accretion/dilution and the LBO."},
    "bbg": {"title": "Bloomberg-style reflexes",
           "body": "A terminal is driven by keyboard function codes. Learn the "
                   "shortcuts: they save huge time and structure your analysis.",
           "formula": "DES profile · FA financials · GP chart · RV peers · WEI indices · "
                      "EQS screener · ECO macro · PRT portfolio",
           "example": "Typing 'DES MVC' opens the profile; 'RV MVC' compares it to peers.",
           "takeaway": "Type COMMANDS for the catalogue, and Tab to autocomplete."},
    "convexity": {"title": "Bond convexity",
           "body": "Duration approximates rate sensitivity with a straight line; "
                   "convexity corrects for the curvature. High convexity gains more when "
                   "rates fall and loses less when they rise.",
           "formula": "ΔP/P ≈ −D*·Δy + ½·Convexity·(Δy)²",
           "example": "Two bonds of equal duration: the more convex one outperforms on a "
                      "large rate move.",
           "takeaway": "At equal duration, prefer convexity when rate vol rises."},
    "carry_roll": {"title": "Carry & roll-down",
           "body": "Carry is the return earned if the market doesn't move: coupon + "
                   "roll-down (the bond 'slides' down an upward curve, its yield falling, "
                   "so its price rising).",
           "formula": "Bond carry ≈ coupon + roll-down ;  FX carry = rate differential",
           "example": "On a steep curve, holding the 5y pays even without a rate fall.",
           "takeaway": "A position can profit from carry alone — but the carry trade "
                       "reverses brutally."},
    "forwards": {"title": "Forwards, futures & cost of carry",
           "body": "A forward contract sets a future exchange price today. The forward "
                   "price comes from the cost of carry (funding, less income, plus "
                   "storage). Futures are standardised and post margin.",
           "formula": "F = S·(1 + r − income + storage)^T",
           "example": "Spot 100, rate 5%, 1 year, no dividend → forward ≈ 105.",
           "takeaway": "An abnormal spot/forward gap is an arbitrage (cash-and-carry)."},
    "contango": {"title": "Contango, backwardation & roll yield",
           "body": "The futures curve links price and maturity. In contango (futures > "
                   "spot), rolling contracts costs (negative roll yield); in "
                   "backwardation (futures < spot), it pays.",
           "formula": "Roll yield ≈ (near price − far price) / far price",
           "example": "An oil ETF in contango underperforms spot due to negative roll.",
           "takeaway": "On commodities, curve structure matters as much as spot."},
    "structured": {"title": "Structured products",
           "body": "A structured product combines a bond leg and options to create a "
                   "non-linear payoff: (partial) capital guarantee, conditional coupons, "
                   "barriers. It carries the issuer's credit risk.",
           "formula": "E.g. capital guaranteed = zero-coupon + call ; reverse convertible "
                      "= bond − sold put",
           "example": "An autocallable is called with a coupon if the underlying stays "
                      "above a level.",
           "takeaway": "Always check WHO the product benefits: payoff, barriers, issuer."},
    "credit_el": {"title": "Credit risk: EL = PD·LGD·EAD",
           "body": "A credit's expected loss combines probability of default (PD), loss "
                   "given default (LGD) and exposure at default (EAD). The structural "
                   "approach (Merton) sees equity as a call on the firm's assets.",
           "formula": "Expected Loss = PD × LGD × EAD",
           "example": "PD 2%, LGD 45%, EAD €1M → expected loss €9,000.",
           "takeaway": "Provision the EXPECTED loss; capital covers the UNEXPECTED loss."},
    "securitisation": {"title": "Securitisation & tranches",
           "body": "A pool of loans sits in an SPV that issues tranched securities. The "
                   "waterfall makes losses hit equity first, then mezzanine, then senior "
                   "(subordination).",
           "formula": "Losses: equity → mezzanine → senior ;  cash flows: reverse",
           "example": "A rise in defaults wipes equity before touching mezzanine.",
           "takeaway": "Senior looks safe — unless defaults correlate more than expected."},
    "microstructure": {"title": "Order book & execution",
           "body": "The book shows bid/ask and depth. A market order fills fast but pays "
                   "the spread and impact; a limit order controls price but may not fill. "
                   "Large orders 'eat' several levels (slippage).",
           "formula": "Spread = ask − bid ;  Mid = (bid + ask)/2",
           "example": "An order too large for the depth moves the price against you.",
           "takeaway": "Match the order type to liquidity: market if urgent, limit if patient."},
    "liquidity": {"title": "Liquidity, repo & spiral",
           "body": "Market liquidity (selling without impact) and funding liquidity "
                   "(refinancing via repo) deteriorate together in a crisis. Rising "
                   "haircuts force you to post more collateral.",
           "formula": "Spiral: drop → losses → margin calls → forced sales → drop",
           "example": "A haircut going from 5% to 20% nearly doubles required collateral.",
           "takeaway": "Leverage turns a price shock into a deadly liquidity problem."},
    "drawdown": {"title": "Drawdown, Sortino & Calmar",
           "body": "Max drawdown is the worst peak-to-trough fall suffered: the real "
                   "pain of the investor. The Sortino penalises only downside volatility; "
                   "the Calmar divides return by max drawdown.",
           "formula": "Sortino = (R − target)/σ_downside ;  Calmar = annual return / max DD",
           "example": "Two strategies with equal Sharpe: prefer the one with smaller drawdown.",
           "takeaway": "A good Sharpe says nothing about the depth of the troughs: watch drawdown."},
    "twr_mwr": {"title": "TWR vs MWR",
           "body": "Time-Weighted Return neutralises inflows/outflows and measures the "
                   "manager's skill. Money-Weighted (IRR) includes the timing of flows "
                   "and reflects the investor's real experience.",
           "formula": "TWR = Π(1 + r_period) − 1 ;  MWR = IRR of cash flows",
           "example": "A good manager can show a poor MWR if the client invests at the worst time.",
           "takeaway": "To judge the manager: TWR. To judge the client experience: MWR."},
    "factors": {"title": "Factors & styles (Fama-French)",
           "body": "Beyond the market, factors explain returns: size (small/big), value "
                   "(cheap/growth), profitability, investment. A portfolio carries factor "
                   "biases.",
           "formula": "R = α + β_mkt·MKT + β_size·SMB + β_value·HML + …",
           "example": "A 'value' fund suffers when growth leads, and vice versa.",
           "takeaway": "Diagnose style biases: they explain performance more than stock-picking."},
    "behavioural": {"title": "Biases & behavioural finance",
           "body": "Biases degrade decisions: anchoring (fixating on a price), loss "
                   "aversion, disposition (selling winners, keeping losers), herding "
                   "(following the crowd, amplifying bubbles and crashes).",
           "formula": "Loss aversion: a loss hurts ≈ 2× the pleasure of an equal gain",
           "example": "Keeping a losing position 'to get even' = disposition effect.",
           "takeaway": "A written rule (stop-loss, rebalancing) protects you from your own biases."},
    "esg": {"title": "ESG & green finance",
           "body": "ESG integration (environment, social, governance) manages "
                   "sustainability risks and opportunities. Green bonds fund green "
                   "projects; transition risk targets carbon-heavy assets.",
           "formula": "Approaches: exclusion · best-in-class · engagement · impact",
           "example": "A governance scandal can sink a stock overnight.",
           "takeaway": "ESG is also a RISK lens, not just ethics."},
    "bank_ratios": {"title": "Capital, liquidity & ALM",
           "body": "A bank must hold ratios: CET1 (core capital / RWA), LCR/NSFR "
                   "(liquidity), leverage ratio. ALM manages rate and liquidity risk "
                   "between assets and liabilities (duration gap).",
           "formula": "CET1 = core capital / RWA ;  DSCR = cash flow / debt service",
           "example": "Hitting a regulatory threshold forces risk reduction (sell RWA).",
           "takeaway": "Capital absorbs losses; liquidity avoids sudden death."},
}
