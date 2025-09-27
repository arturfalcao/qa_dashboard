import { DeviceStatus } from '@qa-dashboard/shared'

import { cn } from '@/lib/utils'

const STATUS_STYLES: Record<DeviceStatus, { label: string; className: string }> = {
  [DeviceStatus.ONLINE]: {
    label: 'Online',
    className: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  },
  [DeviceStatus.OFFLINE]: {
    label: 'Offline',
    className: 'bg-gray-100 text-gray-600 border border-gray-200',
  },
  [DeviceStatus.DEGRADED]: {
    label: 'Degraded',
    className: 'bg-amber-100 text-amber-700 border border-amber-200',
  },
}

interface DeviceStatusPillProps {
  status: DeviceStatus
}

export function DeviceStatusPill({ status }: DeviceStatusPillProps) {
  const { label, className } = STATUS_STYLES[status]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium tracking-wide uppercase',
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {label}
    </span>
  )
}
