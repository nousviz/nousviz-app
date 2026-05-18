/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { JobsDashboardFailingItem } from './JobsDashboardFailingItem';
import type { JobsDashboardNowItem } from './JobsDashboardNowItem';
import type { JobsDashboardRecentItem } from './JobsDashboardRecentItem';
import type { JobsDashboardUpcomingItem } from './JobsDashboardUpcomingItem';
/**
 * B277: GET /api/jobs/dashboard — 4-section centralized job state.
 *
 * Each section is independently sized, so callers can render whichever
 * blocks have content. `collected_at` lets the client tell when a
 * cached vs fresh snapshot is being shown.
 */
export type JobsDashboardResponse = {
    collected_at: string;
    now: Array<JobsDashboardNowItem>;
    recent: Array<JobsDashboardRecentItem>;
    upcoming: Array<JobsDashboardUpcomingItem>;
    failing: Array<JobsDashboardFailingItem>;
};

