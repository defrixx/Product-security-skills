import assert from 'node:assert/strict';
import { createServer } from 'node:http';

export async function extendedChecks(url, browser) {
  const get = async (actor, query = '') => fetch(url + '/api/cache' + query, { headers: { authorization: actor ? 'Bearer SYNTHETIC_' + actor : '' } });
  const alice = await (await get('ALICE')).json();
  const hit = await (await get('ALICE')).json();
  assert.equal(hit.computation, alice.computation, 'actual Next Data Cache hit');
  const bob = await (await get('BOB')).json();
  assert.equal(bob.owner, 'bob');
  assert.notEqual(bob.computation, alice.computation);
  assert.notEqual((await (await get('ALICE', '?variant=full')).json()).computation, alice.computation);
  assert.equal((await get('')).status, 401);
  const unsafe = await (await get('ALICE', '?unsafe=1')).json();
  const leaked = await (await get('BOB', '?unsafe=1')).json();
  assert.equal(leaked.computation, unsafe.computation);
  assert.equal(leaked.owner, 'alice'); // Reproduced unsafe control, not a passed defense.
  await fetch(url + '/api/cache', { method: 'POST', headers: { authorization: 'Bearer SYNTHETIC_ALICE' } });
  assert.equal((await get('ALICE')).status, 403);
  assert.equal((await get('BOB')).status, 200);
  console.log('PASS SD-API-001.C06: actual Next Data Cache hits, actor/variant isolation, revocation outside cache; unsafe leak reproduced');
  console.log('PSS_CASE ' + JSON.stringify({ case: 'SD-API-001.C06', result: 'passed' }));

  const page = await browser.newPage();
  try {
    for (const mode of ['enforce', 'report', 'unsafe']) {
      await page.goto(url + '/policy?mode=' + mode);
      assert.equal(await page.evaluate(() => window.allowed), true);
      assert.equal(await page.evaluate(() => !!window.untrusted), mode !== 'enforce');
    }
    console.log('PASS SD-WEB-001.C08: real Chromium enforces script CSP; allowed nonce works; report-only/unsafe execute payload');
  console.log('PSS_CASE ' + JSON.stringify({ case: 'SD-WEB-001.C08', result: 'passed' }));
    // A distinct loopback port is a distinct origin. Server belongs to this test.
    const attacker = createServer((request, response) => {
      response.setHeader('Content-Type', 'text/html');
      response.end(`<script>window.messages=[];addEventListener('message',e=>{if(e.data==='synthetic-frame-ready')messages.push(e.data)})</script><iframe src="${url}/policy?mode=${request.url.includes('enforce') ? 'enforce' : 'report'}"></iframe>`);
    });
    await new Promise(resolve => attacker.listen(0, '127.0.0.1', resolve));
    try {
      const origin = 'http://127.0.0.1:' + attacker.address().port;
      await page.goto(origin + '/report', { waitUntil: 'networkidle' });
      await page.waitForFunction(() => window.messages.length === 1);
      await page.goto(origin + '/enforce', { waitUntil: 'networkidle' });
      assert.equal(await page.evaluate(() => window.messages.length), 0);
      assert(!page.frames().some(frame => frame.url().includes('/policy?mode=enforce')), 'protected document not loaded into cross-origin frame');
      // Same-origin parent is an allowed framing control, served using page routing.
      await page.route(url + '/synthetic-parent', route => route.fulfill({ contentType: 'text/html', body: `<iframe src="${url}/policy?mode=enforce"></iframe>` }));
      await page.goto(url + '/synthetic-parent');
      await page.frameLocator('iframe').locator('#ready').waitFor();
      console.log('PASS SD-WEB-001.C07: cross-origin frame blocked; same-origin frame allowed; report-only permits framing');
  console.log('PSS_CASE ' + JSON.stringify({ case: 'SD-WEB-001.C07', result: 'passed' }));
    } finally {
      attacker.closeAllConnections();
      await new Promise((resolve, reject) => attacker.close(error => error ? reject(error) : resolve()));
      assert.equal(attacker.listening, false);
    }
  } finally {
    await page.close();
  }
}
