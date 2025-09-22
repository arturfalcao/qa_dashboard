'use client'

import { Batch } from '@qa-dashboard/shared'
import { formatDate, getBatchStatusColor, cn } from '@/lib/utils'
import { CheckIcon, XIcon } from 'lucide-react'

interface BatchHeaderProps {
  batch: Batch
  canApprove: boolean
  onApprove: () => void
  onReject: () => void
}

export function BatchHeader({ batch, canApprove, onApprove, onReject }: BatchHeaderProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-4">
            <h1 className="text-2xl font-bold text-gray-900">{batch.poNumber}</h1>
            <span className={cn('px-3 py-1 text-sm font-medium rounded-full', getBatchStatusColor(batch.status))}>
              {batch.status.replace('_', ' ').toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-gray-500">Vendor</div>
              <div className="font-semibold text-gray-900">{batch.vendor?.name}</div>
              <div className="text-sm text-gray-500">Code: {batch.vendor?.code}</div>
            </div>

            <div>
              <div className="text-sm text-gray-500">Style</div>
              <div className="font-semibold text-gray-900">{batch.style?.styleCode}</div>
              <div className="text-sm text-gray-500">{batch.style?.description}</div>
            </div>

            <div>
              <div className="text-sm text-gray-500">Quantity</div>
              <div className="font-semibold text-gray-900">{batch.quantity.toLocaleString()}</div>
            </div>

            <div>
              <div className="text-sm text-gray-500">Created</div>
              <div className="font-semibold text-gray-900">{formatDate(batch.createdAt)}</div>
            </div>
          </div>
        </div>

        {canApprove && (
          <div className="flex space-x-3 ml-6">
            <button
              onClick={onReject}
              className="flex items-center px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
            >
              <XIcon className="w-4 h-4 mr-2" />
              Reject
            </button>
            <button
              onClick={onApprove}
              className="flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 transition-colors"
            >
              <CheckIcon className="w-4 h-4 mr-2" />
              Approve
            </button>
          </div>
        )}
      </div>
    </div>
  )
}