import { useEffect, useState } from "react";
import { parseHash, operationHash, type HttpMethod } from "./types";

export interface SelectedOp {
  method: HttpMethod;
  path: string;
}

export function useHashOperation(): [SelectedOp | null, (op: SelectedOp) => void] {
  const [selected, setSelected] = useState<SelectedOp | null>(() =>
    typeof window !== "undefined" ? parseHash(window.location.hash) : null
  );

  useEffect(() => {
    function onHashChange() {
      setSelected(parseHash(window.location.hash));
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function setOp(op: SelectedOp) {
    const hash = "#" + operationHash(op.method, op.path);
    if (window.location.hash !== hash) {
      // pushState so back/forward navigates between operations.
      history.pushState(null, "", window.location.pathname + window.location.search + hash);
      setSelected(op);
    }
  }

  return [selected, setOp];
}
