# Hamilton Evaluation for Analysis Layer

This directory contains prototypes and evaluation materials for using [Hamilton](https://github.com/dagworks-inc/hamilton) as a DAG orchestration tool for the butterfly-planner analysis layer.

## What is Hamilton?

Hamilton is a lightweight Python library that models data transformations as a DAG of functions. Each function declares its inputs as parameters, and Hamilton automatically wires the dependency graph. This maps directly to our planned pipeline:

```
datasources/ → analysis/ → renderers/ → site/
```

## Prototypes

### 1. Basic Analysis DAG (`prototype_basic_dag.py`)
Demonstrates Hamilton's function-level DAG with simple analysis functions:
- GDD correlation with observations
- Weather enrichment of observations
- Sunshine/weather merging

### 2. Integration with Store (`prototype_with_store.py`)
Shows how Hamilton can integrate with our existing `store.py` caching layer.

### 3. Prefect + Hamilton (`prototype_prefect_hamilton.py`)
Explores the composition of Prefect (macro-orchestration) with Hamilton (micro-orchestration).

## Running the Examples

```bash
# Run basic DAG prototype
python examples/hamilton_evaluation/prototype_basic_dag.py

# Run with store integration
python examples/hamilton_evaluation/prototype_with_store.py

# Run Prefect + Hamilton integration
python examples/hamilton_evaluation/prototype_prefect_hamilton.py
```

## Evaluation Criteria

1. **Fit with Prefect**: Do they compose well, or overlap?
2. **Analysis layer simplification**: Does the DAG model simplify or complicate things?
3. **Caching overlap with store.py**: Complementary or redundant?
4. **Learning curve vs. benefit**: Is it worth it for 3-5 analysis modules?

## Findings

See `EVALUATION.md` for detailed findings and recommendations.
