'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import {
  ActivityIcon,
  PackageIcon,
  BarChart3Icon,
  DownloadIcon,
  Factory as FactoryIcon,
  Users as UsersIcon,
  Building2 as ClientsIcon,
  ShieldCheckIcon,
  FileTextIcon,
  Sparkles,
} from 'lucide-react'
import { AppShell } from '@/components/navigation/app-shell'
import { SidebarItem } from '@/components/ui/sidebar'
import { BreadcrumbItem } from '@/components/ui/navbar'
import { useAuth } from '@/components/providers/auth-provider'
import { apiClient } from '@/lib/api'
import { storeUser } from '@/lib/auth'
import { UserRole } from '@qa-dashboard/shared'

export default function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { tenantSlug: string }
}) {
  const { user, setUser, isLoading } = useAuth()
  const pathname = usePathname()
  const tenantSlugFromRoute = params.tenantSlug

  useEffect(() => {
    const hydrateTenant = async () => {
      if (user && user.tenantId && !user.tenantSlug) {
        try {
          const tenant = await apiClient.getTenantById(user.tenantId)
          const nextUser = { ...user, tenantSlug: tenant.slug, tenantName: tenant.name }
          setUser(nextUser)
          storeUser(nextUser)
        } catch (error) {
          console.error('Unable to hydrate tenant information', error)
        }
      }
    }

    hydrateTenant()
  }, [user, setUser])

  const resolvedTenantSlug = user?.tenantSlug ?? tenantSlugFromRoute
  const basePath = `/c/${resolvedTenantSlug}`

  const roles = user?.roles ?? []
  const canManage = roles.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))
  const isQualityDirector = roles.includes(UserRole.QUALITY_DIRECTOR)

  const navigation: SidebarItem[] = [
    { label: 'Live Feed', href: `${basePath}/feed`, icon: ActivityIcon },
    { label: 'Lots', href: `${basePath}/lots`, icon: PackageIcon },
    { label: 'Tech Packs', href: `${basePath}/tech-packs`, icon: Sparkles },
  ]

  // Add Quality Control for Quality Directors
  if (isQualityDirector || canManage) {
    navigation.push({ label: 'Quality Control', href: `${basePath}/quality-control`, icon: ShieldCheckIcon })
  }

  // Add management items
  if (canManage) {
    navigation.push({ label: 'Clients', href: `${basePath}/clients`, icon: ClientsIcon })
    navigation.push({ label: 'Factories', href: `${basePath}/factories`, icon: FactoryIcon })
  }

  // Add remaining items
  navigation.push({ label: 'Analytics', href: `${basePath}/analytics`, icon: BarChart3Icon })
  navigation.push({ label: 'Reports', href: `${basePath}/reports`, icon: FileTextIcon })
  navigation.push({ label: 'Exports', href: `${basePath}/exports`, icon: DownloadIcon })

  if (canManage) {
    navigation.push({ label: 'User Access', href: `${basePath}/users`, icon: UsersIcon })
  }

  const activeItem = navigation.find(
    (item) => pathname === item.href || (item.href !== '/' && pathname.startsWith(`${item.href}/`)),
  )

  const breadcrumbs: BreadcrumbItem[] = activeItem
    ? [
        { label: 'Workspace', href: basePath },
        { label: activeItem.label, href: activeItem.href },
      ]
    : [{ label: 'Workspace', href: basePath }]

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600"></div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  if (user.tenantSlug && user.tenantSlug !== tenantSlugFromRoute) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <div className="rounded-2xl border border-neutral-200 bg-white px-10 py-12 text-center shadow-sm">
          <h1 className="text-2xl font-semibold text-neutral-900">Access denied</h1>
          <p className="mt-3 text-sm text-neutral-500">
            You don&apos;t have access to this client workspace.
          </p>
        </div>
      </div>
    )
  }

  return (
    <AppShell
      navigation={navigation}
      tenantLabel={user.tenantName || resolvedTenantSlug}
      breadcrumbTrail={breadcrumbs}
      sidebarFooter={
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <div className="flex-shrink-0 w-6 h-6 rounded bg-primary-100 flex items-center justify-center text-primary-600 font-bold text-xs">
              P&amp;P
            </div>
            <span>Powered by Pack &amp; Polish</span>
          </div>
          <p className="text-xs text-gray-400">
            Quality Assurance Dashboard • v1.0
          </p>
        </div>
      }
    >
      {children}
    </AppShell>
  )
}
