export function SchemaViewer({ title, schema }) {
  if (!schema) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-zinc-300 mb-2">{title}</h4>
      <pre className="text-xs text-zinc-400 overflow-x-auto">
        {JSON.stringify(schema, null, 2)}
      </pre>
    </div>
  );
}
