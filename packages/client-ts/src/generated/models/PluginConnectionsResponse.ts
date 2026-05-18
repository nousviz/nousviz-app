/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConnectionEntry } from './ConnectionEntry';
/**
 * GET /api/plugins/{id}/connections.
 */
export type PluginConnectionsResponse = {
    /**
     * One entry per connection block in the plugin's manifest (typically one).
     */
    connections?: Array<ConnectionEntry>;
};

