'use client'

import { Lot, LotStatus } from '@qa-dashboard/shared'
import { formatDate, getLotStatusColor, cn, formatPercentage, formatNumber } from '@/lib/utils'
import { CheckIcon, XIcon, ImageIcon } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

interface LotHeaderProps {
  lot: Lot
  canApprove: boolean
  onApprove: () => void
  onReject: () => void
  onEdit?: () => void
  canEdit?: boolean
}

export function LotHeader({ lot, canApprove, onApprove, onReject, onEdit, canEdit }: LotHeaderProps) {
  const params = useParams()
  const tenantSlug = params.tenantSlug as string
  const suppliers = lot.suppliers?.slice().sort((a, b) => a.sequence - b.sequence) ?? []
  const primarySupplier = suppliers.find((supplier) => supplier.isPrimary)?.factory ?? lot.factory
  const dppUrl = lot.dppMetadata?.publicUrl
  const isApproved = lot.status === LotStatus.APPROVED

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center flex-wrap gap-2 mb-3">
            <h1 className="text-xl font-bold text-gray-900">{lot.styleRef}</h1>
            <span className={cn('px-2.5 py-0.5 text-xs font-medium rounded-full', getLotStatusColor(lot.status))}>
              {lot.status.replace('_', ' ')}
            </span>
            {isApproved && dppUrl && (
              <a
                href={dppUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
              >
                View DPP
              </a>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div className="col-span-2 md:col-span-1">
              <div className="text-xs text-gray-500">Primary factory</div>
              <div className="font-medium text-gray-900 text-sm">{primarySupplier?.name || 'Unassigned'}</div>
              <div className="text-xs text-gray-500">
                {primarySupplier?.city ? `${primarySupplier.city}, ` : ''}
                {primarySupplier?.country ?? ''}
              </div>
              {suppliers.length > 1 && (
                <div className="mt-2">
                  <div className="text-xs text-gray-400">+{suppliers.length - 1} more in chain</div>
                </div>
              )}
            </div>

            <div>
              <div className="text-xs text-gray-500">Quantity</div>
              <div className="font-medium text-gray-900">{formatNumber(lot.quantityTotal)}</div>
            </div>

            <div>
              <div className="text-xs text-gray-500">Progress</div>
              <div className="font-medium text-gray-900">{formatPercentage(lot.inspectedProgress)}</div>
            </div>

            <div>
              <div className="text-xs text-gray-500">Defect Rate</div>
              <div className="font-medium text-gray-900">{formatPercentage(lot.defectRate)}</div>
            </div>

            <div>
              <div className="text-xs text-gray-500">Created</div>
              <div className="font-medium text-gray-900 text-sm">{formatDate(lot.createdAt)}</div>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 shrink-0">
          <Link
            href={`/c/${tenantSlug}/lots/${lot.id}/gallery`}
            className="flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors whitespace-nowrap"
          >
            <ImageIcon className="w-3.5 h-3.5 mr-1.5" />
            Gallery
          </Link>
          {canEdit && onEdit && (
            <button
              onClick={onEdit}
              className="flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Edit
            </button>
          )}
          {canApprove && (
            <>
              <button
                onClick={onReject}
                className="flex items-center px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
              >
                <XIcon className="w-3.5 h-3.5 mr-1.5" />
                Reject
              </button>
              <button
                onClick={onApprove}
                className="flex items-center px-3 py-1.5 text-xs font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 transition-colors"
              >
                <CheckIcon className="w-3.5 h-3.5 mr-1.5" />
                Approve
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
