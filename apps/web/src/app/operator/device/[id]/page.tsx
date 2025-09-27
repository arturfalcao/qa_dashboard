'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftIcon, Loader2Icon } from 'lucide-react'
import Link from 'next/link'

import { DeviceStatusPill } from '@/components/operator/device-status-pill'
import { DeviceMetrics } from '@/components/operator/device-metrics'
import { QueueDepthCard } from '@/components/operator/queue-depth-card'
import { EventFeed } from '@/components/operator/event-feed'
import { apiClient } from '@/lib/api'

export default function OperatorDeviceDetailPage() {
  const params = useParams<{ id: string }>()
  const deviceId = params?.id
  const queryClient = useQueryClient()
  const [feedback, setFeedback] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: device, isLoading } = useQuery({
    queryKey: ['operator', 'device', deviceId],
    queryFn: () => apiClient.getOperatorDevice(deviceId!),
    enabled: !!deviceId,
  })

  const assignMutation = useMutation({
    mutationFn: apiClient.assignOperatorDevice.bind(apiClient, deviceId!),
    onSuccess: (updated) => {
      queryClient.setQueryData(['operator', 'device', deviceId], updated)
      queryClient.invalidateQueries({ queryKey: ['operator', 'devices'] })
      queryClient.invalidateQueries({ queryKey: ['operator', 'lots'] })
      setFeedback('Device assignment updated successfully')
      setError(null)
    },
    onError: (err: Error) => {
      setError(err.message)
      setFeedback(null)
    },
  })

  const reprintMutation = useMutation({
    mutationFn: apiClient.issueReprintCommand.bind(apiClient, deviceId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operator', 'device', deviceId] })
      queryClient.invalidateQueries({ queryKey: ['operator', 'lots'] })
      setFeedback('Reprint command queued')
      setError(null)
    },
    onError: (err: Error) => {
      setError(err.message)
      setFeedback(null)
    },
  })

  const [assignmentForm, setAssignmentForm] = useState({
    lotId: '',
    styleRef: '',
    customer: '',
  })

  const [reprintForm, setReprintForm] = useState({
    lotId: '',
    pieceSeq: 0,
    reason: '',
  })

  useEffect(() => {
    if (device?.currentAssignment) {
      setAssignmentForm({
        lotId: device.currentAssignment.lotId,
        styleRef: device.currentAssignment.styleRef,
        customer: device.currentAssignment.customer,
      })
      setReprintForm((prev) => ({ ...prev, lotId: device.currentAssignment!.lotId }))
    }
  }, [device?.currentAssignment])

  const handleAssign = (event: FormEvent) => {
    event.preventDefault()
    assignMutation.mutate({ ...assignmentForm })
  }

  const handleReprint = (event: FormEvent) => {
    event.preventDefault()
    reprintMutation.mutate({ ...reprintForm, pieceSeq: Number(reprintForm.pieceSeq) })
  }

  const currentAssignment = useMemo(() => device?.currentAssignment ?? null, [device])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <Link href="/operator" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900">
          <ArrowLeftIcon className="h-4 w-4" aria-hidden />
          Back to devices
        </Link>

        {isLoading || !device ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loader2Icon className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">{device.site}</p>
                <h2 className="text-2xl font-semibold text-slate-900">{device.name}</h2>
                <p className="text-sm text-slate-600">
                  Last seen {device.lastSeenAt ? new Date(device.lastSeenAt).toLocaleTimeString() : '—'}
                </p>
              </div>
              <DeviceStatusPill status={device.status} />
            </div>

            {feedback && (
              <div className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{feedback}</div>
            )}
            {error && <div className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

            <DeviceMetrics device={device} />

            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-4 lg:col-span-2">
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <h3 className="text-sm font-semibold text-slate-700">Assignment</h3>
                  {currentAssignment ? (
                    <p className="mt-2 text-sm text-slate-600">
                      Lot {currentAssignment.lotId} &mdash; {currentAssignment.styleRef} for {currentAssignment.customer}
                    </p>
                  ) : (
                    <p className="mt-2 text-sm text-slate-500">No lot assigned</p>
                  )}

                  <form onSubmit={handleAssign} className="mt-4 grid gap-3 md:grid-cols-3">
                    <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Lot ID
                      <input
                        required
                        value={assignmentForm.lotId}
                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, lotId: event.target.value }))}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
                      />
                    </label>
                    <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Style ref
                      <input
                        required
                        value={assignmentForm.styleRef}
                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, styleRef: event.target.value }))}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
                      />
                    </label>
                    <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Customer
                      <input
                        required
                        value={assignmentForm.customer}
                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, customer: event.target.value }))}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
                      />
                    </label>
                    <div className="md:col-span-3">
                      <button
                        type="submit"
                        disabled={assignMutation.isLoading}
                        className="mt-2 inline-flex w-full items-center justify-center rounded-full bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-primary-700 disabled:opacity-60"
                      >
                        {assignMutation.isLoading ? 'Updating…' : 'Assign lot'}
                      </button>
                    </div>
                  </form>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <h3 className="text-sm font-semibold text-slate-700">Reprint label</h3>
                  <form onSubmit={handleReprint} className="mt-4 grid gap-3 md:grid-cols-3">
                    <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Lot ID
                      <input
                        required
                        value={reprintForm.lotId}
                        onChange={(event) => setReprintForm((prev) => ({ ...prev, lotId: event.target.value }))}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
                      />
                    </label>
                    <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Piece #
                      <input
                        required
                        type="number"
                        min={0}
                        value={reprintForm.pieceSeq}
                        onChange={(event) => setReprintForm((prev) => ({ ...prev, pieceSeq: Number(event.target.value) }))}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
                      />
                    </label>
                    <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Reason
                      <input
                        value={reprintForm.reason}
                        onChange={(event) => setReprintForm((prev) => ({ ...prev, reason: event.target.value }))}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
                      />
                    </label>
                    <div className="md:col-span-3">
                      <button
                        type="submit"
                        disabled={reprintMutation.isLoading}
                        className="mt-2 inline-flex w-full items-center justify-center rounded-full border border-primary-200 bg-white px-4 py-2 text-sm font-medium text-primary-700 shadow-sm transition hover:border-primary-300 hover:text-primary-900 disabled:opacity-60"
                      >
                        {reprintMutation.isLoading ? 'Sending…' : 'Queue reprint command'}
                      </button>
                    </div>
                  </form>
                </div>

                <EventFeed events={device.recentEvents} />
              </div>

              <QueueDepthCard data={device.queueDepthHistory} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
