"""Verify a finished harmonized-workflow submission: per-workflow status, run
summaries, and the content of every error file.

Usage: check_outputs.py <submissionId> [--full-errors]

Default prints each error file's first lines; --full-errors prints everything.
Triage the errors against the KNOWN failure modes before treating anything as
new (see .claude/skills/terra-runs/SKILL.md):
  - itkimage2segimage "Invalid Value"      -> known series class (~2 %), both engines
  - radiomics_jl NaN "not allowed in JSON" -> known Radiomics.jl bug, drops one
                                              (series, model) radiomics + SR
  - "moose produced no output" (body_composition) -> anatomical (no L3 in FOV), benign
  - "Radiomics.jl worker crashed"          -> nb3 RAM pressure (giant series on 16 GB VM)
"""
import json
import subprocess
import sys
import urllib.request

NS, NAME = "terra-billing-datester", "kyle-testing"
FIRECLOUD = "https://api.firecloud.org/api"


def api(path, tok):
    req = urllib.request.Request(FIRECLOUD + path,
                                 headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def gcs_cat(url):
    return subprocess.run(["gcloud", "storage", "cat", url],
                          capture_output=True, text=True, shell=True).stdout


def main():
    sid = sys.argv[1]
    full = "--full-errors" in sys.argv
    tok = subprocess.run("gcloud auth print-access-token", shell=True,
                         capture_output=True, text=True).stdout.strip()
    det = api(f"/workspaces/{NS}/{NAME}/submissions/{sid}", tok)
    print(f"submission {sid[:8]}: status={det.get('status')} "
          f"est=${det.get('cost', 0):.2f}  (billing settles ~24-48 h later)")
    for w in det.get("workflows", []):
        wid = w.get("workflowId")
        if not wid:
            continue
        md = api(f"/workspaces/{NS}/{NAME}/submissions/{sid}/workflows/{wid}"
                 "?includeKey=outputs&includeKey=status", tok)
        ent = w.get("workflowEntity", {}).get("entityName")
        print(f"\n===== entity {ent} [{wid[:8]}] {md.get('status')} =====")
        outs = md.get("outputs", {})
        for k in sorted(outs):
            v = outs[k]
            if not isinstance(v, str):
                continue
            if k.endswith("runSummary"):
                s = json.loads(gcs_cat(v))
                print(f"  summary: seg_err={s.get('dicom_seg_errors')} "
                      f"rad_err={s.get('radiomics_errors')} sr_err={s.get('sr_errors')} "
                      f"srs={s.get('structured_reports_written')} "
                      f"skipped_large={s.get('radiomics_labels_skipped_large')} "
                      f"engine={s.get('engine', '?')} v{s.get('engine_version', '?')} "
                      f"elapsed={s.get('total_elapsed_s', 0) / 60:.0f}m")
            elif "error" in k.lower():
                txt = gcs_cat(v).strip()
                lines = txt.splitlines()
                print(f"  --- {k.split('.')[-1]} ({len(lines)} lines) ---")
                print("\n".join(lines) if full else "\n".join(lines[:8]))


if __name__ == "__main__":
    main()
