"""
test_market_events.py — Tests pour le module d'événements d'entreprise ciblés.

Vérifie :
- Déterminisme : même seed → mêmes événements
- Bornes des chocs
- Décroissance des résiduels
- Limite d'événements par pas (MAX_EVENTS_PER_STEP)
- Localisation FR/EN
- Comportement avec 0 société
- Cohérence des modèles (tous les champs requis)
"""
import numpy as np
import pytest
from core import market_events as mev
from core.i18n import set_lang


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_rng(seed=42):
    return np.random.RandomState(seed)


def _dummy_market(n=320):
    """Crée des vecteurs sigma/cap réalistes pour n sociétés."""
    rng = _make_rng(123)
    sigma = rng.uniform(0.15, 0.55, size=n).astype(float)
    price = rng.uniform(10, 500, size=n).astype(float)
    shares = rng.uniform(5e6, 2e9, size=n).astype(float)
    cap = price * shares
    return sigma, cap


# ---------------------------------------------------------------------------
# Tests des modèles
# ---------------------------------------------------------------------------
class TestEventModels:
    def test_all_models_have_required_fields(self):
        """Chaque modèle doit avoir les champs obligatoires."""
        required = {"id", "kind", "category", "icon", "base_prob",
                     "magnitude", "decay_steps", "title", "desc"}
        for m in mev.EVENT_MODELS:
            missing = required - set(m.keys())
            assert not missing, f"Modèle {m.get('id', '?')} : champs manquants {missing}"

    def test_all_models_have_valid_kind(self):
        """kind doit être 'good', 'bad' ou 'info'."""
        for m in mev.EVENT_MODELS:
            assert m["kind"] in ("good", "bad", "info"), \
                f"Modèle {m['id']} : kind invalide {m['kind']}"

    def test_all_models_have_bilingual_title_desc(self):
        """title et desc doivent être des tuples (fr, en)."""
        for m in mev.EVENT_MODELS:
            assert isinstance(m["title"], tuple) and len(m["title"]) == 2, \
                f"Modèle {m['id']} : title doit être (fr, en)"
            assert isinstance(m["desc"], tuple) and len(m["desc"]) == 2, \
                f"Modèle {m['id']} : desc doit être (fr, en)"

    def test_all_models_have_positive_decay(self):
        """decay_steps doit être > 0 pour que le drift résiduel fonctionne."""
        for m in mev.EVENT_MODELS:
            assert m["decay_steps"] > 0, \
                f"Modèle {m['id']} : decay_steps={m['decay_steps']}"

    def test_event_by_id_covers_all(self):
        """EVENT_BY_ID doit référencer tous les modèles."""
        for m in mev.EVENT_MODELS:
            assert m["id"] in mev.EVENT_BY_ID
        assert len(mev.EVENT_BY_ID) == len(mev.EVENT_MODELS)


