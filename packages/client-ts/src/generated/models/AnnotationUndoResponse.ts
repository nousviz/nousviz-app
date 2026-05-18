/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/annotations/{annotation_id}/undo.
 *
 * Two shapes depending on what was undone:
 * - Undoing a 'created' action: `action='archived (creation undone)'`,
 * no `restored_to`.
 * - Undoing an 'updated' action: `restored_to` carries the snapshot.
 */
export type AnnotationUndoResponse = Record<string, any>;
