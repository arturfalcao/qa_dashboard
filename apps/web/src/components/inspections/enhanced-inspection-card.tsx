'use client'

import { useState } from 'react'
import { Inspection, DefectSeverity, ProcessStation } from '@qa-dashboard/shared'
import { formatRelativeTime, getDefectColor, cn } from '@/lib/utils'
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  EyeIcon,
  ThermometerIcon,
  DropletIcon,
  SunIcon,
  UserIcon,
  ImageIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from 'lucide-react'
import { EnhancedPhotoGallery } from '../photos/enhanced-photo-gallery'

interface EnhancedInspectionCardProps {
  inspection: Inspection
  showPhotos?: boolean
  onPhotosToggle?: () => void
}

const SEVERITY_ICONS = {
  [DefectSeverity.CRITICAL]: '🔴',
  [DefectSeverity.MAJOR]: '🟠',
  [DefectSeverity.MINOR]: '🟡',
}

const SEVERITY_COLORS = {
  [DefectSeverity.CRITICAL]: 'bg-red-100 text-red-800 border-red-200',
  [DefectSeverity.MAJOR]: 'bg-orange-100 text-orange-800 border-orange-200',
  [DefectSeverity.MINOR]: 'bg-yellow-100 text-yellow-800 border-yellow-200',
}

const STATION_LABELS: Record<ProcessStation, string> = {
  [ProcessStation.RECEIVING]: 'Receiving',
  [ProcessStation.INITIAL_INSPECTION]: 'Initial Inspection',
  [ProcessStation.IRONING]: 'Ironing',
  [ProcessStation.FOLDING]: 'Folding',
  [ProcessStation.QUALITY_CHECK]: 'Quality Check',
  [ProcessStation.PACKING]: 'Packing',
  [ProcessStation.FINAL_INSPECTION]: 'Final Inspection',
  [ProcessStation.DISPATCH]: 'Dispatch',
}

