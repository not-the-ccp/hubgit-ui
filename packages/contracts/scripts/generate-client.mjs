import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = new URL('../', import.meta.url);
const spec = JSON.parse(await readFile(new URL('openapi.json', root), 'utf8'));
const outputUrl = new URL('../src/generated-client.ts', import.meta.url);

const refName = (ref) => ref?.split('/').pop();
const resolvePointer = (ref) => {
  if (!ref?.startsWith('#/')) return undefined;
  return ref
    .slice(2)
    .split('/')
    .reduce(
      (current, key) =>
        current?.[key.replaceAll('~1', '/').replaceAll('~0', '~')],
      spec,
    );
};
const dereference = (value) => {
  let current = value;
  const seen = new Set();
  while (current?.$ref) {
    if (seen.has(current.$ref))
      throw new Error(`Circular reference: ${current.$ref}`);
    seen.add(current.$ref);
    current = resolvePointer(current.$ref);
  }
  return current;
};
const tsType = (schema = {}) => {
  if (schema.$ref) return refName(schema.$ref);
  if (schema.const !== undefined) return JSON.stringify(schema.const);
  if (schema.enum)
    return schema.enum.map((value) => JSON.stringify(value)).join(' | ');
  if (schema.oneOf) return schema.oneOf.map(tsType).join(' | ');
  if (schema.allOf) return schema.allOf.map(tsType).join(' & ');
  if (Array.isArray(schema.type))
    return schema.type.map((type) => tsType({ ...schema, type })).join(' | ');
  if (schema.type === 'array') return `Array<${tsType(schema.items)}>`;
  if (schema.type === 'object' || schema.properties) {
    const required = new Set(schema.required ?? []);
    const fields = Object.entries(schema.properties ?? {}).map(
      ([name, value]) =>
        `  ${JSON.stringify(name)}${required.has(name) ? '' : '?'}: ${tsType(value)};`,
    );
    if (schema.additionalProperties)
      fields.push(
        `  [key: string]: ${schema.additionalProperties === true ? 'unknown' : tsType(schema.additionalProperties)};`,
      );
    return fields.length
      ? `{\n${fields.join('\n')}\n}`
      : 'Record<string, unknown>';
  }
  if (schema.type === 'null') return 'null';
  if (schema.type === 'integer' || schema.type === 'number') return 'number';
  if (schema.type === 'boolean') return 'boolean';
  return 'string';
};

const responseType = (operation) => {
  const response = Object.entries(operation.responses ?? {}).find(([status]) =>
    /^2/.test(status),
  )?.[1];
  const success = dereference(response);
  const content = success?.content ?? {};
  const schema =
    content['application/json']?.schema ?? Object.values(content)[0]?.schema;
  return schema ? tsType(schema) : 'void';
};

const operationParameters = (item, operation) =>
  [...(item.parameters ?? []), ...(operation.parameters ?? [])].map(
    dereference,
  );

const requestBodyInfo = (operation) => {
  const requestBody = dereference(operation.requestBody);
  if (!requestBody?.content) return undefined;
  const selected = requestBody.content['application/json']
    ? ['application/json', requestBody.content['application/json']]
    : Object.entries(requestBody.content)[0];
  if (!selected) return undefined;
  return {
    required: Boolean(requestBody.required),
    mediaType: selected[0],
    schema: selected[1].schema,
  };
};

const operationInput = (item, operation) => {
  const parameters = operationParameters(item, operation);
  const fields = [];
  for (const parameter of parameters.filter((value) => value.in === 'path')) {
    fields.push(
      `  ${JSON.stringify(parameter.name)}: ${tsType(parameter.schema)};`,
    );
  }
  for (const location of ['query', 'header']) {
    const located = parameters.filter((value) => value.in === location);
    if (!located.length) continue;
    const required = located.some((value) => value.required);
    const entries = located.map(
      (parameter) =>
        `    ${JSON.stringify(parameter.name)}${parameter.required ? '' : '?'}: ${tsType(parameter.schema)};`,
    );
    const property = location === 'header' ? 'headers' : 'query';
    fields.push(
      `  ${property}${required ? '' : '?'}: {\n${entries.join('\n')}\n  };`,
    );
  }
  const body = requestBodyInfo(operation);
  if (body?.schema) {
    fields.push(`  body${body.required ? '' : '?'}: ${tsType(body.schema)};`);
  }
  return fields.length
    ? `{\n${fields.join('\n')}\n} & RequestControl`
    : 'RequestControl';
};

