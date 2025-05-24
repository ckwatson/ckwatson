import json
from pprint import pprint
from typing import Dict

from flask import jsonify


def save_a_puzzle(data):
    # now convert:
    species_name_to_id = {species: i for i, species in enumerate(data["speciesNames"])}
    coefficient_array = convert_reactions_to_coefficients(
        data["reactions"], species_name_to_id
    )
    coefficient_dict = {
        # TODO: This is AI-generated. Check this.
        species: i
        for i, species in enumerate(data["speciesNames"])
    }
    energies = dict(zip(data["speciesNames"], data["speciesEnergies"]))
    data_to_write = {
        "coefficient_dict": coefficient_dict,
        "energy_dict": energies,
        "coefficient_array": coefficient_array,
        "reagents": list(data["reagentPERs"].keys()),
        "reagentPERs": data["reagentPERs"],
    }
    print("Data prepared:")
    pprint(data_to_write)
    with open("puzzles/" + data["puzzleName"] + ".puz", "w") as f:
        try:
            json.dump(data_to_write, f, indent=4)
        except Exception as e:
            print(e)
            return jsonify(status="danger", message="Error occured. Can't save.")
        else:
            return jsonify(status="success", message="Puzzle successfully saved.")


def convert_reactions_to_coefficients(reactions, species_name_to_id: Dict[str, int]):
    num_species = len(species_name_to_id)
    matrix = []
    for reaction in reactions:
        coefficients = [0.0] * num_species
        for i, speciesName in enumerate(reaction):
            if speciesName:
                speciesID = species_name_to_id[speciesName]
                coefficients[speciesID] += 1 if i > 1 else -1
        matrix.append(coefficients)
    return matrix
