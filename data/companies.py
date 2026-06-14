"""
companies.py — Univers de sociétés fictives (déterministe).

Tout est fictif mais calqué sur le réel : les noms/tickers sont volontairement
déformés (LVMH→LWNH, NVIDIA→MVC, S&P 500→C&D 500, CAC 40→KAK 40...) pour
rappeler que c'est une simulation, pas des données réelles.

Le roster est généré de façon DÉTERMINISTE (graine fixe) : il est donc
identique d'une partie à l'autre, ce qui permet d'écrire des fiches, des
missions et des indices stables. Les PRIX, eux, évoluent dynamiquement dans
core/market.py via un modèle à facteurs.

Chaque société est un dict de données statiques :
  ticker, name, region, sector,
  shares      : nombre d'actions (en millions)
  price0      : prix initial
  revenue     : chiffre d'affaires (M, devise locale)
  ebitda_margin, net_margin : marges (0..1)
  net_debt    : dette nette (M ; négatif = trésorerie nette)
  div_yield   : rendement du dividende (0..1)
  beta        : sensibilité au facteur monde (chargement b_world)
  b_sector    : chargement sur le facteur sectoriel
  b_region    : chargement sur le facteur régional
  sigma       : volatilité idiosyncratique par pas
  drift       : dérive (tendance) par pas
"""
import random

ROSTER_SEED = 20240607     # graine fixe → roster reproductible
TARGET_COUNT = 320         # nombre total de sociétés visé

REGIONS = ["USA", "Am.Nord", "Europe", "Am.Sud", "Afrique", "Asia", "Océanie"]

# Profils sectoriels : (beta, b_sector, sigma, drift, div_yield, ebitda_m, net_m)
# Valeurs « par pas » d'environ une semaine de marché.
SECTORS = {
    "Tech":        dict(beta=1.25, b_sector=1.10, sigma=0.045, drift=0.0022, div=0.004, ebitda=0.34, net=0.22),
    "Semicon":     dict(beta=1.40, b_sector=1.25, sigma=0.055, drift=0.0026, div=0.003, ebitda=0.38, net=0.25),
    "Luxe":        dict(beta=1.10, b_sector=0.95, sigma=0.038, drift=0.0018, div=0.015, ebitda=0.30, net=0.18),
    "Conso":       dict(beta=0.65, b_sector=0.70, sigma=0.022, drift=0.0010, div=0.025, ebitda=0.22, net=0.11),
    "Finance":     dict(beta=1.20, b_sector=1.15, sigma=0.040, drift=0.0012, div=0.030, ebitda=0.45, net=0.26),
    "Energie":     dict(beta=1.05, b_sector=1.20, sigma=0.045, drift=0.0008, div=0.045, ebitda=0.32, net=0.13),
    "Sante":       dict(beta=0.80, b_sector=0.75, sigma=0.028, drift=0.0015, div=0.018, ebitda=0.30, net=0.18),
    "Industrie":   dict(beta=1.10, b_sector=0.90, sigma=0.032, drift=0.0012, div=0.020, ebitda=0.18, net=0.09),
    "Agro":        dict(beta=0.85, b_sector=1.00, sigma=0.035, drift=0.0009, div=0.022, ebitda=0.16, net=0.07),
    "Telecom":     dict(beta=0.70, b_sector=0.65, sigma=0.024, drift=0.0006, div=0.040, ebitda=0.36, net=0.12),
    "Utilities":   dict(beta=0.45, b_sector=0.55, sigma=0.018, drift=0.0007, div=0.050, ebitda=0.40, net=0.14),
    "Materiaux":   dict(beta=1.15, b_sector=1.05, sigma=0.040, drift=0.0010, div=0.025, ebitda=0.20, net=0.10),
    "Immobilier":  dict(beta=0.90, b_sector=0.85, sigma=0.030, drift=0.0008, div=0.045, ebitda=0.55, net=0.20),
    "Auto":        dict(beta=1.20, b_sector=1.00, sigma=0.042, drift=0.0009, div=0.025, ebitda=0.15, net=0.07),
}

