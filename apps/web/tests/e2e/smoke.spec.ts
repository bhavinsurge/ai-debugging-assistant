import { test, expect } from "@playwright/test";

test("login and open investigations", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@rootcause.local");
  await page.getByLabel("Password").fill("Password123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Investigations" })).toBeVisible({
    timeout: 15000,
  });
});
