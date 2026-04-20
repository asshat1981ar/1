"use client";
import { useState } from "react";
import { motion } from "framer-motion";

const SOURCE_TYPES = [
  { value: "openapi", label: "OpenAPI / REST" },
  { value: "graphql", label: "GraphQL" },
  { value: "mcp", label: "MCP Server" },
  { value: "docs", label: "Documentation Site" },
  { value: "auto", label: "Auto-detect" },
];

export default function ScrapeSection() {
  const [formData, setFormData] = useState({ url: "", sourceType: "auto", honeypot: "" });
  const [status, setStatus] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.honeypot) return;
    setStatus("loading");
    setTimeout(() => {
      setStatus("success");
    }, 1200);
  };

  return (
    <section id="scrape" className="bg-indigo-700 text-white py-20 px-6">
      <div className="max-w-2xl mx-auto text-center">
        <motion.h2
          initial={{ opacity: 0, y: -20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-4xl font-bold mb-4"
        >
          Scrape a New Source
        </motion.h2>
        <p className="mb-8 text-lg text-indigo-200">
          Point ToolBank at any URL and we'll extract every tool, endpoint, and
          capability into your registry.
        </p>

        {status === "success" ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white/10 rounded-xl p-8 text-center"
          >
            <p className="text-2xl font-semibold mb-2">Harvest queued!</p>
            <p className="text-indigo-200">
              Results will appear in your registry once processing completes.
            </p>
            <button
              onClick={() => setStatus(null)}
              className="mt-6 underline text-sm text-indigo-200 hover:text-white"
            >
              Scrape another source
            </button>
          </motion.div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 text-left">
            <label className="flex flex-col gap-1 text-sm font-medium">
              Source URL
              <input
                type="url"
                name="url"
                placeholder="https://api.example.com/openapi.json"
                value={formData.url}
                onChange={handleChange}
                className="p-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-indigo-300 focus:outline-none focus:ring-2 focus:ring-white"
                required
              />
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium">
              Source Type
              <select
                name="sourceType"
                value={formData.sourceType}
                onChange={handleChange}
                className="p-3 rounded-xl bg-indigo-800 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-white"
              >
                {SOURCE_TYPES.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <input
              type="text"
              name="honeypot"
              value={formData.honeypot}
              onChange={handleChange}
              className="hidden"
              aria-hidden="true"
            />

            <button
              type="submit"
              disabled={status === "loading"}
              className="bg-white text-indigo-700 hover:bg-indigo-50 font-bold py-3 px-6 rounded-xl mt-2 transition-colors disabled:opacity-60"
            >
              {status === "loading" ? "Harvesting…" : "Start Harvest →"}
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
