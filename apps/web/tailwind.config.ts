import type { Config } from 'tailwindcss'
import { tokens } from './src/styles/tokens'

const buildColorScale = (tokenGroup: Record<string, string>, groupName: string) =>
  Object.fromEntries(
    Object.entries(tokenGroup).map(([step, value]) => [step, `var(--color-${groupName}-${step}, ${value})`]),
  )

const semanticColors = Object.fromEntries(
  Object.entries(tokens.color).map(([groupName, scale]) => [groupName, buildColorScale(scale, groupName)]),
)

const colors = {
  ...semanticColors,
  danger: semanticColors.error,
}

const fontSize = {
  xs: [tokens.text.xs, { lineHeight: tokens.leading.snug, letterSpacing: tokens.tracking.normal }],
  sm: [tokens.text.sm, { lineHeight: tokens.leading.snug, letterSpacing: tokens.tracking.normal }],
  base: [tokens.text.md, { lineHeight: tokens.leading.normal, letterSpacing: tokens.tracking.normal }],
  lg: [tokens.text.lg, { lineHeight: tokens.leading.normal, letterSpacing: tokens.tracking.normal }],
  xl: [tokens.text.xl, { lineHeight: tokens.leading.relaxed, letterSpacing: tokens.tracking.tight }],
  '2xl': [tokens.text['2xl'], { lineHeight: tokens.leading.relaxed, letterSpacing: tokens.tracking.tight }],
  '3xl': [tokens.text['3xl'], { lineHeight: tokens.leading.relaxed, letterSpacing: tokens.tracking.tight }],
}

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors,
      spacing: tokens.space,
      borderRadius: tokens.radius,
      boxShadow: tokens.shadow,
      fontFamily: {
        sans: tokens.font.sans,
        mono: tokens.font.mono,
      },
      fontSize,
    },
  },
  plugins: [],
}

export default config
