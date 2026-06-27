import { expect, test } from "@playwright/test";

const FIREWALL = process.env.NEXT_PUBLIC_FIREWALL_URL ?? "http://127.0.0.1:8000";

test("renders the control-plane shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Agent Firewall" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Live activity" })).toBeVisible();
  await expect(page.getByRole("button", { name: /run demo attack/i })).toBeVisible();
});

test("mission control page renders its controls", async ({ page }) => {
  await page.goto("/mission");
  await expect(page.getByRole("heading", { name: "Agent Firewall" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Execution" })).toBeVisible();
  await expect(page.getByRole("button", { name: /run agent/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /firewall (on|off)/i })).toBeVisible();
});

test("streams a blocked event when the demo runs", async ({ page, request }) => {
  const health = await request.get(`${FIREWALL}/health`).catch(() => null);
  test.skip(!health?.ok(), "firewall backend not reachable on :8000");

  await page.goto("/");
  await page.getByRole("button", { name: /run demo attack/i }).click();

  const blocked = page.locator('[data-testid="event-card"][data-action="block"]');
  await expect(blocked.first()).toBeVisible({ timeout: 15_000 });
});
