'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Batch } from '@qa-dashboard/shared'
import { formatDate, formatNumber, formatPercentage, getBatchStatusColor, cn } from '@/lib/utils'
import { EyeIcon, PackageIcon } from 'lucide-react'

interface BatchCardProps {
  batch: Batch
}

export function BatchCard({ batch }: BatchCardProps) {
  const params = useParams()
  const tenantSlug = params.tenantSlug as string

  const defectRate = (batch._count?.inspections && batch._count?.defects) 
    ? (batch._count.defects / batch._count.inspections) * 100 
    : 0

  const inspectionProgress = (batch._count?.garments && batch._count?.inspections) 
    ? (batch._count.inspections / batch._count.garments) * 100 
    : 0

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <PackageIcon className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{batch.poNumber}</h3>
            <p className="text-sm text-gray-500">{batch.vendor?.name}</p>
          </div>
        </div>
        
        <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getBatchStatusColor(batch.status))}>
          {batch.status.replace('_', ' ').toUpperCase()}
        </span>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Style</span>
          <span className="font-medium">{batch.style?.styleCode}</span>
        </div>
        
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Quantity</span>
          <span className="font-medium">{formatNumber(batch.quantity)}</span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Inspected</span>
          <span className="font-medium">
            {batch._count?.inspections || 0} / {batch._count?.garments || 0}
          </span>
        </div>

        {/* Inspection Progress Bar */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-500">Progress</span>
            <span className="font-medium">{formatPercentage(inspectionProgress)}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(inspectionProgress, 100)}%` }}
            ></div>
          </div>
        </div>

        {(batch._count?.inspections ?? 0) > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Defect Rate</span>
            <span className={cn('font-medium', defectRate > 5 ? 'text-red-600' : 'text-green-600')}>
              {formatPercentage(defectRate)}
            </span>
          </div>
        )}

        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Created</span>
          <span className="font-medium">{formatDate(batch.createdAt)}</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <Link 
          href={`/t/${tenantSlug}/batches/${batch.id}`}
          className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-md transition-colors"
        >
          <EyeIcon className="w-4 h-4 mr-2" />
          View Details
        </Link>
      </div>
    </div>
  )
}