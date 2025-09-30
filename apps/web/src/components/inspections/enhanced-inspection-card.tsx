'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Inspection } from '@qa-dashboard/shared'
import Image from 'next/image'
import { formatRelativeTime, cn } from '@/lib/utils'
import { CameraIcon, ChevronDownIcon, ChevronUpIcon, Factory as FactoryIcon, CheckCircle, XCircle } from 'lucide-react'
import { apiClient } from '@/lib/api'

interface EnhancedInspectionCardProps {
  inspection: Inspection
}

export function EnhancedInspectionCard({ inspection }: EnhancedInspectionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isMarking, setIsMarking] = useState(false)
  const queryClient = useQueryClient()
  const lot = inspection.lot
  const defects = inspection.defects || []

  const markDefectMutation = useMutation({
    mutationFn: (payload: { note: string; defectTypeId?: string }) =>
      apiClient.addDefect(inspection.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] })
      setIsMarking(false)
    },
    onError: (error) => {
      console.error('Failed to mark defect:', error)
      alert('Failed to mark defect. Please try again.')
      setIsMarking(false)
    },
  })

  const handleMarkAsDefect = () => {
    if (confirm('Mark this inspection as having a defect?')) {
      setIsMarking(true)
      markDefectMutation.mutate({
        note: 'Defect identified from live feed',
      })
    }
  }

  const handleMarkAsPass = () => {
    setIsMarking(true)
    markDefectMutation.mutate({
      note: 'Inspection passed - no defects',
    })
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <div className="inline-flex items-center px-3 py-1 bg-primary-50 text-primary-700 text-sm font-medium rounded-full border border-primary-200">
                Inspection {inspection.id.substring(0, 8)}
              </div>
              <span className="text-sm text-gray-500">
                {formatRelativeTime(inspection.createdAt)}
              </span>
            </div>
            <div className="text-gray-900 font-semibold text-lg">{lot?.styleRef}</div>
            <div className="flex items-center text-sm text-gray-500 mt-1">
              <FactoryIcon className="w-4 h-4 mr-1" />
              {lot?.factory?.name || 'Unnamed factory'}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleMarkAsPass}
              disabled={isMarking || defects.length > 0}
              className={cn(
                "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                defects.length > 0
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-green-50 text-green-700 hover:bg-green-100 border border-green-200"
              )}
            >
              <CheckCircle className="w-4 h-4 mr-1.5" />
              Pass
            </button>
            <button
              onClick={handleMarkAsDefect}
              disabled={isMarking}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition-colors"
            >
              <XCircle className="w-4 h-4 mr-1.5" />
              Defect
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm text-primary-600 hover:text-primary-700 flex items-center ml-2"
            >
              {isExpanded ? (
                <>
                  Collapse
                  <ChevronUpIcon className="w-4 h-4 ml-1" />
                </>
              ) : (
                <>
                  Details
                  <ChevronDownIcon className="w-4 h-4 ml-1" />
                </>
              )}
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <Stat label="Inspector" value={inspection.inspectorId || 'Unassigned'} />
          <Stat label="Defects" value={defects.length.toString()} />
          <Stat label="Progress" value={`${lot?.inspectedProgress?.toFixed(1) ?? '0'}%`} />
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-gray-200 bg-gray-50 p-6 space-y-4">
          {defects.length === 0 && (
            <p className="text-sm text-gray-600">No issues recorded during this inspection.</p>
          )}

          {defects.map((defect) => (
            <div key={defect.id} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm text-gray-500">Defect #{defect.id.substring(0, 6)}</div>
                  <div className="text-base font-semibold text-gray-900 mt-1">
                    {defect.defectTypeId || 'Observation'}
                  </div>
                  {defect.note && <p className="text-sm text-gray-700 mt-2">{defect.note}</p>}
                </div>
              </div>

              {(defect.photos || []).length > 0 && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                  {defect.photos?.map((photo) => (
                    <figure key={photo.id} className="border border-gray-200 rounded-md overflow-hidden bg-gray-100">
                      <Image
                        src={photo.url}
                        alt="Inspection evidence"
                        className="w-full h-40 object-cover"
                        width={400}
                        height={160}
                        sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                      />
                      {photo.annotation?.comment && (
                        <figcaption className="px-3 py-2 text-xs text-gray-600 flex items-center">
                          <CameraIcon className="w-4 h-4 mr-2" />
                          {photo.annotation.comment}
                        </figcaption>
                      )}
                    </figure>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-gray-500">{label}</div>
      <div className="text-gray-900 font-medium">{value}</div>
    </div>
  )
}
