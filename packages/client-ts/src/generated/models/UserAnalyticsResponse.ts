/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TimePerPageEntry } from './TimePerPageEntry';
/**
 * GET /api/activity/analytics — admin analytics overview.
 *
 * `devices`, `browsers`, `ip_activity`, `hourly_distribution` are
 * histogram-style maps keyed by the categorical value; treated as
 * open-ended dicts since the keys are inferred from user-agent / IP /
 * timestamp parsing.
 */
export type UserAnalyticsResponse = {
    period_days: number;
    total_events: number;
    total_page_views: number;
    estimated_time_minutes: number;
    estimated_time_display: string;
    sessions: number;
    avg_session_minutes: number;
    devices: Record<string, number>;
    browsers: Record<string, number>;
    unique_ips: Array<string>;
    ip_activity: Record<string, number>;
    peak_hour: string;
    hourly_distribution: Record<string, number>;
    time_per_page: Array<TimePerPageEntry>;
};

