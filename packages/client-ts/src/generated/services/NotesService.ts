/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteCreate } from '../models/NoteCreate';
import type { NoteDeleteResponse } from '../models/NoteDeleteResponse';
import type { NoteEntry } from '../models/NoteEntry';
import type { NotesListResponse } from '../models/NotesListResponse';
import type { NoteUpdate } from '../models/NoteUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class NotesService {
    /**
     * List notes (pinned-first, optional page-path/plugin filter)
     * @returns NotesListResponse Successful Response
     * @throws ApiError
     */
    public static notesList({
        pagePath,
        pluginId,
        includeArchived = false,
    }: {
        pagePath?: (string | null),
        pluginId?: (string | null),
        includeArchived?: boolean,
    }): CancelablePromise<NotesListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/notes',
            query: {
                'page_path': pagePath,
                'plugin_id': pluginId,
                'include_archived': includeArchived,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the notes.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create a note attached to a page (and optional date range)
     * @returns NoteEntry Successful Response
     * @throws ApiError
     */
    public static notesCreate({
        requestBody,
    }: {
        requestBody: NoteCreate,
    }): CancelablePromise<NoteEntry> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/notes',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the notes.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update a note (partial — null fields skipped)
     * @returns NoteEntry Successful Response
     * @throws ApiError
     */
    public static notesUpdate({
        noteId,
        requestBody,
    }: {
        noteId: string,
        requestBody: NoteUpdate,
    }): CancelablePromise<NoteEntry> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Empty body.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the notes.write permission.`,
                404: `Note not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete a note
     * @returns NoteDeleteResponse Successful Response
     * @throws ApiError
     */
    public static notesDelete({
        noteId,
    }: {
        noteId: string,
    }): CancelablePromise<NoteDeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the notes.write permission.`,
                404: `Note not found.`,
                422: `Validation Error`,
            },
        });
    }
}
