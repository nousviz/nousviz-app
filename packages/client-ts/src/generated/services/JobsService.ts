/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FireNowResponse } from '../models/FireNowResponse';
import type { JobRunControlResponse } from '../models/JobRunControlResponse';
import type { JobRunRow } from '../models/JobRunRow';
import type { JobRunsListResponse } from '../models/JobRunsListResponse';
import type { JobsDashboardResponse } from '../models/JobsDashboardResponse';
import type { JobsListResponse } from '../models/JobsListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class JobsService {
    /**
     * List all scheduled jobs with status + cron source
     * Return all known scheduled jobs with status + schedule source.
     *
     * Aggregates plugin sync jobs (one per installed plugin), the alert
     * runner, and the system health monitor. `cron_source` distinguishes
     * PM2-scheduled vs crontab-scheduled deployments — the frontend uses
     * it to show the right "how to schedule" hint.
     * @returns JobsListResponse Successful Response
     * @throws ApiError
     */
    public static jobsList(): CancelablePromise<JobsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/jobs',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.read permission.`,
            },
        });
    }
    /**
     * List recent job runs
     * List recent job runs, optionally filtered by job_id.
     *
     * Returns up to `limit` runs ordered by `started_at` DESC. Used by
     * the System → Jobs page and the per-plugin Sync history block.
     * @returns JobRunsListResponse Successful Response
     * @throws ApiError
     */
    public static jobsRunsList({
        jobId,
        limit = 50,
    }: {
        jobId?: (string | null),
        limit?: number,
    }): CancelablePromise<JobRunsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/jobs/runs',
            query: {
                'job_id': jobId,
                'limit': limit,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Centralized job state — running / recent / upcoming / failing (B277)
     * Return the unified job-state snapshot rendered on /system/jobs.
     *
     * Sections:
     * - now: currently-running + queued jobs with elapsed_ms and
     * will_overlap_next (elapsed already exceeds the gap to next fire)
     * - recent: last 12h of completed runs ordered by started_at DESC
     * - upcoming: next 6h of scheduled fires with may_overlap predictions
     * - failing: jobs with > 50% error rate (min 4 runs) over 24h
     *
     * Cached in-process for 30 seconds; pass `?fresh=true` to bypass.
     * @returns JobsDashboardResponse Successful Response
     * @throws ApiError
     */
    public static jobsDashboard({
        fresh = false,
    }: {
        fresh?: boolean,
    }): CancelablePromise<JobsDashboardResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/jobs/dashboard',
            query: {
                'fresh': fresh,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Detail for a single job run
     * Return detail for a single job_runs row — status, progress, heartbeat.
     * @returns JobRunRow Successful Response
     * @throws ApiError
     */
    public static jobsRunDetail({
        runId,
    }: {
        runId: number,
    }): CancelablePromise<JobRunRow> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/jobs/{run_id}',
            path: {
                'run_id': runId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.read permission.`,
                404: `Run not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Cancel a queued or running job run
     * Cancel a queued or running run. Cooperative — the plugin sees the
     * cancel via check_cancelled() on its next poll.
     *
     * - queued  → status='cancelled' (never ran)
     * - running → status='cancelling' (plugin exits on next check_cancelled)
     * - paused  → status='cancelled'
     * - terminal (success/error/timeout/cancelled/skipped) → 200 no-op
     *
     * `?force=true` (B277 v0.9.11.16.3+): force-marks the run terminal as
     * `cancelled` regardless of current status (skipping the cooperative
     * `cancelling` state). Used for **orphaned runs** where the worker is
     * confirmed gone — e.g. after a Postgres restart or scheduler crash
     * that left rows in `'running'` without any process actively executing
     * them. Without `?force=true`, those rows would hang in `cancelling`
     * forever (no worker to observe the cancel).
     *
     * **Server-gated liveness check (v0.9.11.16.4)**: when `?force=true`
     * is passed against a `'running'` row whose `heartbeat_at` is fresh
     * (worker heartbeated within the last 90 seconds), the request is
     * refused with 409. The worker is alive — cooperative cancel will
     * work, and force-cancel would create a status mismatch where the
     * worker still thinks it's running. The dashboard frontend uses
     * `JobsDashboardNowItem.worker_alive` to pick the right button
     * automatically; this server-side check is the safety net.
     * @returns JobRunControlResponse Successful Response
     * @throws ApiError
     */
    public static jobsRunCancel({
        runId,
        force = false,
    }: {
        runId: number,
        force?: boolean,
    }): CancelablePromise<JobRunControlResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/jobs/{run_id}/cancel',
            path: {
                'run_id': runId,
            },
            query: {
                'force': force,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.write permission.`,
                404: `Run not found.`,
                409: `Run is in a status that can't be cancelled.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Pause a queued or running job run
     * Pause a running run. Plugin exits at next check_cancelled(); the
     * run lands in 'paused' status (not 'cancelled') so resume re-queues it.
     *
     * - running → status='paused' (via cancelling — plugin exits cleanly)
     * - queued  → status='paused' directly (never claimed)
     * @returns JobRunControlResponse Successful Response
     * @throws ApiError
     */
    public static jobsRunPause({
        runId,
    }: {
        runId: number,
    }): CancelablePromise<JobRunControlResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/jobs/{run_id}/pause',
            path: {
                'run_id': runId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.write permission.`,
                404: `Run not found.`,
                409: `Run is in a status that can't be paused.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Re-queue a paused job run
     * Re-queue a paused run so the worker picks it up fresh.
     *
     * Only valid transition: paused → queued.
     * @returns JobRunControlResponse Successful Response
     * @throws ApiError
     */
    public static jobsRunResume({
        runId,
    }: {
        runId: number,
    }): CancelablePromise<JobRunControlResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/jobs/{run_id}/resume',
            path: {
                'run_id': runId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.write permission.`,
                404: `Run not found.`,
                409: `Only paused runs can be resumed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Immediately trigger a schedulable job
     * Immediately trigger a schedulable job.
     *
     * For plugin syncs (job_id looks like '<plugin_id>-sync'), delegates to
     * the manual-trigger endpoint which honors execution_mode (async vs
     * sync). For core jobs (alerts-runner, health-monitor), this is a
     * no-op for now — their schedulers are external (PM2 cron_restart).
     *
     * job_id comes from the `jobs` list `id` field (e.g. 'starter-plugin-sync').
     * @returns FireNowResponse Successful Response
     * @throws ApiError
     */
    public static jobsFireNow({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<FireNowResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/jobs/{job_id}/fire-now',
            path: {
                'job_id': jobId,
            },
            errors: {
                400: `Job is not fire-now capable (core jobs run on PM2).`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the jobs.write permission.`,
                422: `Validation Error`,
            },
        });
    }
}
