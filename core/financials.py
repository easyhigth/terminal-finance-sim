"""
financials.py — États financiers complets et COHÉRENTS par société.

Pour chaque société, on reconstruit :
  - un COMPTE DE RÉSULTAT : CA → coût des ventes → marge brute → (SG&A, R&D) →
    EBITDA → D&A → EBIT → intérêts → résultat avant impôt → impôt → résultat net.
    Le résultat net colle EXACTEMENT à revenue × net_margin (l'ancre utilisée
    partout ailleurs : fiche, earnings, valorisation) ; l'impôt est le solde de
    réconciliation → tout s'emboîte.
  - un BILAN : actifs courants (cash, créances, stocks) + immobilisations (PP&E,
    goodwill) ; passifs (dette, fournisseurs, autres) ; les capitaux propres sont
    le solde → Actif = Passif + Capitaux propres PAR CONSTRUCTION. La dette nette
    (dette − cash) recoupe exactement le net_debt de la société.

Trois exercices N / N-1 / N-2 (year_offset 0/1/2) dérivés d'une croissance
annuelle propre à chaque société. Les fondamentaux « N » viennent du marché
DYNAMIQUE (revenue/marges qui dérivent avec les earnings) : quand le temps de
jeu dépasse un an, l'exercice courant avance et les états se mettent à jour,
comme la fonction FA d'un terminal Bloomberg.

Tout est déterministe (aucun état aléatoire) : fonctions pures de (marché, ticker).
"""

# Profil financier par défaut (ratios en % du CA sauf mention). Les overrides
# sectoriels donnent du sens : tech = R&D haute/peu d'actifs ; utilities/télécom/
# immobilier = très capitalistiques ; finance = créances élevées, peu de stocks.
_DEFAULT = dict(
    sga_pct=0.10, rnd_pct=0.02, da_pct=0.05,        # charges (% CA)
    cost_of_debt=0.05, cash_rate=0.02,              # taux
    cash_pct=0.10, rec_pct=0.14, ppe_pct=0.45, gw_pct=0.20,   # actifs (% CA)
    inv_pct=0.18, pay_pct=0.15,                     # stocks/fournisseurs (% COGS)
    other_pct=0.10, growth=0.05,                    # autres passifs (% CA), croissance annuelle
)
_SECTOR = {
    "Tech":       dict(rnd_pct=0.12, da_pct=0.04, ppe_pct=0.20, inv_pct=0.05, gw_pct=0.35, growth=0.12),
    "Semicon":    dict(rnd_pct=0.15, da_pct=0.10, ppe_pct=0.70, inv_pct=0.20, growth=0.10),
    "Luxe":       dict(sga_pct=0.22, inv_pct=0.35, ppe_pct=0.35, growth=0.06),
    "Conso":      dict(sga_pct=0.14, inv_pct=0.25, growth=0.03),
    "Finance":    dict(da_pct=0.02, ppe_pct=0.10, inv_pct=0.0, cash_pct=0.30, rec_pct=0.40,
                       gw_pct=0.10, sga_pct=0.20, rnd_pct=0.0, growth=0.04),
    "Energie":    dict(da_pct=0.10, ppe_pct=0.90, inv_pct=0.10, rnd_pct=0.01, growth=0.02),
    "Sante":      dict(rnd_pct=0.15, sga_pct=0.18, ppe_pct=0.30, growth=0.07),
    "Industrie":  dict(da_pct=0.06, ppe_pct=0.55, inv_pct=0.22, sga_pct=0.12, growth=0.04),
    "Agro":       dict(ppe_pct=0.60, inv_pct=0.25, growth=0.03),
    "Telecom":    dict(da_pct=0.15, ppe_pct=1.00, rnd_pct=0.01, growth=0.02),
    "Utilities":  dict(da_pct=0.12, ppe_pct=1.20, rnd_pct=0.0, growth=0.02),
    "Materiaux":  dict(ppe_pct=0.80, inv_pct=0.20, growth=0.03),
    "Immobilier": dict(da_pct=0.08, ppe_pct=1.50, inv_pct=0.05, sga_pct=0.08, growth=0.04),
    "Auto":       dict(rnd_pct=0.06, ppe_pct=0.65, inv_pct=0.18, sga_pct=0.10, growth=0.04),
}


def _fp(ticker):
    """Empreinte déterministe d'un ticker dans [-1, 1] (variété sans aléa d'état)."""
    h = 0
    for ch in ticker:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return (h % 1000) / 500.0 - 1.0


def params(sector, ticker):
    """Ratios financiers d'une société (profil sectoriel + variété propre)."""
    p = dict(_DEFAULT)
    p.update(_SECTOR.get(sector, {}))
    fp = _fp(ticker)
    p["growth"] = max(-0.04, min(0.25, p["growth"] + 0.025 * fp))
    p["sga_pct"] = max(0.04, p["sga_pct"] + 0.02 * fp)
    return p


def annual_growth(market, ticker):
    """Croissance annuelle du CA propre à la société (déterministe)."""
    c = market.companies[market.ticker_idx[ticker]]
    return params(c["sector"], ticker)["growth"]


def _row(label, value):
    return {"label": label, "value": value}


