/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Serialized user row — output of `_serialize()` in routes/auth.py.
 *
 * `password_hash` is always stripped. `api_key` is truncated to first
 * 8 chars + ellipsis. Datetimes are ISO-8601 strings.
 *
 * Extra keys are allowed because user rows include columns added by
 * later migrations (e.g. `last_seen_at`, `color`) that may or may not
 * be present depending on schema state.
 */
export type UserSerialized = Record<string, any>;
