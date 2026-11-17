import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/demo': 'http://127.0.0.1:8000',
      '/assistant': 'http://127.0.0.1:8000',
      '/events': 'http://127.0.0.1:8000',
      '/weather': 'http://127.0.0.1:8000',
      '/places': 'http://127.0.0.1:8000',
      '/recommendations': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: '../backend/app/static',
    emptyOutDir: true,
  },
});
