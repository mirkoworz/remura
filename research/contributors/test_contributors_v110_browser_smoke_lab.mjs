import assert from 'node:assert/strict';
import test from 'node:test';
import {launchChromium} from './chromium_v110_fixture.mjs';
import {createFixtureV110, serveFixtureV110} from './fixture_v110_lab.mjs';

test('Chromium desktop and iPhone complete submission, OWNER approval and recovery', async () => {
  const fixture = await createFixtureV110();
  let lab, chrome;
  try {
    lab = await serveFixtureV110(fixture);
    chrome = await launchChromium();
    const contributor = await chrome.newPage(lab.origin, {width: 375, height: 667, mobile: true});
    await contributor.setCookie(lab.cookie, fixture.issueToken('friend-a'));
    await contributor.navigate('/contributors/');
    const mobile = await contributor.evaluate(`({
      title: document.querySelector('.version')?.textContent,
      width: innerWidth, contentWidth: document.documentElement.scrollWidth,
      cot: document.querySelector('#cot')?.textContent.includes('COT'),
      links: Array.from(document.querySelectorAll('a[href^="/owner/"]')).length,
      targets: Array.from(document.querySelectorAll('nav a, nav summary')).filter(el => el.getClientRects().length)
        .map(el => el.getBoundingClientRect().height)
    })`);
    assert.match(mobile.title, /v1\.10 LAB.*Europe\/Rome/);
    assert.equal(mobile.width, 375);
    assert.equal(mobile.contentWidth, 375);
    assert.equal(mobile.cot, true);
    assert.equal(mobile.links, 0);
    assert.ok(mobile.targets.length > 1 && mobile.targets.every(height => height >= 46));
    await contributor.navigate('/contributors/levels/');
    await contributor.waitFor("document.querySelector('#intake')?.hidden === false", 'the level form');
    async function submit(draft) {
      const fields = [
        ['#market', draft.market], ['#provider', draft.provider], ['#mapping', '0'],
        ['#period', draft.period], ['#kind', draft.kind], ['#price', draft.price],
        ['#anchor', draft.anchor_utc], ['#observed', draft.observed_utc], ['#note', draft.note],
      ];
      for (const [selector, value] of fields) await contributor.fill(selector, value);
      await contributor.click('#send');
    }
    await submit(fixture.payload());
    await contributor.waitFor("document.querySelector('#intakeStatus')?.textContent.includes('Ricevuta #')", 'the personal receipt');

    const owner = await chrome.newPage(lab.origin, {width: 1440, height: 900});
    await owner.setCookie(lab.cookie, fixture.issueToken('owner'));
    await owner.navigate('/owner/levels/');
    await owner.waitFor("document.querySelector('#queueRows button')", 'the OWNER review queue');
    await owner.click('#queueRows summary');
    await owner.click('#queueRows button');
    await owner.fill('#decision', 'APPROVED');
    await owner.fill('#reason', 'Collaudo locale');
    await owner.click('#reviewSend');
    await owner.waitFor("document.querySelector('#reviewStatus')?.textContent.includes('Approvazione registrata')", 'approval');
    await owner.waitFor("document.querySelector('#historyRows')?.textContent.includes('Approvato')", 'history');
    const pro = await chrome.newPage(lab.origin, {width: 430, height: 932, mobile: true});
    await pro.setCookie(lab.cookie, fixture.issueToken('owner'));
    await pro.navigate('/owner/levels/');
    assert.equal(await pro.evaluate('innerWidth'), 430);
    assert.equal(await pro.evaluate('document.documentElement.scrollWidth'), 430);

    // Lose the successful reply after the real fetch has reached the Worker and D1.
    await contributor.evaluate(`(() => {
      const fetchFromWorker = window.fetch.bind(window);
      window.fetch = async (path, options) => {
        const reply = await fetchFromWorker(path, options);
        if (path === '/api/submit' && options?.method === 'POST' && reply.ok) {
          window.fetch = fetchFromWorker;
          throw new TypeError('Simulated loss of the submitted reply');
        }
        return reply;
      };
    })()`);
    await submit(fixture.payload({price: '1.0924'}));
    await contributor.waitFor("document.querySelector('#intakeStatus')?.textContent.includes('incerto')", 'an uncertain outcome');
    await contributor.click('#checkAttempt');
    await contributor.waitFor("document.querySelector('#intakeStatus')?.textContent.includes('Ricevuta #')", 'the recovered receipt');
    assert.equal(lab.traffic.filter(({method, path}) => method === 'POST' && path === '/api/submit').length, 2);
    assert.deepEqual([...contributor.pageErrors, ...owner.pageErrors, ...pro.pageErrors], []);
    console.log('Browser pass:', chrome.version, 'desktop 1440x900, iPhone 375x667 and 430x932; COT, signed submit, personal receipt, OWNER approval, history and recovery after a dropped reply.');
  } finally {
    await chrome?.close();
    await lab?.close();
    fixture.db.close();
  }
});
