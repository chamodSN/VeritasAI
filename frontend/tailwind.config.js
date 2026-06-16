// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
  theme: {
    extend: {
      colors: {
        ink:     '#1C1917',
        parchment: '#FAF8F5',
        stone: {
          DEFAULT: '#E8E4DF',
          dark:    '#C9C4BC',
        },
        sage: {
          light:   '#EBF3EE',
          DEFAULT: '#4A7C59',
          dark:    '#2D5E3A',
        },
        amber: {
          light:   '#FEF3C7',
          DEFAULT: '#B45309',
        },
        mist:    '#6B7280',
        danger: {
          light:   '#FEE2E2',
          DEFAULT: '#DC2626',
        },
      },

      fontFamily: {
        serif:   ['"Crimson Pro"', 'Georgia', 'serif'],
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },

      fontSize: {
        display: ['48px', { lineHeight: '1.1', fontWeight: '700' }],
        h1:      ['36px', { lineHeight: '1.2', fontWeight: '600' }],
        h2:      ['24px', { lineHeight: '1.3', fontWeight: '600' }],
        h3:      ['18px', { lineHeight: '1.4', fontWeight: '600' }],
      },

      borderRadius: {
        card:   '8px',
        btn:    '6px',
        input:  '6px',
      },

      boxShadow: {
        card:     '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
        elevated: '0 4px 12px rgba(0,0,0,0.10)',
        focus:    '0 0 0 3px rgba(74,124,89,0.25)',
      },

      transitionTimingFunction: {
        smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
      },

      animation: {
        'pulse-node': 'pulseNode 1.5s ease-in-out infinite',
        'slide-in-right': 'slideInRight 0.25s ease-out',
        'fade-up': 'fadeUp 0.2s ease-out',
      },

      keyframes: {
        pulseNode: {
          '0%, 100%': { opacity: '0.4', transform: 'scale(0.95)' },
          '50%':      { opacity: '1',   transform: 'scale(1)' },
        },
        slideInRight: {
          from: { transform: 'translateX(16px)', opacity: '0' },
          to:   { transform: 'translateX(0)',    opacity: '1' },
        },
        fadeUp: {
          from: { transform: 'translateY(8px)', opacity: '0' },
          to:   { transform: 'translateY(0)',   opacity: '1' },
        },
      },

      width: {
        sidebar:     '240px',
        'right-panel': '320px',
      },
    },
  },
  plugins: [],
};