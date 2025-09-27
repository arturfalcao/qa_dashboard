'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FilterIcon } from 'lucide-react'

import { DeviceCard } from '@/components/operator/device-card'
import { apiClient } from '@/lib/api'

const ALL_SITES = 'all-sites'

export default function OperatorHomePage() {
  const [site, setSite] = useState<string>(ALL_SITES)

  const { data: devices = [], isLoading } = useQuery({
    queryKey: ['operator', 'devices', site],
    queryFn: () => apiClient.getOperatorDevices(site === ALL_SITES ? undefined : site),
  })

  const availableSites = useMemo(() => {
    const unique = new Set<string>()
    devices.forEach((device) => {
      if (device.site) {
        unique.add(device.site)
      }
    })
    return Array.from(unique).sort((a, b) => a.localeCompare(b))
  }, [devices])

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:flex-row md:items-center">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Devices</h2>
          <p className="text-sm text-slate-600">
            Monitor queue depth, live assignments and recent edge events per inspection device.
          </p>
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <FilterIcon className="h-4 w-4" aria-hidden />
          <span className="sr-only">Filter by site</span>
          <select
            value={site}
            onChange={(event) => setSite(event.target.value)}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
          >
            <option value={ALL_SITES}>All sites</option>
            {availableSites.map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>
        </label>
      </section>

      {isLoading ? (
        <div className="flex min-h-[200px] items-center justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-primary-500" />
        </div>
      ) : devices.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-600">
          No devices registered for this site yet.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {devices.map((device) => (
            <DeviceCard key={device.id} device={device} />
          ))}
        </div>
      )}
    </div>
  )
}