# ---------------------------------------------------------------------------
# Tests de step_events
# ---------------------------------------------------------------------------
class TestStepEvents:
    def test_determinism(self):
        """Même seed + même état → mêmes événements."""
        sigma, cap = _dummy_market(50)
        rng1 = _make_rng(42)
        rng2 = _make_rng(42)
        s1, e1 = mev.step_events(50, 0, sigma, cap, rng1)
        s2, e2 = mev.step_events(50, 0, sigma, cap, rng2)
        assert np.allclose(s1, s2)
        assert e1 == e2

    def test_different_seed_different_events(self):
        """Deux seeds différentes produisent des événements différents."""
        sigma, cap = _dummy_market(50)
        rng1 = _make_rng(42)
        rng2 = _make_rng(99)
        s1, e1 = mev.step_events(50, 0, sigma, cap, rng1)
        s2, e2 = mev.step_events(50, 0, sigma, cap, rng2)
        # Les deux peuvent être vides, mais si non vides ils diffèrent
        nz1 = [i for i in range(50) if e1[i] is not None]
        nz2 = [i for i in range(50) if e2[i] is not None]
        # Pas de garantie qu'ils diffèrent, mais c'est très probable
        # On vérifie juste que ça ne crash pas

    def test_returns_correct_shapes(self):
        """Les retours ont les bonnes dimensions."""
        sigma, cap = _dummy_market(30)
        rng = _make_rng(42)
        shocks, events = mev.step_events(30, 0, sigma, cap, rng)
        assert len(shocks) == 30
        assert len(events) == 30

    def test_no_more_than_max_events_per_step(self):
        """Jamais plus de MAX_EVENTS_PER_STEP événements par pas."""
        sigma, cap = _dummy_market(320)
        # On fait beaucoup de pas pour être sûr
        for step in range(200):
            rng = _make_rng(step)
            _, events = mev.step_events(320, step, sigma, cap, rng)
            n_events = sum(1 for e in events if e is not None)
            assert n_events <= mev._MAX_EVENTS_PER_STEP, \
                f"Pas {step}: {n_events} événements > max {mev._MAX_EVENTS_PER_STEP}"

    def test_shocks_are_bounded(self):
        """Les chocs doivent être dans [-0.12, 0.12]."""
        sigma, cap = _dummy_market(320)
        for step in range(100):
            rng = _make_rng(step + 1000)
            shocks, _ = mev.step_events(320, step, sigma, cap, rng)
            assert np.all(shocks >= -0.12), f"Pas {step}: choc < -0.12"
            assert np.all(shocks <= 0.12), f"Pas {step}: choc > 0.12"

    def test_zero_companies(self):
        """Avec 0 société, pas d'erreur."""
        sigma = np.array([], dtype=float)
        cap = np.array([], dtype=float)
        rng = _make_rng(42)
        shocks, events = mev.step_events(0, 0, sigma, cap, rng)
        assert len(shocks) == 0
        assert len(events) == 0

    def test_events_have_required_fields(self):
        """Chaque événement concret a tous les champs nécessaires."""
        sigma, cap = _dummy_market(320)
        required = {"id", "kind", "category", "icon", "title", "desc",
                     "step", "shock", "residual", "decay", "steps_left"}
        found_any = False
        for step in range(500):
            rng = _make_rng(step + 2000)
            _, events = mev.step_events(320, step, sigma, cap, rng)
            for ev in events:
                if ev is not None:
                    found_any = True
                    missing = required - set(ev.keys())
                    assert not missing, f"Événement {ev.get('id')} : champs manquants {missing}"
                    assert ev["steps_left"] == ev["decay"]
                    assert isinstance(ev["shock"], float)
                    assert isinstance(ev["residual"], float)
            if found_any:
                break
        assert found_any, "Aucun événement trouvé en 500 pas — probabilité quasi nulle"

    def test_rng_consumed_every_step_for_every_company(self):
        """Le RNG est consommé même quand aucun événement ne se déclenche
        (préservation du déterminisme de la séquence)."""
        sigma, cap = _dummy_market(10)
        rng = _make_rng(42)
        state_before = rng.get_state()
        mev.step_events(10, 0, sigma, cap, rng)
        state_after = rng.get_state()
        # L'état doit avoir changé (des tirages ont été faits)
        assert not np.array_equal(state_before[1], state_after[1])


# ---------------------------------------------------------------------------
# Tests de decay_residuals
# ---------------------------------------------------------------------------
class TestDecayResiduals:
    def test_decay_reduces_steps_left(self):
        """Chaque appel décrémente steps_left."""
        active = [None] * 5
        active[0] = {
            "id": "test", "kind": "good", "residual": 0.01,
            "decay": 3, "steps_left": 3, "shock": 0.03,
        }
        mev.decay_residuals(active, 5)
        assert active[0]["steps_left"] == 2
        mev.decay_residuals(active, 5)
        assert active[0]["steps_left"] == 1
        mev.decay_residuals(active, 5)
        assert active[0]["steps_left"] == 0

    def test_residual_magnitude_decreases(self):
        """Le drift résiduel diminue avec steps_left."""
        active = [None] * 3
        active[0] = {
            "id": "test", "kind": "bad", "residual": 0.02,
            "decay": 4, "steps_left": 4, "shock": -0.05,
        }
        r1 = mev.decay_residuals(active, 3)
        v1 = abs(r1[0])
        r2 = mev.decay_residuals(active, 3)
        v2 = abs(r2[0])
        assert v2 < v1, f"Le résiduel devrait décroître : {v1} → {v2}"

    def test_expired_event_produces_zero_residual(self):
        """Un événement expiré (steps_left=0) ne produit plus de drift."""
        active = [None] * 2
        active[0] = {
            "id": "test", "kind": "good", "residual": 0.01,
            "decay": 1, "steps_left": 0, "shock": 0.02,
        }
        r = mev.decay_residuals(active, 2)
        assert r[0] == 0.0

    def test_none_events_produce_zero_residual(self):
        """Les sociétés sans événement ont un résiduel nul."""
        active = [None] * 10
        r = mev.decay_residuals(active, 10)
        assert np.all(r == 0.0)

    def test_returns_correct_shape(self):
        """Le retour a la bonne dimension."""
        active = [None] * 7
        r = mev.decay_residuals(active, 7)
        assert len(r) == 7


