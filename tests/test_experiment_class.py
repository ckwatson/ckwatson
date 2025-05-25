import numpy as np
import pytest

from kernel.data.reaction_mechanism_class import reaction_mechanism
from kernel.engine.experiment_class import experiment


@pytest.fixture
def exp():
    mech = reaction_mechanism(
        num_rxn=1,
        num_species=2,
        mol_list=["H2", "H"],
        rxn_array=[[-1, 2]],
        reagEnrg={"H2": 1.0, "H": 0.1},
    )
    exp = experiment(mech, input_temp=25)
    # Simulate a time array and reaction profile
    exp.time_array = np.linspace(0, 10, 11)
    exp.reaction_profile = np.array([[i, i * 2] for i in range(11)])
    return exp


def test_get_reaction_profile_full(exp):
    result = exp.slice_reaction_profile("jobid")
    np.testing.assert_array_equal(result, exp.reaction_profile)


def test_get_reaction_profile_slice(exp):
    # Should return rows where time is between 2 and 5 (inclusive)
    result = exp.slice_reaction_profile("jobid", start=2, end=5)
    expected = exp.reaction_profile[2:6]
    np.testing.assert_array_equal(result, expected)


def test_get_reaction_profile_start_greater_than_end(exp):
    # Should reverse and still return correct slice
    result = exp.slice_reaction_profile("jobid", start=5, end=2)
    expected = exp.reaction_profile[2:6]
    np.testing.assert_array_equal(result, expected)


def test_get_reaction_profile_start_out_of_bounds(exp):
    # Start < min(time_array)
    result = exp.slice_reaction_profile("jobid", start=-5, end=3)
    expected = exp.reaction_profile[0:4]
    np.testing.assert_array_equal(result, expected)


def test_get_reaction_profile_end_out_of_bounds(exp):
    # End > max(time_array)
    result = exp.slice_reaction_profile("jobid", start=8, end=20)
    expected = exp.reaction_profile[8:]
    np.testing.assert_array_equal(result, expected)


def test_get_reaction_profile_start_and_end_out_of_bounds(exp):
    # Both out of bounds
    result = exp.slice_reaction_profile("jobid", start=-10, end=20)
    expected = exp.reaction_profile
    np.testing.assert_array_equal(result, expected)
