/** @type {import('tailwindcss').Config} */
/** 红山量化平台 - 统一设计 Token（与 OpenClaw 协作） */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'terminal-bg': '#0A0C10',
        'card-bg': '#14171C',
        'card-border': '#2A2E36',
        'accent-green': '#22C55E',
        'accent-red': '#FF3B30',
        'text-primary': '#F1F5F9',
        'text-secondary': '#94A3B8',
        background: '#0A0C10',
        surface: '#0B0E14',
        'surface-dim': '#0B0E14',
        'surface-container-low': '#10131A',
        'surface-container': '#161A21',
        'surface-container-high': '#1C2028',
        'surface-container-highest': '#22262F',
        primary: '#FF6B6B',
        'primary-fixed': '#FF3B30',
        'primary-container': '#FF3B30',
        tertiary: '#FF7439',
        'on-surface': '#ECEDF6',
        'on-surface-variant': '#A9ABB3',
        outline: '#73757D',
        'outline-variant': '#45484F',
        fund: {
          dark: '#0A0C10',
          emerald: '#FF3B30',
          indigo: '#FF3B30',
        },
      },
      fontFamily: {
        headline: ['Manrope', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        label: ['Space Grotesk', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        lg: '0.25rem',
        xl: '0.5rem',
        '2xl': '0.75rem',
        card: '16px',
      },
      boxShadow: {
        glass: '0px 24px 48px rgba(0, 0, 0, 0.4)',
        'primary-glow': '0 0 20px rgba(255, 59, 48, 0.3)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: 0, transform: 'translateY(10px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
