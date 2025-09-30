'use client'

import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'

interface Device {
  id: string
  tenantId: string
  name: string
  secretKey: string
  workbenchNumber: number
  status: 'active' | 'inactive' | 'maintenance'
  lastSeenAt: string | null
  assignedOperatorId: string | null
  assignedOperator: {
    id: string
    email: string
  } | null
}

interface Tenant {
  id: string
  name: string
  slug: string
}

interface Operator {
  id: string
  email: string
  tenantId: string
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([])
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showSecretModal, setShowSecretModal] = useState(false)
  const [newDeviceSecret, setNewDeviceSecret] = useState('')
  const [selectedTenantFilter, setSelectedTenantFilter] = useState('')

  // Create device form
  const [createForm, setCreateForm] = useState({
    tenantId: '',
    name: '',
    workbenchNumber: 1,
  })

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [devicesRes, tenantsRes, operatorsRes] = await Promise.all([
        apiClient.getAllDevices(selectedTenantFilter || undefined),
        apiClient.getAllTenants(),
        apiClient.getAllOperators(selectedTenantFilter || undefined),
      ])
      setDevices(devicesRes.devices)
      setTenants(tenantsRes.tenants)
      setOperators(operatorsRes.operators)
    } catch (err: any) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [selectedTenantFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await apiClient.createDevice(createForm)
      setNewDeviceSecret(response.device.secretKey)
      setShowCreateModal(false)
      setShowSecretModal(true)
      loadData()
      setCreateForm({ tenantId: '', name: '', workbenchNumber: 1 })
    } catch (err: any) {
      alert(err.message || 'Failed to create device')
    }
  }

  const handleAssignOperator = async (deviceId: string, operatorId: string) => {
    try {
      await apiClient.assignOperatorToDevice(deviceId, operatorId)
      loadData()
    } catch (err: any) {
      alert(err.message || 'Failed to assign operator')
    }
  }

  const handleUnassignOperator = async (deviceId: string) => {
    try {
      await apiClient.unassignOperatorFromDevice(deviceId)
      loadData()
    } catch (err: any) {
      alert(err.message || 'Failed to unassign operator')
    }
  }

  const handleUpdateStatus = async (deviceId: string, status: 'active' | 'inactive' | 'maintenance') => {
    try {
      await apiClient.updateDeviceStatus(deviceId, status)
      loadData()
    } catch (err: any) {
      alert(err.message || 'Failed to update device status')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    alert('Copied to clipboard!')
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

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Edge Devices</h2>
          <p className="mt-1 text-sm text-slate-500">Manage workbench devices and secrets</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium text-sm"
        >
          + Create Device
        </button>
      </div>

      {/* Tenant Filter */}
      <div className="mb-4">
        <select
          value={selectedTenantFilter}
          onChange={(e) => setSelectedTenantFilter(e.target.value)}
          className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">All Tenants</option>
          {tenants.map((tenant) => (
            <option key={tenant.id} value={tenant.id}>
              {tenant.name}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Device
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Workbench
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Assigned Operator
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Last Seen
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {devices.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-sm text-slate-500">
                  No devices found
                </td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr key={device.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-slate-900">{device.name}</div>
                      <div className="text-xs text-slate-500 font-mono">{device.secretKey.substring(0, 30)}...</div>
                      <button
                        onClick={() => copyToClipboard(device.secretKey)}
                        className="text-xs text-primary-600 hover:text-primary-800 mt-1"
                      >
                        Copy Secret
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">
                    #{device.workbenchNumber}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <select
                      value={device.status}
                      onChange={(e) => handleUpdateStatus(device.id, e.target.value as any)}
                      className={`text-xs px-2 py-1 rounded-full font-semibold ${
                        device.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : device.status === 'maintenance'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="maintenance">Maintenance</option>
                    </select>
                  </td>
                  <td className="px-6 py-4">
                    {device.assignedOperator ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-900">{device.assignedOperator.email}</span>
                        <button
                          onClick={() => handleUnassignOperator(device.id)}
                          className="text-xs text-red-600 hover:text-red-800"
                        >
                          Unassign
                        </button>
                      </div>
                    ) : (
                      <select
                        onChange={(e) => handleAssignOperator(device.id, e.target.value)}
                        className="text-sm border border-slate-300 rounded px-2 py-1"
                        defaultValue=""
                      >
                        <option value="" disabled>
                          Assign operator...
                        </option>
                        {operators
                          .filter((op) => op.tenantId === device.tenantId)
                          .map((op) => (
                            <option key={op.id} value={op.id}>
                              {op.email}
                            </option>
                          ))}
                      </select>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                    {device.lastSeenAt ? new Date(device.lastSeenAt).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => copyToClipboard(device.secretKey)}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      Copy Secret
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Device Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Create New Device</h3>
            <form onSubmit={handleCreateDevice} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tenant</label>
                <select
                  required
                  value={createForm.tenantId}
                  onChange={(e) => setCreateForm({ ...createForm, tenantId: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                >
                  <option value="">Select tenant...</option>
                  {tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Device Name</label>
                <input
                  type="text"
                  required
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  placeholder="e.g., Workbench 1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Workbench Number</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={createForm.workbenchNumber}
                  onChange={(e) => setCreateForm({ ...createForm, workbenchNumber: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Device Secret Modal */}
      {showSecretModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full">
            <h3 className="text-lg font-semibold mb-4 text-green-600">✓ Device Created Successfully</h3>
            <p className="text-sm text-slate-600 mb-4">
              Save this device secret securely. You won’t be able to see it again!
            </p>
            <div className="bg-slate-100 p-4 rounded-lg mb-4">
              <code className="text-sm font-mono break-all">{newDeviceSecret}</code>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => copyToClipboard(newDeviceSecret)}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Copy Secret
              </button>
              <button
                onClick={() => setShowSecretModal(false)}
                className="flex-1 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}