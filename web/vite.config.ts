import { resolve } from 'node:path';
import { defineConfig } from 'vite';

// Relative base so the build works from a GitHub Pages project subpath.
export default defineConfig({
  base: './',
  server: { fs: { allow: ['..'] } },
  build: {
    chunkSizeWarningLimit: 2500,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        methods: resolve(__dirname, 'methods.html'),
        validation: resolve(__dirname, 'validation.html'),
      },
    },
  },
});
