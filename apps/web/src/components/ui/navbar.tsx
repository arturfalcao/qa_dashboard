'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import {
  ChevronDownIcon,
  MenuIcon,
  XIcon,
  UserIcon,
  SearchIcon,
  HomeIcon,
} from 'lucide-react'
import { useAuth } from '@/components/providers/auth-provider'
import { Button, IconButton } from './button'
import { cn } from '@/lib/utils'

export interface BreadcrumbItem {
  label: string
  href?: string
}

export interface NavbarProps {
  tenantLabel?: string
  breadcrumbs?: BreadcrumbItem[]
  actions?: React.ReactNode
  onToggleNavigation?: () => void
  onOpenCommandMenu?: () => void
  isMobileNavOpen?: boolean
}

export function Navbar({
  tenantLabel,
  breadcrumbs = [],
  actions,
  onToggleNavigation,
  onOpenCommandMenu,
  isMobileNavOpen = false,
}: NavbarProps) {
  const { user, logout } = useAuth()
  const pathname = usePathname()
  const [isMenuOpen, setIsMenuOpen] = React.useState(false)
  const menuRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  React.useEffect(() => {
    setIsMenuOpen(false)
  }, [pathname])

  const breadcrumbItems = breadcrumbs.length > 0 ? breadcrumbs : defaultBreadcrumbs(pathname)

  return (
    <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:border-neutral-800 dark:bg-neutral-950/75">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {onToggleNavigation && (
              <IconButton
                aria-label={isMobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'}
                icon={isMobileNavOpen ? <XIcon className="h-4 w-4" /> : <MenuIcon className="h-4 w-4" />}
                variant="subtle"
                size="sm"
                className="lg:hidden"
                onClick={onToggleNavigation}
              />
            )}
            <Link href="/" className="flex items-center gap-3 text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-xs uppercase tracking-wide text-white">
                QA
              </span>
              <div className="hidden sm:flex sm:flex-col">
                <span className="text-sm font-semibold">QA Dashboard</span>
                {tenantLabel && (
                  <span className="text-xs font-medium text-primary-600">{tenantLabel}</span>
                )}
              </div>
            </Link>
            {tenantLabel && (
              <span className="hidden rounded-full border border-primary-100 bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700 sm:inline-flex">
                {tenantLabel}
              </span>
            )}
          </div>

          <div className="ml-auto flex items-center gap-2">
            {actions}
            {onOpenCommandMenu && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={onOpenCommandMenu}
                  className="hidden items-center gap-2 sm:inline-flex"
                >
                  <SearchIcon className="h-4 w-4" />
                  <span>Search</span>
                  <kbd className="ml-2 hidden rounded-md border border-neutral-200 bg-neutral-100 px-1.5 text-xs font-medium text-neutral-500 sm:flex">
                    ⌘K
                  </kbd>
                </Button>
                <IconButton
                  aria-label="Open command palette"
                  icon={<SearchIcon className="h-4 w-4" />}
                  onClick={onOpenCommandMenu}
                  className="sm:hidden"
                />
              </>
            )}

            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setIsMenuOpen((prev) => !prev)}
                className="flex items-center gap-2 rounded-full border border-neutral-200 bg-white/90 px-3 py-1.5 text-sm font-medium text-neutral-700 shadow-sm transition hover:border-primary-200 hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200"
                aria-haspopup="menu"
                aria-expanded={isMenuOpen}
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 text-primary-700">
                  <UserIcon className="h-4 w-4" aria-hidden />
                </span>
                <span className="hidden sm:inline-flex max-w-[14ch] truncate text-left">
                  {user?.email}
                </span>
                <ChevronDownIcon className="h-4 w-4 text-neutral-400" aria-hidden />
              </button>

              {isMenuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 mt-2 w-56 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-xl focus:outline-none dark:border-neutral-700 dark:bg-neutral-900"
                >
                  <div className="px-4 py-3 text-sm">
                    <p className="font-medium text-neutral-900 dark:text-neutral-100">{user?.email}</p>
                    {tenantLabel && (
                      <p className="text-xs text-neutral-500 dark:text-neutral-400">{tenantLabel}</p>
                    )}
                    {user?.roles?.length ? (
                      <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                        Roles: {user.roles.map((role) => role.replace(/_/g, ' ')).join(', ')}
                      </p>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={logout}
                    className="flex w-full items-center gap-2 px-4 py-2 text-sm text-danger-600 transition hover:bg-danger-50 dark:hover:bg-danger-500/10"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <nav aria-label="Breadcrumb" className="hidden flex-wrap items-center gap-2 text-xs text-neutral-500 sm:flex">
          {breadcrumbItems.map((breadcrumb, index) => {
            const isLast = index === breadcrumbItems.length - 1
            return (
              <React.Fragment key={`${breadcrumb.label}-${index}`}>
                {index === 0 ? (
                  <HomeIcon className="h-4 w-4 text-neutral-400" aria-hidden />
                ) : (
                  <span className="text-neutral-300">/</span>
                )}
                {breadcrumb.href && !isLast ? (
                  <Link
                    href={breadcrumb.href}
                    className="text-neutral-500 transition hover:text-neutral-800"
                  >
                    {breadcrumb.label}
                  </Link>
                ) : (
                  <span className={cn('text-neutral-700 dark:text-neutral-200', isLast && 'font-medium')}>
                    {breadcrumb.label}
                  </span>
                )}
              </React.Fragment>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

function defaultBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean)
  if (segments.length === 0) {
    return [{ label: 'Home', href: '/' }]
  }

  const crumbs: BreadcrumbItem[] = [{ label: 'Home', href: '/' }]
  segments.forEach((segment, index) => {
    const href = `/${segments.slice(0, index + 1).join('/')}`
    crumbs.push({ label: segment.replace(/-/g, ' '), href })
  })
  return crumbs
}
