"use client";
import { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

function formatTimestamp(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function StatusBadge({ status }) {
  const styles = {
    success: "bg-green-900/50 text-green-400",
    error: "bg-red-900/50 text-red-400",
    timeout: "bg-yellow-900/50 text-yellow-400",
    cancelled: "bg-zinc-800 text-zinc-400",
  };
  const cls = styles[status] || "bg-zinc-800 text-zinc-400";
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${cls}`}>
      {status}
    </span>
  );
}

export function ExecutionsPanel({ toolId }) {
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    if (!toolId) return;
    async function fetchHistory() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/tools/${encodeURIComponent(toolId)}?history=1&limit=20`
        );
        if (!res.ok) {
          setError(`Error ${res.status}`);
        } else {
          const data = await res.json();
          setExecutions(data.executions || []);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [toolId]);

  if (loading) {
    return <div className="text-zinc-400 text-sm py-4">Loading execution history...</div>;
  }

  if (error) {
    return <div className="text-red-400 text-sm py-4">Failed to load history: {error}</div>;
  }

  if (executions.length === 0) {
    return (
      <div className="py-6 text-center">
        <p className="text-zinc-500 text-sm">No executions yet.</p>
        <a
          href={`/tools/${encodeURIComponent(toolId)}/execute`}
          className="inline-block mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm font-medium"
        >
          Run your first execution
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-zinc-400 text-sm">{executions.length} recent execution{executions.length !== 1 ? "s" : ""}</p>
      </div>
      {executions.map((exec) => (
        <div
          key={exec.id}
          className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 text-sm"
        >
          <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
            <div className="flex items-center gap-2">
              <StatusBadge status={exec.status} />
              <span className="text-zinc-400 text-xs">{formatTimestamp(exec.timestamp)}</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-zinc-500">
              <span>{exec.duration_ms}ms</span>
              <button
                onClick={() => setExpanded(expanded === exec.id ? null : exec.id)}
                className="text-blue-400 hover:text-blue-300"
              >
                {expanded === exec.id ? "Hide details" : "Show details"}
              </button>
            </div>
          </div>

          {expanded === exec.id && (
            <div className="mt-3 space-y-2">
              {exec.arguments && Object.keys(exec.arguments).length > 0 && (
                <div>
                  <p className="text-zinc-500 text-xs mb-1">Arguments</p>
                  <pre className="bg-zinc-950 border border-zinc-700 rounded p-2 text-xs text-zinc-300 overflow-auto max-h-32">
                    {JSON.stringify(exec.arguments, null, 2)}
                  </pre>
                </div>
              )}
              {exec.result && (
                <div>
                  <p className="text-zinc-500 text-xs mb-1">Result</p>
                  <pre className="bg-zinc-950 border border-zinc-700 rounded p-2 text-xs text-zinc-300 overflow-auto max-h-48">
                    {JSON.stringify(exec.result, null, 2)}
                  </pre>
                </div>
              )}
              {exec.error_message && (
                <div>
                  <p className="text-zinc-500 text-xs mb-1">Error</p>
                  <p className="text-red-400 text-xs">{exec.error_message}</p>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
