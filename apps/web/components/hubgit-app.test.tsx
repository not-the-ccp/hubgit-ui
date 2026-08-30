import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('HubGit authentication presentation', () => {
  it('keeps the provider profile redirect-only and free of credential fields', () => {
    const source = readFileSync(
      resolve(import.meta.dirname, 'hubgit-app.tsx'),
      'utf8',
    );
    expect(source).toContain("id: 'github-provider'");
    expect(source).toContain(
      "authorizationPath: '/auth/github/start?returnTo=%2Fdashboard'",
    );
    expect(source).toContain('Continue with {branding.auth.providerName}');
    expect(source).toContain('HubGit does not ask for, see, or store');
    expect(source).not.toContain('GitHub password');
  });
});
