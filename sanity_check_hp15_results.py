"""Sanity checks for agreement between equivalent SEM representations."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "results" / "hp15_results.csv"
COMPARISON_COLUMNS = ("A", "B", "C", "cause", "effect")


def sanity_check_results(
    results_path: Path,
    result_column: str = "hp15_result",
) -> List[Dict[str, str]]:
    """Return mismatches between canonical and alternative model results.

    Rows are paired by logical model, context, and query. Each returned
    dictionary describes one alternative whose result differs from canonical.
    """
    with results_path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {
            "logical_model_id",
            "representation",
            "model_id",
            result_column,
            *COMPARISON_COLUMNS,
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"{results_path} is missing required columns: {sorted(missing)}"
            )

        groups: Dict[tuple[str, tuple[str, ...]], List[dict[str, str]]] = defaultdict(list)
        for row in reader:
            key = (
                row["logical_model_id"],
                tuple(row[column] for column in COMPARISON_COLUMNS),
            )
            groups[key].append(row)

    mismatches: List[Dict[str, str]] = []
    for (logical_model_id, comparison_values), rows in groups.items():
        canonical = [row for row in rows if row["representation"] == "canonical"]
        alternatives = [
            row for row in rows if row["representation"] != "canonical"
        ]
        if len(canonical) != 1:
            raise ValueError(
                f"Expected exactly one canonical row for logical_model_id="
                f"{logical_model_id!r}, query={comparison_values!r}; "
                f"found {len(canonical)}."
            )

        canonical_row = canonical[0]
        for alternative in alternatives:
            if alternative[result_column] != canonical_row[result_column]:
                mismatch = {
                    "logical_model_id": logical_model_id,
                    "canonical_model_id": canonical_row["model_id"],
                    "alternative_model_id": alternative["model_id"],
                    "canonical_representation": canonical_row["representation"],
                    "alternative_representation": alternative["representation"],
                    "canonical_result": canonical_row[result_column],
                    "alternative_result": alternative[result_column],
                }
                mismatch.update(
                    dict(zip(COMPARISON_COLUMNS, comparison_values))
                )
                mismatches.append(mismatch)

    return mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results",
        nargs="?",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="Results CSV to check",
    )
    parser.add_argument(
        "--result-column",
        default="hp15_result",
        help="Column containing the theory result to compare",
    )
    args = parser.parse_args()

    mismatches = sanity_check_results(args.results, args.result_column)
    if mismatches:
        print(f"Found {len(mismatches)} representation mismatches:")
        for mismatch in mismatches:
            print(mismatch)
        raise SystemExit(1)

    print(
        f"Sanity check passed: canonical and alternative representations agree "
        f"for {args.result_column}."
    )


if __name__ == "__main__":
    main()
