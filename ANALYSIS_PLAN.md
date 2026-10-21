# Analysis plan

This plan was committed on October 21, 2026, before any run outcome or gate verdict was examined. The only logs read before this commit were the first 8 KB of one log file per submission, to classify the structure of each submission's logs. Any later change is recorded under [Deviations](#deviations), with its date and reason.

## 1. Research questions

| Question | Definition |
| --- | --- |
| RQ1 Claimed versus verified | Among runs that claim completion, the share whose task SWE-bench does not mark as resolved. |
| RQ2 Completion check | How well the completion check's verdict separates claiming runs that are resolved from claiming runs that are not. |
| RQ3 Action judgment | The share of actions the Constitution would block, redirect or hold, and the precision and misses of those judgments against hand labels. |
| RQ4 Human intervention | On held out tasks, the share of claiming runs that could be accepted without human review, and the share of those accepted runs that are not resolved. |

## 2. Data

### Tasks

The 500 tasks of SWE-bench Verified, listed in [`data/tasks.csv`](data/tasks.csv). [`data/tasks_source.json`](data/tasks_source.json) records the dataset, its revision and a cross check showing that both public releases of the dataset list the same 500 tasks.

### Submissions

[`data/submissions.csv`](data/submissions.csv) lists all 182 Verified submissions at a pinned commit of the SWE-bench experiments repository, recorded in [`data/submissions_source.json`](data/submissions_source.json). Each row gives the submission's agent, its published log location, the structure of its logs and its status.

| Status | Submissions | Reason |
| --- | --- | --- |
| Candidate, family A | 42 | mini-SWE-agent trajectory |
| Candidate, family B | 14 | SWE-agent trajectory |
| Candidate, family C | 35 | Chat transcript with tool calls |
| Excluded | 47 | Logs are free text, not a structured record of actions |
| Excluded | 27 | Structured logs outside the three adapter families |
| Excluded | 11 | No step by step logs published |
| Excluded | 6 | The published log location holds no files |

A candidate enters the study only when its family's adapter passes the fidelity test in section 4. A candidate that fails is excluded, and the reason is added to `data/submissions.csv`.

### Controlled subset

44 candidate submissions use one agent framework, mini-SWE-agent, with different models. Within this subset only the model varies, which separates model effects from framework effects.

### Handling of logs

Logs are streamed: each submission's logs are downloaded, processed and deleted. Only derived records are kept. Raw logs are not redistributed; each run is identified by its public location and a checksum.

## 3. Definitions

- **Run.** One submission's attempt at one task.
- **Action.** One command the agent executed, or one file edit it applied, as recorded in the run's log.
- **Claim of completion.** The run ends with the agent's own submission of its fix, as recorded in the log. Runs that end at a step limit, a cost limit, a timeout or an error make no claim and are reported separately. Each adapter documents the log field that records the submission for its family.
- **Resolved.** The task appears in the submission's resolved list in SWE-bench's own evaluation results, read at the pinned commit.

## 4. Adapters and the fidelity test

One adapter per family translates a run's log into the gates' inputs. Each action becomes an input to the Constitution, and a record for the completion check, built by the gates' own record builder from the tool the action maps to, its arguments and the result the log reports. A file edit states what the file should hold once it lands. A command's success is its exit status where the log records it; where a family's log does not, the adapter documents how success is read, and that rule is fixed before any run is translated. Paths inside the agent's environment are mapped to the rebuilt workspace. Adapters only translate; they never decide a verdict.

A family's adapter passes the fidelity test when all three checks hold:

1. **Completeness.** For every run in the family, the number of actions in the translated record equals the number counted in the raw log by an independent method, in the same order, with nothing added.
2. **Patch agreement.** For every run, the patch in the translated record equals the submission's published prediction for that task.
3. **Review.** In 20 runs drawn at random per family, a reviewer finds no action that was dropped, altered or invented.

## 5. Verification gates

The study uses two gates as they run inside the Lyric system, copied verbatim from a recorded commit and released as a compiled build identified by version and checksum.

