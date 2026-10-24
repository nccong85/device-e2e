#!/bin/sh
# sh runs the next line and re-executes this file with a Python that works; Python reads the line as a string.
# On Windows `python3` is often the Microsoft Store stub that only prints "Python was not found".
''''true; for p in "${E2E_PYTHON:-}" python3 python; do [ -n "$p" ] && "$p" -c '' 2>/dev/null && exec "$p" "$0" "$@"; done; command -v py >/dev/null && exec py -3 "$0" "$@"; echo 'no Python found: set E2E_PYTHON' >&2; exit 127 # '''
__doc__ = """Deterministic checker for a device e2e test plan and its results.

Usage:
  validate_e2e_plan.py <plan.md> [--spec <spec.md>] [--results <summary.md>]...

The plan follows skills/playbook/e2e_test_plan.template.md. Checks what a model should not be trusted to
eyeball on its own plan:
  1. Every spec goal (a `| G<n> |` row of --spec) is a Ref in *Test basis*, and every Ref's Risk is its
     Likelihood × Impact by the matrix in references/test-design.md.
  2. Every basis Ref is traced by a case, cited in *Covered below e2e*, or listed in *Not covered* with a reason;
     every case traces only to basis Refs.
  3. Cases have unique IDs, filled cells, valid platforms, and an Expected that can fail
     ("works", "eventually", "≥ before", "suitable" cannot); every High case has an *Oracle checks* row saying
     how its check is made to fail once (old build, mutation, fault or baseline).
  4. No case is redundant: one whose every Covers item is covered by other cases.
  5. Every State × event cell holds `<case> → <state>`, `below: <test> → <state>`, `untested → <state>` or
     `n/a: <reason>`, the target being one of the table's states; each table's **Coverage:** meets the highest
     risk of its **Traces to:** (H all transitions, M valid transitions, L all states) and is met by the cells;
     all transitions has a round trip in a Sequences table. Every *CRUD* cell holds a case ID, `below: <test>`,
     `n/a: <reason>` (does not apply) or `out: <reason>` (applies, not tested by this plan).
  6. The run steps READY, DRY and DIAG are planned (EXPLORE is optional and states a charter); every case has
     Min and Order; the device time (Min × platforms, run steps included) fits 80 % of the plan's **Device
     budget** (the rest absorbs overruns). With --spec, a feature spec has goal rows (`| G1 |`); a plan whose
     **Mode:** is release may cite a change list without them.
  7. With --results: the header names the build, commit, devices, date and this plan; every case and run step has
     exactly one row per planned platform with PASS, FAIL, BLOCKED or NOT RUN, a reason for BLOCKED / NOT RUN (in the
     Evidence cell, or after a colon: `NOT RUN: budget`), and no row for an ID the plan does not have; every case PASS cites an evidence file; every evidence file cited
     (a path with a directory, e.g. `evidence/E1_ios_1.png`, relative to the summary) exists; every FAIL cites a
     BUG-n whose defect entry is complete; a High case BLOCKED or NOT RUN opens a bullet under Not verified
     (`- E1 ios: <why>`); the `E2E:` line's counts equal the table's; a PASS that mentions a
     retry names its `harness:` cause; with a Min column, a PASS under a quarter of the planned Min is flagged;
     every High case that is not PASS or FAIL on a platform is named under *Not verified*.

Exit 0 = no finding. Exit 1 = at least one finding. Exit 2 = usage error or unreadable file.
A cell is one `|`-separated field; a cell that is a whole `<…>` slot is unfilled.
"""
import re
import sys
from pathlib import Path

