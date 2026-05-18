/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteEntry } from './NoteEntry';
/**
 * GET /api/notes — pinned-first ordering, optional page-path/plugin filter.
 */
export type NotesListResponse = {
    notes: Array<NoteEntry>;
    count: number;
};

