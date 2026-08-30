import { index, route, type RouteConfig } from '@react-router/dev/routes';

export default [
  index('./routes/home.tsx'),
  route('login', './routes/login.tsx'),
  route('join', './routes/join.tsx'),
  route('password-reset', './routes/password-reset.tsx'),
  route('verify', './routes/verify.tsx'),
  route('two-factor', './routes/two-factor.tsx'),
  route('dashboard', './routes/dashboard.tsx'),
  route('issues', './routes/issues.tsx'),
  route('pulls', './routes/pulls.tsx'),
  route('notifications', './routes/notifications.tsx'),
  route('search', './routes/search.tsx'),
  route('settings/*', './routes/settings.tsx'),
  route('orgs/:org/*', './routes/organization.tsx'),
  route(':owner/:repo/*', './routes/repository.tsx'),
  route(':username', './routes/profile.tsx'),
  route('*', './routes/not-found.tsx'),
] satisfies RouteConfig;