WEAK = re.compile(
    r"\bworks?\b|\bcorrectly\b|\bproperly\b|\bas expected\b|\beventually\b|\bsuitabl[ey]\b|\bappropriate(ly)?\b"
    r"|\bas needed\b|\bseveral\b|\breasonabl[ey]\b|(>=|≥)\s*(the\s+)?(before|previous)",
    re.I,
)
PLATFORMS = {"ios", "android"}
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT RUN"}
RUN_STEPS = ("READY", "DRY", "DIAG")
OPTIONAL_STEPS = ("EXPLORE",)
SLACK = 0.8  # planned device time may fill at most this share of the budget; the rest absorbs overruns
CHARTER = re.compile(r"\bexplore\b.+\bwith\b.+\bto discover\b", re.I)
# Risk = RISK_MATRIX[likelihood + impact] (references/test-design.md step 2).
RISK_MATRIX = {"HH": "H", "HM": "H", "HL": "M", "MH": "H", "MM": "M", "ML": "L", "LH": "M", "LM": "L", "LL": "L"}
COVERAGE = {"all states": 0, "valid transitions": 1, "all transitions": 2}
NEEDED = {"L": 0, "M": 1, "H": 2}
ARROW = re.compile(r"\s*(?:→|->)\s*")
ORACLE_CHECK = re.compile(r"^(old build|mutation|fault|baseline)\s*:\s*\S", re.I)
RETRY = re.compile(r"\bretr(y|ies|ied)\b|\bre-?ran\b|\bsecond attempt\b", re.I)
NUM = re.compile(r"\d+(\.\d+)?")
HEADER = ("Build", "Commit", "Devices", "Date", "Plan")
DEFECT_FIELDS = ("Case", "Build", "Device", "Severity", "Steps", "Expected", "Actual", "Evidence", "Harness ruled out by")
TEST_REF = re.compile(r"\S\.[A-Za-z]{1,5}::\s*\S")
EVIDENCE_FILE = re.compile(r"[\w.~/\\-]*[/\\][\w.-]+\.(?:png|jpe?g|heic|gif|xml|json|txt|log|csv|pdf|mp4|mov|ips)\b", re.I)
UNWRITTEN = re.compile(r"\bto be (created|written|added)\b|\bTODO\b|\bTBD\b|\bnot yet\b|\bplanned\b|\bmissing\b", re.I)

findings = []


def find(where, msg):
    findings.append(f"{where}: {msg}")


def clean(cell):
    return cell.strip().replace("`", "").replace("**", "").strip()


def tokens(cell):
    return [t for t in re.split(r"[,;\s]+", clean(cell)) if t]


def unfilled(cell):
    c = clean(cell)
    return not c or c in {"-", "?", "TBD"} or (c.startswith("<") and c.endswith(">"))


def tables_at(lines):
    """Yield (start line, header, rows) for each markdown table in lines; rows are lists of cells."""
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            start = i
            header = [clean(c).lower() for c in lines[i].strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            yield start, header, rows
        else:
            i += 1


def tables(lines):
    for _, header, rows in tables_at(lines):
        yield header, rows


def sections(text):
    out, name, fence = {}, "", False
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        if fence or line.startswith("```"):
            continue
        if line.startswith("## "):
            name = line[3:].strip().lower()
            out.setdefault(name, [])
        elif name:
            out[name].append(line)
    return out


def section(secs, prefix):
    """The lines of every section whose heading starts with `prefix` (a plan may split one, e.g. a state table per
    task), in order; None when there is none."""
    found = [lines for name, lines in secs.items() if name.startswith(prefix)]
    return [line for lines in found for line in lines] if found else None


def col(header, *names):
    for n in names:
        for i, h in enumerate(header):
            if h.startswith(n):
                return i
    return None


def cell(row, i):
    return row[i] if i is not None and i < len(row) else ""


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"FATAL: cannot read {path}: {e}")
        sys.exit(2)


