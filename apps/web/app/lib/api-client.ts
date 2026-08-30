export interface BrandingManifest {
  productName: string;
  shortName: string;
  logoUrl: string | null;
  faviconUrl: string;
  titleTemplate: string;
  colors: {
    accent: string;
    headerBackground: string;
  };
  authentication: {
    heading: string;
    description: string;
    connectLabel: string;
  };
  links: {
    privacy: string | null;
    terms: string | null;
    source: string | null;
    support: string | null;
  };
  notice: string | null;
}

export interface Freshness {
  state: 'live' | 'refreshing' | 'stale' | 'offline';
  lastSyncedAt: string | null;
  lastAuthorizedAt: string | null;
  provider: string;
}

export interface InstanceMeta {
  name: string;
  baseUrl: string;
  version: string;
  provider?: string;
  registrationEnabled: boolean;
  branding: string | BrandingManifest;
}

export interface CapabilityDocument {
  provider: string;
  version: string;
  features: Record<string, boolean>;
  limits: Record<string, number>;
}

export interface Viewer {
  id: string;
  username: string;
  displayName: string;
  email?: string;
  avatarUrl: string;
  roles: string[];
}

export interface Session {
  authenticated: boolean;
  csrfToken: string;
  expiresAt: string | null;
  viewer: Viewer | null;
}

export interface RepositoryOwner {
  id: string;
  kind: 'user' | 'organization';
  login: string;
  avatarUrl: string;
}

export interface Repository {
  id: string;
  kind: 'repository';
  owner: RepositoryOwner;
  name: string;
  fullName: string;
  description: string;
  visibility: 'public' | 'private' | 'internal';
  defaultBranch: string;
  empty: boolean;
  archived: boolean;
  language: string | null;
  topics: string[];
  permissions: Record<string, boolean>;
  counts: {
    stars: number;
    forks: number;
    watchers: number;
    issues: number;
    pullRequests: number;
  };
  freshness?: Freshness;
}

export interface TreeEntry {
  name: string;
  path: string;
  kind: 'file' | 'directory' | 'symlink' | 'submodule';
  sha: string;
  size: number | null;
}

export interface GitTree {
  sha: string;
  ref: string;
  path: string;
  entries: TreeEntry[];
  freshness?: Freshness;
}

export interface Page<T> {
  items: T[];
  pageInfo: {
    startCursor: string | null;
    endCursor: string | null;
    hasNextPage: boolean;
    hasPreviousPage: boolean;
  };
  totalCount?: number;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  code: string;
  detail?: string;
  instance?: string;
  fieldErrors?: Array<{ field: string; code: string; message: string }>;
}

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
  capabilities: () => apiFetch<CapabilityDocument>('/api/v1/capabilities'),
  session: () => apiFetch<Session>('/api/v1/auth/session'),
  repositories: (query = '') =>
    apiFetch<Page<Repository>>(`/api/v1/repositories${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  repository: (owner: string, repo: string) =>
    apiFetch<Repository>(`/api/v1/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`),
  tree: (owner: string, repo: string, ref: string, path = '') => {
    const query = path ? `?path=${encodeURIComponent(path)}` : '';
    return apiFetch<GitTree>(
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
  repository: (owner: string, repo: string) => ['repository', owner, repo] as const,
  tree: (owner: string, repo: string, ref: string, path = '') =>
    ['tree', owner, repo, ref, path] as const,
};
