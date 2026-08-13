import { defineConfig } from 'vite'

export default defineConfig({
  resolve: {
    // GLTFLoader comes from three/addons — keep a single three instance.
    dedupe: ['three'],
  },
  server: {
    port: 5185,
    strictPort: true,
  },
})
