'use client'

import { Event } from '@qa-dashboard/shared'
import { AlertTriangleIcon, ClockIcon, XIcon } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'
import { useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

interface EventBannerProps {
  event: Event
}

export function EventBanner({ event }: EventBannerProps) {
  const [isVisible, setIsVisible] = useState(true)
  const params = useParams()
  const tenantSlug = params.tenantSlug as string

  if (!isVisible) return null

  const renderEventContent = () => {
    switch (event.type) {
      case 'DEFECT_DETECTED': {
        const defectPayload = event.payload || {}
        const defectLotId = typeof defectPayload.lotId === 'string' ? defectPayload.lotId : undefined
        const defectType = typeof defectPayload.defectType === 'string' ? defectPayload.defectType.toUpperCase() : 'Unknown'
        const garmentSerial = typeof defectPayload.garmentSerial === 'string' ? defectPayload.garmentSerial : 'N/A'
        return (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start">
              <AlertTriangleIcon className="w-5 h-5 text-red-500 mr-3 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-red-800 font-medium">
                      Defect Detected
                    </h4>
                    <p className="text-red-700 text-sm mt-1">
                      {defectType} defect found in garment {garmentSerial}
                      {defectLotId && (
                        <Link 
                          href={`/c/${tenantSlug}/lots/${defectLotId}`}
                          className="ml-2 underline hover:no-underline"
                        >
                          View lot
                        </Link>
                      )}
                    </p>
                    <p className="text-red-600 text-xs mt-1">
                      {formatRelativeTime(event.createdAt)}
                    </p>
                  </div>
                  <button
                    onClick={() => setIsVisible(false)}
                    className="text-red-400 hover:text-red-600"
                  >
                    <XIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )
      }

      case 'LOT_AWAITING_APPROVAL': {
        const approvalPayload = event.payload || {}
        const approvalLotId = typeof approvalPayload.lotId === 'string' ? approvalPayload.lotId : undefined
        const approvalStyleRef = typeof approvalPayload.styleRef === 'string' ? approvalPayload.styleRef : approvalLotId
        return (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start">
              <ClockIcon className="w-5 h-5 text-yellow-500 mr-3 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-yellow-800 font-medium">
                      Lot Awaiting Approval
                    </h4>
                    <p className="text-yellow-700 text-sm mt-1">
                      Lot {approvalStyleRef || 'N/A'} is ready for review
                      {approvalLotId && (
                        <Link 
                          href={`/c/${tenantSlug}/lots/${approvalLotId}`}
                          className="ml-2 underline hover:no-underline"
                        >
                          Review now
                        </Link>
                      )}
                    </p>
                    <p className="text-yellow-600 text-xs mt-1">
                      {formatRelativeTime(event.createdAt)}
                    </p>
                  </div>
                  <button
                    onClick={() => setIsVisible(false)}
                    className="text-yellow-400 hover:text-yellow-600"
                  >
                    <XIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )
      }

      default:
        return null
    }
  }

  return renderEventContent()
}
