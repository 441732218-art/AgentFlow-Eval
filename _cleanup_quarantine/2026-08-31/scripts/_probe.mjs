import { chromium } from 'playwright';
import { writeFileSync } from 'fs';
const BASE = 'http://127.0.0.1:5173';
const E = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const NF = /404|not\s*found|找不到|页面不存在|no\s*match|cannot\s*get/i;

async function probe(path) {
  const b = await chromium.launch({ executablePath: E, args: ['--headless=new'] });
  const p = await b.newPage();
  let r = { path, status: null, verdict: 'unknown', textLen: 0, snippet: '', err: '', finalUrl: '' };
  try {
    const resp = await p.goto(BASE + path, { waitUntil: 'load', timeout: 30000 });
    r.status = resp ? resp.status() : null;
    await p.waitForTimeout(2500);
    r.finalUrl = p.url();
    const t = (await p.locator('body').innerText({ timeout: 3000 }) || '').replace(/\s+/g,' ').trim();
    r.textLen = t.length;
    r.snippet = t.slice(0, 120);
    if (NF.test(t)) r.verdict = 'NOT_FOUND';
    else if (t.length < 50) r.verdict = 'BLANK';
    else if (r.finalUrl && !r.finalUrl.includes(path.split('?')[0]) && path !== '/login') r.verdict = 'REDIRECT';
    else r.verdict = 'RENDERED';
  } catch(e) { r.verdict = 'ERROR'; r.err = String(e.message||e).slice(0,200); }
  await b.close();
  return r;
}

async function main() {
  const routes = ['/login','/','/dashboard','/tasks/create','/experiments','/benchmarks','/reports','/settings'];
  const results = [];
  for (const r of routes) {
    const res = await probe(r);
    results.push(res);
  }
  let out = '=== PROBE RESULTS ===\n\n';
  out += '| key | path | http | verdict | textLen | snippet | err |\n';
  out += '|-----|------|------|---------|---------|---------|-----|\n';
  for (const r of results) {
    out += '| ' + r.path.replace('/','') + ' | ' + r.path + ' | ' + r.status + ' | ' + r.verdict + ' | ' + r.textLen + ' | ' + r.snippet + ' | ' + r.err + ' |\n';
  }
  writeFileSync('D:\\AgentFlow-Eval\\_probe_result.md', out, 'utf-8');
  console.log('Done');
}
main();

