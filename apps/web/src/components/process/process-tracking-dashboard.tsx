'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Batch, ProcessStation } from '@qa-dashboard/shared'
import { apiClient } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  Package,
  Search,
  Zap,
  Shirt,
  CheckCircle,
  PackageCheck,
  Eye,
  Truck,
  Clock,
  AlertTriangle,
  ArrowRight,
  Filter
} from 'lucide-react'

interface ProcessTrackingDashboardProps {
  className?: string
}

const STATION_CONFIG: Record<ProcessStation, {
  label: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  description: string
}> = {
  [ProcessStation.RECEIVING]: {
    label: 'Receiving',
    icon: Package,
    color: 'bg-blue-500',
    description: 'Items received and logged'
  },
  [ProcessStation.INITIAL_INSPECTION]: {
    label: 'Initial Inspection',
    icon: Search,
    color: 'bg-purple-500',
    description: 'First quality check'
  },
  [ProcessStation.IRONING]: {
    label: 'Ironing',
    icon: Zap,
    color: 'bg-orange-500',
    description: 'Steam pressing and finishing'
  },
  [ProcessStation.FOLDING]: {
    label: 'Folding',
    icon: Shirt,
    color: 'bg-cyan-500',
    description: 'Professional garment folding'
  },
  [ProcessStation.QUALITY_CHECK]: {
    label: 'Quality Check',
    icon: CheckCircle,
    color: 'bg-green-500',
    description: 'Final quality inspection'
  },
  [ProcessStation.PACKING]: {
    label: 'Packing',
    icon: PackageCheck,
    color: 'bg-indigo-500',
    description: 'Careful packaging process'
  },
  [ProcessStation.FINAL_INSPECTION]: {
    label: 'Final Inspection',
    icon: Eye,
    color: 'bg-pink-500',
    description: 'Last quality verification'
  },
  [ProcessStation.DISPATCH]: {
    label: 'Dispatch',
    icon: Truck,
    color: 'bg-emerald-500',
    description: 'Ready for shipping'
  },
}

const PRIORITY_COLORS = {
  low: 'bg-gray-100 text-gray-800',
  normal: 'bg-blue-100 text-blue-800',
  high: 'bg-orange-100 text-orange-800',
  urgent: 'bg-red-100 text-red-800',
}

