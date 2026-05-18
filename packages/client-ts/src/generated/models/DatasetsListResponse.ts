/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DatasetSummary } from './DatasetSummary';
/**
 * GET /api/datasets — metadata for every dataset, newest-first.
 */
export type DatasetsListResponse = {
    datasets: Array<DatasetSummary>;
    count: number;
};

