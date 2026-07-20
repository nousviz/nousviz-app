# Entitlement contract

The versioned document describing what a managed NousViz customer is allowed. **Produced** by the NousViz control plane; **consumed** by the app's entitlement client and enforced at the relevant seams (users, plugins, SMTP, feature flags). One source of truth so neither side drifts toward the other.

Community/self-hosted installations ignore this entirely — no entitlement is fetched and every feature behaves as documented for the self-hosted product. This contract only governs managed (hosted) instances.

## Files

| File | Purpose |
|---|---|
| `entitlement.schema.json` | JSON Schema (draft 2020-12). Validated by `tests/test_entitlement_contract.py` in CI. |
| `entitlement.example.{free,starter,team,business,enterprise}.json` | Per-tier example fixtures. Enforcement code develops and tests against these — no dependency on the control plane being deployed. |

## ⚠️ Tier numbers are DRAFT

The user/plugin limits and feature gates in the fixtures are **working drafts, not commercial commitments** (pricing review pending). The *schema* is the stable contract; fixture values may become more generous at any time. The `free` fixture in particular describes a tier that is **not yet offered** — it exists so the shape is exercised, nothing more.

## Versioning policy — additive-only

1. `version` is bumped **only** for a breaking shape change (removing or repurposing a field). New optional fields and new feature flags are **additive** and do **not** bump it.
2. The **consumer must tolerate unknown fields** — `additionalProperties` is true throughout, and the client ignores fields it doesn't recognise. A newer producer never breaks an older consumer; no lockstep redeploys.
3. New feature flags default to **off/unavailable** on a consumer that doesn't know them. Community builds treat the whole `features` block as not applicable.

## Enforcement principles (encoded in the schema descriptions)

- **Fail-open**: an instance that cannot reach the control plane keeps running on its last successfully fetched entitlement. Customers are never locked out of their own data by an outage on our side.
- **Grandfathering**: users or plugins over a lowered limit are never deleted or disabled; the instance simply cannot add more until the limit rises.

## Security note

`smtp.password` is a real secret. It is delivered over the authenticated entitlement channel and must never be logged or surfaced in an API response. The fixtures' placeholder values are illustrative only.
