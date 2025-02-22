import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: true,
    hmr: {
      clientPort: 443,
      path: 'hmr',
      timeout: 5000
    },
    watch: {
      usePolling: true,
    },
    allowedHosts: ['test.cahoots.cc'],
    proxy: {
      '^/(api|auth)/.*': {
        target: 'http://master:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        rewrite: (path) => path,
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Pass through the original request's origin and headers
            if (req.headers.origin) {
              proxyReq.setHeader('origin', req.headers.origin);
            }
            if (req.headers.host) {
              proxyReq.setHeader('host', req.headers.host);
            }
          });
        }
      }
    },
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,HEAD,PUT,PATCH,POST,DELETE',
      'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization',
      'Access-Control-Allow-Credentials': 'true'
    }
  },
  resolve: {
    alias: {
      '@tabler/icons-react': '@tabler/icons-react/dist/umd/tabler-icons-react.min.js',
    },
  },
  build: {
    target: 'esnext',
    minify: 'esbuild',
  }
})
