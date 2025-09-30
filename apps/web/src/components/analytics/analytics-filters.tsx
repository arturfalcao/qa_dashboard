'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectOption } from '@/components/ui/select'
import { useMemo } from 'react'
import { Button } from '@/components/ui/button'

interface AnalyticsFiltersProps {
  range: 'last_7d' | 'last_30d'
  setRange: (range: 'last_7d' | 'last_30d') => void
  groupBy: 'style' | 'factory'
  setGroupBy: (groupBy: 'style' | 'factory') => void
}

export function AnalyticsFilters({ range, setRange, groupBy, setGroupBy }: AnalyticsFiltersProps) {
  const rangeOptions = useMemo<SelectOption<string>[]>(
    () => [
      { value: 'last_7d', label: 'Last 7 days' },
      { value: 'last_30d', label: 'Last 30 days' },
    ],
    [],
  )

  const groupOptions = useMemo<SelectOption<string>[]>(
    () => [
      { value: 'factory', label: 'By factory' },
      { value: 'style', label: 'By style' },
    ],
    [],
  )

  const hasCustomFilters = range !== 'last_7d' || groupBy !== 'factory'

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Time range</p>
            <Select value={range} onChange={(value) => setRange(value as 'last_7d' | 'last_30d')} options={rangeOptions} />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Group by</p>
            <Select value={groupBy} onChange={(value) => setGroupBy(value as 'style' | 'factory')} options={groupOptions} />
          </div>
        </div>

        {hasCustomFilters && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-neutral-100 px-3 py-2 text-xs text-neutral-600 dark:bg-neutral-900/50 dark:text-neutral-300">
            <span>
              Showing {range === 'last_7d' ? 'last 7 days' : 'last 30 days'} • grouped by {groupBy}
            </span>
            <Button variant="ghost" size="xs" onClick={() => { setRange('last_7d'); setGroupBy('factory') }}>
              Reset filters
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
