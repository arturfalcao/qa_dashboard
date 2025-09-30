
'use client'

import * as React from 'react'
import { Loader2Icon } from 'lucide-react'
import { cn } from '@/lib/utils'

type ButtonVariant = 'primary' | 'secondary' | 'subtle' | 'ghost' | 'danger' | 'link'

type ButtonSize = 'xs' | 'sm' | 'md' | 'lg'

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-600 text-white shadow-sm hover:bg-primary-500 focus-visible:ring-primary-500 disabled:bg-primary-300',
  secondary:
    'bg-neutral-100 text-neutral-900 shadow-sm hover:bg-neutral-200 focus-visible:ring-neutral-300 disabled:bg-neutral-200',
  subtle:
    'bg-transparent text-neutral-700 hover:bg-neutral-100 focus-visible:ring-neutral-200',
  ghost:
    'bg-transparent text-neutral-600 hover:bg-neutral-100 focus-visible:ring-primary-200',
  danger:
    'bg-danger-600 text-white shadow-sm hover:bg-danger-500 focus-visible:ring-danger-400 disabled:bg-danger-300',
  link: 'bg-transparent text-primary-600 underline-offset-4 hover:underline focus-visible:ring-primary-300',
}

const sizeClasses: Record<ButtonSize, string> = {
  xs: 'h-8 rounded-md px-3 text-xs font-medium',
  sm: 'h-9 rounded-md px-3.5 text-sm font-medium',
  md: 'h-10 rounded-lg px-4 text-sm font-medium',
  lg: 'h-11 rounded-lg px-5 text-base font-semibold',
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: React.ReactNode
  iconPosition?: 'start' | 'end'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'start',
      disabled,
      children,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:cursor-not-allowed',
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        disabled={isDisabled}
        {...props}
      >
        {loading && <Loader2Icon className={cn('h-4 w-4 animate-spin', iconPosition === 'end' && 'order-2')} aria-hidden />}
        {!loading && icon && iconPosition === 'start' && (
          <span className="h-4 w-4 text-current" aria-hidden>
            {icon}
          </span>
        )}
        <span className="truncate">{children}</span>
        {!loading && icon && iconPosition === 'end' && (
          <span className="h-4 w-4 text-current" aria-hidden>
            {icon}
          </span>
        )}
      </button>
    )
  },
)
Button.displayName = 'Button'

export interface IconButtonProps
  extends Omit<ButtonProps, 'children'> {
  'aria-label': string
  size?: Extract<ButtonSize, 'xs' | 'sm' | 'md'>
  children?: never
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, size = 'sm', ...props }, ref) => (
    <Button
      ref={ref}
      variant="subtle"
      size={size}
      className={cn('aspect-square p-0')}
      icon={icon}
      aria-label={props['aria-label']}
      {...props}
    >
      <span className="sr-only">{props['aria-label']}</span>
    </Button>
  ),
)
IconButton.displayName = 'IconButton'
