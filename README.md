# Vignette Space

Compare HP15 and factual difference making (FDM) on all 16 Boolean functions
`C = f(A, B)`, using canonical and simplified equations in all four contexts.
HP15 checks primitive and conjunctive causes; FDM checks primitive causes only.

## Pipeline

1. **Generate models.** `generate_data.py` enumerates the 16 truth tables,
   builds canonical Boolean equations and simplified alternatives, and writes
   them to CSVs in `data/`.
2. **Build queries.** `sem_evaluation.py` evaluates each equation in all four
   `(A, B)` contexts and constructs queries using the actual cause and effect values.
3. **Evaluate causation.** HP15 runs through the Python `causality_checker`;
   FDM sends primitive queries through `run_fdm_evaluation.lisp` to Moonli.
4. **Save results.** Each evaluator writes verdicts, witnesses, and diagnostics
   to its CSV in `results/`, with stable IDs identifying the queries.
5. **Compare representations.** `sanity_check_hp15_results.py` reports verdict
   disagreements between canonical and alternative equations for the same
   logical model, context, and query.

## Run

Requires Python and local checkouts at `causality_checker/` and, for FDM,
`factual_difference_making/`.

```bash
python -m pip install sympy numpy pandas
python generate_data.py
python evaluate_sem_models_hp15.py
python sanity_check_hp15_results.py
```

`generate_data2.py` enumerates singleton and miniterm clauses, including the
true-valued term `T`, and writes all 512 combinations to
`data/sem_models2.csv` using the original `id`, `representation`, `truth_table`,
and `C` columns. It uses `data/sem_models.csv` to mark exactly one matching
formula per truth table as `canonical`; the remaining formulas are
`alternative_1`. It refuses to replace an existing output CSV.

FDM additionally requires SBCL and the Moonli/Quicklisp environment loaded by
`.lisp/setup.lisp`.

```bash
python evaluate_sem_models_fdm.py
python sanity_check_hp15_results.py results/fdm_results.csv
```

The current FDM results contain eight disagreements between logically equivalent
representations; its sanity check reports them and exits with status 1.

Compare the saved HP15 and FDM results using only the Python standard library:

```bash
python compare_sem_results.py
python compare_sem_results.py --disagreements-csv results/hp15_fdm_disagreements.csv
python compare_sem_results.py --participation-disagreements-csv results/hp15_fdm_participation_disagreements.csv
```

The report matches primitive queries by ID, checks that their metadata and
coverage agree, and shows verdict counts, individual disagreements, representation
sensitivity, and the corresponding HP15 conjunction verdicts. It also compares
FDM against HP15 causal participation: a literal is a cause or part of a cause
when its primitive verdict or the conjunction verdict is true. Missing
conjunction evidence leaves participation unknown when the primitive is false;
these queries are excluded from the participation comparison.

In the current results, all 16 primitive disagreements resolve under this
interpretation. Participation agreement is 192/200 (96%), with eight remaining
disagreements involving canonical equations whose FDM verdicts change after
simplification. Use `--hp15 PATH` and `--fdm PATH` to compare other result files.
Differences between theories are reported normally; malformed or unmatched
inputs produce an error.

## Data and results

Generated model CSVs in `data/` contain `id`, `representation`, `truth_table`,
and `C`. Regenerate older files to add explicit representation labels.
Both evaluators accept an input CSV and `-o OUTPUT`.

Outputs are `results/hp15_results.csv` and `results/fdm_results.csv`.
Both include stable `query_id` values, verdicts in `hp15_result` (also for FDM),
witnesses, and diagnostics. Matching primitive queries share IDs across theories.

## Tests

```bash
python -m unittest test_sem_evaluation test_evaluate_sem_models_hp15 test_evaluate_sem_models_fdm test_compare_sem_results
sbcl --script test_fdm_regressions.lisp
```
