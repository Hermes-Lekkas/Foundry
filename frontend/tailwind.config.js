// THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
//
// This software is provided under a proprietary license.
// See the LICENSE file for details.

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Crystalline Material palette
        glass: {
          50: 'rgba(255, 255, 255, 0.05)',
          100: 'rgba(255, 255, 255, 0.10)',
          200: 'rgba(255, 255, 255, 0.15)',
          300: 'rgba(255, 255, 255, 0.20)',
          400: 'rgba(255, 255, 255, 0.30)',
        },
        foundry: {
          primary: '#6366f1',    // Indigo
          secondary: '#8b5cf6',  // Violet
          accent: '#06b6d4',     // Cyan
          success: '#10b981',    // Emerald
          warning: '#f59e0b',    // Amber
          error: '#ef4444',      // Red
          surface: '#0f172a',    // Slate 900
          panel: '#1e293b',      // Slate 800
          border: '#334155',     // Slate 700
        },
      },
      backdropBlur: {
        glass: '50px',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
        'glass-hover': '0 12px 48px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
        specular: 'inset 0 1px 1px rgba(255, 255, 255, 0.15), 0 0 20px rgba(99, 102, 241, 0.1)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'glass-shimmer': 'glass-shimmer 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: 0.6 },
          '50%': { opacity: 1 },
        },
        'glass-shimmer': {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
    },
  },
  plugins: [],
}
