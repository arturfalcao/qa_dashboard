'use client'

import { Inspection } from '@qa-dashboard/shared'
import { formatRelativeTime, getDefectColor, cn } from '@/lib/utils'
import { AlertTriangleIcon, CheckCircleIcon, EyeIcon } from 'lucide-react'
import Image from 'next/image'

interface InspectionCardProps {
  inspection: Inspection
}

export function InspectionCard({ inspection }: InspectionCardProps) {
  const { garment, hasDefect, defectType, inspectedAt, photoUrlBefore, photoUrlAfter } = inspection
  const batch = garment?.batch
  const vendor = batch?.vendor
  const style = batch?.style

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-3">
            {hasDefect ? (
              <div className="flex items-center space-x-2">
                <AlertTriangleIcon className="w-5 h-5 text-red-500" />
                <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getDefectColor(defectType || ''))}>
                  {defectType?.toUpperCase()}
                </span>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <CheckCircleIcon className="w-5 h-5 text-green-500" />
                <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                  PASS
                </span>
              </div>
            )}
            
            <span className="text-sm text-gray-500">
              {formatRelativeTime(inspectedAt)}
            </span>
          </div>

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

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500">Size</div>
              <div>{garment?.size}</div>
            </div>
            <div>
              <div className="text-gray-500">Color</div>
              <div>{garment?.color}</div>
            </div>
          </div>

          {inspection.notes && (
            <div className="mt-4">
              <div className="text-gray-500 text-sm mb-1">Notes</div>
              <div className="text-gray-900">{inspection.notes}</div>
            </div>
          )}
        </div>

        <div className="ml-6 flex space-x-2">
          {photoUrlBefore && (
            <div className="relative">
              <div className="w-24 h-24 bg-gray-100 rounded-lg overflow-hidden">
                <Image
                  src={photoUrlBefore}
                  alt="Before inspection"
                  width={96}
                  height={96}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to placeholder on error
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
          
          {photoUrlAfter && (
            <div className="relative">
              <div className="w-24 h-24 bg-gray-100 rounded-lg overflow-hidden">
                <Image
                  src={photoUrlAfter}
                  alt="After inspection"
                  width={96}
                  height={96}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to placeholder on error
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
      </div>
    </div>
  )
}