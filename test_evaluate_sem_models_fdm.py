"""Regression tests for the Lisp runner's result transport and case IDs."""

import csv
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from evaluate_sem_models_fdm import PROJECT_ROOT, _parse_driver_output


class DriverOutputTests(unittest.TestCase):
    def test_quoted_diagnostics_preserve_special_characters(self):
        witness = '\nModel "example"\n  literals:\tA, B\r\n'
        details = 'Network with "quoted" nodes\nand a tab:\t'
        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter="\t")
        writer.writerow(["RESULT", "example|0|0|A", "True", witness, details])
        writer.writerow(["RESULT", "example|0|0|B", "False", "", ""])

        self.assertEqual(
            _parse_driver_output(output.getvalue()),
            {
                "example|0|0|A": ("True", witness, details),
                "example|0|0|B": ("False", "", ""),
            },
        )

    def test_duplicate_cases_are_rejected(self):
        result = "RESULT\texample|0|0|A\tFalse\t\t\n"
        with self.assertRaisesRegex(ValueError, "Duplicate case ID"):
            _parse_driver_output(result + result)

    def test_incomplete_records_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected output"):
            _parse_driver_output("RESULT\texample|0|0|A\tTrue\t\n")


@unittest.skipUnless(
    shutil.which("sbcl") and (PROJECT_ROOT / ".lisp/setup.lisp").is_file(),
    "Requires SBCL and the project's Lisp dependencies",
)
class EvaluationIntegrationTests(unittest.TestCase):
    def test_identity_model_writes_all_positive_and_negative_cause_rows(self):
        with tempfile.TemporaryDirectory(prefix="fdm-transport-test-") as directory:
            input_path = Path(directory) / "models.csv"
            output_path = Path(directory) / "results.csv"
            model_id = 'identity "quoted"\tmodel'
            with input_path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["id", "representation", "truth_table", "C"])
                # A filtered alternative must keep its explicit label.
                writer.writerow([model_id, "alternative_1", "0 0 1 1", "A"])

            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "evaluate_sem_models_fdm.py"),
                    str(input_path),
                    "-o",
                    str(output_path),
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            with output_path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))

        self.assertEqual(len(rows), 8)
        self.assertEqual(len({row["query_id"] for row in rows}), 8)
        self.assertEqual(
            {(row["A"], row["B"], row["cause"]) for row in rows},
            {
                (str(a), str(b), f"{cause}={value}")
                for a in (0, 1)
                for b in (0, 1)
                for cause, value in (("A", a), ("B", b))
            },
        )
        for row in rows:
            self.assertEqual(row["model_id"], f"{model_id}_alternative_1")
            self.assertEqual(row["representation"], "alternative_1")
            self.assertEqual(
                row["query_id"],
                f'{model_id}_alternative_1|{row["A"]}|{row["B"]}|{row["cause"][0]}',
            )
            is_a_cause = row["cause"].startswith("A=")
            self.assertEqual(row["hp15_result"], str(is_a_cause))
            if is_a_cause:
                self.assertIn("M (equations):", row["witness"])
                self.assertTrue(row["details"])
            else:
                self.assertEqual((row["witness"], row["details"]), ("", ""))


if __name__ == "__main__":
    unittest.main()
