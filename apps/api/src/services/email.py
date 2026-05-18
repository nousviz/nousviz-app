"""
SMTP email service — core platform primitive (P58 design doc §4).

Used by: user invites, password reset (follow-up), alert delivery (v0.3.2),
operator notifications. SMTP is in core because three separate features
need it — a utility-plugin boundary would force three separate installs.

Configuration:
  SMTP_HOST, SMTP_PORT, SMTP_FROM_ADDRESS, SMTP_FROM_NAME in .env
  SMTP_USERNAME + SMTP_PASSWORD stored encrypted in the credentials table
  (not in .env) via the credential manager. Fallback: read SMTP_USERNAME /
  SMTP_PASSWORD from .env for operators who haven't run the wizard yet.

All sends are synchronous in v0.3.1. If alert delivery (v0.3.2) needs
higher throughput, add a lightweight queue then.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("nousviz.email")


def _get_smtp_config() -> dict | None:
    """Read SMTP config from env. Returns None if not configured."""
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return None
    return {
        "host": host,
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "username": os.environ.get("SMTP_USERNAME", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_address": os.environ.get("SMTP_FROM_ADDRESS", "noreply@nousviz.local"),
        "from_name": os.environ.get("SMTP_FROM_NAME", "NousViz"),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
        "timeout": int(os.environ.get("SMTP_TIMEOUT_SEC", "30")),
    }


def is_configured() -> bool:
    """Returns True if SMTP is configured (SMTP_HOST is set)."""
    return bool(os.environ.get("SMTP_HOST", "").strip())


def _send(to: str, subject: str, html: str, plain: str) -> tuple[bool, str]:
    """Send an email. Returns (ok, error_message)."""
    cfg = _get_smtp_config()
    if not cfg:
        return False, "SMTP not configured. Set SMTP_HOST in .env or configure via Settings."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{cfg['from_name']} <{cfg['from_address']}>"
    msg["To"] = to
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if cfg["port"] == 465:
            # SMTPS (implicit TLS)
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=cfg["timeout"])
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=cfg["timeout"])
            if cfg["use_tls"]:
                server.starttls()

        if cfg["username"]:
            server.login(cfg["username"], cfg["password"])

        server.sendmail(cfg["from_address"], [to], msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to}: {subject}")
        return True, ""

    except smtplib.SMTPAuthenticationError as e:
        err = f"Authentication failed — check username and password. ({e})"
        logger.error(err)
        return False, err
    except smtplib.SMTPException as e:
        err = f"SMTP error: {e}"
        logger.error(err)
        return False, err
    except TimeoutError:
        err = f"Connection timed out — could not reach {cfg['host']}:{cfg['port']}. Check that your server allows outbound traffic on port {cfg['port']} (firewall/security group)."
        logger.error(err)
        return False, err
    except OSError as e:
        err = f"Connection failed to {cfg['host']}:{cfg['port']} — {e}. Check host, port, and firewall settings."
        logger.error(err)
        return False, err
    except Exception as e:
        err = f"Email send failed: {e}"
        logger.error(err)
        return False, err


def _wrap_html(body: str) -> str:
    """Wrap email body HTML in the branded NousViz template."""
    from_name = os.environ.get("SMTP_FROM_NAME", "NousViz")
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0c0c10;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0c0c10;">
    <tr><td align="center" style="padding:40px 20px 0;">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;">
        <!-- Logo -->
        <tr><td style="padding:0 0 32px;">
          <span style="font-size:22px;font-weight:700;color:#fff;letter-spacing:0.5px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">Nous<span style="color:#3b82f6;">Viz</span></span>
        </td></tr>
        <!-- Content -->
        <tr><td style="background:#16161d;border-radius:12px;padding:32px;">
          {body}
        </td></tr>
        <!-- Footer -->
        <tr><td style="padding:24px 0 40px;text-align:center;">
          <p style="color:#555;font-size:11px;margin:0;">Sent by {from_name} &middot; Self-hosted data intelligence</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_invite_email(to: str, invite_url: str, inviter_name: str) -> tuple[bool, str]:
    """Send an invitation email to a new user."""
    subject = "You've been invited to NousViz"
    plain = f"""{inviter_name} invited you to NousViz.

Click the link below to set your password and get started:
{invite_url}

This invitation expires in 7 days.

If you didn't expect this email, you can ignore it."""

    body = f"""
          <h2 style="color:#f0f0f5;font-size:20px;font-weight:600;margin:0 0 8px;">You're invited</h2>
          <p style="color:#999;font-size:14px;line-height:1.6;margin:0 0 24px;">{inviter_name} invited you to join their NousViz instance. Click below to set your password and get started.</p>
          <table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="border-radius:8px;background:#3b82f6;">
            <a href="{invite_url}" style="display:inline-block;padding:12px 28px;color:#fff;font-size:14px;font-weight:600;text-decoration:none;">Accept Invitation</a>
          </td></tr></table>
          <p style="color:#555;font-size:12px;line-height:1.5;margin:24px 0 0;">This invitation expires in 7 days. If you didn't expect this email, you can safely ignore it.</p>"""

    return _send(to, subject, _wrap_html(body), plain)


def send_test_email(to: str) -> tuple[bool, str]:
    """Send a test email to verify SMTP configuration."""
    subject = "NousViz — SMTP Test"
    plain = "This is a test email from NousViz. If you received this, SMTP is working correctly."

    body = """
          <h2 style="color:#f0f0f5;font-size:20px;font-weight:600;margin:0 0 8px;">SMTP is working</h2>
          <p style="color:#999;font-size:14px;line-height:1.6;margin:0;">This is a test email from your NousViz instance. If you received this, your SMTP configuration is correct and emails will be delivered for invites, alerts, and notifications.</p>"""

    return _send(to, subject, _wrap_html(body), plain)


def send_password_reset_email(to: str, reset_url: str) -> tuple[bool, str]:
    """Send a password reset email."""
    subject = "Reset your NousViz password"
    plain = f"""Someone requested a password reset for your NousViz account.

Click the link below to set a new password:
{reset_url}

This link expires in 1 hour. If you didn't request this, you can ignore it."""

    body = f"""
          <h2 style="color:#f0f0f5;font-size:20px;font-weight:600;margin:0 0 8px;">Reset your password</h2>
          <p style="color:#999;font-size:14px;line-height:1.6;margin:0 0 24px;">Someone requested a password reset for your NousViz account.</p>
          <table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="border-radius:8px;background:#3b82f6;">
            <a href="{reset_url}" style="display:inline-block;padding:12px 28px;color:#fff;font-size:14px;font-weight:600;text-decoration:none;">Reset Password</a>
          </td></tr></table>
          <p style="color:#555;font-size:12px;line-height:1.5;margin:24px 0 0;">This link expires in 1 hour. If you didn't request this, you can safely ignore it.</p>"""

    return _send(to, subject, _wrap_html(body), plain)
