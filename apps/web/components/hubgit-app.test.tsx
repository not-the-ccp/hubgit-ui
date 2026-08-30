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
      "'/api/v1/auth/providers/github/start?returnTo=%2Fdashboard'",
    );
    expect(source).toContain('{branding.authentication.connectLabel}');
    expect(source).toContain('HubGit does not ask for, see, or store');
    expect(source).not.toContain('GitHub password');
  });

  it('uses the generated deployment branding boundary and conditional freshness', () => {
    const source = readFileSync(
      resolve(import.meta.dirname, 'hubgit-app.tsx'),
      'utf8',
    );
    expect(source).toContain(
      "import type { BrandingManifest, Freshness } from '@hubgit/contracts'",
    );
    expect(source).toContain("freshness.state !== 'live'");
    expect(source).not.toContain('referenceWarning');
  });
});
