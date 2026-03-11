/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        fund: {
          dark: '#0F172A',
          emerald: '#10B981',
          indigo: '#6366F1',
        },
      },
    },
  },
  plugins: [],
};
