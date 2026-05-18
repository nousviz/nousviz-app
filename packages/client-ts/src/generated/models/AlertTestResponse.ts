/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/alerts/{alert_id}/test — dry-run evaluation result.
 *
 * `error` is set when the alert worker module isn't importable or the
 * evaluation raised; otherwise `fired` + `rows_checked` + `triggered_rows`
 * describe the test outcome.
 */
export type AlertTestResponse = {
    alert_id: string;
    fired?: (boolean | null);
    message?: (string | null);
    rows_checked?: (number | null);
    /**
     * Up to 5 rows that would have triggered.
     */
    triggered_rows?: null;
    error?: (string | null);
};

