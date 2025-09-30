'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import * as React from 'react'
import { cn } from '@/lib/utils'

export interface SidebarItem {
  label: string
  href: string
  icon?: React.ComponentType<{ className?: string }>
  badge?: React.ReactNode
  description?: string
}

export interface SidebarProps {
  items: SidebarItem[]
  onNavigate?: () => void
  className?: string
  activePath?: string
  footer?: React.ReactNode
}

export function Sidebar({ items, onNavigate, className, activePath, footer }: SidebarProps) {
  const pathname = usePathname()
  const currentPath = activePath ?? pathname

  return (
    <nav
      className={cn(
        'flex h-full flex-col border-r border-neutral-200 bg-white px-3 py-6 dark:border-neutral-800 dark:bg-neutral-950',
        className,
      )}
      aria-label="Primary"
    >
      <ul className="flex-1 space-y-1">
        {items.map((item) => {
          const isActive =
            currentPath === item.href ||
            (item.href !== '/' && currentPath.startsWith(`${item.href}/`))

          const Icon = item.icon

          return (
            <li key={item.href}>
              <Link
                href={item.href}
                onClick={onNavigate}
                className={cn(
                  'group flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-500/10 dark:text-primary-200'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-300 dark:hover:bg-neutral-800/60',
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <span
                  className={cn(
                    'h-6 w-1 rounded-full transition-all group-hover:bg-primary-300',
                    isActive ? 'bg-primary-500 group-hover:bg-primary-500' : 'bg-transparent',
                  )}
                  aria-hidden
                />
                {Icon && (
                  <Icon
                    className={cn(
                      'h-5 w-5 shrink-0 text-current transition-opacity',
                      !isActive && 'opacity-70 group-hover:opacity-100',
                    )}
                  />
                )}
                <div className="flex flex-1 items-center justify-between gap-2">
                  <span className="truncate">{item.label}</span>
                  {item.badge && <span className="text-xs font-semibold text-primary-600">{item.badge}</span>}
                </div>
              </Link>
              {item.description && (
                <p className="ml-6 mt-1 text-xs text-neutral-500 dark:text-neutral-400">{item.description}</p>
              )}
            </li>
          )
        })}
      </ul>

      {footer && <div className="mt-6 border-t border-neutral-200 pt-4 text-xs text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">{footer}</div>}
    </nav>
  )
}
