import { test, expect } from "@playwright/test";

test.describe("Tools Browse Page", () => {
  test("loads successfully", async ({ page }) => {
    const response = await page.goto("/tools");
    expect(response?.status()).toBe(200);
  });

  test("shows search input", async ({ page }) => {
    await page.goto("/tools");
    const searchInput = page.getByTestId("search-input");
    await expect(searchInput).toBeVisible();
  });

  test("search button is visible", async ({ page }) => {
    await page.goto("/tools");
    const searchBtn = page.getByTestId("search-button");
    await expect(searchBtn).toBeVisible();
  });

  test("filter sidebar is visible", async ({ page }) => {
    await page.goto("/tools");
    const sidebar = page.locator("text=Namespace").first();
    await expect(sidebar).toBeVisible();
  });

  test("theme toggle works", async ({ page }) => {
    await page.goto("/tools");
    const toggle = page.getByTestId("theme-toggle");
    const html = page.locator("html");
    const initial = (await html.getAttribute("class")) ?? "";
    await toggle.click();
    const after = (await html.getAttribute("class")) ?? "";
    expect(after).not.toBe(initial);
  });
});

test.describe("Drift Page", () => {
  test("loads successfully", async ({ page }) => {
    const response = await page.goto("/admin/drift");
    expect(response?.status()).toBe(200);
  });

  test("shows drift stats", async ({ page }) => {
    await page.goto("/admin/drift");
    await expect(page.getByText("Total Tools")).toBeVisible();
    await expect(page.getByText("Changed")).toBeVisible();
    await expect(page.getByText("New")).toBeVisible();
  });

  test("shows drift table or empty state", async ({ page }) => {
    await page.goto("/admin/drift");
    // Either table or "No Drift Detected" message
    const hasTable = await page.locator("table").count();
    const hasEmpty = await page.getByText("No Drift Detected").count();
    expect(hasTable > 0 || hasEmpty > 0).toBe(true);
  });
});

test.describe("Analytics Page", () => {
  test("loads successfully", async ({ page }) => {
    const response = await page.goto("/analytics");
    expect(response?.status()).toBe(200);
  });

  test("shows analytics stats", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.getByText("Total Page Views")).toBeVisible();
  });
});
