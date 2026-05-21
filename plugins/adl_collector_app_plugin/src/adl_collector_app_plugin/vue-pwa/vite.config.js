import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cssInjectedByJsPlugin from 'vite-plugin-css-injected-by-js'

// Plugin Vue apps cannot share the core's Vite dev server (adl/viewer/adl-viewer).
// They output to their own namespaced static directory and are referenced via
// {% static %} in templates — the same approach used by adl-ftp-plugin.
export default defineConfig({
  plugins: [
    vue(),
    cssInjectedByJsPlugin({ jsAssetsFilterFunction: () => true }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: {
    rollupOptions: {
      input: {
        'collector-field-app': resolve('./src/collector-field-app.js'),
      },
      output: {
        dir: '../static/adl_collector_app_plugin/vue',
        entryFileNames: '[name].js',
      },
    },
  },
})
