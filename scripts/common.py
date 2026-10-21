"""Shared helpers: plain HTTP over the standard library, and small CSV writers."""

import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

USER_AGENT = "verified-autonomy-study/1.0"


def http_get(url, headers=None, attempts=4, timeout=60):
    """Return the body of a GET request as bytes, retrying transient failures."""
    merged = {"User-Agent": USER_AGENT}
    merged.update(headers or {})
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=merged)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code in (404, 410):
                raise
            last = error
        except (urllib.error.URLError, TimeoutError) as error:
            last = error
        time.sleep(2 ** attempt)
    raise last


def http_json(url, headers=None):
    return json.loads(http_get(url, headers=headers).decode("utf-8"))


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
