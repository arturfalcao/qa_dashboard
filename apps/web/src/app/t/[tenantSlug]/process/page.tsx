'use client'

import { ProcessTrackingDashboard } from '@/components/process/process-tracking-dashboard'

export default function ProcessPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Process Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time visibility into garment processing stages
          </p>
        </div>
      </div>

      <ProcessTrackingDashboard />
    </div>
  )
}