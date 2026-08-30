import { useLocation, useRouteLoaderData } from 'react-router';

import { HubGitApp } from '../components/hubgit-app';
import type { BootstrapData } from './lib/bootstrap';
import { toHubGitAppData } from './lib/bootstrap';

export function RouteSurface() {
  const location = useLocation();
  const bootstrap = useRouteLoaderData<BootstrapData>('root');
  const appData = bootstrap
    ? toHubGitAppData(bootstrap, `${location.pathname}${location.search}`)
    : undefined;

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

  return (
    <HubGitApp
      initialPath={location.pathname}
      initialBranding={appData.branding}
      authProfile={appData.auth}
      freshness={appData.freshness}
    />
  );
}
