import { test, expect, type Page } from "@playwright/test";

/**
 * Querymancer demo walkthrough.
 *
 * This test is scripted to be *watched*. With `video: "on"` (see
 * playwright.config.ts) the recording is a hands-free product demo:
 *
 *   landing page → ask a question → SQL + chart → switch database →
 *   multi-turn follow-up.
 *
 * Run it once, with fresh free-tier Gemini quota:
 *
 *     npm install                       # first time — pulls @playwright/test
 *     npx playwright install chromium   # first time — pulls the browser
 *     npx playwright test               # records e2e/.artifacts/<…>/video.webm
 *
 * Convert the recording to a GIF for the README hero:
 *
 *     ffmpeg -i video.webm -vf "fps=12,scale=900:-1" demo.gif
 *
 * Targets the deployed app by default; set PLAYWRIGHT_BASE_URL to test a
 * local `npm run dev`. Doubles as the §17 frontend smoke test.
 */

// A deliberate on-screen pause — keeps the recording watchable rather than a
// blur of instant state changes. Not a sync hack: the real waits are below.
const beat = (page: Page, ms = 1400) => page.waitForTimeout(ms);

/**
 * Each answered turn renders exactly one SqlBlock (its copy button is
 * labelled "Copy SQL"). Waiting for that count to reach `turns` is how we
 * know the agent finished — retrieve → generate → execute → render.
 */
async function waitForAnswer(page: Page, turns: number) {
  await expect(page.getByRole("button", { name: "Copy SQL" })).toHaveCount(turns, {
    timeout: 2 * 60 * 1000,
  });
  // The composer re-enables once the request settles.
  await expect(page.getByLabel("Question")).toBeEnabled();
}

test("demo walkthrough — landing, query, DB switch, multi-turn", async ({ page }) => {
  const heroBox = page.getByPlaceholder("e.g. Top 5 product categories by total revenue");

  // 1 ─ Landing page — the "this is a product" first impression.
  await page.goto("/");
  await expect(heroBox).toBeVisible();
  await beat(page);

  // 2 ─ Ask the first question straight from the hero. The form hands the
  //     question to /app?q=… , which auto-submits it against Northwind.
  await heroBox.fill("What are the top 5 products by total revenue?");
  await beat(page, 800);
  await page.getByRole("button", { name: "Run" }).click();

  // 3 ─ The agent retrieves schema chunks, generates SQL, runs it read-only.
  await expect(page).toHaveURL(/\/app/);
  await waitForAnswer(page, 1);
  await expect(page.getByRole("button", { name: "Copy SQL" })).toBeVisible();
  // The results panel auto-selects a chart for the answer.
  await expect(page.getByRole("button", { name: "table" })).toBeVisible();
  await beat(page, 2200);

  // 4 ─ Switch databases from the sidebar. Each switch starts a fresh
  //     conversation — a session is bound to one schema.
  await page.getByRole("button", { name: /^IPL/ }).click();
  await expect(page.getByRole("button", { name: "Copy SQL" })).toHaveCount(0);
  await beat(page);

  // 5 ─ Ask an IPL question through the chat composer.
  await page.getByLabel("Question").fill("Which 5 teams have won the most matches?");
  await beat(page, 800);
  await page.getByLabel("Send").click();
  await waitForAnswer(page, 1);
  await beat(page, 2200);

  // 6 ─ Multi-turn. "those teams" is meaningless on its own — it only
  //     resolves against the previous turn, which the backend inlines into
  //     the prompt as PRIOR TURNS context.
  await page
    .getByLabel("Question")
    .fill("How many matches did each of those teams play in total?");
  await beat(page, 800);
  await page.getByLabel("Send").click();
  await waitForAnswer(page, 2);
  await beat(page, 2600);

  // Final state — two answered turns in one IPL session.
  await expect(page.getByRole("button", { name: "Copy SQL" })).toHaveCount(2);
});
