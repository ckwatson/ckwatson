import numpy as np
import pytest

from kernel.data.reaction_mechanism_class import reaction_mechanism
from kernel.engine.experiment_class import Experiment


@pytest.fixture
def exp():
    mech = mock_reaction_mechanism()
    exp = Experiment(mech, input_temp=25)
    # Simulate a time array and reaction profile
    exp.time_array = np.linspace(0, 10, 11)
    exp.reaction_profile = np.array([[i, i * 2] for i in range(11)])
    return exp


def test_slice_array_by_time_full(exp):
    result = exp.slice_array_by_time("jobid")
    np.testing.assert_array_equal(result, exp.reaction_profile)


def test_slice_array_by_time_slice(exp):
    # Should return rows where time is between 2 and 5 (inclusive)
    result = exp.slice_array_by_time("jobid", start=2, end=5)
    expected = exp.reaction_profile[2:6]
    np.testing.assert_array_equal(result, expected)


def test_slice_array_by_time_start_greater_than_end(exp):
    # Should reverse and still return correct slice
    result = exp.slice_array_by_time("jobid", start=5, end=2)
    expected = exp.reaction_profile[2:6]
    np.testing.assert_array_equal(result, expected)


def test_slice_array_by_time_start_out_of_bounds(exp):
    # Start < min(time_array)
    result = exp.slice_array_by_time("jobid", start=-5, end=3)
    expected = exp.reaction_profile[0:4]
    np.testing.assert_array_equal(result, expected)


def test_slice_array_by_time_end_out_of_bounds(exp):
    # End > max(time_array)
    result = exp.slice_array_by_time("jobid", start=8, end=20)
    expected = exp.reaction_profile[8:]
    np.testing.assert_array_equal(result, expected)


def test_slice_array_by_time_start_and_end_out_of_bounds(exp):
    # Both out of bounds
    result = exp.slice_array_by_time("jobid", start=-10, end=20)
    expected = exp.reaction_profile
    np.testing.assert_array_equal(result, expected)


def mock_reaction_mechanism() -> reaction_mechanism:
    return reaction_mechanism(
        num_rxn=1,
        num_species=2,
        mol_list=["H2", "H"],
        rxn_array=[[-1, 2]],
        reagEnrg={"H2": 1.0, "H": 0.1},
    )


def make_exp_with_flat_region(flat_start=8, total=12, n_species=2) -> Experiment:
    """
    Create an experiment with a reaction profile that has a flat region.

    Parameters:
    - flat_start: The index at which the flat region starts.
    - total: Total number of time points in the experiment. The experiment will always be run for 10 seconds.
    - n_species: Number of species in the reaction profile.
    """
    rm = mock_reaction_mechanism()
    time_array = np.linspace(0, 10, total)
    # Reaction profile: first part changes, then flat
    profile = np.vstack(
        [
            np.linspace(0, 1, flat_start)[:, None] * np.ones(n_species),
            np.ones((total - flat_start, n_species)),
        ]
    )
    return Experiment(rm, 25, input_time=time_array, rxn_profile=profile)


def test_find_flat_region_removes_flat():
    exp = make_exp_with_flat_region(flat_start=50, total=100, n_species=2)
    exp.find_flat_region(job_id="test", threshold=1e-6)
    # After removing, the time_array and reaction_profile should be cut at the start of the flat region.
    # The flat region starts at 50, so we expect the method to detect it at the 60-th time step.
    # (Because the method samples 10 time steps. The resolution is every 10 time steps.)
    # In other words, time_array should be cut to 60 units long.
    assert len(exp.time_array) == 60
    assert round(exp.time_array[-1]) == 6
    assert exp.reaction_profile.shape[0] == exp.time_array.shape[0]


def test_find_flat_region_no_flat():
    exp = make_exp_with_flat_region(flat_start=100, total=100, n_species=2)
    # No flat region, should not cut
    exp.find_flat_region(job_id="test", threshold=1e-6)
    assert len(exp.time_array) == 100
    assert round(exp.time_array[-1]) == 10
    assert exp.reaction_profile.shape[0] == 100


def test_find_flat_region_short_profile():
    exp = make_exp_with_flat_region(flat_start=2, total=5, n_species=2)
    exp.find_flat_region(job_id="test", threshold=1e-3)
    # Should still work for short profiles
    assert len(exp.time_array) == 2
    assert round(exp.time_array[-1]) == 2
    assert exp.reaction_profile.shape[0] == exp.time_array.shape[0]


def test_find_flat_region_all_flat():
    rm = mock_reaction_mechanism()
    time_array = np.linspace(0, 10, 10)
    profile = np.ones((10, 2))
    exp = Experiment(rm, 25, input_time=time_array, rxn_profile=profile)
    exp.find_flat_region(job_id="test", threshold=1e-6)
    # Should cut to the first sample
    assert len(exp.time_array) == 1
    assert round(exp.time_array[-1]) == 0
    assert exp.reaction_profile.shape[0] == exp.time_array.shape[0]


def test_find_experimental_Keq_array_basic():
    mech = mock_reaction_mechanism()
    time_array = np.linspace(0, 10, 5)
    # At equilibrium, [H2] = 2 mol, [H] = 4 mol, so Keq = 2^-1 * 4^2 = 8
    rxn_profile = np.array([[1, 2], [1.5, 3], [2, 4], [2, 4], [2, 4]])
    exp = Experiment(mech, 25, input_time=time_array, rxn_profile=rxn_profile)
    Keq = exp.find_experimental_Keq_array(job_id="test")
    assert np.allclose(Keq, [8])


def test_find_experimental_Keq_array_multiple_reactions():
    # 2 reactions: [A]^1*[B]^1, [A]^-1*[B]^2
    class MockMech:
        number_of_reactions = 2
        number_of_species = 2
        get_name_set = lambda self: ["A", "B"]
        coefficient_array = np.array([[1, 1], [-1, 2]])
        reactant_coefficient_array = np.array([[1, 0], [0, 1]])
        product_coefficient_array = np.array([[0, 1], [1, 1]])
        get_energy_set = lambda self: np.array([1.0, 2.0])

    mech = MockMech()
    time_array = np.linspace(0, 10, 4)
    rxn_profile = np.array([[1, 2], [2, 3], [3, 4], [3, 4]])
    exp = Experiment(mech, 25, input_time=time_array, rxn_profile=rxn_profile)
    Keq = exp.find_experimental_Keq_array(job_id="test")
    # At equilibrium: [A]=3, [B]=4
    # Keq[0] = 3^1 * 4^1 = 12
    # Keq[1] = 3^-1 * 4^2 = (1/3) * 16 = 16/3 ≈ 5.333
    assert np.allclose(Keq, [12, 16 / 3])


def test_find_experimental_Keq_array_calls_find_flat_region(monkeypatch):
    mech = mock_reaction_mechanism()
    time_array = np.linspace(0, 10, 5)
    rxn_profile = np.array([[1, 2], [1.5, 3], [2, 4], [2, 4], [2, 4]])
    exp = Experiment(mech, 25, input_time=time_array, rxn_profile=rxn_profile)
    called = {}

    def fake_find_flat_region(job_id, remove=True):
        called["called"] = True
        return 2

    exp.find_flat_region = fake_find_flat_region
    exp.find_experimental_Keq_array(job_id="test")
    assert called["called"]
