import { describe, expect, it } from 'vitest';

import type { BootstrapData } from './bootstrap';
import { toHubGitAppData } from './bootstrap';
import { createHubgitApi } from './api-client';

const branding = {
  preset: 'family-forge',
  productName: 'Family Forge',
  shortName: 'Forge',
  logoUrl: null,
  faviconUrl: null,
  titleTemplate: '%s · Family Forge',
  colors: { accent: '#123456', headerBackground: '#ffffff' },
  authentication: {
    heading: 'Connect',
    description: 'Private installation',
    connectLabel: 'Continue to provider',
  },
  links: { privacy: null, terms: null, source: null, support: null },
  notice: null,
  providerDisplayNames: { github: 'Source provider' },
} as const;

describe('provider-neutral application bootstrap', () => {
  it('maps an enabled provider to the redirect-only auth profile', () => {
    const bootstrap: BootstrapData = {
      state: 'ready',
      meta: {
        name: 'Family Forge',
        baseUrl: 'http://localhost:8000',
        branding,
        registrationEnabled: false,
      },
      authMethods: {
        password: false,
        passkey: false,
        twoFactor: false,
        providers: [
          {
            id: 'github',
            displayName: 'Source provider',
            enabled: true,
          },
        ],
      },
    };

    expect(toHubGitAppData(bootstrap, '/dashboard?tab=for-you')).toMatchObject({
      branding: { productName: 'Family Forge' },
      auth: {
        mode: 'provider',
        providerName: 'Source provider',
        authorizationPath:
          '/api/v1/auth/providers/github/start?redirectUri=%2Fdashboard%3Ftab%3Dfor-you',
      },
    });
  });

  it('preserves the incoming cookie and request origin during SSR', async () => {
    let observedUrl = '';
    let observedCookie: string | null = null;
    const fakeFetch = (async (input, init) => {
      observedUrl =
        input instanceof Request
          ? input.url
          : input instanceof URL
            ? input.href
            : input;
      observedCookie = new Headers(init?.headers).get('cookie');
      return new Response(
        JSON.stringify({
          name: 'Family Forge',
          baseUrl: 'http://localhost:8000',
          branding,
          registrationEnabled: false,
        }),
        { headers: { 'Content-Type': 'application/json' } },
      );
    }) satisfies typeof fetch;

    const api = createHubgitApi({
      request: new Request('http://localhost:3000/dashboard', {
        headers: { Cookie: 'hubgit_session=opaque' },
      }),
      fetchImplementation: fakeFetch,
    });
    const meta = await api.meta();

    expect(meta.branding.productName).toBe('Family Forge');
    expect(observedUrl).toBe('http://localhost:3000/api/v1/meta');
    expect(observedCookie).toBe('hubgit_session=opaque');
  });
});
