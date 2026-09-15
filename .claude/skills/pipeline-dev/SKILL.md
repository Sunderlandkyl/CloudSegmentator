---
name: pipeline-dev
description: Editing the harmonized workflow notebooks/WDL safely and debugging the pipeline locally (docker repro, checkpoint data recovery, papermill quirks). Use before modifying nb1/nb2/nb3, the WDL, or reproducing a Terra failure on this machine.
---

# Pipeline development and local debugging

## Layout

- nb1 `workflows/common/Notebooks/convertNotebook.ipynb` — DICOM→NIfTI (GPU VM)
- nb2 `workflows/models/{moose,totalseg}/Notebooks/inference.ipynb` — engine-specific (GPU VM)
- nb3 `workflows/common/Notebooks/outputConversionNotebook.ipynb` — SEG/radiomics/SR/upload (CPU VM), shared
- `workflows/common/Notebooks/segmentator_checkpoint.py` — checkpoint/resume + attempt ledger + MemSampler
- WDL `workflows/harmonized/Terra/twoVM.wdl`; boundaries: A `converted_nifti.tar.lz4`, B `segmentations.tar.lz4` (`<uid>/<model>/segmentations + label_map.json`)
- Legacy `workflows/MOOSE/`, `workflows/TotalSegmentator/` are **frozen** — don't port changes into them.

## Editing the notebooks

- **Cell `source` storage is mixed** (some cells JSON lists-of-lines, some
  single strings). Never normalize — it churns the whole file (800-line diffs).
  The repo files round-trip cleanly through
  `json.dumps(nb, indent=1, ensure_ascii=False)` per-file (match the file's
  newline style and trailing-newline); edit cells by exact-substring replace on
  the joined source, re-split with `splitlines(keepends=True)` **only if the
  cell was already a list**, and `assert src.count(old) == 1` per replacement.
- After any edit: `compile()` every code cell, then `git diff --stat` — a
  notebook edit should be tens of lines, not hundreds.
- **WDL ↔ notebook coupling**: output filenames, papermill `-p` names, and
  fetched sidecar files (checkpoint module, SNOMED CSVs,
  `radiomicsFeaturesMaps.csv`) must change together and ship in one push —
  Terra fetches all of it from GitHub raw at run time.
- Papermill quirk: WDL Booleans render lowercase `true`/`false`, which papermill
  passes through as truthy *strings* — notebooks normalize via `_as_bool`; new
  boolean params must do the same.
- New notebook parameters with defaults need **no WDL change** (papermill only
  overrides what `-p` passes); model knobs go through `inferenceParamsYaml`.
- Undeclared task outputs are **not delocalized** — anything that must survive
  the VM needs a WDL `output` entry (or ride an existing archive/CSV; extra CSV
  columns are the compatible way to add metrics).

## Local repro

- Images: `sunderlandkyl/inference_{moose,totalseg}:main`,
  `sunderlandkyl/output_conversion:main` (Docker Hub; may already be pulled).
  On Windows, if `docker info` hangs, Docker Desktop's backend is wedged —
  kill its processes and relaunch; its WSL VM (`vmmemWSL`) holds gigabytes,
  so quit Docker Desktop when done on RAM-constrained hosts.
- Git Bash mangles `/data` args into `C:/Program Files/Git/data` — prefix
  docker commands with `MSYS_NO_PATHCONV=1`.
- nnU-Net passes tensors via `/dev/shm`: local runs need `--shm-size=8g`
  (Terra sizes shm from VM RAM automatically).
- Docker Desktop's WSL VM caps container RAM (~half host); good for
  reproducing VM-memory-ceiling behavior (that's how the lung_vessels 14 GiB
  peak was measured, via `docker stats` sampling).
- **Recover a failed run's inputs from its checkpoint** instead of
  re-downloading/converting: aborted/failed runs leave
  `gs://<workspace-bucket>/segmentator_ckpt/<submissionId>_<workflowId>/`
  (the workspace bucket is the `checkpointGcsPath` config input)
  (`nifti/all.tar.lz4` = nb1's converted NIfTIs; `seg/<uid>/<model>.tar.lz4` =
  finished nb2 outputs). Successful runs clean this up.
- If no `lz4` CLI is available (typical on Windows), use `pip install lz4` +
  `lz4.frame.open()` with streaming `tarfile.open(fileobj=..., mode='r|')`.
- Live logs of a running task: workspace bucket
  `submissions/<sid>/Segmentator/<wid>/call-<task>/stderr` (synced lazily;
  retry attempts under `attempt-N/`). Checkpoint object timestamps are the
  reliable liveness signal.
- Local papermill smoke tests of nb2/nb3 were the pre-Terra validation path for
  every engine upgrade — do that before burning a submission on a code change.
