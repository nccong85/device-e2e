# Changelog

All notable changes are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

- The results summary is a test completion report (CTFL v4.0.1 §5.3.2 and §5.5, ISO/IEC/IEEE 29119-3 §7.4):
  a **Tester** header line; *Summary* with a **Verdict** (`go`, `no-go`, `go with risks`) and each exit
  criterion met or not met; *Metrics*; Results cells of at most 400 characters with the detail under *Case log*;
  defect reports with Observed, Reporter, Priority (P1–P4), Status and Reproducibility; *Deviations and
  impediments*; *Residual risk* per H and M basis Ref; *Lessons learned*. Plans gain *Exit criteria* (X1 to X3).
  The device-tester hand-off adds a `VERDICT:` line and shows each bug's priority. `validate_e2e_plan.py` checks
  the verdict against the results (a criterion marked met that the results contradict; `go` with a criterion not
  met or a Ref at risk that nobody accepted). Older plans and results summaries fail until updated.
- Evidence capture: `harness/evidence.py` names files `evidence/<ID>_<platform>_<n>.<ext>` without overwriting
  an earlier run, and saves a screenshot, the UI tree, a screenshot series or a FAIL bundle. Both drivers gain
  `dump_tree`, `visible`, `log_mark` and `device_log` (Android: logcat since the mark; iOS: the app's crash
  reports through `devicectl`); `AndroidDriver.recording()` films the screen with `screenrecord`. The results
  check accepts `.ips` crash reports as evidence.
- Test design follows ISTQB CTFL v4.0.1, CTAL-TA v4.0 and CT-MAT v1.0 more closely (`references/test-design.md`):
  risk is Likelihood × Impact; the state × event table names target states and a coverage criterion by risk
  (all states, valid transitions, all transitions with a round trip); mobile events are grouped into partitions;
  base choice, pairwise from three factors, domain testing, a CRUD table, metamorphic oracles and an optional
  `EXPLORE` charter session; escaped defects (`ESC-n`) feed the next release plan.
- New section on cases that never run or run and cannot fail: *Oracle checks* (every High case is seen to fail
  once), no silent retry, a PASS far under its planned minutes, High gaps named under *Not verified*.
- `validate_e2e_plan.py` checks all of the above. Plans need the Likelihood and Impact columns, a
  `**Task:** · **Traces to:** · **Coverage:**` line above each state table, `<case> → <state>` cells and an
  *Oracle checks* row per High case; older plans fail until updated.
- Fixes from the first real run (e-Scanner 1.1.4 smoke on a Redmi 15C):
  - `--spec` accepts a change list without goal rows when the plan says **Mode:** release; the template adds
    `SMK-` and `REL-` basis Refs and an "unknown" commit for an installed build.
  - A High case that is BLOCKED or NOT RUN must open a bullet under *Not verified*; a passing mention of its ID
    inside another line no longer counts.
  - CRUD cells take `out: <reason>` for an operation that exists but the plan does not test.
  - The planned device time may fill at most 80 % of the Device budget.
  - An *Oracle checks* row marked `(in <case>)` is made to fail inside that case when DRY cannot build its state.
  - Aborted runs' result files are deleted but their evidence is kept for the retry's `harness:` cause.
  - `Evidence.failure()` defaults to the last minute; `log_mark(offset)`; Android `device_log` keeps only the
    app's lines and errors unless `full=True` (a full dump was about 2 MB).
  - `procs.py` no longer matches shells whose command line holds the text, so `--kill` cannot stop another
    session's shell.
  - New trap: compare UI labels case-insensitively (`SCAN` vs `Scan`).
- Review fixes:
  - The validator reads every section whose heading matches (a second `## State × event` or `## CRUD` was
    skipped), checks the platform in a *Not verified* line and in a defect's **Case:**, flags a results row for a
    platform the case is not planned on, and accepts Windows evidence paths, backticked IDs and a markdown link
    in **Plan:**. `(in <case>)` must name a case. The usage message prints the command line.
  - `recording()` no longer replaces the case's own failure when the pull fails, and always removes the phone's
    file. Android `visible()` uses the screen of the last dump, so landscape works. iOS crash-report times accept
    an offset. `procs.py` reads PowerShell output as UTF-8. The Windows test shim covers `Popen`.
  - Docs: `Evidence(root=<summary dir>/evidence)`; `procs.py` runs through Python; `EXPLORE` is optional; the
    READMEs list `EXPLORE` and non-Mac hosts for Android.
- Moved out of escanner-agent-kit into its own repository and marketplace (`device-e2e@device-e2e`).
- Dropped the hard dependency on `review-gate`; it is now a recommendation.
- `validate_e2e_plan.py --results`: a pulled PDF, a screen recording (`.mp4`, `.mov`), `.heic` or `.gif` counts as an evidence file.
- `validate_e2e_plan.py --results`: `NOT RUN: budget` and `BLOCKED: <reason>` in the Status cell are accepted, with the text after the colon as the reason.
- `validate_e2e_plan.py --results`: every case PASS must cite an evidence file (a path with a directory, e.g. `evidence/E1_ios_1.png`), and every cited evidence file, in the table or a `BUG-n` entry, must exist relative to the summary.
- The agent, playbook, glossary and results template keep evidence in `evidence/` next to the summary, named `<ID>_<platform>_<n>.<ext>`.

## 1.0.0

- First release, as part of escanner-agent-kit 1.0.0.
