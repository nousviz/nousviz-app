/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * B277: an upcoming scheduled fire with collision prediction.
 */
export type JobsDashboardUpcomingItem = {
    plugin_id: string;
    schedule_cron: string;
    next_fire_at: string;
    ms_until_fire: number;
    avg_duration_ms?: (number | null);
    /**
     * True when avg_duration_ms exceeds 90% of ms_until_fire.
     */
    may_overlap?: boolean;
};

