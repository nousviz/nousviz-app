# NousViz Plugins

## Directory layout

```
plugins/
├── utilities/                # Bundled utility plugins (shipped in this repo)
│   ├── clickhouse/           # ClickHouse analytics backend
│   ├── mysql/                # Shared MySQL connection for data plugins
│   └── webhooks/             # Inbound + outbound webhook handling
├── community/                # Community-submitted manifest stubs (clone-on-install)
└── installed/                # Plugins installed at runtime via the marketplace (gitignored)
```

The starter template for building your own plugin lives at [`sdk/examples/starter-plugin/`](../sdk/examples/starter-plugin/).

## Installing plugins

Plugins are installed through the **Plugin Marketplace** in the app:

1. Go to **Marketplace** in the sidebar
2. Click **Install** on a plugin
3. The plugin is cloned into `plugins/installed/{slug}`
4. Migrations run automatically
5. Configure connection credentials in **Connections**
6. Data syncs on the configured schedule

### Plugin sources

| Source | Where the code lives | How operators install it |
|--------|----------------------|--------------------------|
| Bundled utilities | `plugins/utilities/{slug}/` in this repo | Marketplace → Utilities |
| Community | Third-party GitHub repos referenced by `plugins/community/{slug}/plugin.yaml` | Marketplace → Community |
| Private | Any Git URL the operator provides | Install Plugin page → Private install |

## Building your own plugin

Start from the [`starter-plugin`](../sdk/examples/starter-plugin/) template and read the [SDK reference](../sdk/README.md).

Every plugin needs:

- `plugin.yaml` — manifest (metadata, connections, datasets, dashboards, alerts, sync schedule)
- `src/sync.py` — data sync script
- `storage/migrations/` — SQL migrations run on install
- `dashboards/*.yaml` — widget layout specs (optional)
- `alerts/*.yaml` — alert templates (optional)
- `dataport.yaml` — Data Explorer row formatting metadata (optional)
