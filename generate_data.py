import csv
from itertools import product
from pathlib import Path
from sympy import symbols, And, Or, Not, simplify_logic

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

A, B, C = symbols("A B C")
exogenous = [A, B]

# One minterm per input combination (A, B) = 00, 01, 10, 11
minterms = [
    And(*(v if bit else Not(v) for v, bit in zip(exogenous, bits)))
    for bits in product([0, 1], repeat=len(exogenous))
]

# One SEM per subset of minterms: A, B exogenous, C := canonical DNF
with (DATA_DIR / "sem_models.csv").open("w", newline="") as f_canon, \
     (DATA_DIR / "sem_models_simplified.csv").open("w", newline="") as f_simp:
    canon_writer = csv.writer(f_canon)
    simp_writer = csv.writer(f_simp)
    canon_writer.writerow(["id", "representation", "truth_table", "C"])
    simp_writer.writerow(["id", "representation", "truth_table", "C"])

    for k in range(2 ** len(minterms)):
        dnf = Or(*(m for i, m in enumerate(minterms) if (k >> i) & 1))
        simplified = simplify_logic(dnf, form="dnf")
        truth_table = " ".join(str((k >> i) & 1) for i in range(len(minterms)))

        canon_writer.writerow([k + 1, "canonical", truth_table, dnf])
        if simplified != dnf:
            simp_writer.writerow([k + 1, "alternative_1", truth_table, simplified])

# Combine canonical and simplified models into one CSV
with (DATA_DIR / "sem_models_combined.csv").open("w", newline="") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(["id", "representation", "truth_table", "C"])
    for path in ["sem_models.csv", "sem_models_simplified.csv"]:
        with (DATA_DIR / path).open(newline="") as f_in:
            reader = csv.reader(f_in)
            next(reader)  # skip header
            writer.writerows(reader)
