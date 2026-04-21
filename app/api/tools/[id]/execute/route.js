/**
 * POST /api/tools/[id]/execute
 * Executes a tool by ID with the given arguments.
 * Proxies to the FastMCP execute server on port 8765.
 */

const EXECUTE_BASE = process.env.EXECUTE_SERVER_URL || 'http://localhost:8765';

export async function POST(request, { params }) {
  const { id } = params;

  try {
    const body = await request.json();
    const { arguments: args = {}, confirmed = false } = body;

    if (!id) {
      return Response.json({ error: 'tool_id is required' }, { status: 400 });
    }

    const executeUrl = `${EXECUTE_BASE}/tools/execute`;
    const response = await fetch(executeUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'execute_tool',
        arguments: {
          tool_id: decodeURIComponent(id),
          arguments: args,
          confirmed,
        },
      }),
      signal: AbortSignal.timeout(60000), // 60s max for tool execution
    });

    let result;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      result = await response.json();
    } else {
      const text = await response.text();
      try {
        result = JSON.parse(text);
      } catch {
        result = { raw: text, status_code: response.status };
      }
    }

    return Response.json(result, { status: response.status });
  } catch (error) {
    console.error('POST /api/tools/[id]/execute error:', error);
    return Response.json(
      { error: 'Execution failed', message: error.message },
      { status: 500 }
    );
  }
}

export const runtime = 'nodejs';
