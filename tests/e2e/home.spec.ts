import { test, expect } from "@playwright/test";

test("home page loads", async ({ page }) => {
  const res = await page.goto("/", { waitUntil: "domcontentloaded" });
  expect(res?.status()).toBe(200);
});

test("tools page loads", async ({ page }) => {
  const res = await page.goto("/tools", { waitUntil: "domcontentloaded" });
  expect(res?.status()).toBe(200);
});

test("drift page loads", async ({ page }) => {
  const res = await page.goto("/admin/drift", { waitUntil: "domcontentloaded" });
  expect(res?.status()).toBe(200);
});

test("analytics page loads", async ({ page }) => {
  const res = await page.goto("/analytics", { waitUntil: "domcontentloaded" });
  expect(res?.status()).toBe(200);
});