# --------------------------------------------------------------------------
# Sociétés « héros » — renommées de façon reconnaissable. (clin d'œil au réel)
# (ticker, nom, région, secteur, capi cible en milliards de devise locale)
# --------------------------------------------------------------------------
HEROES = [
    # ---- USA (indice C&D 500) ----
    ("MVC",  "Mavric Computing",     "USA", "Semicon",   3000),
    ("MIRC", "Mirocraft",            "USA", "Tech",      3100),
    ("POME", "Pomme Inc.",           "USA", "Tech",      3200),
    ("RIVR", "Riverian",             "USA", "Tech",      1800),
    ("GUGL", "Gugol",                "USA", "Tech",      2100),
    ("MTAX", "Metanox",              "USA", "Tech",      1300),
    ("TSLR", "Teslar Motors",        "USA", "Auto",       800),
    ("JMP",  "J.P. Mornay",          "USA", "Finance",    560),
    ("EXOM", "Exxom Energy",         "USA", "Energie",    520),
    ("KOLA", "Koola Beverages",      "USA", "Conso",      280),
    ("PHIZ", "Phizer Health",        "USA", "Sante",      300),
    ("WALM", "Walmest",              "USA", "Conso",      440),
    ("VYSA", "Vysa Networks",        "USA", "Finance",    480),
    ("BROK", "Brookrock Asset",      "USA", "Finance",    140),
    # ---- Europe (indice KAK 40) ----
    ("LWNH", "Louis Wertton Holding","Europe", "Luxe",    400),
    ("TOTE", "TotalEnergi",          "Europe", "Energie", 160),
    ("ZAP",  "Zap Systems",          "Europe", "Tech",    220),
    ("SANO", "Sanovi",               "Europe", "Sante",   130),
    ("LORL", "Loriel",               "Europe", "Conso",   240),
    ("AIRX", "Airbex",               "Europe", "Industrie",140),
    ("BPN",  "Banque BPN",           "Europe", "Finance",  90),
    ("SMNS", "Siemonds",             "Europe", "Industrie",180),
    ("NSTL", "Nestlon",              "Europe", "Conso",    300),
    ("ASMX", "ASMicro",              "Europe", "Semicon",  350),
    ("HRMS", "Hermez",               "Europe", "Luxe",     220),
    ("SHEL", "Shellix",              "Europe", "Energie",  210),
    # ---- Asia (indice NKX 225) ----
    ("TSMX", "Taisan Microchips",    "Asia", "Semicon",   780),
    ("TYTA", "Toyota Motor",         "Asia", "Auto",      250),
    ("SFTB", "Softblank Group",      "Asia", "Tech",       90),
    ("SMSG", "Samseng Electro",      "Asia", "Tech",      380),
    ("TCNT", "Tencend",              "Asia", "Tech",      400),
    ("ALBB", "Alibubba",             "Asia", "Conso",     220),
    ("SQNY", "Sauny Corp",           "Asia", "Tech",      120),
    ("NTND", "Nintondo",             "Asia", "Tech",       70),
    ("HSBK", "Hong Sang Bank",       "Asia", "Finance",   180),
    ("PCHN", "PetroChine",           "Asia", "Energie",   200),
    # ---- Amérique du Nord (indice TXC 60) ----
    ("SHPF", "Shopstar",             "Am.Nord", "Tech",      90),
    ("RBQ",  "Banque Royale Nord",   "Am.Nord", "Finance",  140),
    ("ENBR", "Enbrige Pipelines",    "Am.Nord", "Energie",  100),
    ("BARK", "Barrock Gold",         "Am.Nord", "Materiaux", 40),
    ("BMBR", "Brambleton Rail",      "Am.Nord", "Industrie", 70),
    # ---- Amérique du Sud (indice BVSP) ----
    ("PTBR", "Petrobas",             "Am.Sud", "Energie",   110),
    ("VALY", "Valle Mining",         "Am.Sud", "Materiaux", 90),
    ("ITAB", "Itaboa Banco",         "Am.Sud", "Finance",    80),
    ("MERC", "Mercabueno",           "Am.Sud", "Conso",      70),
    ("AMBV", "Ambeva Boissons",      "Am.Sud", "Conso",      60),
    # ---- Afrique (indice JT 40) ----
    ("NSPR", "Naspex",               "Afrique", "Tech",      90),
    ("SSOL", "Sasoul Energy",        "Afrique", "Energie",   30),
    ("DANG", "Dangoto Cement",       "Afrique", "Materiaux", 35),
    ("MTNX", "MTNex Telecom",        "Afrique", "Telecom",   25),
    ("SFCM", "Safacom",              "Afrique", "Telecom",   20),
    # ---- Océanie (indice AX 200) ----
    ("BHPX", "Broken Hill Prop.",    "Océanie", "Materiaux", 150),
    ("CWBK", "Commonworth Bank",     "Océanie", "Finance",   130),
    ("CSLX", "CSLab Biotech",        "Océanie", "Sante",     110),
    ("WLWO", "Woolloomoo",           "Océanie", "Conso",      45),
    ("TLST", "Telstro",              "Océanie", "Telecom",    40),
]

