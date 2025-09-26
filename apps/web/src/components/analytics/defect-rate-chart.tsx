'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface DefectRateData {
  name: string
  defectRate: number
  totalInspected: number
  totalDefects: number
}

interface DefectRateChartProps {
  data: DefectRateData[]
  isLoading: boolean
  groupBy: 'style' | 'factory'
}

export function DefectRateChart({ data, isLoading, groupBy }: DefectRateChartProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Defect Rate by {groupBy === 'factory' ? 'Factory' : 'Style'}
        </h3>
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  // Filter out overall data point for grouped view
  const chartData = data.filter(item => item.name !== 'Overall')

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Defect Rate by {groupBy === 'factory' ? 'Factory' : 'Style'}
      </h3>
      
      {chartData.length === 0 ? (
        <div className="h-64 flex items-center justify-center text-gray-500">
          No data available for comparison
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                label={{ value: 'Defect Rate (%)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip 
                formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Defect Rate']}
                labelFormatter={(value) => `${groupBy === 'factory' ? 'Factory' : 'Style'}: ${value}`}
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}
              />
              <Bar 
                dataKey="defectRate" 
                fill="#3b82f6"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
