import * as path from "node:path";
import * as os from "node:os";
import * as puppeteer from "puppeteer";
import type { Browser, PuppeteerLaunchOptions } from "puppeteer";
import {
  install,
  Browser as PuppeteerBrowser,
  type InstalledBrowser,
} from "@puppeteer/browsers";

const DEFAULT_CHROME_BUILD = process.env.PUPPETEER_CHROME_BUILD || "121.0.6167.85";
const CACHE_DIR = process.env.PUPPETEER_CACHE_DIR || path.join(os.homedir(), ".cache", "puppeteer");

function isMissingBrowserError(error: unknown): boolean {
  if (!error || typeof error !== "object") {
    return false;
  }

  const message = "message" in error ? String((error as Error).message) : "";
  return message.includes("Could not find Chrome");
}

async function ensureBrowser(buildId: string): Promise<InstalledBrowser> {
  return install({
    cacheDir: CACHE_DIR,
    browser: PuppeteerBrowser.CHROME,
    buildId,
  });
}

export async function launchPuppeteer(options: PuppeteerLaunchOptions = {}): Promise<Browser> {
  try {
    return await puppeteer.launch({ headless: "new", ...options });
  } catch (error) {
    if (!isMissingBrowserError(error)) {
      throw error;
    }

    const installedBrowser = await ensureBrowser(DEFAULT_CHROME_BUILD);
    const executablePath = installedBrowser.executablePath ?? options.executablePath;

    return puppeteer.launch({
      headless: "new",
      ...options,
      executablePath,
    });
  }
}
