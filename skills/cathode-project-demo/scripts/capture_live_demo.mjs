#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { chromium } from "playwright";

function parseArgs(argv) {
  const args = {
    headless: false,
    timeoutSeconds: 30,
    attemptName: "",
    outputManifest: "",
  };

  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--session-json") {
      args.sessionJson = argv[++index];
    } else if (arg === "--capture-plan") {
      args.capturePlan = argv[++index];
    } else if (arg === "--output-manifest") {
      args.outputManifest = argv[++index];
    } else if (arg === "--attempt-name") {
      args.attemptName = argv[++index] || "";
    } else if (arg === "--timeout-seconds") {
      args.timeoutSeconds = Number(argv[++index] || "30");
    } else if (arg === "--headless") {
      args.headless = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!args.sessionJson || !args.capturePlan) {
    throw new Error("--session-json and --capture-plan are required");
  }
  return args;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function ensureDir(dirPath) {
  await fs.mkdir(dirPath, { recursive: true });
}

function secondsSince(startMs) {
  return Math.max(0, (Date.now() - startMs) / 1000);
}

function slugify(value, fallback) {
  const text = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
  return text || fallback;
}

function resolveUrl(target, baseUrl) {
  if (!target) {
    return String(baseUrl || "");
  }
  try {
    return new URL(target, baseUrl || undefined).toString();
  } catch {
    return String(target);
  }
}

function clampBox(box, viewport) {
  const widthLimit = Number(viewport?.width || 1664);
  const heightLimit = Number(viewport?.height || 928);
  let width = Math.max(2, Math.floor(box.width || widthLimit));
  let height = Math.max(2, Math.floor(box.height || heightLimit));
  if (width > widthLimit) {
    width = widthLimit;
  }
  if (height > heightLimit) {
    height = heightLimit;
  }
  let left = Math.max(0, Math.floor(box.x || 0));
  let top = Math.max(0, Math.floor(box.y || 0));
  left = Math.min(left, Math.max(0, widthLimit - width));
  top = Math.min(top, Math.max(0, heightLimit - height));
  return {
    x: left,
    y: top,
    width,
    height,
  };
}

async function getLocatorBox(page, selector, viewport, padding = 32) {
  if (!selector) {
    return null;
  }
  const locator = page.locator(selector).first();
  await locator.waitFor({ state: "visible", timeout: 5000 });
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) {
    return null;
  }
  return clampBox(
    {
      x: box.x - padding,
      y: box.y - padding,
      width: box.width + padding * 2,
      height: box.height + padding * 2,
    },
    viewport,
  );
}

async function getTextExcerpt(page, selector) {
  const locator = selector ? page.locator(selector).first() : page.locator("body");
  try {
    const text = await locator.innerText({ timeout: 3000 });
    return String(text || "").replace(/\s+/g, " ").trim().slice(0, 600);
  } catch {
    return "";
  }
}

function sanitizeAction(action) {
  const cleaned = { ...action };
  if (typeof cleaned.script === "string" && cleaned.script.length > 180) {
    cleaned.script = `${cleaned.script.slice(0, 177)}...`;
  }
  return cleaned;
}

async function evaluateScriptOnPage(page, scriptSource) {
  const source = String(scriptSource || "").trim();
  if (!source) {
    return null;
  }
  return await page.evaluate(({ sourceText }) => {
    const evaluated = globalThis.eval(sourceText);
    if (typeof evaluated === "function") {
      return evaluated();
    }
    return evaluated;
  }, { sourceText: source });
}

