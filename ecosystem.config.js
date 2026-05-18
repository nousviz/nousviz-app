// pm2 ecosystem config — production process management
// Usage:
//   pm2 start ecosystem.config.js
//   pm2 reload all              # zero-downtime restart
//   pm2 status                  # check all processes
//   pm2 logs                    # tail all logs
//   pm2 save && pm2 startup     # survive server reboots
//
// Install location is read from NOUSVIZ_DIR env var or detected from __dirname.
// No hardcoded paths — works regardless of where you cloned the repo.

const APP_DIR = process.env.NOUSVIZ_DIR || __dirname;

module.exports = {
  apps: [
    // ── FastAPI backend ────────────────────────────────────────────
    {
      name: "api",
      cwd: APP_DIR,
      script: ".venv/bin/gunicorn",
      args: "apps.api.src.main:app --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 127.0.0.1:8000 --timeout 120 --graceful-timeout 30",
      interpreter: "none",
      env: {
        PATH: `${APP_DIR}/.venv/bin:/usr/local/bin:/usr/bin:/bin`,
      },
      max_memory_restart: "512M",
      restart_delay: 2000,
      max_restarts: 10,
      min_uptime: 5000,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: `${APP_DIR}/logs/api-error.log`,
      out_file: `${APP_DIR}/logs/api-out.log`,
      merge_logs: true,
      listen_timeout: 10000,
    },

    // ── Worker: alert runner (runs hourly via cron) ────────────────
    {
      name: "alerts",
      cwd: APP_DIR,
      script: ".venv/bin/python3",
      args: "apps/worker/src/run_alerts.py",
      interpreter: "none",
      cron_restart: "0 * * * *",   // restart every hour to re-run
      autorestart: false,          // don't restart between cron runs
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: `${APP_DIR}/logs/alerts-error.log`,
      out_file: `${APP_DIR}/logs/alerts-out.log`,
    },

    // ── Health monitor (runs every 5 minutes) ──────────────────────
    {
      name: "health-monitor",
      cwd: APP_DIR,
      script: "bash",
      args: "-c 'curl -s -X POST http://127.0.0.1:8000/api/health/record > /dev/null'",
      interpreter: "none",
      cron_restart: "*/5 * * * *",
      autorestart: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: `${APP_DIR}/logs/health-monitor-error.log`,
      out_file: `${APP_DIR}/logs/health-monitor-out.log`,
    },

    // ── Resource history snapshot (B273 v0.9.11.19, daily 03:30 UTC) ──
    //
    // One-shot cron worker. Reads /api/system/resources +
    // /api/system/diagnostics, compacts to top-20 per section,
    // persists one row to system_resources_history, prunes rows
    // older than 90 days. Powers sparklines and per-finding
    // timeline strips. Each row < 50 KB; 90 days ≈ 5 MB total.
    {
      name: "snapshot-resources",
      cwd: APP_DIR,
      script: ".venv/bin/python3",
      args: "apps/worker/src/snapshot_resources.py",
      interpreter: "none",
      cron_restart: "30 3 * * *",   // daily 03:30 UTC
      autorestart: false,            // one-shot
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: `${APP_DIR}/logs/snapshot-resources-error.log`,
      out_file: `${APP_DIR}/logs/snapshot-resources-out.log`,
    },

    // ── Retention cleanup (B279 v0.9.11.17, daily 04:00 UTC) ──────
    //
    // One-shot cron worker. Reads system_retention_overrides, runs
    // every UNPAUSED policy, ANALYZE-s the affected tables, and writes
    // a structured summary to app_logs. Per operator decision
    // 2026-05-04, every policy ships paused — first run is a no-op.
    {
      name: "retention-cleanup",
      cwd: APP_DIR,
      script: ".venv/bin/python3",
      args: "apps/worker/src/retention_cleanup.py",
      interpreter: "none",
      cron_restart: "0 4 * * *",   // daily 04:00 UTC
      autorestart: false,           // one-shot
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: `${APP_DIR}/logs/retention-cleanup-error.log`,
      out_file: `${APP_DIR}/logs/retention-cleanup-out.log`,
    },

    // ── Async job worker (P107 v0.8.2) ─────────────────────────────
    //
    // Long-running process that dequeues rows from job_runs (status=queued)
    // and runs plugin sync scripts. Plugins opt in via
    // `execution_mode: async` in plugin.yaml. Sync-mode plugins continue
    // to execute inline on /api/plugins/:id/sync.
    //
    // autorestart: true — worker should always be running. PM2 respawns
    // on crash; on restart the worker marks any orphaned 'running' rows
    // as error.
    {
      name: "jobs-worker",
      cwd: APP_DIR,
      script: ".venv/bin/python3",
      args: "apps/worker/src/run_jobs.py",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      min_uptime: 10000,
      restart_delay: 2000,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: `${APP_DIR}/logs/jobs-worker-error.log`,
      out_file: `${APP_DIR}/logs/jobs-worker-out.log`,
    },

    // ── Sync scheduler (B147 v0.9.3) ───────────────────────────────
    //
    // Long-running poll loop that walks plugin_registry every 30s,
    // reads each installed plugin's sync.schedule from plugin.yaml
    // (with plugin_settings._sync_schedule overrides), and enqueues
    // job_runs rows when a fire-time arrives. The existing jobs-worker
    // dequeues them.
    //
    // Single instance; no per-plugin pm2 entries needed. New plugins
    // are picked up on the next poll without operator action.
    {
      name: "scheduler",
      cwd: APP_DIR,
      script: ".venv/bin/python3",
      args: "apps/worker/src/run_scheduler.py",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      min_uptime: 10000,
      restart_delay: 5000,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: `${APP_DIR}/logs/scheduler-error.log`,
      out_file: `${APP_DIR}/logs/scheduler-out.log`,
    },

    // ── Legacy plugin sync workers (pre-B147) ──────────────────────
    //
    // Pre-v0.9.3, plugins with schedules required a hand-edited
    // cron_restart entry per plugin here. v0.9.3 replaces that with
    // the `scheduler` process above. Existing entries from before the
    // upgrade keep working but are now redundant — they'll dual-fire
    // alongside the new scheduler. Safe to leave (job_runs serializes);
    // remove at your leisure.
  ],
};
