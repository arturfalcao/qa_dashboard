'use client'

import { useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { ArrowLeftIcon, FlagIcon } from 'lucide-react'

import { EventFeed } from '@/components/operator/event-feed'
import { apiClient } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'

export default function OperatorLotDetailPage() {
  const params = useParams<{ id: string }>()
  const lotId = params?.id
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const [selectedEventId, setSelectedEventId] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: lots = [] } = useQuery({
    queryKey: ['operator', 'lots'],
    queryFn: () => apiClient.getOperatorActiveLots(),
  })

  const { data: events = [], isLoading } = useQuery({
    queryKey: ['operator', 'lot-feed', lotId],
    queryFn: () => apiClient.getOperatorLotFeed(lotId!),
    enabled: !!lotId,
  })

  const summary = useMemo(() => lots.find((item) => item.lotId === lotId), [lots, lotId])

  const mutation = useMutation({
    mutationFn: (payload: { eventId: string; note: string }) =>
      apiClient.createOperatorFlag(lotId!, { eventId: payload.eventId, note: payload.note }),
    onSuccess: (updatedEvent) => {
      queryClient.setQueryData(['operator', 'lot-feed', lotId], (prev?: typeof events) => {
        if (!prev) return [updatedEvent]
        return prev.map((event) => (event.id === updatedEvent.id ? updatedEvent : event))
      })
      setFeedback('Flag saved successfully')
      setError(null)
      setNote('')
      setSelectedEventId('')
    },
    onError: (err: Error) => {
      setError(err.message)
      setFeedback(null)
    },
  })

  const photoEvents = events.filter((event) => !!event.thumbnailUrl)

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <Link href="/operator/lots" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900">
          <ArrowLeftIcon className="h-4 w-4" aria-hidden />
          Back to lots
        </Link>

        <div className="mt-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">{summary?.styleRef ?? '—'}</p>
            <h1 className="text-2xl font-semibold text-slate-900">Lot {summary?.lotCode ?? lotId}</h1>
            <p className="text-sm text-slate-600">{summary?.customer ?? 'Unknown customer'}</p>
          </div>
          {summary?.lastEventAt && (
            <p className="text-xs text-slate-500">Updated {formatRelativeTime(summary.lastEventAt)}</p>
          )}
        </div>

        {feedback && (
          <div className="mt-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{feedback}</div>
        )}
        {error && <div className="mt-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!selectedEventId || !note) {
              setError('Select an event and provide a note before saving a flag.')
              setFeedback(null)
              return
            }
            mutation.mutate({ eventId: selectedEventId, note })
          }}
          className="mt-6 grid gap-3 md:grid-cols-6"
        >
          <label className="md:col-span-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Event
            <select
              required
              value={selectedEventId}
              onChange={(event) => setSelectedEventId(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
            >
              <option value="">Select an event</option>
              {events.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.type.toLowerCase()} &middot; {formatRelativeTime(event.timestamp)}
                </option>
              ))}
            </select>
          </label>

          <label className="md:col-span-3 text-xs font-medium uppercase tracking-wide text-slate-500">
            Note
            <input
              required
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Describe the observation"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
            />
          </label>

          <button
            type="submit"
            disabled={mutation.isLoading}
            className="md:col-span-1 mt-6 inline-flex h-10 items-center justify-center gap-2 rounded-full bg-primary-600 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-primary-700 disabled:opacity-60"
          >
            <FlagIcon className="h-4 w-4" aria-hidden />
            {mutation.isLoading ? 'Saving…' : 'Flag event'}
          </button>
        </form>
      </section>

      {isLoading ? (
        <div className="flex min-h-[160px] items-center justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-primary-500" />
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <EventFeed events={events} className="h-full" />

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-slate-700">Photo stream</h3>
              {photoEvents.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">No photos received for this lot yet.</p>
              ) : (
                <div className="mt-3 grid grid-cols-2 gap-3">
                  {photoEvents.map((event) => (
                    <figure key={event.id} className="overflow-hidden rounded-xl border border-slate-200">
                      <img src={event.thumbnailUrl!} alt={event.transcript ?? 'Inspection photo'} className="h-32 w-full object-cover" />
                      <figcaption className="px-3 py-2 text-xs text-slate-600">
                        {formatRelativeTime(event.timestamp)}
                      </figcaption>
                    </figure>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
