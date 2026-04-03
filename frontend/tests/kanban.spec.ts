import { expect, test, type Page } from "@playwright/test";

const installAuthMocks = async (page: Page) => {
  let authenticated = false;

  await page.route("**/api/auth/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const url = request.url();

    if (url.endsWith("/api/auth/me") && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          authenticated
            ? { authenticated: true, username: "user" }
            : { authenticated: false, username: null }
        ),
      });
      return;
    }

    if (url.endsWith("/api/auth/login") && method === "POST") {
      const payload = request.postDataJSON() as { username?: string; password?: string };
      const valid = payload.username === "user" && payload.password === "password";
      authenticated = valid;
      await route.fulfill({
        status: valid ? 200 : 401,
        contentType: "application/json",
        body: JSON.stringify(
          valid
            ? { authenticated: true, username: "user" }
            : { detail: "Invalid credentials" }
        ),
      });
      return;
    }

    if (url.endsWith("/api/auth/logout") && method === "POST") {
      authenticated = false;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ authenticated: false, username: null }),
      });
      return;
    }

    await route.fallback();
  });
};

const login = async (page: Page) => {
  await installAuthMocks(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

test("loads the kanban board", async ({ page }) => {
  await login(page);
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await login(page);
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("logs out and returns to sign-in", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
});
