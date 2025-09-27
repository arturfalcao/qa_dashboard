'use client'

import { CameraIcon, FlagIcon, PrinterIcon, ShieldCheckIcon } from 'lucide-react'
import { OperatorLotFeedItem, EdgeEventType } from '@qa-dashboard/shared'

import { cn, formatRelativeTime } from '@/lib/utils'

interface EventFeedProps {
  events: OperatorLotFeedItem[]
  className?: string
}

const ICONS: Record<EdgeEventType, typeof CameraIcon> = {
  [EdgeEventType.PHOTO]: CameraIcon,
  [EdgeEventType.DEFECT]: FlagIcon,
  [EdgeEventType.PIECE_END]: ShieldCheckIcon,
  [EdgeEventType.PRINT_LABEL]: PrinterIcon,
  [EdgeEventType.HEARTBEAT]: ShieldCheckIcon,
  [EdgeEventType.FLAG]: FlagIcon,
}

export function EventFeed({ events, className }: EventFeedProps) {
  return (
    <div
      className={cn(
        'space-y-3 overflow-hidden rounded-2xl border border-slate-200 bg-white p-4',
        className,
      )}
    >
      <h3 className="text-sm font-semibold text-slate-700">Recent activity</h3>

      <ul className="divide-y divide-slate-100">
        {events.map((event) => {
          const Icon = ICONS[event.type]

          return (
            <li key={event.id} className="flex items-start gap-3 py-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-50 text-slate-600">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-900 capitalize">{event.type.toLowerCase()}</p>
                  <span className="text-xs text-slate-500">{formatRelativeTime(event.timestamp)}</span>
                </div>
                {event.transcript && <p className="text-sm text-slate-600">{event.transcript}</p>}
                {event.defectText && (
                  <p className="text-sm font-medium text-amber-700">{event.defectText}</p>
                )}
                {event.flag && (
                  <p className="rounded-lg bg-amber-50 px-2 py-1 text-xs text-amber-800">
                    {event.flag.note}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
