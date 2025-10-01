'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useMemo } from 'react'
import { apiClient } from '@/lib/api'
import { EnhancedInspectionCard } from '@/components/inspections/enhanced-inspection-card'
import { EventBanner } from '@/components/events/event-banner'
import { cn, formatRelativeTime } from '@/lib/utils'
import { Inspection, Event } from '@qa-dashboard/shared'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Modal, ModalFooter } from '@/components/ui/modal'
import { useToast } from '@/components/ui/toast'
import { PageHeader } from '@/components/ui/page-header'
import { TextArea } from '@/components/ui/input'
import { useParams, useRouter } from 'next/navigation'
import { ActivityIcon, AlertTriangleIcon, ZoomInIcon, XIcon } from 'lucide-react'
import { ImageZoomViewer } from '@/components/ui/image-zoom-viewer'

export default function LiveFeedPage() {
  const [lastUpdateTime, setLastUpdateTime] = useState<string>()
  const [selectedDefect, setSelectedDefect] = useState<any>(null)
  const queryClient = useQueryClient()
  const { publish } = useToast()
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params?.tenantSlug as string
  const workspaceBasePath = `/c/${tenantSlug}`

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
  const { data: liveFeed, refetch: refetchLiveFeed } = useQuery({
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
  const recentEvents = useMemo(
    () =>
      events.filter(
        (event) => event.type === 'DEFECT_DETECTED' || event.type === 'LOT_AWAITING_APPROVAL',
      ),
    [events],
  )

  const activeSessions = liveFeed?.activeSessions ?? []
  const pendingDefects = liveFeed?.pendingDefects ?? []

  const summaryCards = useMemo(
    () => [
      {
        label: 'Active sessions',
        value: activeSessions.length.toString(),
        helper: activeSessions.length ? 'Operators reporting live' : 'No sessions in progress',
      },
      {
        label: 'Pending defects',
        value: pendingDefects.length.toString(),
        helper: pendingDefects.length ? 'Need review' : 'All clear',
      },
      {
        label: 'Recent inspections',
        value: inspections.length.toString(),
        helper: 'Last 50 records streamed',
      },
      {
        label: 'Live alerts',
        value: recentEvents.length.toString(),
        helper: recentEvents.length ? 'Action required' : 'No new alerts',
      },
    ],
    [activeSessions.length, pendingDefects.length, inspections.length, recentEvents.length],
  )

  const statusMeta = (
    <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-500">
      <span
        className={cn(
          'flex items-center gap-2 font-medium',
          activeSessions.length ? 'text-emerald-600' : 'text-neutral-400',
        )}
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
        </span>
        {activeSessions.length ? 'Live' : 'Idle'}
      </span>
      {lastUpdateTime && <span>Updated {formatRelativeTime(lastUpdateTime)}</span>}
    </div>
  )

  const headerActions = (
    <div className="flex items-center gap-2">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => router.push(`${workspaceBasePath}/analytics`)}
      >
        Analytics
      </Button>
      <Button size="sm" onClick={() => router.push(`${workspaceBasePath}/exports`)}>
        Exports
      </Button>
    </div>
  )

  if (inspectionsLoading && !inspections.length) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Live Feed"
          description="Real-time garment inspection updates."
          meta={statusMeta}
          actions={headerActions}
        />
        <Card>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Live Feed"
        description="Monitor live inspections, alerts, and defect reviews across the production floor."
        meta={statusMeta}
        actions={headerActions}
      />

      {recentEvents.length > 0 && (
        <div className="space-y-3">
          {recentEvents.map((event) => (
            <EventBanner key={event.id} event={event} />
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
          <Card key={card.label}>
            <CardHeader className="space-y-1">
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
                {card.value}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">{card.helper}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Active inspections</CardTitle>
            <CardDescription>Operators streaming edge data in real time.</CardDescription>
          </div>
          {activeSessions.length > 0 && (
            <span className="rounded-full bg-primary-100 px-3 py-1 text-xs font-semibold text-primary-700">
              {activeSessions.length} active
            </span>
          )}
        </CardHeader>
        <CardContent>
          {activeSessions.length === 0 ? (
            <EmptyState
              icon={<ActivityIcon className="h-5 w-5" />}
              title="No sessions online"
              description="When operators start an inspection, it will appear here."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {activeSessions.map((session: any) => (
                <Card key={session.id} className="border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/60">
                  <CardHeader className="flex flex-col gap-1">
                    <CardTitle className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                      {session.lot?.styleRef || 'Unknown lot'}
                    </CardTitle>
                    <CardDescription>
                      Started {new Date(session.startedAt).toLocaleTimeString()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-3 gap-2 text-center text-sm">
                      <div>
                        <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                          {session.piecesInspected}
                        </p>
                        <p className="text-xs text-neutral-500">Inspected</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-danger-600">
                          {session.piecesDefect}
                        </p>
                        <p className="text-xs text-neutral-500">Defects</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-amber-600">
                          {session.piecesPotentialDefect}
                        </p>
                        <p className="text-xs text-neutral-500">Potential</p>
                      </div>
                    </div>
                    <Button
                      variant="link"
                      size="sm"
                      className="px-0"
                      onClick={() => router.push(`/operator/inspection/${session.id}`)}
                    >
                      Open operator view
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Potential Defect Review</CardTitle>
            <CardDescription>
              Review flagged pieces with visual evidence. Confirm real defects or mark as false positives to reduce noise.
            </CardDescription>
          </div>
          {pendingDefects.length > 0 && (
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
              {pendingDefects.length} need review
            </span>
          )}
        </CardHeader>
        <CardContent>
          {pendingDefects.length === 0 ? (
            <EmptyState
              icon={<AlertTriangleIcon className="h-5 w-5" />}
              title="No defects awaiting review"
              description="We’ll notify you here when operators flag issues."
            />
          ) : (
            <div className="space-y-3">
              {pendingDefects.slice(0, 5).map((defect: any) => (
                <button
                  key={defect.id}
                  onClick={() => setSelectedDefect(defect)}
                  className="w-full rounded-xl border border-neutral-200 bg-white p-4 text-left transition hover:border-primary-200 hover:shadow-sm dark:border-neutral-700 dark:bg-neutral-900"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                        Piece #{defect.pieceNumber}
                      </p>
                      <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
                        {defect.audioTranscript || 'No operator notes provided.'}
                      </p>
                      <p className="mt-1 text-xs text-neutral-500">
                        Flagged {new Date(defect.flaggedAt).toLocaleString()}
                      </p>
                    </div>
                    <span className="text-sm font-medium text-primary-600">Review</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent inspections</CardTitle>
          <CardDescription>Latest edge events streamed from the production floor.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {inspections.length === 0 ? (
            <EmptyState
              icon={<ActivityIcon className="h-5 w-5" />}
              title="No inspections yet"
              description="Seed the environment to start streaming live inspections."
            />
          ) : (
            inspections.map((inspection) => (
              <EnhancedInspectionCard key={inspection.id} inspection={inspection} />
            ))
          )}

          {inspections.length >= 50 && (
            <div className="flex justify-center pt-2">
              <Button variant="link" size="sm">
                Load more inspections
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedDefect && (
        <DefectReviewModal
          defect={selectedDefect}
          onClose={() => setSelectedDefect(null)}
          onSuccess={async (status) => {
            // Immediately refetch live feed to update the defects list
            await refetchLiveFeed()
            queryClient.invalidateQueries({ queryKey: ['events'] })
            queryClient.invalidateQueries({ queryKey: ['inspections'] })
            publish({
              variant: status === 'confirmed' ? 'danger' : 'success',
              title: status === 'confirmed' ? 'Defect confirmed' : 'Marked as false positive',
              description: 'The review outcome has been recorded.',
            })
            setSelectedDefect(null)
          }}
          onError={(message) =>
            publish({
              variant: 'danger',
              title: 'Review failed',
              description: message,
            })
          }
        />
      )}
    </div>
  )
}

// Defect Review Modal Component
function DefectReviewModal({
  defect,
  onClose,
  onSuccess,
  onError,
}: {
  defect: any
  onClose: () => void
  onSuccess: (status: 'confirmed' | 'rejected') => void
  onError: (message: string) => void
}) {
  const [status, setStatus] = useState<'confirmed' | 'rejected'>('confirmed')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [selectedPhoto, setSelectedPhoto] = useState<any>(null)

  const photos = defect.photos ?? []

  const handleSubmit = async () => {
    try {
      setSubmitting(true)
      await apiClient.reviewDefect(defect.id, { status, notes })
      onSuccess(status)
    } catch (err: any) {
      onError(err?.message || 'Failed to save review. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Review defect"
      description={`Piece #${defect.pieceNumber}`}
    >
      <div className="space-y-6">
        <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900/40">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wide text-neutral-500">Piece number</dt>
              <dd className="text-sm font-medium text-neutral-900 dark:text-neutral-100">#{defect.pieceNumber}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-neutral-500">Flagged</dt>
              <dd className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {new Date(defect.flaggedAt).toLocaleString()}
              </dd>
            </div>
          </dl>
          {defect.audioTranscript && (
            <p className="mt-3 text-sm text-neutral-700 dark:text-neutral-300">
              <span className="font-medium text-neutral-900 dark:text-neutral-100">Operator notes:</span>{' '}
              {defect.audioTranscript}
            </p>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Defect Photos</h3>
          <p className="mt-1 text-xs text-neutral-500">Click on any photo to zoom and inspect the defect</p>
          {photos.length === 0 ? (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-center">
              <p className="text-sm text-amber-800">No photos available for this defect</p>
              <p className="mt-1 text-xs text-amber-600">Operator may not have captured visual evidence</p>
            </div>
          ) : (
            <div className="mt-3 grid gap-3 sm:grid-cols-2 md:grid-cols-3">
              {photos.map((photo: any) => (
                <button
                  key={photo.id}
                  type="button"
                  onClick={() => setSelectedPhoto(photo)}
                  className="group relative overflow-hidden rounded-lg border border-neutral-200 bg-neutral-100 transition hover:border-primary-300 hover:shadow-md dark:border-neutral-700 dark:bg-neutral-800"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={photo.url || '/placeholder-image.jpg'}
                    alt="Defect photo"
                    className="h-40 w-full object-cover transition group-hover:scale-105"
                    onError={(e) => {
                      e.currentTarget.src =
                        'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23e2e8f0" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="48"%3E📷%3C/text%3E%3C/svg%3E'
                    }}
                  />
                  <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition group-hover:bg-black/20">
                    <ZoomInIcon className="h-6 w-6 text-white opacity-0 transition group-hover:opacity-100" />
                  </div>
                  {photo.annotation?.comment && (
                    <div className="px-3 py-2 text-xs text-neutral-600 dark:text-neutral-300">
                      {photo.annotation.comment}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Button
            type="button"
            variant={status === 'confirmed' ? 'danger' : 'secondary'}
            className={cn(
              'justify-between text-sm',
              status === 'confirmed' && 'ring-2 ring-danger-200',
            )}
            onClick={() => setStatus('confirmed')}
          >
            <span>Confirm defect</span>
            <span className="text-xs font-normal text-neutral-200">Shift owner notified</span>
          </Button>
          <Button
            type="button"
            variant={status === 'rejected' ? 'primary' : 'secondary'}
            className={cn(
              'justify-between text-sm',
              status === 'rejected' && 'ring-2 ring-primary-200',
            )}
            onClick={() => setStatus('rejected')}
          >
            <span>Mark as false positive</span>
            <span className="text-xs font-normal text-neutral-400">Reset piece counter</span>
          </Button>
        </div>

        <div className="space-y-2">
          <label htmlFor="defect-notes" className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Reviewer notes (optional)
          </label>
          <TextArea
            id="defect-notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={4}
            placeholder="Add context for the factory or attach follow-up actions."
          />
        </div>
      </div>
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} loading={submitting}>
          Submit review
        </Button>
      </ModalFooter>

      {/* Enhanced Photo Zoom Viewer */}
      {selectedPhoto && (
        <ImageZoomViewer
          src={selectedPhoto.url || '/placeholder-image.jpg'}
          alt="Defect photo - full resolution"
          annotation={selectedPhoto.annotation?.comment}
          onClose={() => setSelectedPhoto(null)}
          title="Defect Photo Inspection"
          description={`${defect.pieceNumber ? `Piece #${defect.pieceNumber}` : ''} - ${
            defect.defect?.type || 'Potential defect'
          }`}
        />
      )}
    </Modal>
  )
}
