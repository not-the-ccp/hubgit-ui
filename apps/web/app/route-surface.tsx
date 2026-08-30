import { useQuery } from '@tanstack/react-query';
import { useLocation, useRouteLoaderData } from 'react-router';

import { HubGitApp } from '../components/hubgit-app';
import type { BootstrapData } from './lib/bootstrap';
import { toHubGitAppData } from './lib/bootstrap';
import { ApiProblem, hubgitApi, queryKeys } from './lib/api-client';

export function RouteSurface() {
  const location = useLocation();
  const bootstrap = useRouteLoaderData<BootstrapData>('root');
  const appData = bootstrap
    ? toHubGitAppData(bootstrap, `${location.pathname}${location.search}`)
    : undefined;
  const [owner, repo] = location.pathname.split('/').filter(Boolean);
  const reserved = new Set([
    'orgs',
    'settings',
    'search',
    'auth',
    'login',
    'join',
    'issues',
    'pulls',
    'notifications',
  ]);
  const repositoryRoute = Boolean(owner && repo && !reserved.has(owner));
  const repository = useQuery({
    queryKey: queryKeys.repository(owner ?? '', repo ?? ''),
    queryFn: () => hubgitApi.repository(owner ?? '', repo ?? ''),
    enabled: repositoryRoute,
  });
  const tree = useQuery({
    queryKey: queryKeys.tree(
      owner ?? '',
      repo ?? '',
      repository.data?.defaultBranch ?? '',
    ),
    queryFn: () =>
      hubgitApi.tree(
        owner ?? '',
        repo ?? '',
        repository.data?.defaultBranch ?? '',
      ),
    enabled: repositoryRoute && Boolean(repository.data?.defaultBranch),
  });

  if (!bootstrap || !appData) {
    return (
      <main className="error-page" role="alert">
        <span className="error-code">503</span>
        <h1>HubGit is temporarily unavailable</h1>
        <p>
          {bootstrap?.message ??
            'The instance metadata could not be loaded. Check the API service and try again.'}
        </p>
        <a className="primary-button" href={location.pathname}>
          Retry
        </a>
      </main>
    );
  }

  if (repositoryRoute && (repository.isPending || tree.isPending)) {
    return (
      <main className="error-page" aria-busy="true">
        <span className="error-code">···</span>
        <h1>Loading repository</h1>
        <p>Fetching repository permissions, default branch, and tree data.</p>
      </main>
    );
  }

  if (repositoryRoute && (repository.error || tree.error)) {
    const concealed =
      repository.error instanceof ApiProblem &&
      repository.error.problem.status === 404;
    return (
      <main className="error-page" role="alert">
        <span className="error-code">{concealed ? '404' : '503'}</span>
        <h1>{concealed ? 'Repository not found' : 'Repository unavailable'}</h1>
        <p>
          {concealed
            ? 'The repository does not exist or your account cannot access it.'
            : 'The provider could not return repository data. Try again shortly.'}
        </p>
        <a className="primary-button" href={location.pathname}>
          Retry
        </a>
      </main>
    );
  }

  return (
    <HubGitApp
      initialPath={location.pathname}
      initialBranding={appData.branding}
      authProfile={appData.auth}
      freshness={appData.freshness}
      repositoryView={
        repository.data && tree.data
          ? { repository: repository.data, tree: tree.data }
          : undefined
      }
    />
  );
}
