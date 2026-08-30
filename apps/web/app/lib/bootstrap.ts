import type {
  AuthMethods,
  BrandingManifest,
  CapabilitySet,
  Freshness,
  InstanceMeta,
  Session,
} from '@hubgit/contracts';

import { ApiProblem, createHubgitApi } from './api-client';

export type BootstrapData = {
  state: 'ready' | 'degraded' | 'provider-down';
  meta?: InstanceMeta;
  capabilities?: CapabilitySet;
  authMethods?: AuthMethods;
  session?: Session;
  message?: string;
};

export type AppAuth = {
  id: 'mock-local' | 'github-provider';
  mode: 'local' | 'provider';
  label: string;
  providerName?: string;
  authorizationPath?: string;
};

export type HubGitAppData = {
  branding: BrandingManifest;
  auth: AppAuth;
  freshness?: Freshness;
};

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'The HubGit service is unavailable.';
}

function isServiceFailure(error: unknown) {
  return (
    error instanceof TypeError ||
    (error instanceof ApiProblem && error.problem.status >= 500)
  );
}

/** Load the stable shell boundary while allowing optional probes to degrade. */
export async function loadBootstrap(request: Request): Promise<BootstrapData> {
  const api = createHubgitApi({ request });
  const [meta, capabilities, authMethods, session] = await Promise.allSettled([
    api.meta(),
    api.capabilities(),
    api.authMethods(),
    api.session(),
  ]);

  if (meta.status === 'rejected') {
    return {
      state: isServiceFailure(meta.reason) ? 'provider-down' : 'degraded',
      message: errorMessage(meta.reason),
    };
  }

  const optionalFailures = [capabilities, authMethods, session].filter(
    (result): result is PromiseRejectedResult => result.status === 'rejected',
  );

  return {
    state: optionalFailures.length ? 'degraded' : 'ready',
    meta: meta.value,
    capabilities:
      capabilities.status === 'fulfilled' ? capabilities.value : undefined,
    authMethods:
      authMethods.status === 'fulfilled' ? authMethods.value : undefined,
    session: session.status === 'fulfilled' ? session.value : undefined,
    message: optionalFailures.length
      ? errorMessage(optionalFailures[0].reason)
      : undefined,
  };
}

/** Adapt API contracts to the presentation shell without leaking provider DTOs. */
export function toHubGitAppData(
  bootstrap: BootstrapData,
  returnTo: string,
): HubGitAppData | undefined {
  if (!bootstrap.meta) return undefined;

  const provider = bootstrap.authMethods?.providers?.find(
    (item) => item.enabled,
  );
  const auth: AppAuth = provider
    ? {
        id: 'github-provider',
        mode: 'provider',
        label: provider.displayName,
        providerName: provider.displayName,
        authorizationPath: `/api/v1/auth/providers/${encodeURIComponent(provider.id)}/start?returnTo=${encodeURIComponent(returnTo)}`,
      }
    : {
        id: 'mock-local',
        mode: 'local',
        label: 'Local account',
      };

  return {
    branding: bootstrap.meta.branding,
    auth,
    freshness: bootstrap.meta.freshness,
  };
}

export type RouteFailure =
  | 'concealed'
  | 'unauthenticated'
  | 'provider-down'
  | 'error';

export function mapRouteFailure(error: unknown): RouteFailure {
  if (error instanceof ApiProblem) {
    if (error.problem.status === 404) return 'concealed';
    if (error.problem.status === 401) return 'unauthenticated';
    if (error.problem.status >= 500) return 'provider-down';
  }
  if (error instanceof TypeError) return 'provider-down';
  return 'error';
}
