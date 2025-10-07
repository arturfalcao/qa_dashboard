'use client'

import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { apiClient } from '@/lib/api'
import { MetricCard } from '@/components/analytics/metric-card'
import { DefectRateChart } from '@/components/analytics/defect-rate-chart'
import { ThroughputChart } from '@/components/analytics/throughput-chart'
import { DefectTypesChart } from '@/components/analytics/defect-types-chart'
import { AnalyticsFilters } from '@/components/analytics/analytics-filters'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useRouter, useParams } from 'next/navigation'

export default function AnalyticsPage() {
  const [range, setRange] = useState<'last_7d' | 'last_30d'>('last_7d')
  const [groupBy, setGroupBy] = useState<'style' | 'factory'>('factory')

  const router = useRouter()
  const params = useParams()
  const tenantSlug = params?.tenantSlug as string

  const { data: defectRate, isLoading: defectRateLoading } = useQuery({
    queryKey: ['analytics', 'defect-rate', groupBy, range],
    queryFn: () => apiClient.getDefectRate(groupBy, range),
  })

  const { data: throughput, isLoading: throughputLoading } = useQuery({
    queryKey: ['analytics', 'throughput', range],
    queryFn: () => apiClient.getThroughput('day', range),
  })

  const { data: defectTypes, isLoading: defectTypesLoading } = useQuery({
    queryKey: ['analytics', 'defect-types', range],
    queryFn: () => apiClient.getDefectTypes(range),
  })

  const { data: approvalTime, isLoading: approvalTimeLoading } = useQuery({
    queryKey: ['analytics', 'approval-time', range],
    queryFn: () => apiClient.getApprovalTime(range),
  })

  const { data: lots = [], isLoading: lotsLoading } = useQuery({
    queryKey: ['lots'],
    queryFn: () => apiClient.getLots(),
  })

  const { data: factories = [], isLoading: factoriesLoading } = useQuery({
    queryKey: ['factories'],
    queryFn: () => apiClient.getFactories(),
  })

  const { data: clients = [], isLoading: clientsLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.listClients(),
  })

  const totals = useMemo(
    () =>
      defectRate?.data?.reduce(
        (acc, item) => {
          acc.totalInspected += item.totalInspected
          acc.totalDefects += item.totalDefects
          return acc
        },
        { totalInspected: 0, totalDefects: 0 },
      ) || { totalInspected: 0, totalDefects: 0 },
    [defectRate?.data],
  )

  const overallDefectRate = totals.totalInspected
    ? (totals.totalDefects / totals.totalInspected) * 100
    : 0

  const totalThroughput = throughput?.data?.reduce((sum, d) => sum + d.inspections, 0) || 0

  // Production pipeline metrics
  const pipelineMetrics = useMemo(() => {
    const inProduction = lots.filter((l: any) => l.status === 'IN_PRODUCTION')
    const inInspection = lots.filter((l: any) => l.status === 'INSPECTION')
    const pendingApproval = lots.filter((l: any) => l.status === 'PENDING_APPROVAL')
    const approved = lots.filter((l: any) => l.status === 'APPROVED')
    const rejected = lots.filter((l: any) => l.status === 'REJECTED')
    const shipped = lots.filter((l: any) => l.status === 'SHIPPED')

    const unitsInProduction = inProduction.reduce((sum: number, l: any) => sum + (l.quantityTotal || 0), 0)
    const unitsInInspection = inInspection.reduce((sum: number, l: any) => sum + (l.quantityTotal || 0), 0)
    const unitsAwaitingApproval = pendingApproval.reduce((sum: number, l: any) => sum + (l.quantityTotal || 0), 0)

    const approvalRate = approved.length + rejected.length > 0
      ? (approved.length / (approved.length + rejected.length)) * 100
      : 100

    return {
      inProduction: inProduction.length,
      inInspection: inInspection.length,
      pendingApproval: pendingApproval.length,
      unitsInProduction,
      unitsInInspection,
      unitsAwaitingApproval,
      approvalRate,
      totalShipped: shipped.reduce((sum: number, l: any) => sum + (l.quantityTotal || 0), 0),
    }
  }, [lots])

  // Factory performance metrics
  const factoryPerformance = useMemo(() => {
    const activeLots = lots.filter((l: any) =>
      ['IN_PRODUCTION', 'INSPECTION', 'PENDING_APPROVAL'].includes(l.status)
    )

    const factoryStats = new Map()
    activeLots.forEach((lot: any) => {
      const factoryName = lot.factory?.name || lot.suppliers?.find((s: any) => s.isPrimary)?.factory?.name || 'Unknown'
      const factoryId = lot.factory?.id || lot.suppliers?.find((s: any) => s.isPrimary)?.factoryId || 'unknown'

      if (!factoryStats.has(factoryId)) {
        factoryStats.set(factoryId, {
          name: factoryName,
          lots: 0,
          units: 0,
          defects: [],
        })
      }

      const stats = factoryStats.get(factoryId)
      stats.lots++
      stats.units += lot.quantityTotal || 0
      stats.defects.push(lot.defectRate || 0)
    })

    return Array.from(factoryStats.values())
      .map((f: any) => ({
        ...f,
        avgDefectRate: f.defects.length > 0
          ? f.defects.reduce((sum: number, d: number) => sum + d, 0) / f.defects.length
          : 0,
      }))
      .sort((a, b) => b.lots - a.lots)
      .slice(0, 5)
  }, [lots])

  // Client order metrics
  const clientMetrics = useMemo(() => {
    const clientStats = new Map()

    clients.forEach((client: any) => {
      clientStats.set(client.id, {
        id: client.id,
        name: client.name,
        lots: 0,
        units: 0,
        defects: [],
        inProduction: 0,
        inInspection: 0,
        pendingApproval: 0,
        approved: 0,
        shipped: 0,
        rejected: 0,
      })
    })

    lots.forEach((lot: any) => {
      if (!lot.clientId) return

      if (!clientStats.has(lot.clientId)) {
        clientStats.set(lot.clientId, {
          id: lot.clientId,
          name: 'Unknown Client',
          lots: 0,
          units: 0,
          defects: [],
          inProduction: 0,
          inInspection: 0,
          pendingApproval: 0,
          approved: 0,
          shipped: 0,
          rejected: 0,
        })
      }

      const stats = clientStats.get(lot.clientId)
      stats.lots++
      stats.units += lot.quantityTotal || 0
      stats.defects.push(lot.defectRate || 0)

      if (lot.status === 'IN_PRODUCTION') stats.inProduction++
      if (lot.status === 'INSPECTION') stats.inInspection++
      if (lot.status === 'PENDING_APPROVAL') stats.pendingApproval++
      if (lot.status === 'APPROVED') stats.approved++
      if (lot.status === 'SHIPPED') stats.shipped++
      if (lot.status === 'REJECTED') stats.rejected++
    })

    return Array.from(clientStats.values())
      .filter((c: any) => c.lots > 0)
      .map((c: any) => ({
        ...c,
        avgDefectRate: c.defects.length > 0
          ? c.defects.reduce((sum: number, d: number) => sum + d, 0) / c.defects.length
          : 0,
      }))
      .sort((a, b) => b.units - a.units)
  }, [lots, clients])

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        description="Quality control metrics and insights across production."
      />

      <AnalyticsFilters
        range={range}
        setRange={setRange}
        groupBy={groupBy}
        setGroupBy={setGroupBy}
      />

      {/* Production Pipeline Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Production Pipeline</CardTitle>
          <CardDescription>Current state of all lots in the production system</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-700">{pipelineMetrics.inProduction}</div>
              <div className="text-xs text-blue-600 mt-1">In Production</div>
              <div className="text-xs text-blue-500 mt-1">{pipelineMetrics.unitsInProduction.toLocaleString()} units</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-700">{pipelineMetrics.inInspection}</div>
              <div className="text-xs text-purple-600 mt-1">In Inspection</div>
              <div className="text-xs text-purple-500 mt-1">{pipelineMetrics.unitsInInspection.toLocaleString()} units</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-700">{pipelineMetrics.pendingApproval}</div>
              <div className="text-xs text-yellow-600 mt-1">Pending Approval</div>
              <div className="text-xs text-yellow-500 mt-1">{pipelineMetrics.unitsAwaitingApproval.toLocaleString()} units</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-700">{pipelineMetrics.approvalRate.toFixed(0)}%</div>
              <div className="text-xs text-green-600 mt-1">Approval Rate</div>
              <div className="text-xs text-green-500 mt-1">{pipelineMetrics.totalShipped.toLocaleString()} units shipped</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Defect Rate"
          value={`${overallDefectRate.toFixed(1)}%`}
          isLoading={defectRateLoading}
          trend={overallDefectRate < 5 ? 'good' : 'warning'}
          icon="alert-triangle"
        />

        <MetricCard
          title="Avg Approval Time"
          value={`${approvalTime?.average.toFixed(1) || '0.0'}h`}
          isLoading={approvalTimeLoading}
          trend={approvalTime?.average && approvalTime.average < 24 ? 'good' : 'warning'}
          icon="clock"
        />

        <MetricCard
          title="Throughput"
          value={`${totalThroughput} inspections`}
          isLoading={throughputLoading}
          subtitle={range === 'last_7d' ? 'Last 7 days' : 'Last 30 days'}
          icon="activity"
        />

        <MetricCard
          title="Total Inspected"
          value={`${totals.totalInspected}`}
          isLoading={defectRateLoading}
          subtitle={`${totals.totalDefects} defects detected`}
          icon="package"
        />
      </div>

      {/* Client Orders Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Client Orders Overview</CardTitle>
          <CardDescription>Order volume and status breakdown by client</CardDescription>
        </CardHeader>
        <CardContent>
          {clientMetrics.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No client orders found</div>
          ) : (
            <div className="space-y-4">
              {clientMetrics.map((client: any) => (
                <div key={client.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="font-semibold text-gray-900">{client.name}</div>
                      <div className="text-sm text-gray-600 mt-1">
                        {client.lots} lot{client.lots !== 1 ? 's' : ''} · {client.units.toLocaleString()} units total
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-lg font-bold ${client.avgDefectRate > 5 ? 'text-red-600' : 'text-green-600'}`}>
                        {client.avgDefectRate.toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-500">Avg defect rate</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mt-3">
                    {client.inProduction > 0 && (
                      <div className="text-center px-2 py-1.5 bg-blue-50 rounded text-xs">
                        <div className="font-semibold text-blue-700">{client.inProduction}</div>
                        <div className="text-blue-600">Production</div>
                      </div>
                    )}
                    {client.inInspection > 0 && (
                      <div className="text-center px-2 py-1.5 bg-purple-50 rounded text-xs">
                        <div className="font-semibold text-purple-700">{client.inInspection}</div>
                        <div className="text-purple-600">Inspection</div>
                      </div>
                    )}
                    {client.pendingApproval > 0 && (
                      <div className="text-center px-2 py-1.5 bg-yellow-50 rounded text-xs">
                        <div className="font-semibold text-yellow-700">{client.pendingApproval}</div>
                        <div className="text-yellow-600">Pending</div>
                      </div>
                    )}
                    {client.approved > 0 && (
                      <div className="text-center px-2 py-1.5 bg-green-50 rounded text-xs">
                        <div className="font-semibold text-green-700">{client.approved}</div>
                        <div className="text-green-600">Approved</div>
                      </div>
                    )}
                    {client.shipped > 0 && (
                      <div className="text-center px-2 py-1.5 bg-emerald-50 rounded text-xs">
                        <div className="font-semibold text-emerald-700">{client.shipped}</div>
                        <div className="text-emerald-600">Shipped</div>
                      </div>
                    )}
                    {client.rejected > 0 && (
                      <div className="text-center px-2 py-1.5 bg-red-50 rounded text-xs">
                        <div className="font-semibold text-red-700">{client.rejected}</div>
                        <div className="text-red-600">Rejected</div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Factory Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Active Factory Performance</CardTitle>
          <CardDescription>Top 5 factories by active lot count (In Production, Inspection, Pending Approval)</CardDescription>
        </CardHeader>
        <CardContent>
          {factoryPerformance.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No active production lots</div>
          ) : (
            <div className="space-y-4">
              {factoryPerformance.map((factory: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">{factory.name}</div>
                    <div className="text-sm text-gray-600 mt-1">
                      {factory.lots} active lot{factory.lots !== 1 ? 's' : ''} · {factory.units.toLocaleString()} units
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-lg font-bold ${factory.avgDefectRate > 5 ? 'text-red-600' : 'text-green-600'}`}>
                      {factory.avgDefectRate.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">Avg defect rate</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Throughput trend</CardTitle>
            <CardDescription>Inspections processed per day in the selected period.</CardDescription>
          </CardHeader>
          <CardContent>
            <ThroughputChart data={throughput?.data || []} isLoading={throughputLoading} range={range} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Defect type breakdown</CardTitle>
            <CardDescription>Distribution of confirmed defects by category.</CardDescription>
          </CardHeader>
          <CardContent>
            <DefectTypesChart data={defectTypes?.data || []} isLoading={defectTypesLoading} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Defect rate comparison</CardTitle>
          <CardDescription>Highlight hotspots by {groupBy === 'factory' ? 'factory' : 'style'}.</CardDescription>
        </CardHeader>
        <CardContent>
          <DefectRateChart data={defectRate?.data || []} isLoading={defectRateLoading} groupBy={groupBy} />
        </CardContent>
      </Card>
    </div>
  )
}
