import type { ReactNode } from 'react';
import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  isRouteErrorResponse,
  useRouteError,
} from 'react-router';

import './globals.css';
import { AppProviders } from './providers';

export const links = () => [
  { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' },
];

export const meta = () => [
  { title: 'HubGit · Git collaboration without the broken bits' },
  {
    name: 'description',
    content: 'A provider-neutral, self-hosted Git collaboration frontend.',
  },
];

export function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function Root() {
  return <AppProviders><Outlet /></AppProviders>;
}

export function ErrorBoundary() {
  const error = useRouteError();
  const status = isRouteErrorResponse(error) ? error.status : 500;
  const message = isRouteErrorResponse(error)
    ? error.statusText
    : 'HubGit could not render this page.';

  return (
    <main className="error-page">
      <span className="error-code">{status}</span>
      <h1>{message}</h1>
      <p>The route may be unavailable, unsupported by the provider, or temporarily offline.</p>
      <a className="primary-button" href="/dashboard">Return to HubGit</a>
    </main>
  );
}
