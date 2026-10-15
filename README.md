# Vignette Space

This project generates Boolean structural equation models (SEMs) over variables A, B, and C, then evaluates whether the induced causal queries satisfy the Halpern–Pearl 2015 definition of actual causation.

The repository is built around a synthetic model-generation workflow and the bundled `causality_checker` implementation for causal evaluation.

## Overview

The pipeline is:

1. Generate all candidate Boolean models for `C` as a function of `A` and `B`.
2. Write the models to CSV files.
3. Evaluate each model under multiple contexts using the HP15 checker.
4. Save the results to a CSV for downstream analysis.
5. Sanity-check that equivalent model representations agree.

This makes it easy to test whether different but logically equivalent formulations of the same causal structure produce the same actual-causation verdicts.

## Files

- `generate_data.py` — enumerates all binary SEM formulas and writes the generated model CSVs.
- `evaluate_sem_models_hp15.py` — evaluates each generated model and context against the HP15 causal theory.
- `sanity_check_results.py` — checks that canonical and alternative representations agree on the same causal query outcomes.
- `causality_checker/` — bundled causal-evaluation toolkit used to compute actual-causality results.
- `sem_models.csv` — canonical Boolean models.
- `sem_models_simplified.csv` — simplified logical forms where simplification changes the expression.
- `sem_models_combined.csv` — combined canonical + simplified model table used for evaluation.
- `sem_models_hp15_results.csv` — evaluation output produced by HP15 checks.

## Generated model structure

Each generated SEM has the form:

- exogenous variables: `A`, `B`
- target variable: `C`
- `C` is generated as a Boolean formula over `A` and `B`
- all binary inputs are tested for `(A, B) in {(0, 0), (0, 1), (1, 0), (1, 1)}`

The generator creates a complete set of candidate formulas and stores:

- `id`: model identifier
- `truth_table`: the truth-table encoding for the model
- `C`: the symbolic Boolean expression for `C`

## Quick start

### 1. install dependencies

```bash
python -m pip install sympy numpy pandas
```

If you want to use the full `causality_checker` environment described in its own README, you may also install the optional dependencies used there:

```bash
python -m pip install ollama
```

and, for OpenAI-backed evaluation, install:

```bash
python -m pip install openai
```

### 2. generate the SEM CSVs

```bash
python generate_data.py
```

This creates the model tables in the project root.

### 3. evaluate the generated models with HP15

```bash
python evaluate_sem_models_hp15.py
```

This evaluates every model-context-query pair and writes:

```bash
sem_models_hp15_results.csv
```

You can also give a custom input file and output path:

```bash
python evaluate_sem_models_hp15.py sem_models_combined.csv -o sem_models_hp15_results.csv
```

### 4. run the sanity check

```bash
python sanity_check_results.py
```

This ensures that logically equivalent model representations agree on the HP15 verdict for the same query.

## How the evaluation works

The evaluator constructs a `Vignette` for each `(model, A, B)` configuration and then issues queries of the form:

- `A=a is a cause of C=c`
- `B=b is a cause of C=c`
- `A=a and B=b is a conjunctive cause of C=c`

It calls the bundled causal checker with:

```python
check_causality(
    theory="HP2015",
    vignette=vignette,
    query=query,
    gt="HP15",
)
```

The result is recorded in the output CSV under the `hp15_result` column, along with witness and diagnostic metadata.

## Output interpretation

The `sem_models_hp15_results.csv` file includes columns such as:

- `model_id`
- `logical_model_id`
- `representation`
- `truth_table`
- `equation`
- `A`, `B`, `C`
- `cause`
- `effect`
- `hp15_result`
- `witness`
- `details`

This allows you to compare causal results across equivalent model formulations and inspect the exact witness or explanatory details returned by the causal checker.

## Notes

- The study is focused on binary variables and symbolic Boolean models.
- Equivalent forms of the same logical rule are intentionally compared to ensure that the causal evaluation is representation-invariant.
- The repository includes a bundled causal-evaluation submodule, so no external service is required for the core local analysis workflow.

## Related project

The root project is designed to work with the bundled `causality_checker` repository, which implements actual-causation definitions and evaluation utilities for HP2005/HP2015-style reasoning.
