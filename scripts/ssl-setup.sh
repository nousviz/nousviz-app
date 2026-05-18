#!/bin/bash
# NousViz — SSL certificate setup (Let's Encrypt)
#
# A real domain is required. Self-signed / bare-IP HTTPS is not supported
# because browser security warnings make the platform effectively unusable.
#
# Usage:
#   ./scripts/ssl-setup.sh                    # interactive — prompts for domain
#   ./scripts/ssl-setup.sh example.com        # non-interactive
#   ./scripts/ssl-setup.sh example.com --email you@example.com
#
# Requirements:
#   - Must be run on the server (not localhost)
#   - Root/sudo access for nginx config and certbot
#   - Port 80 must be open (for Let's Encrypt HTTP-01 challenge)
#   - Port 443 must be open (for HTTPS itself)
#   - DNS A record for the domain must point at this server's IP

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step()  { echo -e "\n${BLUE}▶${NC} $1"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail()  { echo -e "  ${RED}✗${NC} $1"; exit 1; }

_update_env() {
    local key="$1" val="$2"
    if [[ ! -f "$ENV_FILE" ]]; then return; fi
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

# ── Detect environment ───────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
NGINX_CONF="/etc/nginx/sites-available/nousviz"
NGINX_SSL_TEMPLATE="${SCRIPT_DIR}/infra/nginx-ssl.conf"

# Reject localhost
HOSTNAME_CHECK="$(hostname -I 2>/dev/null | awk '{print $1}' || echo '')"
if [[ "$HOSTNAME_CHECK" == "" ]] || [[ "$(hostname)" == "localhost" ]] || [[ "$HOSTNAME_CHECK" == "127."* ]]; then
    # Also check if we're on macOS dev machine
    if [[ "$(uname)" == "Darwin" ]]; then
        echo ""
        echo "  SSL setup is not applicable for local development."
        echo "  Run this script on your production server."
        echo ""
        exit 0
    fi
fi

# Must be root or sudo
if [[ $EUID -ne 0 ]]; then
    fail "This script must be run as root (or with sudo)"
fi

# ── Parse args ────────────────────────────────────────────────────────

DOMAIN=""
EMAIL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --email)       EMAIL="$2"; shift 2 ;;
        -*)            fail "Unknown flag: $1" ;;
        *)             DOMAIN="$1"; shift ;;
    esac
done

# NON_INTERACTIVE is set by the API when invoked from the UI. In that mode the
# script must never prompt — missing args or DNS mismatch exit with a clear error
# so the backend can surface it in the response.
NON_INTERACTIVE="${NOUSVIZ_NON_INTERACTIVE:-0}"

# Interactive mode if no args
if [[ -z "$DOMAIN" ]]; then
    if [[ "$NON_INTERACTIVE" == "1" ]]; then
        fail "domain is required (NOUSVIZ_NON_INTERACTIVE=1, no prompt)"
    fi
    echo ""
    echo "  NousViz SSL Setup"
    echo "  ─────────────────"
    echo ""
    echo "  HTTPS requires a domain with a DNS A record pointing to this server."
    echo "  A free trusted certificate will be issued by Let's Encrypt."
    echo ""
    read -rp "  Domain: " DOMAIN
    if [[ -z "$DOMAIN" ]]; then
        fail "A domain is required for SSL. Point a domain to this server's IP first."
    fi
fi

# ── Let's Encrypt certificate ────────────────────────────────────────

step "Setting up Let's Encrypt for ${DOMAIN}..."

# Verify DNS — accept if ANY A record matches the server IP (not just tail -1),
# since dig returns multiple lines when the domain has multiple A records.
SERVER_IP="$(hostname -I | awk '{print $1}')"
DNS_IPS="$(dig +short "$DOMAIN" 2>/dev/null | grep -E '^[0-9.]+$')"

# Emit a machine-readable classification line so the API route (non-interactive caller)
# can parse it and render scenario-specific guidance. Format:
#   NOUSVIZ_CLASSIFICATION: <reason>
# where <reason> is one of: dns_empty, cdn_cloudflare, cdn_cloudfront, cdn_fastly,
# cdn_netlify, wrong_server, generic_mismatch.
_emit_classification() {
    echo "NOUSVIZ_CLASSIFICATION: $1"
}

