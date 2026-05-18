/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AlertCreate = {
    name: string;
    label: string;
    description?: (string | null);
    plugin_id: string;
    dataset: string;
    metric: string;
    aggregation?: string;
    condition_type?: string;
    threshold?: (number | null);
    compare_to?: string;
    scope?: string;
    group_by?: (string | null);
    scope_filters?: Record<string, any>;
    check_frequency?: string;
    check_period?: string;
    cooldown_hours?: number;
    min_baseline?: number;
    notify_channels?: Array<string>;
    enabled?: boolean;
    is_template?: boolean;
};

