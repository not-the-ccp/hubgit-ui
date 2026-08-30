import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
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
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

