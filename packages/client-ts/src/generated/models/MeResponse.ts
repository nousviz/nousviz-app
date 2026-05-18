/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/auth/me — Option B identity shape (B236).
 *
 * The top-level fields describe the ACTOR (the human authenticated to
 * this session). `acting_as`, when present, carries the target the
 * actor is currently impersonating.
 *
 * Frontend reads `me` for actor identity (for the impersonation
 * banner, audit display, log-out button) and `me.acting_as` for
 * effective identity (permission resolution, role display). The
 * `useEffectiveIdentity()` hook centralizes this choice.
 */
export type MeResponse = Record<string, any>;
