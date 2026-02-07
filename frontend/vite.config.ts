// THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
//
// This software is provided under a proprietary license.
// See the LICENSE file for details.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8420',
      '/ws': {
        target: 'ws://localhost:8420',
        ws: true,
      },
    },
  },
})
