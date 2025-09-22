'use client'

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { DefectType } from '@qa-dashboard/shared'

interface DefectTypeData {
  type: DefectType
  count: number
  percentage: number
}

interface DefectTypesChartProps {
  data: DefectTypeData[]
  isLoading: boolean
}

const COLORS = {
  stain: '#ef4444',
  stitching: '#f97316',
  misprint: '#8b5cf6',
  measurement: '#3b82f6',
  fabric_defect: '#10b981',
  hardware_issue: '#f59e0b',
  discoloration: '#ec4899',
  tear_damage: '#84cc16',
  other: '#6b7280',
}

export function DefectTypesChart({ data, isLoading }: DefectTypesChartProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Defect Type Breakdown</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Defect Type Breakdown</h3>
      
      {data.length === 0 ? (
        <div className="h-64 flex items-center justify-center text-gray-500">
          No defects in selected period
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={80}
                dataKey="count"
                nameKey="type"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.type]} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value, name) => [value, name?.toString().toUpperCase()]}
              />
              <Legend 
                formatter={(value) => value.toString().toUpperCase()}
                wrapperStyle={{ fontSize: '12px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
      
      {data.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-2">
          {data.map((item) => (
            <div key={item.type} className="flex items-center text-sm">
              <div 
                className="w-3 h-3 rounded-full mr-2"
                style={{ backgroundColor: COLORS[item.type] }}
              ></div>
              <span className="text-gray-600">
                {item.type.toUpperCase()}: {item.count} ({item.percentage.toFixed(1)}%)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}