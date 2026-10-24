# device-e2e

A Claude Code plugin for end-to-end testing of a mobile app on real devices from a Mac: an iPhone through
WebDriverAgent and an Android phone through adb + uiautomator. It ships the `device-tester` agent, the
`device-e2e:playbook` skill, a deterministic plan/results validator and two Python drivers with one interface.

Plugin documentation: [English](plugins/device-e2e/README.md) · [Tiếng Việt](plugins/device-e2e/README.vi.md) ·
[日本語](plugins/device-e2e/README.ja.md)

## Install

```sh
claude plugin marketplace add nccong85/device-e2e
claude plugin install device-e2e@device-e2e
```

Recommended alongside it: `review-gate` from
[escanner-agent-kit](https://github.com/nccong85/escanner-agent-kit), whose hook stops agents running destructive
git commands. `/dev-pipeline:task-decompose` and `/dev-pipeline:implement` from the same kit route device tasks to
`device-e2e:device-tester`.

## Tests

```sh
bash tests/run.sh
```

Python 3 standard library only. The tests fake adb and WebDriverAgent; no device is needed.

## History

Split out of [escanner-agent-kit](https://github.com/nccong85/escanner-agent-kit) at its commit `c07f236`.

## License

MIT
