/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DailyActivityEntry } from './DailyActivityEntry';
import type { PageViewEntry } from './PageViewEntry';
import type { PluginActivityEntry } from './PluginActivityEntry';
/**
 * GET /api/activity/dashboard-usage — analytics aggregate.
 *
 * `unused_dashboards` enumerates manifest-declared dashboard paths
 * that received zero page_view events in the period.
 */
export type DashboardUsageResponse = {
    period_days: number;
    total_events: number;
    page_views: Array<PageViewEntry>;
    plugin_activity: Array<PluginActivityEntry>;
    action_breakdown: Record<string, number>;
    daily_activity: Array<DailyActivityEntry>;
    unused_dashboards: Array<string>;
};

