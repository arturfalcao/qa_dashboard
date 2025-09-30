'use client'

import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Lot } from '@qa-dashboard/shared'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

interface DefectTrendChartProps {
  lots: Lot[]
}

export function DefectTrendChart({ lots }: DefectTrendChartProps) {
  const chartData = useMemo(() => {
    // Group lots by date and calculate average defect rate
    const dataByDate = new Map<string, { total: number; count: number; defectRate: number }>()

    lots.forEach((lot) => {
      const date = new Date(lot.createdAt).toISOString().split('T')[0]
      const existing = dataByDate.get(date) || { total: 0, count: 0, defectRate: 0 }

      existing.total += (lot.defectRate ?? 0) * 100
      existing.count += 1
      existing.defectRate = existing.total / existing.count

      dataByDate.set(date, existing)
    })

    // Convert to array and sort by date
    return Array.from(dataByDate.entries())
      .map(([date, data]) => ({
        date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        defectRate: Number(data.defectRate.toFixed(2)),
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .slice(-14) // Last 14 days
  }, [lots])

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Defect Rate Trend</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Defect Rate Trend</CardTitle>
        <CardDescription>Average defect rate over the last 14 days</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#64748b', fontSize: 12 }}
              stroke="#cbd5e1"
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 12 }}
              stroke="#cbd5e1"
              label={{ value: 'Defect Rate (%)', angle: -90, position: 'insideLeft', style: { fill: '#64748b' } }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
              }}
              formatter={(value: number) => [`${value}%`, 'Defect Rate']}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="defectRate"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ fill: '#ef4444', r: 4 }}
              activeDot={{ r: 6 }}
              name="Defect Rate (%)"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
