# Tests

Suite de tests de la **logique pure** du jeu (sans pygame) :

- `test_finmath.py` — formules financières (`core/finmath.py`) vérifiées contre
  des valeurs à la main et des identités connues (parité call-put, obligation
  au pair, cohérence MOIC/IRR…).
- `test_market.py` — moteur de marché (`core/market.py`) : **déterminisme**
  (même graine → mêmes prix), reconstruction via `sync_to`, robustesse sur long
  horizon (pas de NaN/prix négatif), émergence des indices, effet des crises,
  bornes macro et **calibration** rendement/volatilité.

## Lancer les tests

Avec l'interpréteur du projet (conda `training`, qui a numpy/scipy/pygame) :

```bash
~/miniforge3/envs/training/bin/python -m pytest
```

Ou, dans un environnement où `python` pointe déjà sur le bon interpréteur :

```bash
pytest
```

> pytest doit être installé dans l'environnement :
> `pip install pytest`

La CI (`.github/workflows/tests.yml`) relance cette suite à chaque push sur
`main` et sur chaque pull request.
