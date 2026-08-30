import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

import type { BootstrapData } from './lib/bootstrap';
import { queryKeys } from './lib/api-client';

export function AppProviders({
  children,
  bootstrap,
}: {
  children: ReactNode;
  bootstrap?: BootstrapData;
}) {
  const [queryClient] = useState(() => {
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          retry: (failureCount, error) => {
            const status =
              typeof error === 'object' &&
              error !== null &&
              'problem' in error &&
              typeof error.problem === 'object' &&
              error.problem !== null &&
              'status' in error.problem
                ? Number(error.problem.status)
                : 0;
            if ([401, 403, 404, 422].includes(status)) return false;
            return failureCount < 2;
          },
          staleTime: 15_000,
          refetchOnWindowFocus: false,
        },
        mutations: { retry: false },
      },
    });
    if (bootstrap?.meta) client.setQueryData(queryKeys.meta, bootstrap.meta);
    if (bootstrap?.capabilities) {
      client.setQueryData(queryKeys.capabilities, bootstrap.capabilities);
    }
    if (bootstrap?.authMethods) {
      client.setQueryData(queryKeys.authMethods, bootstrap.authMethods);
    }
    if (bootstrap?.session) {
      client.setQueryData(queryKeys.session, bootstrap.session);
    }
    return client;
  });

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
