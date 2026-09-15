"""Upload a make_terra_manifest data table to Terra and create its _all set.

Usage: upload_table.py <name> [manifests_dir]

Reads <dir>/<name>_terra_data_table.tsv (root entity type twoVM_<name>), uploads
it via flexibleImportEntities, then uploads a membership TSV creating the entity
set twoVM_<name>_set / <name>_all over every row. Submit against it with:

    submit_wave.py twoVM_<name> <name>_all twoVM_<name>_set this.twoVM_<name>s
"""
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

NS, NAME = "terra-billing-datester", "kyle-testing"
FIRECLOUD = "https://api.firecloud.org/api"


def post_tsv(tsv_text, token):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="entities"; filename="upload.tsv"\r\n'
            f"Content-Type: text/tab-separated-values\r\n\r\n"
            f"{tsv_text}\r\n--{boundary}--\r\n").encode()
    req = urllib.request.Request(
        f"{FIRECLOUD}/workspaces/{NS}/{NAME}/flexibleImportEntities",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.read().decode()[:200]
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:500]}")
        sys.exit(1)


def main():
    name = sys.argv[1]
    mdir = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        Path(__file__).resolve().parent.parent / "executionAnalytics" / "manifests"
    tsv = (mdir / f"{name}_terra_data_table.tsv").read_text(encoding="utf-8")
    token = subprocess.run("gcloud auth print-access-token", shell=True,
                           capture_output=True, text=True).stdout.strip()
    print("entities:", post_tsv(tsv, token))
    ids = [row.split("\t", 1)[0] for row in tsv.splitlines()[1:] if row.strip()]
    membership = f"membership:twoVM_{name}_set_id\ttwoVM_{name}\n" + \
        "".join(f"{name}_all\t{i}\n" for i in ids)
    print("set:", post_tsv(membership, token))
    print(f"created set {name}_all with {len(ids)} entities: {ids}")


if __name__ == "__main__":
    main()
