'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface Lot {
  id: string
  styleRef: string
  quantityTotal: number
  status: string
  defectRate: number
  inspectedProgress: number
  factory?: {
    name: string
  }
}

interface Device {
  id: string
  name: string
  workbenchNumber: number
  status: string
  assignedOperator?: {
    id: string
    email: string
  }
}

export default function TenantLotsPage() {
  const params = useParams()
  const router = useRouter()
  const tenantId = params.tenantId as string

  const [tenant, setTenant] = useState<any>(null)
  const [lots, setLots] = useState<Lot[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [assigningLot, setAssigningLot] = useState<string | null>(null)
  const [selectedDevices, setSelectedDevices] = useState<Record<string, string>>({})

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [lotsResponse, devicesResponse] = await Promise.all([
        apiClient.getTenantLots(tenantId),
        apiClient.getAllDevices(),
      ])
      setTenant(lotsResponse.tenant)
      setLots(lotsResponse.lots)
      setDevices(devicesResponse.devices)
    } catch (err: any) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleAssignLot = async (lotId: string) => {
    const selectedDeviceId = selectedDevices[lotId]
    if (!selectedDeviceId) {
      alert('Please select a device')
      return
    }

    try {
      setAssigningLot(lotId)
      const device = devices.find((d) => d.id === selectedDeviceId)
      await apiClient.assignLotToDevice(selectedDeviceId, {
        lotId,
        operatorId: device?.assignedOperator?.id,
      })
      alert('Lot assigned successfully!')
      await loadData()
      setAssigningLot(null)
      // Clear the selected device for this lot after successful assignment
      setSelectedDevices((prev) => {
        const updated = { ...prev }
        delete updated[lotId]
        return updated
      })
    } catch (err: any) {
      alert(err.message || 'Failed to assign lot')
      setAssigningLot(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-red-800">
        <p className="text-sm font-medium">Error: {error}</p>
      </div>
    )
  }

  const availableDevices = devices.filter((d) => d.status === 'active')

  return (
    <div>
      <div className="mb-6">
        <button
          onClick={() => router.push('/admin/tenants')}
          className="text-sm text-slate-600 hover:text-slate-900 mb-2"
        >
          ← Back to Tenants
        </button>
        <h2 className="text-2xl font-semibold text-slate-900">
          {tenant?.name} - Lots
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          View and assign lots to devices for inspection
        </p>
      </div>

      {lots.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-slate-300 p-12 text-center">
          <p className="text-slate-500">No lots found for this tenant</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Style Ref
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Quantity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Progress
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Factory
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {lots.map((lot) => (
                <tr key={lot.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-slate-900">{lot.styleRef}</div>
                    <div className="text-xs text-slate-500">{lot.id.substring(0, 8)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                    {lot.quantityTotal}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                        lot.status === 'INSPECTION'
                          ? 'bg-blue-100 text-blue-800'
                          : lot.status === 'IN_PRODUCTION'
                          ? 'bg-yellow-100 text-yellow-800'
                          : lot.status === 'PENDING_APPROVAL'
                          ? 'bg-orange-100 text-orange-800'
                          : lot.status === 'APPROVED'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      {lot.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                    {lot.inspectedProgress}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                    {lot.factory?.name || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    {lot.status === 'IN_PRODUCTION' || lot.status === 'INSPECTION' ? (
                      <div className="flex items-center justify-end gap-2">
                        <select
                          value={selectedDevices[lot.id] || ''}
                          onChange={(e) => {
                            setSelectedDevices((prev) => ({
                              ...prev,
                              [lot.id]: e.target.value,
                            }))
                          }}
                          className="text-sm border border-slate-300 rounded px-2 py-1 min-w-[250px]"
                          disabled={assigningLot !== null && assigningLot !== lot.id}
                        >
                          <option value="">Select Device</option>
                          {availableDevices.map((device) => (
                            <option key={device.id} value={device.id}>
                              {device.name} (WB #{device.workbenchNumber})
                              {device.assignedOperator
                                ? ` - ${device.assignedOperator.email}`
                                : ' - No operator'}
                            </option>
                          ))}
                        </select>
                        <Button
                          onClick={() => handleAssignLot(lot.id)}
                          disabled={assigningLot === lot.id || !selectedDevices[lot.id]}
                          size="sm"
                        >
                          {assigningLot === lot.id ? 'Assigning...' : 'Assign'}
                        </Button>
                      </div>
                    ) : (
                      <span className="text-slate-400">Not available</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
