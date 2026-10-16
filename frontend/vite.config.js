import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// During local development (`npm run dev`) the browser talks to Vite on 5173 and
// Vite forwards every /api/* call to the FastAPI server on 8000. This mirrors what
// nginx does in the container image, so the React code only ever uses relative
// URLs and never needs to know where the backend lives.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
