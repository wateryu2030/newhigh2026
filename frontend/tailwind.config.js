/** @type {import('tailwindcss').Config} */
/** 红山量化平台 - 统一设计 Token（与 OpenClaw 协作） */
module.exports = {
  /** 与 Next src/ 目录一致；根下无 app/ 时勿写 ./app 以免误导排查 */
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'terminal-bg': 'var(--color-bg-terminal)',
        'card-bg': 'var(--color-surface-mid)',
        'card-border': 'var(--color-border)',
        'accent-green': 'var(--color-success)',
        'accent-red': 'var(--color-danger)',
        'text-primary': 'var(--color-text-primary-alt)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-code': 'var(--color-text-code)',
        'text-dim': 'var(--color-text-dim)',
        background: 'var(--color-bg-terminal)',
        surface: 'var(--color-bg-app)',
        'surface-dim': 'var(--color-bg-app)',
        'surface-container-low': 'var(--color-surface-low)',
        'surface-container': 'var(--color-surface-container)',
        'surface-container-high': 'var(--color-surface-high)',
        'surface-container-highest': 'var(--color-surface-highest)',
        primary: 'var(--color-primary-soft)',
        'primary-fixed': 'var(--color-primary)',
        'primary-container': 'var(--color-primary)',
        tertiary: 'var(--color-tertiary)',
        'on-surface': 'var(--color-text-primary)',
        /** 主色块上的正文（纯白），见 globals.css --color-text-on-warm-fill */
        'on-warm-fill': 'var(--color-text-on-warm-fill)',
        'on-surface-variant': 'var(--color-text-muted)',
        outline: 'var(--color-outline)',
        'outline-variant': 'var(--color-outline-variant)',
        fund: {
          dark: 'var(--color-bg-terminal)',
          emerald: 'var(--color-primary)',
          indigo: 'var(--color-primary)',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        headline: ['var(--font-manrope)', 'Manrope', 'sans-serif'],
        body: ['var(--font-inter)', 'Inter', 'sans-serif'],
        label: ['Space Grotesk', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        lg: '0.25rem',
        xl: '0.5rem',
        '2xl': '0.75rem',
        card: '16px',
      },
      boxShadow: {
        glass: 'var(--shadow-glass)',
        'primary-glow': 'var(--shadow-primary-glow)',
        card: 'var(--shadow-card)',
        modal: 'var(--shadow-modal)',
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
