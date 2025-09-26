
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // Cahoots Brand Colors
        primary: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#FF8C1A', // Vibrant Orange - main brand color
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#909296', // Muted text
          400: '#64748b',
          500: '#475569',
          600: '#334155',
          700: '#1e293b',
          800: '#0f172a',
          900: '#020617',
        },
        // Brand specific colors
        brand: {
          'vibrant-orange': '#FF8C1A',
          'orange-red': '#FF4D1C',
          'accent-red': '#D94167',
          'dark-bg': '#1A1B1E',
          'surface': '#25262B',
          'text': '#FFFFFF',
          'muted-text': '#909296',
          'border': '#373A40',
          'signature-blue': '#2962FF', // For gnome mascot only
        },
        // Status colors
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#71F0A9',
          700: '#15803d',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          500: '#FFB224',
          700: '#b45309',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#FF4444',
          700: '#b91c1c',
        },
        info: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#87CEEB',
          700: '#0369a1',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'primary-gradient': 'linear-gradient(135deg, #E67300 0%, #CC3300 100%)',
        'surface-gradient': 'linear-gradient(180deg, #25262B 0%, #1A1B1E 100%)',
      },
      boxShadow: {
        card: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
        'card-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2)',
      },
    },
  },
  plugins: [],
}