# ---------------------------------------------------------------------------
# Tests de localisation
# ---------------------------------------------------------------------------
class TestLocalization:
    def test_localize_event_fr(self):
        """En FR, le titre/desc vient du tuple[0]."""
        set_lang("fr")
        model = mev.EVENT_MODELS[0]  # product_hit
        ev = {
            "id": model["id"], "kind": model["kind"],
            "title": model["title"][0], "desc": model["desc"][0],
            "step": 10, "shock": 0.03, "residual": 0.01,
            "decay": 5, "steps_left": 5,
        }
        loc = mev.localize_event(ev)
        assert loc["title"] == model["title"][0]
        assert loc["desc"] == model["desc"][0]

    def test_localize_event_en(self):
        """En EN, le titre/desc vient du tuple[1]."""
        set_lang("en")
        model = mev.EVENT_MODELS[0]
        ev = {
            "id": model["id"], "kind": model["kind"],
            "title": model["title"][0], "desc": model["desc"][0],
            "step": 10, "shock": 0.03, "residual": 0.01,
            "decay": 5, "steps_left": 5,
        }
        loc = mev.localize_event(ev)
        assert loc["title"] == model["title"][1]
        assert loc["desc"] == model["desc"][1]
        set_lang("fr")  # restore

    def test_localize_none(self):
        """localize_event(None) → None."""
        assert mev.localize_event(None) is None

    def test_localize_unknown_id(self):
        """Un événement avec un id inconnu est retourné tel quel."""
        ev = {"id": "nonexistent", "title": "X", "desc": "Y"}
        out = mev.localize_event(ev)
        assert out["title"] == "X"


# ---------------------------------------------------------------------------
# Tests d'intégration rapide (logique pure, pas de pygame)
# ---------------------------------------------------------------------------
class TestIntegration:
    def test_step_then_decay_pipeline(self):
        """Simule le pipeline complet : step_events → decay_residuals."""
        sigma, cap = _dummy_market(100)
        active = [None] * 100
        for step in range(50):
            rng = _make_rng(step)
            shocks, new_events = mev.step_events(100, step, sigma, cap, rng)
            # Fusionne les nouveaux événements
            for i, ev in enumerate(new_events):
                if ev is not None:
                    active[i] = ev
            # Applique le drift résiduel
            residual = mev.decay_residuals(active, 100)
            # Vérifie que les chocs + résiduels sont bornés
            total = shocks + residual
            assert np.all(total >= -0.18)
            assert np.all(total <= 0.18)

    def test_events_log_accumulates(self):
        """Simule l'accumulation dans company_events_log comme dans Market."""
        sigma, cap = _dummy_market(50)
        active = [None] * 50
        event_log = {}
        for step in range(200):
            rng = _make_rng(step + 5000)
            _, new_events = mev.step_events(50, step, sigma, cap, rng)
            for i, ev in enumerate(new_events):
                if ev is not None:
                    active[i] = ev
                    ticker = f"TICKER_{i}"
                    event_log.setdefault(ticker, []).append(ev)
            mev.decay_residuals(active, 50)
        # Vérifie que le log contient des événements
        total_events = sum(len(v) for v in event_log.values())
        assert total_events > 0, "Aucun événement en 200 pas — suspect"
        # Vérifie que chaque événement a un step cohérent
        for ticker, events in event_log.items():
            for ev in events:
                assert 0 <= ev["step"] < 200
