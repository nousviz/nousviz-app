/**
 * Privacy System — Core platform feature for confidential data masking.
 *
 * Plugin builders mark fields as confidential. Users choose how to handle them:
 *   - "visible" — show everything (default)
 *   - "blur" — CSS blur effect, hover to peek
 *   - "obfuscate" — replace with masked version (e.g. "341355" → "34••••")
 *
 * Usage in any widget:
 *   import { usePrivacy, ConfidentialValue } from "@/lib/privacy";
 *
 *   // As a component:
 *   <ConfidentialValue value="341355" field="player_id" />
 *
 *   // As a hook:
 *   const { maskValue, mode } = usePrivacy();
 *   <span>{maskValue("341355", "player_id")}</span>
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

// ── Types ───────────────────────────────────────────────────────────────

export type PrivacyMode = "visible" | "blur" | "obfuscate";

interface PrivacyContextValue {
  mode: PrivacyMode;
  setMode: (m: PrivacyMode) => void;
  confidentialFields: Set<string>;
  addField: (field: string) => void;
  removeField: (field: string) => void;
  isConfidential: (field: string) => boolean;
  maskValue: (value: string | number, field: string) => string;
}

const STORAGE_KEY = "nousviz-privacy-mode";
const FIELDS_KEY = "nousviz-privacy-fields";

// ── Default confidential fields ─────────────────────────────────────────
// Plugin builders can register more via addField()

const DEFAULT_CONFIDENTIAL = new Set([
  "player_id",
  "player_alias",
  "email",
  "ip_address",
  "phone",
  "api_key",
  "password",
  "secret",
]);

// ── Obfuscation logic ───────────────────────────────────────────────────

function obfuscate(value: string): string {
  if (!value || value === "—") return value;
  const str = String(value);
  if (str.length <= 3) return "•••";
  // Show first 2 and last 1 char, mask the rest
  const visible = Math.min(2, Math.floor(str.length * 0.3));
  return str.slice(0, visible) + "•".repeat(str.length - visible - 1) + str.slice(-1);
}

// ── Context ─────────────────────────────────────────────────────────────

const PrivacyContext = createContext<PrivacyContextValue>({
  mode: "visible",
  setMode: () => {},
  confidentialFields: DEFAULT_CONFIDENTIAL,
  addField: () => {},
  removeField: () => {},
  isConfidential: () => false,
  maskValue: (v) => String(v),
});

export function usePrivacy() {
  return useContext(PrivacyContext);
}

// ── Provider ────────────────────────────────────────────────────────────

export function PrivacyProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<PrivacyMode>(() => {
    try {
      return (localStorage.getItem(STORAGE_KEY) as PrivacyMode) || "visible";
    } catch {
      return "visible";
    }
  });

  const [fields, setFields] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem(FIELDS_KEY);
      if (stored) return new Set([...DEFAULT_CONFIDENTIAL, ...JSON.parse(stored)]);
    } catch {}
    return new Set(DEFAULT_CONFIDENTIAL);
  });

  const setMode = useCallback((m: PrivacyMode) => {
    setModeState(m);
    try { localStorage.setItem(STORAGE_KEY, m); } catch {}
  }, []);

  const addField = useCallback((field: string) => {
    setFields(prev => {
      const next = new Set(prev);
      next.add(field);
      try { localStorage.setItem(FIELDS_KEY, JSON.stringify([...next])); } catch {}
      return next;
    });
  }, []);

  const removeField = useCallback((field: string) => {
    setFields(prev => {
      const next = new Set(prev);
      next.delete(field);
      try { localStorage.setItem(FIELDS_KEY, JSON.stringify([...next])); } catch {}
      return next;
    });
  }, []);

  const isConfidential = useCallback((field: string) => fields.has(field), [fields]);

  const maskValue = useCallback((value: string | number, field: string): string => {
    const str = String(value);
    if (mode === "visible" || !fields.has(field)) return str;
    if (mode === "obfuscate") return obfuscate(str);
    return str; // blur mode is handled by CSS, value stays the same
  }, [mode, fields]);

  return (
    <PrivacyContext.Provider value={{ mode, setMode, confidentialFields: fields, addField, removeField, isConfidential, maskValue }}>
      {children}
    </PrivacyContext.Provider>
  );
}

// ── Confidential Value Component ────────────────────────────────────────
// Drop-in replacement for displaying any potentially confidential value.

export function ConfidentialValue({
  value,
  field,
  className = "",
}: {
  value: string | number;
  field: string;
  className?: string;
}) {
  const { mode, isConfidential, maskValue } = usePrivacy();
  const str = String(value);

  if (!isConfidential(field) || mode === "visible") {
    return <span className={className}>{str}</span>;
  }

  if (mode === "blur") {
    return (
      <span
        className={`${className} select-none transition-all duration-200`}
        style={{ filter: "blur(5px)" }}
        onMouseEnter={(e) => { (e.target as HTMLElement).style.filter = "blur(0px)"; }}
        onMouseLeave={(e) => { (e.target as HTMLElement).style.filter = "blur(5px)"; }}
        title="Hover to reveal"
      >
        {str}
      </span>
    );
  }

  // obfuscate
  return <span className={className}>{maskValue(str, field)}</span>;
}

// ── Privacy Toggle Component ────────────────────────────────────────────
// Drop into any page's header/toolbar area.

export function PrivacyToggle({ compact = false }: { compact?: boolean }) {
  const { mode, setMode } = usePrivacy();

  if (compact) {
    return (
      <button
        onClick={() => {
          const next: PrivacyMode = mode === "visible" ? "blur" : mode === "blur" ? "obfuscate" : "visible";
          setMode(next);
        }}
        className="h-8 px-3 rounded-md bg-secondary text-xs flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
        title={`Privacy: ${mode}`}
      >
        {mode === "visible" ? "👁" : mode === "blur" ? "🔒" : "🔐"}
        {!compact && <span className="capitalize">{mode}</span>}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
      {(["visible", "blur", "obfuscate"] as PrivacyMode[]).map(m => (
        <button
          key={m}
          onClick={() => setMode(m)}
          className={`h-7 px-3 rounded-md text-[10px] font-medium transition-colors capitalize ${
            mode === m
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {m === "visible" ? "👁 Visible" : m === "blur" ? "🔒 Blur" : "🔐 Obfuscate"}
        </button>
      ))}
    </div>
  );
}
