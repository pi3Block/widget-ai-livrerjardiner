import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/widget-ai-livrerjardiner/',
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/widget-entry.jsx'),
      name: 'LivrerJardinerWidget',
      formats: ['umd'],
      fileName: (format) => `livrerjardiner-widget.${format}.js`
    },
    rollupOptions: {
      external: [],
      output: {
        globals: {
        },
      },
    },
    outDir: 'dist'
  }
});