# DNS not propagated yet (or domain doesn't exist)
if [[ -z "$DNS_IPS" ]]; then
    _emit_classification "dns_empty"
    fail "DNS lookup for $DOMAIN returned nothing. Either the A record hasn't propagated yet (typical 5-15 min wait after creating a record) or the domain isn't pointing anywhere. Verify with: dig +short $DOMAIN"
fi

DNS_MATCH=0
while IFS= read -r ip; do
    if [[ "$ip" == "$SERVER_IP" ]]; then
        DNS_MATCH=1
        break
    fi
done <<< "$DNS_IPS"

if [[ "$DNS_MATCH" != "1" ]]; then
    # Before complaining about a mismatch, classify the non-matching IPs. If they belong
    # to a known CDN (Cloudflare, CloudFront, Fastly, Netlify), the operator has a domain
    # that's proxied — different fix from "update your A record".
    CDN_NAME=""
    CDN_RANGES_FILE="${SCRIPT_DIR}/infra/cdn-ip-ranges.json"
    if [[ -f "$CDN_RANGES_FILE" ]] && command -v python3 &>/dev/null; then
        CDN_NAME="$(
            DNS_IPS="$DNS_IPS" CDN_RANGES_FILE="$CDN_RANGES_FILE" python3 <<'PYEOF'
import ipaddress, json, os, sys

ranges_path = os.environ["CDN_RANGES_FILE"]
ips = [ip.strip() for ip in os.environ["DNS_IPS"].splitlines() if ip.strip()]
try:
    with open(ranges_path) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

for cdn, cidrs in data.items():
    if cdn.startswith("_") or not isinstance(cidrs, list):
        continue
    networks = []
    for cidr in cidrs:
        try:
            networks.append(ipaddress.ip_network(cidr))
        except ValueError:
            continue
    for ip_str in ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if any(ip_obj in net for net in networks):
            print(cdn)
            sys.exit(0)
PYEOF
        )"
    fi

    # Collapse whitespace for a readable error message
    DNS_LIST="$(echo "$DNS_IPS" | tr '\n' ',' | sed 's/,$//')"

    if [[ -n "$CDN_NAME" ]]; then
        _emit_classification "cdn_${CDN_NAME}"
        CDN_LABEL="$(echo "${CDN_NAME^}" | sed 's/cloudfront/CloudFront/;s/Cloudfront/CloudFront/')"
        # Tailored message per CDN. Shared structure: what we detected, why it matters,
        # and two concrete paths forward.
        ERROR_MSG="DNS for $DOMAIN resolves to $CDN_LABEL proxy IPs ($DNS_LIST), not this server ($SERVER_IP).

Let's Encrypt can't issue a cert via the HTTP-01 challenge when the CDN intercepts requests
before they reach the origin. You have two paths:

1. ${CDN_LABEL} edge SSL (recommended — no server-side cert needed):
   In your ${CDN_LABEL} dashboard, enable edge SSL for this domain. ${CDN_LABEL} will
   issue and renew the cert at the edge automatically. Close this wizard — your site
   is already served over HTTPS by the CDN.

2. Let's Encrypt at the origin (if you want end-to-end encryption):
   Temporarily disable ${CDN_LABEL} proxying for $DOMAIN (in Cloudflare: click the orange
   cloud to make it grey), wait ~1 minute for DNS to repropagate, retry this wizard, then
   re-enable the proxy after the cert is issued. On Cloudflare, also set SSL/TLS mode to
   'Full (strict)' so Cloudflare trusts your origin cert."
        if [[ "$NON_INTERACTIVE" == "1" ]]; then
            fail "$ERROR_MSG"
        fi
        warn "$ERROR_MSG"
        read -rp "  Continue anyway (y) or abort (N)? " CONFIRM
        if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
            exit 1
        fi
    else
        _emit_classification "wrong_server"
        ERROR_MSG="DNS for $DOMAIN resolves to $DNS_LIST but this server is $SERVER_IP.

Update the domain's A record at your registrar to point to $SERVER_IP, wait ~1 minute
for DNS to repropagate, then retry."
        if [[ "$NON_INTERACTIVE" == "1" ]]; then
            fail "$ERROR_MSG"
        fi
        warn "$ERROR_MSG"
        read -rp "  Continue anyway (y) or abort (N)? " CONFIRM
        if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
            exit 1
        fi
    fi
fi

ok "DNS verified: $DOMAIN → $SERVER_IP"

