import type {
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
  BrandingManifest,
  CapabilitySet,
  Freshness,
  InstanceMeta,
  ProblemDetails,
  Repository,
  Session,
  Viewer,
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

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers,
  });

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

export const hubgitApi = {
  meta: () => apiFetch<InstanceMeta>('/api/v1/meta'),
  capabilities: () => apiFetch<CapabilitySet>('/api/v1/capabilities'),
  session: () => apiFetch<Session>('/api/v1/auth/session'),
  repositories: (query = '') =>
    apiFetch<RepositoryPage>(
      `/api/v1/repositories${query ? `?q=${encodeURIComponent(query)}` : ''}`,
    ),
  repository: (owner: string, repo: string) =>
    apiFetch<Repository>(
      `/api/v1/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`,
    ),
  tree: (owner: string, repo: string, ref: string, path = '') => {
    const query = path ? `?path=${encodeURIComponent(path)}` : '';
    return apiFetch<CacheAwareGitTree>(
      `/api/v1/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/tree/${encodeURIComponent(ref)}${query}`,
    );
  },
  login: (login: string, password: string) =>
    apiFetch<Session>('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, password }),
    }),
  logout: (csrfToken: string) =>
    apiFetch<void>('/api/v1/auth/session', {
      method: 'DELETE',
      headers: { 'X-CSRF-Token': csrfToken },
    }),
};

export const queryKeys = {
  meta: ['meta'] as const,
  capabilities: ['capabilities'] as const,
  session: ['session'] as const,
  repositories: (query = '') => ['repositories', query] as const,
  repository: (owner: string, repo: string) =>
    ['repository', owner, repo] as const,
  tree: (owner: string, repo: string, ref: string, path = '') =>
    ['tree', owner, repo, ref, path] as const,
};
