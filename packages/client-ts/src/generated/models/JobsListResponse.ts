/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CrontabEntry } from './CrontabEntry';
import type { JobEntry } from './JobEntry';
/**
 * GET /api/jobs — every known scheduled job + crontab/PM2 metadata.
 *
 * `cron_source` flips between 'crontab' and 'pm2' to drive the
 * frontend's "how to schedule" hint.
 */
export type JobsListResponse = {
    jobs: Array<JobEntry>;
    /**
     * System crontab entries containing 'nousviz' — empty on PM2 deployments.
     */
    crontab?: Array<CrontabEntry>;
    /**
     * PM2-managed processes with cron_restart — empty on crontab-only deployments.
     */
    pm2?: Array<CrontabEntry>;
    has_crontab: boolean;
    has_pm2_cron: boolean;
    /**
     * 'pm2' | 'crontab' | 'mixed' | 'none'.
     */
    cron_source: string;
};

