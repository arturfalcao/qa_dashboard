'use client'

import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import { EnhancedInspectionCard } from '@/components/inspections/enhanced-inspection-card'
import { EventBanner } from '@/components/events/event-banner'
import { formatRelativeTime } from '@/lib/utils'
import { Inspection, Event } from '@qa-dashboard/shared'

export default function LiveFeedPage() {
  const [lastUpdateTime, setLastUpdateTime] = useState<string>()

  // Poll for inspections every 5 seconds
  const { data: inspections = [], isLoading: inspectionsLoading } = useQuery({
    queryKey: ['inspections', lastUpdateTime],
    queryFn: () => apiClient.getInspections(lastUpdateTime, 50),
    refetchInterval: 5000,
  })

  // Poll for events every 5 seconds
  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ['events', lastUpdateTime],
    queryFn: () => apiClient.getEvents(lastUpdateTime, 10),
    refetchInterval: 5000,
  })

  // Update last update time when new data comes in
  useEffect(() => {
    if (inspections.length > 0) {
      const latest = inspections[0].createdAt
      if (!lastUpdateTime || new Date(latest) > new Date(lastUpdateTime)) {
        setLastUpdateTime(latest)
      }
    }
  }, [inspections, lastUpdateTime])

  // Filter events to show only defect detection and batch approval events
  const recentEvents = events.filter(
    (event) => event.type === 'DEFECT_DETECTED' || event.type === 'LOT_AWAITING_APPROVAL',
  )

  if (inspectionsLoading && !inspections.length) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Live Feed</h1>
        </div>
        
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Feed</h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time garment inspection updates
            {lastUpdateTime && (
              <span className="ml-2">
                • Last updated {formatRelativeTime(lastUpdateTime)}
              </span>
            )}
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-500">Live</span>
          </div>
        </div>
      </div>

      {/* Event banners */}
      {recentEvents.map((event) => (
        <EventBanner key={event.id} event={event} />
      ))}

      {/* Inspections feed */}
      <div className="space-y-4">
        {inspections.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012-2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No inspections yet</h3>
            <p className="text-gray-500">
            Seed data to see live inspection updates
            </p>
          </div>
        ) : (
          inspections.map((inspection) => (
            <EnhancedInspectionCard key={inspection.id} inspection={inspection} />
          ))
        )}
      </div>

      {/* Load more placeholder for infinite scroll */}
      {inspections.length >= 50 && (
        <div className="text-center py-4">
          <button className="text-primary-600 hover:text-primary-700 font-medium">
            Load more inspections
          </button>
        </div>
      )}
    </div>
  )
}
