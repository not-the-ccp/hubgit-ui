import type {
  AuthMethods,
  BrandingManifest,
  CapabilitySet,
  Freshness,
  GitTree,
  InstanceMeta,
  ProblemDetails,
  Repository,
  RepositoryPage,
  Session,
  Viewer,
} from '@hubgit/contracts';

export type {
  AuthMethods,
  BrandingManifest,
  CapabilitySet,
  Freshness,
  InstanceMeta,
  ProblemDetails,
  Repository,
  Session,
  Viewer,
};

export type ApiClientOptions = {
  /** Incoming loader request used to preserve the session during SSR. */
  request?: Request;
  fetchImplementation?: typeof fetch;
};

export type CacheAwareGitTree = GitTree & { freshness?: Freshness };

export class ApiProblem extends Error {
  readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail ?? problem.title);
    this.name = 'ApiProblem';
    this.problem = problem;
  }
}

function apiUrl(path: string, request?: Request) {
  if (typeof window === 'undefined' && request) {
    return new URL(path, request.url).toString();
  }
  return path;
}

async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  options: ApiClientOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');
  const cookie = options.request?.headers.get('cookie');
  if (cookie && !headers.has('Cookie')) headers.set('Cookie', cookie);
  const response = await (options.fetchImplementation ?? fetch)(
    apiUrl(path, options.request),
    {
      ...init,
      credentials: 'include',
      headers,
    },
  );

  if (!response.ok) {
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/problem+json')) {
      throw new ApiProblem((await response.json()) as ProblemDetails);
    }
    throw new ApiProblem({
      type: 'about:blank',
      title: response.statusText || 'Request failed',
      status: response.status,
      code: 'http.request_failed',
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function createHubgitApi(options: ApiClientOptions = {}) {
  return {
    meta: () => apiFetch<InstanceMeta>('/api/v1/meta', {}, options),
    capabilities: () =>
      apiFetch<CapabilitySet>('/api/v1/capabilities', {}, options),
    authMethods: () =>
      apiFetch<AuthMethods>('/api/v1/auth/methods', {}, options),
    session: () => apiFetch<Session>('/api/v1/auth/session', {}, options),
    repositories: (query = '') =>
      apiFetch<RepositoryPage>(
        `/api/v1/repositories${query ? `?q=${encodeURIComponent(query)}` : ''}`,
        {},
        options,
      ),
    repository: (owner: string, repo: string) =>
      apiFetch<Repository>(
        `/api/v1/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`,
        {},
        options,
      ),
    tree: (owner: string, repo: string, ref: string, path = '') => {
      const query = path ? `?path=${encodeURIComponent(path)}` : '';
      return apiFetch<CacheAwareGitTree>(
        `/api/v1/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/tree/${encodeURIComponent(ref)}${query}`,
        {},
        options,
      );
    },
    login: (login: string, password: string) =>
      apiFetch<Session>(
        '/api/v1/auth/login',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ login, password }),
        },
        options,
      ),
    logout: (csrfToken: string) =>
      apiFetch<void>(
        '/api/v1/auth/session',
        {
          method: 'DELETE',
          headers: { 'X-CSRF-Token': csrfToken },
        },
        options,
      ),
  };
}

export const hubgitApi = createHubgitApi();

export const queryKeys = {
  meta: ['meta'] as const,
  capabilities: ['capabilities'] as const,
  authMethods: ['authMethods'] as const,
  session: ['session'] as const,
  repositories: (query = '') => ['repositories', query] as const,
  repository: (owner: string, repo: string) =>
    ['repository', owner, repo] as const,
  tree: (owner: string, repo: string, ref: string, path = '') =>
    ['tree', owner, repo, ref, path] as const,
};
