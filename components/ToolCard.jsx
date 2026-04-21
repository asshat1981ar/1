export function ToolCard({ tool }) {
  const { name, namespace, description, side_effect_level, status } = tool;

  const sideEffectColors = {
    read: "bg-green-900 text-green-300",
    write: "bg-yellow-900 text-yellow-300",
    destructive: "bg-red-900 text-red-300",
  };

  const statusColors = {
    draft: "bg-gray-700 text-gray-300",
    verified: "bg-blue-900 text-blue-300",
    approved: "bg-green-900 text-green-300",
  };

  return (
    <div
      data-testid="tool-card"
      className="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-colors"
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="text-lg font-semibold text-white">{name}</h3>
          <span className="text-sm text-gray-500">{namespace}</span>
        </div>
        <div className="flex gap-2">
          <span className={`text-xs px-2 py-1 rounded ${sideEffectColors[side_effect_level] || "bg-gray-700"}`}>
            {side_effect_level}
          </span>
          <span className={`text-xs px-2 py-1 rounded ${statusColors[status] || "bg-gray-700"}`}>
            {status}
          </span>
        </div>
      </div>
      <p className="text-sm text-gray-400 mt-2">{description}</p>
    </div>
  );
}
