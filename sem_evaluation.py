"""Shared model loading and query generation for the SEM evaluators."""

from __future__ import annotations

import csv
from itertools import product
from pathlib import Path
from typing import Iterator


def equation_as_python(expression: str) -> str:
    """Translate the SymPy Boolean syntax emitted by generate_data.py."""
    return expression.replace("~", " not ").replace("&", " and ").replace("|", " or ")


def iter_cases(
    input_path: Path, *, include_conjunction: bool = False
) -> Iterator[dict]:
    """Read model CSVs and yield actual-value queries as result-row metadata."""
    candidates = (("A",), ("B",))
    if include_conjunction:
        candidates += (("A", "B"),)
    with input_path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"id", "representation", "truth_table", "C"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"{input_path} is missing required columns: {sorted(missing)}. "
                "Run generate_data.py to regenerate model CSVs."
            )

        model_ids: set[str] = set()
        for row in reader:
            empty = sorted(column for column in required if not row[column])
            if empty:
                raise ValueError(
                    f"{input_path}, line {reader.line_num}: empty values for {empty}"
                )
            model_id = f'{row["id"]}_{row["representation"]}'
            if model_id in model_ids:
                raise ValueError(f"Duplicate model ID in {input_path}: {model_id!r}")
            model_ids.add(model_id)
            equation = compile(
                equation_as_python(row["C"]).strip(), "<generated-sem>", "eval"
            )
            for a, b in product((0, 1), repeat=2):
                values = {"A": bool(a), "B": bool(b)}
                c = eval(equation, {"__builtins__": {}}, values)
                if not isinstance(c, bool):
                    raise ValueError(
                        f'SEM expression did not evaluate to Boolean: {row["C"]!r}'
                    )
                for variables in candidates:
                    yield {
                        "model_id": model_id,
                        "query_id": f"{model_id}|{a}|{b}|{'+'.join(variables)}",
                        "logical_model_id": row["id"],
                        "representation": row["representation"],
                        "truth_table": row["truth_table"],
                        "equation": row["C"],
                        "A": a,
                        "B": b,
                        "C": int(c),
                        "cause_type": "primitive" if len(variables) == 1 else "conjunction",
                        "cause": " and ".join(f"{v}={int(values[v])}" for v in variables),
                        "effect": f"C={int(c)}",
                    }
