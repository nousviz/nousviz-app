import { useState, useEffect, useCallback } from "react";
import { useLocation } from "react-router-dom";
import {
  MessageSquare,
  X,
  Pin,
  CheckCircle2,
  Calendar,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

const API_BASE = "/api";

interface Note {
  id: string;
  page_path: string;
  plugin_id: string | null;
  body: string;
  date_start: string | null;
  date_end: string | null;
  pinned: boolean;
  resolved: boolean;
  archived: boolean;
  created_by: string;
  created_at: string;
}

// ── Notes Button (shown in topbar) ───────────────────────────────────

export function NotesButton({ count, onClick }: { count: number; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="h-9 px-3 rounded-md bg-secondary hover:bg-secondary/80 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors relative"
      title="Page notes"
    >
      <MessageSquare className="h-4 w-4" />
      {count > 0 && (
        <span className="text-xs font-mono-deck">{count}</span>
      )}
    </button>
  );
}

// ── Notes Panel ──────────────────────────────────────────────────────

export default function NotesPanel({
  open,
  onClose,
  activeDateRange,
}: {
  open: boolean;
  onClose: () => void;
  activeDateRange?: { from: string; to: string } | null;
}) {
  const location = useLocation();
  const pagePath = location.pathname;
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState("");
  const [newDateStart, setNewDateStart] = useState("");
  const [newDateEnd, setNewDateEnd] = useState("");
  const [showDateFields, setShowDateFields] = useState(false);

  const fetchNotes = useCallback(async () => {
    try {
      const res = await apiFetch(`${API_BASE}/notes?page_path=${encodeURIComponent(pagePath)}`);
      const data = await res.json();
      setNotes(data.notes);
    } catch {
      setNotes([]);
    } finally {
      setLoading(false);
    }
  }, [pagePath]);

  useEffect(() => {
    if (open) fetchNotes();
  }, [open, fetchNotes]);

  const handleCreate = async () => {
    if (!newNote.trim()) return;
    await apiFetch(`${API_BASE}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        page_path: pagePath,
        body: newNote,
        date_start: newDateStart || null,
        date_end: newDateEnd || null,
      }),
    });
    setNewNote("");
    setNewDateStart("");
    setNewDateEnd("");
    setShowDateFields(false);
    fetchNotes();
  };

  const handleResolve = async (id: string, resolved: boolean) => {
    await apiFetch(`${API_BASE}/notes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolved }),
    });
    fetchNotes();
  };

  const handlePin = async (id: string, pinned: boolean) => {
    await apiFetch(`${API_BASE}/notes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pinned }),
    });
    fetchNotes();
  };

  const handleDelete = async (id: string) => {
    await apiFetch(`${API_BASE}/notes/${id}`, { method: "DELETE" });
    fetchNotes();
  };

  // Check if a note is relevant to the current date range
  const isRelevant = (note: Note): boolean => {
    if (!note.date_start) return true; // No date = always relevant
    if (!activeDateRange) return true; // No active filter = show all

    const noteStart = note.date_start;
    const noteEnd = note.date_end || note.date_start;

    // Overlap check
    return noteStart <= activeDateRange.to && noteEnd >= activeDateRange.from;
  };

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-50" onClick={onClose} />
      <div className="fixed top-0 right-0 bottom-0 w-[380px] bg-card border-l border-border z-50 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="h-[var(--topbar-h)] flex items-center justify-between px-5 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-primary" />
            <span className="font-display text-sm text-foreground">Notes</span>
            <span className="text-xs text-muted-foreground">({notes.length})</span>
          </div>
          <button onClick={onClose} className="h-8 w-8 rounded-md hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* New note form */}
        <div className="p-4 border-b border-border">
          <textarea
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Add a note about what you're seeing..."
            rows={2}
            className="w-full px-3 py-2 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body resize-none"
          />
          <div className="flex items-center justify-between mt-2">
            <button
              onClick={() => setShowDateFields(!showDateFields)}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
            >
              <Calendar className="w-3 h-3" />
              {showDateFields ? "Hide dates" : "Add date range"}
            </button>
            <button
              onClick={handleCreate}
              disabled={!newNote.trim()}
              className="h-7 px-3 rounded-md bg-primary text-primary-foreground text-xs font-body hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              Add Note
            </button>
          </div>
          {showDateFields && (
            <div className="flex items-center gap-2 mt-2">
              <input
                type="date"
                value={newDateStart}
                onChange={(e) => setNewDateStart(e.target.value)}
                className="h-7 px-2 rounded bg-background border border-border text-xs text-foreground flex-1"
                placeholder="From"
              />
              <span className="text-xs text-muted-foreground">to</span>
              <input
                type="date"
                value={newDateEnd}
                onChange={(e) => setNewDateEnd(e.target.value)}
                className="h-7 px-2 rounded bg-background border border-border text-xs text-foreground flex-1"
                placeholder="To"
              />
            </div>
          )}
        </div>

        {/* Notes list */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-16 bg-secondary/30 rounded animate-pulse" />
              ))}
            </div>
          ) : notes.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No notes on this page yet.
            </div>
          ) : (
            <div className="divide-y divide-border">
              {notes.map((note) => {
                const relevant = isRelevant(note);
                return (
                  <div
                    key={note.id}
                    className={cn(
                      "p-4 transition-opacity",
                      !relevant && "opacity-40",
                      note.resolved && "opacity-60"
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-1 min-w-0">
                        <p className={cn(
                          "text-sm font-body leading-relaxed",
                          note.resolved ? "text-muted-foreground line-through" : "text-foreground"
                        )}>
                          {note.body}
                        </p>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          {note.date_start && (
                            <span className={cn(
                              "text-[10px] px-1.5 py-0.5 rounded-full flex items-center gap-1",
                              relevant
                                ? "bg-primary/10 text-primary"
                                : "bg-secondary text-muted-foreground"
                            )}>
                              <Calendar className="w-2.5 h-2.5" />
                              {note.date_start}
                              {note.date_end && note.date_end !== note.date_start && ` → ${note.date_end}`}
                            </span>
                          )}
                          {note.pinned && (
                            <span className="text-[10px] text-primary"><Pin className="w-2.5 h-2.5" /></span>
                          )}
                          <span className="text-[10px] text-muted-foreground">
                            {new Date(note.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-0.5 shrink-0">
                        <button
                          onClick={() => handleResolve(note.id, !note.resolved)}
                          className={cn(
                            "h-6 w-6 rounded flex items-center justify-center transition-colors",
                            note.resolved ? "text-green-400" : "text-muted-foreground hover:text-green-400"
                          )}
                          title={note.resolved ? "Unresolve" : "Mark resolved"}
                        >
                          <CheckCircle2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handlePin(note.id, !note.pinned)}
                          className={cn(
                            "h-6 w-6 rounded flex items-center justify-center transition-colors",
                            note.pinned ? "text-primary" : "text-muted-foreground hover:text-primary"
                          )}
                          title={note.pinned ? "Unpin" : "Pin"}
                        >
                          <Pin className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleDelete(note.id)}
                          className="h-6 w-6 rounded flex items-center justify-center text-muted-foreground hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