def income_statement(market, ticker, year_offset=0):
    """Compte de résultat (en M de devise locale) pour l'exercice N-`year_offset`."""
    i = market.ticker_idx[ticker]
    c = market.companies[i]
    p = params(c["sector"], ticker)
    g = p["growth"]

    rev_n = float(market.revenue[i])
    revenue = rev_n / ((1 + g) ** year_offset)
    net_margin = float(market.net_margin[i])
    ebitda_margin = float(market.ebitda_margin[i])
    shares = c["shares"]
    net_debt = c["net_debt"] * (revenue / rev_n if rev_n else 1.0)

    # marge brute = EBITDA margin + SG&A + R&D  ->  COGS = CA × (1 − marge brute)
    gross_margin = min(0.92, ebitda_margin + p["sga_pct"] + p["rnd_pct"])
    cogs = revenue * (1 - gross_margin)
    gross = revenue - cogs
    sga = revenue * p["sga_pct"]
    rnd = revenue * p["rnd_pct"]
    ebitda = gross - sga - rnd                       # == revenue × ebitda_margin
    da = revenue * p["da_pct"]
    ebit = ebitda - da
    interest = max(0.0, net_debt) * p["cost_of_debt"] - max(0.0, -net_debt) * p["cash_rate"]
    ebt = ebit - interest
    net_income = revenue * net_margin                # ANCRE (cohérence globale)
    tax = ebt - net_income                           # solde de réconciliation
    eff_tax = (tax / ebt) if ebt > 0 else 0.0
    eps = net_income / shares if shares else 0.0

    return {
        "revenue": revenue, "cogs": cogs, "gross_profit": gross,
        "gross_margin": gross_margin, "sga": sga, "rnd": rnd,
        "ebitda": ebitda, "ebitda_margin": ebitda_margin, "da": da, "ebit": ebit,
        "interest": interest, "ebt": ebt, "tax": tax, "effective_tax": eff_tax,
        "net_income": net_income, "net_margin": net_margin, "eps": eps,
        "lines": [
            _row("Chiffre d'affaires", revenue),
            _row("Coût des ventes", -cogs),
            _row("Marge brute", gross),
            _row("Frais commerciaux (SG&A)", -sga),
            _row("R&D", -rnd),
            _row("EBITDA", ebitda),
            _row("Dotations amort. (D&A)", -da),
            _row("Résultat d'exploitation (EBIT)", ebit),
            _row("Charges d'intérêts (nettes)", -interest),
            _row("Résultat avant impôt", ebt),
            _row("Impôt", -tax),
            _row("Résultat net", net_income),
        ],
    }


def balance_sheet(market, ticker, year_offset=0):
    """Bilan (en M) pour l'exercice N-`year_offset`. Équilibré par construction."""
    i = market.ticker_idx[ticker]
    c = market.companies[i]
    p = params(c["sector"], ticker)
    g = p["growth"]

    rev_n = float(market.revenue[i])
    revenue = rev_n / ((1 + g) ** year_offset)
    net_debt = c["net_debt"] * (revenue / rev_n if rev_n else 1.0)
    inc = income_statement(market, ticker, year_offset)
    cogs = inc["cogs"]

    cash_base = revenue * p["cash_pct"]
    cash = cash_base + max(0.0, -net_debt)
    total_debt = cash_base + max(0.0, net_debt)      # dette − cash == net_debt (exact)
    receivables = revenue * p["rec_pct"]
    inventory = cogs * p["inv_pct"]
    ppe = revenue * p["ppe_pct"]
    goodwill = revenue * p["gw_pct"]

    payables = cogs * p["pay_pct"]
    other_liab = revenue * p["other_pct"]
    current_liab = payables + other_liab
    total_liab = total_debt + current_liab

    current_assets = cash + receivables + inventory
    total_assets = current_assets + ppe + goodwill
    equity = total_assets - total_liab               # solde -> bilan équilibré
    # plancher de capitaux propres : une société trop endettée détient en fait
    # plus d'immobilisations (sinon CP négatifs irréalistes). Le bilan reste
    # équilibré et la dette nette inchangée.
    min_equity = 0.12 * total_liab
    if equity < min_equity:
        bump = min_equity - equity
        ppe += bump
        total_assets += bump
        equity = min_equity

    return {
        "cash": cash, "receivables": receivables, "inventory": inventory,
        "current_assets": current_assets, "ppe": ppe, "goodwill": goodwill,
        "total_assets": total_assets,
        "total_debt": total_debt, "payables": payables, "other_liab": other_liab,
        "current_liab": current_liab, "total_liab": total_liab, "equity": equity,
        "net_debt": total_debt - cash,
        "assets_lines": [
            _row("Trésorerie & équivalents", cash),
            _row("Créances clients", receivables),
            _row("Stocks", inventory),
            _row("Total actifs courants", current_assets),
            _row("Immobilisations (PP&E)", ppe),
            _row("Goodwill & incorporels", goodwill),
            _row("TOTAL ACTIF", total_assets),
        ],
        "liab_lines": [
            _row("Dettes fournisseurs", payables),
            _row("Autres passifs courants", other_liab),
            _row("Total passifs courants", current_liab),
            _row("Dette financière", total_debt),
            _row("Total passif (hors CP)", total_liab),
            _row("Capitaux propres", equity),
            _row("TOTAL PASSIF + CP", total_liab + equity),
        ],
    }


def statements(market, ticker, base_year, n_years=3):
    """Renvoie les `n_years` derniers exercices (N, N-1, ...), du plus récent
    au plus ancien, avec leur libellé d'année et leurs deux états."""
    if ticker not in market.ticker_idx:
        return []
    out = []
    for offset in range(n_years):
        out.append({
            "year": base_year - offset,
            "income": income_statement(market, ticker, offset),
            "balance": balance_sheet(market, ticker, offset),
        })
    return out


def fiscal_year(player, base_year):
    """Exercice courant = année de base + années de jeu écoulées (roll-forward)."""
    years_elapsed = (player.day - 1) // 365
    return base_year + years_elapsed
