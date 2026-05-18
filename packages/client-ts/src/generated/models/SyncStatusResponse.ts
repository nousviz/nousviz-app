/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SyncRunCurrent } from './SyncRunCurrent';
import type { SyncRunFailure } from './SyncRunFailure';
import type { SyncRunSuccess } from './SyncRunSuccess';
/**
 * GET /api/plugins/{id}/sync/status — composite snapshot for the Sync card.
 *
 * `current` is the in-flight run, or null when idle. `last_success` /
 * `last_failure` are the most recent terminal runs. `last_sync` mirrors
 * `last_success.completed_at` for backward compatibility with pre-v0.9.6
 * frontend code.
 */
export type SyncStatusResponse = {
    current?: (SyncRunCurrent | null);
    last_success?: (SyncRunSuccess | null);
    last_failure?: (SyncRunFailure | null);
    last_sync?: (string | null);
};

