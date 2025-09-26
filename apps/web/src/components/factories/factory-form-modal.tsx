'use client'

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Factory, SupplyChainRole } from '@qa-dashboard/shared'
import { useAuth } from '@/components/providers/auth-provider'
import { UserRole } from '@qa-dashboard/shared'

interface FactoryFormModalProps {
  isOpen: boolean
  onClose: () => void
  initialFactory?: Factory | null
}

type CapabilityDraft = {
  co2Override: string
  notes: string
}

const toInputString = (value?: number | string | null) => {
  if (value === undefined || value === null) {
    return ''
  }
  const numeric = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(numeric)) {
    return ''
  }
  return numeric.toString()
}

const CERTIFICATION_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'GOTS', label: 'Global Organic Textile Standard (GOTS)' },
  { value: 'OEKO_TEX_STANDARD_100', label: 'OEKO-TEX Standard 100' },
  { value: 'GRS', label: 'Global Recycled Standard (GRS)' },
  { value: 'RCS', label: 'Recycled Claim Standard (RCS)' },
  { value: 'ISO_14001', label: 'ISO 14001' },
  { value: 'BLUESIGN', label: 'Bluesign' },
  { value: 'AMFORI_BSCI', label: 'amfori BSCI' },
]

export function FactoryFormModal({ isOpen, onClose, initialFactory }: FactoryFormModalProps) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [city, setCity] = useState('')
  const [country, setCountry] = useState('PT')
  const [selectedCapabilities, setSelectedCapabilities] = useState<Record<string, CapabilityDraft>>({})
  const [selectedCertifications, setSelectedCertifications] = useState<string[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (initialFactory) {
      setName(initialFactory.name)
      setCity(initialFactory.city || '')
      setCountry(initialFactory.country || 'PT')
      const capabilityDrafts = (initialFactory.capabilities ?? []).reduce<Record<string, CapabilityDraft>>(
        (acc, capability) => {
          acc[capability.roleId] = {
            co2Override: toInputString(capability.co2OverrideKg ?? capability.role?.defaultCo2Kg ?? null),
            notes: capability.notes ?? '',
          }
          return acc
        },
        {},
      )
      setSelectedCapabilities(capabilityDrafts)
      setSelectedCertifications(
        (initialFactory.certifications ?? []).map((certification) => certification.certification),
      )
    } else {
      setName('')
      setCity('')
      setCountry('PT')
      setSelectedCapabilities({})
      setSelectedCertifications([])
    }
    setError('')
  }, [initialFactory, isOpen])

  const { data: supplyChainRoles = [], isLoading: rolesLoading } = useQuery<SupplyChainRole[]>({
    queryKey: ['supply-chain-roles'],
    queryFn: () => apiClient.getSupplyChainRoles(),
    enabled: isOpen,
  })

  const mutation = useMutation({
    mutationFn: (payload: {
      name: string
      city?: string
      country?: string
      capabilities?: Array<{ roleId: string; co2OverrideKg?: number | null; notes?: string | null }>
      certifications?: Array<{ certification: string }>
    }) =>
      initialFactory
        ? apiClient.updateFactory(initialFactory.id, payload)
        : apiClient.createFactory(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['factories'] })
      onClose()
    },
    onError: (err: any) => {
      setError(err?.message || 'Failed to save factory')
    },
  })

  const toggleRole = (roleId: string, defaultCo2: number | string | null | undefined) => {
    setSelectedCapabilities((current) => {
      if (current[roleId]) {
        const { [roleId]: _removed, ...rest } = current
        return rest
      }

      return {
        ...current,
        [roleId]: {
          co2Override: toInputString(defaultCo2),
          notes: '',
        },
      }
    })
  }

  const updateCapabilityCo2 = (roleId: string, value: string) => {
    setSelectedCapabilities((current) => {
      const existing = current[roleId]
      if (!existing) {
        return current
      }
      return {
        ...current,
        [roleId]: {
          ...existing,
          co2Override: value,
        },
      }
    })
  }

  const updateCapabilityNotes = (roleId: string, value: string) => {
    setSelectedCapabilities((current) => {
      const existing = current[roleId]
      if (!existing) {
        return current
      }
      return {
        ...current,
        [roleId]: {
          ...existing,
          notes: value,
        },
      }
    })
  }

  const sortedRoles = useMemo(
    () =>
      [...supplyChainRoles].sort((a, b) => {
        if (a.defaultSequence !== b.defaultSequence) {
          return a.defaultSequence - b.defaultSequence
        }
        return a.name.localeCompare(b.name)
      }),
    [supplyChainRoles],
  )

  const selectedRoleIds = Object.keys(selectedCapabilities)

  const toggleCertification = (value: string) => {
    setSelectedCertifications((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    )
  }

  if (!isOpen) return null

  const canEdit = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))
  if (!canEdit) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl max-h-[90vh] rounded-lg bg-white shadow-xl flex flex-col">
        <div className="border-b px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {initialFactory ? 'Edit Factory' : 'Add Factory'}
          </h3>
          <p className="text-sm text-gray-500">
            Keep your supplier directory up to date for lot creation.
          </p>
        </div>
        <form
          className="flex-1 overflow-y-auto space-y-4 px-6 py-5"
          onSubmit={(e) => {
            e.preventDefault()
            if (!name.trim()) {
              setError('Factory name is required')
              return
            }
            if (!rolesLoading && sortedRoles.length > 0 && selectedRoleIds.length === 0) {
              setError('Select at least one supply-chain capability for this factory')
              return
            }

            const capabilities = selectedRoleIds.map((roleId) => {
              const draft = selectedCapabilities[roleId]
              const trimmedNotes = draft?.notes?.trim() ?? ''
              const co2Value = draft?.co2Override?.trim() ?? ''

              if (co2Value !== '') {
                const parsed = Number(co2Value)
                if (Number.isNaN(parsed) || parsed < 0) {
                  setError('CO₂ override must be a non-negative number')
                  return null
                }
              }

              return {
                roleId,
                co2OverrideKg:
                  co2Value === '' ? undefined : Number(co2Value),
                notes: trimmedNotes === '' ? undefined : trimmedNotes,
              }
            })

            if (capabilities.some((capability) => capability === null)) {
              return
            }

            setError('')
            mutation.mutate({
              name,
              city: city || undefined,
              country,
              capabilities:
                capabilities.length > 0
                  ? (capabilities as Array<{ roleId: string; co2OverrideKg?: number; notes?: string }>)
                  : undefined,
              certifications: selectedCertifications.map((certification) => ({ certification })),
            })
          }}
        >
          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={mutation.isPending}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              placeholder="e.g. Atlantic Apparel"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">City</label>
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              disabled={mutation.isPending}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              placeholder="Guimarães"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Country</label>
            <input
              type="text"
              value={country}
              maxLength={2}
              onChange={(e) => setCountry(e.target.value.toUpperCase())}
              disabled={mutation.isPending}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm uppercase shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            />
            <p className="mt-1 text-xs text-gray-500">Use ISO 3166-1 alpha-2 (e.g. PT, ES, IT).</p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Supply-chain capabilities</label>
            <div className="space-y-2">
              {rolesLoading ? (
                <div className="rounded-md border border-dashed border-gray-200 p-4 text-sm text-gray-500">
                  Loading roles…
                </div>
              ) : sortedRoles.length === 0 ? (
                <div className="rounded-md border border-dashed border-gray-200 p-4 text-sm text-gray-500">
                  No roles configured yet.
                </div>
              ) : (
                sortedRoles.map((role) => (
                  <div key={role.id} className="rounded-md border border-gray-200 px-3 py-2">
                    <label className="flex items-start space-x-3 text-sm">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500"
                        checked={Boolean(selectedCapabilities[role.id])}
                        onChange={() => toggleRole(role.id, role.defaultCo2Kg)}
                        disabled={mutation.isPending}
                      />
                      <span>
                        <span className="font-medium text-gray-900">{role.name}</span>
                        {role.description && (
                          <span className="block text-xs text-gray-500">{role.description}</span>
                        )}
                        <span className="block text-xs text-gray-400">
                          Default CO₂: {Number(role.defaultCo2Kg ?? 0).toFixed(2)} kg
                        </span>
                      </span>
                    </label>
                    {selectedCapabilities[role.id] && (
                      <div className="mt-3 space-y-2 border-t border-dashed border-gray-200 pt-3 text-xs">
                        <div>
                          <label className="mb-1 block font-semibold text-gray-600">
                            CO₂ override (kg)
                          </label>
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={selectedCapabilities[role.id]?.co2Override ?? ''}
                            onChange={(e) => updateCapabilityCo2(role.id, e.target.value)}
                            disabled={mutation.isPending}
                            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                            placeholder="Use default if empty"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block font-semibold text-gray-600">Internal notes</label>
                          <textarea
                            value={selectedCapabilities[role.id]?.notes ?? ''}
                            onChange={(e) => updateCapabilityNotes(role.id, e.target.value)}
                            disabled={mutation.isPending}
                            rows={2}
                            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                            placeholder="Optional context or restrictions"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              These capabilities define which production stages the factory can take on.
            </p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Certifications</label>
            <div className="space-y-2">
              {CERTIFICATION_OPTIONS.map((option) => (
                <label key={option.value} className="flex items-start space-x-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500"
                    checked={selectedCertifications.includes(option.value)}
                    onChange={() => toggleCertification(option.value)}
                    disabled={mutation.isPending}
                  />
                  <span className="text-gray-700">{option.label}</span>
                </label>
              ))}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Certifications are displayed in the DPP hub and supplier reports.
            </p>
          </div>

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={() => {
                if (mutation.isPending) return
                onClose()
              }}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 disabled:opacity-60"
            >
              {mutation.isPending ? (initialFactory ? 'Saving…' : 'Creating…') : initialFactory ? 'Save changes' : 'Create factory'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
