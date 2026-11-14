/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: '#FBFBF9', // Soft warm paper background
          sidebar: '#F4F3EE', // Calm warm sidebar
          surface: '#FFFFFF', // Clean flat surface
          border: '#E6E4DF',  // Subtle 1px warm border
          hover: '#EFEFEA',
        },
        ink: {
          DEFAULT: '#1C1917', // Dark charcoal text
          muted: '#6B6862',   // Secondary readable text
          light: '#9C9890',   // Subtle metadata
        },
        teal: {
          DEFAULT: '#0F766E', // Muted deep teal primary accent
          hover: '#115E59',
          light: '#F0FDFA',
          border: '#CCFBF1',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif'
        ],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '4px',
        sm: '3px',
        md: '6px',
        lg: '8px',
      },
    },
  },
  plugins: [],
}
