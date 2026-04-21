"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

export default function ExecuteToolPage() {
  const { id } = useParams();
  const router = useRouter();
  const [tool, setTool] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Execution state
  const [args, setArgs] = useState({});
  const [argKey, setArgKey] = useState("");
  const [argValue, setArgValue] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  const [execError, setExecError] = useState(null);
  const [durationMs, setDurationMs] = useState(null);

  useEffect(() => {
    if (!id) return;
    async function fetchTool() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/tools/${encodeURIComponent(id)}`);
        if (res.status === 404) {
          setError("Tool not found");
        } else if (!res.ok) {
          setError(`Error ${res.status}`);
        } else {
          const data = await res.json();
          setTool(data);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchTool();
  }, [id]);

  // Build initial args from schema defaults
  useEffect(() => {
    if (!tool) return;
    const schema = tool.full_record?.input_schema || {};
    const properties = schema.properties || {};
    const defaults = {};
    for (const [key, spec] of Object.entries(properties)) {
      if (spec.default !== undefined) {
        defaults[key] = spec.default;
      }
    }
    if (Object.keys(defaults).length > 0) {
      setArgs(defaults);
    }
  }, [tool]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="text-zinc-400 py-12 text-center">Loading tool...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="text-red-400 py-12 text-center">{error}</div>
      </div>
    );
  }

  if (!tool) return null;

  const fullRecord = tool.full_record || {};
  const schema = fullRecord.input_schema || {};
  const properties = schema.properties || {};
  const required = schema.required || [];
  const isWrite = tool.side_effect_level === "write";
  const isDestructive = tool.side_effect_level === "destructive";

  async function handleExecute() {
    setExecuting(true);
    setResult(null);
    setExecError(null);
    setDurationMs(null);

    const start = Date.now();
    try {
      const res = await fetch(
        `${API_BASE}/tools/${encodeURIComponent(id)}/execute`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ arguments: args, confirmed }),
        }
      );
      const data = await res.json();
      setDurationMs(Date.now() - start);

      if (res.status === 202 || data.status === "confirmation_required") {
        setResult(data);
        setExecError(null);
      } else if (!res.ok || data.error) {
        setExecError(data.error || `HTTP ${res.status}`);
        setResult(null);
      } else {
        setResult(data);
        setExecError(null);
      }
    } catch (err) {
      setExecError(err.message);
      setDurationMs(Date.now() - start);
    } finally {
      setExecuting(false);
    }
  }

  function handleConfirm() {
    setConfirmed(true);
    handleExecute();
  }

  function addArg() {
    if (!argKey.trim()) return;
    setArgs((prev) => ({ ...prev, [argKey.trim()]: argValue }));
    setArgKey("");
    setArgValue("");
  }

  function removeArg(key) {
    setArgs((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  const needsConfirm = isWrite && !confirmed;

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="text-zinc-400 hover:text-zinc-200 text-sm mb-4 flex items-center gap-1"
        >
          &#8592; Back
        </button>
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
            {tool.namespace}
          </span>
          {tool.side_effect_level === "read" && (
            <span className="text-xs px-2 py-0.5 rounded bg-green-900/50 text-green-400">
              read
            </span>
          )}
          {tool.side_effect_level === "write" && (
            <span className="text-xs px-2 py-0.5 rounded bg-yellow-900/50 text-yellow-400">
              write
            </span>
          )}
          {tool.side_effect_level === "destructive" && (
            <span className="text-xs px-2 py-0.5 rounded bg-red-900/50 text-red-400">
              destructive
            </span>
          )}
        </div>
        <h1 className="text-2xl font-bold text-white mb-1">
          Execute: {tool.name}
        </h1>
        <p className="text-zinc-400 text-sm">{tool.description}</p>
      </div>

      {/* Arguments Form */}
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 mb-6">
        <h2 className="text-white font-semibold mb-4">Arguments</h2>

        {Object.keys(properties).length === 0 ? (
          <p className="text-zinc-500 text-sm">No arguments required.</p>
        ) : (
          <div className="space-y-3 mb-4">
            {Object.entries(properties).map(([key, spec]) => (
              <div key={key} className="flex flex-col gap-1">
                <label className="text-zinc-300 text-sm font-medium">
                  {key}
                  {required.includes(key) && (
                    <span className="text-red-400 ml-1">*</span>
                  )}
                  {spec.description && (
                    <span className="text-zinc-500 font-normal ml-2">
                      {spec.description}
                    </span>
                  )}
                </label>
                <input
                  type={spec.type === "integer" || spec.type === "number" ? "number" : "text"}
                  value={args[key] ?? ""}
                  onChange={(e) =>
                    setArgs((prev) => ({
                      ...prev,
                      [key]:
                        spec.type === "integer" || spec.type === "number"
                          ? parseInt(e.target.value, 10)
                          : e.target.value,
                    }))
                  }
                  placeholder={spec.example || spec.default || ""}
                  className="bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            ))}
          </div>
        )}

        {/* Manual key-value pairs for extra args */}
        <div className="border-t border-zinc-700 pt-4 mt-4">
          <p className="text-zinc-400 text-xs mb-2">
            Add extra arguments not in schema:
          </p>
          <div className="flex gap-2">
            <input
              value={argKey}
              onChange={(e) => setArgKey(e.target.value)}
              placeholder="key"
              className="bg-zinc-800 border border-zinc-600 rounded px-2 py-1.5 text-white text-sm w-32 focus:outline-none focus:border-blue-500"
              onKeyDown={(e) => e.key === "Enter" && addArg()}
            />
            <input
              value={argValue}
              onChange={(e) => setArgValue(e.target.value)}
              placeholder="value"
              className="bg-zinc-800 border border-zinc-600 rounded px-2 py-1.5 text-white text-sm flex-1 focus:outline-none focus:border-blue-500"
              onKeyDown={(e) => e.key === "Enter" && addArg()}
            />
            <button
              onClick={addArg}
              className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 text-white text-sm rounded"
            >
              Add
            </button>
          </div>
          {Object.keys(args).length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {Object.entries(args).map(([k, v]) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-zinc-800 border border-zinc-600 rounded text-zinc-300 text-xs"
                >
                  {k}: {String(v)}
                  <button
                    onClick={() => removeArg(k)}
                    className="text-zinc-500 hover:text-zinc-300 ml-1"
                  >
                    &#215;
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Warning banners */}
        {isWrite && !confirmed && (
          <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded">
            <p className="text-yellow-300 text-sm font-medium">
              This tool performs a write action.
            </p>
            <p className="text-yellow-200/70 text-xs mt-1">
              Clicking &quot;Execute&quot; will prompt for confirmation before running.
            </p>
          </div>
        )}

        {isDestructive && !confirmed && (
          <div className="mt-4 p-3 bg-red-900/20 border border-red-700/50 rounded">
            <p className="text-red-300 text-sm font-medium">
              This tool performs a destructive action.
            </p>
            <p className="text-red-200/70 text-xs mt-1">
              Confirm to proceed.
            </p>
          </div>
        )}

        {/* Execute button */}
        <div className="mt-6 flex gap-3">
          {needsConfirm ? (
            <>
              <button
                onClick={handleExecute}
                disabled={executing}
                className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded font-medium text-sm"
              >
                {executing ? "Waiting..." : "Confirm & Execute"}
              </button>
              <button
                onClick={() => router.back()}
                disabled={executing}
                className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded text-sm"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={handleExecute}
              disabled={executing}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium text-sm disabled:opacity-50"
            >
              {executing ? "Executing..." : "Execute"}
            </button>
          )}
          {executing && (
            <span className="text-zinc-400 text-sm py-2">Running...</span>
          )}
        </div>
      </div>

      {/* Result */}
      {result && !execError && (
        <div className="bg-zinc-900 border border-green-700/50 rounded-lg p-6 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-green-400 text-sm font-semibold">
              &#10003; Execution successful
            </span>
            {durationMs != null && (
              <span className="text-zinc-500 text-xs">
                {durationMs}ms
              </span>
            )}
          </div>
          <details className="cursor-pointer">
            <summary className="text-zinc-300 text-sm mb-2">
              View response
            </summary>
            <pre className="bg-zinc-950 border border-zinc-700 rounded p-4 text-xs text-zinc-300 overflow-auto max-h-96">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Confirmation required response */}
      {result && result.status === "confirmation_required" && !execError && (
        <div className="bg-zinc-900 border border-yellow-700/50 rounded-lg p-6 mb-6">
          <p className="text-yellow-300 text-sm font-semibold mb-2">
            Confirmation required
          </p>
          <p className="text-zinc-300 text-sm mb-4">
            {result.message}
          </p>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded font-medium text-sm"
          >
            I understand &#8212; execute anyway
          </button>
        </div>
      )}

      {/* Error */}
      {execError && (
        <div className="bg-zinc-900 border border-red-700/50 rounded-lg p-6 mb-6">
          <p className="text-red-400 text-sm font-semibold mb-2">
            &#10007; Execution failed
          </p>
          <p className="text-zinc-300 text-sm mb-4">{execError}</p>
          {result && (
            <details>
              <summary className="text-zinc-500 text-xs cursor-pointer mb-2">
                View full response
              </summary>
              <pre className="bg-zinc-950 border border-zinc-700 rounded p-4 text-xs text-zinc-300 overflow-auto max-h-48">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
