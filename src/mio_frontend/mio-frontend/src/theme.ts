import { Dark, setCssVar } from 'quasar'
import { watch } from 'vue'
import themeConfig from './assets/helpful_warmth_theme.json'
import darkThemeConfig from './assets/helpful_warmth_theme_dark.json'

export interface Theme {
  id: string
  name: string
  description: string
  colors: {
    success: string
    warning: string
    error: string
    info: string
    primary: string
    secondary: string
    accent: string
    background: string
    surface: string
    text: string
    muted: string
  }
  typography: {
    headingFont: string
    bodyFont: string
    scale: string
  }
  ui: {
    borderRadius: string
    borderWidth: string
    shadow: string
  }
}

export const lightTheme: Theme = themeConfig as Theme
export const darkTheme: Theme = darkThemeConfig as Theme

export const currentTheme = { ...lightTheme }

// Apply theme to document
export const applyTheme = (isDark: boolean) => {
  const theme = isDark ? darkTheme : lightTheme
  const root = document.documentElement
  
  // Update currentTheme object
  Object.assign(currentTheme, theme)

  // Update Quasar Brand Colors
  setCssVar('primary', theme.colors.primary)
  setCssVar('secondary', theme.colors.secondary)
  setCssVar('accent', theme.colors.accent)
  setCssVar('positive', theme.colors.success)
  setCssVar('negative', theme.colors.error)
  setCssVar('info', theme.colors.info)
  setCssVar('warning', theme.colors.warning)

  // Update Quasar Dark Mode Backgrounds (optional, but good for consistency)
  if (isDark) {
    setCssVar('dark-page', theme.colors.background)
    setCssVar('dark', theme.colors.surface)
  }

  // Apply Custom CSS Variables
  root.style.setProperty('--color-primary', theme.colors.primary)
  root.style.setProperty('--color-secondary', theme.colors.secondary)
  root.style.setProperty('--color-accent', theme.colors.accent)
  root.style.setProperty('--color-success', theme.colors.success)
  root.style.setProperty('--color-warning', theme.colors.warning)
  root.style.setProperty('--color-error', theme.colors.error)
  root.style.setProperty('--color-info', theme.colors.info)
  root.style.setProperty('--color-background', theme.colors.background)
  root.style.setProperty('--color-surface', theme.colors.surface)
  root.style.setProperty('--color-text', theme.colors.text)
  root.style.setProperty('--color-muted', theme.colors.muted)
  
  // Apply typography
  root.style.setProperty('--font-heading', theme.typography.headingFont)
  root.style.setProperty('--font-body', theme.typography.bodyFont)
  
  // Apply UI
  root.style.setProperty('--border-radius', theme.ui.borderRadius)
  root.style.setProperty('--border-width', theme.ui.borderWidth)
  root.style.setProperty('--shadow', theme.ui.shadow)
}

export const initTheme = () => {
  // Set initial Dark mode preference to auto
  Dark.set('auto')

  watch(() => Dark.isActive, (val) => {
    applyTheme(val)
  }, { immediate: true })
}

// Get color by name
export const getColor = (name: keyof Theme['colors']): string => {
  return currentTheme.colors[name]
}

export default currentTheme
