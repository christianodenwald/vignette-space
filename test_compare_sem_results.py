"""Checks for reliable joins, verdict counts, and representation comparisons."""

import csv
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from compare_sem_results import compare_results, print_report
from sem_evaluation import iter_cases


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="sem-comparison-test-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.hp15_path = self.root / "hp15.csv"
        self.fdm_path = self.root / "fdm.csv"
        models_path = self.root / "models.csv"
        with models_path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("id", "representation", "truth_table", "C"))
            writer.writerows([
                ("15", "canonical", "0 1 1 1", "(A & B) | (A & ~B) | (B & ~A)"),
                ("15", "alternative_1", "0 1 1 1", "A | B"),
                ("9", "canonical", "0 0 0 1", "A & B"),
            ])
        self.hp15_rows = []
        self.fdm_rows = []
        for case in iter_cases(models_path, include_conjunction=True):
            a, b = case["A"], case["B"]
            is_or = case["logical_model_id"] == "15"
            redundant_context = (a, b) == ((1, 1) if is_or else (0, 0))
            if case["cause_type"] == "conjunction":
                hp_verdict = redundant_context
            else:
                other_value = b if case["cause"].startswith("A=") else a
                hp_verdict = other_value == (0 if is_or else 1)
            self.hp15_rows.append({**case, "hp15_result": str(hp_verdict)})
            if case["cause_type"] == "primitive":
                extra_cause = redundant_context and (not is_or or case["representation"] == "alternative_1")
                self.fdm_rows.append({**case, "hp15_result": str(hp_verdict or extra_cause)})
        self.save()

    def write_rows(self, path, rows):
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def save(self):
        self.write_rows(self.hp15_path, self.hp15_rows)
        self.write_rows(self.fdm_path, self.fdm_rows)

    def compare(self):
        return compare_results(self.hp15_path, self.fdm_path)

    def test_shuffled_rows_match_by_id_and_keep_conjunctions_separate(self):
        self.fdm_rows.reverse()
        self.save()
        analysis = self.compare()
        comparisons = analysis["comparisons"]
        self.assertEqual(len(comparisons), 24)
        self.assertEqual(sum(row["hp15_result"] == "True" for row in comparisons), 12)
        self.assertEqual(sum(row["fdm_result"] == "True" for row in comparisons), 16)
        disagreements = [row for row in comparisons if row["hp15_result"] != row["fdm_result"]]
        self.assertEqual(len(disagreements), 4)
        self.assertTrue(all(row["hp15_conjunction_result"] == "True" for row in disagreements))
        fdm_pairs = analysis["representation_pairs"]["FDM"]
        self.assertEqual(len(fdm_pairs), 8)
        self.assertEqual(sum(c["hp15_result"] != a["hp15_result"] for c, a in fdm_pairs), 2)
        with redirect_stdout(io.StringIO()) as output:
            print_report(analysis)
        self.assertIn("Agreement: 20/24 (83.3%)", output.getvalue())
        self.assertIn("HP15 conjunctions: 3/12 accepted", output.getvalue())

    def test_participation_resolves_original_differences_but_finds_canonical_or_cases(self):
        analysis = self.compare()
        comparisons = analysis["comparisons"]
        self.assertEqual(sum(row["hp15_part_of_cause_result"] == "True" for row in comparisons), 18)
        original = [row for row in comparisons if row["hp15_result"] != row["fdm_result"]]
        self.assertTrue(all(row["hp15_part_of_cause_result"] == row["fdm_result"] for row in original))
        remaining = [row for row in comparisons if row["hp15_part_of_cause_result"] != row["fdm_result"]]
        self.assertEqual({row["query_id"] for row in remaining}, {"15_canonical|1|1|A", "15_canonical|1|1|B"})
        with redirect_stdout(io.StringIO()) as output:
            print_report(analysis)
        self.assertIn("Causal-participation agreement: 22/24 (91.7%)", output.getvalue())
        self.assertIn("Resolved original primitive disagreements: 4/4", output.getvalue())
        self.assertIn("2/2 involve FDM verdicts that change between equivalent equations", output.getvalue())

    def test_missing_primitive_queries_are_not_silently_dropped(self):
        self.fdm_rows.pop()
        self.save()
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            self.compare()

    def test_metadata_mismatch_for_same_id_is_rejected(self):
        self.fdm_rows[0]["equation"] = "A"
        self.save()
        with self.assertRaisesRegex(ValueError, "Metadata mismatch.*equation"):
            self.compare()

    def test_duplicate_ids_and_non_boolean_verdicts_are_rejected(self):
        original = list(self.fdm_rows)
        for rows, message in (
            ([*original, original[0]], "duplicate query_id"),
            ([{**original[0], "hp15_result": "ERROR"}, *original[1:]], "invalid verdict"),
        ):
            with self.subTest(message=message):
                self.write_rows(self.fdm_path, rows)
                with self.assertRaisesRegex(ValueError, message):
                    self.compare()

    def test_alternatives_require_canonical_queries(self):
        self.hp15_rows = [row for row in self.hp15_rows if row["representation"] == "alternative_1"]
        self.fdm_rows = [row for row in self.fdm_rows if row["representation"] == "alternative_1"]
        self.save()
        with self.assertRaisesRegex(ValueError, "Expected one canonical row"):
            self.compare()

    def test_missing_conjunction_evidence_is_reported_as_unavailable(self):
        self.hp15_rows = [row for row in self.hp15_rows if row["cause_type"] == "primitive"]
        self.save()
        analysis = self.compare()
        known = [row for row in analysis["comparisons"] if row["hp15_part_of_cause_result"]]
        self.assertEqual(len(known), 12)
        self.assertTrue(all(row["hp15_part_of_cause_result"] == "True" for row in known))
        with redirect_stdout(io.StringIO()) as output:
            print_report(analysis)
        self.assertIn("Conjunction results unavailable for 4 disagreements", output.getvalue())
        self.assertIn("Participation unavailable for 12 queries; excluded", output.getvalue())
        self.assertIn("Causal-participation agreement: 12/12 (100.0%)", output.getvalue())

    def test_no_participation_verdicts_does_not_report_false_agreement(self):
        self.hp15_rows = [
            {**row, "hp15_result": "False"}
            for row in self.hp15_rows if row["cause_type"] == "primitive"
        ]
        self.save()
        with redirect_stdout(io.StringIO()) as output:
            print_report(self.compare())
        self.assertIn("No queries with sufficient evidence to compare causal participation", output.getvalue())
        self.assertNotIn("Causal-participation agreement:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
