/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AlertUpdate = {
    label?: (string | null);
    description?: (string | null);
    enabled?: (boolean | null);
    threshold?: (number | null);
    compare_to?: (string | null);
    check_period?: (string | null);
    group_by?: (string | null);
    scope_filters?: (Record<string, any> | null);
    cooldown_hours?: (number | null);
    min_baseline?: (number | null);
    notify_channels?: (Array<string> | null);
};

