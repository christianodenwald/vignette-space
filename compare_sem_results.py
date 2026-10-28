"""Compare saved HP15 and FDM verdicts without rerunning either evaluator.

Compare both primitive verdicts and causal participation: whether HP15 accepts
the literal individually or as part of an accepted conjunction. Missing
conjunction evidence leaves participation unknown when the primitive is false.
Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
METADATA = (
    "model_id", "logical_model_id", "representation", "truth_table",
    "equation", "A", "B", "C", "cause_type", "cause", "effect",
)
REPRESENTATION_KEY = (
    "logical_model_id", "A", "B", "C", "cause_type", "cause", "effect",
)


def load_results(path: Path) -> list[dict[str, str]]:
    """Read CSV records, rejecting ambiguous identities and invalid verdicts."""
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"query_id", "hp15_result", *METADATA}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = []
        seen = set()
        for row in reader:
            empty = sorted(column for column in required if not row.get(column))
            if empty:
                raise ValueError(f"{path}, line {reader.line_num}: empty fields {empty}")
            query_id = row["query_id"]
            if query_id in seen:
                raise ValueError(f"{path}: duplicate query_id {query_id!r}")
            seen.add(query_id)
            # FDM intentionally uses the same result column name as HP15.
            if row["hp15_result"] not in ("True", "False"):
                raise ValueError(f"{path}: invalid verdict for {query_id!r}")
            if row["cause_type"] not in ("primitive", "conjunction"):
                raise ValueError(f"{path}: invalid cause_type for {query_id!r}")
            rows.append(row)
    return rows


def representation_pairs(rows: list[dict[str, str]]) -> list[tuple[dict, dict]]:
    """Pair each alternative query with its canonical equivalent."""
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[column] for column in REPRESENTATION_KEY)].append(row)
    pairs = []
    for key, group in groups.items():
        canonical = [row for row in group if row["representation"] == "canonical"]
        if len(canonical) != 1:
            raise ValueError(f"Expected one canonical row for {key!r}; found {len(canonical)}")
        for alternative in group:
            if alternative["representation"] != "canonical":
                if alternative["truth_table"] != canonical[0]["truth_table"]:
                    raise ValueError(f"Truth-table mismatch for {key!r}")
                pairs.append((canonical[0], alternative))
    return pairs


def compare_results(hp15_path: Path, fdm_path: Path) -> dict:
    """Validate and join primitive queries by ID, retaining conjunction evidence."""
    hp15_rows = load_results(hp15_path)
    fdm_rows = load_results(fdm_path)
    if any(row["cause_type"] != "primitive" for row in fdm_rows):
        raise ValueError("FDM results must contain primitive queries only")
    hp15 = {row["query_id"]: row for row in hp15_rows if row["cause_type"] == "primitive"}
    fdm = {row["query_id"]: row for row in fdm_rows}
    if hp15.keys() != fdm.keys():
        only_hp15 = sorted(hp15.keys() - fdm.keys())
        only_fdm = sorted(fdm.keys() - hp15.keys())
        raise ValueError(
            "Primitive query coverage differs: "
            f"HP15-only={len(only_hp15)} {only_hp15[:3]}; "
            f"FDM-only={len(only_fdm)} {only_fdm[:3]}"
        )
    if not hp15:
        raise ValueError("No primitive queries to compare")

    conjunctions = {}
    for row in hp15_rows:
        if row["cause_type"] == "conjunction":
            key = (row["model_id"], row["A"], row["B"], row["C"], row["effect"])
            expected_cause = f"A={row['A']} and B={row['B']}"
            if row["cause"] != expected_cause or key in conjunctions:
                raise ValueError(f"Ambiguous conjunction query: {row['query_id']!r}")
            conjunctions[key] = row["hp15_result"]

    comparisons = []
    for query_id, hp_row in hp15.items():
        fdm_row = fdm[query_id]
        different = [column for column in METADATA if hp_row[column] != fdm_row[column]]
        if different:
            raise ValueError(f"Metadata mismatch for {query_id!r}: {different}")
        key = (hp_row["model_id"], hp_row["A"], hp_row["B"], hp_row["C"], hp_row["effect"])
        conjunction = conjunctions.get(key, "")
        if hp_row["hp15_result"] == "True" or conjunction == "True":
            participation = "True"
        elif conjunction == "False":
            participation = "False"
        else:
            participation = ""
        comparisons.append({
            "query_id": query_id,
            **{column: hp_row[column] for column in METADATA},
            "hp15_result": hp_row["hp15_result"],
            "fdm_result": fdm_row["hp15_result"],
            "hp15_conjunction_result": conjunction,
            "hp15_part_of_cause_result": participation,
        })

    return {
        "comparisons": comparisons,
        "hp15_rows": hp15_rows,
        "fdm_rows": fdm_rows,
        "representation_pairs": {
            "HP15": representation_pairs(hp15_rows),
            "FDM": representation_pairs(fdm_rows),
        },
    }


def print_table(headers: tuple[str, ...], rows: list[tuple]) -> None:
    entries = [headers, *[tuple(map(str, row)) for row in rows]]
    widths = [max(len(row[index]) for row in entries) for index in range(len(headers))]
    for row in entries:
        print("  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())


def print_participation_report(analysis: dict) -> None:
    """Compare FDM with HP15 membership in the causes tested in this dataset."""
    comparisons = analysis["comparisons"]
    known = [row for row in comparisons if row["hp15_part_of_cause_result"]]
    unknown = len(comparisons) - len(known)
    print("\nCausal participation: HP15 cause or part of a cause versus FDM")
    print("HP15 participation = primitive True OR conjunction True (among tested causes).")
    if unknown:
        print(f"Participation unavailable for {unknown} queries; excluded from this comparison.")
    if not known:
        print("No queries with sufficient evidence to compare causal participation.")
        return

    counts = Counter((row["hp15_part_of_cause_result"], row["fdm_result"]) for row in known)
    disagreements = [row for row in known if row["hp15_part_of_cause_result"] != row["fdm_result"]]
    agreement = len(known) - len(disagreements)
    print(
        f"Causal-participation agreement: {agreement}/{len(known)} "
        f"({agreement / len(known):.1%}); disagreements: {len(disagreements)}."
    )
    print_table(("HP15 cause or part", "FDM", "Queries"), [
        (hp, fdm, counts[hp, fdm])
        for hp, fdm in (("True", "True"), ("False", "False"), ("False", "True"), ("True", "False"))
    ])
    original = [row for row in comparisons if row["hp15_result"] != row["fdm_result"]]
    resolved = sum(row["hp15_part_of_cause_result"] == row["fdm_result"] for row in original)
    print(f"Resolved original primitive disagreements: {resolved}/{len(original)}.")
    if resolved:
        print("In these cases, HP15 recognises the input as part of a conjunctive cause.")

    print("\nRemaining causal-participation disagreements:")
    if not disagreements:
        print("None.")
        return
    sensitive_ids = {
        row["query_id"]
        for canonical, alternative in analysis["representation_pairs"]["FDM"]
        if canonical["hp15_result"] != alternative["hp15_result"]
        for row in (canonical, alternative)
    }
    sensitive = sum(row["query_id"] in sensitive_ids for row in disagreements)
    print(f"{sensitive}/{len(disagreements)} involve FDM verdicts that change between equivalent equations.")
    print_table(("Query ID", "Cause", "Effect", "HP15 primitive", "HP15 conjunction", "HP15 cause or part", "FDM"), [
        (row["query_id"], row["cause"], row["effect"], row["hp15_result"],
         row["hp15_conjunction_result"] or "unavailable", row["hp15_part_of_cause_result"], row["fdm_result"])
        for row in disagreements
    ])


def print_report(analysis: dict) -> None:
    comparisons = analysis["comparisons"]
    counts = Counter((row["hp15_result"], row["fdm_result"]) for row in comparisons)
    disagreements = [row for row in comparisons if row["hp15_result"] != row["fdm_result"]]
    total = len(comparisons)
    agreement = total - len(disagreements)
    print("HP15 / FDM comparison of saved results")
    print(
        f"{len(analysis['hp15_rows'])} HP15 rows; {len(analysis['fdm_rows'])} FDM rows. "
        f"Matched {total} primitive queries across "
        f"{len({row['logical_model_id'] for row in comparisons})} Boolean functions "
        f"and {len({row['model_id'] for row in comparisons})} equation representations."
    )
    print(f"Agreement: {agreement}/{total} ({agreement / total:.1%}); disagreements: {len(disagreements)}.")
    print()
    print_table(("HP15", "FDM", "Queries"), [
        (hp, fdm, counts[hp, fdm])
        for hp, fdm in (("True", "True"), ("False", "False"), ("False", "True"), ("True", "False"))
    ])
    for theory, column in (("HP15", "hp15_result"), ("FDM", "fdm_result")):
        positive = sum(row[column] == "True" for row in comparisons)
        print(f"{theory} primitive causes: {positive}/{total} ({positive / total:.1%}).")

    print("\nComparison by representation:")
    representation_rows = []
    for representation in sorted({row["representation"] for row in comparisons}):
        rows = [row for row in comparisons if row["representation"] == representation]
        matches = sum(row["hp15_result"] == row["fdm_result"] for row in rows)
        representation_rows.append((representation, len(rows), matches, f"{matches / len(rows):.1%}"))
    print_table(("Representation", "Queries", "Agree", "Agreement"), representation_rows)

    conjunctions = [row for row in analysis["hp15_rows"] if row["cause_type"] == "conjunction"]
    accepted = sum(row["hp15_result"] == "True" for row in conjunctions)
    print(f"\nHP15 conjunctions: {accepted}/{len(conjunctions)} accepted; FDM does not evaluate conjunctions.")
    supported = sum(row["hp15_conjunction_result"] == "True" for row in disagreements)
    unavailable = sum(not row["hp15_conjunction_result"] for row in disagreements)
    print(f"Disagreements with an HP15-accepted conjunction: {supported}/{len(disagreements)}.")
    if unavailable:
        print(f"Conjunction results unavailable for {unavailable} disagreements.")

    print_participation_report(analysis)

    print("\nChanges between canonical and alternative equations:")
    sensitivity_rows = []
    for theory, pairs in analysis["representation_pairs"].items():
        for cause_type in ("primitive", "conjunction"):
            selected = [(c, a) for c, a in pairs if c["cause_type"] == cause_type]
            if selected:
                changed = sum(c["hp15_result"] != a["hp15_result"] for c, a in selected)
                sensitivity_rows.append((theory, cause_type, len(selected), changed))
    print_table(("Theory", "Query type", "Pairs", "Changed"), sensitivity_rows)

    print("\nPrimitive disagreements:")
    if disagreements:
        print_table(("Query ID", "Equation", "Effect", "HP15", "FDM", "HP15 conjunction"), [
            (row["query_id"], row["equation"], row["effect"], row["hp15_result"],
             row["fdm_result"], row["hp15_conjunction_result"] or "unavailable")
            for row in disagreements
        ])
    else:
        print("None.")

    for theory, pairs in analysis["representation_pairs"].items():
        changed = [(c, a) for c, a in pairs if c["hp15_result"] != a["hp15_result"]]
        if changed:
            print(f"\n{theory} representation disagreements:")
            print_table(("Canonical query", "Alternative query", "Cause", "Canonical", "Alternative"), [
                (c["query_id"], a["query_id"], a["cause"], c["hp15_result"], a["hp15_result"])
                for c, a in changed
            ])
    print("\nResults describe the saved runs; FDM defaults in the evaluator are opposite to actual values.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hp15", type=Path, default=PROJECT_ROOT / "results/hp15_results.csv")
    parser.add_argument("--fdm", type=Path, default=PROJECT_ROOT / "results/fdm_results.csv")
    parser.add_argument("--disagreements-csv", type=Path, help="Also export primitive disagreements")
    parser.add_argument(
        "--participation-disagreements-csv", type=Path,
        help="Also export disagreements after counting HP15 membership in a cause",
    )
    args = parser.parse_args()
    try:
        analysis = compare_results(args.hp15, args.fdm)
    except (OSError, ValueError, csv.Error) as error:
        parser.error(str(error))
    print_report(analysis)
    for output, column, label in (
        (args.disagreements_csv, "hp15_result", "primitive"),
        (args.participation_disagreements_csv, "hp15_part_of_cause_result", "causal-participation"),
    ):
        if output is None:
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        rows = analysis["comparisons"]
        with output.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(row for row in rows if row[column] and row[column] != row["fdm_result"])
        print(f"\nWrote {label} disagreements to {output}")


if __name__ == "__main__":
    main()
