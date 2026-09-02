// scripts/generate_copyright_screenshots.mjs
import { chromium } from 'playwright';
import { existsSync, mkdirSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

const BASE = 'http://127.0.0.1:5173';
const OUT = resolve(process.cwd(), 'docs/soft-copyright/screenshots');
if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });

const targets = [
  { key: 'command_center', path: '/dashboard',     file: 'command_center.png' },
  { key: 'nav_overview',   path: '/dashboard',     file: 'nav_overview.png' },
  { key: 'task_list',      path: '/tasks',         file: 'task_list.png' },
  { key: 'task_create',    path: '/tasks/create',  file: 'task_create.png' },
  { key: 'monitoring',     path: '/monitoring',    file: 'monitoring.png' },
  { key: 'trace',          path: '/traces',        file: 'trace.png' },
  { key: 'reports',        path: '/reports',       file: 'reports.png' },
  { key: 'settings',       path: '/settings',      file: 'settings.png' },
  { key: 'analytics',      path: '/analytics',     file: 'analytics.png' },
  { key: 'billing',        path: '/billing',       file: 'billing.png' },
  { key: 'plugins',        path: '/plugins',       file: 'plugins.png' },
  { key: 'login',          path: '/login',         file: 'login.png' },
  { key: 'diagnosis',      path: '/diagnosis',     file: 'diagnosis.png' },
];

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const results = [];

  for (const t of targets) {
    try {
      const resp = await page.goto(BASE + t.path, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(2000);
      const status = resp ? resp.status() : -1;
      const url = page.url();
      // Check for 404 or blank
      let text = '';
      try { text = (await page.locator('body').innerText({ timeout: 2000 })) || ''; } catch {}
      const trimmed = text.replace(/\s+/g, ' ').trim();
      const is404 = /404|not found|找不到/i.test(trimmed) || trimmed.length < 30;

      if (!is404 && status < 400) {
        await page.screenshot({ path: resolve(OUT, t.file), fullPage: false });
        results.push({ key: t.key, path: t.path, status, saved: t.file, note: '' });
      } else {
        results.push({ key: t.key, path: t.path, status, saved: null, note: is404 ? 'NOT_FOUND/BLANK' : `HTTP ${status}` });
      }
    } catch (e) {
      results.push({ key: t.key, path: t.path, status: -1, saved: null, note: e.message?.slice(0, 100) || String(e) });
    }
  }

  await browser.close();

  console.log('\n==== 截图结果 ====');
  console.log('输出目录:', OUT);
  console.log('目录文件:', JSON.stringify(existsSync(OUT) ? readdirSync(OUT) : []));
  console.table(results);
  console.log('================\n');
})();
