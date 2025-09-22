'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { BatchCard } from '@/components/batches/batch-card'
import { BatchFilters } from '@/components/batches/batch-filters'
import { useState } from 'react'
import { Batch } from '@qa-dashboard/shared'

export default function BatchesPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [vendorFilter, setVendorFilter] = useState<string>('all')

  const { data: batches = [], isLoading } = useQuery({
    queryKey: ['batches'],
    queryFn: () => apiClient.getBatches(),
    refetchInterval: 10000, // Refetch every 10 seconds
  })

  // Filter batches based on selected filters
  const filteredBatches = batches.filter((batch: Batch) => {
    if (statusFilter !== 'all' && batch.status !== statusFilter) return false
    if (vendorFilter !== 'all' && batch.vendor?.name !== vendorFilter) return false
    return true
  })

  // Get unique vendors for filter
  const vendors = Array.from(new Set(batches.map((batch: Batch) => batch.vendor?.name).filter(Boolean))) as string[]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Batches</h1>
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
          <h1 className="text-2xl font-bold text-gray-900">Batches</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage production batches and approvals
          </p>
        </div>
      </div>

      <BatchFilters
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        vendorFilter={vendorFilter}
        setVendorFilter={setVendorFilter}
        vendors={vendors}
      />

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredBatches.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No batches found</h3>
            <p className="text-gray-500">
              {statusFilter !== 'all' || vendorFilter !== 'all' 
                ? 'Try adjusting your filters'
                : 'Run the seed command to create sample batches'
              }
            </p>
          </div>
        ) : (
          filteredBatches.map((batch: Batch) => (
            <BatchCard key={batch.id} batch={batch} />
          ))
        )}
      </div>
    </div>
  )
}