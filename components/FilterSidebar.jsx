import { useState } from "react";

const NAMESPACES = ["stripe", "sendgrid", "openai", "anthropic", "github", "twilio", "auth0"];
const SIDE_EFFECT_LEVELS = ["read", "write", "destructive"];
const STATUSES = ["draft", "verified", "approved"];

export function FilterSidebar({ onFilterChange }) {
  const [selectedNamespaces, setSelectedNamespaces] = useState([]);
  const [selectedSideEffects, setSelectedSideEffects] = useState([]);
  const [selectedStatuses, setSelectedStatuses] = useState([]);

  const handleNamespaceChange = (namespace) => {
    const newSelected = selectedNamespaces.includes(namespace)
      ? selectedNamespaces.filter((n) => n !== namespace)
      : [...selectedNamespaces, namespace];
    setSelectedNamespaces(newSelected);
    onFilterChange({ namespaces: newSelected, sideEffects: selectedSideEffects, statuses: selectedStatuses });
  };

  const handleSideEffectChange = (level) => {
    const newSelected = selectedSideEffects.includes(level)
      ? selectedSideEffects.filter((s) => s !== level)
      : [...selectedSideEffects, level];
    setSelectedSideEffects(newSelected);
    onFilterChange({ namespaces: selectedNamespaces, sideEffects: newSelected, statuses: selectedStatuses });
  };

  const handleStatusChange = (status) => {
    const newSelected = selectedStatuses.includes(status)
      ? selectedStatuses.filter((s) => s !== status)
      : [...selectedStatuses, status];
    setSelectedStatuses(newSelected);
    onFilterChange({ namespaces: selectedNamespaces, sideEffects: selectedSideEffects, statuses: newSelected });
  };

  return (
    <aside data-testid="filter-sidebar" className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <h2 className="text-lg font-semibold text-white mb-4">Filters</h2>

      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Namespace</h3>
        <div className="space-y-2">
          {NAMESPACES.map((ns) => (
            <label key={ns} className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-white">
              <input
                type="checkbox"
                checked={selectedNamespaces.includes(ns)}
                onChange={() => handleNamespaceChange(ns)}
                className="rounded border-gray-700 bg-gray-800 text-blue-500 focus:ring-blue-500"
              />
              {ns}
            </label>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-300 mb-2">Side Effect Level</h3>
        <div className="space-y-2">
          {SIDE_EFFECT_LEVELS.map((level) => (
            <label key={level} className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-white">
              <input
                type="checkbox"
                checked={selectedSideEffects.includes(level)}
                onChange={() => handleSideEffectChange(level)}
                className="rounded border-gray-700 bg-gray-800 text-blue-500 focus:ring-blue-500"
              />
              {level}
            </label>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-2">Status</h3>
        <div className="space-y-2">
          {STATUSES.map((status) => (
            <label key={status} className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-white">
              <input
                type="checkbox"
                checked={selectedStatuses.includes(status)}
                onChange={() => handleStatusChange(status)}
                className="rounded border-gray-700 bg-gray-800 text-blue-500 focus:ring-blue-500"
              />
              {status}
            </label>
          ))}
        </div>
      </div>
    </aside>
  );
}
