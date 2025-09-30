'use client'

import { useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

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
  const router = useRouter()

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
    <div className="space-y-6">
      <div className="hidden xl:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[220px]">Lot</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Supply chain</TableHead>
              <TableHead>Current stage</TableHead>
              <TableHead>Inspection progress</TableHead>
              <TableHead>Defect rate</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(({ lot, snapshot }) => {
              const statusBadge = getLotStatusColor(lot.status)
              const stageMeta = stageStatusMeta[snapshot.currentStageStatus]
              const progress = Math.min(lot.inspectedProgress ?? 0, 100)

              return (
                <TableRow key={lot.id} className="align-top">
                  <TableCell className="align-top">
                    <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                      {lot.styleRef}
                    </div>
                    <div className="text-xs text-neutral-500">#{lot.id.slice(0, 8)}</div>
                    <div className="mt-1 text-xs text-neutral-500">
                      {formatNumber(lot.quantityTotal)} units · {snapshot.primaryFactory}
                    </div>
                  </TableCell>
                  <TableCell className="align-top">
                    <span className={cn('inline-flex items-center rounded-full px-3 py-1 text-xs font-medium', statusBadge)}>
                      {formatLotStatus(lot.status)}
                    </span>
                  </TableCell>
                  <TableCell className="align-top text-sm text-neutral-700 dark:text-neutral-300">
                    <div>
                      {snapshot.supplierCount} supplier{snapshot.supplierCount === 1 ? '' : 's'} · {snapshot.totalStages}{' '}
                      stage{snapshot.totalStages === 1 ? '' : 's'}
                    </div>
                    <div className="mt-1 text-xs text-neutral-500">
                      CO₂ footprint · {snapshot.totalCo2Kg.toFixed(2)} kg
                    </div>
                  </TableCell>
                  <TableCell className="align-top text-sm text-neutral-700 dark:text-neutral-300">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-neutral-900 dark:text-neutral-100">
                        {snapshot.currentStageLabel}
                      </span>
                      <span className={cn('w-fit rounded-full px-2 py-0.5 text-[11px] font-semibold', stageMeta.badge)}>
                        {stageMeta.label}
                      </span>
                      {snapshot.nextStageLabel && (
                        <span className="text-xs text-neutral-500">Next: {snapshot.nextStageLabel}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="flex items-center justify-between text-xs text-neutral-500">
                      <span>{formatPercentage(progress)}</span>
                      <span>
                        {snapshot.completedStages}/{snapshot.totalStages}
                      </span>
                    </div>
                    <div className="mt-1 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-800">
                      <div className="h-2 rounded-full bg-primary-600" style={{ width: `${progress}%` }} />
                    </div>
                  </TableCell>
                  <TableCell className="align-top text-sm font-medium">
                    <span className={cn(lot.defectRate > 5 ? 'text-danger-600' : 'text-success-600')}>
                      {formatPercentage(lot.defectRate)}
                    </span>
                  </TableCell>
                  <TableCell className="align-top text-sm text-neutral-500">
                    {formatDate(lot.updatedAt)}
                  </TableCell>
                  <TableCell className="align-top text-right">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => router.push(`/c/${tenantSlug}/lots/${lot.id}`)}
                    >
                      View lot
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-4 xl:hidden">
        {rows.map(({ lot, snapshot }) => {
          const statusBadge = getLotStatusColor(lot.status)
          const stageMeta = stageStatusMeta[snapshot.currentStageStatus]
          const progress = Math.min(lot.inspectedProgress ?? 0, 100)

          return (
            <Card key={lot.id}>
              <CardHeader className="space-y-1">
                <CardTitle className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  {lot.styleRef}
                </CardTitle>
                <CardDescription>#{lot.id.slice(0, 8)} · {formatNumber(lot.quantityTotal)} units</CardDescription>
                <span className={cn('w-fit rounded-full px-3 py-1 text-xs font-semibold', statusBadge)}>
                  {formatLotStatus(lot.status)}
                </span>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-neutral-700 dark:text-neutral-300">
                <div>
                  <p className="font-medium text-neutral-900 dark:text-neutral-100">Primary factory</p>
                  <p className="text-xs text-neutral-500">{snapshot.primaryFactory}</p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-lg bg-neutral-100 p-3 dark:bg-neutral-900/50">
                    <p className="text-[11px] uppercase tracking-wide text-neutral-500">Supply chain</p>
                    <p className="mt-1 text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                      {snapshot.supplierCount} supplier{snapshot.supplierCount === 1 ? '' : 's'}
                    </p>
                    <p className="text-xs text-neutral-500">{snapshot.totalStages} stages</p>
                  </div>
                  <div className="rounded-lg bg-neutral-100 p-3 dark:bg-neutral-900/50">
                    <p className="text-[11px] uppercase tracking-wide text-neutral-500">Current stage</p>
                    <p className="mt-1 text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                      {snapshot.currentStageLabel}
                    </p>
                    <p className={cn('mt-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold', stageMeta.badge)}>
                      {stageMeta.label}
                    </p>
                    {snapshot.nextStageLabel && (
                      <p className="text-xs text-neutral-500">Next: {snapshot.nextStageLabel}</p>
                    )}
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-xs text-neutral-500">
                    <span>{formatPercentage(progress)}</span>
                    <span>
                      {snapshot.completedStages}/{snapshot.totalStages}
                    </span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-800">
                    <div className="h-2 rounded-full bg-primary-600" style={{ width: `${progress}%` }} />
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <div>
                    <p className="text-xs text-neutral-500">Defect rate</p>
                    <p className={cn('text-sm font-semibold', lot.defectRate > 5 ? 'text-danger-600' : 'text-success-600')}>
                      {formatPercentage(lot.defectRate)}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => router.push(`/c/${tenantSlug}/lots/${lot.id}`)}
                  >
                    View lot
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
