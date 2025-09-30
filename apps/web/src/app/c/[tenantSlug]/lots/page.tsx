'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Lot, LotStatus, UserRole } from '@qa-dashboard/shared'
import { LotFilters } from '@/components/lots/lot-filters'
import { LotFormModal } from '@/components/lots/lot-form-modal'
import { useAuth } from '@/components/providers/auth-provider'
import { LotTable } from '@/components/lots/lot-table'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ActivityIcon } from 'lucide-react'

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

  const summary = useMemo(() => {
    const totalLots = lots.length
    const awaitingApproval = lots.filter((lot) => lot.status === LotStatus.PENDING_APPROVAL).length
    const inInspection = lots.filter((lot) => lot.status === LotStatus.INSPECTION).length
    const averageProgress = totalLots
      ? Math.round(
          lots.reduce((sum, lot) => sum + (lot.inspectedProgress ?? 0), 0) / totalLots,
        )
      : 0
    const averageDefectRate = totalLots
      ? (lots.reduce((sum, lot) => sum + (lot.defectRate ?? 0), 0) / totalLots).toFixed(1)
      : '0.0'

    return {
      totalLots,
      awaitingApproval,
      inInspection,
      averageProgress,
      averageDefectRate,
    }
  }, [lots])

  const pageActions = canManageLots ? (
    <Button onClick={() => setIsLotModalOpen(true)}>New lot</Button>
  ) : undefined

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Lots"
          description="Monitor inspection readiness, approvals, and supplier performance."
          actions={pageActions}
        />
        <Card>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Lots"
        description="Monitor inspection readiness, approvals, and supplier performance."
        actions={pageActions}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total lots</CardDescription>
            <CardTitle>{summary.totalLots}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>In inspection</CardDescription>
            <CardTitle>{summary.inInspection}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Awaiting approval</CardDescription>
            <CardTitle>{summary.awaitingApproval}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Average defect rate</CardDescription>
            <CardTitle>{summary.averageDefectRate}%</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-neutral-500">
              {summary.averageProgress}% average inspection progress across active lots.
            </p>
          </CardContent>
        </Card>
      </div>

      <LotFilters
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        factoryFilter={factoryFilter}
        setFactoryFilter={setFactoryFilter}
        factories={factories}
      />

      {filteredLots.length === 0 ? (
        <EmptyState
          icon={<ActivityIcon className="h-5 w-5" />}
          title="No lots match your filters"
          description={
            statusFilter !== 'all' || factoryFilter !== 'all'
              ? 'Adjust the filters to broaden your search.'
              : 'Seed the database to explore sample production lots.'
          }
          action={
            canManageLots
              ? {
                  label: 'Create lot',
                  onClick: () => setIsLotModalOpen(true),
                }
              : undefined
          }
        />
      ) : (
        <LotTable lots={filteredLots} />
      )}

      <LotFormModal isOpen={isLotModalOpen} onClose={() => setIsLotModalOpen(false)} />
    </div>
  )
}
