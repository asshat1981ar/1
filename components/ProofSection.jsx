"use client";
import { motion } from "framer-motion";

const SOURCES = [
  {
    kind: "OpenAPI / REST",
    icon: "🔌",
    description:
      "Parses OpenAPI 2.x / 3.x specs. Extracts every endpoint as a callable tool with input/output schemas.",
    examples: ["Stripe", "GitHub", "Twilio"],
  },
  {
    kind: "GraphQL",
    icon: "◈",
    description:
      "Runs schema introspection and maps every Query, Mutation, and Subscription to a typed ToolbankRecord.",
    examples: ["Shopify", "GitHub v4", "SpaceX"],
  },
  {
    kind: "MCP Servers",
    icon: "⚡",
    description:
      "Scrapes public MCP server manifests from registries like smithery.ai and mcp.so.",
    examples: ["smithery.ai", "mcp.so", "Custom servers"],
  },
  {
    kind: "Docs Sites",
    icon: "📄",
    description:
      "Crawls developer documentation with robots.txt respect, classifying and extracting tool descriptions.",
    examples: ["ReadTheDocs", "Docusaurus", "GitBook"],
  },
];

const STATS = [
  { value: "4", label: "Adapter types" },
  { value: "∞", label: "Sources supported" },
  { value: "100%", label: "robots.txt compliant" },
  { value: "1", label: "Unified registry" },
];

export default function ProofSection() {
  return (
    <section id="sources" className="bg-gray-900 text-white py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: -20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-4xl font-bold text-center mb-4"
        >
          Supported Sources
        </motion.h2>
        <p className="text-center text-gray-400 mb-12 max-w-xl mx-auto">
          ToolBank harvests from any source that exposes structured or
          semi-structured tool definitions.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-16">
          {SOURCES.map((src, i) => (
            <motion.div
              key={src.kind}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="bg-gray-800 rounded-2xl p-6 flex flex-col gap-3 border border-white/5 hover:border-indigo-500/40 transition-colors"
            >
              <div className="text-3xl">{src.icon}</div>
              <h3 className="text-xl font-semibold">{src.kind}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{src.description}</p>
              <div className="flex gap-2 flex-wrap mt-auto">
                {src.examples.map((ex) => (
                  <span
                    key={ex}
                    className="text-xs bg-white/10 text-gray-300 px-2 py-1 rounded-full"
                  >
                    {ex}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
          {STATS.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              className="bg-gray-800 rounded-2xl py-8 border border-white/5"
            >
              <p className="text-4xl font-bold text-indigo-400">{stat.value}</p>
              <p className="text-sm text-gray-400 mt-2">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

