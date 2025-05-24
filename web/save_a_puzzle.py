import json
from typing import Dict

from flask import jsonify


def save_a_puzzle(data):
    species_name_to_id = {name: idx for idx, name in enumerate(data["speciesNames"])}
    coefficient_array = convert_reactions_to_coefficients(
        data["reactions"], species_name_to_id
    )
    energies = dict(zip(data["speciesNames"], data["speciesEnergies"]))
    data_to_write = {
        "coefficient_dict": species_name_to_id,
        "energy_dict": energies,
        "coefficient_array": coefficient_array,
        "reagents": list(data["reagentPERs"]),
        "reagentPERs": data["reagentPERs"],
    }
    try:
        with open(f"puzzles/{data['puzzleName']}.puz", "w") as f:
            json.dump(data_to_write, f, indent=4)
        return jsonify(status="success", message="Puzzle successfully saved.")
    except Exception as e:
        print(e)
        return jsonify(status="danger", message="Error occurred. Can't save.")


def convert_reactions_to_coefficients(reactions, species_name_to_id: Dict[str, int]):
    num_species = len(species_name_to_id)
    matrix = []
    for reaction in reactions:
        coefficients = [0.0] * num_species
        for i, species_name in enumerate(reaction):
            if species_name:
                species_id = species_name_to_id[species_name]
                coefficients[species_id] += 1 if i > 1 else -1
        matrix.append(coefficients)
    return matrix
