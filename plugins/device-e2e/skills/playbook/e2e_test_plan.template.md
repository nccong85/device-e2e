# E2E test plan: <feature or release>

**Mode:** <feature | release> · **Spec:** <path> · **Build under test:** <version, commit (or "commit unknown":
an installed build whose commit cannot be read from the package)>
**Device budget:** <minutes> min · **Approved by:** <owner, date: the plan and the device time>

The procedure is `references/test-design.md`. Check with `validate_e2e_plan.py <this file> --spec <spec>` (a
release plan's spec is its change list, which has no goal rows; the release mode accepts that).
No `|` inside a cell.

## Test basis

Risk = Likelihood × Impact by the matrix in `references/test-design.md` step 2.

| Ref | Source | Item | Likelihood | Impact | Risk | Why this risk |
|---|---|---|---|---|---|---|
| G1 | spec §2 | <goal or acceptance criterion> | M | H | H | <what breaks, for whom; what makes it likely> |
| BUD-<name> | review_brief Part A | <budget the changed code can break> | M | M | M | <why> |
| CH-1 | change list / diff | <user-visible change or changed area> | H | M | H | <why> |
| ESC-1 | user report since last release | <bug that reached users> | M | M | M | <why a device test could have caught it> |
| SMK-<area> | release smoke area | <area every release must keep working: launch, import, search> | L | H | M | <why> |
| REL-<check> | release check | <upgrade over the last store build, config, store version string> | M | H | H | <why> |

## Factors

Rule: <each choice · base choice · pairwise (3+ factors)>, by the highest risk of the items it serves.

| Factor | Partitions (invalid ones too) | Base choice | Why the code path depends on it |
|---|---|---|---|
| <language> | <Latin, CJK> | <Latin> | <tokenizer splits CJK by character> |
| <Android maker> | <Pixel, Xiaomi> | <Pixel> | <the skin kills background work sooner> |

## State × event

Each cell: `<case> → <target state>`, `below: <file::name> → <state>`, `untested → <state>` (not with all
transitions) or `n/a: <reason>`. Events: one per partition of `references/test-design.md` step 4.

**Task:** <indexing> · **Traces to:** <G1> · **Coverage:** <all states · valid transitions · all transitions>

| State | Home | Lock | OS kill | User swipe | Upgrade |
|---|---|---|---|---|---|
| running | <E1 → running> | <E2 → running> | <E3 → running> | <E4 → paused> | <n/a: reason> |
| paused | <untested → paused> | <untested → paused> | <E6 → paused> | <n/a: reason> | <n/a: reason> |
| done | <below: file::name → done> | <n/a: reason> | <n/a: reason> | <n/a: reason> | <E5 → done> |

All transitions also needs a round trip:

| Sequence | Task | Path | Case |
|---|---|---|---|
| <SQ-1> | <indexing> | <running → Home → running → OS kill → relaunch → running> | <E3> |

## CRUD

One row per entity the change stores. Each cell: a case ID, `below: <file::name>`, `n/a: <reason>` (the action
does not exist) or `out: <reason>` (it exists, this plan does not test it; say so under *Not covered*).

| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| <document> | <E1> | <below: file::name> | <E6> | <E7> |

## Run steps

Planned once per platform, outside the cases, with a results row each.

| Step | What | Min |
|---|---|---|
| READY | cable or tunnel up, phone unlocked, WDA authorized, no old suite process (`<python> harness/procs.py <suite>`), owner reachable; record every phone setting the run will change (stay-awake, IME, language) so cleanup puts back what was there | <5> |
| DRY | one cheap case end to end, and each new assertion made to fail once (mutation check; a check marked `(in <case>)` fails inside that case instead) | <15> |
| DIAG | pull the app's diagnostics for the whole run; count failure events by kind | <5> |
| EXPLORE | <Explore the import of a 300-page PDF with leave and connectivity events to discover lost or repeated pages> (optional; one time-boxed session after the High cases) | <15> |

## Cases

`Min` is device minutes per platform; `Order` is run order (1 first, a cut run drops the highest). Cases that need
the same costly setup share it as one group (*Precondition* names the group), unless a failure in one would hide
the next. A shortened variant is its own row with its own Expected.

| ID | Traces to | Covers | Risk | Platforms | Min | Order | Precondition (proven by) | Steps | Expected (FAIL when) | How checked |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | G1 | ST-running×Home | H | both | <15> | <1> | <40-page fixture staged, progress < 50 % read before Home> | <import, Home at 10 pages, wait 60 s, reopen> | <coverage read on return > coverage read before Home; 40/40 within 120 s> | <diagnostics file count, UI tree> |

## Oracle checks

Every High case: how its check is made to fail once, before its result counts. One of `old build: <version>`,
`mutation: <expected value changed>`, `fault: <how the fault is made>`, `baseline: <relation>`. It runs in DRY,
unless it needs state only a case builds (a finished document, a full library): then add `(in <case>)` and make
it fail there, before that case's result is read; the marker ends the *Made to fail by* cell.

| Case | Made to fail by |
|---|---|
| <E1> | <mutation: expect 41/40 pages; the check fails> |

## Covered below e2e

| Ref or item | Test that proves it (file::name) |
|---|---|
| <G2> | <test/search/ranking_test.dart::ranks exact match first> |

## Not covered

| Ref or item | Why | Risk accepted by |
|---|---|---|
| <CH-3> | <no iPhone with a passcode-free setup> | <owner, date> |

## Exit criteria

What the results must show for the build to ship (CTFL §5.3.2: the completion report evaluates the build against
them). Keep these three; add a row for a criterion the spec or the owner sets.

| ID | Criterion |
|---|---|
| X1 | Every High case is PASS on each of its platforms |
| X2 | No S1 or S2 defect is open |
| X3 | Every H or M basis Ref the run did not prove is listed under *Residual risk* with who accepts it |

## Review checklist

- [ ] Every basis Ref is in a case, in *Covered below e2e*, or in *Not covered*; every case traces to a Ref.
- [ ] Each diff change maps to a basis Ref (release: the change list and the diff were both read).
- [ ] Risk follows Likelihood × Impact; Likelihood counts the change size, platform-only code and bug history.
- [ ] Every factor changes the code path; partitions, not values, invalid ones included; device and OS are
      factors where the code depends on them.
- [ ] Every State × event cell names a target state; the Coverage line meets the risk; a round trip for all
      transitions.
- [ ] Every entity the change stores has a CRUD row.
- [ ] Every High case has an Oracle check.
- [ ] Every Expected names the number or state that fails it; preconditions are proven, not assumed.
- [ ] Platforms follow the code: shared → both, one platform's layer → that platform.
- [ ] Release: confirmation cases ran red on the old build; one upgrade-over-data case.
- [ ] The total of Min is at most 80 % of the Device budget (the rest absorbs overruns: a UI-tree dump per poll
      costs seconds); Order puts High risk first; costly setup is shared, or the
      precondition says why a case needs its own.
- [ ] Every pushed-down test exists today (`file::name`), none "to be created".
- [ ] *Exit criteria* keeps X1 to X3; an added criterion names a number or a state that can fail it.

## Results

The results summary (path in `project.md`) is the test completion report (CTFL v4 §5.3.2, ISO/IEC/IEEE 29119-3
§7.4) and holds the defect reports (CTFL §5.5; 29119-3 calls them incident reports).
`validate_e2e_plan.py <plan> --results <summary>` checks it. Status words are defined in `references/glossary.md`.
Evidence files go in `evidence/` next to the summary, named `<ID>_<platform>_<n>.<ext>` (screenshot, UI-tree dump,
the app's diagnostics file, a pulled result file, a log). Every case PASS cites at least one of them by its path;
a number read on the device goes next to the file it was read from.

The reader decides from *Summary* and *Residual risk*; the rest is the record behind them. A Results cell holds
the deciding numbers and their files (at most 400 characters); the steps, timings and every other reading go
under *Case log*.

```markdown
# E2E results: <feature>, <YYYY-MM-DD>

**Build:** <version (build number)>
**Commit:** <sha, or "unknown (installed build)" with where the build came from>
**Devices:** <iPhone model, iOS x.y · Android model, Android x>
**Date:** <YYYY-MM-DD>
**Plan:** <path to this plan>
**Tester:** <who ran it: the device-tester agent, the session or the person>

## Summary

**Verdict:** <go · no-go · go with risks>: <one sentence: what the build can and cannot be trusted with>

| Exit criterion | Result | Because |
|---|---|---|
| X1 | <met · not met> | <the IDs that decide it> |
| X2 | <met · not met> | <BUG-n, or "no S1/S2 defect"> |
| X3 | <met · not met> | <the Refs under Residual risk> |

<Two or three sentences: what was tested, on what, and what the result means for the release.>

## Metrics

| Measure | ios | android |
|---|---|---|
| Cases planned / run (PASS or FAIL) | <5 / 5> | <5 / 4> |
| PASS · FAIL · BLOCKED · NOT RUN | <5 · 0 · 0 · 0> | <4 · 0 · 0 · 1> |
| Basis Refs proven / traced to a case | <6 / 7> | <6 / 7> |
| Defects S1 · S2 · S3 · S4 | <0 · 0 · 1 · 0> | <0 · 0 · 0 · 0> |
| Device minutes planned / used | <24 / 28.4> | <24 / 31> |

## Results

| ID | Platform | Status | Min | Evidence |
|---|---|---|---|---|
| READY | ios | PASS | <4> | <what was checked> |
| E1 | ios | <PASS · FAIL · BLOCKED · NOT RUN> | <minutes it took> | <the deciding numbers and evidence/E1_ios_1.png; BUG-n for a FAIL; the reason for BLOCKED or NOT RUN; every retry and its harness: cause> |

## Case log

### E1 ios
<the steps as run, the timings, every reading with its file; a retry and why>

## Defects

### BUG-1: <title>
- **Case:** <E1 ios>
- **Build:** <version>
- **Device:** <model, OS>
- **Observed:** <YYYY-MM-DD HH:MM, device time>
- **Reporter:** <the tester, as in the header>
- **Severity:** <S1 data loss or crash · S2 feature broken · S3 degraded · S4 cosmetic>
- **Priority:** <P1 fix before release · P2 fix in this release · P3 next release · P4 when convenient>
- **Status:** <open · deferred · duplicate of BUG-n · awaiting confirmation · closed · rejected>
- **Reproducibility:** <n of m attempts, from a fresh state>
- **Steps:** <numbered, from a fresh state>
- **Expected:** <the plan's Expected>
- **Actual:** <numbers, what the screen showed>
- **Evidence:** <evidence/ paths: screenshot, logcat, diagnostics>
- **Harness ruled out by:** <screenshot at the failure, activity log, independent check of the file>

## Deviations and impediments
- Time: <planned N min, used M min, of the B min Device budget>
- <ID platform: how the run differed from the plan (overran, cut, re-ordered, retried with its harness: cause)>
- Impediment: <what got in the way> → <the workaround, or "none: the case is BLOCKED">

## Residual risk

| Ref | Risk | Status | What is still at risk | Accepted by |
|---|---|---|---|---|
| G1 | H | proven: E1 PASS ios, android | <none> | <n/a> |
| CH-2 | M | <not proven: E4 NOT RUN android · failed: BUG-1 · below: <test> · not covered> | <what a user could still hit> | <owner, date, or "open: the owner decides"> |

## Not verified
- <ID> <platform>: <why: every High case that is not PASS or FAIL on that platform opens a line like this>
- <anything else the run could not show, and why>

## Lessons learned
- <what to change in the plan, the harness or project.md before the next run, with the number that showed it>

## Result files
- <per-run result files; aborted runs' result files deleted, their evidence kept for the `harness:` cause>

E2E: ios pass=<n> fail=<n> blocked=<n> not_run=<n> · android pass=<n> fail=<n> blocked=<n> not_run=<n>
```

The counts are over the cases, not the run steps. *Residual risk* has a row for every H and M basis Ref; `proven`
needs every case that traces to the Ref to be PASS on each of its platforms. The **Verdict** is `go` only when
every exit criterion is met and no Ref is left at risk without an owner's name; `no-go` when X1 or X2 is not met
because of a defect.
