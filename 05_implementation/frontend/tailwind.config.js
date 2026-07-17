/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sage: {
          50: '#f6f7f6',
          100: '#e3e7e3',
          200: '#c7d0c7',
          300: '#a3b2a3',
          400: '#7a8f7a',
          500: '#5c7360',
          600: '#485a4c',
          700: '#3c4a3e',
          800: '#313d33',
          900: '#2a332b',
        }
      }
    },
  },
  plugins: [],
}
