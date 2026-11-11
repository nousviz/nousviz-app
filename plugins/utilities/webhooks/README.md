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

Inbound endpoints with a secret check `X-Webhook-Signature` (body-only
HMAC-SHA256). They do not yet accept V2.
