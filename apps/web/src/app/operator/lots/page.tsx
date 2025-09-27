'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { ActivityIcon } from 'lucide-react'

import { apiClient } from '@/lib/api'
import { formatNumber, formatPercentage } from '@/lib/utils'

export default function OperatorLotsPage() {
  const { data: lots = [], isLoading } = useQuery({
    queryKey: ['operator', 'lots'],
    queryFn: () => apiClient.getOperatorActiveLots(),
  })

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Active lots</h2>
        <p className="mt-1 text-sm text-slate-600">
          Aggregated inspection progress, device coverage and defect rate for lots currently in QA.
        </p>
      </section>

      {isLoading ? (
        <div className="flex min-h-[200px] items-center justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-primary-500" />
        </div>
      ) : lots.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-600">
          No active lots in progress.
        </div>
      ) : (
        <div className="space-y-4">
          {lots.map((lot) => (
            <Link
              key={lot.lotId}
              href={`/operator/lot/${lot.lotId}`}
              className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-primary-200 hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">{lot.styleRef}</p>
                  <h3 className="text-lg font-semibold text-slate-900">Lot {lot.lotCode}</h3>
                  <p className="text-sm text-slate-600">{lot.customer}</p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                  <ActivityIcon className="h-4 w-4" aria-hidden />
                  {lot.activeDeviceIds.length} device{lot.activeDeviceIds.length === 1 ? '' : 's'}
                </span>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Pieces inspected</p>
                  <p className="text-xl font-semibold text-slate-900">{formatNumber(lot.piecesInspected)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Defects found</p>
                  <p className="text-xl font-semibold text-slate-900">{formatNumber(lot.defectsFound)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Defect rate</p>
                  <p className="text-xl font-semibold text-slate-900">{formatPercentage(lot.defectRate * 100)}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
