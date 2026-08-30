import { reactRouter } from '@react-router/dev/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [reactRouter()],
  server: {
    proxy: {
      '/api': {
        target: process.env.HUBGIT_API_ORIGIN ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});

