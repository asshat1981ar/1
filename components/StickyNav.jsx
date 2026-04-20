"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

export default function StickyNav({ sections = [] }) {
  const [activeId, setActiveId] = useState(sections[0]?.id ?? "");
  const observerRef = useRef(null);

  useEffect(() => {
    const handleIntersect = (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          setActiveId(entry.target.id);
        }
      }
    };

    observerRef.current = new IntersectionObserver(handleIntersect, {
      threshold: 0.4,
    });

    sections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observerRef.current.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, [sections]);

  return (
    <nav className="fixed left-4 top-1/2 -translate-y-1/2 flex flex-col gap-3 z-50">
      {sections.map(({ id, label }) => {
        const isActive = activeId === id;
        return (
          <a
            key={id}
            href={`#${id}`}
            className="flex items-center gap-2 group"
            aria-label={label}
          >
            <span className="relative flex items-center justify-center w-3 h-3">
              {isActive && (
                <motion.span
                  layoutId="indicator"
                  className="absolute inset-0 rounded-full bg-white"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <span
                className={`w-2 h-2 rounded-full border border-white transition-opacity ${
                  isActive ? "opacity-100" : "opacity-40"
                }`}
              />
            </span>
            <span
              className={`text-xs font-medium transition-opacity ${
                isActive ? "text-white opacity-100" : "text-white opacity-40"
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
