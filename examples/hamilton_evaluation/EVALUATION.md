# Hamilton DAG Orchestration Evaluation

**Date:** February 2026  
**Evaluator:** GitHub Copilot  
**Context:** Issue #[number] - Explore Hamilton for analysis layer DAG orchestration

## Executive Summary

Hamilton is a **lightweight, function-level DAG orchestration library** that could complement the butterfly-planner's architecture. After building three working prototypes, the evaluation finds:

- ✅ **Prefect Compatibility**: Hamilton and Prefect compose perfectly at different abstraction levels
- ✅ **Store Integration**: Hamilton and store.py are complementary, not redundant
- ⚠️ **Current Scale**: For the current 3-5 analysis modules, Hamilton provides marginal benefit
- ✅ **Future Value**: If the project scales to 10+ analysis modules or adds complex multi-datasource pipelines, Hamilton prevents dependency spaghetti

**Recommendation**: **DEFER** Hamilton adoption until the analysis layer grows to 8-10+ functions with complex cross-dependencies. The current architecture is clean enough without it.

---

## Evaluation Criteria

### 1. Fit with Prefect

**Finding: ✅ Perfect Composition - No Overlap**

Prefect and Hamilton operate at different levels of abstraction:

| Layer | Tool | Responsibility |
|-------|------|---------------|
| **Macro** | Prefect | Flow scheduling, task retries, cross-task coordination, observability |
| **Micro** | Hamilton | Function-level DAG, automatic dependency wiring, data transformations |
| **Storage** | store.py | Data persistence, freshness checks, TTL management |

**Architecture:**
```
Prefect Flow
  ├─ Task 1: Load data from store
  ├─ Task 2: Load more data
  ├─ Task 3: Run Hamilton analysis ← Hamilton DAG executes here
  │   └─ Hamilton Driver
  │       ├─ Function A
  │       ├─ Function B (depends on A)
  │       └─ Function C (depends on A, B)
  └─ Task 4: Save results to store
```

**Proof:** See `examples/hamilton_evaluation/prototype_prefect_hamilton.py` - demonstrates seamless integration where:
- Prefect orchestrates: load → analyze → save
- Hamilton orchestrates: data → transform → enrich → summarize

**Verdict:** They compose perfectly. No conflict.

---

### 2. Analysis Layer Simplification

**Finding: ✅ Simplifies Complex Pipelines, ⚠️ Adds Overhead for Simple Ones**

**Benefits:**
1. **Automatic dependency resolution** - No manual ordering of analysis functions
2. **Type safety** - Function signatures declare inputs/outputs
3. **Testability** - Pure functions are easy to unit test
4. **Visibility** - Can visualize the data flow graph
5. **Reusability** - Functions can be composed into different execution paths

**Example:** Current `correlate_observations_with_gdd` in `analysis/species_gdd.py`:
```python
# Current: Manual dependency management in build.py
observations = load_inaturalist()
gdd_data = load_gdd()
profiles = correlate_observations_with_gdd(observations, gdd_data)
```

**With Hamilton:**
```python
# Functions declare dependencies via parameters
def species_gdd_profiles(observations_raw, gdd_year_data):
    # Same logic, but Hamilton auto-wires it
    ...

# Driver figures out execution order
results = driver.execute(final_vars=["species_gdd_profiles"])
```

**Current Analysis Functions:**
- `analysis/species_gdd.py`: `correlate_observations_with_gdd` (1 function)
- `analysis/species_weather.py`: `enrich_observations_with_weather` (1 function)
- `analysis/weekly_forecast.py`: `merge_sunshine_weather` (1 function)

**Dependency Complexity:** LOW
- Most functions are 1:1 or 2:1 (take 1-2 inputs, produce 1 output)
- No deep chains or complex fanout/fanin patterns
- Current manual ordering in `flows/build.py` is clear and maintainable

**Verdict:** Hamilton simplifies complex pipelines but adds overhead for the current simple structure.

---

### 3. Caching Overlap with store.py

**Finding: ✅ Complementary, Not Redundant**

Hamilton and store.py serve **different caching purposes**:

| Layer | Tool | What it Caches | Invalidation | Use Case |
|-------|------|----------------|--------------|----------|
| **Persistence** | store.py | Raw fetched data, derived data | TTL-based (hours/days) | "Cache API responses for 6 hours" |
| **Execution** | Hamilton (optional) | Intermediate function results | Run-based (within pipeline) | "Don't recompute this transformation if inputs unchanged" |

**Example:**
```python
# store.py: "Keep fetched weather data for 6 hours"
weather = store.read("live/weather.json")
if weather is None or store.is_stale("live/weather.json"):
    weather = fetch_weather()
    store.write("live/weather.json", weather, ttl_hours=6)

# Hamilton: "Within this run, don't recompute weather_by_date if it's already done"
# (Only useful if multiple downstream functions need it in the same execution)
```

**Current Pipeline:**
```
fetch.py → store.py (persist) → build.py → analysis functions → store.py (save)
```

Each analysis function runs once per build. There's no need for in-execution caching because:
1. Functions execute once per flow run
2. No branching logic that might skip/reuse computations
3. store.py already handles cross-run persistence

**Verdict:** Hamilton's caching would be redundant for the current linear pipeline. store.py is sufficient.

---

### 4. Learning Curve vs. Benefit

**Finding: ⚠️ Moderate Learning Curve, LOW Immediate Benefit**

#### Learning Curve (Estimated Time)

| Skill | Time to Learn | Current Team Need |
|-------|---------------|-------------------|
| Hamilton basics | 2-4 hours | ✅ Completed in prototypes |
| Function design patterns | 4-8 hours | Medium - requires restructuring |
| Debugging DAG errors | 2-4 hours | Low - errors are usually clear |
| Advanced features (config, parameterization) | 4-8 hours | Not needed yet |
| **Total for basic adoption** | **8-16 hours** | - |

