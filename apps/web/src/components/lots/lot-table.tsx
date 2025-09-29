'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import { useParams } from 'next/navigation'
import {
  Lot,
  SupplyChainStageStatus,
  LotSupplier,
  LotSupplierRole,
} from '@qa-dashboard/shared'
import {
  cn,
  formatDate,
  formatLotStatus,
  formatNumber,
  formatPercentage,
  getLotStatusColor,
} from '@/lib/utils'

interface LotTableProps {
  lots: Lot[]
}

interface SupplyChainSnapshot {
  primaryFactory: string
  supplierCount: number
  stageProgressPercent: number
  currentStageLabel: string
  currentStageStatus: SupplyChainStageStatus
  nextStageLabel?: string
  totalStages: number
  completedStages: number
  totalCo2Kg: number
}

const stageStatusMeta: Record<SupplyChainStageStatus, { badge: string; label: string }> = {
  [SupplyChainStageStatus.NOT_STARTED]: {
    badge: 'bg-gray-100 text-gray-600 border border-gray-200',
    label: 'Not started',
  },
  [SupplyChainStageStatus.IN_PROGRESS]: {
    badge: 'bg-sky-100 text-sky-700 border border-sky-200',
    label: 'In progress',
  },
  [SupplyChainStageStatus.COMPLETED]: {
    badge: 'bg-green-100 text-green-700 border border-green-200',
    label: 'Completed',
  },
}

const defaultSnapshot: SupplyChainSnapshot = {
  primaryFactory: 'Unassigned',
  supplierCount: 0,
  stageProgressPercent: 0,
  currentStageLabel: 'Awaiting kickoff',
  currentStageStatus: SupplyChainStageStatus.NOT_STARTED,
  totalStages: 0,
  completedStages: 0,
  totalCo2Kg: 0,
}

const sortSuppliers = (suppliers?: LotSupplier[]) =>
  (suppliers ?? []).slice().sort((a, b) => a.sequence - b.sequence)

const sortRoles = (roles?: LotSupplierRole[]) =>
  (roles ?? []).slice().sort((a, b) => a.sequence - b.sequence)

const gatherStages = (suppliers: LotSupplierRole[][]) =>
  suppliers
    .map((roles, supplierIdx) =>
      roles.map((role) => ({
        role,
        supplierIdx,
      })),
    )
    .flat()
    .sort((a, b) => {
      if (a.supplierIdx !== b.supplierIdx) {
        return a.supplierIdx - b.supplierIdx
      }
      return (a.role.sequence ?? 0) - (b.role.sequence ?? 0)
    })

function buildSnapshot(lot: Lot): SupplyChainSnapshot {
  const suppliers = sortSuppliers(lot.suppliers)
  if (suppliers.length === 0) {
    return defaultSnapshot
  }

  const primaryFactory =
    suppliers.find((supplier) => supplier.isPrimary)?.factory?.name ??
    lot.factory?.name ??
    suppliers[0]?.factory?.name ??
    'Unassigned'

  const stageMatrix = suppliers.map((supplier) =>
    sortRoles(supplier.roles).map((role) => ({ role, factoryName: supplier.factory?.name })),
  )

  const flattened = gatherStages(stageMatrix.map((entries) => entries.map((entry) => entry.role)))

  if (flattened.length === 0) {
    return {
      ...defaultSnapshot,
      primaryFactory,
      supplierCount: suppliers.length,
    }
  }

  const currentStageEntry =
    flattened.find((entry) => entry.role.status === SupplyChainStageStatus.IN_PROGRESS) ??
    flattened.find((entry) => entry.role.status !== SupplyChainStageStatus.COMPLETED)

  const currentStageIndex = currentStageEntry
    ? flattened.findIndex((entry) => entry.role.id === currentStageEntry.role.id)
    : -1

  const nextStageEntry =
    currentStageIndex >= 0
      ? flattened
          .slice(currentStageIndex + 1)
          .find((entry) => entry.role.status !== SupplyChainStageStatus.COMPLETED)
      : undefined

  const completedStages = flattened.filter(
    (entry) => entry.role.status === SupplyChainStageStatus.COMPLETED,
  ).length
  const totalStages = flattened.length

  const stageProgressPercent =
    totalStages === 0 ? 0 : Math.round((completedStages / totalStages) * 100)

  const totalCo2Kg = flattened.reduce((sum, entry) => {
    const value = entry.role.co2Kg ?? entry.role.role?.defaultCo2Kg ?? 0
    return sum + Number(value || 0)
  }, 0)

  return {
    primaryFactory,
    supplierCount: suppliers.length,
    stageProgressPercent,
    currentStageLabel:
      currentStageEntry?.role.role?.name ?? currentStageEntry?.role.roleId ?? 'Awaiting kickoff',
    currentStageStatus:
      currentStageEntry?.role.status ?? SupplyChainStageStatus.NOT_STARTED,
    nextStageLabel: nextStageEntry?.role.role?.name ?? nextStageEntry?.role.roleId,
    totalStages,
    completedStages,
    totalCo2Kg,
  }
}

