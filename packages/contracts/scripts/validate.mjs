import { readFile } from 'node:fs/promises';

const specUrl = new URL('../openapi.json', import.meta.url);
const spec = JSON.parse(await readFile(specUrl, 'utf8'));
const failures = [];

if (spec.openapi !== '3.1.0') failures.push('openapi must be 3.1.0');
if (!spec.info?.title || !spec.info?.version) failures.push('info is incomplete');
if (!spec.paths || Object.keys(spec.paths).length < 30) failures.push('expected at least 30 paths');
if (!spec.components?.schemas?.ProblemDetails) failures.push('ProblemDetails is required');
if (!spec.components?.schemas?.PageInfo) failures.push('PageInfo is required');

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

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`Validated ${Object.keys(spec.paths).length} paths and ${Object.keys(spec.components.schemas).length} schemas.`);
