'use client'

import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import { EnhancedInspectionCard } from '@/components/inspections/enhanced-inspection-card'
import { EventBanner } from '@/components/events/event-banner'
import { formatRelativeTime } from '@/lib/utils'
import { Inspection, Event } from '@qa-dashboard/shared'
import Link from 'next/link'

export default function LiveFeedPage() {
  const [lastUpdateTime, setLastUpdateTime] = useState<string>()
  const [selectedDefect, setSelectedDefect] = useState<any>(null)

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

  // Poll for live feed data (edge inspections) every 10 seconds
  const { data: liveFeed } = useQuery({
    queryKey: ['live-feed'],
    queryFn: () => apiClient.getLiveFeed(),
    refetchInterval: 10000,
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

      {/* Active Edge Inspection Sessions */}
      {liveFeed?.activeSessions && liveFeed.activeSessions.length > 0 && (
        <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-2xl border border-primary-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              <h2 className="text-lg font-semibold text-slate-900">Active Inspections</h2>
            </div>
            <span className="px-3 py-1 bg-primary-600 text-white rounded-full text-xs font-semibold">
              {liveFeed.activeSessions.length} active
            </span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {liveFeed.activeSessions.map((session: any) => (
              <div key={session.id} className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{session.lot?.styleRef || 'Unknown Lot'}</h3>
                    <p className="text-sm text-slate-500">Started {new Date(session.startedAt).toLocaleTimeString()}</p>
                  </div>
                  <Link
                    href={`/operator/inspection/${session.id}`}
                    className="text-xs text-primary-600 hover:text-primary-800 font-medium"
                  >
                    View →
                  </Link>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-xl font-bold text-slate-900">{session.piecesInspected}</div>
                    <div className="text-xs text-slate-500">Inspected</div>
                  </div>
                  <div>
                    <div className="text-xl font-bold text-red-600">{session.piecesDefect}</div>
                    <div className="text-xs text-slate-500">Defects</div>
                  </div>
                  <div>
                    <div className="text-xl font-bold text-amber-600">{session.piecesPotentialDefect}</div>
                    <div className="text-xs text-slate-500">Potential</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending Defects for Review */}
      {liveFeed?.pendingDefects && liveFeed.pendingDefects.length > 0 && (
        <div className="bg-amber-50 rounded-2xl border border-amber-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">⚠️</span>
              <h2 className="text-lg font-semibold text-slate-900">Pending Defect Review</h2>
            </div>
            <span className="px-3 py-1 bg-amber-600 text-white rounded-full text-xs font-semibold">
              {liveFeed.pendingDefects.length} pending
            </span>
          </div>
          <div className="space-y-3">
            {liveFeed.pendingDefects.slice(0, 5).map((defect: any) => (
              <button
                key={defect.id}
                onClick={() => setSelectedDefect(defect)}
                className="w-full bg-white rounded-xl p-4 shadow-sm border border-amber-200 hover:border-amber-400 transition text-left"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-slate-900">Piece #{defect.pieceNumber}</div>
                    <p className="text-sm text-slate-600 mt-1">{defect.audioTranscript || 'No description'}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Flagged {new Date(defect.flaggedAt).toLocaleString()}
                    </p>
                  </div>
                  <span className="text-primary-600 font-medium text-sm">Review →</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

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

      {/* Defect Review Modal */}
      {selectedDefect && (
        <DefectReviewModal
          defect={selectedDefect}
          onClose={() => setSelectedDefect(null)}
          onReviewed={() => {
            setSelectedDefect(null)
            // Trigger refetch of live feed
          }}
        />
      )}
    </div>
  )
}

// Defect Review Modal Component
function DefectReviewModal({
  defect,
  onClose,
  onReviewed,
}: {
  defect: any
  onClose: () => void
  onReviewed: () => void
}) {
  const [status, setStatus] = useState<'confirmed' | 'rejected'>('confirmed')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    try {
      setSubmitting(true)
      await apiClient.reviewDefect(defect.id, { status, notes })
      alert('Defect reviewed successfully!')
      onReviewed()
    } catch (err: any) {
      alert(err.message || 'Failed to review defect')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 rounded-t-3xl">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold text-slate-900">Review Defect</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 rounded-full transition"
            >
              <span className="text-2xl">×</span>
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Defect Info */}
          <div className="bg-slate-50 rounded-xl p-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Piece Number:</span>
                <span className="ml-2 font-semibold text-slate-900">#{defect.pieceNumber}</span>
              </div>
              <div>
                <span className="text-slate-500">Flagged:</span>
                <span className="ml-2 font-semibold text-slate-900">
                  {new Date(defect.flaggedAt).toLocaleString()}
                </span>
              </div>
            </div>
            {defect.audioTranscript && (
              <div className="mt-3">
                <span className="text-slate-500 text-sm">Operator Notes:</span>
                <p className="mt-1 text-slate-900">{defect.audioTranscript}</p>
              </div>
            )}
          </div>

          {/* Photos */}
          {defect.photos && defect.photos.length > 0 && (
            <div>
              <h3 className="font-semibold text-slate-900 mb-3">Photos</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {defect.photos.map((photo: any) => (
                  <div key={photo.id} className="aspect-square bg-slate-100 rounded-xl overflow-hidden">
                    <img
                      src={`/api/photos/${photo.filePath}`}
                      alt="Defect"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23e2e8f0" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="48"%3E📷%3C/text%3E%3C/svg%3E'
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Review Decision */}
          <div>
            <h3 className="font-semibold text-slate-900 mb-3">Review Decision</h3>
            <div className="flex gap-3">
              <button
                onClick={() => setStatus('confirmed')}
                className={`flex-1 py-3 px-4 rounded-xl font-semibold transition ${
                  status === 'confirmed'
                    ? 'bg-red-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                ✓ Confirm Defect
              </button>
              <button
                onClick={() => setStatus('rejected')}
                className={`flex-1 py-3 px-4 rounded-xl font-semibold transition ${
                  status === 'rejected'
                    ? 'bg-green-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                × Reject (False Positive)
              </button>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block font-semibold text-slate-900 mb-2">Review Notes (Optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200"
              rows={3}
              placeholder="Add any additional notes about this review..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-3 px-4 border border-slate-300 rounded-xl font-semibold hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex-1 py-3 px-4 bg-primary-600 text-white rounded-xl font-semibold hover:bg-primary-700 disabled:opacity-50 transition"
            >
              {submitting ? 'Submitting...' : 'Submit Review'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
