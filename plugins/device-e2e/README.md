**English** · [Tiếng Việt](README.vi.md) · [日本語](README.ja.md)

# device-e2e

A plugin for automated end-to-end testing of mobile apps on real devices from a Mac: it drives an iPhone through
WebDriverAgent and an Android phone through adb + uiautomator.

## Components

| Component | Purpose |
|---|---|
| `agents/device-tester.md` | **Main executing agent:** Writes the test cases, drives the phones, finds the cause of each failure (tool or app), cleans up after the test and reports the results (PASS/FAIL/BLOCKED) with evidence. *Note: It changes app code only if the brief asks for it.* |
| `skills/playbook/` | **Procedure and reference docs:** How to run the steps, classify failures, work with the devices and report. Comes with reference docs (`references/`): how to design test cases, a glossary that defines each status (PASS/FAIL/...), separate docs for iOS/Android, and a list of common traps. |
| `skills/playbook/e2e_test_plan.template.md` | **Test plan template:** A standard format for the inputs, risk assessment, state/event matrix, run steps and the time budget for each case. It also includes the results file template and the defect entry format (`BUG-n`). |
| `bin/validate_e2e_plan.py` | **Test plan checker:** Runs on its own, without an AI model, to cross-check the test plan. It makes sure every requirement (spec) is covered (or has a clear reason to skip it), there are no redundant cases, no empty states, and the total run time fits the limit. With the `--results` flag, it checks the actual results file against the plan (whether the evidence really exists, whether each bug entry is complete). |
| `skills/playbook/harness/` | **Device drivers:** `IosDriver` (HTTP calls to WebDriverAgent) and `AndroidDriver` (adb + uiautomator) share the same set of methods. `evidence.py` names and saves the evidence files (screenshot, UI tree, logcat or iOS crash reports, Android screen recording). Configured through environment variables (`WDA` for the iPhone's IP, `E2E_*` for the rest) and uses only the Python 3 standard library. |
| `commands/init.md` | Holds the `/device-e2e:init` command, which creates the config file `.claude/device-e2e/project.md` from the template and lists what you still need to fill in. |
| `skills/playbook/project.template.md` | **Project config template:** Where you declare what the agent needs to run (devices, app ID, build commands, harness paths, and how to clean up data). |

## Setup

1. **Install the plugin:** Run `claude plugin marketplace add nccong85/device-e2e`, then
   `claude plugin install device-e2e@device-e2e`. *(Recommended: also install the `review-gate` plugin from
   [escanner-agent-kit](https://github.com/nccong85/escanner-agent-kit) for a guard hook that stops the agent running
   git commands that destroy data.)*
2. **Initialize the project:** Run `/device-e2e:init` in the project folder. It creates the config file
   `.claude/device-e2e/project.md` (never over an existing one) and reminds you to fill in what is missing.
3. **Set up the real devices:**
   - **iPhone:** Build WebDriverAgent onto the phone once, and enable Developer Mode and UI Automation. Keep the
     iPhone unlocked and on the same Wi-Fi as the Mac.
   - **Android:** Plug in the cable and make sure the host (Mac, Linux or Windows; iOS needs a Mac) sees the device (check with `adb devices`).

   Details: [`ios.md`](skills/playbook/references/ios.md), [`android.md`](skills/playbook/references/android.md).
4. **Write the suite:** Write your app-flows module and suite on top of the two drivers. The skill explains the shape.

## Usage

### How it is invoked

The plugin has three parts, and Claude Code calls each one differently:

| Part | How it is called |
|---|---|
| Skill `playbook` | Claude loads it on its own when the request matches the skill's description (test on a real phone, e2e or regression on device, verify a fix on hardware…). Call it directly with `/device-e2e:playbook`. |
| Agent `device-tester` | The main session delegates to it when the request matches its description. Ask for it by name ("use the device-tester agent …") or type `@agent-device-e2e:device-tester`. The agent preloads the `playbook` skill at startup. |
| Command `/device-e2e:init` | Runs only when you type it. |

Two facts shape how you write the request:

- **The agent does not see the conversation.** It runs in its own context and gets only the brief the main session
  writes from your request. Everything it needs (spec, plan, platforms, budget, what you approved) must be in what
  you type.
- **The agent cannot ask you questions.** When a fact or an approval is missing it stops with `BLOCKED: …`; the main
  session tells you, and you send the next request.

### The brief

The agent takes these fixed lines:

```
SPEC: <spec path>
PLAN: <plan path> | write (MODE: feature | release)
PLAN_APPROVED: <owner, YYYY-MM-DD> | none
BUILD: installed | approved <owner, YYYY-MM-DD>
PLATFORMS: ios, android | ios | android
CASES: all | <IDs>
BUDGET: <device minutes>
RESULTS: <results summary path> (default: the path in project.md)
```

Without `SPEC`, `PLAN`, `PLATFORMS` or `BUDGET` the agent stops with `BLOCKED: brief missing <field>`. Approval
counts only in the brief: an *Approved by* line inside the plan file does not.

### Two passes

**Pass 1: write the plan.** The agent writes the plan, runs `validate_e2e_plan.py` until it exits 0, and stops with
`BLOCKED: plan <path> needs owner approval` before it touches a device.

> Use the device-tester agent: SPEC docs/specs/import_pdf.md, PLAN write (MODE: feature), PLAN_APPROVED none,
> BUILD installed, PLATFORMS ios, android, CASES all, BUDGET 60.

**Review.** Read the plan (cases, device minutes, *Not covered*) and edit it if needed.

**Pass 2: run.** The agent runs `READY` → `DRY` → the cases in order → `EXPLORE` (if planned) → `DIAG`, triages every FAIL (fixes and re-runs
harness bugs, collects evidence for app bugs), cleans up and writes the results summary: a test completion report in the
ISTQB / ISO/IEC/IEEE 29119-3 shape (verdict against the plan's exit criteria, metrics, results, defects, deviations,
residual risk, lessons learned).

> Use the device-tester agent: SPEC docs/specs/import_pdf.md, PLAN test/e2e/import_pdf_plan.md,
> PLAN_APPROVED nccong 2026-10-24, BUILD installed, PLATFORMS ios, android, CASES all, BUDGET 60.

The agent ends with five lines:

```
E2E: ios pass=<n> fail=<n> blocked=<n> not_run=<n> · android pass=<n> fail=<n> blocked=<n> not_run=<n>
VERDICT: <go | no-go | go with risks>: <why>
APP_BUGS: <none | BUG-n severity priority title>
BLOCKERS: <none | what stopped a case or the run>
REPORT: <results summary path>
```

Other common requests: re-run only the failed cases (`CASES: E3, E7`), one platform only (`PLATFORMS: android`),
allow a rebuild (`BUILD: approved nccong 2026-10-24`, with the build commands in `project.md`).

A short request also works, e.g. "test PDF import on both real phones, spec at docs/specs/import_pdf.md, 60
minutes". The main session builds the brief, but any line still missing makes the agent report `BLOCKED`.

## What it will not do

- Build or reinstall the app unless the brief says the owner approved it. Uninstalling wipes app data.
- Use `xcodebuild test` or `flutter drive` on a phone whose data matters.
- Report a PASS without evidence read from the device, or for a case whose precondition was not proven.
- Run the device before the owner approved the test plan, or drop a planned case from the results.
