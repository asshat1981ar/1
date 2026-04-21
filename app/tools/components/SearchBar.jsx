"use client";
import { useState } from "react";

export function SearchBar({ onSearch }) {
  const [query, setQuery] = useState("");
  return (
    <div className="flex gap-2">
      <input
        data-testid="search-input"
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSearch(query)}
        placeholder="Search tools by name or description..."
        className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
      />
      <button
        data-testid="search-button"
        onClick={() => onSearch(query)}
        className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white hover:bg-zinc-700 transition-colors"
      >
        Search
      </button>
    </div>
  );
}
