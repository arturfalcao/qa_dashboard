'use client'

import { useMemo } from 'react'
import { LotStatus } from '@qa-dashboard/shared'
import { formatLotStatus } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectOption } from '@/components/ui/select'
import { Button } from '@/components/ui/button'

interface LotFiltersProps {
  statusFilter: string
  setStatusFilter: (status: string) => void
  factoryFilter: string
  setFactoryFilter: (factory: string) => void
  factories: string[]
}

const statusOptions: SelectOption<string>[] = [
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
  const factoryOptions = useMemo<SelectOption<string>[]>(
    () => [
      { value: 'all', label: 'All Factories' },
      ...factories.map((factory) => ({ value: factory, label: factory })),
    ],
    [factories],
  )

  const hasActiveFilters = statusFilter !== 'all' || factoryFilter !== 'all'

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</p>
            <Select
              value={statusFilter}
              onChange={(value) => setStatusFilter(value as string)}
              options={statusOptions}
            />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Factory</p>
            <Select
              value={factoryFilter}
              onChange={(value) => setFactoryFilter(value as string)}
              options={factoryOptions}
            />
          </div>
        </div>

        {hasActiveFilters && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-neutral-100 px-3 py-2 text-xs text-neutral-600 dark:bg-neutral-900/50 dark:text-neutral-300">
            <span>Filtering {statusFilter !== 'all' ? `status: ${statusFilter}` : 'all statuses'}{factoryFilter !== 'all' ? ` • factory: ${factoryFilter}` : ''}</span>
            <Button
              variant="ghost"
              size="xs"
              onClick={() => {
                setStatusFilter('all')
                setFactoryFilter('all')
              }}
            >
              Reset filters
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
