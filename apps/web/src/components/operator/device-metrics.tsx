'use client'

import { GaugeIcon, MessageSquareIcon, ZapIcon } from 'lucide-react'
import { OperatorDeviceDetail } from '@qa-dashboard/shared'

import { formatRelativeTime } from '@/lib/utils'

interface DeviceMetricsProps {
  device: OperatorDeviceDetail
}

export function DeviceMetrics({ device }: DeviceMetricsProps) {
  const { metrics } = device
  const qa = metrics.qaIndicators

  const lastEventAt = device.recentEvents[0]?.timestamp

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <ZapIcon className="h-4 w-4" aria-hidden />
          Current piece
        </div>
        <p className="mt-3 text-3xl font-semibold text-slate-900">#{metrics.pieceSequence}</p>
        <p className="mt-1 text-xs text-slate-500">
          Updated {lastEventAt ? formatRelativeTime(lastEventAt) : 'recently'}
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <GaugeIcon className="h-4 w-4" aria-hidden />
          QA metrics
        </div>
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-slate-500">Px/mm</dt>
            <dd className="font-medium text-slate-900">
              {qa.pixelsPerMillimeter ? qa.pixelsPerMillimeter.toFixed(1) : '—'}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-slate-500">Sharpness</dt>
            <dd className="font-medium text-slate-900">
              {qa.sharpnessScore ? Math.round(qa.sharpnessScore * 100) : '—'}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-slate-500">Brightness</dt>
            <dd className="font-medium text-slate-900">
              {qa.brightnessScore ? Math.round(qa.brightnessScore * 100) : '—'}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-slate-500">Status</dt>
            <dd
              className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700"
            >
              {qa.status}
            </dd>
          </div>
        </dl>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <MessageSquareIcon className="h-4 w-4" aria-hidden />
          Transcript
        </div>
        <p className="mt-3 text-sm text-slate-600">
          {metrics.lastTranscript ?? 'No transcript available'}
        </p>
      </div>
    </div>
  )
}
