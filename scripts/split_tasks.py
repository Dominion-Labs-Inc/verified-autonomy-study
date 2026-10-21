"""Split the 500 tasks into a tuning half and a held out half, fixed before any run is examined.

Each task is ranked by the SHA-256 of a fixed salt joined to its identifier; the first 250
in that order form the tuning half. The assignment depends on nothing but the identifiers
and the salt, so any implementation in any language reproduces it exactly.

Writes data/task_split.csv (instance_id, half).
"""

import hashlib
import sys

from common import DATA, read_csv, write_csv

SALT = "verified-autonomy-study/task-split/v1:"
TUNING = 250


def rank(instance_id):
    return hashlib.sha256((SALT + instance_id).encode("utf-8")).hexdigest()


def main():
    tasks = [row["instance_id"] for row in read_csv(DATA / "tasks.csv")]
    if len(tasks) != 2 * TUNING:
        sys.exit(f"expected {2 * TUNING} tasks, found {len(tasks)}")
    ordered = sorted(tasks, key=rank)
    tuning = set(ordered[:TUNING])
    rows = [{"instance_id": t, "half": "tuning" if t in tuning else "held_out"} for t in sorted(tasks)]
    write_csv(DATA / "task_split.csv", ["instance_id", "half"], rows)
    print(f"{TUNING} tuning, {len(tasks) - TUNING} held out")


if __name__ == "__main__":
    main()
