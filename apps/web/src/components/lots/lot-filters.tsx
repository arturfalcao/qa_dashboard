'use client'

import { LotStatus } from '@qa-dashboard/shared'
import { formatLotStatus } from '@/lib/utils'

interface LotFiltersProps {
  statusFilter: string
  setStatusFilter: (status: string) => void
  factoryFilter: string
  setFactoryFilter: (factory: string) => void
  factories: string[]
}

const statusOptions = [
  { value: 'all', label: 'All Statuses' },
  { value: LotStatus.PLANNED, label: formatLotStatus(LotStatus.PLANNED) },
  { value: LotStatus.IN_PRODUCTION, label: formatLotStatus(LotStatus.IN_PRODUCTION) },
  { value: LotStatus.INSPECTION, label: formatLotStatus(LotStatus.INSPECTION) },
  { value: LotStatus.PENDING_APPROVAL, label: formatLotStatus(LotStatus.PENDING_APPROVAL) },
  { value: LotStatus.APPROVED, label: formatLotStatus(LotStatus.APPROVED) },
  { value: LotStatus.REJECTED, label: formatLotStatus(LotStatus.REJECTED) },
  { value: LotStatus.SHIPPED, label: formatLotStatus(LotStatus.SHIPPED) },
]

export function LotFilters({
  statusFilter,
  setStatusFilter,
  factoryFilter,
  setFactoryFilter,
  factories,
}: LotFiltersProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Factory</label>
          <select
            value={factoryFilter}
            onChange={(e) => setFactoryFilter(e.target.value)}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          >
            <option value="all">All Factories</option>
            {factories.map((factory) => (
              <option key={factory} value={factory}>
                {factory}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}
