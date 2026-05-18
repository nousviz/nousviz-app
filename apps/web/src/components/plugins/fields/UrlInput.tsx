/**
 * UrlInput — `type: url` field renderer (P120, v0.8.6).
 *
 * Native HTML5 type="url" for basic browser validation. Optional `scheme:`
 * constraint enforces a specific URL scheme (e.g. mysql://).
 */

import { useMemo } from "react";
import { AlertCircle } from "lucide-react";

interface Props {
  name: string;
  value: string;
  onChange: (next: string) => void;
  scheme?: string;
  required?: boolean;
}

function validate(raw: string, scheme?: string): string | null {
  if (!raw) return null;
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    return "Not a valid URL";
  }
  if (scheme && parsed.protocol !== `${scheme}:`) {
    return `Scheme must be ${scheme}:// (got ${parsed.protocol}//)`;
  }
  if (scheme && (parsed.username || parsed.password)) {
    return "URL contains credentials — use the credential fields instead of embedding in the URL";
  }
  return null;
}

export default function UrlInput({ name, value, onChange, scheme, required }: Props) {
  const error = useMemo(() => validate(value, scheme), [value, scheme]);

  return (
    <div className="space-y-1">
      <input
        name={name}
        type="url"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={scheme ? `${scheme}://host:port/path` : "https://example.com"}
        required={required}
        className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-80"
      />
      {error && (
        <p className="text-[11px] text-red-400 inline-flex items-center gap-1">
          <AlertCircle className="w-3 h-3" /> {error}
        </p>
      )}
    </div>
  );
}