async function runAction(page, action, timeoutMs) {
  const type = String(action?.type || "").trim();
  if (!type) {
    return;
  }

  if (type === "goto") {
    await page.goto(String(action.url || ""), { waitUntil: "networkidle", timeout: timeoutMs });
    return;
  }
  if (type === "click") {
    await page.locator(String(action.selector || "")).first().click({ timeout: timeoutMs });
    return;
  }
  if (type === "dblclick") {
    await page.locator(String(action.selector || "")).first().dblclick({ timeout: timeoutMs });
    return;
  }
  if (type === "fill") {
    await page.locator(String(action.selector || "")).first().fill(String(action.value || ""), { timeout: timeoutMs });
    return;
  }
  if (type === "press") {
    const selector = String(action.selector || "").trim();
    if (selector) {
      await page.locator(selector).first().press(String(action.key || "Enter"), { timeout: timeoutMs });
    } else {
      await page.keyboard.press(String(action.key || "Enter"));
    }
    return;
  }
  if (type === "select_option") {
    const value = action.value ?? action.values;
    const values = Array.isArray(value) ? value.map(String) : [String(value || "")];
    await page.locator(String(action.selector || "")).first().selectOption(values, { timeout: timeoutMs });
    return;
  }
  if (type === "wait_for_selector") {
    await page.locator(String(action.selector || "")).first().waitFor({
      state: String(action.state || "visible"),
      timeout: timeoutMs,
    });
    return;
  }
  if (type === "wait_for_url") {
    await page.waitForURL(String(action.url || ""), { timeout: timeoutMs });
    return;
  }
  if (type === "wait_for_timeout") {
    await page.waitForTimeout(Number(action.ms || 500));
    return;
  }
  if (type === "set_theme") {
    const colorScheme = String(action.value || "dark") === "light" ? "light" : "dark";
    await page.emulateMedia({ colorScheme });
    return;
  }
  if (type === "scroll_into_view") {
    await page.locator(String(action.selector || "")).first().scrollIntoViewIfNeeded({ timeout: timeoutMs });
    return;
  }
  if (type === "evaluate") {
    await evaluateScriptOnPage(page, action.script);
    return;
  }

  throw new Error(`Unsupported capture action: ${type}`);
}

