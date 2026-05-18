/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlertSparklineDay } from './AlertSparklineDay';
/**
 * GET /api/alerts/{alert_id}/sparkline — last N days of trigger activity.
 */
export type AlertSparklineResponse = {
    alert_id: string;
    alert_label: string;
    check_frequency?: (string | null);
    frequency_label?: (string | null);
    check_period?: (string | null);
    period_label?: (string | null);
    cooldown_hours?: (number | null);
    days: Array<AlertSparklineDay>;
    total_triggers: number;
    /**
     * Counts keyed by 'useful' | 'neutral' | 'useless'.
     */
    semantic_summary: Record<string, number>;
};

