#!/usr/bin/env bash
# Contracts inside the plugin: /device-e2e:init, the agent's brief and hand-off, and the playbook's links.
set -uo pipefail
PLUGIN="$(cd "$(dirname "$0")/.." && pwd)/plugins/device-e2e"
pass=0; fail=0
ok() { pass=$((pass+1)); }
ko() { fail=$((fail+1)); echo "FAIL $*"; }

# Nothing else creates .claude/device-e2e/project.md; device-tester reports BLOCKED without it.
E2E_INIT="$PLUGIN/commands/init.md"
[ -f "$E2E_INIT" ] && grep -q 'do not write to it' "$E2E_INIT" && grep -q 'skills/playbook/project.template.md' "$E2E_INIT" \
  && ok || ko "commands/init.md missing, or it may overwrite / names no template"
# device-tester's brief and hand-off are a contract with dev-pipeline's task-decompose and implement.
DT="$PLUGIN/agents/device-tester.md"
for k in 'SPEC:' 'PLAN:' 'PLAN_APPROVED:' 'BUILD:' 'PLATFORMS:' 'CASES:' 'BUDGET:' 'RESULTS:' 'BLOCKERS:' 'not_run=<n>' 'BLOCKED: brief missing'; do
  grep -qF "$k" "$DT" && ok || ko "device-tester.md lacks '$k'"
done
for f in references/test-design.md references/glossary.md e2e_test_plan.template.md; do
  grep -q "$(basename "$f")" "$PLUGIN/skills/playbook/SKILL.md" "$PLUGIN/skills/playbook/references/test-design.md" && ok || ko "$f is not linked from the playbook"
done
echo "plugin: pass=$pass fail=$fail"
[ "$fail" = 0 ]
