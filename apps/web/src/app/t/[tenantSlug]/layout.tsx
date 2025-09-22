'use client'

import { useAuth } from '@/components/providers/auth-provider'
import { useParams, usePathname } from 'next/navigation'
import { Navbar } from '@/components/ui/navbar'
import { Sidebar } from '@/components/ui/sidebar'

export default function TenantLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { tenantSlug: string }
}) {
  const { user, isLoading } = useAuth()
  const pathname = usePathname()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!user) {
    return null // AuthProvider will handle redirect
  }

  // Verify tenant slug matches user's tenant
  if (user.tenantSlug !== params.tenantSlug) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
          <p className="text-gray-600">You don't have access to this tenant.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 ml-64">
          <div className="py-8 px-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}