export function EnhancedInspectionCard({
  inspection,
  showPhotos = false,
  onPhotosToggle
}: EnhancedInspectionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const { garment, hasDefect, defectType, defectSeverity, inspectedAt, processStation, assignedWorker, qualityScore } = inspection
  const batch = garment?.batch
  const vendor = batch?.vendor
  const style = batch?.style

  const environmentalConditions = inspection.environmentalConditions

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Main Card Content */}
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Status and Timing */}
            <div className="flex items-center space-x-3 mb-4">
              {hasDefect ? (
                <div className="flex items-center space-x-2">
                  <AlertTriangleIcon className="w-5 h-5 text-red-500" />
                  <div className="flex items-center space-x-1">
                    <span className={cn('px-2 py-1 text-xs font-medium rounded-full border', getDefectColor(defectType || ''))}>
                      {defectType?.replace('_', ' ').toUpperCase()}
                    </span>
                    {defectSeverity && (
                      <span className={cn('px-2 py-1 text-xs font-medium rounded-full border', SEVERITY_COLORS[defectSeverity])}>
                        {SEVERITY_ICONS[defectSeverity]} {defectSeverity.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <CheckCircleIcon className="w-5 h-5 text-green-500" />
                  <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full border border-green-200">
                    ✓ PASS
                  </span>
                  {qualityScore && (
                    <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full border border-blue-200">
                      Quality: {qualityScore}/100
                    </span>
                  )}
                </div>
              )}

              <span className="text-sm text-gray-500">
                {formatRelativeTime(inspectedAt)}
              </span>
            </div>

            {/* Process Station */}
            <div className="mb-4">
              <div className="inline-flex items-center px-3 py-1 bg-primary-50 text-primary-700 text-sm font-medium rounded-full border border-primary-200">
                <EyeIcon className="w-4 h-4 mr-1" />
                {STATION_LABELS[processStation]}
              </div>
            </div>

            {/* Garment Details */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
              <div>
                <div className="text-gray-500">Garment</div>
                <div className="font-medium">{garment?.serial}</div>
              </div>
              <div>
                <div className="text-gray-500">Vendor</div>
                <div className="font-medium">{vendor?.name}</div>
              </div>
              <div>
                <div className="text-gray-500">Style</div>
                <div className="font-medium">{style?.styleCode}</div>
              </div>
              <div>
                <div className="text-gray-500">PO</div>
                <div className="font-medium">{batch?.poNumber}</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm mb-4">
              <div>
                <div className="text-gray-500">Size</div>
                <div className="font-medium">{garment?.size}</div>
              </div>
              <div>
                <div className="text-gray-500">Color</div>
                <div className="font-medium">{garment?.color}</div>
              </div>
            </div>

            {/* Worker Assignment */}
            {assignedWorker && (
              <div className="mb-4">
                <div className="flex items-center text-sm text-gray-600">
                  <UserIcon className="w-4 h-4 mr-2" />
                  Inspected by: <span className="font-medium ml-1">{assignedWorker}</span>
                </div>
              </div>
            )}

            {/* Notes */}
            {inspection.notes && (
              <div className="mb-4">
                <div className="text-gray-500 text-sm mb-1">Notes</div>
                <div className="text-gray-900 bg-gray-50 p-3 rounded-md text-sm">
                  {inspection.notes}
                </div>
              </div>
            )}

            {/* Environmental Conditions */}
            {environmentalConditions && (
              <div className="mb-4">
                <div className="text-gray-500 text-sm mb-2">Environmental Conditions</div>
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center text-gray-600">
                    <ThermometerIcon className="w-4 h-4 mr-1" />
                    {environmentalConditions.temperature}°C
                  </div>
                  <div className="flex items-center text-gray-600">
                    <DropletIcon className="w-4 h-4 mr-1" />
                    {environmentalConditions.humidity}%
                  </div>
                  <div className="flex items-center text-gray-600">
                    <SunIcon className="w-4 h-4 mr-1" />
                    {environmentalConditions.lightingLevel} lux
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Legacy Photo Thumbnails (if no enhanced photos) */}
          {(inspection.photoUrlBefore || inspection.photoUrlAfter) && (
            <div className="ml-6 flex space-x-2">
              {inspection.photoUrlBefore && (
                <div className="relative">
                  <div className="w-24 h-24 bg-gray-100 rounded-lg overflow-hidden">
                    <img
                      src={inspection.photoUrlBefore}
                      alt="Before inspection"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement
                        target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOTYiIGhlaWdodD0iOTYiIHZpZXdCb3g9IjAgMCA5NiA5NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9Ijk2IiBoZWlnaHQ9Ijk2IiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik00OCA0OEM0Mi40NzcgNDggMzggNTIuNDc3IDM4IDU4VjY4QzM4IDczLjUyMyA0Mi40NzcgNzggNDggNzhINThDNjMuNTIzIDc4IDY4IDczLjUyMyA2OCA2OFY1OEM2OCA1Mi40NzcgNjMuNTIzIDQ4IDU4IDQ4SDQ4WiIgZmlsbD0iIzlDQTNBRiIvPgo8L3N2Zz4K'
                      }}
                    />
                  </div>
                  <div className="absolute bottom-1 left-1 bg-black bg-opacity-50 text-white text-xs px-1 rounded">
                    Before
                  </div>
                </div>
              )}

              {inspection.photoUrlAfter && (
                <div className="relative">
                  <div className="w-24 h-24 bg-gray-100 rounded-lg overflow-hidden">
                    <img
                      src={inspection.photoUrlAfter}
                      alt="After inspection"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement
                        target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOTYiIGhlaWdodD0iOTYiIHZpZXdCb3g9IjAgMCA5NiA5NiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9Ijk2IiBoZWlnaHQ9Ijk2IiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik00OCA0OEM0Mi40NzcgNDggMzggNTIuNDc3IDM4IDU4VjY4QzM4IDczLjUyMyA0Mi40NzcgNzggNDggNzhINThDNjMuNTIzIDc4IDY4IDczLjUyMyA2OCA2OFY1OEM2OCA1Mi40NzcgNjMuNTIzIDQ4IDU4IDQ4SDQ4WiIgZmlsbD0iIzlDQTNBRiIvPgo8L3N2Zz4K'
                      }}
                    />
                  </div>
                  <div className="absolute bottom-1 left-1 bg-black bg-opacity-50 text-white text-xs px-1 rounded">
                    After
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Enhanced Photo Gallery Toggle */}
        <div className="mt-4 pt-4 border-t border-gray-100">
          <button
            onClick={() => {
              setIsExpanded(!isExpanded)
              onPhotosToggle?.()
            }}
            className="flex items-center justify-between w-full text-left hover:bg-gray-50 -mx-2 px-2 py-2 rounded transition-colors"
          >
            <div className="flex items-center space-x-2 text-sm font-medium text-gray-700">
              <ImageIcon className="w-4 h-4" />
              <span>Multi-Angle Photo Gallery</span>
            </div>
            {isExpanded ? (
              <ChevronUpIcon className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-4 h-4 text-gray-400" />
            )}
          </button>
        </div>
      </div>

      {/* Enhanced Photo Gallery */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <EnhancedPhotoGallery
            inspectionId={inspection.id}
            readonly={true}
          />
        </div>
      )}
    </div>
  )
}