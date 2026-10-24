# Changelog

All notable changes are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

- Moved out of escanner-agent-kit into its own repository and marketplace (`device-e2e@device-e2e`).
- Dropped the hard dependency on `review-gate`; it is now a recommendation.
- `validate_e2e_plan.py --results`: a pulled PDF, a screen recording (`.mp4`, `.mov`), `.heic` or `.gif` counts as an evidence file.
- `validate_e2e_plan.py --results`: `NOT RUN: budget` and `BLOCKED: <reason>` in the Status cell are accepted, with the text after the colon as the reason.
- `validate_e2e_plan.py --results`: every case PASS must cite an evidence file (a path with a directory, e.g. `evidence/E1_ios_1.png`), and every cited evidence file, in the table or a `BUG-n` entry, must exist relative to the summary.
- The agent, playbook, glossary and results template keep evidence in `evidence/` next to the summary, named `<ID>_<platform>_<n>.<ext>`.

## 1.0.0

- First release, as part of escanner-agent-kit 1.0.0.
