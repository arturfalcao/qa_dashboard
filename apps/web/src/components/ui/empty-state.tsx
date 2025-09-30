'use client'

import * as React from 'react'
import { Button, ButtonProps } from './button'
import { cn } from '@/lib/utils'

export interface EmptyStateAction extends Omit<ButtonProps, 'children'> {
  label: string
}

export interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  className?: string
  action?: EmptyStateAction
  secondaryAction?: EmptyStateAction
}

export function EmptyState({
  icon,
  title,
  description,
  className,
  action,
  secondaryAction,
}: EmptyStateProps) {
  const renderAction = (btn?: EmptyStateAction, fallbackVariant: ButtonProps['variant'] = 'primary') => {
    if (!btn) return null
    const { label, variant, ...buttonProps } = btn
    return (
      <Button variant={variant ?? fallbackVariant} {...buttonProps}>
        {label}
      </Button>
    )
  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-8 py-16 text-center dark:border-neutral-700 dark:bg-neutral-900/40',
        className,
      )}
    >
      {icon && <div className="rounded-full bg-primary-50 p-3 text-primary-600" aria-hidden>{icon}</div>}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{title}</h3>
        {description && (
          <p className="max-w-md text-sm text-neutral-500 dark:text-neutral-300">{description}</p>
        )}
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        {renderAction(action)}
        {renderAction(secondaryAction, 'secondary')}
      </div>
    </div>
  )
}