# Indices : nom, région, valeur cible de départ, nb de constituants (top capi)
INDEX_DEFS = [
    ("C&D 500", "USA",     5200.0, 90),
    ("TXC 60",  "Am.Nord", 22000.0, 45),
    ("KAK 40",  "Europe",  7800.0, 40),
    ("BVSP",    "Am.Sud",  125000.0, 50),
    ("JT 40",   "Afrique", 70000.0, 35),
    ("NKX 225", "Asia",    39000.0, 80),
    ("AX 200",  "Océanie", 7500.0, 45),
]

# Briques pour fabriquer des noms/tickers procéduraux plausibles.
_PREF = ["Nor", "Vel", "Aru", "Kai", "Zen", "Oro", "Tri", "Lum", "Pal", "Vex",
         "Cor", "Hel", "Mar", "Sol", "Bre", "Dax", "Fyn", "Glo", "Hex", "Ira",
         "Jad", "Kor", "Lyn", "Myr", "Nyx", "Ovi", "Pyr", "Qua", "Rho", "Syl"]
_SUFF = ["dyne", "corp", "tech", "ware", "nova", "lux", "gen", "form", "wave",
         "core", "rion", "tis", "via", "mark", "sys", "field", "stone", "grid",
         "lane", "peak", "ford", "ton", "bury", "shire", "mont", "dale"]


def _make_company(rng, ticker, name, region, sector, mktcap_b):
    """Construit une société à partir d'une capi cible (en milliards)."""
    prof = SECTORS[sector]
    mktcap = mktcap_b * 1000.0  # en millions
    price0 = round(rng.uniform(25, 480), 2)
    shares = round(mktcap / price0, 1)  # millions d'actions
    # chiffre d'affaires via un price/sales plausible selon le secteur
    ps = rng.uniform(1.5, 7.0) if sector in ("Tech", "Semicon", "Luxe") else rng.uniform(0.4, 2.5)
    revenue = round(mktcap / ps, 1)
    return {
        "ticker": ticker, "name": name, "region": region, "sector": sector,
        "shares": shares, "price0": price0, "revenue": revenue,
        "ebitda_margin": round(prof["ebitda"] * rng.uniform(0.85, 1.15), 3),
        "net_margin": round(prof["net"] * rng.uniform(0.8, 1.2), 3),
        "net_debt": round(revenue * rng.uniform(-0.25, 1.1), 1),
        "div_yield": round(prof["div"] * rng.uniform(0.6, 1.4), 4),
        "beta": round(prof["beta"] * rng.uniform(0.85, 1.15), 3),
        "b_sector": round(prof["b_sector"] * rng.uniform(0.85, 1.15), 3),
        "b_region": round(rng.uniform(0.55, 1.0), 3),
        "sigma": round(prof["sigma"] * rng.uniform(0.8, 1.25), 4),
        "drift": round(prof["drift"] * rng.uniform(0.4, 1.4), 5),
    }


def _gen_ticker(rng, used):
    for _ in range(50):
        t = "".join(rng.choice("ABCDEFGHJKLMNPRSTVXYZ") for _ in range(rng.choice([3, 4])))
        if t not in used:
            used.add(t)
            return t
    # fallback improbable
    t = "X" + str(len(used))
    used.add(t)
    return t


def build_roster():
    """Retourne (companies, index_defs). Déterministe via ROSTER_SEED."""
    rng = random.Random(ROSTER_SEED)
    companies = []
    used = set()
    # 1) sociétés héros
    for ticker, name, region, sector, cap in HEROES:
        used.add(ticker)
        companies.append(_make_company(rng, ticker, name, region, sector, cap))
    # 2) génération procédurale jusqu'à TARGET_COUNT
    sectors = list(SECTORS.keys())
    while len(companies) < TARGET_COUNT:
        region = rng.choice(REGIONS)
        sector = rng.choice(sectors)
        ticker = _gen_ticker(rng, used)
        name = rng.choice(_PREF) + rng.choice(_SUFF)
        name = name[0].upper() + name[1:]
        # capitalisation log-uniforme : beaucoup de petites, quelques grosses
        cap_b = round(10 ** rng.uniform(0.0, 2.4), 1)  # ~1 à ~250 milliards
        companies.append(_make_company(rng, ticker, name, region, sector, cap_b))
    return companies, list(INDEX_DEFS)


# Construit une fois à l'import (léger : ~320 dicts).
COMPANIES, INDICES = build_roster()
COMPANY_BY_TICKER = {c["ticker"]: c for c in COMPANIES}
