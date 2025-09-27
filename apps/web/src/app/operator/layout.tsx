'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LogOutIcon } from 'lucide-react'
import { UserRole } from '@qa-dashboard/shared'

import { useAuth } from '@/components/providers/auth-provider'
import { cn } from '@/lib/utils'

const ALLOWED_ROLES = new Set([UserRole.OPERATOR, UserRole.SUPERVISOR, UserRole.ADMIN])

const NAVIGATION = [
  { label: 'Devices', href: '/operator' },
  { label: 'Active lots', href: '/operator/lots' },
  { label: 'Settings', href: '/operator/settings', roles: [UserRole.SUPERVISOR, UserRole.ADMIN] as UserRole[] },
]

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, logout } = useAuth()
  const pathname = usePathname()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-primary-500" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  const hasAccess = user.roles?.some((role) => ALLOWED_ROLES.has(role))

  if (!hasAccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">Access restricted</h1>
          <p className="mt-2 text-sm text-slate-600">
            The operator workspace is available for operator, supervisor or admin roles only.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Cloud operator</p>
            <h1 className="text-xl font-semibold text-slate-900">QA floor overview</h1>
          </div>
          <button
            onClick={logout}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
          >
            <LogOutIcon className="h-4 w-4" aria-hidden />
            Sign out
          </button>
        </div>
        <div className="border-t border-slate-200">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 text-sm font-medium text-slate-600">
            {NAVIGATION.map((item) => {
              if (item.roles && !item.roles.some((role) => user.roles?.includes(role))) {
                return null
              }

              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`)

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'py-3 transition-colors',
                    isActive ? 'text-primary-600' : 'hover:text-slate-900',
                  )}
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  )
}
