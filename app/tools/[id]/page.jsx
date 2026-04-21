"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { SchemaViewer } from "./components/SchemaViewer";
import { CodeExamples } from "./components/CodeExamples";
import { ExecutionsPanel } from "./components/ExecutionsPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

export default function ToolDetailPage() {
  const { id } = useParams();
  const [tool, setTool] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("schema");

  useEffect(() => {
    if (!id) return;
    async function fetchTool() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/tools/${encodeURIComponent(id)}`, {
          signal: AbortSignal.timeout(5000),
        });
        if (res.status === 404) {
          setError("Tool not found");
        } else if (!res.ok) {
          setError(`Error ${res.status}`);
        } else {
          const data = await res.json();
          setTool(data);
        }
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    }
    fetchTool();
  }, [id]);

  if (loading) return <div className="text-zinc-400 py-12 text-center">Loading...</div>;
  if (error) return <div className="text-red-400 py-12 text-center">{error}</div>;
  if (!tool) return null;

  const fullRecord = tool.full_record || {};

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-4">
        <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 mb-2 inline-block">
          {tool.namespace}
        </span>
        <h1 data-testid="tool-name" className="text-3xl font-bold text-white mb-2">
          {tool.name}
        </h1>
        <div className="flex items-center gap-2 flex-wrap mb-4">
          {tool.side_effect_level === "read" && (
            <span className="text-xs px-2 py-0.5 rounded bg-green-900/50 text-green-400">read</span>
          )}
          {tool.side_effect_level === "write" && (
            <span className="text-xs px-2 py-0.5 rounded bg-yellow-900/50 text-yellow-400">write</span>
          )}
          {tool.side_effect_level === "destructive" && (
            <span className="text-xs px-2 py-0.5 rounded bg-red-900/50 text-red-400">destructive</span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded ${tool.status === "approved" ? "bg-blue-900/50 text-blue-400" : "bg-zinc-800 text-zinc-500"}`}>
            {tool.status}
          </span>
          <span className="text-xs text-zinc-500">
            confidence: {tool.confidence != null ? Math.round(tool.confidence * 100) + "%" : "n/a"}
          </span>
        </div>
        <p className="text-zinc-300 text-lg">{tool.description}</p>
        {tool.status === "approved" || tool.status === "verified" ? (
          <a
            href={`/tools/${encodeURIComponent(tool.id)}/execute`}
            className="inline-block mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium text-sm"
          >
            Execute
          </a>
        ) : (
          <span className="inline-block mt-3 text-xs text-zinc-500">
            Only approved tools can be executed
          </span>
        )}
      </div>

      {tool.tags?.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">Tags</h3>
          <div className="flex gap-2 flex-wrap">
            {(tool.tags || []).map((tag) => (
              <span key={tag} className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mb-6">
        <div className="flex gap-1 border-b border-zinc-700">
          <button
            onClick={() => setActiveTab("schema")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "schema"
                ? "text-white border-b-2 border-blue-500"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Schema
          </button>
          <button
            onClick={() => setActiveTab("examples")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "examples"
                ? "text-white border-b-2 border-blue-500"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Examples
          </button>
          <button
            onClick={() => setActiveTab("executions")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "executions"
                ? "text-white border-b-2 border-blue-500"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Executions
          </button>
        </div>
        <div className="mt-4">
          {activeTab === "schema" && (
            <div className="grid gap-6">
              {fullRecord.input_schema && (
                <SchemaViewer title="Input Schema" schema={fullRecord.input_schema} />
              )}
              {fullRecord.output_schema && (
                <SchemaViewer title="Output Schema" schema={fullRecord.output_schema} />
              )}
            </div>
          )}
          {activeTab === "examples" && (
            <CodeExamples toolName={`${tool.namespace}.${tool.name}`} schema={fullRecord.input_schema} />
          )}
          {activeTab === "executions" && (
            <ExecutionsPanel toolId={tool.id} />
          )}
        </div>
      </div>

      {fullRecord.auth && (
        <div className="mt-6 bg-zinc-900 border border-zinc-700 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-zinc-300 mb-2">Authentication</h4>
          <p className="text-sm text-zinc-400">{JSON.stringify(fullRecord.auth)}</p>
        </div>
      )}

      {fullRecord.source_urls?.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">Source URLs</h3>
          <ul className="space-y-1">
            {(fullRecord.source_urls || []).map((url, i) => (
              <li key={i}>
                <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 text-sm break-all">
                  {url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
