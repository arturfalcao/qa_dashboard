'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { Lot, LotStatus, UserRole } from '@qa-dashboard/shared'
import { LotFilters } from '@/components/lots/lot-filters'
import { LotFormModal } from '@/components/lots/lot-form-modal'
import { TechPackWizard } from '@/components/lots/tech-pack-wizard'
import { useAuth } from '@/components/providers/auth-provider'
import { LotTable } from '@/components/lots/lot-table'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ActivityIcon, FileText, Sparkles } from 'lucide-react'

export default function LotsPage() {
  const params = useParams()
  const tenantSlug = params.tenantSlug as string
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [factoryFilter, setFactoryFilter] = useState<string>('all')
  const [isLotModalOpen, setIsLotModalOpen] = useState(false)
  const [isTechPackWizardOpen, setIsTechPackWizardOpen] = useState(false)
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
    <div className="flex gap-3">
      <Button
        onClick={() => setIsTechPackWizardOpen(true)}
        className="relative group bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white px-5 py-2.5 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-violet-400 to-purple-400 rounded-lg blur-lg opacity-25 group-hover:opacity-40 transition-opacity"></div>
        <div className="relative flex items-center gap-2">
          <FileText className="h-4 w-4" />
          <span className="font-semibold">Tech Pack Magic</span>
          <Sparkles className="h-4 w-4 text-yellow-300 animate-pulse" />
        </div>
      </Button>
      <Button onClick={() => setIsLotModalOpen(true)} variant="secondary">
        New lot
      </Button>
    </div>
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

      <TechPackWizard
        isOpen={isTechPackWizardOpen}
        onClose={() => setIsTechPackWizardOpen(false)}
        tenantSlug={tenantSlug}
      />
    </div>
  )
}
