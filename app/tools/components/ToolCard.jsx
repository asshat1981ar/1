export function ToolCard({ tool }) {
  return (
    <div data-testid="tool-card" className="border border-zinc-700 rounded-lg p-4 hover:border-zinc-500 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="font-semibold text-white">{tool.name}</h3>
        <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">{tool.namespace}</span>
      </div>
      <p className="text-sm text-zinc-400 line-clamp-2 mb-3">{tool.description}</p>
      <div className="flex items-center gap-2 flex-wrap">
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
      </div>
    </div>
  );
}
