import { test, expect } from "@playwright/test";

test.describe("Landing smoke", () => {
  test("hero renders the tagline and demo uploader", async ({ page }) => {
    await page.goto("/");

    // Hero heading + demo slot
    await expect(page.getByRole("heading", { name: /Convierte PDF, PNG, JPG/ })).toBeVisible();
    await expect(page.getByText("Subí tu plano arquitectónico")).toBeVisible();
    await expect(page.getByText("Plataforma de conversión CAD")).toBeVisible();
  });

  test("primary navigation is present", async ({ page }) => {
    await page.goto("/");

    for (const label of ["Inicio", "Cómo funciona", "Precios", "Contacto"]) {
      await expect(page.getByRole("link", { name: label }).first()).toBeVisible();
    }
  });

  test("pricing page loads", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page).toHaveTitle(/Precios/i);
  });
});
