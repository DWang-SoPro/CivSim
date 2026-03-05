export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#0a0a0a',
          panel: '#121212',
          'panel-light': '#1a1a1a',
        },
        border: {
          subtle: 'rgba(0, 255, 153, 0.15)',
          focus: 'rgba(0, 255, 153, 0.3)',
        },
        text: {
          primary: 'rgba(180, 200, 180, 0.9)',
          secondary: 'rgba(180, 200, 180, 0.6)',
          dim: 'rgba(180, 200, 180, 0.4)',
        },
        accent: {
          green: '#00ff99',
          amber: '#ffb000',
          blue: '#5aa8cc',
          red: '#ff4444',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
        serif: ['Noto Serif SC', 'serif'],
      },
      fontSize: {
        'xs': '11px',
        'sm': '12px',
        'base': '14px',
        'lg': '15px',
      },
      letterSpacing: {
        'wide': '0.05em',
        'wider': '0.1em',
        'widest': '0.15em',
      },
    },
  },
  plugins: [],
}
