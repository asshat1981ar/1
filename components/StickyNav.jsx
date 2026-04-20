"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const SECTIONS = [
  { id: "discover", label: "Discover" },
  { id: "sources", label: "Sources" },
  { id: "scrape", label: "Scrape" },
];

export default function StickyNav() {
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    const observers = SECTIONS.map(({ id }) => {
      const el = document.getElementById(id);
      if (!el) return null;
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) setActiveId(id);
        },
        { rootMargin: "-40% 0px -40% 0px", threshold: 0 }
      );
      observer.observe(el);
      return observer;
    });

    return () => {
      observers.forEach((obs) => obs && obs.disconnect());
    };
  }, []);

  return (
    <nav className="fixed left-4 top-1/2 -translate-y-1/2 flex flex-col gap-3 z-50 hidden lg:flex">
      {SECTIONS.map(({ id, label }) => {
        const isActive = activeId === id;
        return (
          <a
            key={id}
            href={`#${id}`}
            className="flex items-center gap-2 group"
            aria-label={label}
          >
            <motion.span
              animate={{ width: isActive ? 24 : 8, opacity: isActive ? 1 : 0.4 }}
              transition={{ duration: 0.25 }}
              className="h-0.5 bg-white rounded-full block"
            />
            <span
              className={`text-xs font-medium transition-colors ${
                isActive ? "text-white" : "text-white/40 group-hover:text-white/70"
              }`}
            >
              {label}
            </span>
          </a>
        );
      })}
    </nav>
  );
}

