# Deploy Workflow (pre-v1.0)

**Status:** active — this is how deploys work during the v0.x pre-release cycle.
**Revisit:** at v1.0. A public release needs staging/prod separation, branch-gated deploys, and a deploy-state surface in the UI. See "Future changes" below.

---

## The loop

```
local edit on testing branch (uncommitted)
    ↓
./scripts/deploy-local.sh      ← rsyncs working tree to the deploy target
    ↓
smoke test on live server (manually + automated smoke-test.sh)
    ↓
works?
    ├── yes → git commit on testing
    │            ↓
    │       all scoped changes shipped? → merge testing → main, tag v0.X.Y
    │                                         ↓
    │                                    re-run deploy-local.sh from main (optional — same code)
    │
    └── no → fix locally → deploy again
```

## Why deploy-before-commit

This is a solo-operator pattern for the pre-v1.0 cycle. Deploying the working tree before committing means:

- Real-server validation catches "works on Mac, breaks on Ubuntu" before anything enters git history
- No WIP / "fix typo" / "try again" commits polluting the log
- Small blast radius — rollback is "rsync the previous state back"; no git revert ceremony
- Fast iteration — no commit between each change you're testing

Tradeoff accepted: the server can be ahead of (or different from) git `testing` for brief windows during validation. That's a known property, not a bug. Once the change works, commit; the window closes.

## The one branch rule

Always be on `testing` locally when running `deploy-local.sh`. The script doesn't enforce this today (pre-v1.0 tolerance), so it's on you:

```bash
git rev-parse --abbrev-ref HEAD   # should print: testing
```

If you need to deploy from `main` (e.g., after a merge to re-sync the server with the tagged release), that's fine — but it should be rare and deliberate, not accidental.

## What the deploy script does

`./scripts/deploy-local.sh` in order:

1. Captures current branch + short SHA (for the deploy log)
2. Warns if you have uncommitted changes — offers to continue (you'll almost always say yes during validation)
3. TypeScript type check (`npx tsc --noEmit`) — aborts on errors
4. Frontend build (`npm run build --silent`)
5. rsync working tree → `root@your-server-ip:/opt/nousviz/`
6. Runs plugin migrations on server (idempotent — only applies new ones)
7. Reloads nginx (preserves SSL config)
8. `pm2 reload ecosystem.config.js --update-env` — graceful, zero-downtime, keeps all processes
9. Waits 3s, health check on `127.0.0.1:8000/api/health`
10. SSL cert expiry check (warns if <7 days)
11. Runs `scripts/smoke-test.sh` against the server
12. Appends deploy line to `logs/deploys.log` on the server

Exit code 0 means the deploy landed and the smoke test passed. Exit code non-zero means something failed — don't commit the code yet.

## After the deploy

### Manual smoke checks (2-5 minutes)

Open `https://<your-domain>/` (the server you deployed to) and confirm:
- Page loads, topbar renders, no console errors
- The specific thing you just changed behaves correctly
- System health indicator still shows green

Any feature you touched: exercise it end-to-end. The automated smoke-test.sh catches regressions on the critical paths but not feature-specific behaviour.

### Commit once satisfied

```bash
git add <files>                   # prefer explicit over `git add .` — avoids staging todo/ changes
git commit -m "<message per SOP commit format>"
```

Commit message format is in `todo/WORKFLOW-SOP.md` section 8. Short prefix (`fix:` / `feat:` / `refactor:` / `docs:`), ticket ID in parens.

### If the deploy broke something

Fix locally → re-run `deploy-local.sh`. The working tree gets rsync'd again, replacing the broken code on the server. No rollback needed — you just deploy the fix.

If you need to fully revert to what was there before your edits:
```bash
git stash                         # stash your working changes
./scripts/deploy-local.sh         # redeploys the last committed state
git stash pop                     # retrieve your changes when ready
```

## Releasing (testing → main → tag)

When a release's scope is complete and everything on the server is working:

1. All intended changes committed on `testing`
2. `git checkout main && git merge testing` (or merge via GitHub PR if preferred)
3. `git tag v0.X.Y` + `git push origin main v0.X.Y`
4. Optionally re-run `./scripts/deploy-local.sh` from `main` so the server's state matches a tagged commit exactly (no-op in terms of code, but tidier for audit)
5. `git checkout testing` and continue

The SOP (section 2) covers this. Key rule: `testing → main` is never automated — always your explicit decision after server review.

## What's NOT in this workflow (by design, for now)

- **No staging environment.** The deploy target is both staging and production. A single operator, no paying customers, $5 VPS. Separation would double infra cost for minimal gain.
- **No branch guards on deploy.** The script doesn't enforce `testing` branch. You do, by habit.
- **No deploy-state surface in the UI.** The topbar doesn't show "testing-wip" vs "release v0.3.0". You remember which it is.
- **No automated `testing → main` merge.** Manual decision, every time.
- **No rollback command.** `rsync` the previous state back, or redeploy a working commit.

These are all acceptable at current scale. They become non-acceptable when the project has external users who care about uptime.

## Future changes (post-v1.0)

When v1.0 ships and there are real external users, this workflow gets tightened. Expected shape (not yet planned as a release):

- **Branch guards** in `deploy-local.sh`:
  - Default: require `testing` branch
  - `--release` flag: require `main` at a tag
  - `--force` escape for emergencies
- **Deploy-state file** on the server (`/opt/nousviz/.deploy_state`) recording: kind (testing-wip / release), source SHA, tag if applicable, timestamp
- **`/api/health/deploy` endpoint** exposing the deploy state
- **Topbar badge** reading `/api/health/deploy` and showing "testing build" vs "v0.X.Y"
- **Automated rollback**: `deploy-local.sh --rollback` restores the last snapshot. (B189's pattern was a one-off for SSL setup; generalising it to a deploy-level rollback is the full version.)
- **Optional:** second VPS for real staging/prod split, if uptime SLAs become a thing

The current workflow document gets revised to the post-v1.0 shape when those items land. Until then, this doc is the canonical reference.

## FAQ

**Q: "Am I testing on the deploy target?"**
Yes. It's the only server. Whatever's deployed there is what you're testing. Your local dev server (`./scripts/dev.sh`) is for quick iteration; the deploy target is for validation before commit.

**Q: What if my laptop dies mid-development?**
Uncommitted changes are lost. Commit often once a change works, even if the release isn't complete. You can keep multiple feature commits on `testing` before merging — the branch is cheap.

**Q: How do I know what code is currently on the server?**
`ssh root@your-server-ip 'cat /opt/nousviz/VERSION && git -C /opt/nousviz rev-parse HEAD 2>/dev/null || echo "no git on server"'` — VERSION file shows the release version string. There's no git repo on the server (rsync, not pull), so there's no commit SHA server-side. If you need certainty, grep for a known recent change in the server's source files.

**Q: What if someone else commits to main while I'm mid-deploy?**
Not a scenario right now — solo operator. When it becomes one, the workflow tightens per "Future changes" above.

**Q: Where are deploys logged?**
`/opt/nousviz/logs/deploys.log` on the server. Format: `<timestamp> v<VERSION> <short-sha> <branch>`.

**Q: Can I deploy uncommitted changes?**
Yes — that's the whole point of the pre-commit validation pattern. The script will warn and prompt for confirmation. Answer `y`.

**Q: What if the smoke test fails?**
Exit code non-zero. Don't commit. Fix what broke, redeploy.

---

**Last updated:** 2026-04-16 — documented the pre-v1.0 deploy-first-then-commit workflow. Revisit at v1.0.
