# Admin CLI

A web-based terminal at `/admin/cli` for superadmin users. Run management commands without SSH access.

---

## Access

Navigate to `/admin/cli` in the browser. Requires superadmin role — other roles see "Access Denied".

## Commands

### User Management

```
users list                        List all users with role, status, last seen
users create <email> <role>       Create user with generated password
users reset-password <email>      Generate new password for a user
users set-role <email> <role>     Change role (viewer/analyst/admin/superadmin)
users deactivate <email>          Disable a user account
users reactivate <email>          Re-enable a user account
```

### System

```
health                            Run health check and show results
version                           Show current NousViz version
config                            Show non-secret configuration values
env check                         Validate required environment variables
```

### Database

```
migrations status                 List all migration files
migrations run                    Run pending migrations (idempotent)
backup run                        Create a compressed database backup
backup list                       List existing backups with sizes and dates
backup restore <filename>         Show restore instructions for a backup
```

### Plugins

```
plugins list                      List installed plugins with versions
plugins sync <id>                 Trigger a manual sync for a plugin
```

### Jobs & Logs

```
jobs history [--limit N]          Show recent job runs (default: 10)
logs api [--lines N]              Tail API logs (default: 20 lines)
logs alerts [--lines N]           Tail alert runner logs
logs health [--lines N]           Tail health monitor logs
```

Logs accept `--lines`, `--limit`, or `-n` flags.

### Security

```
security audit                    Check security configuration
security rotate-key               Show encryption key rotation instructions
```

### Updates

```
update check                      Compare current version with latest GitHub release
```

### Terminal

```
clear                             Clear the terminal output
help                              Show all available commands
```

## Updating NousViz

The `update check` command shows available updates with the changelog. Updates are never automatic — you decide when to apply them.

```
update check       → shows current vs latest version + what's new
```

To apply an update, run on the server:

```bash
./scripts/update.sh              # update to latest
./scripts/update.sh v0.8.0       # update to specific version
./scripts/update.sh --dry-run    # preview without applying
```

The update script: creates a backup → pulls code → installs deps → runs migrations → builds frontend → restarts services → verifies health.

## Notes

- Commands are curated — no arbitrary shell execution
- All output is plain text, not interactive
- Command history navigable with up/down arrow keys
- Ctrl+L also clears the terminal
