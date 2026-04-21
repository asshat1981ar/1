import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, '..', '..', '..', 'pageviews.db');

let db;

function getDb() {
  if (!db) {
    db = new Database(DB_PATH);
    db.exec(`
      CREATE TABLE IF NOT EXISTS page_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        referrer TEXT,
        user_agent TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }
  return db;
}

export async function POST(request) {
  try {
    const { path: pagePath, referrer, user_agent } = await request.json();

    if (!pagePath) {
      return Response.json({ error: 'path is required' }, { status: 400 });
    }

    const database = getDb();
    const stmt = database.prepare(`
      INSERT INTO page_views (path, referrer, user_agent)
      VALUES (?, ?, ?)
    `);
    stmt.run(pagePath, referrer || null, user_agent || null);

    return Response.json({ success: true });
  } catch (error) {
    console.error('Track error:', error);
    return Response.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export const runtime = 'nodejs';
