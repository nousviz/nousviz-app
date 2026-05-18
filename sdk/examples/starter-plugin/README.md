# Starter Plugin

> **This is a template.** Replace every instance of `starter-plugin`, `Starter Plugin`, and `starter_` with your own plugin name before publishing.

A template NousViz plugin demonstrating the full plugin contract.

## What this plugin does

<!-- Replace with a clear description of your plugin -->

This template plugin syncs items from an external MySQL database into NousViz and exposes them via a dashboard, data port views, and insight cards.

## Requirements

- NousViz v0.1.1 or later
- PostgreSQL 14+ (included in NousViz core)
- Access to the external MySQL database configured in plugin settings

## Installation

Install from the NousViz marketplace: search for **Starter Plugin** and click Install.

After install:
1. Go to **Plugins → Starter Plugin → Settings**
2. Enter your MySQL connection details
3. Click **Test Connection** to verify
4. Click **Sync Now** to run the first sync

## Configuration

| Setting | Description | Required |
|---------|-------------|----------|
| Host | MySQL hostname | Yes |
| Port | MySQL port (default: 3306) | No |
| Database | Database name | Yes |
| Username | MySQL username | Yes |
| Password | MySQL password | Yes |

## Data

This plugin creates two tables in NousViz's Postgres database:

| Table | Description |
|-------|-------------|
| `starter_items` | Items synced from the external source |
| `starter_events` | Sync audit log |

Data is updated every 6 hours. Run **Sync Now** for an immediate update.

## Limitations

- Does not support real-time updates — poll interval minimum 15 minutes
- Maximum 100,000 items (contact us for higher limits)

## Development

See `docs/plugin-architecture.md` in the NousViz repo for the full plugin development guide.

## License

MIT
