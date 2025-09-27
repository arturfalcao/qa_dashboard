'use client'

import Link from 'next/link'
import { ArrowRightIcon, ClockIcon, LayersIcon } from 'lucide-react'
import {
  OperatorDevice,
  OperatorAssignment,
} from '@qa-dashboard/shared'

import { DeviceStatusPill } from './device-status-pill'
import { cn, formatRelativeTime } from '@/lib/utils'

interface DeviceCardProps {
  device: OperatorDevice
  className?: string
}

function AssignmentSummary({ assignment }: { assignment: OperatorAssignment }) {
  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-gray-900">Lot {assignment.lotId}</p>
      <p className="text-xs text-gray-600">
        {assignment.styleRef} &middot; {assignment.customer}
      </p>
      <p className="flex items-center gap-1 text-xs text-gray-500">
        <ClockIcon className="h-3.5 w-3.5" aria-hidden />
        Assigned {formatRelativeTime(assignment.assignedAt)}
      </p>
    </div>
  )
}

export function DeviceCard({ device, className }: DeviceCardProps) {
  const assignment = device.currentAssignment

  return (
    <Link
      href={`/operator/device/${device.id}`}
      className={cn(
        'group flex flex-col rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-primary-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-gray-500">{device.site}</p>
          <h3 className="mt-1 text-lg font-semibold text-gray-900">{device.name}</h3>
          <p className="mt-1 text-xs text-gray-500">
            Last seen {device.lastSeenAt ? formatRelativeTime(device.lastSeenAt) : 'never'}
          </p>
        </div>
        <DeviceStatusPill status={device.status} />
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
        <div className="rounded-xl bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-slate-600">
            <LayersIcon className="h-4 w-4" aria-hidden />
            Queue depth
          </div>
          <p className="mt-2 text-2xl font-semibold text-slate-900">{device.queueDepth}</p>
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-slate-600">
            <ArrowRightIcon className="h-4 w-4" aria-hidden />
            Assignment
          </div>
          {assignment ? (
            <AssignmentSummary assignment={assignment} />
          ) : (
            <p className="mt-2 text-sm text-slate-500">No active lot</p>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-primary-600">
        <span className="flex items-center gap-1">
          View device
          <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  )
}
