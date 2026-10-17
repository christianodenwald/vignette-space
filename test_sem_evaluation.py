"""Checks for stable model identities and actual-value SEM queries."""

import csv
from pathlib import Path
import tempfile
import unittest

from sem_evaluation import iter_cases


class CaseGenerationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="sem-model-test-")
        self.addCleanup(directory.cleanup)
        self.input_path = Path(directory.name) / "models.csv"

    def write_models(self, rows, fields=("id", "representation", "truth_table", "C")):
        with self.input_path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(fields)
            writer.writerows(rows)

    def test_reordering_and_filtering_preserve_representation_and_query_ids(self):
        rows = [
            ("13", "canonical", "0 0 1 1", "(A & B) | (A & ~B)"),
            ("13", "alternative_1", "0 0 1 1", "A"),
        ]
        self.write_models(rows)
        expected = {case["query_id"]: case for case in iter_cases(self.input_path)}
        self.write_models(reversed(rows))
        reordered = {case["query_id"]: case for case in iter_cases(self.input_path)}
        self.assertEqual(reordered, expected)

        self.write_models(rows[1:])
        cases = list(iter_cases(self.input_path))
        self.assertEqual({case["representation"] for case in cases}, {"alternative_1"})
        self.assertEqual({case["model_id"] for case in cases}, {"13_alternative_1"})

    def test_missing_representation_requires_regeneration(self):
        self.write_models([("13", "0 0 1 1", "A")], ("id", "truth_table", "C"))
        with self.assertRaisesRegex(ValueError, "representation.*generate_data.py"):
            list(iter_cases(self.input_path))

    def test_duplicate_model_ids_are_rejected(self):
        row = ("13", "canonical", "0 0 1 1", "A")
        self.write_models([row, row])
        with self.assertRaisesRegex(ValueError, "Duplicate model ID"):
            list(iter_cases(self.input_path))

    def test_effects_follow_boolean_equations_in_all_contexts(self):
        examples = (
            ("False", "0 0 0 0"),
            ("True", "1 1 1 1"),
            ("~A", "1 1 0 0"),
            ("(A & ~B) | (B & ~A)", "0 1 1 0"),
        )
        for expression, truth_table in examples:
            with self.subTest(expression=expression):
                self.write_models([("example", "canonical", truth_table, expression)])
                cases = list(iter_cases(self.input_path, include_conjunction=True))
                self.assertEqual(len(cases), 12)
                self.assertEqual(len({case["query_id"] for case in cases}), 12)
                for index, expected in enumerate(truth_table.split()):
                    context_cases = cases[index * 3:index * 3 + 3]
                    self.assertEqual(
                        {(case["A"], case["B"], case["C"]) for case in context_cases},
                        {(index // 2, index % 2, int(expected))},
                    )
                    self.assertEqual(
                        [case["cause"] for case in context_cases],
                        [
                            f"A={index // 2}",
                            f"B={index % 2}",
                            f"A={index // 2} and B={index % 2}",
                        ],
                    )


if __name__ == "__main__":
    unittest.main()
