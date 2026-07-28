/**
 * LOD benchmark harness (프롬프트 §15 성능, Gate G8).
 *
 * Drives the browser build headlessly and measures, per LOD setting:
 *   - median / p95 frame time (render + sim, main thread)
 *   - triangles submitted and draw calls
 *   - how the distance policy distributes agents across tiers
 *
 * Run:  node project/tests/bench_lod.mjs [path-to-index.html]
 *
 * IMPORTANT — reading the numbers honestly:
 * Absolute frame times depend entirely on the rasterizer. On a machine without
 * a GPU (CI, containers) Chromium falls back to SwiftShader software rendering,
 * so treat absolute ms as a *relative* comparison only. The triangle counts are
 * hardware-independent and are the load-bearing measurement for Gate G8.
 */
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { createRequire } from 'node:module';

// Resolve Playwright from a local install, else from a global one. A bare ESM
// import does not search global node_modules, so a globally-installed toolchain
// (CI images, this container) would otherwise fail to start.
const { chromium } = await (async () => {
  try { return await import('playwright'); }
  catch {
    const req = createRequire(import.meta.url);
    for (const g of ['/opt/node22/lib/node_modules/playwright/index.mjs',
                     '/usr/lib/node_modules/playwright/index.mjs',
                     '/usr/local/lib/node_modules/playwright/index.mjs']) {
      try { return await import(g); } catch { /* try next */ }
    }
    try { return req('playwright'); } catch {
      throw new Error('playwright not found — npm i -D playwright, or install it globally');
    }
  }
})();

const here = dirname(fileURLToPath(import.meta.url));
const target = process.argv[2] || resolve(here, '../../fish/index.html');

const browser = await chromium.launch({
  args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 960, height: 540 } });

const errs = [];
page.on('pageerror', e => errs.push(e.message));
page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });

await page.goto('file://' + target);
await page.waitForFunction(() => window.__biogen && window.__lodTable, null, { timeout: 15000 });

const lodTable = await page.evaluate(() => window.__lodTable);
console.log('--- mesh budget per LOD tier (hardware-independent) ---');
for (const [id, tiers] of Object.entries(lodTable)) {
  console.log(`${id.padEnd(24)} ${tiers.map(t => String(t.tris).padStart(5)).join(' ')}  tris`);
}

/** Measure N frames at a fixed LOD setting (-1 = distance policy). */
async function measure(lodForce, frames = 70) {
  await page.evaluate(v => window.__biogen.setLOD(v), lodForce);
  await page.waitForTimeout(700);                 // let the tier split settle
  return page.evaluate(async n => {
    const ms = [];
    let tris = 0, calls = 0, tiers = null;
    await new Promise(res => {
      let i = 0;
      const tick = () => {
        const s = window.__biogen.stats;
        ms.push(s.frameMs); tris = s.tris; calls = s.calls; tiers = s.tiers.slice();
        if (++i >= n) return res();
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    ms.sort((a, b) => a - b);
    return {
      median: ms[Math.floor(ms.length / 2)],
      p95: ms[Math.floor(ms.length * 0.95)],
      tris, calls, tiers, agents: window.__biogen.agents(),
    };
  }, frames);
}

console.log('\n--- frame cost by LOD setting ---');
const cases = [['policy', -1], ['forced LOD0', 0], ['forced LOD1', 1],
               ['forced LOD2', 2], ['forced LOD3', 3]];
const results = {};
for (const [label, v] of cases) {
  const r = await measure(v);
  results[label] = r;
  console.log(`${label.padEnd(12)} median=${r.median.toFixed(2)}ms p95=${r.p95.toFixed(2)}ms ` +
              `tris=${r.tris} calls=${r.calls} tiers=${JSON.stringify(r.tiers)} agents=${r.agents}`);
}

const pol = results['policy'], l0 = results['forced LOD0'];
console.log(`\npolicy vs forced LOD0: triangles -${((1 - pol.tris / l0.tris) * 100).toFixed(1)}% ` +
            `· frame ${(l0.median / pol.median).toFixed(2)}x`);

console.log('\n--- scaling: mesh LOD + behaviour LOD at larger populations ---');
for (const n of [120, 260]) {
  await page.evaluate(k => window.__biogen.setPop('clupea_harengus', k), n);
  await page.waitForTimeout(900);

  await page.evaluate(() => window.__biogen.setBehaviorLOD(false));
  const off = await measure(-1, 50);
  await page.evaluate(() => window.__biogen.setBehaviorLOD(true));
  const on = await measure(-1, 50);
  const tiers = await page.evaluate(() => window.__biogen.behTiers());

  console.log(`agents=${off.agents}  behLOD off=${off.median.toFixed(2)}ms  ` +
              `on=${on.median.toFixed(2)}ms  gain=${(off.median / on.median).toFixed(2)}x  ` +
              `behTiers=${JSON.stringify(tiers)}`);
}

/* Behaviour LOD can only pay off when agents actually fall into the lower
   tiers. In the 16 m tank the standard-tier radius covers the whole domain, so
   this case pins the observer far away to exercise the tier machinery. */
console.log('\n--- behaviour LOD with the observer far enough for tiers to engage ---');
await page.evaluate(() => window.__biogen.setBehaviorLOD(true));
for (const d of [0, 60, 200]) {
  await page.evaluate(v => window.__biogen.setObserverOverride(v || null), d);
  await page.waitForTimeout(700);
  const r = await measure(-1, 50);
  const tiers = await page.evaluate(() => window.__biogen.behTiers());
  console.log(`observer=${d ? d + 'm' : 'camera'}  median=${r.median.toFixed(2)}ms  ` +
              `behTiers=${JSON.stringify(tiers)}  agents=${r.agents}`);
}
await page.evaluate(() => window.__biogen.setObserverOverride(null));

console.log('\nERRORS: ' + (errs.length ? errs.join(' | ') : 'none'));
await browser.close();
process.exit(errs.length ? 1 : 0);
