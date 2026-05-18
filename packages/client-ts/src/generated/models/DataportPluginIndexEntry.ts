/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DataportTabIndexEntry } from './DataportTabIndexEntry';
/**
 * A single plugin in the dataport index — slug + tab labels.
 */
export type DataportPluginIndexEntry = {
    slug: string;
    tabs: Array<DataportTabIndexEntry>;
};

