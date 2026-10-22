# Review rules for gitgeist

This file holds the standing acceptance rules for the maintainer's review loop.
The loop, its roles, and its limits are described in [roles](roles.md). The
rules apply to every work item that goes through the loop, on top of the
item-specific acceptance rules written in the Plane work item.

The rules do not replace [AGENTS.md](../AGENTS.md) or the product contracts in
`docs/product/`. They select the parts that a reviewer can decide from
evidence, one line per rule.

## Standing rules

Each rule has a stable id, one requirement, and one way to check it. A rule is
accepted only if a test, a CI check, a script, a log, or one screenshot can
decide it.

```text
R1 | Every "verify" check (GitHub Actions, ubuntu-latest, one per supported Python version) is green on the latest PR commit | check: PR Checks tab
R2 | Every bug fix adds a test that fails without the fix, including fixes that touch only tests or fixtures | check: PR diff + raw test log with a red run before the fix
R3 | The PR references its Plane work item (GITGEIST-<n>) and describes the change | check: PR description
R4 | No changes outside the scope of the work item | check: list of changed files
R5 | Tests stay offline: no test calls OpenRouter, an LLM or image CLI, or the network; backends are faked or stubbed | check: green CI run (no secrets configured) + diff of tests/
R6 | Every red-test log for the PR comes with the literal command that produced it | check: raw log and command in the PR description, a PR comment, or a file under docs/evidence/ linked from the PR body
R7 | A red run that fails only because a module is missing does not count as a red run | check: raw red log fails on an assertion or the expected error, not on ModuleNotFoundError or ImportError
R8 | A breaking API change adds a CHANGELOG entry and updates every spec that contains the affected signature | check: diff of CHANGELOG.md + search of docs/ for the old signature
R9 | The PR does not reference documents that exist only on an unmerged branch | check: every linked repository path exists on main or in the PR diff
R10 | A plan criterion the change does not meet is flagged in the PR, and either the plan is changed or the owner decides | check: PR description + plan diff or the owner's decision in the PR or Plane
R11 | Spec amendments are written in the language of the spec they amend | check: diff of docs/
```

Notes on evidence:

- R1: the `verify` jobs in [the CI workflow](../.github/workflows/ci.yml) run
  `python -m pytest tests` (the `full_command` in
  `.agents/project-profile.yaml`) on every Python version the project
  supports (`requires-python` in `pyproject.toml`). CI runs on Linux; a change
  whose behavior differs on Windows also needs a log from a Windows run.
- R2: keep the raw red run: the unedited pytest output of the new test against
  the code without the fix, with the command, commit, and exit code. Keep the
  red run, or revert and restore the fix before the final check. A summary of
  the failure is not evidence. A fix that changes only tests or fixtures is
  still a bug fix. For a defect that shows only on one platform, the red run
  is either a red run of that platform's CI job or a raw log from that
  platform at the commit before the fix.
- R5: CI has no API keys, so a test that needs a real backend fails there. A
  test that skips itself when a key is missing does not meet R5 either; it
  must use the `fake` backend or a stub.
- R6: the command is the exact one that was run, copied as typed, not a
  description of it, including any environment setup or wrapper that ran it
  (for example a script that starts the tests in a minimal environment).
  Secret values are left out of the command. A log without its command does
  not count as evidence. The log may be in the PR description, in a PR
  comment, or in a file under `docs/evidence/` that the PR body links to.
- R7: an import error shows only that the code under test does not exist yet.
  A red run for R2 must reach the test and fail on the behavior it checks.
- R8: "every spec" includes specs in `docs/features/` and `docs/product/` that
  quote the old signature, in any language.
- R10: the owner is Tomasz; his decision is recorded in the PR or the Plane
  work item.

## Item rules

Rules for a single work item live in its Plane description, in a section named
"Acceptance rules", with ids `T1`, `T2`, and so on:

```text
## Acceptance rules
T1 | <behavior> works when <condition> | check: test <confirmed test path>
T2 | Feature documentation updated | check: diff of docs/
```

## Verdict format

The reviewer posts one comment per pass on the Plane work item. Every standing
rule and every item rule gets exactly one line:

```text
Pass 2/3 | PR #<n> | commit <sha> | CI verify: <result>
R1 PASS
R2 FAIL: fix in <file> has no new test
R3 PASS
R4 PASS
R5 PASS
R6 PASS
R7 PASS
R8 PASS: not applicable, no API change
R9 PASS
R10 PASS
R11 PASS
T1 PASS
T2 FAIL: docs/ unchanged
Result: FAIL (2), back to the doer
Rule proposal: none
```

A rule that does not apply to the change is reported as `PASS: not applicable`
with the reason. Findings that no rule covers are not a FAIL. They go into the
"Rule proposal" line for the owner to decide.

## Turning defects into tests or rules

- Every defect found in review or after merge ends as a pytest test in
  `tests/` or as a new rule in this file. A comment alone is not enough.
- A FAIL for a defect closes only when the new test exists, fails without the
  fix, and passes with it in the `verify` check.
- If no test can be written, the defect becomes a rule checked by a command log
  or one specific screenshot.
- A defect too large for the current item gets its own Plane work item with the
  `bug->test` label. It closes only with a merged test.

## Changing the rules

- Only the owner changes this file, directly or by approving a PR that changes it.
- The doer and the reviewer may only propose changes.
- A change made during a pass applies from the next work item unless the owner
  decides otherwise.
