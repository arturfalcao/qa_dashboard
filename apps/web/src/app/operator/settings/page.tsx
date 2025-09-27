'use client'

import { useAuth } from '@/components/providers/auth-provider'
import { UserRole } from '@qa-dashboard/shared'

export default function OperatorSettingsPage() {
  const { user } = useAuth()
  const canEdit = user?.roles?.some((role) => role === UserRole.SUPERVISOR || role === UserRole.ADMIN)

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Site configuration</h2>
        <p className="mt-2 text-sm text-slate-600">
          Review offline thresholds, camera firmware versions and label templates for each device. This view
          summarises the values currently used by the edge API.
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-700">Offline queue thresholds</h3>
          <p className="mt-2 text-sm text-slate-600">
            Tablets warn operators when the local queue exceeds <strong>5 items</strong> or the last sync is older than
            <strong> 10 minutes</strong>. These defaults ensure visibility even when the network is unstable.
          </p>
          {!canEdit && (
            <p className="mt-3 text-xs text-slate-500">
              Supervisor privileges are required to edit thresholds.
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-700">Firmware cadence</h3>
          <p className="mt-2 text-sm text-slate-600">
            Edge devices currently run firmware versions 1.3.9 to 1.4.2. The API exposes upgrade windows every Friday at
            22:00 local time to avoid disrupting shifts.
          </p>
        </div>
      </div>
    </div>
  )
}
