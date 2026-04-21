"use client";
import { useState, useEffect, useCallback } from "react";
import { ToolCard } from "./components/ToolCard";
import { SearchBar } from "./components/SearchBar";
import { FilterSidebar } from "./components/FilterSidebar";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const PAGE_SIZE = 20;

export default function ToolsPage() {
  const [tools, setTools] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ namespace: "", sideEffect: "" });
  const [error, setError] = useState(null);

  const fetchTools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: PAGE_SIZE, offset });
      if (filters.namespace) params.set("namespace", filters.namespace);
      if (filters.sideEffect) params.set("side_effect", filters.sideEffect);
      const res = await fetch(`${API_BASE}/tools?${params}`, {
        signal: AbortSignal.timeout(5000),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      let filtered = data.tools || [];
      if (search) {
        const q = search.toLowerCase();
        filtered = filtered.filter(
          (t) =>
            t.name?.toLowerCase().includes(q) ||
            t.description?.toLowerCase().includes(q)
        );
      }
      setTools(filtered);
      setTotal(data.total);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message);
        setTools([]);
        setTotal(0);
      }
    } finally {
      setLoading(false);
    }
  }, [offset, filters, search]);

  useEffect(() => { fetchTools(); }, [fetchTools]);

  function handleSearch(q) { setSearch(q); setOffset(0); }
  function handleFilterChange(f) { setFilters(f); setOffset(0); }

  return (
    <div className="max-w-6xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold text-white mb-8">Browse Tools</h1>
      <div className="flex flex-col md:flex-row gap-8">
        <aside className="w-full md:w-64 shrink-0">
          <FilterSidebar onFilterChange={handleFilterChange} />
        </aside>
        <div className="flex-1">
          <div className="mb-6">
            <SearchBar onSearch={handleSearch} />
          </div>
          {loading ? (
            <p className="text-zinc-400 py-8 text-center">Loading tools...</p>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-red-400 mb-2">Failed to load tools: {error}</p>
              <p className="text-zinc-500 text-sm">Is the API server running on port 8765?</p>
            </div>
          ) : tools.length === 0 ? (
            <p className="text-zinc-400 py-8 text-center">No tools found. Try adjusting your filters.</p>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {tools.map((tool) => (
                  <ToolCard key={tool.id} tool={tool} />
                ))}
              </div>
              <div className="flex items-center justify-between border-t border-zinc-800 pt-4">
                <span className="text-sm text-zinc-400">{total} tools total</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    disabled={offset === 0}
                    className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-white text-sm disabled:opacity-40 hover:bg-zinc-700 transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setOffset(offset + PAGE_SIZE)}
                    disabled={offset + PAGE_SIZE >= total}
                    className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-white text-sm disabled:opacity-40 hover:bg-zinc-700 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
