'use client'

import * as React from 'react'
import { Tab } from '@headlessui/react'
import { cn } from '@/lib/utils'

export interface TabsProps extends React.ComponentProps<typeof Tab.Group> {
  className?: string
}

export function Tabs({ children, className, ...props }: TabsProps) {
  return (
    <Tab.Group {...props}>
      <div className={cn('space-y-4', className)}>{children}</div>
    </Tab.Group>
  )
}

export const TabsList = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <Tab.List
      ref={ref}
      className={cn(
        'inline-flex gap-2 rounded-full border border-neutral-200 bg-neutral-100 p-1 text-sm font-medium text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900',
        className,
      )}
      {...props}
    />
  ),
)
TabsList.displayName = 'TabsList'

export const TabsTrigger = React.forwardRef<HTMLButtonElement, React.ComponentProps<typeof Tab>>(
  ({ className, ...props }, ref) => (
    <Tab
      ref={ref}
      className={({ selected }) =>
        cn(
          'inline-flex items-center gap-2 rounded-full px-4 py-2 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400',
          selected
            ? 'bg-white text-primary-700 shadow-sm dark:bg-neutral-800'
            : 'text-neutral-500 hover:text-neutral-700 dark:text-neutral-300 dark:hover:text-neutral-100',
          className,
        )
      }
      {...props}
    />
  ),
)
TabsTrigger.displayName = 'TabsTrigger'

export const TabsContent = React.forwardRef<HTMLDivElement, React.ComponentProps<typeof Tab.Panel>>(
  ({ className, ...props }, ref) => (
    <Tab.Panel ref={ref} className={cn('rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900', className)} {...props} />
  ),
)
TabsContent.displayName = 'TabsContent'
