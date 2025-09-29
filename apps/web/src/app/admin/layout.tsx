'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/providers/auth-provider'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navigation = [
  { name: 'Tenants', href: '/admin/tenants', icon: '🏢' },
  { name: 'Devices', href: '/admin/devices', icon: '🖥️' },
  { name: 'Operators', href: '/admin/operators', icon: '👤' },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!user) {
      router.push('/login')
      return
    }

    // Check if user is super admin
    if (user.email !== 'celso.silva@packpolish.com') {
      router.push('/login')
    }
  }, [user, router])

  if (!user || user.email !== 'celso.silva@packpolish.com') {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-600 text-white font-bold">
                SA
              </div>
              <div>
                <h1 className="text-lg font-semibold text-slate-900">Super Admin</h1>
                <p className="text-xs text-slate-500">System Administration</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-600">{user.email}</span>
              <button
                onClick={() => {
                  router.push('/login')
                }}
                className="text-sm font-medium text-slate-600 hover:text-slate-900"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-slate-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex gap-8">
            {navigation.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`
                    flex items-center gap-2 border-b-2 px-1 py-4 text-sm font-medium transition
                    ${
                      isActive
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-slate-600 hover:border-slate-300 hover:text-slate-900'
                    }
                  `}
                >
                  <span>{item.icon}</span>
                  {item.name}
                </Link>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
    </div>
  )
}