/*
 * AUD-1 qualification adapter for the existing browser journey.
 *
 * The canonical journey predates the one-time launch capability and expects
 * `/api/bootstrap` to disclose an operator token. Rather than reintroducing
 * that authority leak, this test-only loader makes three narrow substitutions:
 * capture the real launch URL printed by the child Station, navigate through
 * that URL once, and rely on the resulting HttpOnly cookie for later API reads.
 * Every expected source fragment is asserted so drift fails closed.
 */
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');

const filename = path.join(__dirname, 'browser.cjs');
let source = fs.readFileSync(filename, 'utf8');

function replaceOnce(needle, replacement, label) {
  const first = source.indexOf(needle);
  if (first < 0 || source.indexOf(needle, first + needle.length) >= 0) {
    throw new Error(`AUD-1 browser adapter expected exactly one ${label} fragment`);
  }
  source = source.slice(0, first) + replacement + source.slice(first + needle.length);
}

replaceOnce(
  'const errors=[],checks=[];let browser;',
  'const errors=[],checks=[];let browser,launchUrl;',
  'browser state',
);
replaceOnce(
  "server.stdout.on('data',b=>{text+=b;if(text.includes('Press Ctrl+C')){clearTimeout(timer);resolve();}});",
  "server.stdout.on('data',b=>{text+=b;const match=text.match(/Open (https?:\\/\\/\\S+\\/auth\\/\\S+)/);if(match)launchUrl=match[1];if(text.includes('Press Ctrl+C')){if(!launchUrl)return reject(Error('Server did not print one-time launch URL'));clearTimeout(timer);resolve();}});",
  'startup capture',
);
replaceOnce(
  'await page.goto(url);',
  'await page.goto(launchUrl);',
  'initial navigation',
);
replaceOnce(
  "await page.waitForFunction(async()=>{const b=await fetch('/api/bootstrap').then(r=>r.json());const r=await fetch('/api/projects',{headers:{'X-Station-Token':b.token}}).then(r=>r.json());return r.projects[0]?.tasks.every(t=>t.state==='integrated');},{},{timeout:45000});",
  "await page.waitForFunction(async()=>{const r=await fetch('/api/projects').then(r=>r.json());return r.projects[0]?.tasks.every(t=>t.state==='integrated');},{},{timeout:45000});",
  'cookie-authenticated project polling',
);

const loaded = new Module(filename, module);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(source, filename);
