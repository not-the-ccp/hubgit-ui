import { readFile } from 'node:fs/promises';

const specUrl = new URL('../openapi.json', import.meta.url);
const spec = JSON.parse(await readFile(specUrl, 'utf8'));
const failures = [];

if (spec.openapi !== '3.1.0') failures.push('openapi must be 3.1.0');
if (!spec.info?.title || !spec.info?.version) failures.push('info is incomplete');
if (!spec.paths || Array.isArray(spec.paths)) failures.push('paths must be an OpenAPI path-item object');
if (!spec.paths || Object.keys(spec.paths).length < 30) failures.push('expected at least 30 paths');
if (!spec.components?.schemas?.ProblemDetails) failures.push('ProblemDetails is required');
if (!spec.components?.schemas?.PageInfo) failures.push('PageInfo is required');
if (!spec.components?.schemas?.Freshness) failures.push('Freshness is required');
if (!spec.components?.schemas?.BrandingManifest) failures.push('BrandingManifest is required');
if (spec.components?.schemas?.InstanceMeta?.properties?.branding?.$ref !== '#/components/schemas/BrandingManifest') failures.push('InstanceMeta.branding must use BrandingManifest');
if (!spec.paths?.['/api/v1/auth/providers/{provider}/start'] || !spec.paths?.['/api/v1/auth/providers/{provider}/callback']) failures.push('provider-neutral auth start/callback paths are required');
if (!spec.paths?.['/api/v1/repositories/{owner}/{repo}/settings/cache']) failures.push('repository cache settings path is required');

const resolveRef = (ref) => {
  if (!ref.startsWith('#/')) return undefined;
  return ref.slice(2).split('/').reduce((value, key) => value?.[key.replaceAll('~1', '/').replaceAll('~0', '~')], spec);
};

const visit = (value, location = '#') => {
  if (!value || typeof value !== 'object') return;
  if (typeof value.$ref === 'string' && !resolveRef(value.$ref)) {
    failures.push(`unresolved $ref at ${location}: ${value.$ref}`);
  }
  for (const [key, child] of Object.entries(value)) visit(child, `${location}/${key}`);
};
visit(spec);

for (const [path, item] of Object.entries(spec.paths ?? {})) {
  if (!path.startsWith('/api/v1')) failures.push(`path outside /api/v1: ${path}`);
  for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
    const operation = item[method];
    if (!operation) continue;
    if (!operation.operationId) failures.push(`${method.toUpperCase()} ${path} has no operationId`);
    if (!operation.responses) failures.push(`${method.toUpperCase()} ${path} has no responses`);
  }
}

const hasRefParameter = (operation, name) => (operation.parameters ?? []).some((parameter) => parameter.$ref === `#/components/parameters/${name}`);
const retrySensitive = new Set(['createRepository', 'createIssue', 'createIssueComment', 'createPullRequest', 'submitPullRequestReview', 'mergePullRequest', 'createRelease', 'createDiscussion', 'createWikiPage', 'createProject', 'dispatchWorkflow', 'createWebhook', 'invalidateRepositoryCache']);
for (const [path, item] of Object.entries(spec.paths ?? {})) for (const [method, operation] of Object.entries(item)) {
  if (!['get', 'post', 'put', 'patch', 'delete'].includes(method) || !operation?.operationId) continue;
  if (retrySensitive.has(operation.operationId) && !hasRefParameter(operation, 'IdempotencyKey')) failures.push(`${operation.operationId} must require Idempotency-Key`);
  if (['updateIssue', 'updatePullRequest', 'replaceRepositoryAccess', 'updateRepositoryCachePolicy'].includes(operation.operationId) && !hasRefParameter(operation, 'IfMatch')) failures.push(`${operation.operationId} must require If-Match`);
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`Validated ${Object.keys(spec.paths).length} paths and ${Object.keys(spec.components.schemas).length} schemas.`);
