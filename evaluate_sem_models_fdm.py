"""Evaluate generated SEMs with the Moonli factual-difference-making theory.

This evaluator deliberately emits primitive-cause rows only.  The Moonli
``is-cause`` API accepts one literal as its candidate cause, so conjunctive
queries are omitted rather than approximated.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from sem_evaluation import equation_as_python, iter_cases


PROJECT_ROOT = Path(__file__).resolve().parent
DRIVER_PATH = PROJECT_ROOT / "run_fdm_evaluation.lisp"
OUTPUT_FIELDS = (
    "model_id",
    "query_id",
    "logical_model_id",
    "representation",
    "truth_table",
    "equation",
    "A",
    "B",
    "C",
    "cause_type",
    "cause",
    "effect",
    "hp15_result",
    "witness",
    "details",
)


def _python_ast_to_lisp(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        if node.id == "True":
            return "t"
        if node.id == "False":
            return "nil"
        return node.id.upper()
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return "t" if node.value else "nil"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return f"(not {_python_ast_to_lisp(node.operand)})"
    if isinstance(node, ast.BoolOp):
        operator = "and" if isinstance(node.op, ast.And) else "or"
        return f"({operator} {' '.join(_python_ast_to_lisp(v) for v in node.values)})"
    raise ValueError(f"Unsupported Boolean expression node: {ast.dump(node)}")


def _equation_as_lisp(expression: str) -> str:
    parsed = ast.parse(equation_as_python(expression).strip(), mode="eval")
    return _python_ast_to_lisp(parsed.body)


def _lisp_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _actual_literal(variable: str, value: int) -> str:
    return variable if value else f"(not {variable})"


def _case_form(case: dict) -> str:
    variable, value = case["cause"].split("=")
    cause = _actual_literal(variable, int(value))
    effect = _actual_literal("C", case["C"])
    return (
        f'({_lisp_string(case["model_id"])} {_equation_as_lisp(case["equation"])} '
        f'{case["A"]} {case["B"]} {case["C"]} "primitive" {cause} {effect})'
    )


def _parse_driver_output(output: str) -> dict[str, tuple[str, str, str]]:
    results: dict[str, tuple[str, str, str]] = {}
    reader = csv.reader(io.StringIO(output, newline=""), delimiter="\t", strict=True)
    for fields in reader:
        if not fields:
            continue
        if len(fields) != 5 or fields[0] != "RESULT":
            raise ValueError(f"Unexpected output from FDM runner: {fields!r}")
        _, case_id, result, witness, details = fields
        if case_id in results:
            raise ValueError(f"Duplicate case ID from FDM runner: {case_id!r}")
        results[case_id] = (result, witness, details)
    return results


def _evaluate_rows(input_path: Path, lisp_command: str, driver_path: Path) -> Iterable[dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="fdm-evaluation-") as temporary_directory:
        temporary_path = Path(temporary_directory)
        cases_path = temporary_path / "cases.lisp"
        output_path = temporary_path / "results.tsv"
        print(f"[1/4] Preparing FDM cases from {input_path}...", flush=True)
        cases = list(iter_cases(input_path))
        with cases_path.open("w") as output:
            output.writelines(_case_form(case) + "\n" for case in cases)
        count = len(cases)
        print(f"[1/4] Prepared {count} primitive cases.", flush=True)
        command = [
            *shlex.split(lisp_command),
            "--script",
            str(driver_path),
            str(cases_path),
            str(output_path),
        ]
        print(
            f"[2/4] Starting Moonli FDM runner: {' '.join(command)}",
            flush=True,
        )
        try:
            completed = subprocess.run(
                command,
                cwd=driver_path.parent,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=None,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                f"Could not start Lisp command {lisp_command!r}. "
                "Install SBCL or pass --lisp-command with an available Lisp runner."
            ) from error
        if completed.returncode:
            raise RuntimeError(
                "Moonli FDM evaluation failed.\n"
                f"Command: {' '.join(command)}"
            )
        print("[3/4] Moonli runner finished; reading results...", flush=True)
        results = _parse_driver_output(output_path.read_text())
        if len(results) != count:
            raise RuntimeError(
                f"Moonli FDM runner returned {len(results)} results for {count} cases."
            )
        print(f"[3/4] Read {len(results)} results.", flush=True)

        for case in cases:
            result, witness, details = results[case["query_id"]]
            yield {
                **case,
                # Keep the HP15-compatible column name so the
                # two result files have the same schema.
                "hp15_result": result,
                "witness": witness,
                "details": details,
            }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "data" / "sem_models_combined.csv",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "fdm_results.csv",
    )
    parser.add_argument(
        "--lisp-command",
        default="sbcl",
        help="Lisp executable and arguments, for example 'sbcl' or 'ros run'.",
    )
    parser.add_argument("--driver", type=Path, default=DRIVER_PATH)
    args = parser.parse_args()

    rows = list(_evaluate_rows(args.input, args.lisp_command, args.driver))
    print("[4/4] Writing CSV rows...", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[4/4] Wrote {len(rows)} evaluations to {args.output}")


if __name__ == "__main__":
    main()
