# Custom Gates Examples

Advanced quality gate patterns — dynamic thresholds, composite scoring, and metric history tracking.

## Files

- `dynamic_thresholds.py` — Adjust gate thresholds based on git change size
- `composite_gates.py` — Weighted composite score from multiple metrics
- `metric_history.py` — Track metrics over time and detect regressions
- `pyqual.yaml` — Pipeline config for custom gates

## dynamic_thresholds.py

Adjusts coverage thresholds based on the number of changed Python files:
- **Large changes** (>10 files): lower threshold (60%)
- **Small changes** (≤10 files): higher threshold (80%)

```bash
python dynamic_thresholds.py
```

## composite_gates.py

Combines coverage, complexity, lint errors, and security issues into a single weighted score (0–100). Gates pass only if both individual gates AND the composite score meet thresholds.

```bash
python composite_gates.py
```

**Weights:**
| Component | Weight | Source |
|-----------|--------|--------|
| Coverage | 35% | pytest-cov |
| Complexity | 25% | code2llm |
| Lint errors | 20% | ruff |
| Security | 20% | bandit |

## metric_history.py

Stores metric snapshots in `.pyqual/metric_history.json` and detects regressions between runs. Fails if any metric regresses beyond a configurable tolerance.

```bash
python metric_history.py
```

**Features:**
- Timestamped metric snapshots
- Per-metric trend analysis (improving / degrading / stable)
- Configurable regression tolerance (default: 2%)
- Distinguishes "higher is better" vs "lower is better" metrics

## Usage

```bash
cd examples/custom_gates

# Run individual examples
python dynamic_thresholds.py
python composite_gates.py
python metric_history.py

# Run the pipeline
pyqual run -c pyqual.yaml
```

## Key Concepts

- **`GateConfig`** — defines a single metric + operator + threshold
- **`GateSet`** — collection of gates with metric collection from `.pyqual/` artifacts
- **`Gate.check(metrics)`** — evaluates one gate against collected metrics
- **`gate_set.check_all(workdir)`** — collects metrics and checks all gates
- **`gate_set._collect_metrics(workdir)`** — gathers metrics from all sources

## pyqual.yaml

See [pyqual.yaml](pyqual.yaml) for the example pipeline configuration.
