'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { apiClient } from '@/lib/api'
import { MetricCard } from '@/components/analytics/metric-card'
import { DefectRateChart } from '@/components/analytics/defect-rate-chart'
import { ThroughputChart } from '@/components/analytics/throughput-chart'
import { DefectTypesChart } from '@/components/analytics/defect-types-chart'
import { AnalyticsFilters } from '@/components/analytics/analytics-filters'

export default function AnalyticsPage() {
  const [range, setRange] = useState<'last_7d' | 'last_30d'>('last_7d')
  const [groupBy, setGroupBy] = useState<'style' | 'factory'>('factory')

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

  const totals = defectRate?.data?.reduce(
    (acc, item) => {
      acc.totalInspected += item.totalInspected
      acc.totalDefects += item.totalDefects
      return acc
    },
    { totalInspected: 0, totalDefects: 0 },
  ) || { totalInspected: 0, totalDefects: 0 }

  const overallDefectRate = totals.totalInspected
    ? (totals.totalDefects / totals.totalInspected) * 100
    : 0

  const totalThroughput = throughput?.data?.reduce((sum, d) => sum + d.inspections, 0) || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">
            Quality control metrics and insights
          </p>
        </div>
      </div>

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
        <ThroughputChart
          data={throughput?.data || []}
          isLoading={throughputLoading}
          range={range}
        />
        
        <DefectTypesChart
          data={defectTypes?.data || []}
          isLoading={defectTypesLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-6">
        <DefectRateChart
          data={defectRate?.data || []}
          isLoading={defectRateLoading}
          groupBy={groupBy}
        />
      </div>
    </div>
  )
}
