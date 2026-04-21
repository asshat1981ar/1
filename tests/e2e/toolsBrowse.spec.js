import { test, expect } from "@playwright/test";

test.describe("Tools Browse and Search Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/tools");
  });

  test("should display the tools browse page with heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /browse tools/i })).toBeVisible();
  });

  test("should display search bar", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search tools/i);
    await expect(searchInput).toBeVisible();
  });

  test("should display filter sidebar", async ({ page }) => {
    const filterSidebar = page.getByTestId("filter-sidebar");
    await expect(filterSidebar).toBeVisible();
  });

  test("should display tool cards", async ({ page }) => {
    const toolCards = page.getByTestId("tool-card");
    await expect(toolCards.first()).toBeVisible();
  });

  test("should filter tools when searching", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search tools/i);
    await searchInput.fill("stripe");
    await page.waitForTimeout(500);
    const toolCards = page.getByTestId("tool-card");
    const count = await toolCards.count();
    expect(count).toBeGreaterThan(0);
  });

  test("should show no results message when search has no matches", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search tools/i);
    await searchInput.fill("xyznonexistenttool12345");
    await page.waitForTimeout(500);
    const noResults = page.getByTestId("no-results-message");
    await expect(noResults).toBeVisible();
  });

  test("should filter by namespace", async ({ page }) => {
    const filterSidebar = page.getByTestId("filter-sidebar");
    const namespaceCheckbox = filterSidebar.locator("label", { hasText: "stripe" }).locator("input");
    await namespaceCheckbox.check();
    await page.waitForTimeout(500);
    const toolCards = page.getByTestId("tool-card");
    const count = await toolCards.count();
    expect(count).toBeGreaterThan(0);
  });
});