async function main() {
  const args = parseArgs(process.argv);
  const session = await readJson(path.resolve(args.sessionJson));
  const plan = await readJson(path.resolve(args.capturePlan));

  const attemptSlug = slugify(args.attemptName || "capture", "capture");
  const timeoutMs = Math.max(1000, Math.floor(Number(args.timeoutSeconds || 30) * 1000));
  const theme = String(plan.theme || session.preferred_theme || "dark").trim().toLowerCase() === "light" ? "light" : "dark";
  const viewport = {
    width: Number(plan.viewport?.width || session.viewport?.width || 1664),
    height: Number(plan.viewport?.height || session.viewport?.height || 928),
  };

  const artifacts = session.artifacts || {};
  const rawDir = path.resolve(artifacts.raw_dir || path.join(process.cwd(), "raw"));
  const screenshotsDir = path.resolve(artifacts.screenshots_dir || path.join(process.cwd(), "screenshots"));
  const tracesDir = path.resolve(artifacts.traces_dir || path.join(process.cwd(), "traces"));
  const reportsDir = path.resolve(artifacts.reports_dir || path.join(process.cwd(), "reports"));
  await Promise.all([ensureDir(rawDir), ensureDir(screenshotsDir), ensureDir(tracesDir), ensureDir(reportsDir)]);
  const attemptScreenshotsDir = path.join(screenshotsDir, attemptSlug);
  await ensureDir(attemptScreenshotsDir);

  const outputManifestPath = path.resolve(
    args.outputManifest || artifacts.capture_manifest_path || path.join(process.cwd(), "capture_manifest.json"),
  );
  const stepManifestPath = path.join(reportsDir, `${attemptSlug}_step_manifest.json`);
  const tracePath = path.join(tracesDir, `${attemptSlug}_trace.zip`);

  const browser = await chromium.launch({ headless: !!args.headless });
  const context = await browser.newContext({
    viewport,
    colorScheme: theme,
    recordVideo: { dir: rawDir, size: viewport },
  });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });

  const page = await context.newPage();
  const pageVideo = page.video();
  const baseUrl = String(plan.start_url || session.app_url || session.expected_url || "");
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  const captureStartMs = Date.now();
  const stepEntries = [];
  const clipEntries = [];

  try {
    if (baseUrl) {
      await page.goto(resolveUrl(baseUrl, session.expected_url || session.app_url || ""), {
        waitUntil: "networkidle",
        timeout: timeoutMs,
      });
    }

    for (const rawStep of steps) {
      if (!rawStep || rawStep.skip) {
        continue;
      }
      const stepId = slugify(rawStep.id || rawStep.label || "step", "step");
      const stepLabel = String(rawStep.label || stepId);
      const stepStartSeconds = secondsSince(captureStartMs);
      const actions = Array.isArray(rawStep.actions) ? rawStep.actions : [];
      const focusSelector = String(rawStep.clip?.focus_selector || rawStep.focus_selector || rawStep.checkpoint_selector || "").trim();

      for (const action of actions) {
        await runAction(page, action, timeoutMs);
      }

      if (focusSelector) {
        await page.locator(focusSelector).first().scrollIntoViewIfNeeded({ timeout: timeoutMs });
      }
      const actionsCompleteSeconds = secondsSince(captureStartMs);

      const holdMs = Number(
        rawStep.hold_ms ??
          rawStep.clip?.hold_ms ??
          rawStep.settle_ms ??
          900,
      );
      if (holdMs > 0) {
        await page.waitForTimeout(holdMs);
      }

      const screenshotPath = path.join(attemptScreenshotsDir, `${stepId}.png`);
      if (focusSelector) {
        await page.locator(focusSelector).first().screenshot({ path: screenshotPath });
      } else {
        await page.screenshot({ path: screenshotPath });
      }

      const focusPadding = Number(rawStep.clip?.focus_padding ?? rawStep.focus_padding ?? 32);
      const focusBox = rawStep.focus_box
        ? clampBox(rawStep.focus_box, viewport)
        : await getLocatorBox(page, focusSelector, viewport, focusPadding);

      const textSelector = String(rawStep.text_selector || focusSelector || rawStep.checkpoint_selector || "body").trim();
      const textExcerpt = await getTextExcerpt(page, textSelector);
      const stepEndSeconds = secondsSince(captureStartMs);

      const stepEntry = {
        id: stepId,
        label: stepLabel,
        url: page.url(),
        start_seconds: stepStartSeconds,
        end_seconds: stepEndSeconds,
        screenshot_path: screenshotPath,
        focus_selector: focusSelector,
        focus_box: focusBox,
        text_excerpt: textExcerpt,
        actions: actions.map(sanitizeAction),
      };
      stepEntries.push(stepEntry);

      const clipConfig = rawStep.clip || null;
      if (clipConfig) {
        const leadInSeconds = Number(clipConfig.lead_in_seconds ?? 0.35);
        const tailSeconds = Number(clipConfig.tail_seconds ?? 0.45);
        const clipAnchor = String(clipConfig.anchor || "step_start").trim().toLowerCase();
        const clipAnchorSeconds = clipAnchor === "post_actions" ? actionsCompleteSeconds : stepStartSeconds;
        clipEntries.push({
          id: String(clipConfig.id || stepId),
          label: String(clipConfig.label || stepLabel),
          notes: String(clipConfig.notes || rawStep.notes || ""),
          source_path: "",
          start_seconds: Math.max(0, clipAnchorSeconds - Math.max(0, leadInSeconds)),
          end_seconds: stepEndSeconds + Math.max(0, tailSeconds),
          focus_box: focusBox,
          screenshot_path: screenshotPath,
          url: page.url(),
          checkpoint_selector: String(rawStep.checkpoint_selector || ""),
          text_excerpt: textExcerpt,
          kind: String(clipConfig.kind || "video_clip"),
          review_status: String(clipConfig.review_status || "accept"),
        });
      }
    }
  } finally {
    await context.tracing.stop({ path: tracePath });
    await context.close();
    await browser.close();
  }

  const tempVideoPath = await pageVideo.path();
  const ext = path.extname(tempVideoPath) || ".webm";
  const rawVideoPath = path.join(rawDir, `${attemptSlug}_browser_capture${ext}`);
  if (path.resolve(tempVideoPath) !== path.resolve(rawVideoPath)) {
    await fs.rename(tempVideoPath, rawVideoPath);
  }

  for (const clip of clipEntries) {
    clip.source_path = rawVideoPath;
  }

  const stepManifest = {
    session_id: session.session_id,
    attempt_name: attemptSlug,
    preferred_theme: theme,
    viewport,
    trace_path: tracePath,
    raw_video_path: rawVideoPath,
    steps: stepEntries,
  };
  await fs.writeFile(stepManifestPath, `${JSON.stringify(stepManifest, null, 2)}\n`, "utf8");

  const captureManifest = {
    session_id: session.session_id,
    target_repo_path: session.target_repo_path,
    app_url: session.app_url || session.expected_url || "",
    preferred_theme: theme,
    viewport,
    raw_video_path: rawVideoPath,
    trace_path: tracePath,
    step_manifest_path: stepManifestPath,
    processed_dir: artifacts.processed_dir || path.join(path.dirname(outputManifestPath), "processed"),
    clips: clipEntries,
  };
  await fs.writeFile(outputManifestPath, `${JSON.stringify(captureManifest, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(captureManifest, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