export function LotTable({ lots }: LotTableProps) {
  const params = useParams()
  const tenantSlug = params.tenantSlug as string

  const rows = useMemo(
    () =>
      lots
        .slice()
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
        .map((lot) => ({
          lot,
          snapshot: buildSnapshot(lot),
        })),
    [lots],
  )

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center">
        <h3 className="text-lg font-semibold text-gray-900">No lots yet</h3>
        <p className="mt-2 text-sm text-gray-500">
          Create your first lot to start orchestrating inspections and supplier stages.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Lot
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Status
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Supply Chain
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Current Stage
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Inspection Progress
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Defect Rate
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Updated
              </th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map(({ lot, snapshot }) => {
              const statusBadge = getLotStatusColor(lot.status)
              const stageMeta = stageStatusMeta[snapshot.currentStageStatus]

              return (
                <tr key={lot.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="text-sm font-semibold text-gray-900">{lot.styleRef}</div>
                    <div className="text-xs text-gray-500">#{lot.id.slice(0, 8)}</div>
                    <div className="mt-1 text-xs text-gray-500">
                      {formatNumber(lot.quantityTotal)} units · {snapshot.primaryFactory}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <span className={cn('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', statusBadge)}>
                      {formatLotStatus(lot.status)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    <div>
                      {snapshot.supplierCount} supplier{snapshot.supplierCount === 1 ? '' : 's'} · {snapshot.totalStages}{' '}
                      stage{snapshot.totalStages === 1 ? '' : 's'}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      CO₂ footprint · {snapshot.totalCo2Kg.toFixed(2)} kg
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-gray-900">{snapshot.currentStageLabel}</span>
                      <span className={cn('w-fit rounded-full px-2 py-0.5 text-[11px] font-medium', stageMeta.badge)}>
                        {stageMeta.label}
                      </span>
                      {snapshot.nextStageLabel && (
                        <span className="text-xs text-gray-500">
                          Next: {snapshot.nextStageLabel}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{formatPercentage(lot.inspectedProgress)}</span>
                      <span>
                        {snapshot.completedStages}/{snapshot.totalStages}
                      </span>
                    </div>
                    <div className="mt-1 h-2 w-full rounded-full bg-gray-200">
                      <div
                        className="h-2 rounded-full bg-primary-600"
                        style={{ width: `${Math.min(lot.inspectedProgress, 100)}%` }}
                      />
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium">
                    <span className={cn(lot.defectRate > 5 ? 'text-red-600' : 'text-green-600')}>
                      {formatPercentage(lot.defectRate)}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {formatDate(lot.updatedAt)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                    <Link
                      href={`/c/${tenantSlug}/lots/${lot.id}`}
                      className="inline-flex items-center rounded-md border border-primary-200 px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-50"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
