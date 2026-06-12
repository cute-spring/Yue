import { defineConfig } from 'vite';
import solidPlugin from 'vite-plugin-solid';

const backendTarget = process.env.YUE_BACKEND_URL || 'http://127.0.0.1:8003';
const frontendHost = process.env.YUE_FRONTEND_HOST || '0.0.0.0';
const frontendPort = Number(process.env.YUE_FRONTEND_PORT || '3000');

export default defineConfig({
  plugins: [solidPlugin()],
  server: {
    host: frontendHost,
    port: frontendPort,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/files': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/exports': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'esnext',
  },
});
