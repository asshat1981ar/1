/**
 * GET /api/tools
 * Returns a paginated list of tools from the registry.
 * Proxies to FastMCP /tools/list and normalises the response format.
 */
import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, '..', '..', '..', 'toolbank', 'registry.db');

let db;

function getDb() {
  if (!db) {
    db = new Database(DB_PATH, { readonly: true });
    db.pragma('journal_mode = WAL');
  }
  return db;
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get('limit') || '50', 10), 200);
  const offset = parseInt(searchParams.get('offset') || '0', 10);
  const status = searchParams.get('status') || 'approved';
  const namespace = searchParams.get('namespace') || '';
  const sideEffect = searchParams.get('side_effect') || '';

  try {
    const database = getDb();

    let where = 'WHERE status IN (?, ?)';
    let params = [status === 'all' ? 'approved' : status, 'verified'];

    if (namespace) {
      where += ' AND namespace = ?';
      params.push(namespace);
    }
    if (sideEffect) {
      where += ' AND side_effect_level = ?';
      params.push(sideEffect);
    }

    const countRow = database
      .prepare(`SELECT COUNT(*) as total FROM tools ${where}`)
      .get(...params);
    const total = countRow.total;

    const rows = database
      .prepare(`SELECT * FROM tools ${where} ORDER BY namespace, name LIMIT ? OFFSET ?`)
      .all(...params, limit, offset);

    const tools = rows.map((row) => ({
      id: row.id,
      name: row.name,
      namespace: row.namespace,
      description: row.description,
      transport: row.transport,
      side_effect_level: row.side_effect_level,
      status: row.status,
      confidence: row.confidence,
      tags: typeof row.tags === 'string' ? JSON.parse(row.tags) : (row.tags || []),
    }));

    return Response.json({ tools, total });
  } catch (error) {
    console.error('GET /api/tools error:', error);
    return Response.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export const runtime = 'nodejs';
