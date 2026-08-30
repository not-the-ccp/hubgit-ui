import { useLocation } from 'react-router';

import { HubGitApp } from '../components/hubgit-app';

export function RouteSurface() {
  const location = useLocation();
  return <HubGitApp initialPath={location.pathname} />;
}

