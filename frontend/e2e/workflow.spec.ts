import { test, expect } from "@playwright/test";
test("import, inspect, record cancellation and review a later debit", async ({
  page,
  request,
}) => {
  await request.delete("/api/workspace");
  await page.goto("/");
  await page.getByRole("button", { name: "Load fictional demo" }).click();
  await expect(
    page.getByText("Fictional sample records loaded.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Inspect StreamBee", exact: true })
    .click();
  await expect(
    page.getByText("Possible price increase:", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Manage cancellation" }).click();
  await page
    .getByLabel("Service status", { exact: true })
    .selectOption("Cancellation reported by user");
  await page.getByLabel("Request date", { exact: true }).fill("2026-09-25");
  await page
    .getByLabel("Effective cancellation date", { exact: true })
    .fill("2026-09-30");
  await page
    .getByRole("button", { name: "Save cancellation record", exact: true })
    .click();
  await expect(
    page.getByText("Cancellation record saved.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Imports", exact: true })
    .click();
  await page.getByRole("button", { name: "Use later statement" }).click();
  await expect(page.getByLabel("CSV content")).toHaveValue(/s6/);
  await page
    .getByRole("button", { name: "Preview import", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Import valid rows" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Import valid rows" }).click();
  await expect(
    page.getByText("Imported 1 rows.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Cancellation Centre" })
    .click();
  await expect(
    page.getByText(
      "Matching debit after recorded effective cancellation date.",
      { exact: false },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Export evidence" }).click();
});
test("mobile layout avoids page-wide overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Know where your money goes." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