def main(argv):
    # Windows writes a pipe or file in the ANSI code page, which has no '≥'.
    sys.stdout.reconfigure(encoding="utf-8")
    if not argv or argv[0].startswith("-"):
        print("\n".join(__doc__.strip().splitlines()[2:4]))
        return 2
    plan_path, spec, results = argv[0], None, []
    rest = argv[1:]
    while rest:
        flag = rest.pop(0)
        if flag not in ("--spec", "--results") or not rest:
            print(f"usage error near {flag!r}")
            return 2
        if flag == "--spec":
            spec = rest.pop(0)
        else:
            results.append(rest.pop(0))

    plan_text = read(plan_path)
    secs = sections(plan_text)
    P = Path(plan_path).name

    # ---- test basis ----------------------------------------------------------
    basis_lines = section(secs, "test basis")
    refs = []
    risk = {}  # ref -> H, M or L
    if basis_lines is None:
        find(P, "no '## Test basis' section")
    else:
        for header, rows in tables(basis_lines):
            ri, rk = col(header, "ref"), col(header, "risk")
            li, ii = col(header, "likelihood"), col(header, "impact")
            if li is None or ii is None:
                find(P, "Test basis has no Likelihood and Impact columns (Risk = Likelihood × Impact)")
            for row in rows:
                ref = clean(cell(row, ri))
                if unfilled(ref):
                    find(P, f"Test basis row with no Ref: {'|'.join(row)}")
                    continue
                if ref in refs:
                    find(P, f"Test basis Ref {ref} listed twice")
                refs.append(ref)
                r = clean(cell(row, rk)).upper()[:1]
                if r not in ("H", "M", "L"):
                    find(P, f"Test basis {ref}: Risk must be H, M or L")
                    continue
                risk[ref] = r
                if li is None or ii is None:
                    continue
                lk, im = clean(cell(row, li)).upper()[:1], clean(cell(row, ii)).upper()[:1]
                if lk not in ("H", "M", "L") or im not in ("H", "M", "L"):
                    find(P, f"Test basis {ref}: Likelihood and Impact must be H, M or L")
                elif RISK_MATRIX[lk + im] != r:
                    find(P, f"Test basis {ref}: Likelihood {lk} × Impact {im} is Risk {RISK_MATRIX[lk + im]}, not {r}")

    release = bool(re.search(r"^\*\*Mode:\*\*\s*release\b", plan_text, re.I | re.M))
    if spec:
        goals = re.findall(r"^\|\s*`?(G\d+)`?\s*\|", read(spec), re.M)
        # A release basis is the change list (what's-new, store notes), which has no goal rows.
        if not goals and not release:
            find(Path(spec).name, "no goal rows (| G1 | …) found; a release plan says **Mode:** release")
        for g in dict.fromkeys(goals):
            if g not in refs:
                find(P, f"spec goal {g} is not in Test basis")

    # ---- cases ---------------------------------------------------------------
    case_lines = section(secs, "cases")
    cases = {}  # id -> (traces, covers, platforms)
    minutes = {}
    case_risk = {}
    if case_lines is None:
        find(P, "no '## Cases' section")
    else:
        for header, rows in tables(case_lines):
            idx = {k: col(header, k) for k in ("id", "traces", "covers", "platform", "expected", "how checked", "min", "order")}
            for k, v in idx.items():
                if v is None:
                    find(P, f"Cases table has no '{k}' column")
            if None in idx.values():
                continue
            for row in rows:
                cid = clean(cell(row, idx["id"]))
                if unfilled(cid):
                    find(P, f"case row with no ID: {'|'.join(row)}")
                    continue
                if cid in cases:
                    find(P, f"case ID {cid} used twice")
                for k in ("traces", "covers", "platform", "expected", "how checked"):
                    if unfilled(cell(row, idx[k])):
                        find(P, f"{cid}: '{k}' is empty or still a slot")
                traces = tokens(cell(row, idx["traces"]))
                for t in traces:
                    if t not in refs:
                        find(P, f"{cid}: traces to {t}, which is not a Test basis Ref")
                plats = {t.lower() for t in tokens(cell(row, idx["platform"]))}
                if "both" in plats:
                    plats = (plats - {"both"}) | PLATFORMS
                if plats - PLATFORMS or not plats:
                    find(P, f"{cid}: Platforms must be ios, android or both")
                expected = clean(cell(row, idx["expected"]))
                m = WEAK.search(expected)
                if m:
                    hint = ("'≥ before' passes when nothing moved; write '> the value read before' or the final count"
                            if re.match(r">=|≥", m.group(0)) else "name the number or state that fails it")
                    find(P, f"{cid}: Expected '{m.group(0)}' cannot fail; {hint}")
                mins = clean(cell(row, idx["min"]))
                if not NUM.fullmatch(mins):
                    find(P, f"{cid}: Min must be a number of device minutes per platform")
                if not re.fullmatch(r"\d+", clean(cell(row, idx["order"]))):
                    find(P, f"{cid}: Order must be a whole number (1 runs first; a cut run drops the highest)")
                cases[cid] = (traces, set(tokens(cell(row, idx["covers"]))), plats & PLATFORMS)
                minutes[cid] = float(mins) if NUM.fullmatch(mins) else 0
                # A case is as risky as its own Risk cell, or the riskiest Ref it traces to.
                levels = [clean(cell(row, col(header, "risk"))).upper()[:1]] + [risk.get(t, "") for t in traces]
                case_risk[cid] = max((x for x in levels if x in NEEDED), key=NEEDED.get, default="L")

    # ---- run steps and budget ----------------------------------------------
    all_plats = set().union(*[c[2] for c in cases.values()]) if cases else set()
    steps = {}
    for header, rows in tables(section(secs, "run steps") or []):
        si, mi, wi = col(header, "step", "id"), col(header, "min"), col(header, "what")
        for row in rows:
            sid = clean(cell(row, si))
            m = clean(cell(row, mi))
            if sid in RUN_STEPS + OPTIONAL_STEPS:
                steps[sid] = float(m) if NUM.fullmatch(m) else None
                if steps[sid] is None:
                    find(P, f"run step {sid}: Min must be a number")
            if sid == "EXPLORE" and not CHARTER.search(clean(cell(row, wi))):
                find(P, "run step EXPLORE: state the charter, 'Explore <target> with <resources> to discover <information>'")
    for sid in RUN_STEPS:
        if sid not in steps:
            find(P, f"run step {sid} is not planned (## Run steps)")
    total = sum(minutes[c] * len(cases[c][2]) for c in cases) + sum((v or 0) * len(all_plats) for v in steps.values())
    m = re.search(r"\*\*Device budget:\*\*\s*(\d+(?:\.\d+)?)", plan_text)
    if not m:
        find(P, "no **Device budget:** <minutes> line")
    elif total > float(m.group(1)):
        find(P, f"planned device time {total:g} min exceeds the Device budget of {m.group(1)} min; cut by Order")
    elif total > SLACK * float(m.group(1)):
        find(P, f"planned device time {total:g} min leaves less than {1 - SLACK:.0%} of the {m.group(1)} min Device "
                "budget for overruns; cut by Order")

    # ---- redundancy ----------------------------------------------------------
    for cid, (_, covers, _) in cases.items():
        others = set().union(*[c[1] for k, c in cases.items() if k != cid]) if len(cases) > 1 else set()
        if covers and covers <= others:
            find(P, f"{cid} is redundant: every item it covers ({', '.join(sorted(covers))}) is covered by another case")

    # ---- state × event and CRUD ---------------------------------------------
    def ref_cell(where, c, out=False):
        """Check a cell that names case IDs, `below: <file::name>`, `n/a: <reason>` (does not apply) or
        `out: <reason>` (CRUD only: applies, not tested by this plan); return its kind or None."""
        if unfilled(c):
            find(P, f"{where} is empty; write a case ID, 'below: <test>', 'n/a: <reason>'" + (" or 'out: <reason>'" if out else ""))
            return None
        if out and re.match(r"^out\b", c, re.I):
            if not re.match(r"^out\s*:\s*\S", c, re.I):
                find(P, f"{where}: '{c}' needs ': <reason>'")
                return None
            return "out"
        if c.lower().startswith(("n/a", "below")):
            if not re.match(r"^(n/a|below)\s*:\s*\S", c, re.I):
                find(P, f"{where}: '{c}' needs ': <reason or test>'")
                return None
            if c.lower().startswith("below") and (not TEST_REF.search(c) or UNWRITTEN.search(c)):
                find(P, f"{where}: 'below:' must name a test that exists (file::name)")
                return None
            return "na" if c.lower().startswith("n/a") else "below"
        bad = [t for t in tokens(c) if t not in cases]
        for t in bad:
            find(P, f"{where}: {t} is not a case ID")
        return None if bad else "case"

    def norm(state):
        return re.sub(r"\s*\(.*\)\s*$", "", state).strip().lower()

    st_lines = section(secs, "state") or []
    task_tables, round_trips = [], set()
    for start, header, rows in tables_at(st_lines):
        if col(header, "path") is not None:  # Sequences: round trips walked by a case
            ti, ci = col(header, "task"), col(header, "case")
            for row in rows:
                seq = clean(cell(row, 0))
                if unfilled(seq):
                    continue
                kind = ref_cell(f"Sequence {seq}", clean(cell(row, ci)))
                if kind == "case":
                    round_trips.add(norm(clean(cell(row, ti))))
                elif kind:
                    find(P, f"Sequence {seq}: name the case that walks it")
            continue
        line = next((l for l in reversed(st_lines[:start]) if "**Task:**" in l), "")
        task_tables.append((line, header, rows))
    for line, header, rows in task_tables:
        task = norm(clean(re.search(r"\*\*Task:\*\*([^·]*)", line).group(1))) if line else ""
        label = f"State × event '{task or '?'}'"
        states = {norm(clean(cell(row, 0))) for row in rows}
        cells = []  # (state, kind, target)
        for row in rows:
            state = clean(cell(row, 0))
            for j in range(1, len(header)):
                c = clean(cell(row, j))
                where = f"State × event [{state} × {header[j]}]"
                if c.lower().startswith("n/a"):
                    ref_cell(where, c)
                    continue
                parts = ARROW.split(c, maxsplit=1)
                if unfilled(c) or len(parts) < 2 or unfilled(parts[1]):
                    find(P, f"{where}{' is empty' if unfilled(c) else ''}: write '<case> → <target state>', 'below: <test> → <state>', "
                            f"'untested → <state>' or 'n/a: <reason>'")
                    continue
                source, target = parts[0].strip(), norm(parts[1])
                if target not in states:
                    find(P, f"{where}: target state '{target}' is not a row of this table")
                kind = "untested" if source.lower() == "untested" else ref_cell(where, source)
                if kind:
                    cells.append((norm(state), kind, target))
        if not line:
            find(P, f"{label}: no '**Task:** <name> · **Traces to:** <Refs> · **Coverage:** <criterion>' line above the table")
            continue
        m = re.search(r"\*\*Coverage:\*\*\s*([a-z ]+)", line, re.I)
        level = COVERAGE.get(m.group(1).strip().lower()) if m else None
        if level is None:
            find(P, f"{label}: **Coverage:** must be all states, valid transitions or all transitions")
            continue
        t = re.search(r"\*\*Traces to:\*\*([^·]*)", line)
        traced = tokens(t.group(1)) if t else []
        for r in traced:
            if r not in refs:
                find(P, f"{label}: traces to {r}, which is not a Test basis Ref")
        need = max((NEEDED[risk[r]] for r in traced if r in risk), default=0)
        if level < need:
            want = next(k for k, v in COVERAGE.items() if v == need)
            find(P, f"{label}: its Refs are risk {'LMH'[need]}, so **Coverage:** must be at least {want}")
        tested = [(st, tg) for st, kind, tg in cells if kind in ("case", "below")]
        if level == 2:
            if any(kind == "untested" for _, kind, _ in cells):
                find(P, f"{label}: all transitions leaves no cell 'untested'")
            if task not in round_trips:
                find(P, f"{label}: all transitions needs a round trip in a Sequences table, walked by a case")
        elif level == 1:
            for st, kind, tg in cells:
                if kind == "untested" and tg != st:
                    find(P, f"{label}: [{st} → {tg}] changes the state, so valid transitions needs a case for it")
        else:
            reached = {st for st, _ in tested} | {tg for _, tg in tested}
            for st in sorted(states - reached):
                find(P, f"{label}: all states, but no case starts in or reaches '{st}'")

    for header, rows in tables(section(secs, "crud") or []):
        for row in rows:
            entity = clean(cell(row, 0))
            for j in range(1, len(header)):
                ref_cell(f"CRUD [{entity} × {header[j]}]", clean(cell(row, j)), out=True)

    # ---- oracle checks: every High case is seen to fail once -----------------
    checked = {}
    for header, rows in tables(section(secs, "oracle check") or []):
        ci, mi = col(header, "case"), col(header, "made to fail", "how")
        for row in rows:
            cid, how = clean(cell(row, ci)), clean(cell(row, mi if mi is not None else 1))
            if unfilled(cid):
                continue
            if cid not in cases:
                find(P, f"Oracle checks: {cid} is not a case ID")
            if not ORACLE_CHECK.match(how):
                find(P, f"Oracle checks {cid}: say how the check fails once: old build:, mutation:, fault: or baseline:")
            inside = re.search(r"\(in\s+([^)]*)\)", how)
            if inside and inside.group(1).strip() not in cases:
                find(P, f"Oracle checks {cid}: '(in {inside.group(1).strip()})' must name the case it fails inside")
            checked[cid] = how
    for cid in cases:
        if case_risk.get(cid) == "H" and cid not in checked:
            find(P, f"{cid} is High risk but has no Oracle checks row (how its check is made to fail once)")

    # ---- covered below / not covered ----------------------------------------
    accounted = {t for c in cases.values() for t in c[0]}
    below = section(secs, "covered below")
    for header, rows in tables(below or []):
        ti = col(header, "test")
        for row in rows:
            item = clean(cell(row, 0))
            if unfilled(item):
                continue
            test = clean(cell(row, ti if ti is not None else 1))
            if unfilled(test) or not TEST_REF.search(test):
                find(P, f"Covered below e2e {item}: name the test (file::name), or keep it on the device")
            elif UNWRITTEN.search(test):
                find(P, f"Covered below e2e {item}: the test is not written yet; keep it on the device or in Not covered")
            else:
                accounted.update(tokens(item))
    notcov = section(secs, "not covered")
    for header, rows in tables(notcov or []):
        wi, ai = col(header, "why"), col(header, "risk accepted", "accepted")
        for row in rows:
            item = clean(cell(row, 0))
            if unfilled(item):
                continue
            if unfilled(cell(row, wi if wi is not None else 1)):
                find(P, f"Not covered {item}: no reason")
            if ai is not None and unfilled(cell(row, ai)):
                find(P, f"Not covered {item}: nobody accepted the risk")
            accounted.update(tokens(item))
    for r in refs:
        if r not in accounted:
            find(P, f"Test basis {r} has no case, no lower-level test and no Not covered line")

    # ---- results -------------------------------------------------------------
    known = dict(cases)
    for sid in steps:
        known[sid] = ([], set(), all_plats)
    for res in results:
        R = Path(res).name
        text = read(res)
        base = Path(res).resolve().parent

        def missing_files(where, evidence):
            for f in EVIDENCE_FILE.findall(evidence):
                if not (base / Path(f.replace("\\", "/")).expanduser()).is_file():
                    find(R, f"{where}: evidence file {f} does not exist")
        for h in HEADER:
            m = re.search(rf"^\*\*{h}:\*\*(.*)$", text, re.M)
            if not m or unfilled(m.group(1)):
                find(R, f"header **{h}:** is missing or still a slot")
            elif h == "Plan" and Path(plan_path).name not in {
                    Path(t).name for t in tokens(re.sub(r"\[[^\]]*\]\(([^)]*)\)", r"\1", m.group(1)))}:
                find(R, f"header **Plan:** does not name {Path(plan_path).name}")
        defects = {}
        for block in re.split(r"^### ", text, flags=re.M)[1:]:
            m = re.match(r"(BUG-\d+)\b", block)
            if not m:
                continue
            fields = dict(re.findall(r"^\s*-\s*\*\*([^*]+?):\*\*(.*)$", block, re.M))
            defects[m.group(1)] = fields
            missing_files(m.group(1), clean(fields.get("Evidence", "")))
            for f in DEFECT_FIELDS:
                if f not in fields or unfilled(fields[f]):
                    find(R, f"{m.group(1)}: field **{f}:** is missing or empty")
            if "Severity" in fields and not re.match(r"\s*S[1-4]\b", fields["Severity"]):
                find(R, f"{m.group(1)}: Severity must be S1 to S4")
        seen = {}
        found_table = False
        for header, rows in tables(text.splitlines()):
            ii, pi, si, ei = col(header, "id"), col(header, "platform"), col(header, "status"), col(header, "evidence")
            mi = col(header, "min")
            if None in (ii, pi, si):
                continue
            found_table = True
            for row in rows:
                cid, plat = clean(cell(row, ii)), clean(cell(row, pi)).lower()
                status = re.sub(r"\s+", " ", clean(cell(row, si)).upper())
                evidence = clean(cell(row, ei))
                m = re.fullmatch(r"(BLOCKED|NOT RUN)\s*:\s*(.*)", status)
                if m:  # `NOT RUN: budget` carries its reason in the Status cell
                    status = m.group(1)
                    reason = clean(cell(row, si)).split(":", 1)[1].strip()
                    evidence = f"{reason} {evidence}".strip()
                if cid not in known:
                    find(R, f"{cid} is not in the plan; add the case to the plan first")
                    continue
                if (cid, plat) in seen:
                    find(R, f"{cid} {plat}: more than one row")
                if plat in PLATFORMS and plat not in known[cid][2]:
                    find(R, f"{cid} {plat}: the plan does not run {cid} on {plat}")
                seen[(cid, plat)] = status
                if status not in STATUSES:
                    find(R, f"{cid} {plat}: status '{status}' is not PASS, FAIL, BLOCKED or NOT RUN")
                if status in ("BLOCKED", "NOT RUN") and unfilled(evidence):
                    find(R, f"{cid} {plat}: {status} with no reason")
                if status == "PASS" and cid in cases and not EVIDENCE_FILE.search(evidence):
                    find(R, f"{cid} {plat}: PASS cites no evidence file (e.g. evidence/{cid}_{plat}_1.png)")
                missing_files(f"{cid} {plat}", evidence)
                if status == "PASS" and RETRY.search(evidence) and not re.search(r"\bharness\s*:\s*\S", evidence, re.I):
                    find(R, f"{cid} {plat}: PASS after a retry; name the 'harness: <cause>', or it is a FAIL (intermittent)")
                took = clean(cell(row, mi))
                if status == "PASS" and cid in cases and NUM.fullmatch(took) and float(took) < minutes[cid] / 4:
                    find(R, f"{cid} {plat}: PASS in {took} of {minutes[cid]:g} planned min; show it ran the whole case, or BLOCKED")
                if status == "FAIL":
                    bugs = re.findall(r"BUG-\d+", evidence)
                    if not bugs:
                        find(R, f"{cid} {plat}: FAIL cites no BUG-n")
                    for bug in bugs:
                        if bug not in defects:
                            find(R, f"{cid} {plat}: {bug} has no entry under Defects")
                        elif not re.search(rf"\b{re.escape(cid)}\W+{plat}\b", clean(defects[bug].get("Case", "")), re.I):
                            find(R, f"{bug}: **Case:** does not name {cid} {plat}")
        if not found_table:
            find(R, "no results table with ID, Platform and Status columns")
            continue
        for cid, (_, _, plats) in known.items():
            for plat in sorted(plats):
                if (cid, plat) not in seen:
                    find(R, f"{cid} {plat}: planned but has no row (write NOT RUN with the reason)")
        not_verified = "\n".join(section(sections(text), "not verified") or [])
        for (cid, plat), st in sorted(seen.items()):
            # The ID must open a bullet ("- E1 android: why"); a passing mention inside another line does not count.
            named = re.search(rf"^\s*[-*]\s*[*`]*{re.escape(cid)}[*`]*\s+{plat}\b", not_verified, re.M | re.I)
            if case_risk.get(cid) == "H" and st in ("BLOCKED", "NOT RUN") and not named:
                find(R, f"{cid} {plat}: High risk and {st}; open a line under '## Not verified' with it: '- {cid} {plat}: <why>'")
        m = re.search(r"^E2E:.*$", text, re.M)
        if not m:
            find(R, "no E2E: hand-off line")
        else:
            for plat in sorted(PLATFORMS):
                got = re.search(rf"{plat}\s+pass=(\d+)\s+fail=(\d+)\s+blocked=(\d+)\s+not_run=(\d+)", m.group(0))
                want = [sum(1 for (c, p), st in seen.items() if c in cases and p == plat and st == x)
                        for x in ("PASS", "FAIL", "BLOCKED", "NOT RUN")]
                if plat not in all_plats and not got:
                    continue
                if not got or [int(g) for g in got.groups()] != want:
                    find(R, f"E2E: line {plat} counts differ from the table (pass, fail, blocked, not_run = {want})")

    for f in findings:
        print(f"FAIL {f}")
    print(f"e2e plan: {len(refs)} basis ref(s), {len(cases)} case(s), {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
