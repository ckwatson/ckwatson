import numpy as np
import pytest

from kernel.data import reaction_mechanism_class
from web.run_simulation import (
    make_reaction_mechanism_for_reagent,
    simulate_experiments_and_plot,
)


def handles_no_pre_equilibration_needed(self):
    """
    `is_each_involved` is a list of booleans indicating whether each elementary reaction is involved in the pre-equilibration of the reagent.
    If no reactions are involved, the function should create a reaction mechanism with just the reagent itself.
    """
    is_each_involved = [False, False]
    job_id = "test_job"
    energy_dict = {"A": -10.0, "B": -5.0}
    puzzle_definition = {
        "coefficient_dict": {"A": 0, "B": 1},
        "coefficient_array": [[-1.0, 1.0], [0.0, 0.0]],
    }
    reagent = "A"
    species_list = ["A", "B"]

    result = make_reaction_mechanism_for_reagent(
        is_each_involved, job_id, energy_dict, puzzle_definition, reagent, species_list
    )

    self.assertEqual(result.num_rxn, 1)
    self.assertEqual(result.num_species, 1)
    self.assertEqual(result.species_list, ["A"])
    self.assertTrue((result.coefficient_array == [[0.0]]).all())


def filters_unused_species_correctly(self):
    """
    Test that the function correctly filters out unused species from the reaction mechanism.

    Assuming the puzzle specified these two reactions:
    - A + B -> C
    - (nothing) -> (nothing) <-- malformed reaction, but it should be ignored.
    The function should only keep the first reaction and filter out the second one.
    """
    is_each_involved = [True, False]
    job_id = "test_job"
    energy_dict = {"A": -10.0, "B": -5.0, "C": -2.0}
    puzzle_definition = {
        "coefficient_dict": {"A": 0, "B": 1, "C": 2},
        "coefficient_array": [[-1.0, 1.0, 0.0], [0.0, 0.0, 0.0]],
    }
    reagent = "A"
    species_list = ["A", "B", "C"]

    result = make_reaction_mechanism_for_reagent(
        is_each_involved, job_id, energy_dict, puzzle_definition, reagent, species_list
    )

    self.assertEqual(result.num_rxn, 1)
    self.assertEqual(result.num_species, 2)
    self.assertEqual(result.species_list, ["A", "B"])
    self.assertTrue((result.coefficient_array == [[-1.0, 1.0]]).all())


def handles_empty_reactions(self):
    is_each_involved = []
    job_id = "test_job"
    energy_dict = {}
    puzzle_definition = {"coefficient_dict": {}, "coefficient_array": []}
    reagent = "X"
    species_list = []

    result = make_reaction_mechanism_for_reagent(
        is_each_involved, job_id, energy_dict, puzzle_definition, reagent, species_list
    )

    self.assertEqual(result.num_rxn, 1)
    self.assertEqual(result.num_species, 1)
    self.assertEqual(result.species_list, ["X"])
    self.assertTrue((result.coefficient_array == [[0.0]]).all())


def test_make_reaction_mechanism_for_reagent_for_normal_case():
    # Setup minimal data and puzzle_definition to trigger a normal reaction_mechanism
    puzzle_definition = {
        "coefficient_array": [
            [1, -1, 0],  # A -> B
            [0, 1, -1],  # B -> C
        ],
        "energy_dict": {"A": 10.0, "B": 20.0, "C": 30.0},
        "coefficient_dict": {"A": 0, "B": 1, "C": 2},
        "reagentPERs": {"A": [True, False]},
    }
    reaction_mechanism = make_reaction_mechanism_for_reagent(
        [True, False],
        "job_id",
        puzzle_definition,
        "A",
        ["A", "B", "C"],
    )
    # Assert all fields using __dict__ and correct keys
    rm_dict = reaction_mechanism.__dict__
    # It will look like this:
    #   {'JSON_Encoder': <class 'kernel.data.molecular_species.mol_JSON_Encoder'>, 'number_of_reactions': 1,
    #   'number_of_species': 2, 'molecular_species_dict': {'A': {'name': 'A', 'energy': 10.0, 'atom_list': None},
    #   'B': {'name': 'B', 'energy': 20.0, 'atom_list': None}}, 'coefficient_dict': {'A': 0, 'B': 1},
    #   'coefficient_array': array([[ 1., -1.]]),
    #   'reactant_coefficient_array': array([[0., 1.]]),
    #   'product_coefficient_array': array([[1., 0.]])}
    assert rm_dict["number_of_reactions"] == 1
    assert rm_dict["number_of_species"] == 2  # A and B
    assert rm_dict["coefficient_dict"] == {"A": 0, "B": 1}
    assert list(rm_dict["molecular_species_dict"].keys()) == ["A", "B"]
    np.testing.assert_array_equal(rm_dict["coefficient_array"], np.array([[1, -1]]))
    # Check energies for each species
    assert rm_dict["molecular_species_dict"]["A"].energy == 10.0
    assert rm_dict["molecular_species_dict"]["B"].energy == 20.0
