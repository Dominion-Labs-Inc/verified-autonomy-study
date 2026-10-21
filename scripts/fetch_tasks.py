"""Record the 500 SWE-bench Verified task identifiers and the dataset revision they came from.

Writes data/tasks.csv (instance_id, repo) and data/tasks_source.json. The identifiers are
also read from the earlier publication of the same dataset, and the run fails if the two
lists differ, so the task set is the one every submission was evaluated on.
"""

import json
import sys
import urllib.parse
from datetime import datetime, timezone

from common import DATA, http_json, write_csv

PRIMARY = "SWE-bench/SWE-bench_Verified"
CROSS_CHECK = "princeton-nlp/SWE-bench_Verified"
EXPECTED = 500
PAGE = 100


def instance_ids(dataset):
    rows, offset = [], 0
    while True:
        query = urllib.parse.urlencode(
            {"dataset": dataset, "config": "default", "split": "test", "offset": offset, "length": PAGE}
        )
        page = http_json(f"https://datasets-server.huggingface.co/rows?{query}")
        batch = [r["row"] for r in page["rows"]]
        rows.extend({"instance_id": r["instance_id"], "repo": r["repo"]} for r in batch)
        offset += len(batch)
        if not batch or offset >= page["num_rows_total"]:
            return rows


def revision(dataset):
    return http_json(f"https://huggingface.co/api/datasets/{dataset}")["sha"]


def main():
    primary = instance_ids(PRIMARY)
    check = instance_ids(CROSS_CHECK)
    ids = sorted(r["instance_id"] for r in primary)
    if len(ids) != EXPECTED or len(set(ids)) != EXPECTED:
        sys.exit(f"expected {EXPECTED} unique tasks in {PRIMARY}, found {len(set(ids))}")
    if ids != sorted(r["instance_id"] for r in check):
        sys.exit(f"{PRIMARY} and {CROSS_CHECK} list different tasks")
    write_csv(DATA / "tasks.csv", ["instance_id", "repo"], sorted(primary, key=lambda r: r["instance_id"]))
    source = {
        "dataset": PRIMARY,
        "dataset_revision": revision(PRIMARY),
        "cross_checked_against": CROSS_CHECK,
        "cross_check_revision": revision(CROSS_CHECK),
        "split": "test",
        "tasks": len(ids),
        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (DATA / "tasks_source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print(f"{len(ids)} tasks written; identical in both publications")


if __name__ == "__main__":
    main()
