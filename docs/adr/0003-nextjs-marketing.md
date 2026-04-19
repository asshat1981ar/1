# ADR 0003 — Next.js 14 App Router for Marketing Site

**Date:** 2025-01  
**Status:** Accepted

---

## Context

The No-Bull Marketing site needs to be fast, SEO-friendly, and easy to deploy. The site is primarily static content (hero, social proof, CTA) with minimal interactivity.

## Decision

Use **Next.js 14** with the **App Router** (`app/` directory), React 18, Tailwind CSS, and Framer Motion. Deploy to Vercel.

## Rationale

- Next.js App Router provides server components by default, improving performance and SEO
- Tailwind CSS removes the need for a separate CSS framework and scales well with a small component set
- Framer Motion handles all animation needs without a second animation library
- Vercel provides zero-config deployment for Next.js with edge CDN

## Consequences

- All new React components must use the App Router conventions (`"use client"` directive for interactive components)
- The Pages Router (`pages/` directory) must not be used — mixing the two causes routing conflicts
- The `public/media/` directory must contain the hero video and related assets before deployment
