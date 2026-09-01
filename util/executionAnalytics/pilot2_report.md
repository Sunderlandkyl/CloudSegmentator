# pilot2 cost/time report — harmonized Segmentator, 2026-08-31

Fresh 30-series designed pilot on the post-fix `harmonized_models` code (commit `bb537b2`:
radiomics engine fixes, 5-Mvox ROI guard, `juliaThreads=1`), run to (1) re-measure cost/time
with current code and (2) test whether **a-priori dataset size** (the load-balancing metric
`Mvox = slices × rows × cols / 1e6`, known from idc-index before any run) predicts cost/time.

| | MOOSE | TotalSegmentator |
|---|---|---|
| Submission | `71a2f34a-768b-4a10-bc7f-25f0ede7660c` | `02b36d47-a0bd-4025-98cb-dd9c08b0ab29` |
| Result | 8/9 succeeded (entity 9 failed, see below) | 9/9 succeeded |
| Billed (2026-09-01) | $1.30 ($0.043/series) | $0.79 ($0.027/series) |
| Predicted a priori (pilot-1 model) | $1.32 (+1.4%) | $0.56 (−30%) |
| Config | 10 clin_ct models, radiomicsjl, firstorder+shape | `total` task, radiomicsjl, firstorder+shape |

Entity set `twoVM_pilot2_set/pilot2_all`: 9 entities of 1/3/6 series (small/large/mixed per
size), 30 series, 1442 Mvox, corr(nSeries, Mvox) = 0.45, no overlap with the Aug-18 pilot.
Region us-west4, spot, checkpointing on. Fits: `model_moose_pilot2.json`,
`model_totalseg_pilot2.json`; data: `submission_{71a2f34a,02b36d47}_*.csv`; figures:
`figs_moose_pilot2/`, `figs_totalseg_pilot2/`.

> **All `$` figures are from the GCP billing export** (settled 2026-09-01, net of credits).
> `model_*_pilot2.json` are refit on billed dollars; the pre-settlement fits are kept as
> `model_*_pilot2_estcost.json`. See section 1b for prediction vs bill.

## 1. Can cost/time be estimated from dataset size?

**Output conversion (nb3): yes, strongly.** `time = a + b·nSeries + c·Mvox` per workflow:

| task | fit (min) | R² |
|---|---|---|
| MOOSE nb3 | 10.0 − 1.75·nSeries + 0.130·Mvox | 0.89 |
| TotalSeg nb3 | 8.4 − 1.71·nSeries + 0.075·Mvox | 0.86 |

Per-series phases are near-pure functions of Mvox: SEG encoding R² = 0.99–1.00,
radiomics R² = 0.79–0.82, dcm2niix R² = 0.72–0.97 (`series_phase_timings.png`).

**Inference (nb2): the compute is predictable, the spot market is not.** Per-series
inference time is stable and reproduces the Aug-18 pilot almost exactly (TotalSeg:
77 s + 0.55 s/Mvox now vs 77 s + 0.58 s/Mvox then). But workflow-level wall-clock fits
degraded (MOOSE R² = 0.87, TotalSeg R² = 0.02) because this was a heavy spot-churn day:
~15 preemptions plus GPU-quota waits up to 78 min. Measured preemption/retry overhead:
**98% (MOOSE) / 73% (TotalSeg)** of successful-attempt time, vs 0% on Aug 18.

**Recommendation:** predict inference from the per-series fit × (1 + preempt_overhead),
carrying preemption overhead as its own measured, region/time-varying factor; predict nb3
directly from the workflow-level fit. Both predictors come from the manifest before launch.

## 1b. Prediction vs the bill

The Aug-18 pilot-1 models (`model_*_pilot1.json`) priced pilot2 from the manifest alone
before launch (`cost_model.py predict`), then were scored against the billing export
(`cost_model.py evaluate`).

| | Predicted | 95% interval | Catalog estimate | Billed | Error | MAPE / coverage |
|---|---|---|---|---|---|---|
| MOOSE | $1.32 | 1.13–1.51 | $1.62 | **$1.30** | +1.4% | 12% / 89% |
| TotalSegmentator | $0.56 | 0.50–0.62 | $0.90 | **$0.79** | −30% | 26% / 33% |

Per task:

| Task | Pred $ | Billed $ | Error | Pred min | Billed min | Cause |
|---|---|---|---|---|---|---|
| MOOSE inference | 0.82 | 1.07 | −24% | 187 | 340 | preemption/retry overhead 0% → 98% |
| MOOSE output conversion | 0.50 | 0.23 | +120% | 464 | 221 | 5-Mvox ROI guard (shipped between pilots) |
| TotalSeg inference | 0.46 | 0.64 | −28% | 104 | 185 | preemption/retry overhead 0% → 73% |
| TotalSeg output conversion | 0.10 | 0.15 | −35% | 88 | 133 | `juliaThreads=1` vs racy auto-threading |

- MOOSE's +1.4% is two ~equal errors cancelling; TotalSeg's −30% is genuine under-prediction
  on both tasks, and its intervals (calibrated on a calm day) covered only 3/9 workflows.