export function ProcessTrackingDashboard({ className }: ProcessTrackingDashboardProps) {
  const [selectedStation, setSelectedStation] = useState<ProcessStation | null>(null)
  const [selectedPriority, setSelectedPriority] = useState<string | null>(null)

  // Fetch all batches
  const { data: batches = [], isLoading } = useQuery({
    queryKey: ['batches'],
    queryFn: () => apiClient.getBatches(),
    refetchInterval: 10000, // Refresh every 10 seconds for real-time updates
  })

  // Filter batches based on selected filters
  const filteredBatches = batches.filter(batch => {
    if (selectedStation && batch.currentStation !== selectedStation) return false
    if (selectedPriority && batch.priority !== selectedPriority) return false
    return true
  })

  // Calculate station statistics
  const stationStats = Object.values(ProcessStation).map(station => {
    const stationBatches = batches.filter(batch => batch.currentStation === station)
    const urgent = stationBatches.filter(batch => batch.priority === 'urgent').length
    const high = stationBatches.filter(batch => batch.priority === 'high').length

    return {
      station,
      count: stationBatches.length,
      urgent,
      high,
      config: STATION_CONFIG[station]
    }
  })

  const getBatchProgress = (batch: Batch): number => {
    const stations = Object.values(ProcessStation)
    const currentIndex = stations.indexOf(batch.currentStation)
    return ((currentIndex + 1) / stations.length) * 100
  }

  const getEstimatedDelay = (batch: Batch): string | null => {
    if (!batch.estimatedCompletionTime) return null

    const estimated = new Date(batch.estimatedCompletionTime)
    const now = new Date()

    if (estimated < now) {
      const hoursDelayed = Math.ceil((now.getTime() - estimated.getTime()) / (1000 * 60 * 60))
      return `${hoursDelayed}h delayed`
    }

    return null
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Station Overview */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Process Station Overview</h2>
          <div className="text-sm text-gray-500">
            {batches.length} active batches • Updates every 10s
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          {stationStats.map(({ station, count, urgent, high, config }) => {
            const Icon = config.icon
            const isSelected = selectedStation === station

            return (
              <button
                key={station}
                onClick={() => setSelectedStation(isSelected ? null : station)}
                className={cn(
                  'relative p-4 rounded-lg border transition-all duration-200',
                  isSelected
                    ? 'border-primary-300 bg-primary-50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                )}
              >
                <div className="text-center">
                  <div className={cn('w-8 h-8 rounded-full mx-auto mb-2 flex items-center justify-center', config.color)}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <div className="text-sm font-medium text-gray-900 mb-1">{config.label}</div>
                  <div className="text-lg font-bold text-gray-900">{count}</div>

                  {(urgent > 0 || high > 0) && (
                    <div className="flex items-center justify-center space-x-1 mt-2">
                      {urgent > 0 && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          {urgent}
                        </span>
                      )}
                      {high > 0 && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                          {high}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">Priority:</span>
            <div className="flex space-x-1">
              {['low', 'normal', 'high', 'urgent'].map(priority => (
                <button
                  key={priority}
                  onClick={() => setSelectedPriority(selectedPriority === priority ? null : priority)}
                  className={cn(
                    'px-3 py-1 text-xs font-medium rounded-full border transition-colors',
                    selectedPriority === priority
                      ? 'border-primary-300 bg-primary-100 text-primary-800'
                      : 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'
                  )}
                >
                  {priority.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {(selectedStation || selectedPriority) && (
            <button
              onClick={() => {
                setSelectedStation(null)
                setSelectedPriority(null)
              }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Batch List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">
            Active Batches
            {selectedStation && (
              <span className="ml-2 text-sm font-normal text-gray-500">
                • {STATION_CONFIG[selectedStation].label}
              </span>
            )}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {filteredBatches.length} of {batches.length} batches shown
          </p>
        </div>

        <div className="divide-y divide-gray-200">
          {filteredBatches.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Package className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No batches match the current filters</p>
            </div>
          ) : (
            filteredBatches.map(batch => {
              const progress = getBatchProgress(batch)
              const delay = getEstimatedDelay(batch)
              const currentStationConfig = STATION_CONFIG[batch.currentStation]
              const CurrentStationIcon = currentStationConfig.icon

              return (
                <div key={batch.id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-3">
                        <div className={cn('w-8 h-8 rounded-full flex items-center justify-center', currentStationConfig.color)}>
                          <CurrentStationIcon className="w-4 h-4 text-white" />
                        </div>

                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-medium text-gray-900">
                              {batch.vendor?.name} • {batch.style?.styleCode}
                            </span>
                            <span className={cn(
                              'px-2 py-1 text-xs font-medium rounded-full',
                              PRIORITY_COLORS[batch.priority as keyof typeof PRIORITY_COLORS]
                            )}>
                              {batch.priority.toUpperCase()}
                            </span>
                          </div>
                          <div className="text-sm text-gray-500">
                            PO: {batch.poNumber} • {batch.quantity} items
                          </div>
                        </div>
                      </div>

                      <div className="mb-3">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="font-medium text-gray-700">
                            {currentStationConfig.label}
                          </span>
                          <span className="text-gray-500">
                            {Math.round(progress)}% complete
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-primary-600 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">
                          {currentStationConfig.description}
                        </span>

                        {delay && (
                          <div className="flex items-center text-red-600">
                            <AlertTriangle className="w-4 h-4 mr-1" />
                            {delay}
                          </div>
                        )}

                        {batch.estimatedCompletionTime && !delay && (
                          <div className="flex items-center text-gray-500">
                            <Clock className="w-4 h-4 mr-1" />
                            Est. {new Date(batch.estimatedCompletionTime).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="ml-6">
                      <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                        <ArrowRight className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}