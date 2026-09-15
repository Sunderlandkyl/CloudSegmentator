"""Poll Terra submissions; print a line on every status change; exit when all done.

Usage: watch_wave.py <label:submissionId> [<label:submissionId> ...]

Each printed line is an event (drive it from a Monitor or a background shell and
treat exit as "all terminal"). Warns hourly after 3 h so preemption churn or a
livelocked task gets noticed. Poll errors (Terra 502s) are printed and retried.
"""
import json
import subprocess
import sys
import time
import urllib.request

NS, NAME = "terra-billing-datester", "kyle-testing"
FIRECLOUD = "https://api.firecloud.org/api"


def token():
    return subprocess.run("gcloud auth print-access-token", shell=True,
                          capture_output=True, text=True).stdout.strip()


def api(path, tok):
    req = urllib.request.Request(FIRECLOUD + path,
                                 headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    targets = [a.split(":", 1) for a in sys.argv[1:]]
    prev = {}
    start = time.time()
    warned_hours = set()
    while True:
        tok = token()
        all_done = True
        for label, sid in targets:
            try:
                det = api(f"/workspaces/{NS}/{NAME}/submissions/{sid}", tok)
            except Exception as exc:  # noqa: BLE001 - transient API errors
                print(f"{label}: poll error ({exc}); retrying", flush=True)
                all_done = False
                continue
            sub_status = det.get("status")
            wf = {}
            for w in det.get("workflows", []):
                wf[w.get("status", "?")] = wf.get(w.get("status", "?"), 0) + 1
            state = f"{sub_status} {json.dumps(wf, sort_keys=True)}"
            if prev.get(sid) != state:
                print(f"{label} [{sid[:8]}]: {state} (T+{(time.time() - start) / 60:.0f}m)",
                      flush=True)
                prev[sid] = state
            if sub_status not in ("Done", "Aborted"):
                all_done = False
        hours = int((time.time() - start) / 3600)
        if hours >= 3 and hours not in warned_hours:
            warned_hours.add(hours)
            print(f"WARNING: wave still running after {hours}h — "
                  f"check for preemption churn / cost", flush=True)
        if all_done:
            print("ALL SUBMISSIONS TERMINAL", flush=True)
            break
        time.sleep(90)


if __name__ == "__main__":
    main()
