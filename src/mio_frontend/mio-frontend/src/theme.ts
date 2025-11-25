import themeConfig from './assets/helpful_warmth_theme.json'

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

export const theme: Theme = themeConfig as Theme

// Apply theme to document
export const applyTheme = () => {
  const root = document.documentElement
  
  // Apply colors
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

// Get color by name
export const getColor = (name: keyof Theme['colors']): string => {
  return theme.colors[name]
}

export default theme