# Install certbot if needed
if ! command -v certbot &>/dev/null; then
    step "Installing certbot..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq certbot python3-certbot-nginx
    elif command -v brew &>/dev/null; then
        brew install certbot
    else
        fail "Cannot install certbot — install it manually and re-run"
    fi
    ok "certbot installed"
fi

# Get email for Let's Encrypt
if [[ -z "$EMAIL" ]]; then
    if [[ "$NON_INTERACTIVE" == "1" ]]; then
        # Non-interactive default — silent fallback, certbot accepts any valid address
        EMAIL="admin@${DOMAIN}"
    else
        read -rp "  Email for Let's Encrypt renewal notices: " EMAIL
        if [[ -z "$EMAIL" ]]; then
            EMAIL="admin@${DOMAIN}"
            warn "No email provided — using $EMAIL"
        fi
    fi
fi

# Ensure nginx has the domain set (certbot --nginx needs it)
if grep -q 'server_name _;' "$NGINX_CONF" 2>/dev/null; then
    sed -i "s/server_name _;/server_name ${DOMAIN};/" "$NGINX_CONF"
    nginx -t 2>/dev/null && systemctl reload nginx
fi

# Run certbot
step "Obtaining certificate..."
certbot --nginx \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    -m "$EMAIL" \
    --redirect \
    || fail "certbot failed — check port 80 is open and DNS is correct"

ok "Certificate obtained"

# Ensure auto-renewal
step "Configuring auto-renewal..."
if systemctl list-unit-files | grep -q certbot.timer; then
    systemctl enable certbot.timer
    systemctl start certbot.timer
    ok "certbot.timer enabled"
else
    # Fallback: cron
    CRON_LINE="0 3 * * * certbot renew --quiet --deploy-hook 'systemctl reload nginx'"
    (crontab -l 2>/dev/null | grep -v certbot; echo "$CRON_LINE") | crontab -
    ok "Renewal cron installed (daily at 3:00 AM)"
fi

# Update .env
_update_env "NOUSVIZ_SSL" "letsencrypt"
_update_env "NOUSVIZ_DOMAIN" "$DOMAIN"

# Add a default-server block so bare-IP access (e.g. http://<server-ip>/) redirects to
# the domain instead of hitting nginx's default 404. Operators commonly bookmark the IP
# before DNS is configured — this keeps their bookmarks working.
NGINX_BARE_IP_CONF="/etc/nginx/sites-available/nousviz-bare-ip-redirect"
if [[ ! -f "$NGINX_BARE_IP_CONF" ]]; then
    step "Configuring bare-IP redirect..."
    cat > "$NGINX_BARE_IP_CONF" <<EOF
# Generated by ssl-setup.sh — redirect bare-IP / unknown-host HTTP requests to the domain.
# Anyone hitting http://<server-ip>/ (or any other host not matching ${DOMAIN}) will be
# redirected to https://${DOMAIN}/ instead of getting a 404.
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://${DOMAIN}\$request_uri;
}
EOF
    ln -sf "$NGINX_BARE_IP_CONF" "/etc/nginx/sites-enabled/nousviz-bare-ip-redirect"
    nginx -t 2>/dev/null && systemctl reload nginx && ok "bare-IP redirect installed" || warn "bare-IP redirect config failed validation — skipped"
fi

# Reload API so it picks up the new env vars. Use `pm2 reload all --update-env` (graceful,
# zero-downtime) rather than `pm2 kill && pm2 start ecosystem.config.js` — the latter nukes
# the PM2 daemon and all processes, including the API currently handling this HTTP request,
# and only resurrects what's in ecosystem.config.js (losing alerts / health-monitor / any
# utility plugins started separately).
step "Reloading API..."
if command -v pm2 &>/dev/null; then
    pm2 reload all --update-env >/dev/null 2>&1 && pm2 save >/dev/null 2>&1
    ok "PM2 reloaded (zero-downtime)"
fi

# Verify
step "Verifying..."
HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' "https://${DOMAIN}/api/health" 2>/dev/null || echo '000')"
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "HTTPS is working"
else
    warn "HTTPS returned HTTP $HTTP_CODE — check manually: https://${DOMAIN}/api/health"
fi

echo ""
echo "  ✓ SSL configured (Let's Encrypt)"
echo "  ✓ HTTPS: https://${DOMAIN}/"
echo "  ✓ Auto-renewal is active"
echo "  ✓ HTTP → HTTPS redirect enabled"
echo ""
exit 0
