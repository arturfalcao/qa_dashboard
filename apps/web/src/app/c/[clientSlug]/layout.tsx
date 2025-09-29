'use client'

import { useEffect } from 'react'
import { useAuth } from '@/components/providers/auth-provider'
import { usePathname } from 'next/navigation'
import { Navbar } from '@/components/ui/navbar'
import { Sidebar } from '@/components/ui/sidebar'
import { apiClient } from '@/lib/api'
import { storeUser } from '@/lib/auth'

export default function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { clientSlug: string }
}) {
  const { user, setUser, isLoading } = useAuth()
  const pathname = usePathname()

  useEffect(() => {
    const hydrateClient = async () => {
      if (user && user.clientId && !user.clientSlug) {
        try {
          const client = await apiClient.getClientById(user.clientId)
          const nextUser = { ...user, clientSlug: client.slug, clientName: client.name }
          setUser(nextUser)
          storeUser(nextUser)
        } catch (error) {
          console.error('Unable to hydrate client information', error)
        }
      }
    }

    hydrateClient()
  }, [user, setUser])

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

  if (user.clientSlug && user.clientSlug !== params.clientSlug) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
          <p className="text-gray-600">You don&apos;t have access to this client workspace.</p>
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
