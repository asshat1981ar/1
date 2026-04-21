"use client";

import { useEffect, useState } from "react";
import { DriftTable } from "./components/DriftTable";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

export default function DriftPage() {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ total: 0, drifted: 0, new: 0 });

  useEffect(() => {
    async function fetchDrift() {
      try {
        const res = await fetch(`${API_BASE}/admin/drift`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        setTools(data.tools || []);
        setStats({
          total: data.total || 0,
          drifted: (data.tools || []).filter((t) => t.previous_hash).length,
          new: (data.tools || []).filter((t) => !t.previous_hash).length,
        });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchDrift();
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-white mb-2">
          Drift Detection
        </h1>
        <p className="text-zinc-500">
          Tools that have changed since their last harvest. Re-scrape to sync.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg p-4">
          <div className="text-2xl font-bold text-zinc-900 dark:text-white">
            {stats.total}
          </div>
          <div className="text-sm text-zinc-500">Total Tools</div>
        </div>
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg p-4">
          <div className="text-2xl font-bold text-amber-600">
            {stats.drifted}
          </div>
          <div className="text-sm text-zinc-500">Changed</div>
        </div>
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-600">
            {stats.new}
          </div>
          <div className="text-sm text-zinc-500">New</div>
        </div>
      </div>

      {/* Refresh */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">
          Tools with Uncommitted Changes
        </h2>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 text-sm bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 transition-colors"
        >
          Refresh
        </button>
      </div>

      {loading && (
        <div className="text-center py-16 text-zinc-500">Loading…</div>
      )}

      {error && (
        <div className="text-center py-16">
          <div className="text-red-500 mb-2">Failed to load drift data</div>
          <div className="text-sm text-zinc-500">{error}</div>
        </div>
      )}

      {!loading && !error && <DriftTable tools={tools} />}
    </div>
  );
}
