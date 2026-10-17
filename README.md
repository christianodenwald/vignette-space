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

FDM additionally requires SBCL and the Moonli/Quicklisp environment loaded by
`.lisp/setup.lisp`.

```bash
python evaluate_sem_models_fdm.py
python sanity_check_hp15_results.py results/fdm_results.csv
```

The current FDM results contain eight disagreements between logically equivalent
representations; its sanity check reports them and exits with status 1.

## Data and results

Generated model CSVs in `data/` contain `id`, `representation`, `truth_table`,
and `C`. Regenerate older files to add explicit representation labels.
Both evaluators accept an input CSV and `-o OUTPUT`.

Outputs are `results/hp15_results.csv` and `results/fdm_results.csv`.
Both include stable `query_id` values, verdicts in `hp15_result` (also for FDM),
witnesses, and diagnostics. Matching primitive queries share IDs across theories.

## Tests

```bash
python -m unittest test_sem_evaluation test_evaluate_sem_models_hp15 test_evaluate_sem_models_fdm
sbcl --script test_fdm_regressions.lisp
```