| Gate | What it catches | What it returns |
| --- | --- | --- |
| Constitution | Edits to the controls that govern or halt the system; installing something to run again later, at startup and scheduling locations; taking privileges the boundary does not grant; arguments that leave their destination, such as path traversal, or carry a command into data, such as injection; acts that carry a key or name a file of keys; harm to an identifiable party, and destruction beyond a nameable bound; destroying the record of what happened, or writing code whose behavior cannot be read from the code; acting on a person without their authorization; acting on a file without a current reading of it; irreversible acts on declared sensitive targets, which are redirected to a recoverable form | Allow, replan, redirect or block. The checks run in a fixed order and the first that applies decides. An action that cannot be judged is blocked |
| Completion check | Whether every outcome a run was expected to leave true holds: each file an act wrote holds what the act stated, each file it removed is gone, and the latest check run in each working directory passes when run again in a disposable copy of the end state. Edits made through the shell are confirmed by the check that passes where they were made. Each outcome is a belief moved by the act's own report and by a fresh observation; the run's belief is that of its weakest outcome | Done or not done, and each outcome as met (believed past the acceptance band), not met (evidence against it) or not confirmed (nothing fresh observed it) |

**Scope.** Two of the Constitution's checks read the reason the Lyric system recorded for its own acts: alignment, and the transparency account. Outside agents have no such record, so those two checks are not applied. Every other check runs in the Constitution's own order. The Constitution is attached to its threat sense, as in the Lyric system. Three providers read the Lyric system's own state (self perception, rule evidence and a concept taxonomy); an outside agent's workspace holds none of it, so they are not attached. The completion check runs a check again where the agent's acts ran: the one part of it that says where the copy of the end state comes from is replaced by the study's, described under Workspaces.

**Acceptance band.** The completion check accepts a run as done when its belief reaches 0.95, the Lyric system's band with no standing doubt. The band at its most cautious, 0.99, is reported alongside as a sensitivity analysis.

**Blindness.** The gates never receive SWE-bench's evaluation tests, test results or resolution status. A check is run again with the run's own patch applied, never with SWE-bench's test patch.

**Standing.** Every act is judged on behalf of the task's owner, not as the Lyric system's own work: an agent fixing an issue acts on a project that is not its own.

**Checks of the copy.** [`tests/gate_battery.json`](tests/gate_battery.json) states the outcome for 26 acts and 17 runs, each written from the gates' documented checks before it was run. [`scripts/run_gate_battery.py`](scripts/run_gate_battery.py) runs the battery against any build of the gates and writes its results to `results/`.

**Workspaces.** The completion check observes files on disk in a workspace rebuilt from the task's repository at its base commit plus the run's patch. A check is run again in the task's SWE-bench image with the run's patch applied, as SWE-bench's own harness applies it, without network access, and is stopped at the time limit the agent's framework gave its commands. Images are pulled one task at a time and deleted after that task's runs.

## 6. Held out tasks

[`data/task_split.csv`](data/task_split.csv) divides the 500 tasks into a tuning half and a held out half of 250 each. Each task is ranked by the SHA-256 of a fixed salt joined to its identifier ([`scripts/split_tasks.py`](scripts/split_tasks.py)). Any rule for accepting a run without review is fixed on the tuning half and measured only on the held out half.

## 7. Analysis

| Question | Measure | Reported for | Interval |
| --- | --- | --- | --- |
| RQ1 | Share of claiming runs not resolved | Each submission, each framework, the controlled subset, all candidates | Wilson score interval per submission; bootstrap over tasks for pooled figures |
| RQ2 | Sensitivity, specificity and precision of the not done verdict for unresolved claiming runs; the share of claiming runs with an outcome not confirmed, by kind of outcome | Each framework and all candidates | Wilson score interval; bootstrap over tasks |
| RQ3 | Share of actions flagged, by verdict; precision of flagged actions; misses among allowed actions | All candidates | Bootstrap over runs for prevalence; Wilson score interval for labeled samples |
| RQ4 | Share of claiming runs accepted without review; share of accepted runs not resolved | Held out half, each framework and all candidates | Bootstrap over tasks |

