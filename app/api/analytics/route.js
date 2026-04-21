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

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const period = searchParams.get('period') || '7d';
    
    const database = getDb();
    
    let dateFilter;
    switch (period) {
      case '24h':
        dateFilter = "datetime('now', '-1 day')";
        break;
      case '30d':
        dateFilter = "datetime('now', '-30 days')";
        break;
      default:
        dateFilter = "datetime('now', '-7 days')";
    }

    // Get total page views
    const totalStmt = database.prepare(`
      SELECT COUNT(*) as count FROM page_views 
      WHERE timestamp >= ${dateFilter}
    `);
    const totalResult = totalStmt.get();

    // Get unique pages
    const pagesStmt = database.prepare(`
      SELECT path, COUNT(*) as views 
      FROM page_views 
      WHERE timestamp >= ${dateFilter}
      GROUP BY path 
      ORDER BY views DESC 
      LIMIT 10
    `);
    const topPages = pagesStmt.all();

    // Get views by day
    const dailyStmt = database.prepare(`
      SELECT DATE(timestamp) as date, COUNT(*) as views 
      FROM page_views 
      WHERE timestamp >= ${dateFilter}
      GROUP BY DATE(timestamp) 
      ORDER BY date ASC
    `);
    const dailyViews = dailyStmt.all();

    // Get referrer stats
    const referrerStmt = database.prepare(`
      SELECT referrer, COUNT(*) as count 
      FROM page_views 
      WHERE timestamp >= ${dateFilter} AND referrer IS NOT NULL
      GROUP BY referrer 
      ORDER BY count DESC 
      LIMIT 5
    `);
    const topReferrers = referrerStmt.all();

    return Response.json({
      total: totalResult.count,
      topPages,
      dailyViews,
      topReferrers,
      period
    });
  } catch (error) {
    console.error('Analytics error:', error);
    return Response.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export const runtime = 'nodejs';