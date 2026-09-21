---
name: dicom-delivery
description: Delivering DICOM-SEG/SR outputs to GCS and (eventually) a Healthcare DICOM store — bucket layout, overwrite semantics, provenance-metadata verification with pydicom, store-import prerequisites. Use for "upload results", "check the metadata", "import into the DICOM store".
---

# DICOM delivery: bucket upload, metadata, store import

## Bucket upload (works, in production)

Set `dicomSegBucketUri` (currently `gs://idc-not-a-challenge/kyle/`) and nb3
uploads every SEG **and** TID1500 SR as
`<prefix>/<SeriesInstanceUID>/<model>_<idx>[_sr].dcm`. Leave
`dicomStoreImportUri` empty.

- **Per-file overwrite**: deterministic names mean a re-run clobbers in place
  (latest wins) but **never deletes** — a file the new run didn't regenerate
  (e.g. an SR lost to a NaN-radiomics drop) lingers with old metadata. Audit
  freshness by object timestamp (`gcloud storage ls -l`), not by folder.
- Upload is warn-and-continue (`WARNING: GCS upload failed` in the output
  notebook only) — spot-check the bucket after enabling it on a new config.
- Auth is the Terra pet service account via ADC; no secrets. (`secret_project`
  is unrelated — s5cmd HMAC keys for private-GCS *input*.)

## Provenance metadata (since commit 9e5bba4)

nb2 bundles `engine_provenance.json` (engine + package version) into the
Boundary-B archive; nb3 stamps, per SEG:

- `SegmentAlgorithmName` = `"MOOSE v3.2.2 clin_ct_organs"` /
  `"TotalSegmentator v2.18.0 total_fast"` (engine + version + `model_id` from
  nb2's `label_map.json`), `SegmentAlgorithmType: AUTOMATIC` (per segment)
- `SeriesDescription` = `"MOOSE(v3.2.2) clin_ct_organs Segmentation"`,
  `ContentCreatorName: IDC`
- `SeriesNumber` = sourceSeriesNumber×100 + a stable per-model slot
  (`MODEL_SERIES_SLOTS` in nb3: clin_ct_* → 1–10, total 11, total_fast 12,
  lung_vessels 13; unknown models overflow); paired SR = base + 50 + slot.
  Missing/non-numeric source SeriesNumber → base 100.
- SR: `SeriesDescription` = `"<SegmentAlgorithmName> Radiomics"`; each
  measurement group's `AlgorithmParameters` = `segmentation=<SegmentAlgorithmName>`.
  Radiomics JSON rows: `model_id`, `seg_engine`, `seg_engine_version`.

Each SEG/SR is its own new DICOM series (fresh dcmqi UIDs) inside the **source
study's** StudyInstanceUID. Re-uploading a series creates new SOPInstanceUIDs —
a DICOM store that already imported the old version will keep both.

### Verifying with pydicom — the segment-0 trap

dcmqi **labelmap** SEGs prepend a background segment (SegmentNumber 0) whose
`SegmentAlgorithmName` is None and `SegmentAlgorithmType` is `MANUAL`.
**Always skip SegmentNumber 0**; reading `SegmentSequence[0]` produces the
false conclusion "metadata missing / MANUAL" (this mistake has been made twice).

```python
ds = pydicom.dcmread(f, stop_before_pixels=True)
segs = [s for s in ds.SegmentSequence if int(s.SegmentNumber) != 0]
```

## Healthcare DICOM store import (NEVER validated end-to-end)

nb3's `dicomStoreImportUri` path (GCS → `dicomStores.import`, polled) has never
run successfully. Prereqs for whoever enables it:

1. Store's project needs **active billing** and the Healthcare API enabled
   (the original test store's project no longer qualifies — verify before use).
2. Pet SA needs `roles/healthcare.dicomEditor` on the dataset.
3. That project's Healthcare service agent
   (`service-<PROJECT_NUMBER>@gcp-sa-healthcare.iam.gserviceaccount.com`) needs
   read on the staging bucket — for `idc-not-a-challenge` only IDC admins can
   grant this.
4. URI format: bare resource name
   `projects/P/locations/L/datasets/D/dicomStores/S` (no `https://`, no
   `/dicomWeb`). Import pattern `<bucket>/**.dcm` picks up SEGs + SRs.
5. Deflate transfer syntax (our SEGs) is supported by the Healthcare API.
6. Import failures only WARN in the output notebook — verify in the store.

The plan of record: bucket delivery from Terra; IDC-side store import later.
