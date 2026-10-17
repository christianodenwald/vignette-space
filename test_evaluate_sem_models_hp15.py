"""Regression checks for HP15 query identities and representation metadata."""

import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import evaluate_sem_models_hp15 as hp15


class EvaluationTests(unittest.TestCase):
    def test_identity_representations_keep_labels_and_unique_checker_query_ids(self):
        with tempfile.TemporaryDirectory(prefix="hp15-query-test-") as directory:
            input_path = Path(directory) / "models.csv"
            with input_path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["id", "representation", "truth_table", "C"])
                # The alternative intentionally precedes the canonical model.
                writer.writerow(["13", "alternative_1", "0 0 1 1", "A"])
                writer.writerow([
                    "13", "canonical", "0 0 1 1", "(A & B) | (A & ~B)"
                ])

            with patch.object(hp15, "check_causality", wraps=hp15.check_causality) as checker:
                rows = list(hp15._evaluate_rows(input_path))

        self.assertEqual(len(rows), 24)
        query_ids = [call.kwargs["query"].query_id for call in checker.call_args_list]
        self.assertEqual(len(set(query_ids)), 24)
        self.assertEqual(query_ids, [row["query_id"] for row in rows])
        self.assertEqual(
            {row["representation"] for row in rows[:12]}, {"alternative_1"}
        )
        self.assertEqual(
            {row["representation"] for row in rows[12:]}, {"canonical"}
        )
        for row in rows:
            self.assertEqual(row["C"], row["A"])
            self.assertEqual(row["hp15_result"], row["cause"] == f'A={row["A"]}')


if __name__ == "__main__":
    unittest.main()
