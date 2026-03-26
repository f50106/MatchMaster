import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // In Docker Compose, set API_URL=http://backend:8000 in the frontend service env.
        // For local dev outside Docker, defaults to localhost:8000.
        target: process.env.API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
