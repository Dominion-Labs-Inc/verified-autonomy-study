"""Compute the worst case 95 percent margin of every planned proportion before any data exists.

Each margin is the half width of the Wilson score interval at a true rate of 50 percent, the
widest it can be for that sample size. The pooled run count is read from the inventory, so
the margin follows the set of candidate submissions rather than a typed number.

Writes results/sample_sizes.csv.
"""

import math

from common import DATA, RESULTS, read_csv, write_csv

Z = 1.959963984540054
TASKS = 500
LABELED_PER_SAMPLE = 400


def wilson_half_width(n, p=0.5, z=Z):
    denominator = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator


def main():
    candidates = sum(row["status"] == "candidate" for row in read_csv(DATA / "submissions.csv"))
    plan = [
        ("RQ1 unconfirmed completion claims, per model", TASKS),
        ("RQ1 unconfirmed completion claims, all candidate runs", candidates * TASKS),
        ("RQ3 precision of flagged actions", LABELED_PER_SAMPLE),
        ("RQ3 misses among allowed actions", LABELED_PER_SAMPLE),
    ]
    rows = [
        {"quantity": name, "n": n, "worst_case_margin_points": f"{100 * wilson_half_width(n):.1f}"}
        for name, n in plan
    ]
    write_csv(RESULTS / "sample_sizes.csv", ["quantity", "n", "worst_case_margin_points"], rows)
    for row in rows:
        print(f"{row['quantity']}: n = {row['n']}, plus or minus {row['worst_case_margin_points']} points")


if __name__ == "__main__":
    main()
