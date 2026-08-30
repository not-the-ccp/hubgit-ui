import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const load = (name) => readFile(new URL(`scenarios/${name}.json`, root), 'utf8').then(JSON.parse);

test('fixture scenarios are deterministic and complete', async () => {
  const names = ['users', 'repositories', 'collaboration', 'failures'];
  const scenarios = await Promise.all(names.map(load));
  assert.deepEqual(scenarios.map((scenario) => scenario.scenario), names.map((name) => name === 'failures' ? 'failure-states' : name));
  assert.ok(scenarios.every((scenario) => scenario.asOf === '2026-01-15T12:00:00Z'));
});

test('failure fixtures preserve status and problem code', async () => {
  const failures = await load('failures');
  for (const item of failures.cases) {
    assert.equal(item.status, item.problem.status, item.name);
    assert.match(item.problem.code, /^[a-z][a-z0-9_.-]+$/);
  }
});
