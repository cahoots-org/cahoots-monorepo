// Design System Tokens
// Centralized design tokens replacing scattered styling patterns

export const tokens = {
  // Color Palette - Semantic color assignments
  colors: {
    // Primary Brand Colors - Vibrant Orange
    primary: {
      50: '#FFF7ED',
      100: '#FFEDD5',
      200: '#FED7AA',
      300: '#FDBA74',
      400: '#FF8C1A', // Main brand - Vibrant Orange
      500: '#FF8C1A',
      600: '#EA580C',
      700: '#C2410C',
      800: '#9A3412',
      900: '#7C2D12',
    },
    
    // Secondary - Verdigris
    secondary: {
      50: '#F0F9F8',
      100: '#DCF0EF',
      200: '#B9E1DE',
      300: '#96D2CE',
      400: '#78B7B4', // Verdigris
      500: '#5FA09C',
      600: '#4C807D',
      700: '#3F6765',
      800: '#355452',
      900: '#2E4544',
    },
    
    // Neutral Colors - Warmer grays based on Sepia
    neutral: {
      0: '#FFFFFF',
      50: '#FAF9F7',
      100: '#F5F3F0',
      200: '#E8E4DD',
      300: '#D4CFC5',
      400: '#A39B8B',
      500: '#7A6F5C',
      600: '#593E0C', // Sepia
      700: '#3D2A08',
      800: '#2A1D05',
      900: '#1A1206',
      950: '#0D0903',
    },
    
    // Dynamic Theme Colors - Warmer dark theme
    dark: {
      bg: 'var(--color-bg, #0D0903)',              // Very dark brown-black
      surface: 'var(--color-surface, #1A1206)',     // Dark sepia surface
      border: 'var(--color-border, #2A1D05)',       // Sepia border
      text: 'var(--color-text, #FAF9F7)',           // Warm white text
      muted: 'var(--color-text-muted, #A39B8B)',    // Muted warm gray
      body: 'var(--color-text-body, #FAF9F7)',      // Body text
    },
    
    // Semantic State Colors
    success: {
      50: '#F0F9F8',
      100: '#DCF0EF',
      500: '#78B7B4', // Verdigris for success
      600: '#5FA09C',
      700: '#4C807D',
    },
    
    warning: {
      50: '#FEF8F1',
      100: '#FDF3E3',
      500: '#F7CA84', // Sunset for warnings
      600: '#E5B36B',
      700: '#D39C52',
    },
    
    error: {
      50: '#FDF1ED',
      100: '#FAE0D8',
      500: '#D24E26', // Cinnabar for errors
      600: '#B83E1C',
      700: '#973118',
    },
    
    info: {
      50: '#EEF4FD',
      100: '#DCE8FB',
      500: '#5B8FD9', // Blue for info/processing
      600: '#4A7AC7',
      700: '#3A65B5',
    },
  },
  
  // Typography Scale
  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Monaco', 'Courier New', 'monospace'],
    },
    
    fontSize: {
      xs: ['0.75rem', { lineHeight: '1rem' }],     // 12px
      sm: ['0.875rem', { lineHeight: '1.25rem' }], // 14px
      base: ['1rem', { lineHeight: '1.5rem' }],    // 16px
      lg: ['1.125rem', { lineHeight: '1.75rem' }], // 18px
      xl: ['1.25rem', { lineHeight: '1.75rem' }],  // 20px
      '2xl': ['1.5rem', { lineHeight: '2rem' }],   // 24px
      '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
      '4xl': ['2.25rem', { lineHeight: '2.5rem' }],   // 36px
    },
    
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    
    lineHeight: {
      tight: '1.25',
      normal: '1.5',
      relaxed: '1.75',
    },
    
    letterSpacing: {
      tight: '-0.025em',
      normal: '0em',
      wide: '0.025em',
    },
  },
  
  // Spacing Scale - 8px grid system
  spacing: {
    0: '0',
    1: '0.25rem',   // 4px
    2: '0.5rem',    // 8px
    3: '0.75rem',   // 12px
    4: '1rem',      // 16px
    5: '1.25rem',   // 20px
    6: '1.5rem',    // 24px
    8: '2rem',      // 32px
    10: '2.5rem',   // 40px
    12: '3rem',     // 48px
    16: '4rem',     // 64px
    20: '5rem',     // 80px
    24: '6rem',     // 96px
    32: '8rem',     // 128px
  },
  
  // Border Radius
  borderRadius: {
    none: '0',
    sm: '0.125rem',   // 2px
    base: '0.25rem',  // 4px
    md: '0.375rem',   // 6px
    lg: '0.5rem',     // 8px
    xl: '0.75rem',    // 12px
    '2xl': '1rem',    // 16px
    '3xl': '1.5rem',  // 24px
    full: '9999px',
  },
  
  // Shadows
  boxShadow: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
  },
  
  // Transitions
  transitionDuration: {
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
  },
  
  transitionTimingFunction: {
    ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
  
  transitions: {
    colors: 'color 150ms ease, background-color 150ms ease, border-color 150ms ease',
    all: 'all 150ms ease',
    transform: 'transform 150ms ease',
  },
  
  // Layout
  zIndex: {
    hide: -1,
    auto: 'auto',
    base: 0,
    docked: 10,
    dropdown: 1000,
    sticky: 1100,
    banner: 1200,
    overlay: 1300,
    modal: 1400,
    popover: 1500,
    skipLink: 1600,
    toast: 1700,
    tooltip: 1800,
  },
  
  // Breakpoints for responsive design
  screens: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },
};

// CSS Custom Properties for runtime theming
export const cssVariables = {
  // Primary colors - Cinnabar
  '--color-primary-50': tokens.colors.primary[50],
  '--color-primary-100': tokens.colors.primary[100],
  '--color-primary-500': tokens.colors.primary[500],
  '--color-primary-600': tokens.colors.primary[600],
  '--color-primary-700': tokens.colors.primary[700],
  
  // Secondary colors - Verdigris
  '--color-secondary-400': tokens.colors.secondary[400],
  '--color-secondary-500': tokens.colors.secondary[500],
  '--color-secondary-600': tokens.colors.secondary[600],
  
  // Dark theme - Warmer tones
  '--color-bg': '#0D0903',              // Very dark brown-black
  '--color-surface': '#1A1206',         // Dark sepia surface
  '--color-border': '#2A1D05',          // Sepia border
  '--color-text': '#FAF9F7',            // Warm white text
  '--color-text-muted': '#A39B8B',      // Muted warm gray
  
  // State colors
  '--color-success': tokens.colors.success[500],
  '--color-warning': tokens.colors.warning[500],
  '--color-error': tokens.colors.error[500],
  '--color-info': tokens.colors.info[500],
  
  // Typography
  '--font-sans': tokens.typography.fontFamily.sans.join(', '),
  '--font-mono': tokens.typography.fontFamily.mono.join(', '),
  
  // Spacing
  '--spacing-1': tokens.spacing[1],
  '--spacing-2': tokens.spacing[2],
  '--spacing-4': tokens.spacing[4],
  '--spacing-6': tokens.spacing[6],
  '--spacing-8': tokens.spacing[8],
  
  // Borders
  '--radius-base': tokens.borderRadius.base,
  '--radius-lg': tokens.borderRadius.lg,
  '--radius-xl': tokens.borderRadius.xl,
  
  // Shadows
  '--shadow-base': tokens.boxShadow.base,
  '--shadow-lg': tokens.boxShadow.lg,
  '--shadow-xl': tokens.boxShadow.xl,
};

export default tokens;