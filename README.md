# Verified Autonomy Study

An empirical study of independent verification for autonomous software engineering agents. The study replays public runs of coding agents on SWE-bench Verified through two verification gates from the Lyric system, and compares each agent's own report of success with what its record and the projects' tests show.

**Status:** pre-registration. The analysis plan, sample sizes, labeling codebook, held out task split and submission inventory are committed before any run outcome or gate verdict is examined.

## Contents

| Path | What it holds |
| --- | --- |
| [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md) | Research questions, data, definitions, the adapter fidelity test, analysis and sample sizes |
| [`labels/codebook.md`](labels/codebook.md) | The labeling rules for RQ3 |
| [`data/tasks.csv`](data/tasks.csv) | The 500 SWE-bench Verified tasks |
| [`data/tasks_source.json`](data/tasks_source.json) | Dataset revision and cross check |
| [`data/task_split.csv`](data/task_split.csv) | Tuning and held out halves |
| [`data/submissions.csv`](data/submissions.csv) | Every Verified submission, its log structure and its status |
| [`data/submissions_source.json`](data/submissions_source.json) | The pinned commit and the inventory counts |
| [`results/sample_sizes.csv`](results/sample_sizes.csv) | Worst case margin of every planned proportion |
| [`scripts/`](scripts/) | The scripts that produce every file above |

## Reproduce

Python 3.9 or later, standard library only. Network access is needed for the first three targets.

```bash
make tasks          # data/tasks.csv, data/tasks_source.json
make split          # data/task_split.csv
make inventory      # data/submissions.csv, data/submissions_source.json
make sample-sizes   # results/sample_sizes.csv
make prereg         # all of the above, in order
```

`make split` and `make sample-sizes` need no network and reproduce their files exactly from the committed inputs.

## License

Everything in this repository is released under the [MIT License](LICENSE). The compiled build of the verification gates, added at release, carries its own license in `gates/`.
