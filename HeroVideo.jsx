"use client";
import { useState } from "react";
import { motion } from "framer-motion";

export default function Hero() {
  const [query, setQuery] = useState("");

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    alert(`Searching the registry for: "${query}"`);
  };

  return (
    <section
      id="discover"
      className="relative w-full min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-gray-950 via-gray-900 to-gray-800 text-white text-center px-6"
    >
      <motion.h1
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="text-5xl font-bold mb-4 tracking-tight"
      >
        ⚙ ToolBank
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
        className="text-lg mb-10 max-w-xl text-gray-300"
      >
        Scrape, discover, and manage tools from any source — REST APIs, GraphQL
        endpoints, MCP servers, and documentation sites. One registry for
        everything.
      </motion.p>
      <motion.form
        onSubmit={handleSearch}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1, delay: 0.2 }}
        className="w-full max-w-xl flex gap-2"
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search tools by name or capability…"
          className="flex-1 p-4 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="submit"
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-4 rounded-xl font-semibold transition-colors"
        >
          Search
        </button>
      </motion.form>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.2, delay: 0.6 }}
        className="mt-12 flex gap-4 flex-wrap justify-center text-sm text-gray-400"
      >
        <a href="#scrape" className="underline hover:text-white transition-colors">
          Scrape a new source →
        </a>
        <span>·</span>
        <a href="#sources" className="underline hover:text-white transition-colors">
          Browse supported sources →
        </a>
      </motion.div>
    </section>
  );
}
