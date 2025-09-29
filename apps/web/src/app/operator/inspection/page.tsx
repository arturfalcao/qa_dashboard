'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/providers/auth-provider'

interface Device {
  id: string
  name: string
  workbenchNumber: number
  status: string
}

interface Lot {
  id: string
  styleRef: string
  quantityTotal: number
  status: string
  factory?: {
    name: string
  }
}

export default function InspectionHomePage() {
  const { user } = useAuth()
  const router = useRouter()
  const [devices, setDevices] = useState<Device[]>([])
  const [lots, setLots] = useState<Lot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedDevice, setSelectedDevice] = useState('')
  const [selectedLot, setSelectedLot] = useState('')
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      // For now, get all devices and lots from tenant
      // TODO: Filter to assigned devices for operator
      const [devicesRes, lotsRes] = await Promise.all([
        apiClient.getAllDevices(),
        apiClient.getLots(),
      ])
      setDevices(devicesRes.devices.filter((d: any) => d.status === 'active'))
      setLots(lotsRes.filter((l: any) => l.status === 'IN_PRODUCTION' || l.status === 'PLANNED'))
    } catch (err: any) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleStartSession = async () => {
    if (!selectedDevice || !selectedLot) {
      alert('Please select both device and lot')
      return
    }

    try {
      setStarting(true)
      const response = await apiClient.startInspectionSession({
        lotId: selectedLot,
        deviceId: selectedDevice,
      })
      router.push(`/operator/inspection/${response.sessionId}`)
    } catch (err: any) {
      alert(err.message || 'Failed to start session')
    } finally {
      setStarting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="max-w-md p-8 bg-white rounded-2xl shadow-lg">
          <div className="text-red-600 text-center">
            <div className="text-6xl mb-4">⚠️</div>
            <p className="text-lg font-semibold">Error</p>
            <p className="text-sm mt-2 text-slate-600">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Quality Inspection</h1>
          <p className="text-lg text-slate-600">Welcome, {user?.email}</p>
        </div>

        {/* Start Session Card */}
        <div className="bg-white rounded-3xl shadow-xl p-8 md:p-12">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-primary-100 rounded-full mb-4">
              <span className="text-4xl">📸</span>
            </div>
            <h2 className="text-2xl font-semibold text-slate-900">Start New Inspection</h2>
            <p className="text-slate-600 mt-2">Select your workbench and lot to begin</p>
          </div>

          <div className="space-y-6">
            {/* Device Selection */}
            <div>
              <label className="block text-lg font-medium text-slate-700 mb-3">
                Select Workbench
              </label>
              <select
                value={selectedDevice}
                onChange={(e) => setSelectedDevice(e.target.value)}
                className="w-full text-lg px-6 py-4 border-2 border-slate-200 rounded-2xl focus:border-primary-500 focus:outline-none focus:ring-4 focus:ring-primary-100 transition"
              >
                <option value="">Choose your workbench...</option>
                {devices.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.name} (Workbench #{device.workbenchNumber})
                  </option>
                ))}
              </select>
              {devices.length === 0 && (
                <p className="text-sm text-amber-600 mt-2">⚠️ No active devices available</p>
              )}
            </div>

            {/* Lot Selection */}
            <div>
              <label className="block text-lg font-medium text-slate-700 mb-3">
                Select Lot
              </label>
              <select
                value={selectedLot}
                onChange={(e) => setSelectedLot(e.target.value)}
                className="w-full text-lg px-6 py-4 border-2 border-slate-200 rounded-2xl focus:border-primary-500 focus:outline-none focus:ring-4 focus:ring-primary-100 transition"
              >
                <option value="">Choose lot to inspect...</option>
                {lots.map((lot) => (
                  <option key={lot.id} value={lot.id}>
                    {lot.styleRef} - {lot.quantityTotal} pieces ({lot.factory?.name || 'Unknown'})
                  </option>
                ))}
              </select>
              {lots.length === 0 && (
                <p className="text-sm text-amber-600 mt-2">⚠️ No lots available for inspection</p>
              )}
            </div>

            {/* Start Button */}
            <button
              onClick={handleStartSession}
              disabled={!selectedDevice || !selectedLot || starting}
              className="w-full py-5 px-8 bg-primary-600 text-white rounded-2xl font-semibold text-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 active:translate-y-0"
            >
              {starting ? (
                <span className="flex items-center justify-center gap-3">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                  Starting Session...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-3">
                  <span>🚀</span>
                  Start Inspection
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Info Card */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-6">
          <div className="flex items-start gap-3">
            <span className="text-2xl">💡</span>
            <div>
              <h3 className="font-semibold text-blue-900 mb-1">Before You Start</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Ensure your workbench camera is connected</li>
                <li>• Keyboard shortcuts are ready (Keys 1-4)</li>
                <li>• Good lighting conditions for photo capture</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}