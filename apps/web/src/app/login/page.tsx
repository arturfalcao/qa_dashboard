'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/providers/auth-provider'
import { apiClient } from '@/lib/api'
import { storeUser } from '@/lib/auth'
import { UserRole } from '@qa-dashboard/shared'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const { setUser } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const response = await apiClient.login({ email, password })

      let tenantSlug: string | null = null
      let tenantName: string | null = null

      if (response.user.tenantId) {
        try {
          const tenant = await apiClient.getTenantById(response.user.tenantId)
          tenantSlug = tenant.slug
          tenantName = tenant.name
        } catch (tenantError) {
          console.error('Failed to load tenant information', tenantError)
        }
      }

      const userWithTenant = {
        ...response.user,
        tenantSlug,
        tenantName,
      }

      storeUser(userWithTenant)
      setUser(userWithTenant)

      const isOperator = response.user.roles.some((role) =>
        [UserRole.OPERATOR, UserRole.SUPERVISOR].includes(role),
      )

      if (isOperator) {
        router.push('/operator')
      } else {
        if (tenantSlug) {
          router.push(`/c/${tenantSlug}/feed`)
        } else {
          router.push('/')
        }
      }
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            QA Dashboard
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to your account
          </p>
        </div>
        
        <div className="bg-white p-8 rounded-lg shadow-md">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}
            
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                placeholder="your-email@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-blue-800 mb-2">Demo Credentials</h3>
          <div className="text-xs text-blue-700 space-y-1">
            <div><strong>PA&amp;CO Luxury Manufacturing:</strong></div>
            <div>• carlos.martins@paco.example / demo1234</div>
            <div>• ines.azevedo@paco.example / demo1234</div>
            <div>• joana.costa@paco.example / demo1234</div>
            <div>• miguel.lopes@paco.example / demo1234</div>
          </div>
        </div>
      </div>
    </div>
  )
}
