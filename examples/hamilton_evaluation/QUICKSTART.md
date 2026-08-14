# Hamilton Evaluation: Quick Start Guide

This directory contains a complete evaluation of Hamilton for the butterfly-planner analysis layer.

## What's Here

### Documentation
- **EVALUATION.md** - Comprehensive evaluation with findings and recommendations (START HERE)
- **README.md** - Overview of prototypes and how to run them

### Prototypes
1. **prototype_basic_dag.py** - Basic Hamilton DAG with analysis functions
2. **prototype_with_store.py** - Integration with store.py
3. **prototype_prefect_hamilton.py** - Integration with Prefect flows
4. **visualize_dag.py** - DAG visualization tool

## Quick Summary

**TL;DR:** Hamilton is excellent but **overkill at current scale (3-5 analysis functions)**. Revisit when the analysis layer grows to **8-10+ functions** with complex dependencies.

## Recommendation

✅ **DEFER** adoption until analysis layer grows
✅ **KEEP** the prototypes as reference
✅ **DOCUMENT** the current DAG pattern in `src/butterfly_planner/analysis/`
✅ **MAINTAIN** pure function design (makes future Hamilton adoption easy)

## Run the Prototypes

```bash
# Basic DAG demonstration
python examples/hamilton_evaluation/prototype_basic_dag.py

# Store.py integration
python examples/hamilton_evaluation/prototype_with_store.py

# Prefect + Hamilton composition
python examples/hamilton_evaluation/prototype_prefect_hamilton.py

# DAG visualization
python examples/hamilton_evaluation/visualize_dag.py
```

## Key Findings

### ✅ Prefect Compatibility
Hamilton and Prefect compose perfectly:
- **Prefect** = macro-orchestration (scheduling, retries, flow coordination)
- **Hamilton** = micro-orchestration (function-level DAG, auto-wiring)
- **No overlap**, different abstraction levels

### ✅ Store.py Integration
Hamilton and store.py are complementary:
- **store.py** = persistence, TTL, freshness checks
- **Hamilton** = transformation orchestration
- **Both needed** for complete pipeline

### ⚠️ Scale Threshold
Current state: **3-5 analysis functions** → Hamilton adds overhead
Future state: **10+ analysis functions** → Hamilton essential

### 📊 ROI Analysis
- **Cost:** 8-16 hours to adopt + maintenance
- **Benefit at current scale:** ~2-4 hours/year saved
- **Break-even:** 4-8 years (current scale) vs 6 months (10+ functions)

## When to Revisit

Trigger conditions:
1. Analysis layer grows to **8-10+ functions**
2. Complex **fanout/fanin patterns** emerge
3. Functions are **reused in multiple contexts**
4. Debugging dependency order becomes **time-consuming**

## For Future Reference

The current analysis functions are already Hamilton-compatible because they:
- Are pure transformations
- Use type annotations
- Have no side effects
- Declare dependencies via parameters

Future adoption would be straightforward.

## Questions?

See **EVALUATION.md** for detailed analysis, decision matrices, and architectural diagrams.

---

**Issue:** #[number] - Explore Hamilton for analysis layer DAG orchestration  
**Date:** February 2026  
**Status:** ✅ Evaluation Complete - DEFER recommendation
