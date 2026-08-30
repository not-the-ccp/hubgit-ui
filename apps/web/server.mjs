import { createRequestHandler } from '@react-router/express';
import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const port = Number(process.env.PORT ?? 3000);
const apiOrigin = process.env.HUBGIT_API_ORIGIN ?? 'http://127.0.0.1:8000';

app.disable('x-powered-by');
app.use(
  createProxyMiddleware({
    pathFilter: '/api/**',
    target: apiOrigin,
    changeOrigin: true,
    ws: true,
  }),
);
app.use(
  '/assets',
  express.static('build/client/assets', {
    immutable: true,
    maxAge: '1y',
  }),
);
app.use(express.static('build/client', { maxAge: '1h' }));
app.all(
  '*splat',
  createRequestHandler({
    build: await import('./build/server/index.js'),
  }),
);

app.listen(port, '0.0.0.0', () => {
  console.log(`HubGit web listening on http://0.0.0.0:${port}`);
});

