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

## Results

The results summary (path in `project.md`) has this layout. `validate_e2e_plan.py <plan> --results <summary>`
checks it. Status words are defined in `references/glossary.md`. Evidence files go in `evidence/` next to the
summary, named `<ID>_<platform>_<n>.<ext>` (screenshot, UI-tree dump, the app's diagnostics file, a pulled result
file, a log). Every case PASS cites at least one of them by its path; a number read on the device goes in the cell
next to the file it was read from.

```markdown
# E2E results: <feature>, <YYYY-MM-DD>

**Build:** <version (build number)>
**Commit:** <sha, or "unknown (installed build)" with where the build came from>
**Devices:** <iPhone model, iOS x.y · Android model, Android x>
**Date:** <YYYY-MM-DD>
**Plan:** <path to this plan>

| ID | Platform | Status | Min | Evidence |
|---|---|---|---|---|
| READY | ios | PASS | <4> | <what was checked> |
| E1 | ios | <PASS · FAIL · BLOCKED · NOT RUN> | <minutes it took> | <numbers and evidence/E1_ios_1.png; BUG-n for a FAIL; the reason for BLOCKED or NOT RUN; every retry and its harness: cause> |

## Defects

### BUG-1: <title>
- **Case:** <E1 ios>
- **Build:** <version>
- **Device:** <model, OS>
- **Severity:** <S1 data loss or crash · S2 feature broken · S3 degraded · S4 cosmetic>
- **Steps:** <numbered, from a fresh state>
- **Expected:** <the plan's Expected>
- **Actual:** <numbers, what the screen showed>
- **Evidence:** <evidence/ paths: screenshot, logcat, diagnostics>
- **Harness ruled out by:** <screenshot at the failure, activity log, independent check of the file>

## Not verified
- <ID> <platform>: <why: every High case that is not PASS or FAIL on that platform opens a line like this>
- <anything else the run could not show, and why>

## Result files
- <per-run result files; aborted runs' result files deleted, their evidence kept for the `harness:` cause>

E2E: ios pass=<n> fail=<n> blocked=<n> not_run=<n> · android pass=<n> fail=<n> blocked=<n> not_run=<n>
```

The counts are over the cases, not the run steps.
