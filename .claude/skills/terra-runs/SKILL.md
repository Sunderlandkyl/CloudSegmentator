---
name: terra-runs
description: Launch, monitor, and verify harmonized Segmentator (MOOSE + TotalSegmentator) runs on Terra — manifest → data table → submission → triage. Use for "run a batch", "resubmit", "check the runs", "why did this workflow fail".
---

# Running harmonized Segmentator workflows on Terra

Workspace `terra-billing-datester/kyle-testing`; method config
`SegmentatorTwoVmWorkflowOnTerra` → Dockstore
`github.com/Sunderlandkyl/CloudSegmentator` @ `harmonized_models`.
All tooling below is in `util/terraOps/` (Terra REST via
`gcloud auth print-access-token`; run `gcloud auth login` once).

## Before ANY submission

1. **Commit + push** the branch. Notebooks, WDL, `segmentator_checkpoint.py`,
   SNOMED CSVs are all fetched from GitHub raw **at run time** — local edits do
   not run. Notebook and WDL changes must land in the same push (e.g. an output
   filename change in one but not the other fails every workflow *after* the
   compute is spent).
2. **Verify Dockstore synced the WDL** (webhook, usually instant):
   `curl -s "https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2FSunderlandkyl%2FCloudSegmentator%2FSegmentatorTwoVmWorkflowOnTerra/versions/harmonized_models/PLAIN-WDL/descriptor" | grep <changed text>`
3. If the docker images changed, rebuild and push them too (`sunderlandkyl/inference_*`,
   `sunderlandkyl/output_conversion`) — the config pins `:main` tags.

## Launch

```
cd util/executionAnalytics
python make_terra_manifest.py full --collections '%cmb%' '%cptac%' \
  --n-series 60 --batch-target 900000000 --seed <n> \
  --exclude manifests/*_series.csv --name batch<N> --outdir manifests
python ../terraOps/upload_table.py batch<N>
python ../terraOps/submit_wave.py twoVM_batch<N> batch<N>_all \
       twoVM_batch<N>_set this.twoVM_batch<N>s
# single entity (smoke test):  submit_wave.py twoVM_pilot2 4
```

- `--batch-target 900000000` ≈ 20 series/entity — the measured $/series knee.
  The default target (~6/entity) is below it.
- Always exclude every prior `*_series.csv` (and `full_series.csv`, reserved for
  cost-model validation) unless deliberately re-running series.
- `submit_wave.py` submits **both engines** (MOOSE all 10 clin_ct models,
  TotalSeg `total,lung_vessels`) by editing then submitting the shared config —
  Terra snapshots the config per submission, so sequential reconfigure/submit is safe.
- Validate risky changes with a **small run first** (pilot2 entity 4 = 3 series,
  ~$0.10, ~15–60 min) before batch-scale submissions.

## Monitor

`python util/terraOps/watch_wave.py label:submissionId ...` prints a line per
status change and exits when all submissions are terminal. Run it under a
Monitor or background shell; **cap watch intervals at ~30 min** (Monitor expiry
as heartbeat) and poll the API directly if a watcher dies — background tasks get
killed under local memory pressure.

- Typical wall clock (20-series entity, us-west4 spot T4): TotalSeg 1–3 h,
  MOOSE 1.5–4.5 h. Small 3-series runs: 12–60 min.
- **Preemption weather dominates**: identical workloads have run 0-preemption
  and 3–8-attempts-per-workflow within the same week. `preemptibleTries=5` then
  on-demand fallback (2.2× spot). Checkpointing (verified working) restores the
  NIfTI bundle + finished (series, task) outputs in ~12 s per retry.
- A workflow "Running" for hours with **no new checkpoint objects** under
  `gs://<workspace-bucket>/segmentator_ckpt/<submissionId>_<workflowId>/` is
  wedged, not slow — read the call's live stderr under the workspace bucket
  `submissions/<sid>/Segmentator/<wid>/call-inference/`, and abort with
  `DELETE /workspaces/{ns}/{name}/submissions/{sid}` (other workflows in the
  submission keep their results).
- RAM: `inferenceRAM=32` is the default in submit_wave.py — TotalSeg
  `lung_vessels` peaks ~14 GiB on a 320-Mvox series and **livelocks** a
  swapless 16 GB VM (hours of billed no-progress). nb3 stays 16 GB; series
  ≳300 Mvox can crash its Radiomics.jl worker (loses one (series, task)
  radiomics+SR, SEG survives).

## Verify + triage

`python util/terraOps/check_outputs.py <submissionId>` — statuses, run
summaries, error files. Known failure modes (do NOT treat as new):

| Signature | Meaning |
|---|---|
| `itkimage2segimage ... Invalid Value` | Series class (~2 % of series) failing SEG for **all models, both engines**. Known: `...69653227`, `...730074`, `...891272`, `...222052`. Unfixed; needs dcmqi repro. |
| `radiomics_jl_extract.jl ... NaN not allowed` | Known Radiomics.jl bug; drops one (series, model) radiomics + SR. Fix identified (write null), unimplemented. |
| `body_composition: moose produced no output` | Anatomical (no L3 in FOV) — benign. |
| `Radiomics.jl worker crashed twice` | nb3 RAM pressure on a giant series. |
| Missing lungs/ribs/lung_vessels files for a series | Empty mask outside FOV — by design, not an error. |

Costs: Terra's `cost` field is an **estimate** (historically up to 3× off under
churn; sometimes exact); truth is the BigQuery billing export, settled 24–48 h
later (`util/executionAnalytics/submission_cost.py`). Ballpark: ~$0.02/series
calm → ~$0.045/series churn, both engines combined, at 20-series batching.
