'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  startIcon?: React.ReactNode
  endIcon?: React.ReactNode
  error?: string
  helperText?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', startIcon, endIcon, error, helperText, ...props }, ref) => {
    const describedById = helperText || error ? `${props.id || props.name}-description` : undefined

    return (
      <div className="space-y-1">
        <div
          className={cn(
            'flex w-full items-center rounded-md border border-neutral-200 bg-white px-3 shadow-sm transition focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-200 dark:bg-transparent',
            error && 'border-danger-500 focus-within:border-danger-500 focus-within:ring-danger-200',
            startIcon && 'pl-2.5',
            endIcon && 'pr-2.5',
          )}
        >
          {startIcon && (
            <span className="mr-2 inline-flex h-5 w-5 items-center justify-center text-neutral-400" aria-hidden>
              {startIcon}
            </span>
          )}
          <input
            ref={ref}
            type={type}
            className={cn(
              'flex-1 bg-transparent py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none dark:text-neutral-100',
              className,
            )}
            aria-invalid={Boolean(error)}
            aria-describedby={describedById}
            {...props}
          />
          {endIcon && (
            <span className="ml-2 inline-flex h-5 w-5 items-center justify-center text-neutral-400" aria-hidden>
              {endIcon}
            </span>
          )}
        </div>
        {(helperText || error) && (
          <p
            id={describedById}
            className={cn(
              'text-xs text-neutral-500',
              error && 'text-danger-600',
            )}
          >
            {error || helperText}
          </p>
        )}
      </div>
    )
  },
)
Input.displayName = 'Input'

export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string
  helperText?: string
}

export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className, error, helperText, rows = 4, ...props }, ref) => {
    const describedById = helperText || error ? `${props.id || props.name}-description` : undefined

    return (
      <div className="space-y-1">
        <textarea
          ref={ref}
          rows={rows}
          className={cn(
            'w-full rounded-md border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 shadow-sm transition focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:bg-transparent dark:text-neutral-100',
            error && 'border-danger-500 focus:border-danger-500 focus:ring-danger-200',
            className,
          )}
          aria-invalid={Boolean(error)}
          aria-describedby={describedById}
          {...props}
        />
        {(helperText || error) && (
          <p
            id={describedById}
            className={cn('text-xs text-neutral-500', error && 'text-danger-600')}
          >
            {error || helperText}
          </p>
        )}
      </div>
    )
  },
)
TextArea.displayName = 'TextArea'

export interface FieldProps {
  label: string
  htmlFor: string
  description?: string
  required?: boolean
  children: React.ReactNode
}

export function Field({ label, htmlFor, description, required, children }: FieldProps) {
  return (
    <label htmlFor={htmlFor} className="block text-sm font-medium text-neutral-700">
      <span className="flex items-center gap-1">
        {label}
        {required && <span className="text-danger-600">*</span>}
      </span>
      {description && <span className="mt-1 block text-xs font-normal text-neutral-500">{description}</span>}
      <div className="mt-2">{children}</div>
    </label>
  )
}
