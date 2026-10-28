"""Remove SEM models equivalent under interchanging A and B."""

from __future__ import annotations

import csv
import re
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
INPUT_PATH = DATA_DIR / "sem_models2.csv"
OUTPUT_PATH = DATA_DIR / "sem_models2-dedup.csv"
VARIABLE_PATTERN = re.compile(r"(?<![A-Za-z0-9_])([AB])(?![A-Za-z0-9_])")


def interchange_a_and_b(expression: str) -> str:
    """Return an expression with the variable names A and B interchanged."""
    return VARIABLE_PATTERN.sub(
        lambda match: "B" if match.group(1) == "A" else "A",
        expression,
    )


def deduplicate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep all canonical rows and one alternative per expression class."""
    canonical_keys = {
        min(row["C"], interchange_a_and_b(row["C"]))
        for row in rows
        if row["representation"] == "canonical"
    }
    seen_alternatives: set[str] = set()
    deduplicated = []
    for row in rows:
        expression = row["C"]
        equivalence_key = min(expression, interchange_a_and_b(expression))
        if row["representation"] == "canonical":
            deduplicated.append(row)
        elif (
            equivalence_key not in canonical_keys
            and equivalence_key not in seen_alternatives
        ):
            seen_alternatives.add(equivalence_key)
            deduplicated.append(row)
    return deduplicated


def main() -> None:
    with INPUT_PATH.open(newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != ["id", "representation", "truth_table", "C"]:
            raise ValueError(f"Unexpected columns in {INPUT_PATH}")
        rows = list(reader)

    deduplicated = deduplicate_rows(rows)
    with OUTPUT_PATH.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(deduplicated)

    print(f"Wrote {len(deduplicated)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
