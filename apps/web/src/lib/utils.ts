import { LotStatus } from '@qa-dashboard/shared'
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const formatDate = (date: string | Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export const formatRelativeTime = (date: string | Date): string => {
  const now = new Date()
  const target = new Date(date)
  const diffInSeconds = Math.floor((now.getTime() - target.getTime()) / 1000)

  if (diffInSeconds < 60) {
    return 'Just now'
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60)
    return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600)
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`
  } else {
    const days = Math.floor(diffInSeconds / 86400)
    return `${days} day${days !== 1 ? 's' : ''} ago`
  }
}

export const formatPercentage = (value: number): string => {
  return `${value.toFixed(1)}%`
}

export const formatNumber = (value: number): string => {
  return new Intl.NumberFormat('en-US').format(value)
}

export const getDefectColor = (defectType: string): string => {
  const colors: Record<string, string> = {
    stain: 'bg-red-100 text-red-800',
    stitching: 'bg-orange-100 text-orange-800',
    misprint: 'bg-purple-100 text-purple-800',
    measurement: 'bg-blue-100 text-blue-800',
    other: 'bg-gray-100 text-gray-800',
  }
  return colors[defectType] || colors.other
}

export const getLotStatusColor = (status: string): string => {
  const normalized = status.toUpperCase()
  const colors: Record<string, string> = {
    INSPECTION: 'bg-blue-100 text-blue-800',
    PENDING_APPROVAL: 'bg-yellow-100 text-yellow-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
    SHIPPED: 'bg-emerald-100 text-emerald-800',
  }
  return colors[normalized] || 'bg-gray-100 text-gray-800'
}

export const formatLotStatus = (status: LotStatus | string): string => {
  const mapping: Record<string, string> = {
    [LotStatus.PLANNED]: 'Planned',
    [LotStatus.IN_PRODUCTION]: 'In production',
    [LotStatus.INSPECTION]: 'In inspection',
    [LotStatus.PENDING_APPROVAL]: 'Pending approval',
    [LotStatus.APPROVED]: 'Approved',
    [LotStatus.REJECTED]: 'Rejected',
    [LotStatus.SHIPPED]: 'Shipped',
  }
  const key = typeof status === 'string' ? status.toUpperCase() : status
  return mapping[key as LotStatus] || key.toString()
}
