# Local verification and retired Actions

Alexa's October 15 instruction removes reliance on Actions and paid automation.
All 45 default-branch workflows are preserved byte-for-byte under
`archived-workflows/`; their original names, Git blob identities and modes are
recorded in `retired-actions.json`. Fourteen workflow files had scheduled
triggers. The daily `self-healing.yml` job generated dependency PRs #2–#14;
the archived weekly dependency job also contained a force push. No archived
command is executed by this migration.

Runtime source, dependency manifests/lock and deployment configuration are
unchanged. The daily PR branches and original draft runtime-repair PR #1 stay
preserved; stopping a generator does not establish which dependency updates are
safe or superseded. Deployment, publishing, issue-comment replies, automatic
assignment and old auto-approval are stopped on the default branch.

```sh
python3 scripts/local_check.py --structure-only
python3 -m unittest discover -s scripts/tests -v
python3 scripts/local_check.py
```

The first command verifies archive hashes, absence of active workflow files and
the five pinned runtime inputs; it explicitly reports runtime `NOT_RUN`. The
default command additionally requires declared/installed local TypeScript,
Vitest, Hono and a real test corpus before running TypeScript and Vitest. It
never installs packages, invokes npx, contacts a provider or deploys. Failures
propagate. `BLOCKED` exits 2; failed verification exits 1. Structure-only success
must never be published as a successful application-test status.

Current runtime verification is **BLOCKED**: package.json names `vitest` without
declaring it, and main has no application tests. This migration does not repair
or qualify the inherited Worker backend. PR #1 contains separate proposed
runtime/test repairs and remains draft; preserve and review it independently.
Node dependencies are absent in this session, so no mesh typecheck, HTTP,
WebSocket, Cloudflare engine, deployment or security-audit pass is claimed.

Use the existing [Garage local PR worker](https://github.com/blackboxprogramming/blackroad-garage/blob/main/docs/local-github-worker.md)
for owner-host scheduling after real local verification and independent review
are configured. No second scheduler or cloud model is introduced here. This
repository is not yet admitted to an autonomous merge policy.

Repository-level Actions settings and queued/running historical jobs are not
changed by moving source. Workflows on old branches can still exist. The linked
connector cannot disable account/repository Actions or cancel existing runs;
that administration boundary remains in the existing
[rollout issue](https://github.com/blackboxprogramming/blackroad-garage/issues/21).

Retirement uses a commit whose single parent is the observed main head and an
ordinary non-force fast-forward update. This avoids opening another PR while
main still has a `pull_request_target` welcome job and unsafe auto-approval
handlers. A concurrent main update must reject that sibling commit rather than
be overwritten. Original application/history and all archive blob modes are
checked through fresh GitHub tree readback.
