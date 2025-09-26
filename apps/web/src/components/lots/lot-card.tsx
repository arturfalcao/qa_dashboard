'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Lot } from '@qa-dashboard/shared'
import { formatDate, formatNumber, formatPercentage, getLotStatusColor, cn } from '@/lib/utils'
import { Factory as FactoryIcon, Eye as EyeIcon } from 'lucide-react'

interface LotCardProps {
  lot: Lot
}

export function LotCard({ lot }: LotCardProps) {
  const params = useParams()
  const clientSlug = params.clientSlug as string
  const suppliers = lot.suppliers?.slice().sort((a, b) => a.sequence - b.sequence) ?? []
  const primarySupplier = suppliers.find((supplier) => supplier.isPrimary)?.factory ?? lot.factory
  const additionalSuppliers = suppliers.filter((supplier) => !supplier.isPrimary)

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <FactoryIcon className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{lot.styleRef}</h3>
            <p className="text-sm text-gray-500">
              {primarySupplier?.name || 'Unassigned factory'}
              {additionalSuppliers.length > 0 && (
                <span className="ml-1 text-xs text-gray-400">
                  (+{additionalSuppliers.length} upstream)
                </span>
              )}
            </p>
          </div>
        </div>

        <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getLotStatusColor(lot.status))}>
          {lot.status.replace('_', ' ')}
        </span>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Quantity</span>
          <span className="font-medium">{formatNumber(lot.quantityTotal)}</span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Progress</span>
          <span className="font-medium">{formatPercentage(lot.inspectedProgress)}</span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(lot.inspectedProgress, 100)}%` }}
          ></div>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Defect Rate</span>
          <span className={cn('font-medium', lot.defectRate > 5 ? 'text-red-600' : 'text-green-600')}>
            {formatPercentage(lot.defectRate)}
          </span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Last Update</span>
          <span className="font-medium">{formatDate(lot.updatedAt)}</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <Link
          href={`/c/${clientSlug}/lots/${lot.id}`}
          className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-md transition-colors"
        >
          <EyeIcon className="w-4 h-4 mr-2" />
          View Lot
        </Link>
      </div>
    </div>
  )
}
