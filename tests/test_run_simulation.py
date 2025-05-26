import numpy as np

from web.run_simulation import make_reaction_mechanism_for_reagent


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
