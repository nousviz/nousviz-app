/**
 * FileInput — `type: file` field renderer (P120, v0.8.6).
 *
 * Drag-drop zone → reads File.text() into the value. Paste-text fallback
 * textarea is always visible for operators who copied from elsewhere.
 * With `format_hint: pem`, shows a ✓ when content contains BEGIN CERTIFICATE.
 *
 * Storage is a string (same as v0.8.5 textarea approach); the new UI is
 * purely for entering it more comfortably.
 */

import { useRef, useState } from "react";
import { UploadCloud, CheckCircle2, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  name: string;
  value: string;
  onChange: (next: string) => void;
  accept?: string;
  format_hint?: string;
  required?: boolean;
}

const MAX_FILE_SIZE = 1024 * 1024; // 1MB soft limit

function matchesHint(content: string, hint: string): boolean {
  if (hint === "pem") return /-----BEGIN [A-Z ]+-----/.test(content);
  if (hint === "json") {
    try { JSON.parse(content); return true; } catch { return false; }
  }
  return false;
}

export default function FileInput({ name, value, onChange, accept, format_hint, required }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function readFile(file: File) {
    setError(null);
    if (file.size > MAX_FILE_SIZE) {
      setError(`File too large (${(file.size / 1024).toFixed(1)} KB, max 1 MB)`);
      return;
    }
    const text = await file.text();
    setFileName(file.name);
    setFileSize(file.size);
    onChange(text);
  }

  function clear() {
    setFileName(null);
    setFileSize(null);
    onChange("");
    if (inputRef.current) inputRef.current.value = "";
  }

  const hintOk = format_hint && value ? matchesHint(value, format_hint) : false;

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) void readFile(file);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "rounded-md border-2 border-dashed px-4 py-6 text-center cursor-pointer transition-colors",
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-secondary/20",
        )}
      >
        <UploadCloud className="w-5 h-5 mx-auto mb-1 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">
          {fileName ? (
            <>
              <span className="text-foreground font-mono-deck">{fileName}</span>
              {fileSize !== null && <> · {(fileSize / 1024).toFixed(1)} KB</>}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  clear();
                }}
                className="ml-2 inline-flex items-center gap-0.5 text-red-400 hover:text-red-300"
              >
                <X className="w-3 h-3" /> remove
              </button>
            </>
          ) : (
            <>Drop a file or click to browse</>
          )}
        </p>
        {hintOk && (
          <p className="text-xs text-emerald-400 mt-1 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> looks like a valid {format_hint}
          </p>
        )}
        {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void readFile(file);
        }}
      />
      <div>
        <p className="text-[10px] text-muted-foreground mb-1">
          or paste content below:
        </p>
        <textarea
          name={name}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          required={required}
          className="w-full px-3 py-2 rounded-md bg-background border border-border text-xs font-mono-deck text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
    </div>
  );
}
