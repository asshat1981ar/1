import { useState, useCallback } from "react";

export function SearchBar({ onSearch, initialValue = "" }) {
  const [query, setQuery] = useState(initialValue);

  const handleChange = useCallback(
    (e) => {
      const value = e.target.value;
      setQuery(value);
      onSearch(value);
    },
    [onSearch]
  );

  return (
    <div className="relative w-full">
      <input
        type="text"
        placeholder="Search tools..."
        value={query}
        onChange={handleChange}
        className="w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 pl-10 text-white placeholder-gray-500 focus:outline-none focus:border-gray-700 transition-colors"
      />
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
    </div>
  );
}
