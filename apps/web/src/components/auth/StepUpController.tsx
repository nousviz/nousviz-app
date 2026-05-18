/**
 * StepUpController — globally-mounted listener that shows StepUpModal
 * when apiFetch dispatches a `nousviz:stepup-required` event.
 *
 * B236 (v0.9.10.0). Mounted once at AppLayout level so any apiFetch
 * call from anywhere in the app can trigger the modal.
 */

import { useEffect, useState } from "react";
import StepUpModal from "./StepUpModal";
import { retryStepUpRequest, cancelStepUpRequest } from "@/lib/api";

export default function StepUpController() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onStepUp(e: Event) {
      const evt = e as CustomEvent<{ pending: boolean }>;
      setOpen(!!evt.detail?.pending);
    }
    window.addEventListener("nousviz:stepup-required", onStepUp);
    return () => window.removeEventListener("nousviz:stepup-required", onStepUp);
  }, []);

  return (
    <StepUpModal
      open={open}
      onSuccess={() => {
        setOpen(false);
        retryStepUpRequest();
      }}
      onCancel={() => {
        setOpen(false);
        cancelStepUpRequest();
      }}
    />
  );
}
