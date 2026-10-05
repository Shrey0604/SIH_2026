import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['maplibre-gl'],
  },
  build: {
    rollupOptions: {
      output: {
        // Keep large vendor libraries in their own long-cached chunks.
        manualChunks: {
          maplibre: ['maplibre-gl'],
          charts: ['recharts'],
          react: ['react', 'react-dom', '@tanstack/react-query'],
        },
      },
    },
    chunkSizeWarningLimit: 1200,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
