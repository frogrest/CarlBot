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
        background: '#0a0e17',
        surface: {
          DEFAULT: '#111827',
          subtle: '#0f172a',
          elevated: '#172033',
          border: '#1e293b',
          borderLight: '#334155',
          hover: '#1e293b',
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
          technician: '#f97316',
          critical: '#ef4444',
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
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'panel': '0 4px 20px -2px rgba(0, 0, 0, 0.4), 0 2px 6px -1px rgba(0, 0, 0, 0.3)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.5)',
      },
    },
  },
  plugins: [],
}
