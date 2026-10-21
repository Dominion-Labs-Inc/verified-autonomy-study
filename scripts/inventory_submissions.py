"""Inventory every SWE-bench Verified submission and classify the structure of its logs.

For each submission at a pinned commit of the SWE-bench experiments repository, this reads
its metadata, finds where its step by step logs are published, reads the first 8 KB of one
log file, and records the log's structure. Each structure is assigned to one of three adapter
families or to an exclusion reason. A candidate enters the study only after its family's
adapter passes the fidelity test in ANALYSIS_PLAN.md; this inventory decides nothing more.

Writes data/submissions.csv and data/submissions_source.json.
"""

import concurrent.futures
import json
import re
import urllib.error
import urllib.parse
from datetime import datetime, timezone

from common import DATA, http_get, http_json, write_csv

EXPERIMENTS_REPO = "SWE-bench/experiments"
EXPERIMENTS_COMMIT = "40f164d5b8f1d249bf95a6df8b74b577fd8e519d"
SPLIT_DIR = "evaluation/verified"
PREVIEW_BYTES = 8192
PREFERRED_LOG = re.compile(r"\.(traj\.json|traj|json|jsonl)$")

FAMILIES = {
    "A": "mini-SWE-agent trajectory",
    "B": "SWE-agent trajectory",
    "C": "chat transcript with tool calls",
}
CHAT_OBJECT_MARKERS = ("messages,role,content", "type,message,role,content", "iteration,input,role,content", "llm_call_data")


def raw_url(path, ref=EXPERIMENTS_COMMIT, repo=EXPERIMENTS_REPO):
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(path)}"


def list_submissions():
    entries = http_json(
        f"https://api.github.com/repos/{EXPERIMENTS_REPO}/contents/{SPLIT_DIR}?ref={EXPERIMENTS_COMMIT}"
    )
    return sorted(e["name"] for e in entries if e["type"] == "dir")


def read_metadata(submission):
    for name in ("metadata.yaml", "metadata.yml"):
        try:
            return name, http_get(raw_url(f"{SPLIT_DIR}/{submission}/{name}")).decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    return None, None


def field(text, key):
    match = re.search(rf"^\s*{key}:\s*(.+?)\s*$", text, re.M)
    if not match:
        return ""
    value = match.group(1).strip().strip("'\"")
    return "" if value in ("null", "~", "") else value


def first_log_s3(location):
    bucket, prefix = location[len("s3://"):].split("/", 1)
    query = urllib.parse.urlencode({"list-type": "2", "prefix": prefix.rstrip("/") + "/", "max-keys": "60"})
    listing = http_get(f"https://{bucket}.s3.amazonaws.com/?{query}").decode("utf-8")
    keys = [k for k in re.findall(r"<Key>([^<]+)</Key>", listing) if not k.endswith("/")]
    chosen = next((k for k in keys if PREFERRED_LOG.search(k)), keys[0] if keys else None)
    if chosen is None:
        return None, None
    return chosen, f"https://{bucket}.s3.amazonaws.com/{urllib.parse.quote(chosen)}"


def first_log_github(owner_repo, ref, path):
    for _ in range(3):
        try:
            entries = http_json(
                f"https://api.github.com/repos/{owner_repo}/contents/{urllib.parse.quote(path)}?ref={urllib.parse.quote(ref)}"
            )
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None, None
            raise
        files = [e for e in entries if e["type"] == "file"]
        chosen = next((e for e in files if PREFERRED_LOG.search(e["name"])), files[0] if files else None)
        if chosen:
            return chosen["path"], chosen["download_url"]
        dirs = [e for e in entries if e["type"] == "dir"]
        if not dirs:
            return None, None
        path = dirs[0]["path"]
    return None, None


def locate_first_log(location):
    if location.startswith("s3://"):
        return first_log_s3(location)
    match = re.match(r"https://github\.com/([^/]+/[^/]+)/tree/([^/]+)/(.+)$", location)
    if match:
        return first_log_github(match.group(1), match.group(2), match.group(3))
    if location.startswith(SPLIT_DIR + "/"):
        return first_log_github(EXPERIMENTS_REPO, EXPERIMENTS_COMMIT, location)
    return None, None


def structure(text):
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")):
        keys = []
        for key in re.findall(r'"([A-Za-z_][A-Za-z0-9_ ]{0,40})"\s*:', stripped):
            if key not in keys:
                keys.append(key)
        return ("json-list:" if stripped.startswith("[") else "json:") + ",".join(keys[:6])
    first_line = stripped.splitlines()[0][:60] if stripped else ""
    return "text:" + re.sub(r"\d", "9", first_line)


def classify(signature):
    if signature.startswith("json:info,"):
        return "A"
    if "trajectory" in signature and ("action" in signature or "observation" in signature):
        return "B"
    if signature.startswith("json-list:") and ("role" in signature or "content" in signature) and "found_files" not in signature:
        return "C"
    if signature.startswith("json:") and any(marker in signature for marker in CHAT_OBJECT_MARKERS):
        return "C"
    if signature.startswith("text:"):
        return "free_text"
    return "other_json"


EXCLUSION_REASONS = {
    "free_text": "logs are free text, not a structured record of actions",
    "other_json": "structured logs outside the three adapter families",
    "no_metadata": "metadata could not be read",
    "no_logs": "no step by step logs published",
    "empty_logs": "published log location holds no files",
    "unreadable_logs": "published logs could not be read",
}


def inventory(submission):
    row = {"submission": submission, "agent": "", "model": "", "log_location": "", "sample_log": "",
           "structure": "", "family": "", "status": "", "reason": ""}
    meta_name, text = read_metadata(submission)
    if text is None:
        row.update(status="excluded", reason=EXCLUSION_REASONS["no_metadata"])
        return row
    row["agent"] = field(text, "agent")
    row["model"] = field(text, "name")
    location = field(text, "trajs")
    row["log_location"] = location
    if not location:
        row.update(status="excluded", reason=EXCLUSION_REASONS["no_logs"])
        return row
    try:
        key, url = locate_first_log(location)
        if not url:
            row.update(status="excluded", reason=EXCLUSION_REASONS["empty_logs"])
            return row
        preview = http_get(url, headers={"Range": f"bytes=0-{PREVIEW_BYTES - 1}"}).decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
        row.update(status="excluded", reason=f"{EXCLUSION_REASONS['unreadable_logs']} ({type(error).__name__})")
        return row
    signature = structure(preview)
    family = classify(signature)
    row.update(sample_log=key, structure=signature)
    if family in FAMILIES:
        row.update(family=family, status="candidate", reason=f"{FAMILIES[family]}; inclusion requires the adapter fidelity test")
    else:
        row.update(status="excluded", reason=EXCLUSION_REASONS[family])
    return row


def main():
    submissions = list_submissions()
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(inventory, submissions))
    fields = ["submission", "agent", "model", "log_location", "sample_log", "structure", "family", "status", "reason"]
    write_csv(DATA / "submissions.csv", fields, rows)
    counts = {}
    for row in rows:
        label = f"family {row['family']}" if row["family"] else row["reason"].split(" (")[0]
        counts[label] = counts.get(label, 0) + 1
    source = {
        "repository": EXPERIMENTS_REPO,
        "commit": EXPERIMENTS_COMMIT,
        "split": SPLIT_DIR,
        "submissions": len(rows),
        "candidates": sum(r["status"] == "candidate" for r in rows),
        "counts": dict(sorted(counts.items())),
        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (DATA / "submissions_source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(source, indent=2))


if __name__ == "__main__":
    main()
