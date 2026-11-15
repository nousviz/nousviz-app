# Webhooks

Inbound endpoints receive data from external services. Outbound endpoints
deliver alert notifications to Slack, Discord, Teams, PagerDuty, or any HTTP
service.

## Outbound signatures

When an outbound endpoint has a secret, every delivery is signed. This covers
alert webhooks, job-failure and diagnostic alerts, and the endpoint **Test**
button. Since B346 each signed delivery carries three headers:

| Header | Value |
|---|---|
| `X-Webhook-Signature` | lowercase hex `HMAC-SHA256(secret, body)`. This is the original body-only signature, unchanged, kept for existing consumers. |
| `X-Webhook-Timestamp` | Unix time in whole seconds, as a decimal string (e.g. `1700000000`) |
| `X-Webhook-Signature-V2` | lowercase hex `HMAC-SHA256(secret, timestamp + "." + body)` |

`body` is the exact bytes of the POST body. For V2, the signed message is the
`X-Webhook-Timestamp` string, a literal `.`, and then the raw body bytes:

```python
msg = f"{timestamp}.".encode() + body
v2 = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
```

An endpoint without a secret sends none of these headers.

### Verifying V2 (recommended)

V1 can be replayed: anyone who captures a delivery can POST it again and the
signature still matches. V2 binds the signature to a timestamp, so a consumer
can reject old deliveries:

1. Read `X-Webhook-Timestamp` and `X-Webhook-Signature-V2`.
2. Reject the delivery if the timestamp is outside your tolerance window
   (5 minutes is common). The consumer chooses the window; NousViz does not
   set one.
3. Compute `HMAC-SHA256(secret, f"{timestamp}." + raw_body)` over the raw
   request bytes, before any JSON parsing.
4. Compare it to the header with a constant-time comparison
   (`hmac.compare_digest`).

This is the timestamped scheme used by Standard Webhooks-style receivers
(the "timestamp.body" construction).

## Inbound signatures

An inbound endpoint without a secret accepts every request, signed or not.
An endpoint with a secret verifies each request as follows (B347):

1. **V2, when the sender sends it.** If the request has
   `X-Webhook-Timestamp` or `X-Webhook-Signature-V2`, it must have both,
   and:
   - the timestamp must be a whole number of Unix seconds within ±300 s
     (5 minutes) of the server's clock;
   - `X-Webhook-Signature-V2` must equal lowercase hex
     `HMAC-SHA256(secret, timestamp + "." + body)`, the same scheme NousViz
     sends (see [Outbound signatures](#outbound-signatures)).

   If any check fails, the response is **401**. The endpoint does **not**
   fall back to `X-Webhook-Signature`. A captured old delivery also carries
   a valid V1 signature, so a fallback would accept exactly the replay that
   V2 blocks. A sender that sends V2 must keep its clock in sync.
2. **V1, only when no V2 header is sent.** The endpoint checks
   `X-Webhook-Signature` = hex `HMAC-SHA256(secret, body)`, as before. This
   keeps third-party senders and NousViz versions before B346 working.
3. **Require timestamped signature.** This per-endpoint setting is off by
   default. Turn it on under the endpoint's settings (the gear icon on an
   inbound endpoint, or when creating one). When it is on, a request without
   valid V2 headers gets **401**, even with a valid V1 signature. Without
   it, someone who captured a delivery could strip its V2 headers and replay
   it with V1. Turn it on once every sender to that endpoint signs V2. It
   has no effect on an endpoint without a secret.
4. **Duplicates.** A verified V2 delivery is stored with its
   `x-webhook-signature-v2` and `x-webhook-timestamp` headers. If the same
   endpoint receives the same V2 signature again within 10 minutes, the
   response is **409** and nothing is stored. Ten minutes covers the whole
   time a timestamp stays valid. V1-only requests are not de-duplicated:
   without a timestamp, two identical bodies may be legitimate.

Error responses are always `{"detail": "Invalid signature"}`,
`{"detail": "Signature expired"}` or `{"detail": "Duplicate delivery"}`.
They never include the expected signature.

| Request | Require timestamped signature off | On |
|---|---|---|
| Valid V2 (V1 optional) | 200 | 200 |
| V2 timestamp more than 5 minutes off, or bad V2 (even with valid V1) | 401 | 401 |
| Same V2 delivery again within 10 minutes | 409 | 409 |
| Valid V1 only | 200 | 401 |
| No signature | 401 | 401 |
