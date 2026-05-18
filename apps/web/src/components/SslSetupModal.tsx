import { useState } from "react";
import { X, Shield, Globe, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

const ANSI_RE = /\x1b\[[0-9;]*m/g;

interface SslSetupModalProps {
  onClose: () => void;
  onComplete?: () => void;
}

// Scenario-specific guidance panels keyed on the `reason` field returned by the backend.
// Title, short summary, and numbered next-steps. Rendered when the backend classified
// the failure (CDN proxy, DNS not propagated, wrong server, etc.) rather than showing a
// raw error message.
interface ScenarioPanel {
  title: string;
  summary: string;
  options: { heading: string; steps: string[]; docsUrl?: string }[];
}

function _scenarioForReason(reason: string | undefined, domain: string): ScenarioPanel | null {
  if (!reason) return null;
  switch (reason) {
    case "dns_empty":
      return {
        title: "DNS hasn't propagated yet",
        summary: `No A record found for ${domain || "this domain"}. Either the record hasn't been created yet, or DNS needs more time to propagate.`,
        options: [
          {
            heading: "If you just created the A record",
            steps: [
              "Wait 5-15 minutes for DNS to propagate",
              `Verify with: dig +short ${domain || "<your-domain>"}`,
              "Once it returns this server's IP, retry this wizard",
            ],
          },
          {
            heading: "If the record should be there",
            steps: [
              "Check your DNS provider — is the A record created and enabled?",
              "Confirm the record points to this server's public IP",
              "Remove any conflicting AAAA records if you aren't using IPv6",
            ],
          },
        ],
      };
    case "cdn_cloudflare":
      return {
        title: "Domain is behind Cloudflare",
        summary: `${domain} is proxied through Cloudflare. Let's Encrypt can't verify ownership at the origin because Cloudflare intercepts the HTTP-01 challenge. You have two options:`,
        options: [
          {
            heading: "Option A — Use Cloudflare's edge SSL (recommended)",
            steps: [
              "Cloudflare already serves HTTPS at the edge for proxied domains",
              "In Cloudflare dashboard: SSL/TLS → set mode to Full (strict) if your origin will also have a cert, or Flexible if not",
              "Close this wizard — your site is already served over HTTPS",
            ],
            docsUrl: "https://developers.cloudflare.com/ssl/",
          },
          {
            heading: "Option B — Let's Encrypt at the origin (end-to-end encryption)",
            steps: [
              "In Cloudflare DNS: click the orange cloud on the A record — it turns grey (DNS-only)",
              "Wait ~1 minute for DNS to repropagate",
              "Retry this wizard — Let's Encrypt will issue the cert",
              "Turn the orange cloud back on in Cloudflare",
              "Set Cloudflare SSL/TLS mode to Full (strict) for end-to-end encryption",
            ],
          },
        ],
      };
    case "cdn_cloudfront":
      return {
        title: "Domain is behind AWS CloudFront",
        summary: `${domain} resolves to CloudFront distribution IPs. Configure SSL at the CloudFront layer instead of the origin.`,
        options: [
          {
            heading: "Use an ACM certificate on the CloudFront distribution",
            steps: [
              "In AWS Certificate Manager, request a cert for your domain",
              "Attach the cert to your CloudFront distribution in the AWS console",
              "CloudFront issues and renews the cert automatically — no action needed on this server",
              "Close this wizard",
            ],
            docsUrl: "https://docs.aws.amazon.com/acm/",
          },
        ],
      };
    case "cdn_fastly":
      return {
        title: "Domain is behind Fastly",
        summary: `${domain} resolves to Fastly edge IPs. Configure SSL through Fastly's TLS service.`,
        options: [
          {
            heading: "Use Fastly-managed TLS",
            steps: [
              "In your Fastly account, enable TLS for this domain",
              "Follow Fastly's domain verification flow",
              "Close this wizard — Fastly serves HTTPS at the edge",
            ],
            docsUrl: "https://docs.fastly.com/en/guides/tls-termination",
          },
        ],
      };
    case "cdn_netlify":
      return {
        title: "Domain is behind Netlify",
        summary: `${domain} resolves to Netlify IPs. Netlify provisions Let's Encrypt certs automatically for custom domains.`,
        options: [
          {
            heading: "Use Netlify's automatic HTTPS",
            steps: [
              "In your Netlify site settings, confirm the custom domain is attached",
              "Netlify issues a cert automatically within a few minutes",
              "Close this wizard",
            ],
            docsUrl: "https://docs.netlify.com/domains-https/https-ssl/",
          },
        ],
      };
    case "wrong_server":
      return {
        title: "Domain points to a different server",
        summary: `${domain} resolves to IPs that don't match this server. You need to update your DNS A record.`,
        options: [
          {
            heading: "Update the A record at your DNS provider",
            steps: [
              "Log into your DNS provider (Cloudflare, Namecheap, Route 53, etc.)",
              "Find the A record for this domain",
              "Update the value to this server's public IP",
              "Wait ~1 minute for DNS to repropagate",
              "Retry this wizard",
            ],
          },
        ],
      };
    case "timeout":
      return {
        title: "SSL setup timed out",
        summary: "The setup took longer than 300 seconds. It may still be running on the server.",
        options: [
          {
            heading: "Check from the command line",
            steps: [
              "SSH to the server",
              "Run: ps aux | grep ssl-setup",
              "If a process is running, wait for it to finish, then refresh this page",
              "If no process is running, try: sudo ./scripts/ssl-setup.sh " + (domain || "<domain>"),
            ],
          },
        ],
      };
    default:
      return null;
  }
}

export default function SslSetupModal({ onClose, onComplete }: SslSetupModalProps) {
  const [mode, setMode] = useState<"choose" | "domain" | "running" | "done" | "error">("choose");
  const [sslType, setSslType] = useState<"letsencrypt" | "self-signed" | null>(null);
  const [domain, setDomain] = useState("");
  const [email, setEmail] = useState("");
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");
  const [reason, setReason] = useState<string | undefined>(undefined);

  async function runSetup() {
    setMode("running");
    setOutput("");
    setError("");
    setReason(undefined);

    const manualFallback =
      "\n\nRun SSL setup from the server command line instead:\n" +
      "  sudo ./scripts/ssl-setup.sh <domain>";

    try {
      const body: Record<string, string> = { mode: sslType! };
      if (sslType === "letsencrypt") {
        body.domain = domain;
        if (email) body.email = email;
      }

      const res = await apiFetch("/api/admin/ssl/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      // Gracefully handle non-JSON responses (nginx 504 HTML, reverse proxy error pages,
      // backend crash). Trying to res.json() a <html>... page surfaces as an unhelpful
      // "Unexpected token '<'" parse error.
      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        const text = await res.text().catch(() => "");
        const hint = res.status === 504 || res.status === 502
          ? `The server took too long or is unreachable (HTTP ${res.status}).`
          : `The server returned a non-JSON response (HTTP ${res.status}).`;
        setError(hint + manualFallback + (text ? `\n\nRaw response:\n${text.slice(0, 300)}` : ""));
        setMode("error");
        return;
      }

      const data = await res.json();

      if (data.ok) {
        setOutput(data.output || "SSL configured successfully.");
        setMode("done");
      } else {
        setReason(data.reason);
        // If the backend classified the failure (CDN proxy, DNS not propagated, etc.), the
        // scenario panel renders the guidance — we still store the raw error for the "show
        // full error" expander. If no classification, the raw error is the primary display.
        setError((data.error || "SSL setup failed.") + (data.reason ? "" : manualFallback));
        setMode("error");
      }
    } catch (e) {
      setError((e instanceof Error ? e.message : "Network error") + manualFallback);
      setMode("error");
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-2xl w-full max-w-[480px] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            <span className="text-sm font-display text-foreground">Configure HTTPS</span>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {mode === "choose" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Secure your NousViz instance with a free HTTPS certificate from Let's Encrypt.
                You'll need a domain with a DNS A record pointing to this server.
              </p>

              <button
                onClick={() => { setSslType("letsencrypt"); setMode("domain"); }}
                className="w-full text-left p-4 rounded-lg border border-border hover:border-primary/30 transition-colors space-y-1"
              >
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium text-foreground">Set up HTTPS</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Free trusted certificate from Let's Encrypt. No browser warnings, auto-renews every 90 days.
                </p>
              </button>

              <div className="rounded-lg border border-border bg-secondary/20 p-4 space-y-2">
                <p className="text-xs font-medium text-muted-foreground">Don't have a domain?</p>
                <p className="text-xs text-muted-foreground">
                  HTTPS requires a domain name — it cannot be set up on a bare IP address.
                  Domains cost ~$10/year from any registrar (Cloudflare, Namecheap, etc.).
                  Point an A record to your server IP, then come back here.
                </p>
              </div>

              <button
                onClick={onClose}
                className="w-full text-center text-xs text-muted-foreground hover:text-foreground py-2 transition-colors"
              >
                Do this later
              </button>
            </div>
          )}

          {mode === "domain" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Domain</label>
                <input
                  autoFocus
                  type="text"
                  value={domain}
                  onChange={e => setDomain(e.target.value)}
                  placeholder="app.example.com"
                  className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <p className="text-[11px] text-muted-foreground mt-1">
                  The domain's A record must point to this server's IP.
                </p>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Email (for renewal notices)</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@example.com (optional)"
                  className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="flex items-center gap-3 pt-1">
                <button
                  onClick={() => setMode("choose")}
                  className="h-9 px-4 rounded-lg bg-secondary text-sm text-foreground hover:bg-secondary/80 transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={runSetup}
                  disabled={!domain.trim()}
                  className="h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Set up HTTPS
                </button>
              </div>
            </div>
          )}

          {mode === "running" && (
            <div className="py-8 text-center space-y-3">
              <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" />
              <p className="text-sm text-foreground">Configuring SSL...</p>
              <p className="text-xs text-muted-foreground">
                Verifying DNS, obtaining certificate, configuring nginx...
              </p>
            </div>
          )}

          {mode === "done" && (
            <div className="py-6 text-center space-y-4">
              <div className="h-14 w-14 rounded-2xl bg-green-500/10 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7 text-green-400" />
              </div>
              <div>
                <h3 className="font-display text-lg text-foreground">HTTPS configured</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Your site is now available at https://{domain}/
                </p>
              </div>
              {output && (
                <pre className="text-[11px] font-mono-deck text-muted-foreground bg-secondary rounded-lg p-3 text-left max-h-32 overflow-y-auto whitespace-pre-wrap">
                  {output.replace(ANSI_RE, "")}
                </pre>
              )}
              <button
                onClick={() => {
                  onComplete?.();
                  onClose();
                  window.location.href = `https://${domain}/`;
                }}
                className="h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                Go to https://{domain}
              </button>
            </div>
          )}

          {mode === "error" && (() => {
            const scenario = _scenarioForReason(reason, domain);
            return (
              <div className="py-6 space-y-4">
                {scenario ? (
                  <div className="space-y-3">
                    <div className="flex items-start gap-3 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                      <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-yellow-400">{scenario.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">{scenario.summary}</p>
                      </div>
                    </div>
                    {scenario.options.map((opt, i) => (
                      <div key={i} className="p-4 rounded-lg bg-secondary/30 border border-border space-y-2">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-foreground">{opt.heading}</p>
                          {opt.docsUrl && (
                            <a
                              href={opt.docsUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary hover:text-primary/80 transition-colors"
                            >
                              Docs →
                            </a>
                          )}
                        </div>
                        <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside ml-1">
                          {opt.steps.map((step, j) => (
                            <li key={j}>{step}</li>
                          ))}
                        </ol>
                      </div>
                    ))}
                    <details className="text-xs text-muted-foreground">
                      <summary className="cursor-pointer hover:text-foreground transition-colors">
                        Show full error output
                      </summary>
                      <pre className="mt-2 text-[11px] font-mono-deck bg-secondary rounded-lg p-3 whitespace-pre-wrap max-h-40 overflow-y-auto">
                        {error.replace(ANSI_RE, "")}
                      </pre>
                    </details>
                  </div>
                ) : (
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                    <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-400">SSL setup failed</p>
                      <p className="text-xs text-red-300/80 mt-1 whitespace-pre-wrap font-mono-deck">
                        {error.replace(ANSI_RE, "")}
                      </p>
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setMode("choose")}
                    className="h-9 px-4 rounded-lg bg-secondary text-sm text-foreground hover:bg-secondary/80 transition-colors"
                  >
                    Try again
                  </button>
                  <button
                    onClick={onClose}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Close
                  </button>
                </div>
                <p className="text-xs text-muted-foreground">
                  You can also run SSL setup from the command line:{" "}
                  <code className="font-mono-deck bg-secondary px-1.5 py-0.5 rounded">./scripts/ssl-setup.sh</code>
                </p>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
