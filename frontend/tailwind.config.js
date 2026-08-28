/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#effcf8',
          100: '#d8f7ed',
          500: '#0e9f76',
          600: '#087f60',
          700: '#08664f',
          900: '#064336',
        },
        ink: '#14201d',
      },
      boxShadow: {
        card: '0 18px 50px -28px rgba(20, 32, 29, 0.35)',
      },
    },
  },
  plugins: [],
}

