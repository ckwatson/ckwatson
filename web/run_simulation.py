import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from gevent import sleep
from numpy._typing import NDArray
from tabulate import tabulate

from kernel.data import (
    condition_class,
    puzzle_class,
    reaction_mechanism_class,
    solution_class,
)
from kernel.engine import align, plotter
from kernel.engine.driver import run_proposed_experiment, run_true_experiment


def score_user_answer(true_data: np.ndarray, user_data: np.ndarray) -> float:
    """
    Compare user_data to true_data and return a score as a percentage (100 = perfect match).
    The score is 100 * (1 - (sum(abs(true-user)) / sum(abs(true))))
    """
    true_aligned, user_aligned = align.align_for_scoring(true_data, user_data)
    # Only compare concentrations, not time (assume first row is time)
    diff = np.abs(true_aligned[1:] - user_aligned[1:])
    denom = np.abs(true_aligned[1:]).sum()
    if denom == 0:
        return 0.0
    score = 1.0 - (diff.sum() / denom)
    return max(0.0, min(1.0, score)) * 100


def simulate_experiments_and_plot(
    data: Dict,
    puzzle_definition: Dict,
    temperature: float,
    diag: bool = False,
) -> Tuple[str, str, float]:
    """
    Simulate the puzzle and draw plots.
    """
    logger = logging.getLogger(data["jobID"]).getChild("simulate_experiments_and_plot")
    # TODO: Remove this hack add properly fix the "first couple of lines missing" issue.
    sleep(0.1)
    # Now start preparing the instances of custom classes for further actual use in Engine.Driver:
    #    (1) Instance of the Puzzle class:
    #           (1.1) general data:
    elementary_reactions = np.array(puzzle_definition["coefficient_array"], dtype=float)
    # `coefficient_dict` maps species names to their indices in the coefficient array.
    species_list = sorted(
        puzzle_definition["coefficient_dict"],
        key=puzzle_definition["coefficient_dict"].get,
    )
    num_rxn = len(puzzle_definition["coefficient_array"])
    num_mol = len(species_list)
    logger.info(
        "        %i species are involved. They are: %s", num_mol, " ".join(species_list)
    )
    #           (1.2) data about the reagents, used in pre-equilibrium computations:
    #         - - - - - - - - - - - - - - -
    logger.info("    (0) Pre-equilibration data:")
    this_puzzle = puzzle_class.puzzle(
        num_rxn,
        num_mol,
        species_list,
        elementary_reactions,
        puzzle_definition["energy_dict"],
        reagent_dictionary=[
            # Note: We use a list here because we want to keep the order of the reagents as they are defined in the puzzle file.
            # TODO: Why would it matter? The `.puz` files, when loaded into the Python realm as `dict`s, will not be ordered.
            (
                reagent,
                make_reaction_mechanism_for_reagent(
                    PERsToggles,
                    data["jobID"],
                    puzzle_definition,
                    reagent,
                    species_list,
                ),
            )
            for reagent, PERsToggles in puzzle_definition["reagentPERs"].items()
        ],
        Ea=puzzle_definition.get("transition_state_energies", None),
    )
    logger.info("    (1) Puzzle Instance successfully created.")
    #    (2) Instance of the Condition class:
    # rxn_temp = temperature
    # Each entry in data['conditions'] is of the form:
    #     [name of the reactant, amount, its fridge temperature]
    r_names = [reactant["name"] for reactant in data["conditions"]]
    r_concs = [reactant["amount"] for reactant in data["conditions"]]
    r_temps = [reactant["temperature"] for reactant in data["conditions"]]
    m_concs = [0.0] * num_mol
    logger.info("        %i reactants out of %i species.", len(r_names), num_mol)
    #         - - - - - - - - - - - - - - -
    this_condition: condition_class.Condition = condition_class.Condition(
        temperature, species_list, r_names, r_temps, r_concs, m_concs
    )
    logger.info("    (2) Condition Instance successfully created.")
    #    (3) Instance of the Solution class:
    coefficient_array_proposed = []
    for each_rxn_proposed in data["reactions"]:
        coefficient_line_proposed = [0] * num_mol
        for slot_id, each_slot in enumerate(each_rxn_proposed):
            if each_slot == "":
                continue
            if each_slot not in species_list:
                logger.error(
                    '            The species "%s" is not in the list of species: %s',
                    each_slot,
                    ", ".join(species_list),
                )
                continue
            species_id = species_list.index(each_slot)
            # Reactants (which sit in the first 2 slots) have a positive coefficient, because they are consumed in the reaction.
            # Products (which sit in the last 2 slots) have a negative coefficient, because they are produced in the reaction.
            coefficient_line_proposed[species_id] += 1 if slot_id < 2 else -1
        coefficient_array_proposed.append(coefficient_line_proposed)
    # collect the equilibrated concentrations
    table = tabulate(
        coefficient_array_proposed,
        headers=species_list,
        floatfmt=".4g",
        tablefmt="github",
    )
    num_rxn_proposed = len(coefficient_array_proposed)
    logger.info(
        f"        User-proposed {num_rxn_proposed} reactions. They form a coefficient array of:\n%s",
        table,
    )
    table = tabulate(
        puzzle_definition["coefficient_array"],
        headers=species_list,
        floatfmt=".4g",
        tablefmt="github",
    )
    logger.info(
        "        Compare this array with the true coefficient array:\n%s",
        table,
    )
    #         - - - - - - - - - - - - - - -
    this_solution = solution_class.solution(
        num_rxn_proposed,
        num_mol,
        species_list,
        coefficient_array_proposed,
        puzzle_definition["energy_dict"],
    )
    logger.info("    (3) Solution Instance successfully created.")
    # Finally, drive the engine with these data:
    logger.info("    (4) Simulating...")

    logger.info("         (a) True Model first:")

    logger.info("             simulating...")
    true_data: np.ndarray = run_true_experiment(
        data["jobID"], this_puzzle, this_condition, diag=diag
    )
    logger.info("         (b) User Model then:")

    logger.info("             simulating...")
    # if we are simulating the true_model then solution argument is none
    user_data: Optional[np.ndarray] = run_proposed_experiment(
        data["jobID"], this_condition, this_solution, true_data, diag=diag
    )
    if user_data is None:
        logger.error("             The model you proposed failed.")

    logger.info("    (5) Drawing plots... ")
    (plot_individual, plot_combined) = plotter.sub_plots(
        job_id=data["jobID"],
        plotting_dict=puzzle_definition["coefficient_dict"],
        true_data=true_data,
        user_data=user_data,
    )
    score = None
    if user_data is not None:
        score = score_user_answer(true_data, user_data)
    else:
        score = 0.0
    return plot_combined, plot_individual, score


