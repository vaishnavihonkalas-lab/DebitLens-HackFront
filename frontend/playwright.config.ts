import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: process.env.E2E_URL || "http://127.0.0.1:5173",
    headless: true,
  },
  workers: 1,
});
