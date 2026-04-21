"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { CASE_STUDIES, LOGOS, METRICS } from "../lib/proof-data";

function MetricCard({ value, label }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center gap-1"
    >
      <span className="text-4xl font-extrabold text-white">{value}</span>
      <span className="text-sm text-white/60 text-center">{label}</span>
    </motion.div>
  );
}

export default function ProofSection() {
  return (
    <section className="bg-black text-white py-24 px-6">
      <div className="max-w-5xl mx-auto flex flex-col gap-20">
        {/* Heading */}
        <h2 className="text-4xl md:text-5xl font-extrabold text-center">
          Results, not promises.
        </h2>

        {/* Metrics row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          {METRICS.map((m) => (
            <MetricCard key={m.label} value={m.value} label={m.label} />
          ))}
        </div>

        {/* Case studies */}
        <div className="flex flex-col gap-6">
          {CASE_STUDIES.map((cs, i) => (
            <motion.div
              key={cs.client}
              initial={{ opacity: 0, x: i % 2 === 0 ? -30 : 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="bg-zinc-900 rounded-2xl p-8 flex flex-col gap-3"
            >
              <span className="text-sm font-semibold text-white/50 uppercase tracking-widest">
                {cs.client}
              </span>
              <p className="text-2xl font-bold text-white">{cs.result}</p>
              <p className="text-white/70 leading-relaxed">{cs.description}</p>
            </motion.div>
          ))}
        </div>

        {/* Logo strip */}
        <div className="flex flex-wrap justify-center gap-4">
          {LOGOS.map((logo) => (
            <span
              key={logo.name}
              className="px-4 py-2 rounded-full border border-white/20 text-white/60 text-sm font-medium"
            >
              {logo.name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
