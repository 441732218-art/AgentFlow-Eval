// scripts/soft_screenshots.mjs
import { chromium } from 'playwright';
import { mkdirSync, existsSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

const BASE = 'http://127.0.0.1:5173';
const OUT = resolve(process.cwd(), 'docs/soft-copyright/screenshots');
if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });

const NOTFOUND_RE = /404|not\s*found|找不到|页面不存在|no\s*match|cannot\s*get/i;

async function probe(page, path) {
  let status = null, finalUrl = '', text = '', verdict = 'unknown', err = '';
  try {
    const resp = await page.goto(BASE + path, { waitUntil: 'load', timeout: 60000 });
    status = resp ? resp.status() : null;
    await page.waitForTimeout(2500);
    finalUrl = page.url();
    try { text = (await page.locator('body').innerText({ timeout: 3000 })) || ''; } catch {}
    const t = text.replace(/\s+/g, ' ').trim();
    if (NOTFOUND_RE.test(t)) verdict = 'NOT_FOUND';
    else if (t.length < 50) verdict = 'BLANK';
    else if (finalUrl && !finalUrl.includes(path.split('?')[0]) && path !== '/login') verdict = 'REDIRECT';
    else verdict = 'RENDERED';
  } catch (e) { err = String(e && e.message || e); verdict = 'ERROR'; }
  return { status, finalUrl, textLen: text.replace(/\s+/g,' ').trim().length, snippet: text.replace(/\s+/g,' ').trim().slice(0,160), verdict, err };
}

async function shot(page, path, file, fullPage) {
  const p = await probe(page, path);
  if (file && (p.verdict === 'RENDERED' || p.verdict === 'REDIRECT')) {
    try { await page.screenshot({ path: resolve(OUT, file), fullPage: !!fullPage }); p.saved = file; }
    catch (e) { p.saved = 'SAVE_ERROR:' + e.message; }
  } else { p.saved = null; }
  return p;
}

async function tryExportDialog(page) {
  for (const t of ['导出','下载','Export','export']) {
    const el = page.getByText(t, { exact: false }).first();
    if (await el.count()) {
      try {
        await el.click({ timeout: 2000 }); await page.waitForTimeout(1200);
        const dlg = page.locator('[role=dialog], .ant-modal, .el-dialog, .modal, .drawer');
        if (await dlg.count()) return 'clicked:' + t + ' -> dialog';
        return 'clicked:' + t + ' -> no-dialog';
      } catch {}
    }
  }
  const view = page.getByText('查看', { exact: false }).first();
  if (await view.count()) {
    try {
      await view.click({ timeout: 2000 }); await page.waitForTimeout(1500);
      for (const t of ['导出','下载','Export']) {
        const el2 = page.getByText(t, { exact: false }).first();
        if (await el2.count()) { try { await el2.click({ timeout: 2000 }); await page.waitForTimeout(1200); return 'via-查看->clicked:' + t; } catch {} }
      }
      return 'via-查看 -> no-export-button';
    } catch {}
  }
  return 'export-entry-not-found';
}

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const rows = [];

  let login = await shot(page, '/login', 'login.png', false);
  if (login.verdict !== 'RENDERED') {
    const r2 = await probe(page, '/');
    let hasPwd = false;
    try { hasPwd = (await page.locator('input[type=password]').count()) > 0; } catch {}
    login.note = `/login=${login.verdict}; 根路径 password 输入框=${hasPwd}`;
    if (hasPwd) { try { await page.screenshot({ path: resolve(OUT,'login.png'), fullPage:false }); login.saved='login.png'; } catch {} }
    else login.note += ' => 无独立登录页(开发模式免登)';
  }
  rows.push({ key:'login', path:'/login', ...login });

  rows.push({ key:'experiments', path:'/experiments', ...(await shot(page, '/experiments', 'ab_experiment.png', true)) });
  rows.push({ key:'benchmarks',  path:'/benchmarks',  ...(await shot(page, '/benchmarks',  'benchmark.png',  true)) });

  const rep = await probe(page, '/reports');
  const expRes = (rep.verdict === 'RENDERED') ? await tryExportDialog(page) : 'reports-not-rendered';
  let expSaved = null;
  try { await page.screenshot({ path: resolve(OUT,'export.png'), fullPage:false }); expSaved='export.png'; } catch (e) { expSaved='SAVE_ERROR:'+e.message; }
  rows.push({ key:'export', path:'/reports(+click)', verdict: rep.verdict, exportAction: expRes, saved: expSaved, snippet: rep.snippet });

  for (const [key, path] of [['dashboard','/dashboard'],['tasks_create','/tasks/create'],['reports','/reports'],['settings','/settings']]) {
    rows.push({ key, path, ...(await probe(page, path)), saved: null });
  }

  await browser.close();

  console.log('\n================ 截图与可达性回报 ================');
  console.log('存储目录:', OUT);
  console.log('目录文件:', JSON.stringify(existsSync(OUT)?readdirSync(OUT):[]));
  console.table(rows.map(r => ({
    key: r.key, path: r.path, http: r.status, verdict: r.verdict,
    finalUrl: r.finalUrl || '', textLen: r.textLen ?? '', saved: r.saved || '-',
    exportAction: r.exportAction || '', note: r.note || '', err: r.err || ''
  })));
  console.log('\n--- 关键三行 snippet（供人工判断是否空壳）---');
  for (const k of ['login','experiments','benchmarks']) {
    const r = rows.find(x => x.key === k);
    console.log(`[${k}] verdict=${r.verdict} | snippet="${r.snippet||''}"`);
  }
  console.log('==================================================\n');
})();
