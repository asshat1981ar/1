"use client";
import { useState } from "react";

const SIDE_EFFECT_OPTIONS = [
  { value: "", label: "All" },
  { value: "read", label: "Read" },
  { value: "write", label: "Write" },
  { value: "destructive", label: "Destructive" },
];

const NAMESPACE_OPTIONS = [
  { value: "", label: "All namespaces" },
  { value: "github", label: "GitHub" },
  { value: "stripe", label: "Stripe" },
  { value: "anthropic", label: "Anthropic" },
  { value: "openai", label: "OpenAI" },
  { value: "sendgrid", label: "SendGrid" },
  { value: "twilio", label: "Twilio" },
  { value: "auth0", label: "Auth0" },
];

export function FilterSidebar({ onFilterChange }) {
  const [namespace, setNamespace] = useState("");
  const [sideEffect, setSideEffect] = useState("");

  function handleChange(newNamespace, newSideEffect) {
    setNamespace(newNamespace);
    setSideEffect(newSideEffect);
    onFilterChange({ namespace: newNamespace, sideEffect: newSideEffect });
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-zinc-300 mb-2">Namespace</label>
        <select
          data-testid="namespace-filter"
          value={namespace}
          onChange={(e) => handleChange(e.target.value, sideEffect)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-zinc-500"
        >
          {NAMESPACE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-zinc-300 mb-2">Side Effect</label>
        <div className="space-y-1">
          {SIDE_EFFECT_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer hover:text-white">
              <input
                type="radio"
                name="side_effect"
                value={opt.value}
                checked={sideEffect === opt.value}
                onChange={(e) => handleChange(namespace, e.target.value)}
                className="text-zinc-400 focus:ring-zinc-500"
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