def make_reaction_mechanism_for_reagent(
    is_each_involved: List[bool],
    job_id: str,
    puzzle_definition: Dict,
    reagent: str,
    species_list: List[str],
):
    """
    Make a reaction mechanism for the natural reaction of the reagent when sitting idle in a canister/beaker.
    This will be used for simulating the pre-equilibration of the reagent.
    """
    logger = logging.getLogger(job_id).getChild("make_reaction_mechanism_for_reagent")
    logger.info('        Making reaction mechanism for the reagent "%s":', reagent)
    reagent_id = puzzle_definition["coefficient_dict"][reagent]
    # Filter for pre-equilibration reactions:
    pre_equl_elem_rxns = [
        # `is_involved` = "is this elementary reaction involved in the pre-equilibration of this reagent?"
        rxn
        for rxn, is_involved in zip(
            puzzle_definition["coefficient_array"], is_each_involved
        )
        if is_involved
    ]
    if not pre_equl_elem_rxns:
        logger.info(
            f'            For the reagent #{reagent_id} "{reagent}", no pre-equilibration is needed.'
        )
        pre_equl_elem_rxns = np.array([[0.0]], dtype=float)
        reagent_species_list = [reagent]
    else:
        # convert it into a numpy dict
        pre_equl_elem_rxns = np.array(pre_equl_elem_rxns, dtype=float)
        # a boolean array of whether each species specified in the puzzle file is present in this set of ElemRxns for preEqul.
        if_uninvolvedSpecies: NDArray[np.bool_] = np.all(
            pre_equl_elem_rxns == False, axis=0
        )
        # now, remove unused species to simplify the rxn. set used for pre-equilibration of this particular reagent:
        pre_equl_elem_rxns = np.delete(
            pre_equl_elem_rxns, np.where(if_uninvolvedSpecies), axis=1
        )
        logger.debug(f"            species_list         : {species_list}")
        logger.debug(f"            if_uninvolvedSpecies: {if_uninvolvedSpecies}")
        # List of species involved in the pre-equilibration of this reagent.
        reagent_species_list = [
            s
            for s, uninvolved in zip(species_list, if_uninvolvedSpecies)
            if not uninvolved
        ]
        # Print out the pre-equilibration reactions:
        table = tabulate(
            pre_equl_elem_rxns,
            headers=reagent_species_list,
            floatfmt=".4g",
            tablefmt="github",
        )
        logger.info("            About pre-equilibration:\n%s", table)
    reaction_mechanism = reaction_mechanism_class.reaction_mechanism(
        len(pre_equl_elem_rxns),
        len(reagent_species_list),
        reagent_species_list,
        pre_equl_elem_rxns,
        puzzle_definition["energy_dict"],
    )
    return reaction_mechanism
