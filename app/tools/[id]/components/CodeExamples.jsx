import { useState } from "react";

const LANGUAGES = [
  { id: "python", label: "Python" },
  { id: "javascript", label: "JavaScript" },
  { id: "curl", label: "curl" },
  { id: "go", label: "Go" },
];

function generatePython(name, schema) {
  const props = schema.properties || {};
  const required = schema.required || [];
  const args = Object.keys(props).map((k) => {
    const t = props[k].type || "string";
    const def = required.includes(k) ? "" : "=None";
    return `${k}: ${t}${def}`;
  });
  return `from your_tool_library import call_tool

result = call_tool(
    "${name}",
    {
${Object.keys(props).map((k) => `        "${k}": ${props[k].type === "integer" || props[k].type === "number" ? "0" : `"${k}"`}`).join(",\n")}
    }
)
print(result)`;
}

function generateJS(name, schema) {
  const props = schema.properties || {};
  const args = Object.keys(props).map((k) => `  ${k}: "${props[k].type === "integer" || props[k].type === "number" ? "0" : k}"`).join(",\n");
  return `const response = await fetch("/api/tools/${name}/execute", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    arguments: {
${args}
    },
    confirmed: false,
  }),
});
const data = await response.json();
console.log(data);`;
}

function generateCurl(name, schema) {
  const props = schema.properties || {};
  const argsObj = Object.fromEntries(
    Object.keys(props).map((k) => [k, props[k].type === "integer" || props[k].type === "number" ? 0 : k])
  );
  const body = JSON.stringify({ arguments: argsObj, confirmed: false });
  return `curl -X POST /api/tools/${encodeURIComponent(name)}/execute \\
  -H "Content-Type: application/json" \\
  -d '${body}'`;
}

function generateGo(name, schema) {
  const props = schema.properties || {};
  const fields = Object.keys(props).map((k) => {
    const t = props[k].type === "integer" || props[k].type === "number" ? "int" : "string";
    return `${k.charAt(0).toUpperCase() + k.slice(1)} ${t}`;
  }).join(",\n    ");
  return `package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

type Request struct {
${Object.keys(props).map((k) => `    ${k.charAt(0).toUpperCase() + k.slice(1)} ${props[k].type === "integer" || props[k].type === "number" ? "int" : "string"}`).join("\n")}
}

func main() {
    req := Request{
${Object.keys(props).map((k) => `        ${k.charAt(0).toUpperCase() + k.slice(1)}: ${props[k].type === "integer" || props[k].type === "number" ? "0" : `""`}`).join(",\n")}
    }
    body, _ := json.Marshal(req)
    resp, err := http.Post("/api/tools/${name}/execute", "application/json", bytes.NewBuffer(body))
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()
    fmt.Println(resp.Status)
}`;
}

function getExample(lang, name, schema) {
  switch (lang) {
    case "python": return generatePython(name, schema);
    case "javascript": return generateJS(name, schema);
    case "curl": return generateCurl(name, schema);
    case "go": return generateGo(name, schema);
    default: return "";
  }
}

export function CodeExamples({ toolName, schema }) {
  const [active, setActive] = useState("python");
  const [copied, setCopied] = useState(false);

  if (!schema) return null;

  const example = getExample(active, toolName, schema);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(example);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.id}
              onClick={() => setActive(lang.id)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                active === lang.id
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>
        <button
          onClick={handleCopy}
          className="text-xs px-2 py-1 rounded bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="text-xs text-green-400 overflow-x-auto bg-zinc-950 rounded p-3">
        <code>{example}</code>
      </pre>
    </div>
  );
}