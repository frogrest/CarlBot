/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#070b12',
        surface: {
          DEFAULT: '#0e1524',
          subtle: '#0a0f1d',
          elevated: '#152035',
          border: '#1c2a44',
          borderLight: '#2d4268',
          hover: '#192740',
        },
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        },
        status: {
          healthy: '#10b981',
          warning: '#f59e0b',
          investigating: '#38bdf8',
          technician: '#fb923c',
          critical: '#f43f5e',
          unknown: '#64748b',
        },
        policy: {
          read: '#38bdf8',
          safe: '#10b981',
          approval: '#f59e0b',
          human: '#f43f5e',
        }
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Consolas', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'panel': '0 4px 20px -2px rgba(0, 0, 0, 0.4), 0 2px 6px -1px rgba(0, 0, 0, 0.3)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.5)',
      },
    },
  },
  plugins: [],
}
