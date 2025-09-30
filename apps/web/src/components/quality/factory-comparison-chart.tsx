'use client'

import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell } from 'recharts'
import { Lot } from '@qa-dashboard/shared'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

interface FactoryComparisonChartProps {
  lots: Lot[]
}

export function FactoryComparisonChart({ lots }: FactoryComparisonChartProps) {
  const chartData = useMemo(() => {
    // Group lots by factory and calculate metrics
    const dataByFactory = new Map<string, { totalLots: number; totalDefectRate: number; approved: number; rejected: number }>()

    lots.forEach((lot) => {
      const factoryName = lot.factory?.name || 'Unknown'
      const existing = dataByFactory.get(factoryName) || {
        totalLots: 0,
        totalDefectRate: 0,
        approved: 0,
        rejected: 0,
      }

      existing.totalLots += 1
      existing.totalDefectRate += (lot.defectRate ?? 0) * 100

      if (lot.status === 'APPROVED') existing.approved += 1
      if (lot.status === 'REJECTED') existing.rejected += 1

      dataByFactory.set(factoryName, existing)
    })

    // Convert to array with calculated averages
    return Array.from(dataByFactory.entries())
      .map(([factory, data]) => ({
        factory: factory.length > 20 ? factory.substring(0, 20) + '...' : factory,
        avgDefectRate: Number((data.totalDefectRate / data.totalLots).toFixed(2)),
        totalLots: data.totalLots,
        approvalRate: data.totalLots > 0 ? Number(((data.approved / data.totalLots) * 100).toFixed(1)) : 0,
      }))
      .sort((a, b) => b.avgDefectRate - a.avgDefectRate) // Sort by highest defect rate
      .slice(0, 8) // Top 8 factories
  }, [lots])

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Factory Performance Comparison</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Factory Performance Comparison</CardTitle>
        <CardDescription>Average defect rate and approval rate by factory</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              type="number"
              tick={{ fill: '#64748b', fontSize: 12 }}
              stroke="#cbd5e1"
              label={{ value: 'Defect Rate (%)', position: 'insideBottom', offset: -5, style: { fill: '#64748b' } }}
            />
            <YAxis
              type="category"
              dataKey="factory"
              tick={{ fill: '#64748b', fontSize: 11 }}
              stroke="#cbd5e1"
              width={120}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
              }}
              formatter={(value: number, name: string) => {
                if (name === 'avgDefectRate') return [`${value}%`, 'Avg Defect Rate']
                if (name === 'approvalRate') return [`${value}%`, 'Approval Rate']
                return [value, name]
              }}
            />
            <Legend />
            <Bar dataKey="avgDefectRate" name="Avg Defect Rate (%)" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.avgDefectRate > 5 ? '#ef4444' : entry.avgDefectRate > 2 ? '#f59e0b' : '#10b981'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
