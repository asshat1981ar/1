"use client";

export function DriftTable({ tools }) {
  if (!tools || tools.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-4">✅</div>
        <h3 className="text-xl font-semibold text-zinc-900 dark:text-white mb-2">No Drift Detected</h3>
        <p className="text-zinc-500">All tools are in sync with their last harvested state.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs uppercase bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
          <tr>
            <th className="px-4 py-3">Tool</th>
            <th className="px-4 py-3">Namespace</th>
            <th className="px-4 py-3">Last Harvested</th>
            <th className="px-4 py-3">Current Version</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => (
            <tr
              key={tool.id}
              className="border-b border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
            >
              <td className="px-4 py-3 font-medium text-zinc-900 dark:text-white">
                <a href={`/tools/${tool.id}`} className="hover:underline">
                  {tool.name}
                </a>
              </td>
              <td className="px-4 py-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                  {tool.namespace}
                </span>
              </td>
              <td className="px-4 py-3 text-zinc-500">
                {tool.last_harvested_at
                  ? new Date(tool.last_harvested_at).toLocaleString()
                  : "Never"}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-zinc-600 dark:text-zinc-400">
                {tool.version_hash ? tool.version_hash.slice(0, 8) : "—"}
              </td>
              <td className="px-4 py-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                  {tool.previous_hash ? "Changed" : "New"}
                </span>
              </td>
              <td className="px-4 py-3">
                <a
                  href={`/tools/${tool.id}`}
                  className="text-blue-600 hover:underline dark:text-blue-400"
                >
                  View →
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
