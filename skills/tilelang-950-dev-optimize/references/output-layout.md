# Output layout

Use this structure under the target operator repository:

```text
optimization/<operator>/
├── TASK.md
├── case_selection/
│   ├── cases_candidates.csv
│   └── cases.csv
├── design/
│   └── DESIGN.md
├── baseline/
│   ├── precision.csv
│   └── profile/
│       ├── manifest.json
│       ├── summary.csv
│       └── raw/
├── analysis/
│   ├── BOTTLENECKS.md
│   └── CANDIDATES.md
├── iterations/
│   └── <candidate-id>/
│       ├── hypothesis.md
│       ├── changes.patch
│       ├── precision.csv
│       ├── profile/
│       │   ├── manifest.json
│       │   ├── summary.csv
│       │   └── raw/
│       ├── comparison.json
│       └── decision.md
└── FINAL_REPORT.md
```

Store generated compiler output or large profiler payloads outside version control when repository policy requires it, but keep stable paths or checksums in the evidence manifest. Do not copy framework or CANNBot source into this directory.

