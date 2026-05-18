import { createContext, useContext, useEffect, type ReactNode } from "react";

/**
 * BootCoordinator (B225 v0.9.7.8) — lets the destination page signal
 * "I'm ready to be seen" up to AuthGate so the boot splash carries
 * through the first page's data fetch instead of dismissing prematurely.
 *
 * AuthGate owns the actual state (`pageReady`, `isFirstPaint`); this
 * context just exposes the signaller to descendants.
 *
 * Outside the provider, the hook returns no-ops and `isFirstPaint = false`,
 * so any consumer is safe to call without guards.
 */
interface BootCoordinatorValue {
  isFirstPaint: boolean;
  markBootPageReady: () => void;
}

const BootCoordinatorContext = createContext<BootCoordinatorValue>({
  isFirstPaint: false,
  markBootPageReady: () => {},
});

export function BootCoordinatorProvider({
  value,
  children,
}: {
  value: BootCoordinatorValue;
  children: ReactNode;
}) {
  return (
    <BootCoordinatorContext.Provider value={value}>
      {children}
    </BootCoordinatorContext.Provider>
  );
}

export function useBootCoordinator() {
  return useContext(BootCoordinatorContext);
}

/**
 * Convenience hook for fast pages: signals "boot page ready" once on
 * mount. Pages with meaningful loading states should NOT use this —
 * they should call `markBootPageReady` from `useBootCoordinator()`
 * after their initial fetch resolves.
 */
export function useMarkBootReadyOnMount() {
  const { markBootPageReady } = useBootCoordinator();
  useEffect(() => {
    markBootPageReady();
  }, [markBootPageReady]);
}
