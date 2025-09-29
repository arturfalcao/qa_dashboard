'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Factory, UserRole } from '@qa-dashboard/shared'
import { FactoryFormModal } from '@/components/factories/factory-form-modal'
import { useAuth } from '@/components/providers/auth-provider'
import { formatDate } from '@/lib/utils'

export default function FactoriesPage() {
  const { user } = useAuth()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingFactory, setEditingFactory] = useState<Factory | null>(null)

  const canEdit = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)) ?? false

  const { data: factories = [], isLoading } = useQuery({
    queryKey: ['factories'],
    queryFn: () => apiClient.getFactories(),
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Factories</h1>
        </div>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Factories</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage the production facilities available when your team creates lots.
          </p>
        </div>
        {canEdit && (
          <button
            onClick={() => {
              setEditingFactory(null)
              setIsModalOpen(true)
            }}
            className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700"
          >
            Add Factory
          </button>
        )}
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr className="text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
              <th className="px-6 py-3">Name</th>
              <th className="px-6 py-3">Location</th>
              <th className="px-6 py-3">Created</th>
              {canEdit && <th className="px-6 py-3 text-right">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {factories.length === 0 ? (
              <tr>
                <td colSpan={canEdit ? 4 : 3} className="px-6 py-6 text-center text-gray-500">
                  No factories yet. {canEdit ? 'Start by adding one.' : 'Contact your administrator to add factories.'}
                </td>
              </tr>
            ) : (
              factories.map((factory) => (
                <tr key={factory.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{factory.name}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {[factory.city, factory.country].filter(Boolean).join(', ') || '—'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{formatDate(factory.createdAt)}</td>
                  {canEdit && (
                    <td className="px-6 py-4 text-right text-sm">
                      <button
                        onClick={() => {
                          setEditingFactory(factory)
                          setIsModalOpen(true)
                        }}
                        className="text-primary-600 hover:text-primary-700"
                      >
                        Edit
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <FactoryFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        initialFactory={editingFactory}
      />
    </div>
  )
}
