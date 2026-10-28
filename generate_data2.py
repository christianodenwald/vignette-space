"""Generate SEM expressions from singleton and miniterm clauses."""

import csv
from itertools import product
from pathlib import Path

from sympy import And, Not, Or, symbols


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = DATA_DIR / "sem_models2.csv"
CANONICAL_PATH = DATA_DIR / "sem_models.csv"

A, B, T = symbols("A B T")
rows = list(product((0, 1), repeat=2))
terms = [
    ("A", lambda a, b: a, A),
    ("~A", lambda a, b: not a, Not(A)),
    ("B", lambda a, b: b, B),
    ("~B", lambda a, b: not b, Not(B)),
    ("(~A & ~B)", lambda a, b: not a and not b, And(Not(A), Not(B))),
    ("(~A & B)", lambda a, b: not a and b, And(Not(A), B)),
    ("(A & ~B)", lambda a, b: a and not b, And(A, Not(B))),
    ("(A & B)", lambda a, b: a and b, And(A, B)),
    ("T", lambda a, b: True, T),
]
HEADER = ["id", "representation", "truth_table", "C"]


def load_canonical_expressions() -> dict[str, str]:
    with CANONICAL_PATH.open(newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != HEADER:
            raise ValueError(f"Unexpected columns in {CANONICAL_PATH}")
        return {
            " ".join(row["truth_table"].split()): row["C"]
            for row in reader
        }


def main() -> None:
    canonical_expressions = load_canonical_expressions()
    with OUTPUT_PATH.open("w", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(HEADER)

        for model_id, mask in enumerate(range(2 ** len(terms)), start=1):
            chosen = [
                expression
                for index, (_, _, expression) in enumerate(terms)
                if mask >> index & 1
            ]
            expression = Or(*chosen)
            # truth_table = " ".join(str((k >> i) & 1) for i in range(len(minterms)))
            truth_table = " ".join(
                str(
                    int(
                        any(
                            evaluator(a, b)
                            for index, (_, evaluator, _) in enumerate(terms)
                            if mask >> index & 1
                        )
                    )
                )
                for a, b in rows
            )
            representation = (
                "canonical"
                if canonical_expressions[truth_table] == str(expression)
                else "alternative"
            )
            writer.writerow([model_id, representation, truth_table, expression])


if __name__ == "__main__":
    main()
