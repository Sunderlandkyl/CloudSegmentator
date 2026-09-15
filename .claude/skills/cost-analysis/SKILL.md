---
name: cost-analysis
description: Measure what a Terra submission actually cost and predict runs before launching them (submission_cost → cost_model fit/predict/batch/evaluate). Use for "what did that run cost", "predict the full run", "is this batch size right".
---

# Cost measurement and prediction

Full runbook: `util/executionAnalytics/README.md`. This skill is the
operational gotchas layered on top.

## Measuring a finished submission

```
cd util/executionAnalytics
python submission_cost.py <submission-url-or-id> [--workspace ns/name]
```
Writes `submission_<id>_{workflows,series,cost,billing}.csv` (per-task VM
lifecycles from Cromwell metadata + per-series timings + billing join).

- **Never trust Terra's cost field for analysis** — `costType=Estimated` has
  been 3× off under churn (and exact on calm days; you can't tell which).
- **Billing settles 24–48 h after the run.** Measuring earlier silently yields
  lower-bound $ (partial export). Re-measure after ~2 days.
- Preemption tax is visible as `runtimeMin` vs `doneRuntimeMin` / `attempts`.

## The model

Per WDL task: `time = a + b·nSeries + c·Mvox`, `$` fitted directly on billing.
`Mvox` comes from idc-index **before** a run, so manifests are priceable
pre-submission. `cost_model.py fit | predict | batch | evaluate | report`.

- **Pilot design matters**: nSeries and Mvox must vary independently
  (`make_terra_manifest.py pilot` stratifies deliberately) or b and c are
  confounded — uniform batches make c unidentifiable.
- **Model staleness**: a fit is only valid for the config it measured
  (image digests, tasks, params, region — recorded in the model JSON;
  `evaluate` warns on drift). The pilot2 TotalSeg fit under-predicted by 29 %
  after the v2.18 upgrade + lung_vessels addition. Refit after engine upgrades.
- **Preemption is a scenario, not a prediction**: spot preemption rates aren't
  in any catalog. `batch` shows calm vs churn curves; measured reality spans
  ~$0.02 (calm) to ~$0.045 (churn) per series through both engines at n≈20.
- **Batch size**: $/series falls monotonically with n (fixed ~15–20 min/VM
  overhead amortizes); the practical knee is n≈20 (MOOSE) / 20–30 (TotalSeg).
  Above that, on-demand-fallback probability and wall clock grow for cents of
  saving. `--batch-target 900000000` voxels ≈ 20 series.
- Region rates: `region_prices.py` → `region_rates.json`; us-west4 is the
  cheapest US region (~11 % under us-east4). Billed spot rates have run
  0.74–0.82× catalog.
- Reference scale: whole eligible CMB+CPTAC CT cohort (~4,341 series =
  regularly-spaced 3D, ≥20 slices — 55 % of raw CT; another ~1,575 real
  volumes are excluded only for non-uniform slice spacing) ≈ $85–195 both
  engines.

## Run metrics inside the workflow

Each notebook writes per-series/phase CSVs (`*_UsageMetrics.csv`, concatenated
into `combined_UsageMetrics.csv`) and ends with a "Run metrics summary" cell:
phase timings, peak RAM (MemSampler), and — via the checkpoint attempt ledger —
every **preempted predecessor attempt** (runtime, units done, last phase, peak
RAM). nb3's `run_summary.json` carries the same. Extra CSV columns are
append-only, so `submission_cost.py`/`cost_model.py` parsing stays compatible.
