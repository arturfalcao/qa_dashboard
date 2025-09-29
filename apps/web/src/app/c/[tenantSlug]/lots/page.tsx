'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Lot, UserRole } from '@qa-dashboard/shared'
import { LotFilters } from '@/components/lots/lot-filters'
import { LotFormModal } from '@/components/lots/lot-form-modal'
import { useAuth } from '@/components/providers/auth-provider'
import { LotTable } from '@/components/lots/lot-table'

export default function LotsPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [factoryFilter, setFactoryFilter] = useState<string>('all')
  const [isLotModalOpen, setIsLotModalOpen] = useState(false)
  const { user } = useAuth()

  const canManageLots = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)) ?? false

  const { data: lots = [], isLoading } = useQuery({
    queryKey: ['lots'],
    queryFn: () => apiClient.getLots(),
    refetchInterval: 10000,
  })

  const filteredLots = lots.filter((lot: Lot) => {
    if (statusFilter !== 'all' && lot.status !== statusFilter) return false
    if (factoryFilter !== 'all' && lot.factory?.name !== factoryFilter) return false
    return true
  })

  const factories = Array.from(
    new Set(lots.map((lot: Lot) => lot.factory?.name).filter(Boolean)),
  ) as string[]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Lots</h1>
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
          <h1 className="text-2xl font-bold text-gray-900">Lots</h1>
          <p className="text-sm text-gray-500 mt-1">
            Monitor inspection readiness, approvals, and supplier performance.
          </p>
        </div>
        {canManageLots && (
          <button
            onClick={() => setIsLotModalOpen(true)}
            className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700"
          >
            New Lot
          </button>
        )}
      </div>

      <LotFilters
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        factoryFilter={factoryFilter}
        setFactoryFilter={setFactoryFilter}
        factories={factories}
      />

      {filteredLots.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No lots match your filters</h3>
          <p className="text-gray-500">
            {statusFilter !== 'all' || factoryFilter !== 'all'
              ? 'Try adjusting the filters to broaden your search.'
              : 'Seed the database to explore sample production lots.'}
          </p>
        </div>
      ) : (
        <LotTable lots={filteredLots} />
      )}

      <LotFormModal isOpen={isLotModalOpen} onClose={() => setIsLotModalOpen(false)} />
    </div>
  )
}
