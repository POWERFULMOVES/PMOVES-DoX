import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [],
    alias: {
      '@': resolve(__dirname, './'),
    },
    // Silence the CJS deprecation warning
    server: {
      deps: {
        inline: ['d3', '@testing-library/react'],
      },
    },
  },
});
