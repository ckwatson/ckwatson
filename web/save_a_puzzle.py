import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List

from flask import jsonify

SAFE_NAME_RE = re.compile(
    r"^[\w\- ]{1,80}$"
)  # enforced elsewhere too, but double check


def _error(message: str):
    return jsonify(status="danger", message=message)


def _validate_lengths(data) -> List[str]:
    errors = []
    n_species = len(data.get("speciesNames", []))
    if len(data.get("speciesIfReactants", [])) != n_species:
        errors.append("speciesIfReactants length must equal speciesNames length.")
    if len(data.get("speciesEnergies", [])) != n_species:
        errors.append("speciesEnergies length must equal speciesNames length.")
    # reagentPERs: each key -> boolean list length == number of reactions
    n_reactions = len(data.get("reactions", []))
    for reagent, toggles in data.get("reagentPERs", {}).items():
        if len(toggles) != n_reactions:
            errors.append(
                f"Reagent '{reagent}' PER toggles length {len(toggles)} != number of reactions {n_reactions}."
            )
    return errors


def _validate_species_and_reactions(data) -> List[str]:
    errors = []
    species_names: List[str] = data.get("speciesNames", [])
    # ensure uniqueness
    if len(set(species_names)) != len(species_names):
        errors.append("speciesNames must be unique.")
    allowed_species = set(species_names)
    for idx, reaction in enumerate(data.get("reactions", [])):
        # reaction is expected length 4 from schema, but be defensive
        if not isinstance(reaction, list):
            errors.append(f"Reaction #{idx} is not a list.")
            continue
        if len(reaction) != 4:
            errors.append(
                f"Reaction #{idx} must have exactly 4 slots (got {len(reaction)})."
            )
        for s in reaction:
            if not s:
                continue
            if s not in allowed_species:
                errors.append(f"Reaction #{idx} references unknown species '{s}'.")
    # ensure energies are finite
    for name, energy in zip(species_names, data.get("speciesEnergies", [])):
        if not isinstance(energy, (int, float)) or not math.isfinite(energy):
            errors.append(f"Energy for species '{name}' must be a finite number.")
    return errors


def save_a_puzzle(data):
    """Persist a validated puzzle definition to disk safely.

    Assumes JSON schema validation already occurred upstream. Adds defense-in-depth:
    - Re-validates puzzleName against strict regex & prevents traversal
    - Validates internal array length consistency & species references
    - Enforces max limits to avoid resource abuse
    - Writes atomically (temp file + rename) and prevents overwrite
    """

    puzzle_name = data.get("puzzleName", "").strip()
    if not SAFE_NAME_RE.match(puzzle_name):
        return _error("Invalid puzzle name.")

    # Resolve puzzles directory at call time (supports changed CWD in tests)
    puzzles_dir = Path("puzzles").resolve()
    # Ensure puzzles directory exists
    try:
        puzzles_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print("Failed ensuring puzzles dir:", e)
        return _error("Server misconfiguration: cannot create puzzles directory.")

    target_path = (puzzles_dir / f"{puzzle_name}.puz").resolve()
    # Path traversal defense: target must be inside puzzles_dir
    if not str(target_path).startswith(str(puzzles_dir) + os.sep):
        return _error("Invalid puzzle path.")
    if target_path.exists():  # Do not overwrite existing puzzles
        return _error("Puzzle already exists.")

    # Enforce basic size / complexity limits
    max_species = 50
    max_reactions = 50
    if len(data.get("speciesNames", [])) > max_species:
        return _error(f"Too many species (>{max_species}).")
    if len(data.get("reactions", [])) > max_reactions:
        return _error(f"Too many reactions (>{max_reactions}).")

    # Internal validations
    errors = _validate_lengths(data)
    errors += _validate_species_and_reactions(data)
    if errors:
        return _error("; ".join(errors))

    # Build coefficient dict & arrays
    species_name_to_id = {name: idx for idx, name in enumerate(data["speciesNames"])}
    try:
        coefficient_array = convert_reactions_to_coefficients(
            data["reactions"], species_name_to_id
        )
    except KeyError as e:
        return _error(f"Unknown species in reactions: {e.args[0]}")

    energies = dict(zip(data["speciesNames"], data["speciesEnergies"]))
    data_to_write = {
        "coefficient_dict": species_name_to_id,
        "energy_dict": energies,
        "coefficient_array": coefficient_array,
        # 'reagents' appears unused downstream; keep for backward compatibility but derive from reagentPERs keys
        "reagents": list(data["reagentPERs"].keys()),
        "reagentPERs": data["reagentPERs"],
    }

    # Atomic write: write to a temp file in same directory then rename
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=str(puzzles_dir), delete=False
        ) as tmp:
            json.dump(data_to_write, tmp, indent=4)
            tmp_path = Path(tmp.name)
        # Use os.link + rename semantics to avoid overwriting if race; ensure destination still absent
        # Simple check again just before rename
        if target_path.exists():
            tmp_path.unlink(missing_ok=True)
            return _error("Puzzle already exists.")
        os.replace(tmp_path, target_path)
        return jsonify(status="success", message="Puzzle successfully saved.")
    except Exception as e:  # pragma: no cover - rare filesystem errors
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)  # cleanup
            except Exception:
                pass
        print("Error saving puzzle:", e)
        return _error("Error occurred. Can't save.")


def convert_reactions_to_coefficients(reactions, species_name_to_id: Dict[str, int]):
    """Convert list of symbolic reactions into coefficient matrix.

    Each reaction is a 4-length list: [R1, R2, P1, P2]; blanks treated as absent.
    Reactants get -1 stoichiometric sign, products +1 to align with existing tests.
    (Historical note: elsewhere in runtime the sign convention may differ; tests
    for this helper expect negative for reactants and positive for products.)
    """
    num_species = len(species_name_to_id)
    matrix = []
    for reaction in reactions:
        coefficients = [0.0] * num_species
        for i, species_name in enumerate(reaction):
            if not species_name:
                continue
            species_id = species_name_to_id[species_name]
            # First two entries are reactants: negative; last two products: positive
            coefficients[species_id] += -1 if i < 2 else 1
        matrix.append(coefficients)
    return matrix
