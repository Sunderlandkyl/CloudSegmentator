"""Submit a MOOSE + TotalSegmentator pair of harmonized-workflow runs on Terra.

For each engine: PUT the shared method config with that engine's inputs (docker,
nb2 path, SNOMED mapping, model list), point it at the requested root entity
type, then POST a submission. The config is a shared mutable slot -- Terra
snapshots it per submission, so reconfigure-then-submit per engine is safe.

Usage:
    python submit_wave.py <rootEntityType> <entityName> [entityType] [expression]

    # one entity:            submit_wave.py twoVM_pilot2 4
    # an entity set:         submit_wave.py twoVM_batch23 batch23_all \\
    #                                       twoVM_batch23_set this.twoVM_batch23s

Constants below (workspace, config name, bucket, RAM) are the current campaign
defaults -- edit them deliberately. dicomSegBucketUri deliveries overwrite
per-file (same <uid>/<model>_<idx>[_sr].dcm names -> latest run wins).
"""
import json
import subprocess
import sys
import urllib.request

NS, NAME = "terra-billing-datester", "kyle-testing"
CNS, CNAME = "terra-billing-datester", "SegmentatorTwoVmWorkflowOnTerra"
FIRECLOUD = "https://api.firecloud.org/api"
BUCKET = '"gs://idc-not-a-challenge/kyle/"'
# 32 GB: TotalSegmentator lung_vessels needs ~14 GiB peak on a 320-Mvox series and
# LIVELOCKS a swapless 16 GB VM (Sep 2026). ~+$0.03/h on the GPU VM.
INFERENCE_RAM = "32"

MODELS = {
    "moose": {
        "Segmentator.inferenceDocker": '"sunderlandkyl/inference_moose:main"',
        "Segmentator.inferenceNotebookPath": '"workflows/models/moose/Notebooks/inference.ipynb"',
        "Segmentator.snomedMappingPath": '""',   # moosez bundles its own mapping
        "Segmentator.inferenceParamsYaml": '"moose_models: clin_ct_body,clin_ct_body_composition,clin_ct_cardiac,clin_ct_digestive,clin_ct_lungs,clin_ct_muscles,clin_ct_organs,clin_ct_peripheral_bones,clin_ct_ribs,clin_ct_vertebrae"',
        "Segmentator.modelName": '"moose"',
    },
    "totalseg": {
        "Segmentator.inferenceDocker": '"sunderlandkyl/inference_totalseg:main"',
        "Segmentator.inferenceNotebookPath": '"workflows/models/totalseg/Notebooks/inference.ipynb"',
        "Segmentator.snomedMappingPath": '"workflows/models/totalseg/resources/snomed_mapping.csv"',
        "Segmentator.inferenceParamsYaml": '"task: total,lung_vessels"',
        "Segmentator.modelName": '"totalseg"',
    },
}


def api(path, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(FIRECLOUD + path, data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:800]}")
        sys.exit(1)


def main():
    root_type, entity_name = sys.argv[1], sys.argv[2]
    entity_type = sys.argv[3] if len(sys.argv) > 3 else root_type
    expression = sys.argv[4] if len(sys.argv) > 4 else None
    token = subprocess.run("gcloud auth print-access-token", shell=True,
                           capture_output=True, text=True).stdout.strip()

    for model, overrides in MODELS.items():
        cfg = api(f"/workspaces/{NS}/{NAME}/method_configs/{CNS}/{CNAME}", token)
        cfg["inputs"].update(overrides)
        cfg["inputs"]["Segmentator.dicomSegBucketUri"] = BUCKET
        cfg["inputs"]["Segmentator.dicomStoreImportUri"] = '""'
        cfg["inputs"]["Segmentator.inferenceRAM"] = INFERENCE_RAM
        cfg["rootEntityType"] = root_type
        api(f"/workspaces/{NS}/{NAME}/method_configs/{CNS}/{CNAME}", token, "PUT", cfg)
        body = {
            "methodConfigurationNamespace": CNS,
            "methodConfigurationName": CNAME,
            "entityType": entity_type,
            "entityName": entity_name,
            "useCallCache": False,
            "deleteIntermediateOutputFiles": False,
        }
        if expression:
            body["expression"] = expression
        sub = api(f"/workspaces/{NS}/{NAME}/submissions", token, "POST", body)
        print(f"{model}: submissionId={sub['submissionId']}")


if __name__ == "__main__":
    main()
