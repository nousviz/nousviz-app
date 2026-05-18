/**
 * CheckAction — shared renderer for HealthCheck.action (P115 v0.8.4).
 *
 * Extracted from Topbar.tsx so the System Status page and the topbar
 * dropdown render actions identically. The modal-trigger branches
 * (`ssl-setup`, `setup-wizard`) take callbacks so each consumer can
 * wire them to its own state.
 */

import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import type { HealthCheck } from "@/lib/health-checks";

interface CheckActionProps {
  /** Pull just the `action` field; lets callers pass any shape they like. */
  action: NonNullable<HealthCheck["action"]>;
  /** Called before navigating / opening a modal — typically used to
   * close the containing dropdown. Fires for all action types. */
  onFire?: () => void;
  /** onClick=="ssl-setup" opens the SSL setup modal. Caller owns state. */
  onSslSetup?: () => void;
  /** onClick=="setup-wizard" opens the setup wizard. Caller owns state. */
  onSetupWizard?: () => void;
  /** Tailwind classes applied to all variants. */
  className?: string;
}

export default function CheckAction({
  action,
  onFire,
  onSslSetup,
  onSetupWizard,
  className,
}: CheckActionProps) {
  const baseClass = cn(
    "text-[11px] text-primary hover:underline",
    className,
  );

  if (action.onClick === "ssl-setup") {
    return (
      <button
        onClick={() => {
          onFire?.();
          onSslSetup?.();
        }}
        className={baseClass}
      >
        {action.label}
      </button>
    );
  }
  if (action.onClick === "setup-wizard") {
    return (
      <button
        onClick={() => {
          onFire?.();
          onSetupWizard?.();
        }}
        className={baseClass}
      >
        {action.label}
      </button>
    );
  }
  if (action.href) {
    return (
      <Link
        to={action.href}
        onClick={() => onFire?.()}
        className={baseClass}
      >
        {action.label}
      </Link>
    );
  }
  return null;
}
