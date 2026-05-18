/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Per-plugin schedule override.
 *
 * B148: cron=None or "" clears the override (falls back to manifest).
 * B205 (v0.9.6): friendly form — supply interval_value + interval_unit
 * instead of a raw cron expression. The two forms are mutually exclusive
 * in a single request.
 *
 * Examples:
 * {"cron": "*15 * * * *"}                      raw cron
 * {"interval_value": 15, "interval_unit": "minutes"}  friendly form
 * {"cron": null}                                 clear override
 */
export type SyncScheduleBody = {
    cron?: (string | null);
    interval_value?: (number | null);
    interval_unit?: (string | null);
};

