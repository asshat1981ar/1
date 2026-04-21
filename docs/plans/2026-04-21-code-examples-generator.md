# Code Examples Generator — Implementation Plan

## Goal
Add a "Code Examples" tab to the tool detail page that generates runnable code snippets from the tool's input_schema. Supports Python, JavaScript, curl, and Go.

## Architecture
- `mcp_server/code_generator.py` — Pure Python module that generates snippets from JSON schemas
- `app/tools/[id]/components/CodeExamples.jsx` — Tab component with language switcher
- Update `app/tools/[id]/page.jsx` — Add "Examples" tab alongside Schema tab

## TDD Tasks

### Task 1: Create `mcp_server/code_generator.py`
**Step 1: Write failing test**
```bash
cd /home/westonaaron675/gadk/1
cat > tests/test_code_generator.py << 'EOF'
from mcp_server.code_generator import generate_examples, _python_example, _js_example, _curl_example, _go_example

def test_python_example_basic():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Customer name"},
            "amount": {"type": "integer", "description": "Amount in cents"}
        },
        "required": ["name", "amount"]
    }
    result = _python_example("stripe.create_charge", schema)
    assert "stripe.create_charge" in result
    assert "name:" in result
    assert "amount:" in result

def test_curl_example():
    schema = {
        "type": "object",
        "properties": {"to": {"type": "string"}, "body": {"type": "string"}},
        "required": ["to", "body"]
    }
    result = _curl_example("POST", "https://api.sendgrid.com/v3/mail/send", schema)
    assert "curl" in result
    assert "-X POST" in result

def test_all_languages():
    schema = {"type": "object", "properties": {"id": {"type": "string"}}}
    examples = generate_examples("github.get_repo", schema)
    assert set(examples.keys()) == {"python", "javascript", "curl", "go"}
    assert all(examples.values())
EOF
echo "test written"
```

**Step 2: Run test** — expect FAIL (module not found)

**Step 3: Implement** — Create `mcp_server/code_generator.py` with:
- `_python_example(tool_name, schema)` — returns Python snippet with typed args
- `_js_example(tool_name, schema)` — returns JS/TypeScript fetch snippet
- `_curl_example(method, url, schema)` — returns curl command
- `_go_example(tool_name, schema)` — returns Go http.Request snippet
- `generate_examples(tool_name, schema)` — returns dict of all 4 languages

**Step 4: Run test** — expect PASS

**Step 5: Commit**

### Task 2: Create `app/tools/[id]/components/CodeExamples.jsx`
**Step 1:** Create component with language tabs (Python/JS/curl/Go), syntax-highlighted code blocks, copy button

**Step 2:** Verify page renders with `curl -s http://localhost:3000/tools/test-id | grep -i code`

**Step 3: Commit**

### Task 3: Update detail page with Examples tab
**Step 1:** Add tab state (Schema | Examples) to `app/tools/[id]/page.jsx`

**Step 2:** Show CodeExamples when Examples tab active

**Step 3:** Verify both tabs work

**Step 4: Commit**

## Verification
```bash
pytest tests/test_code_generator.py -v
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/tools/test-tool
```
