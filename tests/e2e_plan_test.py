import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BIN = HERE / "plugins/device-e2e/bin/validate_e2e_plan.py"
TEMPLATE = HERE / "plugins/device-e2e/skills/playbook/e2e_test_plan.template.md"

passed = 0
failed = 0


def check(name, cond, out=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {name}")
        if out:
            print("  " + "\n  ".join(out.splitlines()[:6]))


WORK = Path(tempfile.mkdtemp(prefix="e2e_plan_"))
SPEC = WORK / "spec.md"
SPEC.write_text("""## 2. Goals & Non-Goals
| # | Goal | Acceptance criterion |
|---|------|------|
| G1 | indexing resumes after Home | coverage grows in background |
| G2 | results ranked | unit test |
""", encoding="utf-8")

PLAN = """# E2E test plan: resume

**Device budget:** 150 min · **Approved by:** owner, 2026-10-18

## Test basis

| Ref | Source | Item | Likelihood | Impact | Risk | Why this risk |
|---|---|---|---|---|---|---|
| G1 | spec §2 | resumes after Home | M | H | H | every large import |
| G2 | spec §2 | ranking | L | L | L | pure Dart |
| BUD-1s | review_brief Part A | first result within 1 s | M | M | M | user waits |
| CH-1 | diff | Android Otsu fix | H | L | M | Android only |

## Factors

| Factor | Partitions | Why the code path depends on it |
|---|---|---|
| language | Latin, CJK | tokenizer |

## State × event

**Task:** indexing · **Traces to:** G1 · **Coverage:** all transitions

| State | Home | OS kill |
|---|---|---|
| running | E1 → running | E2 → running |
| done | below: index_test.dart::done stays done → done | n/a: nothing to resume |

| Sequence | Task | Path | Case |
|---|---|---|---|
| SQ-1 | indexing | running → Home → running → OS kill → relaunch → running | E2 |

## CRUD

| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| document | E1 | below: doc_test.dart::reads back | n/a: no edit in this change | below: doc_test.dart::delete removes file |

## Run steps

| Step | What | Min |
|---|---|---|
| READY | unlocked, WDA up | 5 |
| DRY | one cheap case | 10 |
| DIAG | pull diagnostics | 5 |

## Oracle checks

| Case | Made to fail by |
|---|---|
| E1 | mutation: expect coverage on return > 40/40; the check fails |
| E2 | fault: relaunch without waiting; 40/40 not reached |

## Cases

| ID | Traces to | Covers | Risk | Platforms | Min | Order | Precondition (proven by) | Steps | Expected (FAIL when) | How checked |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | G1, BUD-1s | ST-running×Home, BUD-1s | H | both | 15 | 1 | progress 10/40 read before Home | Home, wait 60 s, reopen | coverage on return > coverage before Home; first result ≤ 1 000 ms | diagnostics file |
| E2 | G1 | ST-running×OSkill | H | both | 15 | 2 | progress 10/40 read before kill | am kill, relaunch | 40/40 within 120 s of relaunch | UI tree |
| E3 | CH-1 | EP-scanned-image | M | android | 10 | 3 | scanned JPG staged | import, search a word | the word is found on page 1 | UI tree |

## Covered below e2e

| Ref or item | Test that proves it (file::name) |
|---|---|
| G2 | test/search/ranking_test.dart::exact match first |

## Not covered

| Ref or item | Why | Risk accepted by |
|---|---|---|
| E3 ios | Android-only code | owner, 2026-10-18 |
"""

RESULTS = """# Results

**Build:** 1.1.4 (57)
**Commit:** abc1234
**Devices:** iPhone 13, iOS 18.6 · Redmi 15C, Android 15
**Date:** 2026-10-18
**Plan:** docs/plan.md

| ID | Platform | Status | Evidence |
|---|---|---|---|
| READY | ios | PASS | unlocked, WDA 200 |
| READY | android | PASS | adb device |
| DRY | ios | PASS | E1 dry, assertion mutated → FAIL |
| DRY | android | PASS | same |
| DIAG | ios | PASS | 0 failure events |
| DIAG | android | PASS | 0 failure events |
| E1 | ios | PASS | 12/40 → 31/40, 640 ms, `evidence/E1_ios_1.png` |
| E1 | android | PASS | 9/40 → 28/40, 810 ms, evidence/E1_android_1.xml |
| E2 | ios | BLOCKED | indexing done before kill (40/40) |
| E2 | android | FAIL | BUG-1, 10/40 after 120 s, logs/e2.txt |
| E3 | android | NOT RUN | no scanned fixture on this phone |

## Defects

### BUG-1: indexing does not resume after OS kill
- **Case:** E2 android
- **Build:** 1.1.4 (57)
- **Device:** Redmi 15C, Android 15
- **Severity:** S2 feature broken
- **Steps:** 1. import 40 pages 2. Home at 10 3. am kill 4. relaunch
- **Expected:** 40/40 within 120 s
- **Actual:** 10/40 after 120 s
- **Evidence:** logs/e2.txt
- **Harness ruled out by:** logcat shows am_proc_died then wm_on_resume

## Not verified
- E2 ios: indexing finished before the kill, so resume after OS kill is not shown on iOS

E2E: ios pass=1 fail=0 blocked=1 not_run=0 · android pass=1 fail=1 blocked=0 not_run=1
"""


for f in ("evidence/E1_ios_1.png", "evidence/E1_android_1.xml", "logs/e2.txt", "evidence/E1_ios_2.pdf", "evidence/E1_ios_3.mp4"):
    (WORK / f).parent.mkdir(parents=True, exist_ok=True)
    (WORK / f).write_text("x")


def run(plan, *args):
    p = WORK / "docs" / "plan.md"; p.parent.mkdir(exist_ok=True)
    p.write_text(plan, encoding="utf-8")
    extra = []
    for a in args:
        if a in ("--spec", "--results"):
            extra.append(a)
        elif isinstance(a, str) and a.startswith("RES:"):
            r = WORK / f"res{len(extra)}.md"
            r.write_text(a[4:], encoding="utf-8")
            extra.append(str(r))
        else:
            extra.append(str(a))
    out = subprocess.run([sys.executable, str(BIN), str(p), *extra], capture_output=True, encoding="utf-8")
    return out.returncode, out.stdout + out.stderr


def expect(name, want, plan, *args, pattern=None):
    code, out = run(plan, *args)
    check(f"{name}: want exit {want}, got {code}", code == want, out)
    if pattern:
        check(f"{name}: output lacks '{pattern}'", pattern in out, out)


expect("good plan", 0, PLAN, "--spec", SPEC, "--results", "RES:" + RESULTS)

# 1. a spec goal the plan never lists
expect("missing goal", 1, PLAN.replace("| G2 | spec §2 | ranking | L | L | L | pure Dart |\n", "")
       .replace("| G2 | test/search", "| X | test/search"), "--spec", SPEC, pattern="spec goal G2 is not in Test basis")
# 2. a basis Ref with no case, no lower test, no Not covered line
expect("orphan ref", 1, PLAN.replace("| G2 | test/search/ranking_test.dart::exact match first |\n", ""),
       pattern="Test basis G2 has no case")
expect("case traces outside basis", 1, PLAN.replace("| E3 | CH-1 |", "| E3 | CH-9 |"),
       pattern="traces to CH-9, which is not a Test basis Ref")
expect("pushed down without a test", 1, PLAN.replace("test/search/ranking_test.dart::exact match first", "unit tests"),
       pattern="Covered below e2e G2: name the test")
expect("pushed down to a file, no test name", 1, PLAN.replace("ranking_test.dart::exact match first", "ranking_test.dart (exact match)"),
       pattern="Covered below e2e G2: name the test")
expect("pushed down to a test not written yet", 1, PLAN.replace("::exact match first", "::exact match first (to be created)"),
       pattern="the test is not written yet")
expect("state cell below without file::name", 1, PLAN.replace("below: index_test.dart::done stays done → done", "below: index_test.dart → done"),
       pattern="'below:' must name a test that exists")
expect("not covered without reason", 1, PLAN.replace("| E3 ios | Android-only code |", "| E3 ios | |"),
       pattern="Not covered E3 ios: no reason")
# 3. case cells
expect("weak oracle", 1, PLAN.replace("40/40 within 120 s of relaunch", "indexing eventually finishes"),
       pattern="E2: Expected 'eventually' cannot fail")
expect("weak oracle >= before", 1, PLAN.replace("40/40 within 120 s of relaunch", "coverage ≥ before"),
       pattern="cannot fail")
expect("duplicate id", 1, PLAN.replace("| E3 | CH-1 |", "| E2 | CH-1 |"), pattern="case ID E2 used twice")
expect("bad platform", 1, PLAN.replace("| M | android | 10 |", "| M | web | 10 |"),
       pattern="E3: Platforms must be")
expect("unfilled slot", 1, PLAN.replace("| diagnostics file |", "| <how> |"), pattern="E1: 'how checked' is empty")
# 4. redundancy
expect("redundant case", 1, PLAN.replace("| E3 | CH-1 | EP-scanned-image |", "| E3 | CH-1 | ST-running×Home |"),
       pattern="E3 is redundant")
# 5. state × event
expect("empty state cell", 1, PLAN.replace("| running | E1 → running | E2 → running |", "| running | E1 → running | |"),
       pattern="[running × os kill] is empty")
expect("n/a without reason", 1, PLAN.replace("n/a: nothing to resume", "n/a"), pattern="needs ': <reason or test>'")
expect("state cell names no case", 1, PLAN.replace("| running | E1 → running | E2 → running |", "| running | E1 → running | E9 → running |"),
       pattern="E9 is not a case ID")
# 6. results
expect("planned id missing from results", 1, PLAN, "--results", "RES:" + RESULTS.replace("| E3 | android | NOT RUN | no scanned fixture on this phone |\n", ""),
       pattern="E3 android: planned but has no row")
expect("blocked without reason", 1, PLAN, "--results", "RES:" + RESULTS.replace("| BLOCKED | indexing done before kill (40/40) |", "| BLOCKED | |"),
       pattern="E2 ios: BLOCKED with no reason")
expect("result outside the plan", 1, PLAN, "--results", "RES:" + RESULTS.replace("\n\n## Defects", "\n| X1 | ios | PASS | found a bug |\n\n## Defects"),
       pattern="X1 is not in the plan")
expect("bad status", 1, PLAN, "--results", "RES:" + RESULTS.replace("| E1 | ios | PASS |", "| E1 | ios | PASS (quick) |"),
       pattern="is not PASS, FAIL, BLOCKED or NOT RUN")
expect("no results table", 1, PLAN, "--results", "RES:# nothing\n", pattern="no results table")
# 7. budget and run steps
expect("over budget", 1, PLAN.replace("**Device budget:** 150 min", "**Device budget:** 60 min"),
       pattern="planned device time 110 min exceeds the Device budget of 60 min")
expect("no budget line", 1, PLAN.replace("**Device budget:** 150 min · ", ""), pattern="no **Device budget:**")
expect("missing run step", 1, PLAN.replace("| DIAG | pull diagnostics | 5 |\n", ""), pattern="run step DIAG is not planned")
expect("min not a number", 1, PLAN.replace("| both | 15 | 2 |", "| both | ~15 | 2 |"), pattern="E2: Min must be a number")
expect("order not a number", 1, PLAN.replace("| both | 15 | 2 |", "| both | 15 | high |"), pattern="E2: Order must be")
# 8. results header, defects, hand-off counts
expect("header slot", 1, PLAN, "--results", "RES:" + RESULTS.replace("**Commit:** abc1234", "**Commit:** <sha>"),
       pattern="header **Commit:** is missing")
expect("results name another plan", 1, PLAN, "--results", "RES:" + RESULTS.replace("docs/plan.md", "docs/other_plan.md"),
       pattern="does not name plan.md")
expect("run step row missing", 1, PLAN, "--results", "RES:" + RESULTS.replace("| DIAG | android | PASS | 0 failure events |\n", ""),
       pattern="DIAG android: planned but has no row")
expect("FAIL without a bug", 1, PLAN, "--results", "RES:" + RESULTS.replace("| FAIL | BUG-1, ", "| FAIL | "),
       pattern="E2 android: FAIL cites no BUG-n")
expect("FAIL cites an unknown bug", 1, PLAN, "--results", "RES:" + RESULTS.replace("| FAIL | BUG-1, ", "| FAIL | BUG-7, "),
       pattern="BUG-7 has no entry under Defects")
expect("defect field empty", 1, PLAN, "--results", "RES:" + RESULTS.replace("- **Harness ruled out by:** logcat shows am_proc_died then wm_on_resume", "- **Harness ruled out by:**"),
       pattern="BUG-1: field **Harness ruled out by:** is missing")
expect("bad severity", 1, PLAN, "--results", "RES:" + RESULTS.replace("S2 feature broken", "high"), pattern="Severity must be S1 to S4")
expect("defect names another case", 1, PLAN, "--results", "RES:" + RESULTS.replace("- **Case:** E2 android", "- **Case:** E1 android"),
       pattern="BUG-1: **Case:** does not name E2 android")
expect("hand-off counts differ", 1, PLAN, "--results", "RES:" + RESULTS.replace("android pass=1 fail=1", "android pass=2 fail=0"),
       pattern="E2E: line android counts differ")
expect("PASS with only words", 1, PLAN, "--results", "RES:" + RESULTS.replace(", `evidence/E1_ios_1.png`", ""),
       pattern="E1 ios: PASS cites no evidence file")
expect("PASS cites a missing file", 1, PLAN, "--results", "RES:" + RESULTS.replace("E1_android_1.xml", "E1_android_9.xml"),
       pattern="evidence file evidence/E1_android_9.xml does not exist")
expect("defect cites a missing file", 1, PLAN, "--results", "RES:" + RESULTS.replace("- **Evidence:** logs/e2.txt", "- **Evidence:** logs/e9.txt"),
       pattern="BUG-1: evidence file logs/e9.txt does not exist")
# a pulled result file or a screen recording is evidence too
expect("PASS cites a pulled PDF", 0, PLAN, "--results", "RES:" + RESULTS.replace("`evidence/E1_ios_1.png`", "evidence/E1_ios_2.pdf"))
expect("PASS cites a recording", 0, PLAN, "--results", "RES:" + RESULTS.replace("`evidence/E1_ios_1.png`", "evidence/E1_ios_3.mp4"))
expect("PASS cites a missing PDF", 1, PLAN, "--results", "RES:" + RESULTS.replace("`evidence/E1_ios_1.png`", "evidence/E1_ios_9.pdf"),
       pattern="evidence file evidence/E1_ios_9.pdf does not exist")
# the agent writes `NOT RUN: budget`; the reason may sit in the Status cell
expect("NOT RUN: reason in the status cell", 0, PLAN, "--results", "RES:" + RESULTS.replace("| NOT RUN | no scanned fixture on this phone |", "| NOT RUN: budget | |"))
expect("BLOCKED: reason in the status cell", 0, PLAN, "--results", "RES:" + RESULTS.replace("| BLOCKED | indexing done before kill (40/40) |", "| BLOCKED: indexing done before kill | |"))
expect("NOT RUN: with no reason anywhere", 1, PLAN, "--results", "RES:" + RESULTS.replace("| NOT RUN | no scanned fixture on this phone |", "| NOT RUN: | |"),
       pattern="E3 android: NOT RUN with no reason")
expect("PASS: is still not a status", 1, PLAN, "--results", "RES:" + RESULTS.replace("| E1 | ios | PASS |", "| E1 | ios | PASS: quick |"),
       pattern="is not PASS, FAIL, BLOCKED or NOT RUN")
expect("no hand-off line", 1, PLAN, "--results", "RES:" + RESULTS.replace("E2E: ios", "ios"), pattern="no E2E: hand-off line")

# risk = likelihood × impact
expect("risk not the matrix", 1, PLAN.replace("| M | H | H | every large import |", "| L | M | H | every large import |"),
       pattern="G1: Likelihood L × Impact M is Risk L, not H")
expect("no likelihood column", 1, PLAN.replace("| Likelihood | Impact | Risk |", "| Prob | Impact | Risk |"),
       pattern="no Likelihood and Impact columns")
# state × event: target states and coverage criteria
expect("cell without target state", 1, PLAN.replace("| E1 → running |", "| E1 |"), pattern="write '<case> → <target state>'")
expect("target not a state", 1, PLAN.replace("| E1 → running |", "| E1 → paused |"),
       pattern="target state 'paused' is not a row")
expect("no coverage line", 1, PLAN.replace("**Task:** indexing · **Traces to:** G1 · **Coverage:** all transitions\n", ""),
       pattern="no '**Task:** <name>")
expect("coverage below the risk", 1, PLAN.replace("**Coverage:** all transitions", "**Coverage:** valid transitions"),
       pattern="so **Coverage:** must be at least all transitions")
expect("all transitions with an untested cell", 1, PLAN.replace("| E2 → running |", "| untested → running |"),
       pattern="all transitions leaves no cell 'untested'")
expect("all transitions without a round trip", 1, PLAN.replace("| SQ-1 | indexing |", "| SQ-1 | export |"),
       pattern="needs a round trip")
low = PLAN.replace("| M | H | H | every large import |", "| L | L | L | every large import |").replace(
    "| H | both | 15 | 1 |", "| L | both | 15 | 1 |").replace("| H | both | 15 | 2 |", "| L | both | 15 | 2 |")
expect("valid transitions: untested self-loop is fine", 0,
       low.replace("**Coverage:** all transitions", "**Coverage:** valid transitions").replace("| E2 → running |", "| untested → running |"))
two_states = low.replace("**Coverage:** all transitions", "**Coverage:** valid transitions").replace(
    "| running | E1 → running | E2 → running |", "| running | E1 → running | untested → done |")
expect("valid transitions: untested state change", 1, two_states, pattern="valid transitions needs a case for it")
expect("all states: a state never reached", 1, low.replace("**Coverage:** all transitions", "**Coverage:** all states").replace(
    "| done | below: index_test.dart::done stays done → done |", "| done | untested → done |"), pattern="no case starts in or reaches 'done'")
# CRUD
expect("CRUD empty cell", 1, PLAN.replace("| document | E1 |", "| document | |"), pattern="CRUD [document × create] is empty")
expect("CRUD below without a test", 1, PLAN.replace("below: doc_test.dart::reads back", "below: unit tests"),
       pattern="'below:' must name a test")
# oracle checks
expect("High case without an oracle check", 1, PLAN.replace("| E2 | fault: relaunch without waiting; 40/40 not reached |\n", ""),
       pattern="E2 is High risk but has no Oracle checks row")
expect("oracle check of an unknown kind", 1, PLAN.replace("fault: relaunch", "looked at it: relaunch"),
       pattern="Oracle checks E2: say how the check fails once")
expect("weak word suitable", 1, PLAN.replace("40/40 within 120 s of relaunch", "a suitable number of pages"),
       pattern="Expected 'suitable' cannot fail")
# EXPLORE run step
expect("explore with a charter", 0, PLAN.replace("| DIAG | pull diagnostics | 5 |", "| DIAG | pull diagnostics | 5 |\n| EXPLORE | Explore import with leave events to discover lost pages | 5 |"),
       "--results", "RES:" + RESULTS.replace("| DIAG | ios | PASS | 0 failure events |", "| DIAG | ios | PASS | 0 failure events |\n| EXPLORE | ios | PASS | nothing new |\n| EXPLORE | android | PASS | nothing new |"))
expect("explore without a charter", 1, PLAN.replace("| DIAG | pull diagnostics | 5 |", "| DIAG | pull diagnostics | 5 |\n| EXPLORE | poke around | 5 |"),
       pattern="state the charter")
# results: cases that ran without running, retries, High gaps
expect("PASS after a silent retry", 1, PLAN, "--results", "RES:" + RESULTS.replace("640 ms,", "640 ms, passed on retry,"),
       pattern="E1 ios: PASS after a retry")
expect("PASS after a retry with its harness cause", 0, PLAN, "--results", "RES:" + RESULTS.replace("640 ms,", "640 ms, retry, harness: WDA session expired,"))
timed = RESULTS.replace("| ID | Platform | Status | Evidence |\n|---|---|---|---|", "| ID | Platform | Status | Min | Evidence |\n|---|---|---|---|---|")
import re as _re
timed = _re.sub(r"^(\| \w+ \| \w+ \| [A-Z ]+ \|)", r"\1 14 |", timed, flags=_re.M)
expect("results with a Min column", 0, PLAN, "--results", "RES:" + timed)
expect("PASS far under its planned minutes", 1, PLAN, "--results", "RES:" + timed.replace("| E1 | ios | PASS | 14 |", "| E1 | ios | PASS | 2 |"),
       pattern="E1 ios: PASS in 2 of 15 planned min")

expect("High case BLOCKED and not in Not verified", 1, PLAN, "--results", "RES:" + RESULTS.replace("- E2 ios: indexing", "- the iOS run: indexing"),
       pattern="E2 ios: High risk and BLOCKED; open a line under '## Not verified'")
expect("High case only mentioned inside another Not verified line", 1, PLAN, "--results",
       "RES:" + RESULTS.replace("- E2 ios: indexing", "- the iOS run (E2 too): indexing"),
       pattern="E2 ios: High risk and BLOCKED; open a line")
expect("High case named in bold at the start of a Not verified line", 0, PLAN, "--results",
       "RES:" + RESULTS.replace("- E2 ios: indexing", "- **E2** ios: indexing"))

# budget slack: the plan may fill at most 80 % of the budget
expect("budget without slack", 1, PLAN.replace("**Device budget:** 150 min", "**Device budget:** 120 min"),
       pattern="planned device time 110 min leaves less than 20% of the 120 min Device budget")

# --spec with a release plan: a change list has no goal rows
(WORK / "whats_new.md").write_text("- faster search\n- camera modes\n", encoding="utf-8")
expect("feature plan against a spec without goals", 1, PLAN, "--spec", WORK / "whats_new.md", pattern="no goal rows")
expect("release plan against a change list without goals", 0,
       PLAN.replace("**Device budget:**", "**Mode:** release\n\n**Device budget:**", 1), "--spec", WORK / "whats_new.md")

# CRUD 'out:' = applies but not tested here; state cells keep 'untested'
expect("CRUD out with a reason", 0, PLAN.replace("n/a: no edit in this change", "out: rename is not in this smoke"))
expect("CRUD out without a reason", 1, PLAN.replace("n/a: no edit in this change", "out"), pattern="needs ': <reason>'")
expect("state cell does not take out", 1, PLAN.replace("n/a: nothing to resume", "out: later"),
       pattern="'untested → <state>' or 'n/a: <reason>'")

# weak '≥ before' gets a concrete hint
expect("≥ before hint", 1, PLAN.replace("40/40 within 120 s", "coverage ≥ before", 1), pattern="write '> the value read before'"),

# a second section with the same heading is checked too
expect("second state section is checked", 1, PLAN + """
## State × event: export

**Task:** export · **Traces to:** G1 · **Coverage:** all states

| State | Home |
|---|---|
| idle | E9 → nowhere |
""", pattern="E9 is not a case ID")
expect("second CRUD section is checked", 1, PLAN + "\n## CRUD\n\n| Entity | Create | Read | Update | Delete |\n|---|---|---|---|---|\n| page | | E1 | E1 | E1 |\n",
       pattern="CRUD [page × create] is empty")

# results: platform-exact Not verified, rows only for planned platforms, Windows paths, links, defect case
expect("Not verified names the case on the wrong platform", 1, PLAN, "--results",
       "RES:" + RESULTS.replace("- E2 ios: indexing", "- E2 android: indexing"), pattern="E2 ios: High risk and BLOCKED")
expect("Not verified with the ID in backticks", 0, PLAN, "--results", "RES:" + RESULTS.replace("- E2 ios: indexing", "- `E2` ios: indexing"))
expect("Windows evidence path", 0, PLAN, "--results", "RES:" + RESULTS.replace("evidence/E1_ios_1.png", "evidence\\E1_ios_1.png", 1))
expect("Plan header as a markdown link", 0, PLAN, "--results", "RES:" + RESULTS.replace("**Plan:** docs/plan.md", "**Plan:** [plan](docs/plan.md)"))
expect("defect Case names the case on another platform", 1, PLAN, "--results",
       "RES:" + RESULTS.replace("- **Case:** E2 android", "- **Case:** E2 ios (not run), E1 android"), pattern="does not name E2 android")

expect("row for a platform the case is not planned on", 1, PLAN, "--results",
       "RES:" + RESULTS.replace("| E3 | android | NOT RUN | no scanned fixture on this phone |",
                                "| E3 | android | NOT RUN | no scanned fixture on this phone |\n| E3 | ios | NOT RUN | not planned |"),
       pattern="E3 ios: the plan does not run E3 on ios")
expect("oracle check made to fail inside a case", 0,
       PLAN.replace("fault: relaunch without waiting; 40/40 not reached", "fault: relaunch without waiting; 40/40 not reached (in E1)"))
expect("oracle check inside a case that does not exist", 1,
       PLAN.replace("fault: relaunch without waiting; 40/40 not reached", "fault: relaunch without waiting (in E9)"),
       pattern="'(in E9)' must name the case")

# usage and the shipped template
code, out = run(PLAN, "--bogus")
check("usage error exits 2", code == 2, out)
usage = subprocess.run([sys.executable, str(BIN)], capture_output=True, encoding="utf-8")
check("usage prints the command line", usage.returncode == 2 and "validate_e2e_plan.py <plan.md>" in usage.stdout, usage.stdout)
code, out = subprocess.run([sys.executable, str(BIN), str(TEMPLATE)], capture_output=True, encoding="utf-8").returncode, ""
check("the unfilled template is not accepted", code == 1)


# Windows writes a pipe in the ANSI code page; a code page without the character must not crash the report.
nogoals = WORK / "nogoals.md"
nogoals.write_text("no goals here\n", encoding="utf-8")
narrow = subprocess.run([sys.executable, str(BIN), str(TEMPLATE), "--spec", str(nogoals)], capture_output=True,
                        env={**os.environ, "PYTHONIOENCODING": "ascii"})
check("findings print through a pipe whose code page lacks the character",
      narrow.returncode == 1 and "(| G1 | …)" in narrow.stdout.decode("utf-8"), narrow.stderr.decode(errors="replace"))
# The sh launcher at the top of the script picks a working Python (python3 is the Store stub on many Windows hosts).
if shutil.which("sh"):
    run(PLAN)
    launched = subprocess.run(["sh", str(BIN), str(WORK / "docs" / "plan.md")], capture_output=True, encoding="utf-8",
                              env={**os.environ, "E2E_PYTHON": sys.executable})
    check("sh launcher runs the checker", launched.returncode == 0 and "0 finding(s)" in launched.stdout,
          launched.stdout + launched.stderr)

print(f"e2e plan: pass={passed} fail={failed}")
sys.exit(1 if failed else 0)
