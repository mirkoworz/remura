// Node-only DevTools client for isolated local Chrome browser fixtures.
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {access, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {setTimeout as sleep} from 'node:timers/promises';

async function chromiumPath() {
  const candidates = [process.env.REMURA_TEST_CHROME,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/chromium', '/usr/bin/google-chrome'].filter(Boolean);
  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {}
  }
  throw Error('Chrome or Chromium is required for the browser fixture');
}

export async function launchChromium() {
  const executable = await chromiumPath();
  const directory = await mkdtemp(join(tmpdir(), 'remura-v110-chrome-'));
  const browser = spawn(executable, [
    '--headless', '--remote-debugging-pipe', `--user-data-dir=${directory}`,
    '--disable-background-networking', '--disable-component-update', '--disable-default-apps',
    '--disable-sync', '--no-first-run', '--no-default-browser-check', '--use-mock-keychain',
    '--password-store=basic', '--no-proxy-server', '--disable-gpu',
    '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',
  ], {stdio: ['ignore', 'ignore', 'ignore', 'pipe', 'pipe']});
  const exit = once(browser, 'exit').catch(() => []);
  const pending = new Map();
  const events = new Map();
  let sequence = 0;
  let closed = false;
  let input = '';

  function interrupted() {
    for (const entry of pending.values()) entry.finish(Error('Chrome DevTools stopped'));
    pending.clear();
  }
  browser.on('error', interrupted);
  browser.on('exit', interrupted);
  browser.stdio[3].on('error', interrupted);
  browser.stdio[4].setEncoding('utf8');
  browser.stdio[4].on('data', chunk => {
    input += chunk;
    let end;
    while ((end = input.indexOf('\0')) !== -1) {
      const raw = input.slice(0, end);
      input = input.slice(end + 1);
      if (!raw) continue;
      const message = JSON.parse(raw);
      if (message.id) {
        const entry = pending.get(message.id);
        pending.delete(message.id);
        if (entry) entry.finish(message.error ? Error(`Chrome DevTools rejected ${entry.method}`) : null, message.result);
      } else if (message.sessionId) {
        events.get(message.sessionId)?.(message);
      }
    }
  });

  function send(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const id = ++sequence;
      const timeout = setTimeout(() => {
        pending.delete(id);
        reject(Error(`Chrome DevTools timed out: ${method}`));
      }, 8000);
      pending.set(id, {
        method,
        finish(error, result) {
          clearTimeout(timeout);
          if (error) reject(error);
          else resolve(result);
        },
      });
      browser.stdio[3].write(`${JSON.stringify({id, method, params, sessionId})}\0`);
    });
  }

  async function close() {
    if (closed) return;
    closed = true;
    if (browser.exitCode === null && browser.signalCode === null) {
      browser.kill();
      await Promise.race([exit, sleep(1500)]);
      if (browser.exitCode === null && browser.signalCode === null) browser.kill('SIGKILL');
    }
    await Promise.race([exit, sleep(1500)]);
    await rm(directory, {recursive: true, force: true, maxRetries: 3});
  }

  try {
    const version = await send('Browser.getVersion');
    async function newPage(origin, {width = 1340, height = 950, mobile = false} = {}) {
      const {browserContextId} = await send('Target.createBrowserContext');
      const {targetId} = await send('Target.createTarget', {url: 'about:blank', browserContextId});
      const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
      const command = (method, params) => send(method, params, sessionId);
      const pageErrors = [];
      events.set(sessionId, ({method}) => {
        if (method === 'Runtime.exceptionThrown') pageErrors.push('uncaught page exception');
      });
      await command('Page.enable');
      await command('Runtime.enable');
      await command('Network.enable');
      await command('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: mobile ? 3 : 1, mobile,
        screenOrientation: {type: 'portraitPrimary', angle: 0}});
      if (mobile) await command('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 5});

      async function evaluate(expression) {
        const result = await command('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
        if (result.exceptionDetails) throw Error('Chrome page evaluation failed');
        return result.result.value;
      }

      async function waitFor(expression, description) {
        const end = Date.now() + 5000;
        while (Date.now() < end) {
          if (await evaluate(expression)) return;
          await sleep(40);
        }
        throw Error(`Chrome page did not show ${description}`);
      }

      async function navigate(path) {
        const destination = origin + path;
        const result = await command('Page.navigate', {url: destination});
        if (result.errorText) throw Error('Chrome fixture navigation failed');
        await waitFor(`document.readyState === 'complete' && location.href === ${JSON.stringify(destination)}`, 'the completed navigation');
      }

      async function setCookie(name, value) {
        await command('Network.setCookie', {url: origin, name, value, httpOnly: true, sameSite: 'Strict'});
      }

      const select = selector => `document.querySelector(${JSON.stringify(selector)})`;
      function click(selector) {
        return evaluate(`(() => {
          const control = ${select(selector)};
          if (!control?.getClientRects().length || control.disabled) throw Error('Control unavailable');
          control.click();
        })()`);
      }

      function fill(selector, value) {
        return evaluate(`(() => {
          const control = ${select(selector)};
          if (!control?.getClientRects().length || control.disabled) throw Error('Control unavailable');
          control.value = ${JSON.stringify(value)};
          control.dispatchEvent(new Event('input', {bubbles: true}));
          control.dispatchEvent(new Event('change', {bubbles: true}));
          if (String(control.value) !== ${JSON.stringify(value)}) throw Error('Value not applied');
        })()`);
      }

      return {pageErrors, evaluate, waitFor, navigate, setCookie, click, fill, width};
    }
    return {version: version.product, newPage, close};
  } catch (error) {
    await close();
    throw error;
  }
}
