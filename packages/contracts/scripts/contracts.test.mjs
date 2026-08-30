import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const spec = JSON.parse(await readFile(new URL('../openapi.json', import.meta.url), 'utf8'));

test('OpenAPI contract has the bounded foundation', () => {
  assert.equal(spec.openapi, '3.1.0');
  assert.equal(Array.isArray(spec.paths), false);
  assert.ok(spec.paths['/api/v1/auth/providers/{provider}/start']);
  assert.ok(spec.paths['/api/v1/auth/providers/{provider}/callback']);
  assert.ok(spec.paths['/api/v1/repositories/{owner}/{repo}/settings/cache']);
  assert.ok(spec.components.schemas.Freshness);
  assert.equal(spec.components.schemas.InstanceMeta.properties.branding.$ref, '#/components/schemas/BrandingManifest');
});

test('all references resolve locally', () => {
  const unresolved = [];
  const visit = (value, location = '#') => {
    if (!value || typeof value !== 'object') return;
    if (typeof value.$ref === 'string' && value.$ref.startsWith('#/')) {
      const found = value.$ref.slice(2).split('/').reduce((current, key) => current?.[key.replaceAll('~1', '/').replaceAll('~0', '~')], spec);
      if (found === undefined) unresolved.push(`${location}: ${value.$ref}`);
    }
    for (const [key, child] of Object.entries(value)) visit(child, `${location}/${key}`);
  };
  visit(spec);
  assert.deepEqual(unresolved, []);
});