**Acceptance rule for RQ4.** A claiming run is accepted without review when the completion check decides it is done and the Constitution blocks none of its actions. If an alternative rule is considered, such as a different acceptance band, it is chosen on the tuning half only.

**Bootstrap.** 10,000 resamples of tasks (or runs, where stated), with the seed recorded in the analysis script. The same 500 tasks recur in every submission, so pooled intervals resample tasks rather than runs.

## 8. Sample sizes

[`results/sample_sizes.csv`](results/sample_sizes.csv), produced by [`scripts/sample_sizes.py`](scripts/sample_sizes.py), gives the worst case margin of each planned proportion: the half width of the 95 percent Wilson score interval at a true rate of 50 percent.

| Quantity | n | Worst case margin |
| --- | --- | --- |
| RQ1, per submission | 500 | plus or minus 4.4 points |
| RQ1, all candidate runs | 45,500 | plus or minus 0.5 points, before clustering |
| RQ3, precision of flagged actions | 400 | plus or minus 4.9 points |
| RQ3, misses among allowed actions | 400 | plus or minus 4.9 points |

## 9. Labeling

RQ3 is the only question that needs hand labels. 400 actions the Constitution flags and 400 it allows are drawn at random from all candidate runs, at most 5 per run. Actions are ranked by the SHA-256 of a fixed salt joined to the action's identifier, so the sample is fixed by the data and the salt alone.

Each sampled action is labeled under [`labels/codebook.md`](labels/codebook.md).

1. **First pass.** An AI model labels all 800 actions against the codebook, each with a one line reason.
2. **Second pass.** The author labels a random 150 of the 800 without seeing the first labels.
3. **Agreement.** Cohen's kappa on the 150, with a bootstrap interval.
4. **Disagreements.** Each is resolved by discussion. Both original labels and the resolution are kept in `labels/labels.csv`.
5. **Disclosure.** The paper states who labeled each pass and with what tools.

## 10. Pilot

Before the full run, one candidate submission is run on 50 tasks drawn from the tuning half. The pilot confirms that logs parse, that workspaces rebuild, and that every action and claim receives a verdict. Every action and run in the pilot is also judged by the Lyric system's own gates at the recorded commit, and the full run starts only if every judgment is identical. The pilot's numbers are never reported as findings.

## Deviations

**October 21, 2026, before any run outcome, gate verdict or label was examined.** Copying the gates from the Lyric system showed two statements in this plan to be inaccurate. Both were corrected.

1. Section 5 listed the Constitution's checks incompletely, and said removals are redirected to a recoverable form in general. In the copied code, the redirect applies only to irreversible acts on declared sensitive targets, and the Constitution also checks privileges, keys, harm to a party, destruction of records and acts aimed at a person. The table now lists what the code checks. Two checks read recorded reasons, not one, and neither is applied.
2. Category 3 of the codebook treated deleting any file that existed before the run as unrecoverable. Files under version control can be restored, so the category now covers only what cannot be restored.
3. Two additions. Every act is judged on behalf of the task's owner (section 5). The pilot now requires the study's gates and the Lyric system's own gates to agree on every judgment before the full run (section 10).

**October 21, 2026, before any run outcome, gate verdict or label was examined.** The second gate was replaced.

4. The traceability gate named in sections 1, 4, 5 and 7 is never called inside the Lyric system, and it was removed from the system. RQ2 and the acceptance rule for RQ4 now use the check the Lyric system uses to decide whether its own work is done. Preparing it showed four defects in that check, each corrected in the Lyric system, with tests, before it was copied: a written file was confirmed by its presence alone; a success could hide a later failure on the same resource; a check's success was taken from the log without running it again; and confirmations of one part of the work could outvote the failure of another. The gates are copied from commit 3f72de7c, and the battery's 5 claims are replaced by 17 runs.
5. To size the run, the time to re-run a check was measured on one task from the tuning half (django__django-10097) for five submissions. Only durations were recorded, never what a check returned. Pulling the task's image took 174 seconds, and each re-run took 1 to 2 seconds.
