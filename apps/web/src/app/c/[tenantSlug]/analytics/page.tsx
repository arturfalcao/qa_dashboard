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

  const pageActions = (
    <Button variant="secondary" onClick={() => router.push(`/c/${tenantSlug}/exports`)}>
      Export data
    </Button>
  )

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        description="Quality control metrics and insights across production."
        actions={pageActions}
      />

      <AnalyticsFilters
        range={range}
        setRange={setRange}
        groupBy={groupBy}
        setGroupBy={setGroupBy}
      />

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