- Terra's reported cost matched the export to the cent once `costType=Actual`.
- The offline catalog estimate (`submission_cost.py` fallback) overshoots inference by 19–33%:
  the T4 VM billed at an effective $0.19–0.21/h vs $0.254/h catalog (ratio 0.74–0.82);
  the CPU VM billed 1.08× catalog (disk/egress/external-IP SKUs). Bake both ratios into the
  estimator.
- Refit on billing: MOOSE inference $ R²=0.96, nb3 $ R²=0.87–0.90; TotalSeg inference $
  R²=0.22 (preemption noise, as with time).
- Lesson: the size model captures the structure, but a prediction only holds for the code
  that generated its pilot (two code changes moved per-task cost 2× in opposite directions)
  and preemption overhead alone swings inference ±25% between days. Predict the full run
  from the billing-refit pilot2 models; re-pilot TotalSegmentator on v2.18 first.

## 2. Effect of the code changes (vs Aug-18 pilot, same series count basis)

- **MOOSE nb3 ~40% faster per Mvox** (9.1 vs 14.7 s/Mvox): the 5-Mvox ROI guard skips
  whole-body radiomics (`clin_ct_body` etc.); SEG is still written for those labels.
- **TotalSeg nb3 ~2.6× slower per Mvox** (5.9 vs 2.3 s/Mvox): the price of
  `juliaThreads=1`, which avoids the Radiomics.jl multi-label thread race. Reverts when
  the upstream race is fixed.

## 3. Checkpointing validated live on Terra

The restore-on-preemption path (unexercised in the Aug-28 validation) ran for real:
- TotalSeg entity 3 (preempted 2×): attempt 3 restored the 3-series NIfTI bundle in 1.7 s,
  skipped the 1 finished series, inferred the remaining 2, cleaned up the prefix on success.
- MOOSE entity 4: checkpoint timestamps show attempt 2 resumed at model 5/10
  (`clin_ct_lungs`) without re-uploading anything attempt 1 finished.

A preemption now costs ~10–15 min of boot/pull/restore instead of the whole task.

## 4. Spot vs on-demand economics

Inference VM: $0.25/h spot vs ~$0.55/h on-demand (~2.2×). Break-even needs
`preemptions × penalty > 1.2 × runtime` ≈ 3+ preemptions per task, which Cromwell's
`preemptible: 3` + on-demand fallback caps by construction. Even at today's 98% overhead
MOOSE inference was at worst break-even; on a normal day spot wins >2×. Checkpointing is
what keeps bad days bounded.

## 5. Entity-9 failure: moosez native crash on an L3-clipped chest CT

MOOSE entity 9 failed terminally. Root cause (reproduced/diagnosed locally with the same
image digest):

- Series `1.3.6.1.4.1.14519.5.2.1.1.24600201214821555311405515776776509079` (cmb_mel,
  `CHEST ST Body Axial`) barely contains L3 — the vertebra moosez's
  `clin_ct_body_composition` workflow crops to (fast_vertebrae → L3 z-band → composition).
- With L3 edge-clipped, the pipeline crashes **natively** (Jupyter kernel death, no Python
  traceback) on the T4; on a local RTX 3070 the slightly different vertebrae prediction
  yields a degenerate-but-survivable 2-slice output. Deterministic on Terra: attempts 2
  and 4 died at the identical spot; the two other attempts were ordinary preemptions.
- nb2's per-series `try/except` cannot catch a kernel death, so all 6 series in the batch
  were lost, not just the bad one.

**Actions:** (1) run each `moose()` call in a child process in nb2 so a native crash
becomes an `inference_errors.txt` entry and the batch survives; (2) report upstream to
ENHANCE-PET/MOOSE ("body_composition crashes when L3 is absent/edge-clipped; validate the
crop bbox"); (3) optionally bake `Dataset112_FastVertebrae` into the image to remove the
per-VM runtime download.

## 6. Figure guide (per model, in `figs_*_pilot2/`)

- `phase_breakdown_per_workflow.png` — VM time per workflow by phase; the *unaccounted*
  band is boot/pull/preemption tax (dominant for MOOSE inference on this churn day).
- `model_fit.png` — predicted vs actual per task; nb3 on the diagonal, TotalSeg inference
  scattered by preemption noise.
- `unit_cost_vs_batch_size.png` — $/series falls with batch size (fixed-overhead
  amortization; the case for larger entities now that checkpointing bounds preemption risk).
- `series_phase_timings.png` — per-series phase time vs Mvox; SEG/radiomics as near-perfect
  lines through the load-balancing metric.
- `cost_vs_workload.png`, `task_runtime_vs_workload.png`, `cost_by_task_per_workflow.png`,
  `download_vs_size.png` — supporting views.

## 7. Next steps

1. Commit the prediction for the 300-series full run (`manifests/full_terra_data_table.tsv`)
   from the billing-refit `model_*_pilot2.json` before launching; re-pilot TotalSegmentator
   on v2.18 first. Bake the effective-rate ratios into the offline estimator.
2. nb2 subprocess isolation for MOOSE (poison-series robustness).
3. Upstream reports: moosez body_composition crash; Radiomics.jl thread race + NIfTI
   scl_slope rescale gotcha.
