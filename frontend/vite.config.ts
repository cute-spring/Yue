import { defineConfig } from 'vite';
import solidPlugin from 'vite-plugin-solid';

const backendTarget = process.env.YUE_BACKEND_URL || 'http://127.0.0.1:8003';

export default defineConfig({
  plugins: [solidPlugin()],
  server: {
    port: 3000,
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
