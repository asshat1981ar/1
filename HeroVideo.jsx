"use client";
import { motion } from "framer-motion";

export default function HeroVideo() {
  return (
    <div className="relative w-full h-screen overflow-hidden">
      <video
        autoPlay
        loop
        muted
        playsInline
        poster="/media/hero-blur.jpg"
        className="absolute w-full h-full object-cover"
      >
        <source src="/media/hero.mp4" type="video/mp4" />
        Your browser does not support the video tag.
      </video>
      <div className="absolute inset-0 bg-black/50 flex flex-col items-center justify-center text-white text-center px-6">
        <motion.h1
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          className="text-5xl font-bold mb-4"
        >
          No Bull. Just Results.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.2 }}
          className="text-lg mb-6 max-w-xl"
        >
          We don’t do buzzwords. We build brands that convert.
        </motion.p>
        <motion.a
          href="#cta"
          whileHover={{ scale: 1.05 }}
          className="bg-red-600 hover:bg-red-700 text-white py-3 px-6 rounded-full font-bold"
        >
          Book a Call →
        </motion.a>
      </div>
    </div>
  );
}