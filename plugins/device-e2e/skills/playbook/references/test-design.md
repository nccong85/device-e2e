# Designing the e2e cases: complete, and nothing twice

A device case costs minutes to hours; a missed case costs a field bug. So the plan is built from the test basis by
a fixed procedure, every item is traced both ways, and a script checks the result before any device time is spent.
The techniques follow ISTQB CTFL v4.0.1 (§4 techniques, §5.1.5 prioritization, §5.1.6 test pyramid, §5.2 risk),
CTAL-TA v4.0 (§1.3.2 test case quality, §1.3.4 oracles, §3 techniques, §5.3 test effectiveness) and, for the mobile events and factors,
CT-MAT v1.0 (§1.6 device selection, §2 test types, §3.1 quality characteristics).

Terms (test basis, coverage item, oracle, BLOCKED vs NOT RUN, …) are defined in `glossary.md`. Write the plan from
`${CLAUDE_SKILL_DIR}/e2e_test_plan.template.md`, then run
`validate_e2e_plan.py <plan> --spec <spec>` (exit 0 = no finding). The owner approves the plan together with the
device time, before the run.

Contents: [Two modes](#two-modes) · [The procedure](#the-procedure) (1 basis, 2 risk, 3 factors, 4 state × event,
5 CRUD, 6 technique, 7 push down, 8 platforms, 9 write, 10 oracle, 11 dedupe, 12 budget, 13 close) ·
[Oracles that can fail](#oracles-that-can-fail) · [Cases that run and still miss the bug](#cases-that-run-and-still-miss-the-bug) ·
[Results](#results)

## Two modes

- **Feature:** the basis is one spec. Depth follows risk.
- **Release:** the basis is the user-visible change list (what's-new, store notes) plus the diff since the last
  release, plus every bug that reached users since then. Cases come in three groups, in this order:
  **confirmation** (each fixed bug, reproduced on the old build first), **regression** of the areas the diff
  touches, and a **smoke** pass of everything else. A release plan always has one **upgrade over existing data**
  case: install the previous release, create data, upgrade, check it.

## The procedure

1. **Collect the basis, from four sources.** Every item gets a Ref in the plan's *Test basis* table:
   - the spec's goals and acceptance criteria (`G1`, `G2`, …);
   - the Part A budgets and non-negotiables of `.claude/review-gate/review_brief.md` (if the project uses review-gate) that the changed code can
     break (a 1 s budget is a case even when no goal names it);
   - the change list: each user-visible change and each changed area of the diff (`CH-1`, …), and each fixed bug
     (`BUG-…`);
   - release: each bug users hit since the last release that a device test could have caught (`ESC-1`, …). Each
     one is a case this time (CTAL-TA §5.3: an escaped defect shows where the tests were too thin). The smoke
     areas every release must keep working (`SMK-<area>`: launch, import, search) and the release checks
     (`REL-<check>`: upgrade over the last store build, config, the version string) are Refs too. A release spec
     is the change list (what's new, store notes), so it has no `G` rows; the plan says **Mode:** release and
     `--spec` accepts that.
   Trace both ways: a diff change that maps to no goal and no case is a gap, not an unlisted extra (test gap
   analysis, CTAL-TA §5.3: changed code no test exercised is where new bugs are).
2. **Rate the risk** of each item as *Likelihood* × *Impact*, each High / Medium / Low with one line of why
   (CTFL §5.2.1). Impact: what breaks, for how many users, data loss or not. Likelihood: how much code changed,
   code in one platform's layer, a new OS version or device class, and the bug history of the area (where bugs
   were found before, more are likely). The *Risk* column is read from this matrix, and the validator checks it:

   | Likelihood \ Impact | H | M | L |
   |---|---|---|---|
   | **H** | H | H | M |
   | **M** | H | M | L |
   | **L** | M | L | L |

   Risk sets the depth (CTAL-TA §3.5.1: the higher the risk, the more rigorous the coverage):

   | Risk | State × event (step 4) | Boundaries | Combinations (step 3) | Decision table |
   |---|---|---|---|---|
   | H | all transitions + round trips | 3-value | pairwise (3+ factors) | every column, not minimized |
   | M | valid transitions | 2-value | base choice | minimized |
   | L | all states | 2-value, main boundary only | each choice | main column |

3. **List the factors the code path varies on.** A factor enters the plan only when the code branches on it.
   Language is a factor for tokenizing and OCR, not for a cache or a scheduler. The device is a factor too when
   the code depends on it: OS major version, maker (Android skins kill background work differently), screen
   size or density, and the settings the code reads (locale date format, font scale, dark mode).
   Write the partitions (`Latin`, `CJK`), not every value, and include the invalid partitions (a file the app
   must reject is a partition with its own coverage item). Then pick the combination rule by risk:
   - **each choice:** every partition of every factor appears in at least one case;
   - **base choice:** pick one base value per factor (the most common real use, written in the *Base choice*
     column), run the base once, then change one factor at a time. It is the cheapest rule that still isolates
     the factor that failed;
   - **pairwise:** every pair of partitions of every two factors appears once. It saves cases only from three
     factors up; with two factors pairwise is all combinations.
   **Domain:** when one rule ties two inputs ("over 200 MB *or* over 500 pages", a size limit that depends on
   the page count), test the border of the combined rule: for each border one ON point (on it) and one OFF
   point (just across it), instead of the boundaries of each input alone (CTAL-TA §3.1.1). Tag `DM-<border>`.
4. **Draw the state × event table** for every long-running or background task (import, indexing, sync, export).
   States: idle, running, paused, done, failed, as the task has them. Events are grouped into partitions
   (CT-MAT §2.1 to §2.3); one event per partition is enough unless the code handles events in the same partition
   differently, and a High task takes the events the code handles differently (OS kill and swipe always differ):

   | Partition | Events |
   |---|---|
   | leave | Home, lock, camera or another app in front, notification tapped, share sheet, split screen |
   | interrupt | incoming call, alarm, a notification burst after Do Not Disturb ends |
   | process ends | OS kills the process in the background, low-memory kill, user swipes the app away, force-stop, reboot |
   | resource | low disk space during write, low memory, low battery or power-save mode, charger plugged in or out, thermal throttling, Android Doze |
   | connectivity | no network, Wi-Fi ↔ cellular switch, flight mode on then off, a captive portal |
   | OS setting | permission revoked in Settings, permission denied at first then granted later, language, time zone or date changed, font size or dark mode changed |
   | install | upgrade, an upgrade interrupted, reinstall keeping data (iOS offload, Android backup) and without |
   | screen | rotation, rotation twice in a row, window resize |

   Battery drain and thermal throttling need hours of device time; list them under *Not covered* unless the item
   is High risk and the code reacts to them.
   Above each table write `**Task:** <name> · **Traces to:** <Refs> · **Coverage:** <criterion>`. The criterion
   follows the highest risk of the Refs (step 2), and the validator checks it:
   - **all states:** every state is the start or the target of a case;
   - **valid transitions:** every cell whose target differs from its state has a case (ISTQB 0-switch);
   - **all transitions:** every cell has a case, the ones that should leave the state unchanged too (they are
     this table's invalid transitions: the event must not change the task), plus at least one *round trip*
     (a sequence that leaves a state and comes back to it, CTAL-TA §3.2.2), listed in a *Sequences* table with
     the case that walks it. Do not go to 2-switch: the cases grow by the number of events each step.
   Each cell holds the expected target state after an arrow: `E1 → running`, `below: <file::name> → done`,
   `untested → paused` (target known, no case: allowed only below *all transitions*) or `n/a: <reason>` (the event
   cannot happen in this state). No cell is left empty; an empty cell has no meaning.
   OS kill and user swipe are different events: Android keeps saved state after a system kill
   (`adb shell am kill <pkg>` from the background) and clears it after a swipe or force-stop; iOS drops restored
   state when the user force-quits.
5. **Draw the CRUD table** for every entity the change stores (document, page, index entry, setting): one row per
   entity, one column per operation, Create, Read, Update, Delete (CTAL-TA §3.2.1). Each cell holds a case ID,
   `below: <file::name>`, `n/a: <reason>` when the operation does not exist, or `out: <reason>` when it exists
   and this plan leaves it untested (a smoke that skips rename); an `out:` cell goes under *Not covered* too, so
   nobody reads it as "does not apply". The table finds the operation nobody tests (a rename that leaves the
   old name in the index, a delete that leaves the file on disk). Most cells push down (step 7); the device keeps
   the cells that touch real storage or the platform's index, and a delete or update interrupted by an event from
   step 4. Tag `CR-<entity>×<op>`.
6. **Pick a technique per item** and name its coverage items in the *Covers* column:
   - `EP-<partition>`: one value per partition, invalid partitions included;
   - `BV-<boundary>(<values>)`: the values written out, 2-value (the boundary and its neighbour across it) or
     3-value (the boundary and both neighbours) by risk: `BV-limit(500,501)`, `BV-limit(499,500,501)`;
   - `DM-<border>` (step 3), `DT-<column>` for a decision table when conditions combine;
   - `ST-<state>×<event>` (step 4), `SQ-<sequence>` for a round trip, `CR-<entity>×<op>` (step 5);
   - `MR-<relation>` for a metamorphic relation (*Oracles that can fail*);
   - `ER-<guess>` for error guessing, drawn from `traps.md`, from the bugs found here before, and from the
     escaped bugs of step 1. Add the failure inputs: a file the app must reject, a page that fails, a scanned
     image next to a PDF.
7. **Push down what a lower level proves.** Validation, parsing, ranking, empty states and layout belong in unit
   or widget tests (CTFL §5.1.6). Keep on the device only what needs it: OS lifecycle, background execution, the
   platform's OCR and file picker, real file sizes, upgrade over real data, permissions. Each pushed-down item
   cites the test that proves it (`file::name`) in *Covered below e2e*, and the test exists today. No such test,
   or one "to be created" → keep it on the device. The same holds for `below:` cells in steps 4 and 5.
8. **Choose platforms per case.** Shared code → `both`. Code in one platform's layer (a Kotlin-only fix) →
   that platform only. A platform skipped for any other reason goes to *Not covered*.
9. **Write the cases.** Chain steps that share a costly setup into one case, or one group of cases on one setup,
   each step with its own expected result. In e-Scanner every interruption case re-imported a 300-page fixture and
   waited for indexing, and the run took about 7 hours. When several cases list the same costly precondition
   ("fixture A imported fresh"), either share one setup or say in the precondition why each needs its own (for
   example, the event under test ends the task, so the next case cannot reuse it). Split wherever an early
   failure would hide the later checks, and keep one invalid transition per case. A shortened variant ("quick")
   is its own row with its own Expected; running a case shorter than planned makes it `BLOCKED`.
10. **Give every case an oracle that can fail** (rules below), and say in *Expected* what number or state makes it
    FAIL. For every High case, plan in *Oracle checks* how the oracle is made to fail once
    ([below](#cases-that-run-and-still-miss-the-bug)): in `DRY`, or marked `(in <case>)` when the check needs
    state only a case builds (a finished document), and made to fail there before that case's result counts.
    The marker ends the *Made to fail by* cell: `mutation: expect progress to grow on a finished document (in E3)`.
11. **Remove duplicates.** A case whose every coverage item is also covered by another case goes. The validator
    flags it.
12. **Budget the device time and order the cases.** Give each case its `Min` (device minutes per platform, from
    the last run where there is one) and an `Order`: High risk first; among equal risk, the case that adds the
    most coverage items not yet covered; a case that needs another's end state (the upgrade needs the data)
    after it (CTFL §5.1.5). Plan the run steps `READY`, `DRY` and `DIAG`, and, when a High item has risks no scripted case reaches, one optional `EXPLORE`
    session (below). The total may fill at most 80 % of the **Device budget** (the validator checks it): a case
    whose checks poll the UI tree runs over (a smoke search case planned at 5 minutes took 7.6, and pushed
    `EXPLORE` out). Cut by Order and list what was cut under *Not covered*. A run that runs out of time stops at a case boundary and marks the rest `NOT RUN: budget`.
    In e-Scanner the device work of a release took 50 minutes inside 11 hours of waiting for cable, unlock and the
    owner; `READY` checks that before the first case, and `DIAG` (the whole run's diagnostics) found the one real
    bug no case planned for.
    **`EXPLORE`** is one time-boxed exploratory session (about 15 minutes per platform, after the High cases) with
    a charter: `Explore <target> with <resources> to discover <information>` (CTAL-TA §3.4.1), for example
    "Explore the import of a 300-page PDF with leave and connectivity events to discover lost or repeated
    pages". It is planned like a run step, with a results row; whatever it finds becomes a case in the plan
    before it is reported. Random monkey input and field testing are not worth device time here: they have no
    oracle and no coverage measure (CTAL-TA §3.1.3, CT-MAT §3.2.1).
13. **Close the plan.** Every basis Ref is in a case's *Traces to*, in *Covered below e2e*, or in *Not covered*
    with a reason and who accepted the risk. Run the validator; then the review checklist at the end of the
    template.

## Oracles that can fail

These rules come from cases that passed while proving nothing:

- **Write a number or a state, in words with one meaning.** "Coverage ≥ before", "eventually", "works", "a record
  exists", "suitable", "several", "as needed" cannot fail (CTAL-TA §1.3.2: an ambiguous test case gives false
  negatives). Write "coverage = 40/40 pages within 60 s", "timing record ≤ 1 000 ms", "the card shows page 3".
- **Observe during the interruption, not only after.** Read progress just before leaving, right after coming
  back, and at the end. Read after the return only, and you cannot tell background progress from progress made
  after the reopen.
- **Prove the precondition you mean to test.** "Leave the app mid-task" is only tested if the task was mid-way
  when you left. Measure progress *before* the interruption and mark the case BLOCKED (not PASS) if the work had
  already finished. A slow probe can finish the work for you. Prove staging the same way (the fixture is the
  regenerated one, on this phone), and, for a fix, that the old build fails the case.
- **Measure progress where it happens.** If the user-visible signal lags the work (search finds a page tens of
  seconds after OCR finished it), a probe of that signal says the task is mid-way when it is already done. Read
  progress from the app's own record (diagnostics, log, a progress field), and check in `DRY` that the record
  has what you need. In an e-Scanner trial the search probe said 22 to 27 of 48 pages at Home; the diagnostics
  showed all 48 OCR calls done 1 s before Home, so the case was BLOCKED.
- **Compare with a baseline when the exact answer is unknown (metamorphic testing, CTAL-TA §3.3.2).** OCR text,
  ranking and timing have no exact expected value, but a relation between two runs does. Run the fixture once
  without the event (the baseline) and once with it, and compare: same page count, same set of pages found for
  each search word, same file hash after export. Other relations: importing the same file twice gives one
  document (or two identical ones, as the spec says); a search word found on page 3 is still found after a
  rename. Tag the case `MR-<relation>`; the baseline run is part of its `Min`, or a shared group's.
- **Probe progress cheaply.** If the work is sequential, binary-search checkpoints (about 5 probes) instead of
  probing every one.
- **Use tokens the device reads reliably.** On-device OCR misreads look-alike characters (one engine read `0`
  after letters as `O`), so letter+digit tokens produce false FAILs on one platform only. All-digit tokens and
  real words are safer.
- **Match the right item.** Results can include the user's real data; check the fixture's own title too, and
  allow for truncated names in grids (`abc…xyz.pdf`).
- **The element must be visible, not only in the tree.** An element in the UI tree can be off screen, covered by
  a sheet or zero-sized, and a check that finds it passes while the user sees nothing (CT-MAT §5.2: object
  identification gives false negatives). Check `driver.visible(el)` (bounds inside the screen, non-zero size);
  nothing checks that another view covers it, so keep a screenshot of the moment.
- **Assert absence structurally.** "The removed thing is gone" must look for something that would come back with
  it (an icon, a key), not for the deleted literal string, and never on a page that is blank anyway: such a test
  can never fail. Mutation-check new assertions when cheap.
- **Read the app's own record.** After an interruption pull the app's diagnostics or log file and count the
  failure events it recorded.

## Cases that run and still miss the bug

A plan can lose a case in two ways: it never runs, or it runs and cannot fail. These mechanisms close both.

**A case that never runs.**
- Every planned ID has a results row per platform, with a reason for `NOT RUN` and `BLOCKED`; a suite that drops
  a case leaves a missing row, and the validator reports it. The suite reads its case list from the plan, not
  from its own code.
- A High-risk case that is not PASS or FAIL on a planned platform is named under *Not verified* in the results,
  so the owner sees the gap and decides; the validator checks it.
- A PASS that took far less than its planned `Min` did not do what the plan said (no wait, a skipped step, a
  fixture already indexed). The results table records the minutes each case took (*Min* column); a PASS under a
  quarter of the plan is a finding until the evidence shows it ran the whole case, or it is `BLOCKED`.

**A case that runs and cannot fail.**
- **Show every High oracle failing once (Oracle checks).** Before its result counts, each High case's check is
  seen to fail on purpose, one of:
  - `old build: <version>`: the confirmation case fails on the build before the fix;
  - `mutation: <what>`: in `DRY`, the expected value is changed so the check must fail (expect 41/40 pages, a
    word that is not in the fixture), and it does;
  - `fault: <how>`: the fault is made on the device (airplane mode during sync, the fixture's page removed, a
    debug build's switch), and the check catches it;
  - `baseline: <relation>`: a metamorphic case, compared with a baseline run made differently on purpose once.
  A check that still passes with the fault in place proves nothing; fix the check before the run. This is
  mutation analysis applied to one assertion at a time: the cheapest proof that a test can detect a defect.
- **No silent retry.** A case that fails and then passes on a retry is an intermittent failure, not a PASS: it is
  `FAIL` with a `BUG-n` unless the evidence names the harness cause (a harness bug, fixed and re-run). Every
  retry is written in the Evidence cell; the validator rejects a PASS whose evidence mentions a retry with no
  `harness:` cause.
- **Prove the precondition** (above): a case whose condition did not hold is `BLOCKED`, never PASS.
- **After the release, count what escaped** (CTAL-TA §5.3): each bug users report that a device case could have
  caught is an `ESC-n` Ref in the next release plan, an `ER-` coverage item, and a line in `traps.md` when the
  cause was how the test was done. When the escaped bugs cluster in an area the plan rated Low, raise that area's
  Likelihood next time (predicted against actual defect clusters).

## Results

Every planned ID gets one row per platform in the results table: `PASS`, `FAIL`, `BLOCKED` or `NOT RUN` with the
reason. A run that did not meet the plan's condition (a quick variant, another language, the wrong build) is
`BLOCKED`, never PASS. A bug found outside the plan gets a new case in the plan before it is reported, so the next
run repeats it. `validate_e2e_plan.py <plan> --results <summary>` checks all of this.
