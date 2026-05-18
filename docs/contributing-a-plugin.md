# Contributing a Plugin to the NousViz Marketplace

This guide covers the community plugin submission process: how to package your plugin, what the review checklist covers, and how versioning works after your plugin is listed.

---

## Overview

Community plugins are third-party plugins listed in the NousViz Marketplace. They are maintained by external authors — not the NousViz core team. Operators install them with a one-click install, and they run with the same trust level as the core API (see [Security model](plugin-architecture.md#16-security-model)).

---

## Before you start

Read [Plugin Architecture](plugin-architecture.md) — particularly the isolation model, `plugin.yaml` schema, and the security model section. Your plugin must follow the architecture documented there.

For the runtime API your plugin code calls (`get_pg_conn`, `BaseSyncScript`, `progress.report`, `log_event`, etc.), see the [SDK Reference](sdk-reference.md).

---

## Declaring permissions (B247, v0.9.10.6+)

Plugins with HTTP routes should declare a `permissions:` block in `plugin.yaml`. This binds each route to a per-plugin RBAC permission of the form `plugin.<slug>.<level>` so operators can grant or revoke access in `/system/permissions` without editing your code.

**Levels** (in increasing privilege order):

| Level | Default role | Use for |
|---|---|---|
| `read` | viewer+ | Reading plugin data (GETs that don't mutate) |
| `write` | analyst+ | Creating/editing plugin data |
| `configure` | admin+ | Plugin settings, secrets, schedules |
| `admin` | superadmin | Destructive ops (uninstall hooks, data wipe, role overrides specific to your plugin) |

### Minimal example

```yaml
# plugin.yaml
name: my-plugin
display_name: My Plugin
version: 1.0.0
permissions:
  default: read
```

This single block tags every route under `/api/plugins/my-plugin/*` with `plugin.my-plugin.read`. Viewer-and-up roles can call them; analyst+ can call any future write/configure routes once you bump them per-route (below).

### Per-route overrides

```yaml
permissions:
  default: read
  routes:
    # Specific path glob bumps to admin-level
    - path: /api/plugins/my-plugin/admin/*
      level: admin
    # All POSTs require write-level (regardless of path)
    - method: POST
      level: write
    # Specific method + path combo
    - method: DELETE
      path: /api/plugins/my-plugin/data/*
      level: configure
```

Rules apply in **first-match-wins** order — list more specific rules before more general ones. `default:` is the fallback when no rule matches.

### What happens if you omit `permissions:`

Plugins without a `permissions:` block fall back to the legacy B229 method-derived default — `plugins.read` for GETs, `plugins.configure` for everything else. This works (your plugin keeps running) but operators can't fine-tune per-plugin grants for you. The matrix UI flags these rows with a `legacy` badge so the operator knows to ask you to add `permissions:` in your next release.

### Validation

The platform parses your `permissions:` block at install time. Errors (unknown level, missing required fields, invalid HTTP method) **block install** with a clear error message — fix the manifest and reinstall. There's no silent fallback for typos.

### See also

- [`/system/permissions`](https://nousviz.online/system/permissions) — operator's view of what permissions exist and which roles hold them.
- The platform's static permission catalog: `apps/api/src/rbac/permissions.py`.

---

## Submission process

### Step 1: Create your plugin repo

Name your repository: `github.com/{org}/nousviz-plugin-{slug}`

Example: `github.com/acmecorp/nousviz-plugin-acme-analytics`

The `{slug}` must be lowercase, hyphenated, and globally unique in the marketplace. Check `plugins/official/` and `plugins/community/` in the core repo — if a directory with your slug already exists, choose a different name.

### Step 2: Build and test locally

Use the starter plugin template in `sdk/examples/starter-plugin/` as a reference. Run the validation checklist in [Section 15](plugin-architecture.md#15-validation-checklist) against your plugin before submitting.

At minimum:
- Fresh install on clean Postgres completes without errors
- `GET /api/plugins/{slug}/health-check` returns 200
- Uninstall with `remove_data=true` drops all plugin tables cleanly

### Step 3: Tag a release

Your `plugin.yaml` must declare a `version` field using semantic versioning (`MAJOR.MINOR.PATCH`). The Marketplace installs by cloning the git tag `v{version}`.

```bash
git tag v1.0.0
git push origin v1.0.0
```

Installs without a matching git tag will fail. Never use branch names as versions.

### Step 4: Open a PR to the core repo

Add a `plugin.yaml` stub to `plugins/community/{slug}/plugin.yaml` in `github.com/nousviz/nousviz-app`.

Your community stub must include:

```yaml
name: your-plugin-slug
display_name: Your Plugin Name
version: "1.0.0"          # must match a git tag in your repo
category: analytics        # see plugin.yaml schema for valid values
description: >
  One paragraph. What does your plugin do? What data source does it connect to?
  What value does it provide to the operator? Keep under 100 words.
license: MIT               # or Apache-2.0 / Sustainable Use
repository_url: https://github.com/your-org/nousviz-plugin-your-slug.git
homepage: https://github.com/your-org/nousviz-plugin-your-slug
publisher:
  name: Your Name or Org
  website: https://example.com
tags: [analytics, your-tag]
```

The `repository_url` field is required for community plugins — it tells the install endpoint where to clone from.

### Step 5: PR review

The core team will review:

| Check | What we verify |
|-------|----------------|
| Slug uniqueness | No existing official or community plugin uses this slug |
| `repository_url` reachable | The URL resolves and the version tag exists |
| `plugin.yaml` validity | Required fields present, category valid, description quality |
| Security contract | Plugin does not patch `PUBLIC_PREFIXES` or read core DB tables it doesn't own |
| Isolation rules | No imports from other plugin modules; no cross-plugin DB access |

We do not review your plugin's full source code — that is the operator's responsibility. We review the manifest for correctness and flag obvious security violations.

### Step 6: PR merged

Once merged, your plugin appears in the Marketplace for all NousViz users with a **Community** badge. Operators see a trust warning before installing.

---

## Publishing updates

To publish a new version:

1. Bump `version` in your plugin repo's `plugin.yaml`
2. Tag the release: `git tag v1.2.0 && git push origin v1.2.0`
3. Open a PR updating `version` in `plugins/community/{slug}/plugin.yaml` in the core repo

Operators will not automatically receive the update — they must reinstall. A future release will add "update available" notifications.

---

## Version pinning model

The core repo's `plugins/community/{slug}/plugin.yaml` acts as the version lock. When an operator installs your plugin, the Marketplace clones `--branch v{version}` from your `repository_url`. This prevents your plugin from pushing breaking changes to existing installs.

You control when operators receive updates: only when a PR updating the version in the core repo is merged.

---

## Removing a plugin

Open a PR removing your `plugins/community/{slug}/` directory. Existing installs are not affected — the plugin remains installed until the operator explicitly uninstalls it.

---

## Trust model and operator responsibility

Installing a community plugin grants it full API process permissions. This is documented in the [Security model](plugin-architecture.md#16-security-model). Operators are responsible for reviewing community plugins before installing them in production.

The Marketplace shows a trust warning modal for all community plugins. It is not possible to suppress this warning.

---

## Public API documentation (opt-in)

**TL;DR**: by default, your plugin's HTTP routes are *not* shown in the
platform's public OpenAPI spec at `/openapi.json` or in the interactive
reference at `/docs/api`. Operators can still call them; they're
just not auto-documented. Opt in if you want public docs.

### How to opt in

Add to your plugin's `plugin.yaml`:

```yaml
openapi_public: true
```

When set, the platform includes all routers your plugin registers (main,
extra, widget, module) in the public spec, grouped under your plugin's
own tag (default `plugin: <slug>` — override by setting `tags=[...]` on
your `APIRouter` constructor).

### Why default-private

Plugins ship behavior that's specific to the plugin author's use case. If
you're running NousViz internally and you've installed plugins from
multiple sources, you probably don't want every plugin's routes leaked
into the platform's public docs surface — especially if some are
proprietary integrations or expose endpoints intended only for the
plugin's own UI.

The platform's public spec covers the platform itself: the core 152
handlers in `apps/api/src/routes/*.py`. Plugin authors decide their own
opt-in posture per plugin.

### Per-plugin private docs

If your plugin has rich public-facing endpoints worth documenting but you
don't want them in the platform's spec, you can ship your own
`/openapi.json` from the plugin under a plugin-prefixed path. See the
[Scalar embedding docs](https://github.com/scalar/scalar) for hosting
patterns.

### Tagging convention if you opt in

If `openapi_public: true` is set, the recommended tag for your routes is
`plugin: <slug>`:

```python
from fastapi import APIRouter
from nousviz_sdk import router_for_plugin

router = router_for_plugin("avizo-jira")  # already has prefix=/api/plugins/avizo-jira
router.tags = ["plugin: avizo-jira"]
```

The platform's `/docs/api` will then group your routes under this tag
in the left navigation, alongside (but distinct from) the platform's
`plugins`, `sync`, etc. tag groups.

For the canonical Python SDK reference (the contract your plugin programs
against), see `docs/sdk-reference.md` *(arrives in v0.9.7.3)*.
