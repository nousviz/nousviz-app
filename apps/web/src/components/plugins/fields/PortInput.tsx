/**
 * PortInput — `type: port` field renderer (P120, v0.8.6).
 *
 * Native number input with 1-65535 range and a "privileged port"
 * badge when value < 1024. Client-side validation prevents saving
 * out-of-range values.
 */

import { ShieldAlert } from "lucide-react";

interface Props {
  name: string;
  value: number | string;
  onChange: (next: number | "") => void;
  required?: boolean;
}

export default function PortInput({ name, value, onChange, required }: Props) {
  const num =
    typeof value === "number" ? value : value === "" ? NaN : parseInt(String(value), 10);
  const privileged = !Number.isNaN(num) && num > 0 && num < 1024;

  return (
    <div className="space-y-1">
      <input
        name={name}
        type="number"
        min={1}
        max={65535}
        step={1}
        value={value === "" ? "" : num}
        onChange={(e) => {
          const v = e.target.value;
          if (v === "") {
            onChange("");
          } else {
            onChange(parseInt(v, 10));
          }
        }}
        required={required}
        className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-32"
      />
      {privileged && (
        <p className="text-[11px] text-amber-400 inline-flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" /> Privileged port — may need root
        </p>
      )}
    </div>
  );
}
