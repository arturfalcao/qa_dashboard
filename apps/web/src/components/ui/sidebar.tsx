'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import { useParams, usePathname } from 'next/navigation'
import { ActivityIcon, PackageIcon, BarChart3Icon, DownloadIcon, Factory as FactoryIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/components/providers/auth-provider'
import { UserRole } from '@qa-dashboard/shared'

export function Sidebar() {
  const params = useParams()
  const pathname = usePathname()
  const { user } = useAuth()
  const clientSlug = params.clientSlug as string
  const basePath = `/c/${clientSlug}`

  const navigation = useMemo(() => {
    const base = [
      { name: 'Live Feed', href: '/feed', icon: ActivityIcon },
      { name: 'Lots', href: '/lots', icon: PackageIcon },
      { name: 'Analytics', href: '/analytics', icon: BarChart3Icon },
      { name: 'Exports', href: '/exports', icon: DownloadIcon },
    ]

    const canManageFactories = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))
    if (canManageFactories) {
      return [
        base[0],
        base[1],
        { name: 'Factories', href: '/factories', icon: FactoryIcon },
        base[2],
        base[3],
      ]
    }

    return base
  }, [user?.roles])

  return (
    <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-sm border-r border-gray-200 pt-16">
      <div className="flex flex-col h-full">
        <div className="flex-1 px-4 py-6">
          <nav className="space-y-1">
            {navigation.map((item) => {
              const href = `${basePath}${item.href}`
              const isActive = pathname === href
              
              return (
                <Link
                  key={item.name}
                  href={href}
                  className={cn(
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <item.icon
                    className={cn(
                      'mr-3 h-5 w-5 transition-colors',
                      isActive
                        ? 'text-primary-500'
                        : 'text-gray-400 group-hover:text-gray-500'
                    )}
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>

        <div className="px-4 py-4 border-t border-gray-200 text-xs text-gray-500">
          Observability endpoint available at <code className="font-mono">/metrics</code>
        </div>
      </div>
    </div>
  )
}