#### Benefit Assessment (Current State)

**Scale:** 3-5 analysis modules with simple dependencies

| Benefit | Current Value | Future Value (10+ modules) |
|---------|---------------|---------------------------|
| Auto dependency wiring | 🟡 Low - manual is easy | 🟢 High - prevents mistakes |
| Type safety | 🟢 Medium - already using type hints | 🟢 High - enforced at runtime |
| Testability | 🟢 Medium - functions already testable | 🟢 High - easier mocking |
| Visualization | 🟡 Low - can mentally model 5 functions | 🟢 High - essential for 10+ |
| Reusability | 🟡 Low - each function used once | 🟢 High - compose different views |

**ROI Calculation:**
- **Cost:** 8-16 hours to adopt + ongoing maintenance
- **Benefit:** Prevents ~2-4 hours of debugging per year (dependency ordering bugs)
- **Break-even:** 4-8 years at current scale
- **BUT:** If scaling to 10+ analysis modules, break-even is ~6 months

**Verdict:** At current scale (3-5 functions), **ROI is poor**. At 10+ functions, **ROI is excellent**.

---

## Prototypes Built

### 1. Basic DAG (`prototype_basic_dag.py`)

**Demonstrates:**
- Converting existing analysis functions to Hamilton DAG nodes
- Automatic dependency resolution from function signatures
- Execution with mock data

**Key Code:**
```python
def observations_with_weather(
    observations_raw: list[dict],
    weather_by_date: dict,
) -> list[dict]:
    # Hamilton sees: depends on observations_raw AND weather_by_date
    ...

driver.execute(final_vars=["observations_with_weather"])
# Hamilton auto-wires: observations_raw → weather_by_date → observations_with_weather
```

**Run:** `python examples/hamilton_evaluation/prototype_basic_dag.py`

### 2. Store Integration (`prototype_with_store.py`)

**Demonstrates:**
- Hamilton loading from store.py
- Hamilton saving back to store.py
- Complementary roles (Hamilton = transforms, store = persistence)

**Run:** `python examples/hamilton_evaluation/prototype_with_store.py`

### 3. Prefect + Hamilton (`prototype_prefect_hamilton.py`)

**Demonstrates:**
- Prefect flow with Hamilton task
- Macro vs micro orchestration
- No overlap in responsibilities

**Run:** `python examples/hamilton_evaluation/prototype_prefect_hamilton.py`

---

## Recommendations

### Recommendation 1: **DEFER** Hamilton Adoption (Current State)

**Rationale:**
- Current analysis layer has 3-5 simple functions
- Manual dependency ordering in `flows/build.py` is clear and maintainable
- Learning curve (8-16 hours) doesn't justify ROI at this scale
- No complex DAG patterns that benefit from auto-wiring

**Action:** Keep the prototypes as reference. Don't integrate into production yet.

### Recommendation 2: **REVISIT** at Scale Threshold

**Trigger conditions for re-evaluation:**
1. Analysis layer grows to **8-10+ functions**
2. Complex multi-datasource joins with **fanout/fanin patterns** emerge
3. Functions start being **reused in multiple contexts** (e.g., different views)
4. Debugging dependency order becomes a **time sink**

**If any of these occur, Hamilton should be adopted.**

### Recommendation 3: **Document the DAG Pattern** (Now)

Even without Hamilton, document the analysis layer as a DAG in:
- `src/butterfly_planner/analysis/README.md`
- Show: `datasources → analysis → renderers`
- Make dependency flow explicit for future maintainers

This documentation will make Hamilton adoption easier later if needed.

### Recommendation 4: **Keep Functions Pure** (Now)

Current analysis functions are already well-designed:
- Pure transformations (input → output)
- Type-annotated
- No side effects
- Testable

**Continue this pattern.** It makes future Hamilton adoption trivial because the functions are already Hamilton-compatible.

---

## Decision Matrix

| Project State | Analysis Functions | Recommendation |
|---------------|-------------------|----------------|
| **Now** | 3-5 simple functions | ❌ Don't adopt Hamilton |
| **Near Future** | 6-8 functions, some complexity | 🟡 Monitor complexity |
| **Growth** | 10+ functions, complex deps | ✅ Adopt Hamilton |
| **Mature** | 15+ functions, multiple views | ✅✅ Hamilton essential |

---

## References

- Hamilton GitHub: https://github.com/dagworks-inc/hamilton
- Hamilton Docs: https://hamilton.dagworks.io/
- Prototype code: `examples/hamilton_evaluation/`
- PLAN-app-refactor.md: Analysis layer section

---

## Appendix: Hamilton DAG Visualization

```
Source Nodes (Data Loaders):
  observations_raw
  weather_data_raw
  gdd_year_data

Transformation Nodes:
  weather_by_date ← weather_data_raw
  observations_with_weather ← observations_raw, weather_by_date
  species_gdd_profiles ← observations_raw, gdd_year_data

Final Outputs:
  observations_with_weather
  species_gdd_profiles
```

See `examples/hamilton_evaluation/visualize_dag.py` for full visualization.

---

## Questions for Stakeholders

1. **Timeline:** How soon do you expect the analysis layer to grow to 10+ functions?
2. **Complexity:** Are there plans for complex multi-datasource composite indexes (e.g., viewing score = f(GDD, weather, bloom, species))?
3. **Team:** Will other developers need to understand the analysis pipeline?
4. **Maintenance:** How important is reducing cognitive load for future maintainers?

If the answer to any of these suggests **imminent growth**, consider adopting Hamilton sooner.
