import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const spec = JSON.parse(
  await readFile(new URL('../openapi.json', import.meta.url), 'utf8'),
);
const generated = await readFile(
  new URL('../src/generated-client.ts', import.meta.url),
  'utf8',
);

test('OpenAPI contract has the bounded foundation', () => {
  assert.equal(spec.openapi, '3.1.0');
  assert.equal(Array.isArray(spec.paths), false);
  assert.ok(spec.paths['/api/v1/auth/providers/{provider}/start']);
  assert.ok(spec.paths['/api/v1/auth/providers/{provider}/callback']);
  assert.ok(spec.paths['/api/v1/repositories/{owner}/{repo}/settings/cache']);
  assert.ok(spec.components.schemas.Freshness);
  assert.equal(
    spec.components.schemas.InstanceMeta.properties.branding.$ref,
    '#/components/schemas/BrandingManifest',
  );
});

test('all references resolve locally', () => {
  const unresolved = [];
  const visit = (value, location = '#') => {
    if (!value || typeof value !== 'object') return;
    if (typeof value.$ref === 'string' && value.$ref.startsWith('#/')) {
      const found = value.$ref
        .slice(2)
        .split('/')
        .reduce(
          (current, key) =>
            current?.[key.replaceAll('~1', '/').replaceAll('~0', '~')],
          spec,
        );
      if (found === undefined) unresolved.push(`${location}: ${value.$ref}`);
    }
    for (const [key, child] of Object.entries(value))
      visit(child, `${location}/${key}`);
  };
  visit(spec);
  assert.deepEqual(unresolved, []);
});

test('generated operations resolve response, parameter, and body references', () => {
  for (const expected of [
    'export type getMetaOutput = InstanceMeta;',
    'export type getCapabilitiesOutput = CapabilitySet;',
    'export type getSessionOutput = Session;',
    'export type loginOutput = Session;',
    'export type listRepositoriesOutput = RepositoryPage;',
    'export type getRepositoryOutput = Repository;',
    'export type getTreeOutput = GitTree;',
    'export type updateRepositoryCachePolicyOutput = RepositoryCache;',
    'body: LoginRequest;',
    'body: RepositoryCachePolicy;',
    '"number": number;',
    '"X-CSRF-Token": string;',
    '"Idempotency-Key": string;',
  ]) {
    assert.ok(
      generated.includes(expected),
      `missing generated fragment: ${expected}`,
    );
  }
  assert.ok(
    generated.includes('input, "application/merge-patch+json"'),
    'merge-patch request bodies must retain their media type',
  );
  assert.ok(
    generated.includes('export class HubGitRequestError extends Error'),
  );
  assert.equal(
    generated.includes(
      'async getMeta(input: RequestControl): Promise<ApiResponse<void>>',
    ),
    false,
  );
});
