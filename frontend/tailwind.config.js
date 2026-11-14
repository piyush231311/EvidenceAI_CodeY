/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0B1120', // Dark navy background
          light: '#F8FAFC',
        },
        sidebar: {
          DEFAULT: '#0F172A', // Sidebar background
          light: '#FFFFFF',
        },
        surface: {
          DEFAULT: '#1E293B', // Dark slate surfaces
          light: '#FFFFFF',
          hover: '#293548',
          card: '#162032',
          border: '#334155',
        },
        brand: {
          primary: '#3B82F6', // Blue accent
          secondary: '#22D3EE', // Cyan accent
          dark: '#1D4ED8',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.35)',
        'glow-primary': '0 0 20px rgba(59, 130, 246, 0.15)',
        'glow-cyan': '0 0 20px rgba(34, 211, 238, 0.15)',
      },
    },
  },
  plugins: [],
}
