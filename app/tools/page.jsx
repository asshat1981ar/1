"use client";

import { useState, useMemo } from "react";
import { ToolCard } from "../../components/ToolCard";
import { SearchBar } from "../../components/SearchBar";
import { FilterSidebar } from "../../components/FilterSidebar";
import { MOCK_TOOLS } from "../../data/mockTools";

function filterTools(tools, { query, namespaces, sideEffects, statuses }) {
  return tools.filter((tool) => {
    const matchesQuery =
      !query ||
      tool.name.toLowerCase().includes(query.toLowerCase()) ||
      tool.namespace.toLowerCase().includes(query.toLowerCase()) ||
      tool.description.toLowerCase().includes(query.toLowerCase());

    const matchesNamespace = namespaces.length === 0 || namespaces.includes(tool.namespace);
    const matchesSideEffect = sideEffects.length === 0 || sideEffects.includes(tool.side_effect_level);
    const matchesStatus = statuses.length === 0 || statuses.includes(tool.status);

    return matchesQuery && matchesNamespace && matchesSideEffect && matchesStatus;
  });
}

export default function ToolsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({ namespaces: [], sideEffects: [], statuses: [] });

  const handleSearch = (query) => {
    setSearchQuery(query);
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  const filteredTools = useMemo(() => {
    return filterTools(MOCK_TOOLS, { query: searchQuery, ...filters });
  }, [searchQuery, filters]);

  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-white mb-8">Browse Tools</h1>

        <div className="mb-6">
          <SearchBar onSearch={handleSearch} initialValue={searchQuery} />
        </div>

        <div className="flex flex-col md:flex-row gap-6">
          <div className="w-full md:w-64 flex-shrink-0">
            <FilterSidebar onFilterChange={handleFilterChange} />
          </div>

          <div className="flex-1">
            {filteredTools.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTools.map((tool) => (
                  <ToolCard key={tool.id} tool={tool} />
                ))}
              </div>
            ) : (
              <div data-testid="no-results-message" className="text-center py-12">
                <p className="text-gray-400 text-lg">No tools found matching your criteria.</p>
                <p className="text-gray-600 text-sm mt-2">Try adjusting your search or filters.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
