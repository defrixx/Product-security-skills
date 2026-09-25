import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { readdir, readFile } from 'node:fs/promises';
const url = 'http://127.0.0.1:3000';
const canary = process.env.SYNTHETIC_PRIVATE_CREDENTIAL;
assert(canary);
const server = spawn('node', ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1'], { stdio: 'inherit' });
let browser;
try {
  let ready = false;
  for (let i = 0; i < 120; i++) {
    if (server.exitCode !== null) throw new Error('server_exited');
    try { if ((await fetch(url)).ok) { ready = true; break; } } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  assert(ready, 'server_ready');
  const mutate = (token, body) => fetch(url + '/api/records', { method: 'POST', headers: { 'content-type': 'application/json', authorization: token }, body: JSON.stringify(body) });
  const body = { id: 'record-a', value: 'changed' };
  assert.equal((await mutate('', body)).status, 401);
  assert.equal((await mutate('Bearer SYNTHETIC_BOB', body)).status, 403);
  assert.equal((await mutate('Bearer SYNTHETIC_ALICE', { ...body, id: 'other' })).status, 403);
  assert.equal((await mutate('Bearer SYNTHETIC_ALICE', { ...body, owner: 'bob' })).status, 400);
  assert.equal((await (await fetch(url + '/api/records')).json()).value, 'initial');
  assert.equal((await mutate('Bearer SYNTHETIC_ALICE', body)).status, 200);
  assert.equal((await (await fetch(url + '/api/records')).json()).value, 'changed');
  console.log('PASS SD-TS-001: direct HTTP Route Handler authorization and mutation boundaries');
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  const responseBodies = [];
  page.on('response', response => { responseBodies.push(response.body().catch(() => ({ unreadable: true }))); });
  await page.goto(url, { waitUntil: 'networkidle' });
  const payload = '<img src=x onerror="window.syntheticExecuted=true"><script>window.syntheticExecuted=true</script>';
  await page.getByLabel('Untrusted text').fill(payload);
  assert.equal(await page.getByTestId('rendered').textContent(), payload);
  assert.equal(await page.getByTestId('rendered').locator('img,script').count(), 0);
  assert.equal(await page.evaluate(() => window.syntheticExecuted), undefined);
  console.log('PASS SD-TS-002: hydrated browser DOM retains payload as inert text');
  async function scan(dir) {
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      const path = dir + '/' + entry.name;
      if (entry.isDirectory()) await scan(path);
      else assert(!(await readFile(path)).includes(Buffer.from(canary)), 'client_bundle_canary');
    }
  }
  await scan('.next/static');
  assert(!(await page.content()).includes(canary), 'page_canary');
  for (const body of await Promise.all(responseBodies)) {
    assert(Buffer.isBuffer(body), 'browser_response_unreadable');
    assert(!body.includes(Buffer.from(canary)), 'network_canary');
  }
  console.log('PASS SD-TS-003: client files, HTML and observed browser responses omit synthetic canary');
  console.log(JSON.stringify({ next: JSON.parse(await readFile('node_modules/next/package.json')).version, react: JSON.parse(await readFile('node_modules/react/package.json')).version, browser: browser.version(), checks: 3 }));
} finally {
  if (browser) await browser.close();
  server.kill('SIGTERM');
}
