import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, '..', '..', '..', '..', 'toolbank', 'registry.db');

let db;

function getDb() {
  if (!db) {
    db = new Database(DB_PATH, { readonly: true });
    db.pragma('journal_mode = WAL');
  }
  return db;
}

export async function GET(request, { params }) {
  const { id } = params;
  const { searchParams } = new URL(request.url);
  const includeHistory = searchParams.get('history') === '1';
  const limit = parseInt(searchParams.get('limit') || '20', 10);

  if (!id) {
    return Response.json({ error: 'tool_id is required' }, { status: 400 });
  }

  try {
    const database = getDb();

    // Get tool record
    const toolStmt = database.prepare(`
      SELECT * FROM tool_records WHERE id = ?
    `);
    const row = toolStmt.get(decodeURIComponent(id));

    if (!row) {
      return Response.json({ error: 'Tool not found' }, { status: 404 });
    }

    // Parse full_record JSON
    let fullRecord = {};
    try {
      fullRecord = typeof row.full_record === 'string'
        ? JSON.parse(row.full_record)
        : (row.full_record || {});
    } catch {
      fullRecord = {};
    }

    const tool = {
      id: row.id,
      name: row.name,
      namespace: row.namespace,
      description: row.description,
      source_type: row.source_type,
      transport: row.transport,
      side_effect_level: row.side_effect_level,
      permission_policy: row.permission_policy,
      status: row.status,
      confidence: row.confidence,
      version_hash: row.version_hash,
      tags: typeof row.tags === 'string' ? JSON.parse(row.tags) : (row.tags || []),
      full_record: fullRecord,
    };

    // Optionally include execution history
    if (includeHistory) {
      const historyStmt = database.prepare(`
        SELECT id, tool_id, arguments, result, status, duration_ms, error_message, timestamp
        FROM tool_executions
        WHERE tool_id = ?
        ORDER BY id DESC
        LIMIT ?
      `);
      const history = historyStmt.all(decodeURIComponent(id), limit).map(r => ({
        ...r,
        arguments: typeof r.arguments === 'string' ? JSON.parse(r.arguments) : (r.arguments || {}),
        result: typeof r.result === 'string' ? JSON.parse(r.result) : (r.result || null),
        timestamp: r.timestamp,
      }));
      tool.executions = history;
    }

    return Response.json(tool);
  } catch (error) {
    console.error('GET /api/tools/[id] error:', error);
    return Response.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export const runtime = 'nodejs';
