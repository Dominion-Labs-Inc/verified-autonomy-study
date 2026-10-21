"""Run the gate battery against a build of the gates and compare each verdict with the stated one.

Usage: python3 scripts/run_gate_battery.py <directory holding study_gates> <label>

Each case runs in a fresh workspace with a fresh RunGates. Acts listed under
'before' are judged and, when allowed, reported as executed; 'change' rewrites a
file on disk. Writes results/gate_battery_<label>.json and exits nonzero on any
difference from the stated verdicts. Clock times inside reasons are written as
{time}, so two runs of the same build produce identical files.
"""

import asyncio
import json
import os
import re
import sys
import tempfile
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fill(value, ws):
    if isinstance(value, str):
        return value.replace("{ws}", ws)
    if isinstance(value, dict):
        return {k: fill(v, ws) for k, v in value.items()}
    if isinstance(value, list):
        return [fill(v, ws) for v in value]
    return value


async def run_case(RunGates, battery, case):
    with tempfile.TemporaryDirectory() as tmp:
        ws = os.path.realpath(tmp)
        for name, content in battery["workspace"].items():
            Path(ws, name).write_text(content)
        gates = RunGates(ws)
        for step in case.get("before", []):
            if step[0] == "change":
                target = Path(ws, step[1])
                target.write_text(step[2])
                stamp = time.time() + 2
                os.utime(target, (stamp, stamp))
                continue
            tool, params = step[0], fill(step[1], ws)
            judgment = await gates.judge(tool, params)
            if judgment.verdict.value != "allow":
                return {"id": case["id"], "error": f"setup step {tool} was not allowed: {judgment.reason}"}
            gates.executed(tool, params)
        tool, params = case["act"][0], fill(case["act"][1], ws)
        judgment = await gates.judge(tool, params)
        got = [judgment.verdict.value, judgment.law_number]
        reason = re.sub(r"\b\d{2}:\d{2}:\d{2}\b", "{time}", judgment.reason.replace(ws, "{ws}"))
        return {"id": case["id"], "expect": case["expect"], "got": got,
                "match": got == case["expect"], "reason": reason}


def run_trace_case(RunGates, case):
    with tempfile.TemporaryDirectory() as tmp:
        ws = os.path.realpath(tmp)
        start = time.time()
        for name, (content, offset) in case["files"].items():
            target = Path(ws, name)
            target.write_text(content)
            os.utime(target, (start + offset, start + offset))
        gates = RunGates(ws)
        claims = case["claims"]
        proposal = types.SimpleNamespace(
            files_created=claims.get("files_created", []), files_modified=claims.get("files_modified", []),
            artifact_hashes=claims.get("artifact_hashes", {}), summary="", claimed_outputs={})
        tool_results = [dict(r, timestamp=start + r["timestamp"]) for r in case["tool_results"]]
        result = gates.verify_claim(proposal, "EXECUTION", tool_results)
        got = {"passed": bool(result.passed), "score": round(float(result.score), 4)}
        match = all(got[k] == v for k, v in case["expect"].items())
        failures = [f.replace(ws, "{ws}") for f in (result.hard_failures or [])]
        return {"id": case["id"], "expect": case["expect"], "got": got, "match": match, "hard_failures": failures}


def main():
    build, label = sys.argv[1], sys.argv[2]
    sys.path.insert(0, build)
    from study_gates import RunGates
    battery = json.loads((ROOT / "tests" / "gate_battery.json").read_text())
    results = [asyncio.run(run_case(RunGates, battery, case)) for case in battery["cases"]]
    results += [run_trace_case(RunGates, case) for case in battery.get("traceability", [])]
    matched = sum(bool(r.get("match")) for r in results)
    summary = {"label": label, "cases": len(results), "matched": matched, "results": results}
    out = ROOT / "results" / f"gate_battery_{label}.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for r in results:
        if not r.get("match"):
            print(f"{r['id']}: expected {r.get('expect')}, got {r.get('got')} | "
                  f"{r.get('reason') or r.get('error') or r.get('hard_failures')}")
    print(f"{matched} of {len(results)} cases match the stated verdicts")
    sys.exit(0 if matched == len(results) else 1)


if __name__ == "__main__":
    main()
