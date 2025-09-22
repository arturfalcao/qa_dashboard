'use client'

import { 
  AlertTriangleIcon, 
  ClockIcon, 
  ActivityIcon, 
  PackageIcon,
  TrendingUpIcon,
  TrendingDownIcon
} from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string
  subtitle?: string
  isLoading?: boolean
  trend?: 'good' | 'warning' | 'danger'
  icon: 'alert-triangle' | 'clock' | 'activity' | 'package'
}

const iconMap = {
  'alert-triangle': AlertTriangleIcon,
  'clock': ClockIcon,
  'activity': ActivityIcon,
  'package': PackageIcon,
}

const iconColorMap = {
  'alert-triangle': 'text-red-600 bg-red-100',
  'clock': 'text-yellow-600 bg-yellow-100',
  'activity': 'text-blue-600 bg-blue-100',
  'package': 'text-green-600 bg-green-100',
}

export function MetricCard({ title, value, subtitle, isLoading, trend, icon }: MetricCardProps) {
  const Icon = iconMap[icon]
  const iconColors = iconColorMap[icon]

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconColors}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <div className="flex items-center mt-1">
            {isLoading ? (
              <div className="h-8 w-16 bg-gray-200 rounded animate-pulse"></div>
            ) : (
              <>
                <p className="text-2xl font-semibold text-gray-900">{value}</p>
                {trend && (
                  <div className="ml-2">
                    {trend === 'good' ? (
                      <TrendingDownIcon className="w-4 h-4 text-green-500" />
                    ) : (
                      <TrendingUpIcon className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
      </div>
    </div>
  )
}