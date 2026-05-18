import { useState, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Terminal } from "lucide-react";

interface HistoryEntry {
  command: string;
  output: string;
  ok: boolean;
}

export default function AdminCliPage() {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [accessDenied, setAccessDenied] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [history]);

  async function runCommand(cmd: string) {
    if (!cmd.trim()) return;

    if (cmd.trim() === "clear") {
      setHistory([]);
      setInput("");
      return;
    }

    setRunning(true);
    setCmdHistory(prev => [cmd, ...prev.slice(0, 50)]);
    setHistoryIdx(-1);

    const res = await apiFetch("/api/admin/cli", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd.trim() }),
    });

    if (res.status === 403) {
      setAccessDenied(true);
      setRunning(false);
      return;
    }

    const data = await res.json().catch(() => ({ output: "Failed to parse response", ok: false }));
    setHistory(prev => [...prev, { command: cmd.trim(), output: data.output || "", ok: data.ok }]);
    setInput("");
    setRunning(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !running) {
      runCommand(input);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (cmdHistory.length > 0) {
        const newIdx = Math.min(historyIdx + 1, cmdHistory.length - 1);
        setHistoryIdx(newIdx);
        setInput(cmdHistory[newIdx]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIdx > 0) {
        const newIdx = historyIdx - 1;
        setHistoryIdx(newIdx);
        setInput(cmdHistory[newIdx]);
      } else {
        setHistoryIdx(-1);
        setInput("");
      }
    } else if (e.key === "l" && e.ctrlKey) {
      e.preventDefault();
      setHistory([]);
    }
  }

  if (accessDenied) {
    return (
      <div className="max-w-[800px] py-20 text-center">
        <Terminal className="w-8 h-8 text-muted-foreground mx-auto mb-4" />
        <h2 className="font-display text-lg text-foreground mb-2">Access Denied</h2>
        <p className="text-sm text-muted-foreground">The admin CLI requires superadmin access.</p>
      </div>
    );
  }

  return (
    <div className="max-w-[900px] h-[calc(100vh-var(--topbar-h)-var(--banner-h,0px)-3rem)] flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <Terminal className="w-4 h-4 text-muted-foreground" />
        <h1 className="font-display text-sm text-foreground">Admin CLI</h1>
        <span className="text-[10px] text-muted-foreground font-mono-deck">Type 'help' for commands · Ctrl+L to clear</span>
      </div>

      <div
        ref={outputRef}
        onClick={() => inputRef.current?.focus()}
        className="flex-1 bg-[#0a0a0f] rounded-lg border border-border p-4 overflow-y-auto font-mono-deck text-[13px] leading-relaxed cursor-text"
      >
        {/* Welcome */}
        {history.length === 0 && (
          <div className="text-muted-foreground mb-4">
            <p>NousViz Admin CLI</p>
            <p>Type <span className="text-foreground">help</span> to see available commands.</p>
          </div>
        )}

        {/* Command history */}
        {history.map((entry, i) => (
          <div key={i} className="mb-3">
            <div className="flex items-center gap-2">
              <span className="text-primary">❯</span>
              <span className="text-foreground">{entry.command}</span>
            </div>
            <pre className={`whitespace-pre-wrap break-all mt-1 ${entry.ok ? "text-[#a0a0b0]" : "text-red-400"}`}>
              {entry.output}
            </pre>
          </div>
        ))}

        {/* Input line */}
        <div className="flex items-center gap-2">
          <span className="text-primary shrink-0">❯</span>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={running}
            autoComplete="off"
            spellCheck={false}
            className="flex-1 bg-transparent text-foreground outline-none border-none caret-primary disabled:opacity-50"
            placeholder={running ? "Running..." : ""}
          />
        </div>
      </div>
    </div>
  );
}
