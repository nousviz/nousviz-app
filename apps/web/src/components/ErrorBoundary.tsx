import { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
  /** B154 (v0.9.4.6): optional fallback for callers that want an
   * inline error UI instead of the full-page treatment. Receives the
   * error and a reset callback. Useful per-widget so one bad plugin
   * widget doesn't take out the whole route. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** Optional context label for console logs (e.g. "plugin-widget:foo/Bar") */
  context?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    const ctx = this.props.context ? ` [${this.props.context}]` : "";
    console.error(`ErrorBoundary caught${ctx}:`, error, info.componentStack);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      // B154: if a fallback was provided, use it (caller wants inline UI).
      if (this.props.fallback && this.state.error) {
        return this.props.fallback(this.state.error, this.reset);
      }
      // Default: full-page treatment (route-level boundary).
      return (
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
          <AlertTriangle className="w-10 h-10 text-yellow-400 mb-4" />
          <h2 className="font-display text-lg text-foreground mb-2">Something went wrong</h2>
          <p className="text-sm text-muted-foreground max-w-md mb-4">
            This page encountered an error. Try refreshing, or navigate to a different page.
          </p>
          {this.state.error && (
            <pre className="text-[11px] text-muted-foreground/60 font-mono-deck bg-secondary/30 rounded-lg p-3 max-w-md overflow-auto max-h-32">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
            className="mt-4 h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
