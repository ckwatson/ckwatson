import unittest

from web.save_a_puzzle import convert_reactions_to_coefficients


class TestConvertReactionsToCoefficients(unittest.TestCase):
    def test_basic_conversion(self):
        reactions = [
            ["A", "B", "C"],  # A + B -> C
            ["C", "", "A", "B"],  # C -> A + B
            ["A", "B", "A", "B"],  # A + B -> A + B (no net change)
        ]
        species_name_to_id = {"A": 0, "B": 1, "C": 2}
        expected = [[-1.0, -1.0, 1.0], [1.0, 1.0, -1.0], [0.0, 0.0, 0.0]]
        result = convert_reactions_to_coefficients(reactions, species_name_to_id)
        self.assertEqual(result, expected)

    def test_empty_reaction(self):
        reactions = [[]]
        species_name_to_id = {"A": 0, "B": 1}
        expected = [[0.0, 0.0]]
        result = convert_reactions_to_coefficients(reactions, species_name_to_id)
        self.assertEqual(result, expected)

    def test_missing_species(self):
        reactions = [["A", "", "B"]]  # A -> B
        species_name_to_id = {"A": 0, "B": 1, "C": 2}
        expected = [[-1.0, 1.0, 0.0]]
        result = convert_reactions_to_coefficients(reactions, species_name_to_id)
        self.assertEqual(result, expected)

    def test_multiple_products(self):
        reactions = [["A", "B", "C", "D"]]  # A + B -> C + D
        species_name_to_id = {"A": 0, "B": 1, "C": 2, "D": 3}
        expected = [[-1.0, -1.0, 1.0, 1.0]]
        result = convert_reactions_to_coefficients(reactions, species_name_to_id)
        self.assertEqual(result, expected)

    def test_duplicate_species(self):
        reactions = [["A", "A", "B"]]  # 2A -> B
        species_name_to_id = {"A": 0, "B": 1}
        expected = [[-2.0, 1.0]]
        result = convert_reactions_to_coefficients(reactions, species_name_to_id)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
