"""
missions_en.py — Traduction EN des structures statiques de core/missions.py :
_SECTOR_LABELS (libellés de secteur) et _PORTFOLIO_TASKS (banque de tâches
portefeuille/hedging : prompt, choix, idx correct, explication).
Sélectionnées via core.missions._L() / get_lang().
"""

SECTOR_LABELS_EN = {
    "Tech": "Technology", "Semicon": "Semiconductors", "Luxe": "Luxury",
    "Conso": "Consumer", "Finance": "Finance", "Energie": "Energy",
    "Sante": "Healthcare", "Industrie": "Industrials", "Agro": "Agribusiness",
    "Telecom": "Telecom", "Utilities": "Utilities",
    "Materiaux": "Materials", "Immobilier": "Real Estate", "Auto": "Automotive",
}

# Banque de tâches portefeuille / hedging — version EN, alignée par index avec
# core.missions._PORTFOLIO_TASKS. (prompt, choix, idx correct, expl)
PORTFOLIO_TASKS_EN = [
    ("Portfolio heavily concentrated in tech (beta 1.4). To reduce market risk:",
     ["Sell index futures", "Double the tech position",
      "Buy tech small caps", "Do nothing"], 0,
     "Selling index futures reduces the portfolio's directional (beta) exposure."),
    ("You hold $8M of stocks and fear a short-term drop without wanting to sell. "
     "The most targeted hedge:",
     ["Buy puts (put options)", "Buy calls",
      "Buy the index", "Increase leverage"], 0,
     "Puts offer downside protection while keeping upside potential."),
    ("Two assets correlated at +0.9. Does combining them strongly reduce risk?",
     ["No, correlation too high", "Yes, very strongly",
      "It doubles the risk", "No effect on risk"], 0,
     "Diversification only works well when correlation is low (or negative)."),
    ("'Risk parity' approach: allocation is set so that…",
     ["each asset contributes equally to risk", "dollar weights are equal",
      "beta is zero", "return is maximized"], 0,
     "Risk parity equalizes risk contributions, not dollar amounts invested."),
    ("Hedge $10M of stocks with beta 1.3 using index futures (beta 1). Notional ≈ ?",
     ["$13M", "$10M", "$7.7M", "$1.3M"], 0,
     "Notional = exposure × beta = $10M × 1.3 = $13M (beta-adjusted hedge)."),
    ("US assets held by a euro-denominated fund. Hedge the FX risk:",
     ["Sell USD forward", "Buy more US stocks",
      "Buy gold", "Do nothing"], 0,
     "Selling USD forward neutralizes the EUR/USD exposure on dollar-denominated assets."),
    ("To reduce the SPECIFIC (idiosyncratic) risk of a portfolio:",
     ["Diversify across more issuers", "Concentrate on one stock",
      "Increase leverage", "Buy calls"], 0,
     "Specific risk can be diversified away; market risk cannot."),
    ("A portfolio with beta 0 is:",
     ["market-neutral", "risk-free", "zero-return", "100% cash"], 0,
     "Beta 0 = insensitive to the market (market-neutral), but not free of all risk."),
]
