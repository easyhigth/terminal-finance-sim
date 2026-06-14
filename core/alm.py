"""
alm.py — Asset-Liability Management (gestion actif-passif bancaire, logique pure).

Le banking book porte un risque de TAUX et de LIQUIDITÉ. On mesure :
  - le repricing gap = actifs sensibles aux taux − passifs sensibles (sur 1 an) ;
    sa multiplication par un choc de taux approxime la variation de marge nette
    d'intérêt (NII) sur l'année ;
  - le duration gap = D_actifs − (Passifs/Actifs)·D_passifs ; il pilote la
    sensibilité de la VALEUR ÉCONOMIQUE DES FONDS PROPRES (ΔEVE) à un choc de taux :
    ΔEVE ≈ −DurationGap · Actifs · Δtaux.

Une banque « asset-sensitive » (gap > 0) gagne quand les taux montent ; une banque
« liability-sensitive » (gap < 0) y perd.
"""


def repricing_gap(rate_sensitive_assets, rate_sensitive_liabilities):
    """Gap de repricing 1 an (en M) = RSA − RSL."""
    return rate_sensitive_assets - rate_sensitive_liabilities


def nii_change(rep_gap, dy):
    """Variation de la marge nette d'intérêt sur 1 an pour un choc de taux dy."""
    return rep_gap * dy


def duration_gap(assets, dur_assets, liabilities, dur_liabilities):
    """Duration gap = D_a − (L/A)·D_l."""
    if assets <= 0:
        return 0.0
    return dur_assets - (liabilities / assets) * dur_liabilities


def delta_eve(assets, dgap, dy):
    """Variation de la valeur économique des fonds propres ≈ −DurationGap·A·Δy."""
    return -dgap * assets * dy


def equity(assets, liabilities):
    return assets - liabilities


def summary(state, dy):
    """Synthèse ALM à partir d'un état (dict) et d'un choc de taux dy.
    state : rsa, rsl (sensibles 1 an), assets, liabilities, dur_a, dur_l (totaux)."""
    rg = repricing_gap(state["rsa"], state["rsl"])
    dg = duration_gap(state["assets"], state["dur_a"], state["liabilities"], state["dur_l"])
    eq = equity(state["assets"], state["liabilities"])
    d_nii = nii_change(rg, dy)
    d_eve = delta_eve(state["assets"], dg, dy)
    profile = ("asset-sensitive" if rg > 0 else
               "liability-sensitive" if rg < 0 else "neutre")
    return {"repricing_gap": rg, "duration_gap": dg, "equity": eq,
            "delta_nii": d_nii, "delta_eve": d_eve, "profile": profile,
            "eve_pct_equity": (d_eve / eq * 100) if eq else 0.0}


# état par défaut du desk (en M) — banque de détail typique : prêts longs financés
# par des dépôts courts -> liability-sensitive, duration gap positif.
DEFAULT_STATE = {
    "rsa": 400.0, "rsl": 600.0,           # sensibles aux taux à 1 an
    "assets": 1000.0, "liabilities": 900.0,
    "dur_a": 4.5, "dur_l": 1.5,
}