const operations = [];
for (const [path, item] of Object.entries(spec.paths ?? {})) {
  for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
    const operation = item[method];
    if (!operation) continue;
    operations.push({ path, method, operation, item });
  }
}

const schemaTypes = Object.entries(spec.components?.schemas ?? {})
  .map(([name, schema]) => `export type ${name} = ${tsType(schema)};`)
  .join('\n\n');

const operationTypes = operations
  .map(({ item, operation }) => {
    return `export type ${operation.operationId}Input = ${operationInput(item, operation)};\nexport type ${operation.operationId}Output = ${responseType(operation)};`;
  })
  .join('\n\n');

const methods = operations
  .map(({ path, method, operation }) => {
    const mediaType = requestBodyInfo(operation)?.mediaType;
    return `  async ${operation.operationId}(input: ${operation.operationId}Input): Promise<ApiResponse<${operation.operationId}Output>> {\n    return this.request<${operation.operationId}Output>(${JSON.stringify(path)}, ${JSON.stringify(method.toUpperCase())}, input${mediaType ? `, ${JSON.stringify(mediaType)}` : ''});\n  }`;
  })
  .join('\n\n');

const output = `/* eslint-disable */
/**
 * Generated from ../openapi.json by scripts/generate-client.mjs.
 * Do not edit this file directly; run pnpm generate after changing the contract.
 */

export interface RequestControl {
  signal?: AbortSignal;
  credentials?: RequestCredentials;
}

export interface RequestOptions extends RequestControl {
  body?: unknown;
  headers?: Record<string, string>;
  query?: Record<string, string | number | boolean | undefined>;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  headers: Headers;
}

export class HubGitRequestError extends Error {
  constructor(
    readonly response: Response,
    readonly problem: ProblemDetails | unknown,
  ) {
    super(\`HubGit request failed with \${response.status}\`);
    this.name = 'HubGitRequestError';
  }
}

${schemaTypes}

${operationTypes}

export class HubGitClient {
  constructor(private readonly baseUrl: string, private readonly fetchImpl: typeof fetch = fetch) {}

  private async request<T>(template: string, method: string, input: RequestOptions, contentType = 'application/json'): Promise<ApiResponse<T>> {
    const path = template.replace(/\\{([^}]+)\\}/g, (_, key) => encodeURIComponent(String((input as Record<string, unknown>)[key])));
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(input.query ?? {})) if (value !== undefined) query.set(key, String(value));
    const url = new URL(path + (query.size ? \`?\${query}\` : ''), this.baseUrl);
    const response = await this.fetchImpl(url, { method, credentials: input.credentials ?? 'include', headers: { Accept: 'application/json', ...(input.body === undefined ? {} : { 'Content-Type': contentType }), ...input.headers }, body: input.body === undefined ? undefined : JSON.stringify(input.body), signal: input.signal });
    const responseContentType = response.headers.get('content-type') ?? '';
    const data = response.status === 204 ? undefined as T : responseContentType.includes('json') ? await response.json() as T : await response.text() as T;
    if (!response.ok) throw new HubGitRequestError(response, data);
    return { data, status: response.status, headers: response.headers };
  }

${methods}
}
`;

if (process.argv.includes('--check')) {
  const current = await readFile(outputUrl, 'utf8').catch(() => '');
  if (current !== output) {
    console.error(`${fileURLToPath(outputUrl)} is stale; run pnpm generate`);
    process.exit(1);
  }
} else {
  await mkdir(new URL('../src/', import.meta.url), { recursive: true });
  await writeFile(outputUrl, output);
}
