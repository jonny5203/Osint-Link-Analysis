import { expect, test } from "@playwright/test";
import { resolve } from "node:path";

const username = process.env.PHASE4_ANALYST_USERNAME;
const password = process.env.PHASE4_ANALYST_PASSWORD;

test("signs in, searches Avery, expands OWNS, and opens provenance", async ({
  page,
}) => {
  test.skip(!username || !password, "Phase 4 runtime credentials are required");

  await page.goto("/");
  await page.getByLabel("Username").fill(username!);
  await page.getByLabel("Password").fill(password!);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(
    page.getByRole("heading", { name: "Graph", exact: true }),
  ).toBeVisible();
  await expect(
    page.evaluate(() => ({
      local: window.localStorage.length,
      session: window.sessionStorage.length,
    })),
  ).resolves.toEqual({ local: 0, session: 0 });

  await page.getByRole("combobox", { name: "Search entities" }).fill("Avery");
  await page.getByRole("option").filter({ hasText: "Avery Stone" }).click();

  const nodes = page.getByRole("region", { name: /Nodes \(/ });
  await expect(nodes.getByRole("button", { name: /Avery Stone/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Avery Stone" })).toBeVisible();

  await page.getByRole("button", { name: "Expand selected" }).click();

  await expect(
    nodes.getByRole("button", { name: /Northstar Trading Ltd/ }),
  ).toBeVisible();
  const relationships = page.getByRole("region", { name: /Relationships \(/ });
  await expect(relationships).toContainText("OWNS");
  await expect(relationships).toContainText("fixture:entity:avery");
  await expect(relationships).toContainText("fixture:entity:northstar");

  await expect(page.getByRole("heading", { name: "Provenance" })).toBeVisible();
  await expect(page.getByText("fixture:record:alpha:avery")).toBeVisible();

  await page.screenshot({
    path: resolve(process.cwd(), "../docs/verification/phase-4.png"),
    fullPage: true,
  });
});
