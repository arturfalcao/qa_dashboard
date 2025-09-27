'use client'

import { Lot, LotStatus } from '@qa-dashboard/shared'
import { formatDate, getLotStatusColor, cn, formatPercentage, formatNumber } from '@/lib/utils'
import { CheckIcon, XIcon } from 'lucide-react'

interface LotHeaderProps {
  lot: Lot
  canApprove: boolean
  onApprove: () => void
  onReject: () => void
  onEdit?: () => void
  canEdit?: boolean
}

export function LotHeader({ lot, canApprove, onApprove, onReject, onEdit, canEdit }: LotHeaderProps) {
  const suppliers = lot.suppliers?.slice().sort((a, b) => a.sequence - b.sequence) ?? []
  const primarySupplier = suppliers.find((supplier) => supplier.isPrimary)?.factory ?? lot.factory
  const dppUrl = lot.dppMetadata?.publicUrl
  const isApproved = lot.status === LotStatus.APPROVED

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-4">
            <h1 className="text-2xl font-bold text-gray-900">{lot.styleRef}</h1>
            <span className={cn('px-3 py-1 text-sm font-medium rounded-full', getLotStatusColor(lot.status))}>
              {lot.status.replace('_', ' ')}
            </span>
            {isApproved && dppUrl && (
              <a
                href={dppUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
              >
                View DPP
              </a>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-gray-500">Primary factory</div>
              <div className="font-semibold text-gray-900">{primarySupplier?.name || 'Unassigned'}</div>
              <div className="text-sm text-gray-500">
                {primarySupplier?.city ? `${primarySupplier.city}, ` : ''}
                {primarySupplier?.country ?? ''}
              </div>
              {suppliers.length > 0 && (
                <div className="mt-3 space-y-1">
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">Supply chain</div>
                  <ul className="space-y-1">
                    {suppliers.map((supplier, index) => (
                      <li key={`${supplier.factoryId}-${index}`} className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
                        <span className="text-xs text-gray-400">{index + 1}.</span>
                        <span>{supplier.factory?.name || 'Unknown factory'}</span>
                        {supplier.stage && (
                          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                            {supplier.stage}
                          </span>
                        )}
                        {supplier.isPrimary && (
                          <span className="rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700">
                            Primary
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div>
              <div className="text-sm text-gray-500">Quantity</div>
              <div className="font-semibold text-gray-900">{formatNumber(lot.quantityTotal)}</div>
            </div>

            <div>
              <div className="text-sm text-gray-500">Progress</div>
              <div className="font-semibold text-gray-900">{formatPercentage(lot.inspectedProgress)}</div>
            </div>

            <div>
              <div className="text-sm text-gray-500">Defect Rate</div>
              <div className="font-semibold text-gray-900">{formatPercentage(lot.defectRate)}</div>
            </div>

            <div>
              <div className="text-sm text-gray-500">Created</div>
              <div className="font-semibold text-gray-900">{formatDate(lot.createdAt)}</div>
            </div>

            <div>
              <div className="text-sm text-gray-500">Updated</div>
              <div className="font-semibold text-gray-900">{formatDate(lot.updatedAt)}</div>
            </div>
          </div>
        </div>

        <div className="flex space-x-3 ml-6">
          {canEdit && onEdit && (
            <button
              onClick={onEdit}
              className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Edit
            </button>
          )}
          {canApprove && (
            <>
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
            </>
          )}
        </div>
      </div>
    </div>
  )
}
