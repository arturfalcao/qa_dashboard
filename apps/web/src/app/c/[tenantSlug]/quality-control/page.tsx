'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Lot, LotStatus } from '@qa-dashboard/shared'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { AlertTriangleIcon, CheckCircleIcon, ClockIcon, TrendingUpIcon } from 'lucide-react'
import Link from 'next/link'

export default function QualityControlPage() {
  const { data: lots = [], isLoading } = useQuery({
    queryKey: ['lots'],
    queryFn: () => apiClient.getLots(),
    refetchInterval: 10000,
  })

  const qualityMetrics = useMemo(() => {
    const totalLots = lots.length
    const pendingApproval = lots.filter((lot) => lot.status === LotStatus.PENDING_APPROVAL)
    const inInspection = lots.filter((lot) => lot.status === LotStatus.INSPECTION)
    const rejected = lots.filter((lot) => lot.status === LotStatus.REJECTED)
    const approved = lots.filter((lot) => lot.status === LotStatus.APPROVED)

    // Calculate average defect rate
    const lotsWithDefects = lots.filter((lot) => lot.defectRate != null && lot.defectRate > 0)
    const averageDefectRate = lotsWithDefects.length
      ? (lotsWithDefects.reduce((sum, lot) => sum + (lot.defectRate ?? 0), 0) / lotsWithDefects.length)
      : 0

    // Identify high-risk lots (defect rate > 5%)
    const highRiskLots = lots.filter((lot) => (lot.defectRate ?? 0) > 0.05)

    // Approval rate
    const completedLots = approved.length + rejected.length
    const approvalRate = completedLots > 0 ? (approved.length / completedLots) * 100 : 0

    return {
      totalLots,
      pendingApproval: pendingApproval.length,
      inInspection: inInspection.length,
      rejected: rejected.length,
      approved: approved.length,
      averageDefectRate: (averageDefectRate * 100).toFixed(2),
      highRiskLots,
      approvalRate: approvalRate.toFixed(1),
      pendingApprovalLots: pendingApproval,
    }
  }, [lots])

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Quality Control Dashboard"
          description="Monitor quality metrics, approvals, and non-conformities"
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
        title="Quality Control Dashboard"
        description="Monitor quality metrics, approvals, and non-conformities"
      />

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Approval</CardTitle>
            <ClockIcon className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{qualityMetrics.pendingApproval}</div>
            <p className="text-xs text-slate-500">Lots awaiting QA decision</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Inspection</CardTitle>
            <ActivityIcon className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{qualityMetrics.inInspection}</div>
            <p className="text-xs text-slate-500">Currently being inspected</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Defect Rate</CardTitle>
            <TrendingUpIcon className="h-4 w-4 text-slate-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{qualityMetrics.averageDefectRate}%</div>
            <p className="text-xs text-slate-500">Across all active lots</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Approval Rate</CardTitle>
            <CheckCircleIcon className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{qualityMetrics.approvalRate}%</div>
            <p className="text-xs text-slate-500">
              {qualityMetrics.approved} approved, {qualityMetrics.rejected} rejected
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Pending Approvals */}
      {qualityMetrics.pendingApprovalLots.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Lots Pending Approval</CardTitle>
            <CardDescription>
              Review and approve/reject completed inspections
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {qualityMetrics.pendingApprovalLots.map((lot: Lot) => (
                <Link
                  key={lot.id}
                  href={`/c/${lot.client?.slug || 'unknown'}/lots/${lot.id}`}
                  className="flex items-center justify-between rounded-lg border border-slate-200 p-4 transition hover:border-primary-300 hover:bg-slate-50"
                >
                  <div>
                    <p className="font-medium text-slate-900">{lot.styleRef}</p>
                    <p className="text-sm text-slate-500">
                      Factory: {lot.factory?.name || 'N/A'} • Defect Rate: {((lot.defectRate ?? 0) * 100).toFixed(2)}%
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-900">
                      {lot.inspectedProgress}% Inspected
                    </p>
                    <p className="text-xs text-slate-500">{lot.quantityTotal} pieces</p>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* High Risk Lots */}
      {qualityMetrics.highRiskLots.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangleIcon className="h-5 w-5 text-red-500" />
              High Risk Lots
            </CardTitle>
            <CardDescription>
              Lots with defect rate above 5% requiring attention
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {qualityMetrics.highRiskLots.map((lot: Lot) => (
                <Link
                  key={lot.id}
                  href={`/c/${lot.client?.slug || 'unknown'}/lots/${lot.id}`}
                  className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-4 transition hover:border-red-300"
                >
                  <div>
                    <p className="font-medium text-slate-900">{lot.styleRef}</p>
                    <p className="text-sm text-slate-600">
                      Factory: {lot.factory?.name || 'N/A'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-red-600">
                      {((lot.defectRate ?? 0) * 100).toFixed(2)}%
                    </p>
                    <p className="text-xs text-slate-600">Defect Rate</p>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quality Summary by Status */}
      <Card>
        <CardHeader>
          <CardTitle>Quality Summary</CardTitle>
          <CardDescription>Overview of lot statuses and quality metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircleIcon className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Approved Lots</p>
                  <p className="text-sm text-slate-500">Passed quality inspection</p>
                </div>
              </div>
              <p className="text-2xl font-bold text-green-600">{qualityMetrics.approved}</p>
            </div>

            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center">
                  <AlertTriangleIcon className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Rejected Lots</p>
                  <p className="text-sm text-slate-500">Failed quality standards</p>
                </div>
              </div>
              <p className="text-2xl font-bold text-red-600">{qualityMetrics.rejected}</p>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                  <ActivityIcon className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">In Progress</p>
                  <p className="text-sm text-slate-500">Currently in inspection</p>
                </div>
              </div>
              <p className="text-2xl font-bold text-blue-600">{qualityMetrics.inInspection}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
