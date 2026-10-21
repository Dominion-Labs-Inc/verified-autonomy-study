"""Run the gate battery against a build of the gates and compare each verdict with the stated one.

Usage: python3 scripts/run_gate_battery.py <directory holding study_gates> <label>

Each case runs in a fresh workspace with a fresh RunGates. Acts listed under
'before' are judged and, when allowed, reported as executed; 'change' rewrites a
file on disk. Completion cases build each act's record with the gates' own record
builder, apply what the act did to the workspace, and give the check's re-run the
stated exit code, the same for every build. Writes results/gate_battery_<label>.json
and exits nonzero on any difference from the stated verdicts. Clock times inside
reasons are written as {time}, so two runs of the same build produce identical files.
"""

import asyncio
import json
import os
import re
import sys
import tempfile
import time
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


def records_for(case, ws, run_record, text_digest):
    """Each act's record, built by the gates' own builder, with what it did applied to the workspace."""
    for name, content in case["files"].items():
        Path(ws, name).write_text(content)
    records = []
    for tool, args, said in fill(case["acts"], ws):
        ran = {"success": said["success"], "error": said.get("error")}
        if said["success"]:
            output = {}
            if "wrote" in said:
                if said.get("lands", True):
                    Path(args["file_path"]).write_text(said["wrote"])
                output = {"file_path": args["file_path"], "content_digest": text_digest(said["wrote"])}
            elif tool == "delete_file":
                Path(args["path"]).unlink()
            elif tool == "read_file":
                text = Path(args["file_path"]).read_text()
                output = {"file_path": args["file_path"], "content": text, "size_bytes": len(text.encode("utf-8"))}
            ran["output"] = output
        records.append(run_record(tool, args, ran))
    for name, content in case.get("end", {}).items():
        Path(ws, name).write_text(content)
    return records


async def run_completion_case(gates_module, case):
    with tempfile.TemporaryDirectory() as tmp:
        ws = os.path.realpath(tmp)
        rerun = None
        if "rerun" in case:
            async def rerun(check, code=case["rerun"]):
                return {"exit_code": code, "seconds": 0.0}
        records = records_for(case, ws, gates_module.run_record, gates_module.text_digest)
        bar = case.get("verify_bar", gates_module.NO_DOUBT)
        got = await gates_module.RunGates(ws, rerun=rerun).completion(records, "fix the issue", bar)
        # Lyric's acceptance band: 0.95, raised toward 0.99 by caution.
        accept = 0.95 + 0.04 * (bar / 0.85)
        outcomes = {o["outcome"].replace(ws, "{ws}"):
                    "met" if o["posterior"] + 1e-9 >= accept else "not met" if o["against"] else "not confirmed"
                    for o in got["outcomes"]}
        result = {"done": got["done"], "outcomes": outcomes}
        return {"id": case["id"], "expect": case["expect"], "got": result, "match": result == case["expect"],
                "posterior": round(got["posterior"], 4),
                "issues": [i.replace(ws, "{ws}") for i in got["issues"]]}


def main():
    build, label = sys.argv[1], sys.argv[2]
    sys.path.insert(0, build)
    import study_gates
    battery = json.loads((ROOT / "tests" / "gate_battery.json").read_text())
    results = [asyncio.run(run_case(study_gates.RunGates, battery, case)) for case in battery["cases"]]
    results += [asyncio.run(run_completion_case(study_gates, case)) for case in battery["completion"]]
    matched = sum(bool(r.get("match")) for r in results)
    summary = {"label": label, "cases": len(results), "matched": matched, "results": results}
    out = ROOT / "results" / f"gate_battery_{label}.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for r in results:
        if not r.get("match"):
            print(f"{r['id']}: expected {r.get('expect')}, got {r.get('got')} | "
                  f"{r.get('reason') or r.get('error') or r.get('issues')}")
    print(f"{matched} of {len(results)} cases match the stated verdicts")
    sys.exit(0 if matched == len(results) else 1)


if __name__ == "__main__":
    main()
